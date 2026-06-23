# Vachan Study — Vercel Deployment Fix Log

## Error Diagnosed (Vercel Logs)

```
500: INTERNAL_SERVER_ERROR
Code: FUNCTION_INVOCATION_FAILED

Traceback:
  File "/var/task/app/main.py", line 8, in <module>
    from .core.config import settings
  File "/var/task/app/__init__.py", line 3, in <module>
    from .main import app
ImportError: cannot import name 'app' from 'app.main'
```

## Root Cause

**Vercel is trying to import `app/main.py` as the Python entry point** instead of `api/index.py`. This file was removed from the repo in commit `bc17ac7`, but the deployed Vercel build still has it (cached or stale deployment).

The `app/main.py` file has a circular import:
- `app/main.py` imports `app.core.config`
- `app.core.config` triggers `app/__init__`
- `app/__init__` imports `app.main` (circular!)
- `app` doesn't exist yet → crash

## Fix Applied

### 1. `vercel.json` — Explicit entry point declaration

```json
{
  "version": 2,
  "functions": {
    "api/index.py": {
      "maxDuration": 60
    }
  },
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "/api/index.py"
    }
  ]
}
```

The `functions` key tells Vercel to explicitly use `api/index.py` as the serverless function entry point. The `maxDuration: 60` allows 60-second requests (Vercel Pro required).

### 2. `api/index.py` — Defensive startup wrapper (if deployed)

If `app/main.py` is still found by Vercel, the code should not crash on import. The defensive wrapper catches any import failure and creates a fallback FastAPI app that returns the actual error message instead of a generic 500.

### 3. Environment Variables Required in Vercel

| Variable | Value | Required For |
|----------|-------|-------------|
| `MONGO_URI` | `mongodb+srv://...` | Database, auth, history, key rotation |
| `SECRET_KEY` | Random 64-char hex | JWT token signing |
| `ALLOWED_ORIGINS` | `https://vachan-study-chat-snpm.vercel.app` | CORS (frontend URL) |
| `SSE_MAX_DURATION` | `10` | SSE timeout (optional, defaults to 8s on Vercel) |

### 4. MongoDB Atlas Network Access

Go to MongoDB Atlas → Network Access → Add IP Address → `0.0.0.0/0`

Vercel serverless functions run on AWS Lambda with dynamic IPs. Without this, MongoDB connection will timeout and all endpoints return 500.

## Redeploy Steps

1. **Commit and push the latest code**
   ```bash
   git add backend/vercel.json backend/api/index.py
   git commit -m "fix(vercel): explicit entry point api/index.py, remove stale app/main.py reference"
   git push origin main
   ```

2. **If push fails (DNS/SSH issue):**
   - Use GitHub Desktop, or
   - Create a GitHub Personal Access Token at https://github.com/settings/tokens
   - Use HTTPS: `git push https://<token>@github.com/Seffin/vachan-study-chat.git main`

3. **Verify Vercel auto-deploy**
   - Go to [vercel.com](https://vercel.com) → your backend project → Deployments
   - Check that the latest commit is building
   - If stuck, click "Redeploy" manually

4. **Test after deploy**
   ```bash
   curl https://vachan-study-chat.vercel.app/
   # Should return: {"message": "Vachan Study Bible Chatbot API", ...}

   curl https://vachan-study-chat.vercel.app/api/health
   # Should return: {"status": "healthy", "database": {"connection": "ok"}, ...}
   ```

## If the Error Persists

**Check Vercel project settings:**
1. Go to Vercel Dashboard → your backend project → Settings
2. **Framework Preset:** Set to "Other" (not Python)
3. **Root Directory:** Make sure it's `backend` (or `.` if deploying from root)
4. **Build Command:** Leave empty (or `echo "Build skipped"`)
5. **Output Directory:** Leave empty

**Clear Vercel build cache:**
1. Go to Project Settings → Git
2. Disconnect and reconnect the GitHub repo
3. Or add a new empty commit: `git commit --allow-empty -m "trigger: clear build cache" && git push`

## Files Changed in This Fix

| File | Change |
|------|--------|
| `backend/vercel.json` | Added `functions` key, explicit `api/index.py` entry point, `maxDuration: 60` |
| `backend/api/index.py` | Defensive import wrapper with fallback error app |
| `GITHUB_ISSUES.md` | Updated with this deployment fix log |

---

*Last updated: After Vercel 500 diagnosis — circular import in stale `app/main.py`*
