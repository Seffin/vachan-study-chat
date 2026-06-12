# 🧠 Vachan Study — Backend API & Architecture Docs

*Note: This repository recently underwent a massive architectural overhaul. We migrated from local FAISS Vector Stores to **MongoDB Atlas Vector Search**, and upgraded from native Browser Speech to **Google gTTS (Base64 Tunnelling)**.* 

**For a complete, full-stack overview of the entire project structure, please see [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md).**

---

## 🐍 Backend Technology Stack

The backend is built with Python 3.12 and optimized for **Vercel Serverless Functions**.

- **Framework:** FastAPI (ASGI framework, auto-generating Swagger UI at `/docs`)
- **LLM Intelligence:** Google Gemini (`gemini-2.5-flash` for transcription, `text-embedding-004` for RAG, `gemini-1.5-flash` for fallback generation)
- **Database:** MongoDB Atlas (M0 Free Tier)
- **Vector Search:** Atlas Vector Search (HNSW indices with 768-dimensional Matryoshka embeddings)
- **Re-Ranking:** HuggingFace `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **Voice STT/TTS:** `gTTS` (Google Text-to-Speech), `langdetect`, and `ffmpeg`/Gemini multimodal.

---

## 🌐 Core API Routes

### 1. `POST /api/chat` (Server-Sent Events)
The main conversational intelligence loop. Receives the user's message, detects language, retrieves scripture context via Hybrid Search, and streams back AI-generated answers and dynamically extracted UI Suggestion Chips.
- **Input Payload:** `{"book": "GEN", "message": "...", "history": ["..."]}`
- **Output:** `text/event-stream` returning iterative text chunks, followed by a final JSON payload containing `suggested_questions` and `reference`.

### 2. `POST /api/transcribe`
Receives raw `audio/webm` BLOB data from the frontend microphone, proxies it to Google Gemini Flash for multimodal voice-to-text extraction, and returns accurate native-language text.

### 3. `POST /api/tts` (Base64 Audio Tunnelling)
Accepts an AI-generated text string. Automatically detects the language (e.g., `ml` vs `en`), requests an MP3 stream from Google TTS, and encodes the raw binary to a Base64 JSON string.
*Why Base64?* It completely eliminates browser Blob corruption and chunking failures common in strict environments (like iOS Safari).

### 4. `GET /api/history/{book}` & `DELETE /api/history/{book}`
Fetches or purges the user's conversation history for the current session from the MongoDB `chat_history` collection.

---

## 💾 MongoDB Database Schema

### `qa_dataset` (RAG Knowledge Base)
```json
{
  "_id": "ObjectId",
  "book": "GEN",
  "chapter": 1,
  "verse": 1,
  "question": "What did God create in the beginning?",
  "answer": "God created the heavens and the earth.",
  "lang_code": "en",
  "embedding": [0.012, -0.045, ...] // 768 dimensions
}
```

### `chat_history` (Conversation Logs)
```json
{
  "_id": "ObjectId",
  "session_id": "default_user_session",
  "book": "GEN",
  "timestamp": "2026-06-12T14:00:00Z",
  "messages": [
    {"role": "user", "content": "Hello"},
    {"role": "ai", "content": "How can I help you study?"}
  ]
}
```

---

## 🚀 Deployment (Vercel)

The backend is deployed automatically via Vercel using the `vercel.json` manifest.
- **Environment Variables:** You MUST configure your `GEMINI_API_KEY` and `MONGODB_URI` in the Vercel Dashboard.
- **Limitations:** Vercel functions are read-only. We no longer write to the filesystem (e.g., legacy FAISS `static_data/vectorstores`), everything is handled entirely in memory (`io.BytesIO`) or piped directly to MongoDB Atlas.
