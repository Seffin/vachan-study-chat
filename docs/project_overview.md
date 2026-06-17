# Logos Bible Study Chatbot (Vachan Study) Overview

## 🌟 Core Features & Purpose
The Logos Bible Study Chatbot is an advanced, full-stack, multilingual AI application designed to provide scholarly, faithful, and contextual answers to biblical questions based on the unfoldingWord theological dataset. 

Key capabilities include:
- **Intelligent Hybrid RAG Engine:** Uses MongoDB Atlas Vector Search for semantic and keyword retrieval, backed by dynamic confidence routing (High, Medium, Low) to fallback to LLM generation when needed.
- **Multilingual Support:** Auto-detects user language, translates queries to English for internal RAG, and translates the answer back.
- **Real-Time Streaming:** Streams generative AI responses over Server-Sent Events (SSE) to the frontend.
- **Audio/Voice Integration:** "Push-to-talk" microphone feature on the frontend using `gTTS` for text-to-speech and Google Gemini for Speech-to-Text via Base64 tunneling.
- **Offline / Self-Healing Mode:** If the backend or AI provider is offline, the frontend falls back to a simulated offline mode using local datasets.
- **API Key Rotation:** Manages free-tier Gemini API keys dynamically through MongoDB to avoid rate-limit exhaustion.

## 🏗️ Architecture

### Frontend (Next.js)
The frontend is built with **Next.js 16** and **React 19**, written in TypeScript. 
- **Styling:** Tailwind CSS v4 and Framer Motion for elegant UI animations.
- **Core Components:** The main interface is centered around the `Workspace.tsx` component, dividing the view into a chat pane, a scripture reader (which dynamically highlights verses), and suggested follow-up questions chips.
- **State Management:** Handles connection drop-offs natively, switching to a local simulation if the FastAPI backend fails. 

### Backend (FastAPI / Python)
The backend is a **FastAPI** service running in Python, designed to be deployed as Vercel Serverless Functions.
- **Database:** MongoDB Atlas (M0 Free Tier) for both standard collections (`chat_history`, `api_keys`) and vector indices (`qa_dataset` with 768-dimensional Matryoshka embeddings).
- **Core Endpoints:**
  - `POST /api/chat`: Handles the conversational loop via SSE.
  - `POST /api/transcribe`: Processes `audio/webm` BLOBs via Gemini for transcription.
  - `POST /api/tts`: Base64 audio tunneling for text-to-speech (via Google gTTS).
- **LLM/AI Stack:** LangChain, Google Gemini API (`gemini-2.5-flash`, `text-embedding-004`), and HuggingFace Cross-Encoder for re-ranking.

## 🚀 Running the Project
The project is currently running in your environment:
- **Backend Server:** Running via `python .\api\index.py` on `http://127.0.0.1:8000`.
- **Frontend Server:** Running via `npm run dev` on `http://localhost:3000`.

## 📁 Key Directories
- `/src/components/` - Houses the main Next.js React components (e.g., `Workspace.tsx`).
- `/backend/api/` - FastAPI backend application entry points.
- `/docs/` and `*.md` - In-depth documentation (e.g., `BACKEND_DOCS.md`, `FRONTEND_DOCS.md`).
