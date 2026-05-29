# 📖 Vachan Study Bible Study Chatbot — Running & Setup Guide

Welcome to the **Vachan Study Bible Study Chatbot**! This guide contains everything you need to set up, configure, pre-compile, and run both the FastAPI backend and the Next.js frontend.

---

## 🏗️ System Architecture

The application is structured into two main components:

1. **Frontend (`src/` & `app/`)**: A sleek, high-fidelity Next.js web application utilizing **Tailwind CSS v4**, **Framer Motion**, and **Lucide Icons** to deliver a modern, interactive Bible study chat interface.
2. **Backend (`backend/`)**: A **FastAPI** server hosting a **Dual-Mode Retrieval-Augmented Generation (RAG)** pipeline.
   * **OpenAI Mode**: High-fidelity vector search using `FAISS` and `OpenAIEmbeddings`, combined with `gpt-4o-mini` for response generation.
   * **Semantic Fallback Mode**: Offline, zero-cost semantic overlap matching that runs fully locally if no OpenAI API Key is configured.

---

## 🛠️ Prerequisites

Before you begin, ensure you have the following installed on your machine:
* **Node.js** (v18.x or newer) & **npm** (v9.x or newer)
* **Python** (v3.10 or newer)
* **Git** (for cloning dataset repositories during bootstrapping)

---

## 🚀 Step-by-Step Installation

### Step 1: Clone & Initialize the Workspace
Open your terminal (PowerShell, CMD, or Bash) and navigate to the project root directory:
```bash
cd "H:\Seffin\Benjamin\Logos Bible Study Chatbot"
```

---

### Step 2: Configure and Run the Backend

The backend handles text ingestion, vector stores, and scripture/QA endpoints.

#### 1. Navigate to the backend folder
```bash
cd backend
```

#### 2. Create a Python Virtual Environment
Creating a virtual environment ensures dependencies do not conflict with other Python projects on your system:
* **Windows (PowerShell/CMD)**:
  ```powershell
  python -m venv venv
  .\venv\Scripts\activate
  ```
* **macOS/Linux**:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

#### 3. Install Backend Dependencies
With your virtual environment activated, run:
```bash
pip install -r requirements.txt
```

#### 4. Configure Environment Variables
Copy the backend environment template file to `.env`:
* **Windows (PowerShell)**:
  ```powershell
  Copy-Item .env.example .env
  ```
* **macOS/Linux / Git Bash**:
  ```bash
  cp .env.example .env
  ```

Open the newly created `backend/.env` file in your editor. Here are the core settings:
```ini
HOST=127.0.0.1
PORT=8000
RELOAD=True

# 🧠 LLM API CONFIGURATIONS
# Paste your OpenAI API key to enable FAISS vector search and gpt-4o-mini.
# If left blank, the system automatically runs in zero-cost, offline fallback mode!
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.1

# 📂 Data URLs (Pre-configured)
TQ_SOURCE_URL=https://git.door43.org/unfoldingWord/en_tq.git
TQ_ZIP_FALLBACK_URL=https://git.door43.org/unfoldingWord/en_tq/archive/master.zip
```

> [!NOTE]
> **Data Self-Healing Bootstrapping:** When you start the backend, it will automatically check if the unfoldingWord English Translation Questions (`en_tq`) repository is present. If it is missing, it will attempt a `git clone` or pull from the HTTP ZIP fallback url to fetch the datasets automatically.

#### 5. Pre-compile the Vector Database (Optional — OpenAI Mode only)
If you have configured a valid `OPENAI_API_KEY` in `backend/.env` and want to build the FAISS persistent vector databases for all books of the Bible, run the CLI pre-compiler:
```bash
python build_vector_db.py
```
*This will parse all TSV datasets in `backend/data/en_tq/`, generate OpenAI Embeddings, and save the persistent FAISS indexes locally in `backend/data/vectorstores/` for ultra-fast lookup.*

#### 6. Start the FastAPI Backend Server
Now run the backend:
```bash
python main.py
```
You should see Uvicorn start on `http://127.0.0.1:8000`. You can visit `http://127.0.0.1:8000/docs` in your browser to view the interactive FastAPI documentation (Swagger UI).

---

### Step 3: Configure and Run the Frontend

The frontend is a Next.js web application built with a responsive user interface.

#### 1. Navigate back to the Root Workspace
Open a new terminal session or navigate out of the backend folder:
```bash
cd ..
```

#### 2. Install Frontend Dependencies
```bash
npm install
```

#### 3. Configure Frontend Environment Variables
Copy the frontend environment template file to `.env.local`:
* **Windows (PowerShell)**:
  ```powershell
  Copy-Item .env.example .env.local
  ```
* **macOS/Linux / Git Bash**:
  ```bash
  cp .env.example .env.local
  ```

Open the `h:\Seffin\Benjamin\Logos Bible Study Chatbot\.env.local` file and verify the backend API address matches:
```ini
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

#### 4. Run the Next.js Development Server
Start the frontend development server:
```bash
npm run dev
```
The Next.js server will spin up on `http://localhost:3000`.

---

## 🎨 Verification & Interaction

1. Open your web browser and navigate to **`http://localhost:3000`**.
2. You will be greeted by the Vachan Study Bible Study Chatbot interface.
3. Select a book (e.g., **Matthew**) and a chapter to load scripture context on the screen.
4. Type a question in the chat bar (e.g., *"Why did Joseph want to divorce Mary?"* or *"Explain the significance of the name Immanuel"*).
5. Watch the dual-mode RAG retrieve scripture references and context to answer your question!

---

## ⚠️ Troubleshooting & FAQ

* **Q: I don't have an OpenAI API Key. Can I still run the project?**
  * **A:** Yes! The backend automatically detects the absence of `OPENAI_API_KEY` and falls back to our **Semantic Fallback Mode** which calculates local string overlap scores against the QA datasets offline. No tokens are consumed and zero cost is incurred.

* **Q: Git clone of `en_tq` fails during bootstrapping.**
  * **A:** The system has an HTTP ZIP fallback failsafe. If `git clone` fails, it automatically downloads and extracts the ZIP archive from Door43. Ensure you have an active internet connection.

* **Q: CORS errors in the browser console.**
  * **A:** Verify that the backend is running on `127.0.0.1:8000` and the frontend is on `localhost:3000`. The FastAPI server is configured to trust these domains by default. If your frontend is running on a different port/IP, you can add it to the CORS middleware configuration in `backend/main.py`.
