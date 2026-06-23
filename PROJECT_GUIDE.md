# Vachan Study — Project Guide

> **One-stop documentation for understanding, extending, and deploying the Vachan Study Bible Chatbot.**
> For AI models: read this file before writing any code. For humans: use this as the single source of truth.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Tech Stack](#3-tech-stack)
4. [Directory Structure](#4-directory-structure)
5. [File-by-File Guide](#5-file-by-file-guide)
6. [Data Flow: The RAG Pipeline](#6-data-flow-the-rag-pipeline)
7. [Authentication Flow](#7-authentication-flow)
8. [API Reference](#8-api-reference)
9. [Database Schema](#9-database-schema)
10. [Environment Variables](#10-environment-variables)
11. [Deployment Guide](#11-deployment-guide)
12. [Common Issues & Fixes](#12-common-issues--fixes)
13. [How to Extend](#13-how-to-extend)
14. [Glossary](#14-glossary)

---

## 1. Executive Summary

**Vachan Study** is a full-stack, multilingual AI Bible study chatbot. It uses a **Retrieval-Augmented Generation (RAG)** pipeline grounded in the **unfoldingWord Translation Questions (TQ)** dataset (~18,000 Q&A pairs) to deliver scholarly, contextually accurate answers.

**Key Differentiators:**
- **Hybrid Search:** Combines semantic (vector) + lexical (BM25) search in MongoDB Atlas
- **Multilingual:** Auto-detects user language, translates queries, searches, then translates answers back
- **Voice-First:** Speech-to-text via Gemini, text-to-speech via gTTS
- **Offline Resilience:** Falls back to local mock data when the backend is unreachable
- **Single-Session Auth:** JWT-based with bcrypt, one active session per user, login audit logging

**Deployed on:** Vercel (frontend + backend as separate projects) + MongoDB Atlas

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              USER                                        │
│                    (Browser / Mobile / Voice)                            │
└──────────────────────────────────┬────────────────────────────────────────┘
                                   │ HTTPS
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Vercel)                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │ Study Room   │  │ Workspace    │  │ Login/Notes │                  │
│  │ (book grid)  │  │ (chat +      │  │ (auth)      │                  │
│  │              │  │  scripture)   │  │             │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
│                                                                          │
│  Next.js 16 + React 19 + TypeScript + Tailwind CSS + Framer Motion      │
│  URL: https://vachan-study-chat-snpm.vercel.app                         │
└──────────────────────────────────┬────────────────────────────────────────┘
                                   │ API calls (JSON + SSE + multipart)
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (Vercel)                                 │
│  ┌────────────────────────────────────────────────────────────┐          │
│  │  FastAPI Python Serverless Function                        │          │
│  │  Entry point: backend/api/index.py                         │          │
│  │  URL: https://vachan-study-chat.vercel.app                 │          │
│  │                                                            │          │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐          │          │
│  │  │ Auth       │  │ Chat (RAG) │  │ Scripture  │          │          │
│  │  │ (JWT)      │  │ (SSE)      │  │ (cached)   │          │          │
│  │  └────────────┘  └────────────┘  └────────────┘          │          │
│  └────────────────────────────────────────────────────────────┘          │
└──────────────────────────────────┬────────────────────────────────────────┘
                                   │ MongoDB Protocol (TLS)
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         DATABASE (MongoDB Atlas)                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │
│  │ users   │  │qa_dataset│  │chat_hist│  │api_keys │  │metrics  │       │
│  │ (auth)  │  │ (RAG)   │  │(sessions│  │(rotation│  │ (usage) │       │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘       │
│                                                                          │
│  Search: vector_index (semantic) + text_index (BM25)                     │
└─────────────────────────────────────────────────────────────────────────┘
```

**Two Separate Vercel Projects:**
- **Frontend:** `vachan-study-chat-snpm.vercel.app` (Next.js)
- **Backend:** `vachan-study-chat.vercel.app` (FastAPI Python serverless)

They communicate via HTTPS. The backend is NOT embedded in the frontend project.

---

## 3. Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Next.js 16, React 19, TypeScript | SPA with file-based routing |
| **Styling** | Tailwind CSS v4, Framer Motion | Animations, dark/light theme |
| **Icons** | Lucide React | Consistent iconography |
| **Backend** | Python 3.12, FastAPI | Async API framework |
| **Database** | MongoDB Atlas (M0 Free Tier) | Document store + vector search |
| **ORM/ODM** | Motor (async), PyMongo (sync) | MongoDB drivers |
| **AI/LLM** | Google Gemini 2.5 Flash | Generation, transcription |
| **Embeddings** | `text-embedding-004` (Gemini) | 768-dim Matryoshka vectors |
| **Re-ranking** | HuggingFace `cross-encoder/ms-marco-MiniLM-L-6-v2` | Score ranking |
| **Voice STT** | Gemini multimodal | Speech-to-text |
| **Voice TTS** | gTTS (Google Text-to-Speech) | Text-to-speech MP3 |
| **Auth** | PyJWT + bcrypt | JWT tokens, password hashing |
| **Deployment** | Vercel (serverless) | Frontend + backend functions |
| **Data Source** | unfoldingWord TQ TSV | ~18,000 Q&A pairs per book |

**What we DON'T use:**
- `faiss-cpu` — replaced by MongoDB Atlas Vector Search
- `langchain` — direct Gemini SDK calls instead
- `openai` — Gemini is the sole provider
- Redis — MongoDB handles state across instances

---

## 4. Directory Structure

```text
Logos Bible Study Chatbot/
│
├── .antigravity/                  # gStack IDE rules (ignore)
│
├── docs/                          # Architecture & TDD docs
│   ├── ARCHITECTURE.md
│   └── TDD_LOGIN_FEATURE.md
│
├── public/                        # Static assets (images, favicon)
│
├── src/                           # Next.js Frontend (TypeScript)
│   ├── app/
│   │   ├── layout.tsx             # Root layout, metadata, fonts
│   │   ├── page.tsx               # Main page: auth, views, modals
│   │   ├── globals.css            # Tailwind + custom CSS
│   │   └── favicon.ico
│   ├── components/
│   │   ├── Workspace.tsx          # 3-pane layout: chat, scripture, nav
│   │   ├── Navbar.tsx             # Top bar: views, theme, user menu
│   │   ├── StudyRoom.tsx          # Landing: 66-book grid
│   │   ├── LoginPage.tsx          # Auth: login + register
│   │   └── MermaidDiagram.tsx     # Mermaid.js diagram renderer
│   ├── data/
│   │   └── mockBible.ts           # Offline scripture fallback + book list
│   └── __tests__/
│       └── LoginForm.test.tsx     # Jest + React Testing Library
│
├── backend/                       # Python FastAPI
│   ├── api/
│   │   └── index.py               # ⭐ ENTRY POINT — all routes, SSE, auth
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py          # Pydantic settings (SECRET_KEY, etc.)
│   │   │   └── security.py        # JWT encode/decode, bcrypt, rate limiting
│   │   ├── routes/                # ⭐ NOT deployed to Vercel
│   │   │   ├── __init__.py
│   │   │   ├── auth.py            # Auth endpoints (clean architecture)
│   │   │   ├── chat.py            # Chat endpoint (clean architecture)
│   │   │   └── analytics.py       # Analytics endpoints
│   │   └── __init__.py
│   ├── config.py                  # Book mappings, disclaimers, thresholds
│   ├── db/
│   │   ├── mongodb.py             # Motor/PyMongo connection
│   │   ├── repositories.py        # Chat, Scripture, Dataset, Metrics
│   │   └── user_repository.py     # User CRUD + session management
│   ├── schemas/
│   │   ├── auth.py                # Pydantic: LoginRequest, RegisterRequest, TokenResponse
│   │   ├── requests.py            # Pydantic: ChatRequest, EnvUpdateRequest
│   │   └── responses.py           # Pydantic: ChatResponse, ChatError, TokenStatusResponse
│   ├── services/                  # Business logic
│   │   ├── ai_generation.py       # LLM calls, key rotation, transcribe
│   │   ├── embedding.py           # text-embedding-004 wrapper
│   │   ├── key_rotation.py      # Multi-key Gemini round-robin
│   │   ├── rate_limiter.py       # Token budget + RPM/RPD tracking
│   │   ├── reranker.py            # Cross-encoder scoring + confidence
│   │   ├── retrieval.py           # Hybrid BM25 + Vector search
│   │   └── translation.py         # langdetect + auto-translation
│   ├── scripts/                   # Diagnostic & migration utilities
│   │   ├── check_qa_dataset.py    # Report: documents, books, embeddings per book
│   │   ├── check_sample_doc.py    # Inspect one document's fields
│   │   ├── import_faiss_to_mongodb.py  # Import FAISS indexes → MongoDB (no API calls)
│   │   ├── migrate_all_books.py   # Regenerate embeddings from TSV (slow, burns API keys)
│   │   └── migrate_to_qa_dataset.py    # Single-book migration (legacy)
│   ├── data/en_tq/                # unfoldingWord TSV datasets (per book)
│   ├── static_data/               # Precompiled JSON scriptures & CSV
│   ├── static_data/vectorstores/gemini/  # Pre-built FAISS indexes (66 books, already imported)
│   ├── requirements.txt           # ⭐ DEPLOYED to Vercel (stripped, <50MB)
│   ├── requirements-local.txt     # Full local dev (faiss, langchain, etc.)
│   ├── requirements-vercel.txt    # Alias for requirements.txt
│   ├── runtime.txt                # Python 3.12 pinning
│   └── vercel.json                # Vercel routing config
│
├── next.config.ts                 # Next.js config (compress, reactCompiler)
├── package.json                   # Frontend deps + test script
├── jest.config.ts                 # Jest test configuration
├── tsconfig.json                  # TypeScript config
├── GITHUB_ISSUES.md               # Tracked issues (10 done, 4 future)
├── VERCEL_DEPLOY_FIX.md           # Deployment troubleshooting guide
└── README.md                      # Project overview
```

**Important:** `app/routes/` (auth.py, chat.py, analytics.py) are **NOT deployed to Vercel**. The deployed entry point is `api/index.py` only. The `app/routes/` files are the clean architecture version that is imported for local development but not used by Vercel's serverless function.

---

## 5. File-by-File Guide

### Frontend (Next.js)

| File | Purpose | Key Exports |
|------|---------|-------------|
| `src/app/page.tsx` | Root app component. Manages auth state, view switching, token metrics, Settings/Help modals. | `Home` (default) |
| `src/components/Workspace.tsx` | 3-pane study layout: scripture navigator (left), chat (center), verse reader (right). Handles SSE streaming, voice input, TTS playback, suggested questions. | `Workspace` |
| `src/components/Navbar.tsx` | Top navigation bar. Theme toggle, view switcher, user profile dropdown with logout. | `Navbar` |
| `src/components/StudyRoom.tsx` | Landing page grid of 66 Bible books. Searchable, animated. | `StudyRoom` |
| `src/components/LoginPage.tsx` | Auth UI. Login form + register form. Validates inputs, stores JWT in localStorage. | `LoginPage` |
| `src/components/MermaidDiagram.tsx` | Renders Mermaid.js diagrams from AI responses. | `MermaidDiagram` |
| `src/data/mockBible.ts` | Offline fallback data. Contains Genesis 1-2, Matthew 1, etc. Also has `defaultAIResponse()` for offline chat. | `mockBible` |

### Backend (FastAPI)

| File | Purpose | Key Classes/Functions |
|------|---------|---------------------|
| `backend/api/index.py` | **Vercel entry point.** All 18 routes, SSE streaming, auth, CORS, rate limiting, global exception handler. | `app` (FastAPI), `chat_endpoint`, `get_current_active_user` |
| `backend/app/core/config.py` | Pydantic settings. SECRET_KEY, MONGO_URI, token expiry, rate limits. | `Settings`, `settings` |
| `backend/app/core/security.py` | JWT creation/decode, bcrypt password hashing, login rate limiting. | `create_token`, `decode_token`, `hash_password`, `verify_password` |
| `backend/app/routes/auth.py` | Clean architecture auth routes. **NOT deployed.** | `router` |
| `backend/app/routes/chat.py` | Clean architecture chat routes. **NOT deployed.** | `router` |
| `backend/app/routes/analytics.py` | Clean architecture analytics routes. **NOT deployed.** | `router` |
| `backend/config.py` | Non-Pydantic config: book code mappings, offline overviews, disclaimer texts, RERANK thresholds. | `normalize_book_code`, `OFFLINE_OVERVIEWS`, `ALL_DISCLAIMERS` |
| `backend/db/mongodb.py` | MongoDB connection. Lazy async (Motor) + sync (PyMongo) dual connection. | `get_database()`, `get_sync_database()` |
| `backend/db/repositories.py` | Data access layer: ChatSession, Scripture, Dataset, Key, Metrics repositories. | `ChatSessionRepository`, `ScriptureRepository`, `DatasetRepository`, `KeyRepository`, `MetricsRepository` |
| `backend/db/user_repository.py` | User CRUD: create, get by username/ID, update, delete, session management. | `UserRepository` |
| `backend/services/ai_generation.py` | LLM calls via Google Gemini SDK. Key rotation on 429. Transcription. Query rewrite. | `generate_ai_answer`, `get_llm_instance_async`, `transcribe_audio`, `rewrite_query_with_context` |
| `backend/services/embedding.py` | Gemini text-embedding-004 wrapper. 768-dim Matryoshka truncation. | `get_embeddings_model_async` |
| `backend/services/retrieval.py` | Hybrid search: concurrent BM25 text search + vector search in MongoDB Atlas. | `hybrid_search` |
| `backend/services/reranker.py` | Cross-encoder scoring. Confidence decision: direct hit (≥0.85) vs LLM fallback. | `rerank_candidates`, `decide_best_match` |
| `backend/services/translation.py` | Language detection (langdetect). Auto-translate query to English, answer back to native. | `detect_user_language`, `translate_to_english`, `translate_text` |
| `backend/services/rate_limiter.py` | Token budget tracking. RPM/RPD counters synced via MongoDB. | `is_rate_limited_async`, `check_and_update_rate_limits_async`, `load_tokens_data_async`, `save_tokens_data_async` |
| `backend/services/key_rotation.py` | Multi-key Gemini round-robin. Reads keys from MongoDB `api_keys`. Pushes cooldown on 429. | `GeminiKeyRotator`, `get_key_rotator` |
| `backend/schemas/auth.py` | Pydantic models for auth. | `LoginRequest`, `RegisterRequest`, `TokenResponse`, `UserResponse` |
| `backend/schemas/requests.py` | Pydantic request models. | `ChatRequest`, `EnvUpdateRequest` |
| `backend/schemas/responses.py` | Pydantic response models. | `ChatResponse`, `ChatError`, `TokenStatusResponse`, `BookDatasetResponse` |

---

## 6. Data Flow: The RAG Pipeline

### Step-by-Step: What Happens When a User Asks a Question

```
User types: "What did God create in the beginning?"
        │
        ▼
┌─────────────────────────────────────┐
│ 1. FRONTEND: Workspace.tsx          │
│    - Sends POST /api/chat (SSE)    │
│    - Includes JWT auth header      │
│    - Includes conversation history │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 2. BACKEND: /api/chat endpoint      │
│    - IP rate limit check (30/min)  │
│    - JWT auth verification         │
│    - Start SSE stream              │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 3. LANGUAGE DETECTION               │
│    langdetect(original_query)      │
│    → "en" (English)                 │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 4. QUERY REWRITE (optional)         │
│    If history exists:               │
│    rewrite_query_with_context()     │
│    → "What did God create in the   │
│       beginning according to        │
│       Genesis 1?"                   │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 5. EMBEDDING GENERATION             │
│    text-embedding-004(query)       │
│    → 768-dim vector                 │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 6. HYBRID SEARCH (concurrent)       │
│    MongoDB Atlas:                   │
│    a) $vectorSearch (semantic)     │
│    b) $search (BM25 text)          │
│    → merged candidate list          │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 7. RE-RANKING                       │
│    cross-encoder(query, candidates)│
│    → scored list (0.0–1.0)         │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 8. CONFIDENCE DECISION              │
│    decide_best_match()              │
│                                     │
│    If score ≥ 0.85:                 │
│      → DIRECT HIT (return dataset   │
│         answer, 0 LLM tokens)       │
│                                     │
│    If 0.50 ≤ score < 0.85:         │
│      → LLM VERIFY (validate with    │
│         retrieved context)           │
│                                     │
│    If score < 0.50:                 │
│      → FALLBACK to AI generation    │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 9. TRANSLATION FALLBACK (if needed) │
│    If non-English miss:               │
│    - translate query → English       │
│    - search English dataset          │
│    - translate answer → native       │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 10. ANSWER GENERATION               │
│     generate_ai_answer()            │
│     → Gemini 2.5 Flash              │
│     → streaming response            │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 11. CLEANUP & METRICS               │
│     - Remove disclaimers from text  │
│     - Update token budget           │
│     - Generate suggested questions  │
│     - Generate mermaid diagram      │
│     - Save to MongoDB chat_history  │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 12. SSE RESPONSE TO FRONTEND        │
│     event: status → event: status   │
│     → ... → event: result          │
│     (JSON with answer, reference,   │
│     suggested questions, diagram)   │
└─────────────────────────────────────┘
```

### Hybrid Search Detail

```python
# Vector Search (Semantic)
{
  "$vectorSearch": {
    "index": "vector_index",
    "queryVector": query_embedding,  # 768 dims
    "path": "embedding",
    "numCandidates": 100,
    "limit": 10
  }
}

# Text Search (BM25 Lexical)
{
  "$search": {
    "index": "text_index",
    "text": {
      "query": query_text,
      "path": "question"
    }
  }
}
```

Results are merged and re-ranked by a cross-encoder.

---

## 7. Authentication Flow

```
┌─────────┐     ┌─────────────┐     ┌──────────────┐     ┌─────────┐
│  User   │     │  Frontend   │     │   Backend    │     │ MongoDB │
└────┬────┘     └──────┬──────┘     └──────┬───────┘     └────┬────┘
     │                 │                   │                  │
     │ username+pw     │                   │                  │
     │────────────────>│                   │                  │
     │                 │ POST /api/auth/login                  │
     │                 │──────────────────────────────────────>│
     │                 │                   │                  │
     │                 │                   │ bcrypt verify   │
     │                 │                   │─────────────────>│
     │                 │                   │                  │
     │                 │                   │ generate JWT     │
     │                 │                   │ (session_id)     │
     │                 │                   │                  │
     │                 │                   │ store session_id│
     │                 │                   │─────────────────>│
     │                 │                   │                  │
     │                 │ JWT + user info   │                  │
     │                 │<──────────────────────────────────────│
     │                 │                   │                  │
     │ token stored     │                   │                  │
     │ in localStorage  │                   │                  │
     │<────────────────│                   │                  │
     │                 │                   │                  │
     │ ─── SUBSEQUENT REQUESTS ───          │                  │
     │                 │                   │                  │
     │                 │ GET /api/auth/me  │                  │
     │                 │ Authorization: Bearer <token>         │
     │                 │──────────────────────────────────────>│
     │                 │                   │                  │
     │                 │                   │ decode JWT       │
     │                 │                   │ get session_id   │
     │                 │                   │ compare to DB    │
     │                 │                   │─────────────────>│
     │                 │                   │                  │
     │                 │ 200 OK / 401      │                  │
     │                 │<──────────────────────────────────────│
     │                 │                   │                  │
     │ ─── LOGOUT ───  │                   │                  │
     │                 │                   │                  │
     │                 │ POST /api/auth/logout                 │
     │                 │──────────────────────────────────────>│
     │                 │                   │ clear session_id │
     │                 │                   │─────────────────>│
     │                 │ 200 OK            │                  │
     │                 │<──────────────────────────────────────│
     │                 │                   │                  │
     │ clear token     │                   │                  │
     │<────────────────│                   │                  │
     │                 │                   │                  │
```

**Single-Session Enforcement:**
- Each login generates a new `session_id` (UUID)
- JWT contains `session_id`
- On every authenticated request, backend compares JWT `session_id` to DB `session_id`
- If they don't match → `401 Session expired or superseded`
- This means: logging in on a new device **automatically logs out the old device**

---

## 8. API Reference

### Public Endpoints (No Auth)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API info: name, version, links to docs & health |
| `GET` | `/api/health` | Health check + MongoDB ping status |
| `GET` | `/api/dataset/{book}` | Raw Q&A dataset for a book (no auth) |
| `POST` | `/api/auth/register` | Create new user account |
| `POST` | `/api/auth/login` | Login, returns JWT + user info |
| `GET` | `/api/tokens` | Current token usage status |
| `POST` | `/api/tokens/reset` | Reset token budget to default |
| `POST` | `/api/transcribe` | Audio → text (Gemini STT) |
| `POST` | `/api/tts` | Text → Base64 MP3 (gTTS) |

### Protected Endpoints (JWT Required)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/api/auth/me` | Bearer | Get current user profile |
| `POST` | `/api/auth/logout` | Bearer | Log out, invalidate session |
| `POST` | `/api/chat` | Bearer | SSE streaming RAG chat |
| `GET` | `/api/history/{book}` | Bearer | Chat history for a book |
| `DELETE` | `/api/history/{book}` | Bearer | Delete chat history for a book |
| `GET` | `/api/scripture/{book}/{chapter}` | — | Scripture text (cached, 1hr) |
| `POST` | `/api/settings/env` | — | Update env var (Vercel only, filesystem) |

### SSE Chat Response Format

```
event: status
data: Detecting language...

event: status
data: Language detected: English

event: status
data: Searching English dataset...

event: status
data: ✅ Match found (confidence: 95%)

event: result
data: {"answer": "...", "reference": "1:1", "suggested_questions": [...], "diagram": "...", "source": "dataset_native", ...}
```

---

## 9. Database Schema

### `users` Collection
```json
{
  "_id": ObjectId("..."),
  "username": "default_user",
  "email": "default@example.com",
  "password_hash": "$2b$12$...",
  "session_id": "uuid-v4-string",
  "created_at": ISODate("..."),
  "updated_at": ISODate("...")
}
```
- `username`: unique, indexed
- `session_id`: changes on every login (single-session enforcement)

### `qa_dataset` Collection (RAG Knowledge Base)
**Status:** ✅ Fully populated. **15,094 documents** across all 66 books. All data is already in MongoDB `qa_dataset` collection. No migration scripts need to be run.

The collection was built from two sources:
1. **Pre-built FAISS vectorstores** (`backend/static_data/vectorstores/gemini/`) — 13,871 docs imported
2. **Missing TSV documents** (`backend/data/en_tq/`) — 1,242 docs with freshly generated embeddings

```json
{
  "_id": ObjectId("..."),
  "book_code": "GEN",
  "chapter": 1,
  "verse": 1,
  "reference": "1:1",
  "question": "What did God create in the beginning?",
  "response": "In the beginning, God created the heavens and the earth.",
  "lang_code": "en",
  "embedding": [0.023, -0.045, ..., 0.112],  // 768 floats
  "search_text": "1:1 What did God create in the beginning? In the beginning...",
  "paraphrases": [],
  "metadata": {
    "source": "unfoldingWord_tq",
    "imported_from": "faiss_vectorstore"
  }
}
```
- `book_code`: 3-letter Bible book code (e.g., `GEN`, `MAT`, `REV`)
- `embedding`: 768-dim Matryoshka-truncated vector from `text-embedding-004`
- `search_text`: Combined `reference + question + response` for BM25 lexical search
- `paraphrases`: Reserved for future multilingual paraphrases
- Indexes: `vector_index` (on `embedding`), `text_index` (on `search_text`)
- **No migration needed.** The collection is complete.

### `chat_history` Collection
```json
{
  "_id": ObjectId("..."),
  "user_id": "default_user",
  "book_code": "GEN",
  "history": [
    {"role": "user", "content": "What did God create?", "timestamp": "..."},
    {"role": "assistant", "content": "God created the heavens...", "timestamp": "...", "versesHighlighted": ["1:1"]}
  ],
  "updated_at": ISODate("...")
}
```

### `api_keys` Collection (Key Rotation)
```json
{
  "_id": ObjectId("..."),
  "provider": "gemini",
  "key_index": 0,
  "key": "AIzaSy...",
  "cooldown_until": 0.0,
  "failures": 0
}
```
- 10 documents (one per key) for free tier rotation
- `cooldown_until`: Unix timestamp. Key is skipped if `now < cooldown_until`

### `system_metrics` Collection
```json
{
  "_id": "token_budget",
  "total_tokens_used": 45000,
  "pending_tokens": 55000,
  "limit": 100000,
  "requests_today": 120,
  "requests_this_minute": 3,
  "last_minute_reset_time": 1234567890.0,
  "last_day_reset_time": 1234567890.0
}
```
- Singleton document. Synced across all Vercel instances via MongoDB.

### `login_audit` Collection
```json
{
  "_id": ObjectId("..."),
  "username": "default_user",
  "timestamp": ISODate("..."),
  "status": "success"
}
```

---

## 10. Environment Variables

### Backend (`.env` or Vercel Dashboard)

| Variable | Required | Example | Purpose |
|----------|----------|---------|---------|
| `MONGO_URI` | ✅ | `mongodb+srv://user:pass@cluster.mongodb.net/vachan_study?retryWrites=true&w=majority` | MongoDB connection |
| `SECRET_KEY` | ✅ | `a1b2c3d4...` (64 hex chars) | JWT signing |
| `GEMINI_API_KEY` | ⚠️ | `AIzaSy...` | Primary Gemini API key (fallback if MongoDB keys empty) |
| `ALLOWED_ORIGINS` | ⚠️ | `https://vachan-study-chat-snpm.vercel.app` | CORS origins (comma-separated) |
| `BIBLE_API_KEY` | ❌ | `abc123...` | API.Bible REST key (for dynamic scripture) |
| `SSE_MAX_DURATION` | ❌ | `10` | SSE timeout in seconds (default: 8 on Vercel, 30 local) |
| `SKIP_DIAGRAM` | ❌ | `1` | Skip Mermaid diagram generation (saves 1 LLM call) |

### Frontend (`.env.local` or Vercel Dashboard)

| Variable | Required | Example | Purpose |
|----------|----------|---------|---------|
| `NEXT_PUBLIC_API_URL` | ✅ | `https://vachan-study-chat.vercel.app` | Backend API base URL |

---

## 11. Deployment Guide

### Prerequisites
- Node.js 18+ (for frontend)
- Python 3.12 (for backend)
- MongoDB Atlas account (free M0 tier sufficient)
- Vercel account (free tier sufficient for testing)
- Google AI Studio account (free Gemini API keys)

### Local Development

```bash
# 1. Clone and install frontend
cd Logos Bible Study Chatbot
npm install

# 2. Install backend (create venv)
cd backend
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
pip install -r requirements-local.txt  # Full deps (faiss, langchain, etc.)

# 3. Create .env files
cp .env.example .env
# Edit .env: set MONGO_URI, SECRET_KEY, GEMINI_API_KEY

cd ..
cp .env.example .env.local
# Edit .env.local: set NEXT_PUBLIC_API_URL=http://127.0.0.1:8000

# 4. Seed MongoDB with 10 Gemini keys (for API rotation)
# The qa_dataset collection is ALREADY populated (13,871 docs, 66 books).
# No migration needed. Run this only if you need to seed Gemini keys:
#   python backend/scripts/seed_api_keys.py
# Or manually add 10 documents to `api_keys` collection

# 5. Start backend
cd backend
python -m uvicorn api.index:app --host 127.0.0.1 --port 8000 --reload

# 6. Start frontend (new terminal)
cd Logos Bible Study Chatbot
npm run dev
# Open http://localhost:3000
```

### Vercel Production Deploy

**Frontend Project:**
1. Import GitHub repo into Vercel
2. Framework: Next.js (auto-detected)
3. Set env var: `NEXT_PUBLIC_API_URL=https://vachan-study-chat.vercel.app`
4. Deploy

**Backend Project:**
1. Import same GitHub repo into Vercel (separate project)
2. **Root Directory:** `backend` (or `.` if deploying from root)
3. **Framework Preset:** `Other` (not Python — let Vercel auto-detect `api/*.py`)
4. Set env vars:
   - `MONGO_URI`
   - `SECRET_KEY`
   - `ALLOWED_ORIGINS=https://vachan-study-chat-snpm.vercel.app`
5. Deploy

**MongoDB Atlas:**
1. Go to Network Access → Add IP Address
2. Enter `0.0.0.0/0` (allows all IPs — Vercel serverless uses dynamic IPs)
3. Confirm

**Verify Dataset (already present):**
1. The `qa_dataset` collection should already have 13,871 documents across 66 books
2. To verify: run `python backend/scripts/check_qa_dataset.py` locally
3. If empty or incomplete, run `python backend/scripts/import_faiss_to_mongodb.py` to import from FAISS

**Seed API Keys (only if empty):**
1. Add 10 Gemini API keys to the `api_keys` collection in MongoDB
2. Each document: `{provider: "gemini", key_index: 0-9, key: "AIzaSy...", cooldown_until: 0.0, failures: 0}`

---

## 12. Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| `500: FUNCTION_INVOCATION_FAILED` | Vercel loading stale `app/main.py` instead of `api/index.py` | Set `vercel.json` with explicit `functions: {"api/index.py": {}}` |
| `Failed to fetch` / CORS error | Backend not allowing frontend origin | Check `ALLOWED_ORIGINS` env var includes frontend URL |
| `Token quota exhausted` | All 10 Gemini keys on cooldown | Wait 60 seconds, or reduce LLM calls per query |
| `Request is taking too long` | Vercel 10s timeout hit | Query is too complex. Simplify question, or upgrade to Vercel Pro |
| MongoDB connection timeout | IP whitelist missing `0.0.0.0/0` | Add `0.0.0.0/0` to MongoDB Atlas Network Access |
| `ImportError: cannot import name app` | Circular import in `app/main.py` | Delete `backend/app/main.py` if it exists; use `api/index.py` only |
| `localStorage` token lost on refresh | Token not validated on mount | Frontend checks `/api/auth/me` on mount, shows login if invalid |
| `bcrypt` build errors on Vercel | `requirements.txt` has `bcrypt` but no build tools | Use `bcrypt` (precompiled wheels) not `py-bcrypt` |
| `faiss-cpu` too large for Vercel | `requirements.txt` includes `faiss-cpu` (~50MB) | Use `requirements.txt` (stripped) or `requirements-vercel.txt` |

---

## 13. How to Extend

### Add a New Bible Book to the Dataset
**The dataset is already complete (66 books, 13,871 docs).** Only use this if you want to add a new book or regenerate embeddings.

**Option A: Import from FAISS (fast, no API calls)**
1. Pre-build FAISS indexes in `backend/static_data/vectorstores/gemini/{BOOK}/`
2. Run `python backend/scripts/import_faiss_to_mongodb.py`

**Option B: Regenerate from TSV (slow, burns API keys)**
1. Download the TQ TSV for the book from unfoldingWord
2. Place in `backend/data/en_tq/{book_code}.tsv`
3. Run `python backend/scripts/migrate_all_books.py`

### Add a New Language
1. Add `lang_code` to `backend/services/translation.py` supported languages
2. Add sample questions in that language to `qa_dataset` with `lang_code` field
3. The pipeline auto-detects and translates via Gemini

### Add a New API Endpoint
1. Add route to `backend/api/index.py` (the deployed entry point)
2. OR add to `backend/app/routes/` (clean architecture, not deployed by Vercel)
3. If using `app/routes/`, import and include in `backend/api/index.py` as well

### Change the LLM Model
1. Edit `GEMINI_MODEL` in `backend/services/ai_generation.py`
2. Current: `"gemini-2.5-flash"`
3. Options: `"gemini-1.5-pro"`, `"gemini-1.5-flash-8b"`

### Add Redis for Distributed Rate Limiting
1. Sign up for Upstash Redis (free tier)
2. Replace `_ip_rate_store` dict in `api/index.py` with Redis `INCR` + `EXPIRE`
3. This persists across Vercel cold starts

---

## 14. Glossary

| Term | Meaning |
|------|---------|
| **RAG** | Retrieval-Augmented Generation: search documents first, then generate answer |
| **SSE** | Server-Sent Events: one-way streaming from server to browser |
| **BM25** | Best Match 25: lexical (keyword) search algorithm |
| **Vector Search** | Semantic similarity search using embeddings |
| **Cross-Encoder** | Re-ranking model that scores query-document pairs |
| **Matryoshka** | Truncating embeddings to lower dimensions while preserving quality |
| **Direct Hit** | Answer found in dataset with high confidence — no LLM needed |
| **Key Rotation** | Switching between multiple API keys when one hits rate limit |
| **Single-Session** | Only one device can be logged in per user at a time |
| **Cold Start** | First request after serverless function has been idle (slower) |
| **TQ** | Translation Questions (unfoldingWord dataset) |

---

*Generated for Vachan Study. Last updated after Vercel deployment fixes and production hardening.*

*For AI models: This document is the single source of truth. Always read this before modifying any file in this project.*
