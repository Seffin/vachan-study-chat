# Logos Bible Study Chatbot - Project Outline

This is the detailed outline of the project structure and architecture for the **Logos Bible Study Chatbot (vachan-study-chat)**.

## 1. Project Overview & Architecture
The project is a Dual-Mode Retrieval-Augmented Generation (RAG) chatbot designed for Bible study, built as a monorepo containing both the frontend and backend.
- **Frontend:** Next.js 16 (App Router) with Tailwind CSS v4, Framer Motion, and Lucide React.
- **Backend:** Python FastAPI providing AI routing, data retrieval, and data persistence.
- **Database:** MongoDB Atlas (accessed asynchronously via Motor).
- **Deployment:** Vercel (Frontend deployed as Next.js app, Backend deployed as Vercel Serverless Functions via `@vercel/python`).

---

## 2. Root Directory Configuration
- `package.json` / `package-lock.json`: Node dependencies and Next.js run scripts.
- `next.config.ts` / `tsconfig.json` / `eslint.config.mjs`: TypeScript and Next.js configuration.
- `.env.local` / `.env.example`: Frontend environment variable configuration.
- **Documentation:**
  - `README.md`: High-level project summary.
  - `RUNNING.md`: Local setup, Vercel simulation, and running instructions.
  - `BACKEND_DOCS.md` / `FRONTEND_DOCS.md`: Detailed architectural docs for respective halves of the app.
  - `VERCEL_LOCAL_SETUP.md`: Explanation of Vercel serverless behavior and quotas.

---

## 3. Frontend (`src/` and `public/`)
The Next.js frontend handles the interactive UI, displaying scriptures and the chatbot interface side-by-side.

- **`src/app/`**
  - `layout.tsx`: Root HTML layout wrapper.
  - `page.tsx`: Landing page and main application entry point.
  - `globals.css`: Tailwind configuration and global styles.

- **`src/components/`**
  - `Workspace.tsx`: The core component that controls the dual-pane layout. It manages state for the scripture reader, fetches dynamic scriptures, displays chat history, and sends queries to the RAG backend.
  - *(Other UI components like Navbar or Settings panels as they are split out)*.

- **`src/data/`**
  - Contains frontend mock data (`mockBible.ts`) which acts as an offline fallback if the API is unreachable.

---

## 4. Backend (`backend/`)
The FastAPI backend serves the intelligent RAG pipeline, interacts with MongoDB, and processes AI responses.

- **Configuration & Setup:**
  - `requirements.txt`: Python pip dependencies (FastAPI, Motor, LangChain, FAISS, etc.).
  - `.env`: Backend environment variables (`MONGO_URI`, `OPENAI_API_KEY`, etc.).
  - `vercel.json`: Directs Vercel to use the python builder for all `/api/(.*)` requests routing to `api/index.py`.

- **`backend/api/` (Core API)**
  - `index.py`: The main FastAPI application. Contains the endpoints:
    - `POST /api/chat`: The intelligent 3-Tier Matcher (Dataset Exact Match ➔ FAISS/Semantic Match ➔ LLM Gen-AI Fallback).
    - `GET /api/scripture/{book}/{chapter}`: Fetches scripture dynamically from API.Bible and caches it to MongoDB.
    - `GET /api/history/{book}`: Retrieves user chat history from MongoDB.
    - `DELETE /api/history/{book}`: Clears chat history for a given book.

- **`backend/db/` (Database Layer)**
  - `mongodb.py`: Manages the MongoDB connection using the async `Motor` driver. It includes **lazy initialization** to cleanly support Vercel's ephemeral Serverless Function cold-starts.

- **`backend/scripts/` (Utilities & Processing)**
  - `build_vector_db.py`: Compiles local TSV datasets into optimized FAISS vector indices for semantic search.
  - `setup_mongodb.py`: Initializes MongoDB collections and validation schemas.

- **`backend/data/` and `backend/static_data/`**
  - Stores the UnfoldingWord dataset files (`.tsv`, `.csv`).
  - Stores local FAISS vector indices used to minimize AI costs.
  - `tokens.json`: Tracks LLM token usage for rate-limiting.
