# Logos Bible Study Chatbot (Vachan Study)

A highly advanced, full-stack, multilingual AI application designed to provide scholarly, faithful, and contextual answers to biblical questions based on the unfoldingWord theological dataset.

## 🌟 Core Features

### 🧠 Intelligent Hybrid RAG Engine
- **MongoDB Atlas Vector Search:** Combines deep semantic vector embeddings with keyword-based exact matching for unparalleled retrieval accuracy.
- **Dynamic Confidence Routing:** Evaluates search results using a custom re-ranker.
  - **High Confidence (>0.85):** Instantly returns the exact theological dataset answer.
  - **Medium Confidence:** Runs a secondary LLM verification pass to ensure the answer strictly answers the user's question without hallucinations.
  - **Low Confidence (Miss):** Falls back to generative AI to provide a scholarly answer based on general theological knowledge.

### 🌍 Universal Multilingual Support
- **Native Translation Pipeline:** Users can ask questions in any language (e.g., Malayalam, Hindi, Spanish). The system automatically detects the language, translates the query to English to query the dataset, and flawlessly translates the theological answer back to the user's native tongue.

### 🔄 Fault-Tolerant API Key Rotation
- **Zero-Downtime Gemini Pool:** Built specifically for free-tier LLM limits. The system accepts a comma-separated list of Gemini API keys.
- **Auto-Healing:** If an API key hits a rate limit (`429 RESOURCE_EXHAUSTED`), an invalid state (`400`), or server overload (`503`), the key is instantly placed on a 60-second cooldown and the request seamlessly rotates to the next available key without interrupting the user.

### ⚡ Real-Time Streaming (SSE)
- **Server-Sent Events (SSE):** The FastAPI backend streams the generative text back to the Next.js frontend token-by-token.
- **Interactive UI Feedback:** The frontend displays live internal RAG states (e.g., "Attempting English Translation...", "Re-ranker MEDIUM confidence", "Rotating API Key...") inside a loading bubble so the user always knows what the system is doing.

### 💡 Context-Aware Suggestions
- **Smart Follow-ups:** Dynamically generates 3 relevant follow-up questions based on the current chat history and the current book of the Bible.
- **Chapter Rollover Logic:** Intelligently suggests questions for the *next* chapter when the user reaches the end of the current context.

### 📖 Open Bible Integration
- **Live Scripture:** Integrates directly with `rest.api.bible` to fetch full biblical chapters on demand for side-by-side reading and context.

### 🏗️ Offline / Zero-Cost Fallback
- **Local RAG:** If no API keys are provided or all keys fail, the system falls back to a completely offline, zero-cost semantic overlap search using local CSV datasets, ensuring the app never truly goes down.

### 🎙️ Voice & Audio Experience
- **Push-to-Talk Microphone Flow:** The workspace includes a push-to-talk microphone button that captures audio input.
- **Animated Recording Feedback:** Visual feedback animates during recording to show the user the system is listening.
- **Voice-First Prompts:** Voice-first prompts make the study experience feel more conversational and immersive.

---

### Architecture at a Glance

Vachan Study is a full-stack scripture study experience built around a Next.js frontend and a FastAPI backend. The frontend provides a book navigator, live chat workspace, scripture reader, and voice-first interaction layer, while the backend streams responses over Server-Sent Events, detects user language, runs hybrid retrieval, and returns context-aware answers with scripture references. The system is designed to stay useful even when AI providers are unavailable by falling back to local datasets, translation steps, or a lightweight offline simulator.

---

## 🛠️ Technology Stack

**Frontend:**
- **Framework:** Next.js (React)
- **Language:** TypeScript
- **Styling:** Tailwind CSS (or Vanilla CSS) + Framer Motion for smooth streaming animations.

**Backend:**
- **Framework:** FastAPI (Python)
- **Database:** MongoDB Atlas (Cloud Vector Database)
- **AI/LLM:** LangChain, Google Gemini (2.5-flash & Embeddings), OpenAI (optional fallback)
- **Concurrency:** `asyncio` and thread-safe locks for API key management.

---

## 🚀 Getting Started

### Prerequisites
- Node.js (v18+)
- Python (3.10+)
- A free MongoDB Atlas cluster.
- One or more Google Gemini API keys.

### 1. Backend Setup
1. Navigate to the `/backend` directory.
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `.\venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Configure your `.env` file (see `.env.example`). Add your `MONGO_URI` and `GEMINI_API_KEYS`.
6. Run the server: `python api/index.py` (Server starts on `http://127.0.0.1:8000`)

### 2. Frontend Setup
1. Navigate to the project root directory.
2. Install dependencies: `npm install`
3. Start the Next.js development server: `npm run dev`
4. Open `http://localhost:3000` in your browser.

---

## 🗄️ Database Architecture
The system uses **MongoDB Atlas** for data storage. The core collection is `qa_dataset` located inside the `vachan_study` database.
- **Vectors:** Stores 768-dimensional Matryoshka embeddings.
- **Metadata:** Stores `book_code`, `chapter`, `verse`, `question`, and `response`.

*(Migration scripts from legacy FAISS indexes are provided in `backend/scripts/migrate_from_faiss_to_mongodb.py`)*
