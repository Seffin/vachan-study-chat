# Vachan Study

A full-stack, multilingual AI Bible study chatbot with JWT authentication and strict single-session enforcement. Uses hybrid RAG (MongoDB Atlas Vector Search + BM25 keyword search) over the unfoldingWord dataset to deliver scholarly, contextual answers with real-time SSE streaming.

## Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS v4, Framer Motion |
| Backend | FastAPI, Python 3.12 |
| Database | MongoDB Atlas (Vector Search + collections) |
| AI/LLM | Google Gemini (2.5-flash, text-embedding-004), HuggingFace Cross-Encoder |
| Voice | gTTS (TTS), Gemini multimodal (STT) |

## Quick Start

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
# Copy .env.example → .env, set MONGO_URI and GEMINI_API_KEYS
python api/index.py          # http://127.0.0.1:8000
```

### Frontend
```bash
npm install
# Copy .env.example → .env.local
npm run dev                  # http://localhost:3000
```

## Key API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root route (API info + links) |
| GET | `/api/health` | Health check with MongoDB ping |
| POST | `/api/auth/register` | User registration |
| POST | `/api/auth/login` | User login (returns JWT token and session ID) |
| POST | `/api/auth/logout` | User logout (invalidates session ID) |
| GET | `/api/auth/me` | Fetch currently logged-in user profile |
| POST | `/api/chat` | SSE streaming RAG chat (authenticated) |
| POST | `/api/transcribe` | Audio → text (Gemini) |
| POST | `/api/tts` | Text → Base64 MP3 (gTTS) |
| GET | `/api/scripture/{book}/{chapter}` | Bible text + cache (HTTP caching) |
| GET/DELETE | `/api/history/{book}` | Chat history (authenticated, per-user) |
| GET/POST | `/api/tokens` | Quota status / reset |
| GET | `/api/dataset/{book}` | Q&A dataset viewer |

## Project Structure

```
src/
  app/              Next.js routing & layout (Settings + Help modals)
  components/       Workspace, Navbar, StudyRoom, LoginPage
  data/             Offline scripture fallback
backend/
  api/index.py      FastAPI entry point (all endpoints consolidated)
  app/core/         Security (JWT, bcrypt, rate limiting), config
  db/               MongoDB connection, repositories, user_repository
  services/         RAG, translation, AI, key rotation, rate limiter
  schemas/          Pydantic request/response models
  scripts/          Vector migration, dataset setup, key management
  data/en_tq/       unfoldingWord TSV datasets
  static_data/      Precompiled JSON scriptures & CSV fallbacks
  requirements.txt          Vercel-safe deps (stripped, no heavy ML)
  requirements-local.txt    Full local dev deps (faiss, langchain, etc.)
  runtime.txt               Python 3.12 pinning for Vercel
docs/
  ARCHITECTURE.md   System design & data flow
  TDD_LOGIN_FEATURE.md  TDD strategy example
GITHUB_ISSUES.md    Vercel hosting audit & improvement tracker
```

## Offline Resilience

If the backend is unreachable, the frontend automatically falls back to a local simulator using `mockBible.ts` and `defaultAIResponse()` — no API keys required.

## Vercel Production Hardening

Deployed as Vercel Serverless Functions with the following production optimizations:

- **CORS lockdown**: Only the production frontend origin is allowed (not `*`)
- **IP rate limiting**: 30 req / 60 sec per IP on `/api/chat` (in-memory, resets per cold start)
- **SSE timeout guard**: 8s hard limit on Vercel Free Tier (30s locally) to prevent 504s
- **Startup diagnostics**: `MONGO_URI` presence check and MongoDB connection test on cold start
- **Health check**: `GET /api/health` with MongoDB `ping` for uptime monitoring
- **Global exception handler**: All unhandled errors return structured JSON (not raw HTML 500)
- **HTTP caching**: `Cache-Control` headers on scripture endpoints
- **Dual requirements files**: `requirements.txt` (Vercel-safe, stripped) vs `requirements-local.txt` (full dev)
- **Python 3.12**: Pinned via `runtime.txt`
- **Next.js optimizations**: `compress`, no source maps in prod, `reactCompiler`

## Frontend Features

- **Settings modal**: Theme switcher, API backend display, version info
- **Help & Guide modal**: Getting started, voice features, keyboard shortcuts
- **Q&A Dataset Viewer**: Browse the unfoldingWord translation questions per book

---

*For detailed architecture, see [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md).*  
*For TDD methodology, see [`docs/TDD_LOGIN_FEATURE.md`](./docs/TDD_LOGIN_FEATURE.md).*  
*For hosting improvements, see [`GITHUB_ISSUES.md`](./GITHUB_ISSUES.md).*
