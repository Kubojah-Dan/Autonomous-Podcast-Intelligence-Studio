"""PulseVault AI — Autonomous Podcast Intelligence Studio backend v2."""
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
from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import PlainTextResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from groq import Groq

from services.ingest_router import UniversalIngestRouter
from services.voice_agent import VoiceAgent

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
ingest_router = UniversalIngestRouter()
voice_agent = VoiceAgent()

# In-memory pub/sub for WebSocket streaming per job
job_queues: Dict[str, "asyncio.Queue[dict]"] = {}

# Media directory setup
MEDIA_DIR = ROOT_DIR / "media"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)


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


class TTSSynthesizeRequest(BaseModel):
    text: str
    profile: Optional[str] = "narrator"
    artifact_id: Optional[str] = None


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


# -------------------- Agent pipeline v2 --------------------
async def run_pipeline(job_id: str, url: str, demo_id: Optional[str], title: Optional[str]):
    try:
        await log_agent(job_id, "ORCHESTRATOR", ">>> booting 11-agent swarm for job " + job_id[:8])
        await log_agent(job_id, "ORCHESTRATOR", "target url = " + url)

        # 1. AUDIO_INGEST Agent (Universal Router)
        await log_agent(job_id, "AUDIO_INGEST", "resolving platform & acquiring stream via Universal Router...")
        ingest_res = await ingest_router.resolve(url, custom_title=title)
        
        await log_agent(job_id, "AUDIO_INGEST", f"resolved source platform: {ingest_res.source_platform} [kind: {ingest_res.kind}]")
        if ingest_res.drm_notice:
            await log_agent(job_id, "AUDIO_INGEST", ingest_res.drm_notice, level="warn")

        transcript = None
        detected_title = ingest_res.title or title
        detected_host = ingest_res.host
        detected_guest = ingest_res.guest

        if demo_id and demo_id in DEMO_EPISODES:
            demo = DEMO_EPISODES[demo_id]
            transcript = demo["transcript"]
            detected_title = detected_title or demo["title"]
            detected_host = demo["host"]
            detected_guest = demo["guest"]
            await log_agent(job_id, "AUDIO_INGEST", f"loaded demo transcript '{demo['title']}' [{len(transcript)} chars]")
        elif ingest_res.audio_path and os.path.exists(ingest_res.audio_path):
            try:
                await log_agent(job_id, "AUDIO_INGEST", "transcribing local audio file with Whisper-large-v3...")
                with open(ingest_res.audio_path, "rb") as f:
                    audio_bytes = f.read()
                def _transcribe_file():
                    r = groq_client.audio.transcriptions.create(
                        model="whisper-large-v3",
                        file=(Path(ingest_res.audio_path).name, audio_bytes),
                        temperature=0.0,
                    )
                    return r.text
                transcript = await asyncio.to_thread(_transcribe_file)
                await log_agent(job_id, "AUDIO_INGEST", f"transcribed file [{len(transcript)} chars]")
            except Exception as e:
                await log_agent(job_id, "AUDIO_INGEST", f"file transcription failed: {e}", level="warn")
        elif ingest_res.audio_url:
            try:
                await log_agent(job_id, "AUDIO_INGEST", "calling groq whisper-large-v3 on resolved url...")
                transcript = await asyncio.wait_for(groq_transcribe_url(ingest_res.audio_url), timeout=120)
                await log_agent(job_id, "AUDIO_INGEST", f"transcribed [{len(transcript)} chars]")
            except Exception as e:
                await log_agent(job_id, "AUDIO_INGEST", f"transcription failed: {e}", level="warn")

        if not transcript:
            await log_agent(job_id, "AUDIO_INGEST", "falling back to metadata mode")
            transcript = (
                f"[Episode metadata for: {detected_title or url}]\n"
                f"Platform: {ingest_res.source_platform or 'Universal Ingest'}\n"
                "This transcript was constructed for metadata analysis. For full audio transcription, "
                "upload an MP3/WAV file directly or use a demo episode."
            )

        if not detected_title and transcript and len(transcript) > 50 and not transcript.startswith("[Episode metadata"):
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

        # Phase 1 Parallel Swarm Execution (TopicMiner + QuoteHunter + SocialCopy + Chapters + FactCheck + Sentiment)
        transcript_slice = transcript[:9000]

        async def topic_miner():
            await log_agent(job_id, "TOPIC_MINER", "extracting key topics via gemini...")
            prompt = (
                "Extract 5 key topics from this transcript. Return STRICT JSON array of objects: "
                '{"topic": "2-5 word title", "summary": "one sentence explanation", "importance": 1-10}. JSON only.\n\n' + transcript_slice
            )
            try:
                raw = await smart_chat(prompt, system="You output ONLY valid JSON.", max_tokens=800, prefer="gemini", json_mode=True)
                res = await parse_json_response(raw)
                topics = res if isinstance(res, list) else (res.get("topics") if isinstance(res, dict) else [])
            except Exception as e:
                await log_agent(job_id, "TOPIC_MINER", f"error: {e}", level="error")
                topics = []
            await log_agent(job_id, "TOPIC_MINER", f"found {len(topics)} topics")
            return topics or []

        async def quote_hunter():
            await log_agent(job_id, "QUOTE_HUNTER", "scanning for viral quotes via groq...")
            prompt = (
                "Find 5 tweet-worthy quotes from this transcript. Return STRICT JSON array of objects: "
                '{"quote": "exact or lightly cleaned quote", "speaker": "Host/Guest/Unknown", "punch": "why it hits (max 10 words)"}. JSON only.\n\n' + transcript_slice
            )
            try:
                raw = await groq_chat(prompt, system="You output ONLY valid JSON.", max_tokens=900, json_mode=True)
                res = await parse_json_response(raw)
                quotes = res if isinstance(res, list) else (res.get("quotes") if isinstance(res, dict) else [])
            except Exception as e:
                await log_agent(job_id, "QUOTE_HUNTER", f"error: {e}", level="error")
                quotes = []
            await log_agent(job_id, "QUOTE_HUNTER", f"harvested {len(quotes)} quotes")
            return quotes or []

        async def social_copy():
            await log_agent(job_id, "SOCIAL_COPY", "generating captions for twitter, linkedin, instagram...")
            prompt = (
                "Given this podcast transcript, write social media copy. Return STRICT JSON with keys 'twitter', 'linkedin', 'instagram'. "
                "Twitter: max 260 chars, punchy + hashtags. LinkedIn: 3 short paragraphs + question. Instagram: hook + 4 bullets + hashtags. JSON only.\n\n" + transcript_slice
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
                        copy[k] = "\n\n".join(str(val) for val in v.values() if val)
                    else:
                        copy[k] = str(v or "")
            except Exception as e:
                await log_agent(job_id, "SOCIAL_COPY", f"error: {e}", level="error")
                copy = {}
            await log_agent(job_id, "SOCIAL_COPY", f"generated {len(copy)} platform captions")
            return copy

        async def chapters_agent():
            await log_agent(job_id, "CHAPTERS_AGENT", "analyzing topic shifts & generating timestamped chapter markers...")
            prompt = (
                "Analyze transcript and create 5-7 chapter markers. Return STRICT JSON array of objects: "
                '{"timestamp": "MM:SS", "seconds": int, "title": "short chapter title", "summary": "one sentence"}. JSON only.\n\n' + transcript_slice
            )
            try:
                raw = await smart_chat(prompt, system="You output ONLY valid JSON.", max_tokens=800, prefer="gemini", json_mode=True)
                res = await parse_json_response(raw)
                chapters = res if isinstance(res, list) else (res.get("chapters") if isinstance(res, dict) else [])
            except Exception as e:
                await log_agent(job_id, "CHAPTERS_AGENT", f"error: {e}", level="error")
                chapters = []
            await log_agent(job_id, "CHAPTERS_AGENT", f"generated {len(chapters)} chapter markers")
            return chapters or []

        async def fact_check_agent():
            await log_agent(job_id, "FACT_CHECK_AGENT", "verifying factual claims & checking sources...")
            prompt = (
                "Extract 4 key factual claims made in transcript. Return STRICT JSON array of objects: "
                '{"claim": "statement made", "speaker": "Speaker", "verdict": "VERIFIED|NEEDS_CONTEXT|UNVERIFIED", "source": "reference or rationale"}. JSON only.\n\n' + transcript_slice
            )
            try:
                raw = await groq_chat(prompt, system="You output ONLY valid JSON.", max_tokens=800, json_mode=True)
                res = await parse_json_response(raw)
                claims = res if isinstance(res, list) else (res.get("claims") if isinstance(res, dict) else [])
            except Exception as e:
                await log_agent(job_id, "FACT_CHECK_AGENT", f"error: {e}", level="error")
                claims = []
            await log_agent(job_id, "FACT_CHECK_AGENT", f"verified {len(claims)} factual claims")
            return claims or []

        async def sentiment_mapper():
            await log_agent(job_id, "SENTIMENT_MAPPER", "mapping emotional arc timeline & viral peaks...")
            prompt = (
                "Map emotional arc over episode duration into 6 points. Return STRICT JSON array of objects: "
                '{"timestamp": "MM:SS", "sentiment_score": float -1.0 to 1.0, "intensity": 1-10, "emotion": "curiosity|excitement|debate|insight", "is_viral_peak": bool}. JSON only.\n\n' + transcript_slice
            )
            try:
                raw = await smart_chat(prompt, system="You output ONLY valid JSON.", max_tokens=800, prefer="gemini", json_mode=True)
                res = await parse_json_response(raw)
                arc = res if isinstance(res, list) else (res.get("arc") if isinstance(res, dict) else [])
            except Exception as e:
                await log_agent(job_id, "SENTIMENT_MAPPER", f"error: {e}", level="error")
                arc = []
            await log_agent(job_id, "SENTIMENT_MAPPER", f"mapped {len(arc)} emotional arc segments")
            return arc or []

        # Run 6 agents in parallel
        topics, quotes, social, chapters, claims, sentiment = await asyncio.gather(
            topic_miner(), quote_hunter(), social_copy(), chapters_agent(), fact_check_agent(), sentiment_mapper()
        )

        # Phase 2 Agents: ClipCutter + GuestResearcher + ShowNotes
        async def clip_cutter():
            await log_agent(job_id, "CLIP_CUTTER", "generating 9:16 vertical video specs & subtitle configs...")
            prompt = (
                "Select top 3 viral clip candidates from quotes & sentiment. Return STRICT JSON array of objects: "
                '{"title": "clip title", "start": "01:15", "end": "01:45", "duration_sec": 30, "hook": "screen hook subtitle", "viral_score": 95, "layout": "9:16 vertical"}. JSON only.\n\n'
                f"Quotes: {json.dumps(quotes[:3])}\nTranscript slice: {transcript_slice[:2000]}"
            )
            try:
                raw = await groq_chat(prompt, system="You output ONLY valid JSON.", max_tokens=800, json_mode=True)
                res = await parse_json_response(raw)
                clips = res if isinstance(res, list) else (res.get("clips") if isinstance(res, dict) else [])
            except Exception as e:
                await log_agent(job_id, "CLIP_CUTTER", f"error: {e}", level="error")
                clips = []
            await log_agent(job_id, "CLIP_CUTTER", f"produced {len(clips)} vertical clip specs")
            return clips or []

        async def guest_researcher():
            await log_agent(job_id, "GUEST_RESEARCH", "building guest dossier & contact enrichment...")
            guest_name = detected_guest or "Guest Expert"
            prompt = (
                f"Provide a brief profile & outreach email for guest '{guest_name}' based on transcript. "
                "Return STRICT JSON object with keys: 'name', 'bio', 'linkedin_url', 'contact_email_hint', 'talking_points' (list of 3), 'pitch_email_draft'. JSON only.\n\n" + transcript_slice[:3000]
            )
            try:
                raw = await smart_chat(prompt, system="You output ONLY valid JSON.", max_tokens=800, prefer="gemini", json_mode=True)
                dossier = await parse_json_response(raw) or {}
            except Exception as e:
                await log_agent(job_id, "GUEST_RESEARCH", f"error: {e}", level="error")
                dossier = {}
            await log_agent(job_id, "GUEST_RESEARCH", f"compiled dossier for {guest_name}")
            return dossier

        async def show_notes():
            await log_agent(job_id, "SHOW_NOTES", "composing SEO markdown notes via groq...")
            top_json = json.dumps(topics, ensure_ascii=False)[:1500]
            quote_json = json.dumps(quotes, ensure_ascii=False)[:1500]
            show_notes_prompt = (
                "Write SEO-optimized podcast show notes in Markdown. "
                "Structure: # Title, > 1-sentence hook, ## Overview (2 paragraphs), "
                "## Key Topics (bullet list), ## Best Quotes (blockquotes), "
                "## Chapters, ## Fact-Check Highlights, ## Resources. Keep under 500 words. ONLY markdown.\n\n"
                f"Episode title: {detected_title or 'Untitled Episode'}\n"
                f"Topics: {top_json}\nQuotes: {quote_json}"
            )
            try:
                notes = await groq_chat(show_notes_prompt, system="You write publish-ready Markdown.", max_tokens=1400)
            except Exception as e:
                await log_agent(job_id, "SHOW_NOTES", f"error: {e}", level="error")
                notes = "# Show Notes\n\nGeneration failed."
            await log_agent(job_id, "SHOW_NOTES", f"produced {len(notes)} chars of markdown")
            return notes

        clips, guest_dossier, show_notes_md = await asyncio.gather(clip_cutter(), guest_researcher(), show_notes())

        # Phase 3 Agent: VOICE_AGENT (Synthesize audio for overview summary & key quote)
        await log_agent(job_id, "VOICE_AGENT", "synthesizing voice audio narrations for overview & top quote...")
        overview_audio = None
        quote_audio = None
        try:
            summary_text = f"Welcome to {detected_title or 'this episode'}. Here is your podcast briefing. " + (topics[0]["summary"] if topics else "")
            ov_res = await voice_agent.synthesize(summary_text, profile="narrator", artifact_id=f"{job_id}_overview")
            overview_audio = ov_res["audio_url"]
            if quotes:
                top_q = quotes[0].get("quote") or ""
                q_res = await voice_agent.synthesize(top_q, profile="dramatic", artifact_id=f"{job_id}_quote")
                quote_audio = q_res["audio_url"]
            await log_agent(job_id, "VOICE_AGENT", "voice audio synthesis complete")
        except Exception as e:
            await log_agent(job_id, "VOICE_AGENT", f"voice synthesis warning: {e}", level="warn")

        await log_agent(job_id, "ORCHESTRATOR", "<<< 11-agent pipeline complete. sealing artifact.")

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
            "show_notes_md": show_notes_md,
            "social": social,
            "chapters": chapters,
            "claims": claims,
            "sentiment": sentiment,
            "clips": clips,
            "guest_dossier": guest_dossier,
            "overview_audio": overview_audio,
            "quote_audio": quote_audio,
            "platform": ingest_res.source_platform or "universal",
            "drm_notice": ingest_res.drm_notice,
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
app = FastAPI(title="PulseVault AI v2")
api = APIRouter(prefix="/api")

# Serve media static files (for TTS MP3 files)
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR.parent)), name="media")


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
    return {"service": "pulsevault-ai-v2", "status": "online"}


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
    asyncio.create_task(run_pipeline(job_id, req.url, req.demo_id, req.title))
    return {"job_id": job_id}


@api.post("/episode/upload")
async def upload_audio_file(file: UploadFile = File(...), title: Optional[str] = Form(None)):
    """Drag-and-drop local audio file ingest."""
    file_id = str(uuid.uuid4())[:8]
    dest_path = MEDIA_DIR / f"upload_{file_id}_{file.filename}"
    with open(dest_path, "wb") as f:
        content = await file.read()
        f.write(content)

    upload_url = f"upload://{dest_path}"
    job_id = str(uuid.uuid4())
    doc = {
        "id": job_id,
        "url": upload_url,
        "title": title or file.filename.replace("_", " ").title(),
        "status": "running",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "result": None,
    }
    await episodes_col.insert_one(doc)
    job_queues[job_id] = asyncio.Queue()
    asyncio.create_task(run_pipeline(job_id, upload_url, None, title))
    return {"job_id": job_id, "filename": file.filename}


@api.post("/tts/synthesize")
async def tts_synthesize(req: TTSSynthesizeRequest):
    """Synthesize text artifact to audio."""
    try:
        res = await voice_agent.synthesize(text=req.text, profile=req.profile or "narrator", artifact_id=req.artifact_id)
        return res
    except Exception as e:
        raise HTTPException(500, f"TTS synthesis failed: {e}")


@api.post("/tts/{artifact_id}")
async def tts_synthesize_path(artifact_id: str, req: TTSSynthesizeRequest):
    try:
        res = await voice_agent.synthesize(text=req.text, profile=req.profile or "narrator", artifact_id=artifact_id)
        return res
    except Exception as e:
        raise HTTPException(500, f"TTS synthesis failed: {e}")


@api.get("/episode/{job_id}")
async def get_episode(job_id: str):
    doc = await episodes_col.find_one({"id": job_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "not found")
    return doc


@api.get("/episode/{job_id}/chapters.txt")
async def download_chapters(job_id: str):
    doc = await episodes_col.find_one({"id": job_id}, {"_id": 0})
    if not doc or not doc.get("result"):
        raise HTTPException(404, "chapters not found")
    chapters = doc["result"].get("chapters") or []
    lines = ["# Podcast Chapter Markers (.chapters.txt)", ""]
    for ch in chapters:
        ts = ch.get("timestamp", "00:00")
        t = ch.get("title", "Chapter")
        s = ch.get("summary", "")
        lines.append(f"{ts} {t} - {s}".strip())
    content = "\n".join(lines)
    return PlainTextResponse(content, media_type="text/plain", headers={"Content-Disposition": f'attachment; filename="chapters_{job_id[:8]}.txt"'})


@api.get("/vault")
async def vault():
    docs = await episodes_col.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    for d in docs:
        if d.get("result"):
            d["result"] = {
                "title": d["result"].get("title"),
                "host": d["result"].get("host"),
                "guest": d["result"].get("guest"),
                "topics_count": len(d["result"].get("topics") or []),
                "quotes_count": len(d["result"].get("quotes") or []),
                "chapters_count": len(d["result"].get("chapters") or []),
            }
    return docs


@app.websocket("/api/agents/stream/{job_id}")
async def agent_stream(websocket: WebSocket, job_id: str):
    await websocket.accept()
    past = await events_col.find({"job_id": job_id}, {"_id": 0, "job_id": 0}).sort("ts", 1).to_list(500)
    for ev in past:
        await websocket.send_text(json.dumps(ev))
    q = job_queues.get(job_id)
    if q is None:
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
