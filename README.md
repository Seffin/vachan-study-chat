# Vachan Study

A full-stack, multilingual AI Bible study chatbot. Uses hybrid RAG (MongoDB Atlas Vector Search + BM25 keyword search) over the unfoldingWord dataset to deliver scholarly, contextual answers with real-time SSE streaming.

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
| POST | `/api/chat` | SSE streaming RAG chat |
| POST | `/api/transcribe` | Audio → text (Gemini) |
| POST | `/api/tts` | Text → Base64 MP3 (gTTS) |
| GET | `/api/scripture/{book}/{chapter}` | Bible text + cache |
| GET/DELETE | `/api/history/{book}` | Chat history |
| GET/POST | `/api/tokens` | Quota status / reset |

## Project Structure

```
src/
  app/              Next.js routing & layout
  components/       Workspace, Navbar, StudyRoom
  data/             Offline scripture fallback
backend/
  api/index.py      FastAPI entry point
  db/               MongoDB connection + repositories
  services/         RAG, translation, AI, key rotation, rate limiter
  scripts/          Vector migration, dataset setup, key management
  data/en_tq/       unfoldingWord TSV datasets
  static_data/      Precompiled JSON scriptures & CSV fallbacks
docs/
  ARCHITECTURE.md   System design & data flow
  TDD_LOGIN_FEATURE.md  TDD strategy example
```

## Offline Resilience

If the backend is unreachable, the frontend automatically falls back to a local simulator using `mockBible.ts` and `defaultAIResponse()` — no API keys required.

## Vercel Notes

Deployed as Vercel Serverless Functions. The filesystem is read-only; all state (tokens, vectors, history) lives in MongoDB Atlas or `/tmp`.

---

*For detailed architecture, see [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md).*  
*For TDD methodology, see [`docs/TDD_LOGIN_FEATURE.md`](./docs/TDD_LOGIN_FEATURE.md).*
