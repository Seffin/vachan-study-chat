# Logos Bible Study Chatbot - Project Outline

This is the outline of the current project structure for the **Logos Bible Study Chatbot (vachan-study-chat)**.

## 1. Project Root Directory
The project uses a monorepo-style structure, housing both the Next.js frontend and Python FastAPI backend in the same repository.

- **Config & Meta Files:**
  - `package.json` / `package-lock.json` - Node dependencies and scripts.
  - `next.config.ts` / `tsconfig.json` / `eslint.config.mjs` - Next.js and TypeScript configurations.
  - `.env.local` / `.env.example` - Frontend environment variables.
  - `AGENTS.md`, `README.md`, `BACKEND_DOCS.md`, `FRONTEND_DOCS.md`, `RUNNING.md`, `VERCEL_LOCAL_SETUP.md` - Comprehensive documentation and agent instructions.
  - `.antigravity/` - Local gStack and Antigravity persona definitions/rules.

## 2. Frontend (`src/` and `public/`)
The frontend is built with **Next.js 16 (App Router)** and styled using Tailwind CSS (configured via `postcss.config.mjs`).

- **`src/app/` (Next.js App Router)**
  - `layout.tsx` - Root layout wrapper.
  - `page.tsx` - Main landing page and dashboard logic.
  - `globals.css` - Global styling configurations.

- **`src/components/` (React Components)**
  - `Navbar.tsx` - Top navigation bar component.
  - `StudyRoom.tsx` - UI for the Bible study interface.
  - `Workspace.tsx` - Core component handling the chat interface, scripture viewing, and layout management.

- **`src/data/`**
  - Contains frontend-specific static data or constants.

- **`public/`**
  - Static assets (images, fonts, etc.).

## 3. Backend (`backend/`)
The backend is a **FastAPI** Python application that serves the Q&A endpoints, handles vector retrieval, and interfaces with LLMs (Gemini/OpenAI) for the RAG (Retrieval-Augmented Generation) pipeline.

- **Configuration:**
  - `requirements.txt` - Python dependencies.
  - `.env` / `.env.example` - Backend environment variables (API keys).
  - `vercel.json` - Deployment configuration for Vercel Serverless Functions.
  - `BACKEND_DOCS.md` - Backend-specific documentation.

- **`backend/api/` (API Endpoints)**
  - `index.py` - Main FastAPI application file. Contains the `/api/chat` endpoint and implements the **3-Tier Matching Algorithm**:
    - **Tier 1:** Exact Match (from Dataset)
    - **Tier 2:** Semantic Match (via Word Overlap / FAISS distance thresholds)
    - **Tier 3:** AI Generation Fallback (using LLMs)

- **`backend/scripts/` (Data Processing & Utility Scripts)**
  - `build_vector_db.py` - Compiles FAISS vector databases from the UnfoldingWord dataset for fast retrieval.
  - `fetch_api_scripture.py` - Fetches scripture text.
  - `generate_csv_fallbacks.py` - Generates fallback CSVs for semantic offline search.
  - `precompile_all_scriptures.py` - Precompiles scripture data for quick access.

- **`backend/static_data/` and `backend/data/`**
  - Stores the UnfoldingWord Q&A dataset (`tq_MAT.csv`, etc.).
  - Contains dynamically generated Vectorstores (FAISS indices) used by the LLM RAG pipelines.
  - `tokens.json` (inside `backend/data/`) - Token tracking or analytics.
