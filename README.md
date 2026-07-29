# PulseVault AI

**Autonomous Podcast Intelligence Studio.** Paste any podcast episode URL — ten collaborative
AI agents transcribe, mine topics, hunt viral quotes, cut clips, write show-notes, research
guests, map sentiment, spin up social copy, and pitch future guest ideas.

Built with **FastAPI + Groq (Whisper + Llama-3.3) + Gemini 2.0 + MongoDB + React + Tailwind**,
wrapped in a full **brutalist** design language.

---

## Quick start (Docker)

```bash
cp .env.example .env
# edit .env and set GEMINI_API_KEY + GROQ_API_KEY
docker-compose up --build
```

Then open:
- Frontend: <http://localhost:3000>
- Backend:  <http://localhost:8001>
- MCP:      <http://localhost:8765/health>

## Quick start (local dev)

```bash
# backend
cd backend
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# frontend (new terminal)
cd frontend
yarn install
yarn start

# mcp-chrome (optional, new terminal)
cd mcp-chrome
node server.js
```

## Environment variables

| var                  | required | default                    | notes                     |
|----------------------|----------|----------------------------|---------------------------|
| `GEMINI_API_KEY`     | yes      | —                          | Google AI Studio          |
| `GROQ_API_KEY`       | yes      | —                          | Groq Console              |
| `MONGO_URL`          | yes      | `mongodb://mongo:27017`    |                           |
| `DB_NAME`            | yes      | `pulsevault`               |                           |
| `GROQ_LLM_MODEL`     | no       | `llama-3.3-70b-versatile`  |                           |
| `GEMINI_MODEL`       | no       | `gemini-2.0-flash`         |                           |

## API

- `POST /api/episode/ingest`  `{ url, demo_id?, title? }` → `{ job_id }`
- `WS   /api/agents/stream/{job_id}` → live agent event stream
- `GET  /api/episode/{id}` → full episode + result
- `GET  /api/vault` → recent episodes list
- `GET  /api/demos` → 2 preloaded demo episodes

## Preloaded demos

Two demo episodes ship in-box with canned transcripts so you can experience the swarm without
needing a hosted audio URL:

- `demo-huberman` — "The Science of Focus & Deep Work"
- `demo-lex` — "Building Machines That Think — AGI, Alignment & the Next Decade"

## Roadmap

**Phase 1 (shipped):**
- Brutalist landing + URL ingest + 2 preloaded demos
- Live agent terminal (WebSocket)
- Orchestrator + Audio Ingest + Topic Miner + Quote Hunter + Show Notes + Social Copy
- Episode dashboard with topics / quotes / show-notes / social tabs
- Vault (episode history grid)

**Phase 2:**
- Faster-whisper local transcription option
- Clip Cutter with waveform preview + download
- Sentiment Mapper with emotional arc chart
- Guest Researcher via real Chrome MCP
- Guest Suggestor with contact hints

