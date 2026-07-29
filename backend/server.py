"""PulseVault AI — Autonomous Podcast Intelligence Studio backend."""
import os
import json
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List, Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from groq import Groq

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GROQ_LLM_MODEL = os.environ.get("GROQ_LLM_MODEL", "llama-3.3-70b-versatile")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("pulsevault")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
episodes_col = db["episodes"]
events_col = db["events"]

groq_client = Groq(api_key=GROQ_API_KEY)

# In-memory pub/sub for WebSocket streaming per job
job_queues: Dict[str, "asyncio.Queue[dict]"] = {}


# -------------------- Demo transcripts --------------------
DEMO_EPISODES = {
    "demo-huberman": {
        "title": "The Science of Focus & Deep Work",
        "host": "Andrew Huberman",
        "guest": "Cal Newport",
        "url": "demo://huberman-focus",
        "duration_sec": 4200,
        "transcript": (
            "Welcome back to the podcast. Today we're talking with Cal Newport about deep work "
            "and how focus is a trainable skill. Cal, welcome. Thanks Andrew, great to be here. "
            "So let's start with the neuroscience of attention. When you sit down to work on a "
            "cognitively demanding task, the prefrontal cortex has to inhibit competing signals. "
            "The interesting finding from recent papers is that context switching literally leaves "
            "residue in the brain — attention residue that lasts up to 20 minutes. "
            "The single most impactful thing anybody can do is protect a 90-minute block of "
            "uninterrupted, phone-away, notification-off deep work every single morning. "
            "One thing I want people to hear: multitasking is a myth. Your brain does not do it. "
            "You are just rapidly switching, and each switch has a cost. Cal you have this "
            "wonderful line — clarity about what matters provides clarity about what does not. "
            "That's actually the entire operating system for a focused life. "
            "For students I'd say: measure your deep work hours the way athletes measure reps. "
            "Then let's talk about the dopamine piece. Cheap dopamine from short-form video "
            "raises your baseline, and everything effortful feels boring by comparison. "
            "The prescription is boredom tolerance. Sit with the discomfort. It rewires you. "
            "We close with actionable tools: a shutdown ritual, a weekly review, and a strict "
            "no-phone-in-the-bedroom rule. Thank you Cal, this was fantastic."
        ),
    },
    "demo-lex": {
        "title": "Building Machines That Think — AGI, Alignment & the Next Decade",
        "host": "Lex Fridman",
        "guest": "Dr. Ilya Sutskever",
        "url": "demo://lex-agi",
        "duration_sec": 7200,
        "transcript": (
            "Ilya, thanks for coming on. The question everyone wants to know: are we close to AGI. "
            "I think we are closer than most people realize, but the last mile is the hardest. "
            "Scaling laws still hold, but the interesting bottleneck is now data quality and reasoning. "
            "The models learn a compressed model of the world. That compression is intelligence. "
            "On alignment: the biggest risk isn't a rogue agent, it's slow value drift at scale. "
            "Small misalignments compounded across billions of interactions become systemic. "
            "I want to be optimistic. Human-AI collaboration will feel like a superpower. "
            "Coders will feel it first, then scientists, then artists, then everyone. "
            "The philosophical question — will these systems be conscious — I honestly don't know. "
            "But I know we should treat that question with humility, not certainty. "
            "Lex, one thing I've come to appreciate: love is the training signal for humanity. "
            "Curiosity is the loss function. If we optimize those, the machines will be fine. "
            "We end with a lightning round on books, on regret, and on hope for the next generation."
        ),
    },
}


# -------------------- Models --------------------
class IngestRequest(BaseModel):
    url: str
    demo_id: Optional[str] = None
    title: Optional[str] = None


class EpisodeOut(BaseModel):
    id: str
    url: str
    title: Optional[str] = None
    status: str
    created_at: str
    result: Optional[Dict[str, Any]] = None


# -------------------- LLM helpers --------------------
async def groq_chat(prompt: str, system: str = "You are a helpful assistant.", max_tokens: int = 800, json_mode: bool = False) -> str:
    def _call():
        kwargs = dict(
            model=GROQ_LLM_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_completion_tokens=max_tokens,
        )
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        r = groq_client.chat.completions.create(**kwargs)
        return r.choices[0].message.content
    return await asyncio.to_thread(_call)


async def gemini_chat(prompt: str, max_tokens: int = 1200) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.5, "maxOutputTokens": max_tokens},
    }
    async with httpx.AsyncClient(timeout=90) as http:
        resp = await http.post(
            url,
            headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
            json=body,
        )
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


async def smart_chat(prompt: str, system: str = "You are a helpful assistant.", max_tokens: int = 1000, prefer: str = "gemini", json_mode: bool = False) -> str:
    """Try preferred provider first, fall back to the other on any failure."""
    providers = [prefer, "groq" if prefer == "gemini" else "gemini"]
    last_err = None
    for p in providers:
        try:
            if p == "gemini":
                return await gemini_chat(prompt, max_tokens=max_tokens)
            return await groq_chat(prompt, system=system, max_tokens=max_tokens, json_mode=json_mode)
        except Exception as e:
            last_err = e
            log.warning(f"{p} failed: {e}; trying next provider")
    raise RuntimeError(f"all providers failed: {last_err}")


async def groq_transcribe_url(audio_url: str) -> str:
    target_url = audio_url.strip()
    if "archive.org/details/" in target_url:
        target_url = target_url.replace("archive.org/details/", "archive.org/download/")
        log.info(f"rewrote archive.org details URL to download URL: {target_url}")

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    async with httpx.AsyncClient(follow_redirects=True, timeout=120, headers=headers) as http:
        resp = await http.get(target_url)
        resp.raise_for_status()
        audio_bytes = resp.content

    filename = target_url.split("/")[-1].split("?")[0] or "audio.mp3"
    if not any(filename.lower().endswith(ext) for ext in [".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"]):
        filename += ".mp3"

    def _call():
        r = groq_client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=(filename, audio_bytes),
            temperature=0.0,
            response_format="verbose_json",
        )
        return r.text

    return await asyncio.to_thread(_call)


def _strip_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        # remove leading language tag like "json"
        first_nl = text.find("\n")
        if first_nl != -1:
            text = text[first_nl + 1:]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


async def parse_json_response(text: str) -> Any:
    cleaned = _strip_json(text)
    try:
        return json.loads(cleaned)
    except Exception:
        # try to find first { or [
        for start in ("[", "{"):
            i = cleaned.find(start)
            if i != -1:
                try:
                    return json.loads(cleaned[i:])
                except Exception:
                    pass
        return None


# -------------------- Pub/sub helpers --------------------
async def emit(job_id: str, event: dict):
    event["ts"] = datetime.now(timezone.utc).isoformat()
    q = job_queues.get(job_id)
    if q is not None:
        await q.put(event)
    await events_col.insert_one({"job_id": job_id, **event})


async def log_agent(job_id: str, agent: str, message: str, level: str = "info"):
    await emit(job_id, {"type": "log", "agent": agent, "level": level, "message": message})


# -------------------- Agent pipeline --------------------
async def run_pipeline(job_id: str, url: str, demo_id: Optional[str], title: Optional[str]):
    try:
        await log_agent(job_id, "ORCHESTRATOR", ">>> booting agent swarm for job " + job_id[:8])
        await log_agent(job_id, "ORCHESTRATOR", "target url = " + url)

        # 1. AudioIngestAgent
        await log_agent(job_id, "AUDIO_INGEST", "acquiring audio stream...")
        transcript = None
        detected_title = title
        detected_host = None
        detected_guest = None

        if demo_id and demo_id in DEMO_EPISODES:
            demo = DEMO_EPISODES[demo_id]
            transcript = demo["transcript"]
            detected_title = detected_title or demo["title"]
            detected_host = demo["host"]
            detected_guest = demo["guest"]
            await log_agent(job_id, "AUDIO_INGEST", f"loaded demo transcript '{demo['title']}' [{len(transcript)} chars]")
        else:
            try:
                await log_agent(job_id, "AUDIO_INGEST", "calling groq whisper-large-v3 on url...")
                transcript = await asyncio.wait_for(groq_transcribe_url(url), timeout=120)
                await log_agent(job_id, "AUDIO_INGEST", f"transcribed [{len(transcript)} chars]")
            except Exception as e:
                await log_agent(job_id, "AUDIO_INGEST", f"transcription failed: {e}", level="warn")
                await log_agent(job_id, "AUDIO_INGEST", "falling back to metadata-only mode")
                transcript = (
                    f"[No direct audio transcription available for the provided URL: {url}]\n"
                    "The following agents will operate on the URL metadata only. "
                    "For best results, provide a direct .mp3/.wav audio URL or use a demo episode."
                )

        if not detected_title and transcript and len(transcript) > 50 and not transcript.startswith("[No direct"):
            try:
                title_prompt = (
                    "Based on the following transcript, generate a concise, professional, engaging episode title (3-7 words). "
                    "Return ONLY the title text, with no quotes or extra formatting.\n\n" + transcript[:2000]
                )
                gen_title = await smart_chat(title_prompt, max_tokens=30, prefer="gemini")
                if gen_title:
                    detected_title = gen_title.strip().strip('"').strip("'")
                    await log_agent(job_id, "AUDIO_INGEST", f"auto-titled episode: '{detected_title}'")
            except Exception as e:
                log.warning(f"auto title generation failed: {e}")

        await emit(job_id, {"type": "milestone", "step": "transcript", "chars": len(transcript)})

        # Parallel: TopicMiner (Gemini) + QuoteHunter (Groq) + SocialCopy (Gemini)
        transcript_slice = transcript[:8000]

        async def topic_miner():
            await log_agent(job_id, "TOPIC_MINER", "extracting key topics via gemini (fallback: groq)...")
            prompt = (
                "Extract the key topics from this podcast transcript. "
                "Return STRICT JSON array of 5 objects with fields: "
                '{"topic": "short 2-5 word title", "summary": "one-sentence explanation", "importance": 1-10}. '
                "No prose, JSON only.\n\nTranscript:\n" + transcript_slice
            )
            try:
                raw = await smart_chat(prompt, system="You output ONLY valid JSON.", max_tokens=800, prefer="gemini", json_mode=True)
                topics_raw = await parse_json_response(raw)
                # Handle both array response and {"topics":[...]} shape
                if isinstance(topics_raw, dict):
                    topics = topics_raw.get("topics") or list(topics_raw.values())[0] if topics_raw else []
                else:
                    topics = topics_raw or []
            except Exception as e:
                await log_agent(job_id, "TOPIC_MINER", f"error: {e}", level="error")
                topics = []
            await log_agent(job_id, "TOPIC_MINER", f"found {len(topics)} topics")
            return topics

        async def quote_hunter():
            await log_agent(job_id, "QUOTE_HUNTER", "scanning for viral quotes via groq...")
            prompt = (
                "Find the 5 most shareable, tweet-worthy quotes from this transcript. "
                "Return STRICT JSON array of objects with fields: "
                '{"quote": "the exact or lightly cleaned quote", "speaker": "best guess or Unknown", "punch": "why it hits (max 10 words)"}. '
                "No prose, JSON only.\n\nTranscript:\n" + transcript_slice
            )
            try:
                raw = await groq_chat(prompt, system="You output ONLY valid JSON.", max_tokens=900, json_mode=True)
                quotes_raw = await parse_json_response(raw)
                if isinstance(quotes_raw, dict):
                    quotes = quotes_raw.get("quotes") or (list(quotes_raw.values())[0] if quotes_raw else [])
                else:
                    quotes = quotes_raw or []
            except Exception as e:
                await log_agent(job_id, "QUOTE_HUNTER", f"error: {e}", level="error")
                quotes = []
            await log_agent(job_id, "QUOTE_HUNTER", f"harvested {len(quotes)} quotes")
            return quotes

        async def social_copy():
            await log_agent(job_id, "SOCIAL_COPY", "generating captions for twitter, linkedin, instagram...")
            prompt = (
                "Given this podcast transcript, write social media copy. "
                "Return STRICT JSON with keys 'twitter', 'linkedin', 'instagram'. "
                "Twitter: max 260 chars, punchy, includes 1-2 hashtags. "
                "LinkedIn: 3-4 short paragraphs, professional but bold, ends with a question. "
                "Instagram: hook line + 4 bullet takeaways + 5 relevant hashtags. "
                "JSON only.\n\nTranscript:\n" + transcript_slice
            )
            try:
                raw = await smart_chat(prompt, system="You output ONLY valid JSON.", max_tokens=1200, prefer="gemini", json_mode=True)
                copy_raw = await parse_json_response(raw) or {}
                copy = {}
                for k in ("twitter", "linkedin", "instagram"):
                    v = copy_raw.get(k)
                    if isinstance(v, str):
                        copy[k] = v
                    elif isinstance(v, dict):
                        parts = []
                        if v.get("hook"):
                            parts.append(str(v["hook"]))
                        if isinstance(v.get("bullets"), list):
                            parts.append("\n".join(f"• {b}" for b in v["bullets"]))
                        if isinstance(v.get("hashtags"), list):
                            parts.append(" ".join(v["hashtags"]))
                        if not parts:
                            parts.append(json.dumps(v, ensure_ascii=False))
                        copy[k] = "\n\n".join(parts)
                    elif isinstance(v, list):
                        copy[k] = "\n".join(str(x) for x in v)
            except Exception as e:
                await log_agent(job_id, "SOCIAL_COPY", f"error: {e}", level="error")
                copy = {}
            await log_agent(job_id, "SOCIAL_COPY", f"generated {len(copy)} platform captions")
            return copy

        topics, quotes, social = await asyncio.gather(topic_miner(), quote_hunter(), social_copy())

        # ShowNotes agent depends on topics + quotes
        await log_agent(job_id, "SHOW_NOTES", "composing SEO markdown notes via groq...")
        top_json = json.dumps(topics, ensure_ascii=False)[:2000]
        quote_json = json.dumps(quotes, ensure_ascii=False)[:2000]
        show_notes_prompt = (
            "Write SEO-optimized podcast show notes in Markdown. "
            "Structure: # Title, > 1-sentence hook, ## Overview (2 paragraphs), "
            "## Key Topics (bullet list from topics), ## Best Quotes (blockquotes from quotes), "
            "## Chapters (mock timestamped list of 5 chapters starting 00:00), "
            "## Resources (3 plausible resources). Keep it under 500 words. Return ONLY markdown.\n\n"
            f"Episode title: {detected_title or 'Untitled Episode'}\n"
            f"Topics JSON: {top_json}\nQuotes JSON: {quote_json}"
        )
        try:
            show_notes = await groq_chat(show_notes_prompt, system="You write publish-ready Markdown.", max_tokens=1400)
        except Exception as e:
            await log_agent(job_id, "SHOW_NOTES", f"error: {e}", level="error")
            show_notes = "# Show Notes\n\nGeneration failed."
        await log_agent(job_id, "SHOW_NOTES", f"produced {len(show_notes)} chars of markdown")

        await log_agent(job_id, "ORCHESTRATOR", "<<< pipeline complete. sealing artifact.")

        final_title = detected_title or title or "Untitled Episode"

        result = {
            "title": final_title,
            "host": detected_host,
            "guest": detected_guest,
            "transcript": transcript,
            "transcript_preview": transcript[:1500],
            "transcript_length": len(transcript),
            "topics": topics,
            "quotes": quotes,
            "show_notes_md": show_notes,
            "social": social,
        }

        await episodes_col.update_one(
            {"id": job_id},
            {
                "$set": {
                    "title": final_title,
                    "status": "complete",
                    "result": result,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )
        await emit(job_id, {"type": "done", "job_id": job_id})
    except Exception as e:
        log.exception("pipeline crashed")
        await log_agent(job_id, "ORCHESTRATOR", f"FATAL: {e}", level="error")
        await episodes_col.update_one(
            {"id": job_id},
            {"$set": {"status": "error", "error": str(e)}},
        )
        await emit(job_id, {"type": "error", "message": str(e)})


# -------------------- FastAPI app --------------------
app = FastAPI(title="PulseVault AI")
api = APIRouter(prefix="/api")


class TitleUpdate(BaseModel):
    title: str


@api.patch("/episode/{job_id}/title")
async def update_episode_title(job_id: str, req: TitleUpdate):
    doc = await episodes_col.find_one({"id": job_id})
    if not doc:
        raise HTTPException(404, "episode not found")
    new_title = req.title.strip()
    if not new_title:
        raise HTTPException(400, "title cannot be empty")
    
    update_fields = {"title": new_title}
    if doc.get("result"):
        update_fields["result.title"] = new_title
        
    await episodes_col.update_one({"id": job_id}, {"$set": update_fields})
    return {"status": "ok", "title": new_title}


@api.get("/")
async def root():
    return {"service": "pulsevault-ai", "status": "online"}


@api.get("/demos")
async def demos():
    return [
        {"demo_id": k, "title": v["title"], "host": v["host"], "guest": v["guest"], "url": v["url"]}
        for k, v in DEMO_EPISODES.items()
    ]


@api.post("/episode/ingest")
async def ingest(req: IngestRequest):
    job_id = str(uuid.uuid4())
    doc = {
        "id": job_id,
        "url": req.url,
        "title": req.title,
        "demo_id": req.demo_id,
        "status": "running",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "result": None,
    }
    await episodes_col.insert_one(doc)
    job_queues[job_id] = asyncio.Queue()
    # kick off background task
    asyncio.create_task(run_pipeline(job_id, req.url, req.demo_id, req.title))
    return {"job_id": job_id}


@api.get("/episode/{job_id}")
async def get_episode(job_id: str):
    doc = await episodes_col.find_one({"id": job_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "not found")
    return doc


@api.get("/vault")
async def vault():
    docs = await episodes_col.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    # trim result on list
    for d in docs:
        if d.get("result"):
            d["result"] = {
                "title": d["result"].get("title"),
                "host": d["result"].get("host"),
                "guest": d["result"].get("guest"),
                "topics_count": len(d["result"].get("topics") or []),
                "quotes_count": len(d["result"].get("quotes") or []),
            }
    return docs


@app.websocket("/api/agents/stream/{job_id}")
async def agent_stream(websocket: WebSocket, job_id: str):
    await websocket.accept()
    # Replay past events first
    past = await events_col.find({"job_id": job_id}, {"_id": 0, "job_id": 0}).sort("ts", 1).to_list(500)
    for ev in past:
        await websocket.send_text(json.dumps(ev))
    # Live stream
    q = job_queues.get(job_id)
    if q is None:
        # job finished before ws connected; send done and close
        doc = await episodes_col.find_one({"id": job_id}, {"_id": 0})
        if doc and doc.get("status") == "complete":
            await websocket.send_text(json.dumps({"type": "done", "job_id": job_id}))
        await websocket.close()
        return
    try:
        while True:
            event = await q.get()
            await websocket.send_text(json.dumps(event))
            if event.get("type") in ("done", "error"):
                break
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def _shutdown():
    client.close()
