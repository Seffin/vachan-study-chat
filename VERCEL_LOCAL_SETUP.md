# Local Vercel Simulation & Vercel Support Guide

This guide explains how to run the application locally in the exact same environment as Vercel, allowing you to test changes, and how Vercel manages the backend.

---

## 1. Simulating Vercel Mode Locally

To run the backend locally in Vercel mode (read-only filesystem with `/tmp` caching and in-memory fallback), do the following:

### Step 1: Update `.env` or Environment Variables
Set the environment variable `VERCEL=1` in your command line or add it to your local environment file:

```env
# backend/.env or your terminal environment
VERCEL=1
```

### Step 2: Start the Backend
Start the FastAPI server normally:
```bash
cd backend
venv\Scripts\python api/index.py
```
* **What happens now:** The backend detects `VERCEL=1` and dynamically maps the `tokens.json` data path to `/tmp/tokens.json`.
* **Testing on Windows:** On Windows, the folder `C:\tmp` or `H:\tmp` (depending on your workspace drive) will be automatically created to emulate the Vercel ephemeral temporary store.

---

## 2. Vercel Serverless Architecture & Quota Tracking

When deployed to Vercel, the application operates as an ephemeral serverless function:

### File Write Rules in Vercel
* **Read-Only Root:** The entire directory structure of your deployed project is read-only.
* **Writable `/tmp`:** The only writable directory is `/tmp`.

### How Token Status is Managed on Vercel
1. **Initial Status Check (`GET /api/tokens`):**
   - The serverless function reads `/tmp/tokens.json`.
   - If `/tmp/tokens.json` does not exist (e.g. on container cold start), it initializes it with default values: **1,000,000 pending tokens** and **0 used tokens**.
2. **Deductions (`POST /api/chat`):**
   - When a request is completed, the tokens returned by Gemini are subtracted from `/tmp/tokens.json`.
3. **In-Memory Fallback:**
   - If writing or reading `/tmp/tokens.json` encounters any unexpected error or permission restriction, the backend automatically stores the metrics in-memory without throwing a 500 error.
4. **Ephemeral Nature:**
   - Note that because Vercel Serverless Functions spin up and down dynamically, `/tmp/tokens.json` and in-memory caches are ephemeral. The token limit will reset to default limits (1,000,000) when the serverless container recycles or scale-up creates new instances.
