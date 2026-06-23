# GitHub Issues for Vachan Study Hosting Improvements

This document contains all the improvements made and suggested for the Vercel Free Tier deployment. You can copy-paste these into GitHub Issues, or run the `curl` commands at the bottom after creating a GitHub Personal Access Token.

---

## Issue 1: [DONE] Remove `lifespan` context manager to reduce cold start latency

**Priority:** Critical  
**Status:** ✅ Completed in `backend/api/index.py`

### Problem
The `lifespan` context manager in `api/index.py` connected to MongoDB and seeded a default user on every cold start. This added 1–3 seconds of latency before the first API response in Vercel's serverless environment.

### Fix Applied
- Removed the `lifespan` async context manager entirely.
- Removed `lifespan=lifespan` from `FastAPI()` initialization.
- MongoDB now connects lazily via `get_database()` only when needed.
- Default user seeding should be a one-time migration script.

### Files Changed
- `backend/api/index.py`

---

## Issue 2: [DONE] Lock CORS to specific frontend origin

**Priority:** Critical  
**Status:** ✅ Completed in `backend/api/index.py`

### Problem
`allow_origins=["*"]` allowed any website on the internet to call the API. Combined with no per-IP rate limiting, this exposed the backend to abuse.

### Fix Applied
```python
_origins = get_allowed_origins()
if os.environ.get("VERCEL_ENV") == "production":
    _origins = ["https://vachan-study-chat-snpm.vercel.app"]
else:
    if "https://vachan-study-chat-snpm.vercel.app" not in _origins:
        _origins.append("https://vachan-study-chat-snpm.vercel.app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Files Changed
- `backend/api/index.py`

---

## Issue 3: [DONE] Add 8-second timeout guard to `/api/chat` SSE endpoint

**Priority:** Critical  
**Status:** ✅ Completed in `backend/api/index.py`

### Problem
The `/api/chat` SSE endpoint makes up to 6 sequential LLM calls (query rewrite → embedding → hybrid search → decide best match → translation fallback → AI generation). On Vercel Free Tier (10s timeout), this frequently causes 504 Gateway Timeouts.

### Fix Applied
- Added `start_time = time.time()` and `MAX_DURATION = 8.0` at the beginning of the SSE stream.
- Added timeout checks after every expensive operation:
  - After query rewrite with context
  - After embedding generation
  - After `decide_best_match`
  - After English translation fallback's `decide_best_match`
  - Before translation fallback and AI generation
- If timeout is exceeded, yields an SSE error event and returns gracefully.

### Files Changed
- `backend/api/index.py`

---

## Issue 4: [DONE] Add IP-based rate limiting to API endpoints

**Priority:** Critical  
**Status:** ✅ Completed in `backend/api/index.py`

### Problem
No per-IP rate limiting existed. A malicious user or bot could hit `/api/chat` thousands of times and exhaust the free Gemini tier (15 RPM / 1500 RPD).

### Fix Applied
- Added simple in-memory IP rate limiter: 30 requests per 60 seconds per IP.
- Resets per Vercel function cold start (acceptable for free tier).
- Applied to `/api/chat` endpoint specifically.

```python
_ip_rate_store: Dict[str, list] = {}

def is_ip_rate_limited(ip: str, max_requests: int = 30, window: int = 60) -> bool:
    now = time.time()
    requests = _ip_rate_store.get(ip, [])
    requests = [t for t in requests if now - t < window]
    _ip_rate_store[ip] = requests
    if len(requests) >= max_requests:
        return True
    requests.append(now)
    return False
```

### Files Changed
- `backend/api/index.py`

### Future Work
Consider applying the same rate limiting to `/api/transcribe` and `/api/tts`.

---

## Issue 5: [DONE] Add `/api/health` health check endpoint

**Priority:** Medium  
**Status:** ✅ Completed in `backend/api/index.py`

### Problem
No health check endpoint existed for monitoring tools (e.g., UptimeRobot, Pingdom) to verify the backend is alive.

### Fix Applied
```python
@app.get("/api/health")
async def health_check():
    db = get_database()
    db_status = "connected" if db else "disconnected"
    return {
        "status": "healthy" if db else "degraded",
        "version": "2.0.0",
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
```

### Files Changed
- `backend/api/index.py`

---

## Issue 6: [DONE] Add HTTP caching headers to `/api/scripture`

**Priority:** Medium  
**Status:** ✅ Completed in `backend/api/index.py`

### Problem
The `/api/scripture/{book}/{chapter}` endpoint re-fetched scripture from API.Bible or MongoDB on every request. Scripture text is immutable, so caching is safe and reduces redundant API calls.

### Fix Applied
- Added `Cache-Control: public, max-age=3600` (1 hour) to MongoDB hit responses.
- Added `Cache-Control: public, max-age=3600` to API.Bible fetched responses.
- Added `Cache-Control: public, max-age=300` (5 min) to fallback placeholder responses.

### Files Changed
- `backend/api/index.py`

---

## Issue 7: [DONE] Add global exception handler

**Priority:** Medium  
**Status:** ✅ Completed in `backend/api/index.py`

### Problem
Unhandled exceptions in FastAPI would return a raw HTML 500 error instead of a structured JSON response, making frontend error handling difficult.

### Fix Applied
```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"UNHANDLED ERROR: {exc}", flush=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )
```

### Files Changed
- `backend/api/index.py`

---

## Issue 8: [DONE] Update `vercel.json` to remove deprecated `builds` syntax

**Priority:** Low  
**Status:** ✅ Completed

### Problem
The `vercel.json` used the deprecated `builds` array:
```json
"builds": [{"src": "api/index.py", "use": "@vercel/python"}]
```

### Fix Applied
Replaced with the modern `routes`-only syntax. Vercel auto-detects Python files in `api/`.
```json
{
  "version": 2,
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "api/index.py"
    }
  ]
}
```

### Files Changed
- `backend/vercel.json`

---

## Issue 9: [DONE] Add `runtime.txt` for Python 3.12

**Priority:** Low  
**Status:** ✅ Completed

### Problem
Vercel defaults to Python 3.9 for serverless functions. The codebase may use Python 3.12+ features.

### Fix Applied
Created `backend/runtime.txt`:
```
python-3.12.0
```

### Files Changed
- `backend/runtime.txt` (new file)

---

## Issue 10: [DONE] Optimize `next.config.ts` for Vercel production

**Priority:** Low  
**Status:** ✅ Completed

### Problem
`next.config.ts` had no production optimizations (`compress`, `productionBrowserSourceMaps`, `images`, `reactCompiler`).

### Fix Applied
```typescript
const nextConfig: NextConfig = {
  allowedDevOrigins: ["192.168.1.101", "192.168.1.102", "192.168.1.104", "localhost", "127.0.0.1"],
  compress: true,
  productionBrowserSourceMaps: false,
  images: {
    remotePatterns: [{ protocol: "https", hostname: "**.vercel.app" }],
  },
  experimental: {
    reactCompiler: true,
  },
};
```

### Files Changed
- `next.config.ts`

---

## Issue 15: [DONE] Fix Vercel 504 Timeout via SSE Heartbeats & Async Generation

**Priority:** Critical  
**Status:** ✅ Completed

### Problem
The frontend UI was silently hanging and crashing during complex fallback generation (like Malayalam translation). This was caused by Vercel Serverless killing the HTTP connection prematurely, either due to idle timeout (no data sent) or because the internal limits were too restrictive (15s).

### Fix Applied
- Implemented `execute_with_heartbeat()` wrapper to yield an SSE `event: status` every 2 seconds, keeping the Vercel connection alive and defeating the idle timeout.
- Wrapped all LangChain and native generation calls in `asyncio.wait_for` with extended 30s–50s timeouts.
- Patched the frontend SSE stream parser in `Workspace.tsx` to handle `event: result` error payloads safely instead of silently dying when timeouts occur.

### Files Changed
- `backend/api/index.py`
- `backend/services/ai_generation.py`
- `backend/services/translation.py`
- `src/components/Workspace.tsx`

---

## Issue 11: [FUTURE] Upgrade to Vercel Pro for longer timeouts

**Priority:** High (when traffic grows)  
**Status:** ⏳ Deferred

### Problem
Vercel Free Tier has a 10-second function timeout. The RAG pipeline sometimes needs 12–18 seconds for complex queries (translation fallback + AI generation).

### Recommendation
Upgrade to **Vercel Pro ($20/month)** to get:
- 60-second function timeout
- `maxDuration: 60` configuration
- More bandwidth and concurrent functions

### Alternative (Free Tier)
Keep the 8-second timeout guard and optimize the pipeline further (see Issue 12).

---

## Issue 12: [FUTURE] Optimize RAG pipeline to reduce LLM calls

**Priority:** High  
**Status:** ⏳ Deferred

### Problem
Even with the 8-second guard, the pipeline still tries 6+ LLM calls. This is wasteful and slow.

### Suggestions
1. **Skip `rewrite_query_with_context`** on free tier — saves 1–2s.
2. **Skip `generate_mermaid_diagram`** on free tier — saves 1–2s. Make it a background task or skip entirely.
3. **Cache embeddings** in MongoDB for common queries to avoid re-embedding.
4. **Precompute cross-encoder scores** for the top 100 most common questions per book.
5. **Use a smaller/faster LLM** for translation and query rewrite (e.g., `gemini-1.5-flash-8b`).

---

## Issue 13: [FUTURE] Add Redis for distributed rate limiting

**Priority:** Medium  
**Status:** ⏳ Deferred

### Problem
The current IP rate limiter is in-memory and resets on every Vercel function cold start. A determined attacker can still exhaust quota by hitting different cold starts.

### Recommendation
Use **Upstash Redis** (free tier: 10,000 requests/day) or **Vercel KV** for distributed rate limiting that persists across function instances.

---

## Issue 14: [FUTURE] Add structured logging with Logflare or Sentry

**Priority:** Medium  
**Status:** ⏳ Deferred

### Problem
Errors are only visible via `print()` statements in Vercel logs, which expire quickly and are hard to search.

### Recommendation
- **Logflare** (free tier) for searchable log aggregation.
- **Sentry** (free for small projects) for error tracking and alerting.

---

# How to Create These Issues on GitHub

## Option A: Manual Copy-Paste
1. Go to https://github.com/Seffin/vachan-study-chat/issues
2. Click "New issue"
3. Copy-paste each issue title and body from above.

## Option B: Using `curl` (requires GitHub Personal Access Token)

1. Create a GitHub Personal Access Token at https://github.com/settings/tokens
2. Run the commands below in a terminal with `curl`:

```bash
export GITHUB_TOKEN="your_token_here"
export REPO="Seffin/vachan-study-chat"

# Issue 1: Remove lifespan
curl -X POST https://api.github.com/repos/$REPO/issues \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "[DONE] Remove lifespan context manager to reduce cold start latency",
    "body": "Removed the `lifespan` async context manager from `backend/api/index.py`. MongoDB now connects lazily via `get_database()`. This eliminates 1-3 seconds of cold start latency on Vercel serverless.",
    "labels": ["enhancement", "vercel", "done"]
  }'

# Issue 2: Lock CORS
curl -X POST https://api.github.com/repos/$REPO/issues \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "[DONE] Lock CORS to specific frontend origin",
    "body": "Replaced `allow_origins=[\"*\"]` with a locked list that only includes the frontend domain (`https://vachan-study-chat-snpm.vercel.app`) in production. This prevents unauthorized API access from third-party sites.",
    "labels": ["security", "vercel", "done"]
  }'

# Issue 3: Timeout guard
curl -X POST https://api.github.com/repos/$REPO/issues \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "[DONE] Add 8-second timeout guard to /api/chat SSE endpoint",
    "body": "Added `MAX_DURATION = 8.0` hard stop inside the SSE stream to prevent Vercel Free Tier 10-second timeouts. Checks are inserted after query rewrite, embedding generation, decide_best_match, and translation fallback.",
    "labels": ["enhancement", "vercel", "done"]
  }'

# Issue 4: IP rate limiting
curl -X POST https://api.github.com/repos/$REPO/issues \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "[DONE] Add IP-based rate limiting to API endpoints",
    "body": "Added a simple in-memory IP rate limiter (30 req / 60 sec) to the `/api/chat` endpoint. Resets per function cold start, which is acceptable for Vercel Free Tier. Prevents quota exhaustion from abuse.",
    "labels": ["security", "vercel", "done"]
  }'

# Issue 5: Health check
curl -X POST https://api.github.com/repos/$REPO/issues \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "[DONE] Add /api/health health check endpoint",
    "body": "Added a public `/api/health` endpoint that returns status, version, database connection status, and timestamp. Useful for uptime monitoring tools like UptimeRobot or Pingdom.",
    "labels": ["enhancement", "vercel", "done"]
  }'

# Issue 6: Scripture caching
curl -X POST https://api.github.com/repos/$REPO/issues \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "[DONE] Add HTTP caching headers to /api/scripture",
    "body": "Added `Cache-Control: public, max-age=3600` to scripture responses. Since Bible text is immutable, this reduces redundant MongoDB/API.Bible calls and improves response times.",
    "labels": ["enhancement", "performance", "done"]
  }'

# Issue 7: Global exception handler
curl -X POST https://api.github.com/repos/$REPO/issues \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "[DONE] Add global exception handler",
    "body": "Added a FastAPI `@app.exception_handler(Exception)` that catches all unhandled exceptions and returns a structured JSON error response instead of raw HTML 500.",
    "labels": ["enhancement", "done"]
  }'

# Issue 8: Update vercel.json
curl -X POST https://api.github.com/repos/$REPO/issues \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "[DONE] Update vercel.json to remove deprecated builds syntax",
    "body": "Replaced deprecated `builds` array with modern `routes`-only syntax. Vercel auto-detects Python files in `api/` directory.",
    "labels": ["enhancement", "vercel", "done"]
  }'

# Issue 9: runtime.txt
curl -X POST https://api.github.com/repos/$REPO/issues \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "[DONE] Add runtime.txt for Python 3.12",
    "body": "Created `backend/runtime.txt` with `python-3.12.0` to ensure Vercel uses Python 3.12 instead of the default 3.9.",
    "labels": ["enhancement", "vercel", "done"]
  }'

# Issue 10: next.config.ts
curl -X POST https://api.github.com/repos/$REPO/issues \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "[DONE] Optimize next.config.ts for Vercel production",
    "body": "Added `compress`, `productionBrowserSourceMaps`, `images.remotePatterns`, and `experimental.reactCompiler` to `next.config.ts` for better production performance.",
    "labels": ["enhancement", "performance", "done"]
  }'

# Issue 11: Vercel Pro upgrade
curl -X POST https://api.github.com/repos/$REPO/issues \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "[FUTURE] Upgrade to Vercel Pro for longer timeouts",
    "body": "Vercel Free Tier has a 10-second function timeout. The RAG pipeline sometimes needs 12-18 seconds for complex queries. Upgrading to Vercel Pro ($20/month) would unlock 60-second timeouts and `maxDuration: 60` configuration.",
    "labels": ["enhancement", "future", "vercel"]
  }'

# Issue 12: Optimize RAG pipeline
curl -X POST https://api.github.com/repos/$REPO/issues \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "[FUTURE] Optimize RAG pipeline to reduce LLM calls",
    "body": "The pipeline currently makes 6+ LLM calls per query. Suggestions: skip query rewrite on free tier, skip mermaid diagrams, cache embeddings in MongoDB, precompute cross-encoder scores for common questions, use a faster LLM for translation.",
    "labels": ["enhancement", "future", "performance"]
  }'

# Issue 13: Redis rate limiting
curl -X POST https://api.github.com/repos/$REPO/issues \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "[FUTURE] Add Redis for distributed rate limiting",
    "body": "The current in-memory IP rate limiter resets on every Vercel cold start. Consider Upstash Redis or Vercel KV for persistent, distributed rate limiting across function instances.",
    "labels": ["enhancement", "future", "security"]
  }'

# Issue 14: Structured logging
curl -X POST https://api.github.com/repos/$REPO/issues \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "[FUTURE] Add structured logging with Logflare or Sentry",
    "body": "Errors currently only appear in Vercel logs via `print()`. Consider integrating Logflare (free tier) for searchable log aggregation or Sentry (free for small projects) for error tracking and alerting.",
    "labels": ["enhancement", "future", "monitoring"]
  }'
# Issue 15: Fix Vercel 504 Timeout via SSE Heartbeats & Async
curl -X POST https://api.github.com/repos/$REPO/issues \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "[DONE] Fix Vercel 504 Timeout via SSE Heartbeats & Async Generation",
    "body": "Fixed the silent UI hanging issue caused by Vercel 504 Gateway Timeouts. Added an `execute_with_heartbeat` wrapper that yields an SSE `event: status` every 2 seconds to keep the Vercel connection alive during long LLM calls. Wrapped all LangChain and native generation calls in strict 30s/50s timeouts. Fixed frontend SSE parser to safely handle `event: result` error payloads instead of freezing when limits are hit.",
    "labels": ["bug", "vercel", "done"]
  }'
```

---

# Issue 16: Fix Vercel 500 — Stale `app/main.py` circular import crash

curl -X POST https://api.github.com/repos/$REPO/issues \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "[DONE] Fix Vercel 500 — Stale app/main.py circular import crash",
    "body": "Vercel logs showed `ImportError: cannot import name app from app.main` because the deployed build still contained a stale `app/main.py` that created a circular import with `app/__init__.py`. Fixed by explicitly declaring `api/index.py` as the sole entry point in `vercel.json` via the `functions` key, preventing Vercel from auto-detecting the old `app/main.py`. See VERCEL_DEPLOY_FIX.md for full redeploy steps.",
    "labels": ["bug", "vercel", "done"]
  }'
```

---

*Generated by Kimi Work — Vachan Study Vercel Hosting Audit*
