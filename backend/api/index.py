"""
Vachan Study Bible Chatbot RAG API
FastAPI Backend serving retrieval-augmented scripture insights.
Refactored to use Clean Architecture and Hybrid Search (BM25 + Vector).
"""

import os
import sys
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends

# Auth schemes
security_scheme = HTTPBearer()

# Add backend directory to sys.path so Uvicorn can import correctly
API_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(API_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from config import get_allowed_origins, normalize_book_code, OFFLINE_OVERVIEWS, ALL_DISCLAIMERS
from db.mongodb import connect_to_mongo, close_mongo_connection, get_database
from db.repositories import ChatSessionRepository, ScriptureRepository, DatasetRepository
from schemas.requests import ChatRequest, EnvUpdateRequest
from schemas.responses import ChatResponse, ChatError, BookDatasetResponse, TokenStatusResponse

from services.translation import detect_user_language, translate_text, translate_to_english
from services.rate_limiter import is_rate_limited, check_and_update_rate_limits, load_tokens_data, save_tokens_data
from services.ai_generation import generate_ai_answer, get_active_provider, get_llm_instance, transcribe_audio, rewrite_query_with_context
from services.embedding import get_embeddings_model
from services.retrieval import hybrid_search
from services.reranker import rerank_candidates, decide_best_match

import urllib.request
import json
import re

from app.core.security import decode_token
from db.user_repository import UserRepository

async def get_current_active_user(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)):
    try:
        payload = decode_token(credentials.credentials)
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    username = payload.get("username")
    token_session_id = payload.get("session_id")
    
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token payload")
        
    # Single query: fetch user and validate session_id from same document
    user = await UserRepository.get_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    db_session_id = user.get("session_id")
    if not db_session_id or db_session_id != token_session_id:
        raise HTTPException(status_code=401, detail="Session expired or superseded")
        
    return user


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    
    # Seed default user if not exists
    from db.user_repository import UserRepository
    from app.core.security import hash_password
    default_user = await UserRepository.get_by_username("default_user")
    if not default_user:
        try:
            await UserRepository.create_user({
                "username": "default_user",
                "email": "default@example.com",
                "password": "Default@123"
            })
            print("Seeded default_user successfully.")
        except Exception as e:
            print(f"Failed to seed default_user: {e}")

    yield
    await close_mongo_connection()

app = FastAPI(
    title="Vachan Study Bible Study Chatbot RAG API",
    description="FastAPI Backend serving retrieval-augmented scripture insights using Hybrid Search.",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def normalize_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r'[^a-z0-9]', '', text.lower())


def is_overview_query(query: str) -> bool:
    if not query:
        return False
    q_lower = query.lower().strip()
    patterns = [
        r'\boverview\b', r'\bsummary\b', r'\bintroduce\b',
        r'\bintroduction\b', r'\boutline\b', r'\bthemes\b'
    ]
    for pattern in patterns:
        if re.search(pattern, q_lower):
            if not re.search(r'\b(?:ch|chapter|verse|v)\b|\d+[\s:]\d+', q_lower):
                return True
    return False


async def generate_mermaid_diagram(query: str, book: str, lang_name: str, llm) -> dict:
    if not llm:
        return None
    
    prompt = f"""Evaluate the following user query about the Bible book '{book}': "{query}"
Determine if the user is asking for:
1. A genealogy, family tree, or lineage (return "family_tree").
2. A historical timeline, overview, or writing period (return "timeline").
3. Neither (return null).

If 1 or 2, generate valid Mermaid.js code for the chart. Do NOT wrap the mermaid code in markdown code blocks. Use graph TD for family_tree and timeline for timeline.
CRITICAL: To prevent Mermaid syntax errors, ALWAYS wrap node labels in double quotes. For example, use A["Node Name (Extra info)"] instead of A[Node Name (Extra info)].
CRITICAL: All text inside the Mermaid diagram (node names, timeline events, labels) MUST be written in {lang_name}.
Return ONLY a valid JSON object in this exact format, with no markdown formatting:
{{
  "type": "family_tree" | "timeline" | null,
  "mermaid_code": "mermaid code here or null"
}}
"""
    active_provider = get_active_provider()
    if active_provider == "gemini":
        from services.key_rotation import get_key_rotator
        from google import genai
        from config import GEMINI_MODEL
        rotator = get_key_rotator()
        max_attempts = max(rotator.total_keys, 1)
        
        for attempt in range(max_attempts):
            key = rotator.get_active_key()
            if not key:
                break
            
            try:
                client = genai.Client(api_key=key)
                response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
                content = response.text.strip() if response.text else ""
                content = content.replace("```json", "").replace("```", "").strip()
                result = json.loads(content)
                rotator.report_success()
                if result.get("type") in ["family_tree", "timeline"] and result.get("mermaid_code"):
                    return result
                return None
            except Exception as e:
                err_str = str(e).lower()
                if any(k in err_str for k in ["429", "resource_exhausted", "quota", "503", "unavailable"]):
                    rotator.report_rate_limited()
                    continue
                else:
                    print(f"Mermaid generation failed: {e}")
                    break
    else:
        try:
            response = await llm.ainvoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            content = content.replace("```json", "").replace("```", "").strip()
            result = json.loads(content)
            if result.get("type") in ["family_tree", "timeline"] and result.get("mermaid_code"):
                return result
            return None
        except Exception as e:
            print(f"Mermaid generation failed: {e}")

    # Fallback diagram if API fails
    return {
        "type": "timeline",
        "mermaid_code": "graph TD\n  Error[Diagram Generation Failed] --> Cause[API High Demand / Rate Limited]\n  Cause --> Fix[Please try asking again later]"
    }



@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest, current_user: Dict = Depends(get_current_active_user)):
    """SSE streaming chat endpoint. Sends real-time status events, then a final JSON result."""
    from fastapi.responses import StreamingResponse

    async def event_stream():
        original_query = request.message.strip()
        book_code = normalize_book_code(request.book)
        
        if not original_query:
            yield f"event: error\ndata: Query message cannot be empty.\n\n"
            return
            
        print(f"API Chat Query: '{original_query}' for book '{book_code}'", flush=True)

        yield f"event: status\ndata: Detecting language...\n\n"
        lang_code, lang_name = detect_user_language(original_query)
        print(f"Detected Language: {lang_name} ({lang_code})", flush=True)
        yield f"event: status\ndata: Language detected: {lang_name}\n\n"

        rate_limited, limit_msg = is_rate_limited()
        tokens_data = load_tokens_data()
        tokens_used = 0
        stats = load_tokens_data()

        active_provider = get_active_provider()
        llm = get_llm_instance(active_provider)
        embeddings_model = get_embeddings_model(active_provider)

        # Intercept and rewrite query using history
        active_query = original_query
        if request.history and not rate_limited and tokens_data["pending_tokens"] > 0:
            yield f"event: status\ndata: Analyzing conversation context...\n\n"
            active_query = await rewrite_query_with_context(original_query, request.history, llm)
            if active_query != original_query:
                print(f"Rewritten Query: '{active_query}'", flush=True)
                yield f"event: status\ndata: Understood as: '{active_query}'\n\n"

        is_overview = is_overview_query(active_query)
        
        answer = ""
        top_ref = "1:1"
        source = "ai_general"
        is_general_knowledge = False
        error_obj = ChatError(status=False)
        
        diagram_task = asyncio.create_task(generate_mermaid_diagram(active_query, book_code, lang_name, llm))

        try:
            # Step 0: Overview Fast-Path
            if is_overview and book_code in OFFLINE_OVERVIEWS and lang_code == "en":
                yield f"event: status\ndata: Loading cached overview...\n\n"
                answer = OFFLINE_OVERVIEWS[book_code]
                source = "dataset_native"
                is_general_knowledge = True
                
            else:
                # Generate Embedding for Hybrid Search
                query_embedding = []
                if embeddings_model and not rate_limited and tokens_data["pending_tokens"] > 0:
                    yield f"event: status\ndata: Generating query embedding...\n\n"
                    try:
                        query_embedding = embeddings_model.embed_query(active_query)
                    except Exception as e:
                        print(f"Embedding generation failed: {e}")
                
                # Step 1: Native Language Hybrid Search
                yield f"event: status\ndata: Searching {lang_name} dataset...\n\n"
                candidates = await hybrid_search(active_query, query_embedding, book_code, lang_code, k=10)
                
                # Step 2: Re-rank Candidates
                if candidates:
                    yield f"event: status\ndata: Ranking {len(candidates)} candidates...\n\n"
                ranked_candidates = rerank_candidates(active_query, candidates)
                
                # Step 3: Confidence Decision
                best_match, source_label, verify_tokens = await decide_best_match(active_query, ranked_candidates, llm)
                tokens_used += verify_tokens
                
                if best_match:
                    score = best_match.get("rerank_score", 0)
                    yield f"event: status\ndata: ✅ Match found (confidence: {score:.0%})\n\n"
                    answer = best_match["response"]
                    top_ref = best_match["reference"]
                    source = source_label
                    
                else:
                    # Step 4: Translation Fallback OR AI Generation
                    if lang_code != "en" and not rate_limited and tokens_data["pending_tokens"] > 0 and llm:
                        yield f"event: status\ndata: Native search missed. Attempting English fallback...\n\n"
                        print("Native search missed. Attempting English Translation Fallback...", flush=True)
                        
                        # Translate query to English
                        yield f"event: status\ndata: Translating query to English...\n\n"
                        en_query = await translate_to_english(active_query, llm)
                        tokens_used += max(1, int(len(active_query)/4)) + 10
                        
                        # English Embedding & Hybrid Search
                        en_embedding = []
                        if embeddings_model:
                            try:
                                en_embedding = embeddings_model.embed_query(en_query)
                            except Exception:
                                pass
                        
                        yield f"event: status\ndata: Searching English dataset...\n\n"
                        en_candidates = await hybrid_search(en_query, en_embedding, book_code, "en", k=10)
                        en_ranked = rerank_candidates(en_query, en_candidates)
                        
                        en_best, en_source, en_verify_tokens = await decide_best_match(en_query, en_ranked, llm)
                        tokens_used += en_verify_tokens
                        
                        if en_best:
                            score = en_best.get("rerank_score", 0)
                            yield f"event: status\ndata: ✅ English match found (confidence: {score:.0%}). Translating to {lang_name}...\n\n"
                            print("Match found in English dataset. Translating answer to native language...")
                            answer = await translate_text(en_best["response"], lang_name, llm)
                            top_ref = en_best["reference"]
                            source = "dataset_translated"
                            tokens_used += max(1, int(len(en_best["response"])/4)) + max(1, int(len(answer)/4))
                        else:
                            yield f"event: status\ndata: No dataset match. Generating AI response...\n\n"
                            print("English dataset missed. Falling back to AI Generation...")
                            answer, ai_tokens = await generate_ai_answer(active_query, lang_name, book_code, is_overview, active_provider)
                            source = "ai_general"
                            tokens_used += ai_tokens
                    else:
                        # English or rate-limited: Fall back directly to AI Generation
                        if rate_limited or tokens_data["pending_tokens"] <= 0:
                            answer = "Token quota exhausted or rate limit active. Please try again later."
                            source = "dataset_native"
                        else:
                            yield f"event: status\ndata: No dataset match. Generating AI response...\n\n"
                            print("Falling back to AI Generation...")
                            answer, ai_tokens = await generate_ai_answer(active_query, lang_name, book_code, is_overview, active_provider)
                            source = "ai_general"
                            is_general_knowledge = True
                            tokens_used += ai_tokens

            # Clean up disclaimers
            for d in ALL_DISCLAIMERS:
                if d in answer:
                    answer = answer.replace(d, "").strip()

            # Update Token Status
            if tokens_used > 0:
                stats = check_and_update_rate_limits()
                stats["total_tokens_used"] += tokens_used
                stats["pending_tokens"] = max(0, stats["pending_tokens"] - tokens_used)
                save_tokens_data(stats)

        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "503" in err_str or "unavailable" in err_str or "high traffic" in err_str:
                error_obj = ChatError(status=True, tag="high traffic", message="The AI model is currently experiencing high demand. Please try again later.")
            elif "exhausted" in err_str or "limit" in err_str or "quota" in err_str:
                error_obj = ChatError(status=True, tag="exceed data limit", message="Your free tier data quota has been exceeded.")
            else:
                error_obj = ChatError(status=True, tag="system error", message=f"An unexpected API error occurred: {e}")
            print(f"API Chat Error Catch: {e}", flush=True)
            answer = "⚠️ " + error_obj.message
            source = "ai_general"

        # Suggested Questions
        suggested = []
        records = DatasetRepository.load_dataset_records(book_code)
        if records:
            asked_set = {normalize_text(original_query)}
            if request.history:
                for h in request.history:
                    if h.role == "user":
                        asked_set.add(normalize_text(h.content))
            
            valid_records = [r for r in records if normalize_text(r["Question"]) not in asked_set]
            
            curr_chapter = 1
            if ":" in top_ref:
                try:
                    curr_chapter = int(top_ref.split(":")[0])
                except ValueError:
                    pass
            
            chapter_records = [r for r in valid_records if r["Reference"].startswith(f"{curr_chapter}:")]
            if chapter_records:
                suggested = [x["Question"] for x in chapter_records[:3]]
            else:
                for next_ch in range(curr_chapter + 1, curr_chapter + 10):
                    next_records = [r for r in valid_records if r["Reference"].startswith(f"{next_ch}:")]
                    if next_records:
                        suggested = [x["Question"] for x in next_records[:3]]
                        break
                
                if not suggested and valid_records:
                    suggested = [x["Question"] for x in valid_records[:3]]

        if len(suggested) < 3:
            suggested = ["What does this passage mean?", "How can I apply this?", "Tell me more about the context."]

        diagram_result = None
        try:
            diagram_result = await diagram_task
        except Exception as e:
            print(f"Diagram task error: {e}")

        # MongoDB Persistence
        await ChatSessionRepository.save_turn(book_code, original_query, answer, top_ref, source, diagram_result, user_id=current_user["username"])

        # Final result event
        result = {
            "answer": answer,
            "reference": top_ref,
            "suggested_questions": suggested[:3],
            "diagram": diagram_result,
            "is_general_knowledge": is_general_knowledge,
            "tokens_used": tokens_used,
            "total_tokens_used": stats.get("total_tokens_used", 0),
            "pending_tokens": stats.get("pending_tokens", 0),
            "requests_today": stats.get("requests_today", 0),
            "requests_this_minute": stats.get("requests_this_minute", 0),
            "source": source,
            "error": {"status": error_obj.status, "tag": error_obj.tag, "message": error_obj.message}
        }
        yield f"event: result\ndata: {json.dumps(result)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/transcribe")
async def transcribe_endpoint(file: UploadFile = File(...)):
    """Accepts a multipart audio file and transcribes it using Gemini."""
    try:
        audio_bytes = await file.read()
        if not audio_bytes:
            raise ValueError("Empty audio file received. Please make sure your microphone is working.")
            
        mime_type = file.content_type or "audio/webm"
        if ";" in mime_type:
            mime_type = mime_type.split(";")[0]
            
        transcript = await transcribe_audio(audio_bytes, mime_type)
        return {"transcript": transcript}
    except Exception as e:
        print(f"Transcription Error: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dataset/{book}", response_model=BookDatasetResponse)
async def get_book_dataset(book: str):
    book_code = normalize_book_code(book).upper()
    records = DatasetRepository.load_dataset_records(book_code)
    if not records:
        raise HTTPException(status_code=404, detail=f"No dataset found for book {book_code}")
        
    return BookDatasetResponse(
        book=book_code,
        total_questions=len(records),
        data=records
    )


@app.get("/api/tokens", response_model=TokenStatusResponse)
async def get_tokens_endpoint():
    data = load_tokens_data()
    # Dry check resets (handled in check_and_update_rate_limits, but for read-only here)
    import time
    now = time.time()
    if now - data.get("last_day_reset_time", 0.0) >= 86400:
        data["requests_today"] = 0
        data["last_day_reset_time"] = now
        data["pending_tokens"] = data["limit"]
        save_tokens_data(data)
    if now - data.get("last_minute_reset_time", 0.0) >= 60:
        data["requests_this_minute"] = 0
        data["last_minute_reset_time"] = now
        save_tokens_data(data)
        
    return TokenStatusResponse(
        total_tokens_used=data["total_tokens_used"],
        pending_tokens=data["pending_tokens"],
        limit=data["limit"],
        requests_today=data["requests_today"],
        requests_this_minute=data["requests_this_minute"]
    )


@app.post("/api/tokens/reset", response_model=TokenStatusResponse)
async def reset_tokens_endpoint():
    import time
    from config import TOKEN_BUDGET_DEFAULT
    default_data = {
        "total_tokens_used": 0,
        "pending_tokens": TOKEN_BUDGET_DEFAULT,
        "limit": TOKEN_BUDGET_DEFAULT,
        "requests_today": 0,
        "requests_this_minute": 0,
        "last_minute_reset_time": time.time(),
        "last_day_reset_time": time.time()
    }
    save_tokens_data(default_data)
    return TokenStatusResponse(
        total_tokens_used=default_data["total_tokens_used"],
        pending_tokens=default_data["pending_tokens"],
        limit=default_data["limit"],
        requests_today=default_data["requests_today"],
        requests_this_minute=default_data["requests_this_minute"]
    )


@app.post("/api/settings/env")
async def update_env(request: EnvUpdateRequest):
    allowed_keys = ["OPENAI_API_KEY", "GEMINI_API_KEY", "OPENAI_MODEL", "GEMINI_MODEL"]
    if request.key not in allowed_keys:
        raise HTTPException(status_code=400, detail="Invalid environment variable key")
    
    env_path = os.path.join(BACKEND_DIR, ".env")
    try:
        from dotenv import set_key
        set_key(env_path, request.key, request.value)
    except Exception as e:
        print(f"RAG System: Failed to write to .env file ({e})")
        
    os.environ[request.key] = request.value
    return {"status": "success", "message": f"{request.key} updated successfully"}


def parse_html_to_verses(html: str) -> list:
    """Splits API.Bible HTML into verse objects."""
    matches = list(re.finditer(r'<span[^>]*data-number="(\d+)"[^>]*>.*?</span>', html))
    if not matches:
        matches = list(re.finditer(r'<span[^>]*class="v"[^>]*>(\d+)</span>', html))
        
    verses = []
    if not matches:
        clean_text = re.sub(r'<[^>]+>', ' ', html).strip()
        clean_text = re.sub(r'\s+', ' ', clean_text)
        if clean_text:
            verses.append({"verse": 1, "text": clean_text})
        return verses
        
    for i, match in enumerate(matches):
        verse_num = int(match.group(1))
        start_pos = match.end()
        end_pos = matches[i+1].start() if i + 1 < len(matches) else len(html)
        
        verse_html = html[start_pos:end_pos]
        verse_text = re.sub(r'<[^>]+>', ' ', verse_html).strip()
        verse_text = re.sub(r'\s+', ' ', verse_text)
        
        if verse_text:
            verses.append({"verse": verse_num, "text": verse_text})
    return verses


@app.get("/api/scripture/{book}/{chapter}")
async def get_scripture(book: str, chapter: int):
    book_code = normalize_book_code(book)
    
    # Mode 1: MongoDB
    doc = await ScriptureRepository.get_scripture(book_code, chapter)
    if doc:
        return doc
        
    # Mode 2: Dynamic API.Bible fetch
    from config import BIBLE_API_KEY, BIBLE_API_URL, BIBLE_ID
    if BIBLE_API_KEY:
        try:
            base_url = BIBLE_API_URL
            if "/v1" not in base_url:
                base_url = f"{base_url}/v1"
                
            api_url = f"{base_url}/bibles/{BIBLE_ID}/chapters/{book_code}.{chapter}?content-type=html&include-notes=false&include-titles=false"
            req = urllib.request.Request(
                api_url,
                headers={"api-key": BIBLE_API_KEY, "User-Agent": "VachanStudyBibleChatbot/2.0"}
            )
            
            with urllib.request.urlopen(req, timeout=8) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                
            html_content = res_data.get("data", {}).get("content", "")
            reference = res_data.get("data", {}).get("reference", f"{book_code} {chapter}")
            
            if html_content:
                parsed_verses = parse_html_to_verses(html_content)
                if parsed_verses:
                    await ScriptureRepository.cache_scripture(book_code, chapter, reference, parsed_verses)
                    return {
                        "book": book_code,
                        "chapter": chapter,
                        "reference": reference,
                        "verses": parsed_verses
                    }
        except Exception as e:
            print(f"Bible API Fetch Exception ({e}).")

    return {
        "book": book_code,
        "chapter": chapter,
        "reference": f"{book.capitalize()} {chapter}",
        "verses": [
            {"verse": 1, "text": f"This is placeholder scripture context for {book.capitalize()} chapter {chapter} verse 1."},
            {"verse": 2, "text": f"This is placeholder scripture context for {book.capitalize()} chapter {chapter} verse 2."}
        ]
    }


@app.get("/api/history/{book}")
async def get_history(book: str, current_user: Dict = Depends(get_current_active_user)):
    book_code = normalize_book_code(book)
    history = await ChatSessionRepository.get_history(book_code, user_id=current_user["username"])
    return {"history": history}


@app.delete("/api/history/{book}")
async def delete_history(book: str, current_user: Dict = Depends(get_current_active_user)):
    book_code = normalize_book_code(book)
    deleted = await ChatSessionRepository.delete_history(book_code, user_id=current_user["username"])
    if deleted:
        return {"status": "success", "message": f"Chat history for {book} deleted successfully."}
    return {"status": "success", "message": "No chat history found to delete."}

from pydantic import BaseModel

class TTSRequest(BaseModel):
    text: str

@app.post("/api/tts")
async def text_to_speech(req: TTSRequest):
    """Generates MP3 audio using gTTS to bypass browser restrictions."""
    try:
        from fastapi.responses import JSONResponse
        import io
        from gtts import gTTS
        from services.translation import detect_user_language
        
        text = req.text
        if not text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
            
        # Automatically detect language (e.g. 'ml' for Malayalam, 'hi' for Hindi)
        lang_code, _ = detect_user_language(text)
        print(f"TTS Request: Lang detected as '{lang_code}' for text: {text[:50]}...", flush=True)
        
        tts = gTTS(text=text, lang=lang_code, slow=False)
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        
        audio_data = audio_fp.getvalue()
        import base64
        b64 = base64.b64encode(audio_data).decode("utf-8")
        print(f"TTS Generated successfully. Base64 length: {len(b64)} bytes.", flush=True)
        
        return {"audio_base64": b64}
    except Exception as e:
        print(f"TTS Error: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------------------------
# Auth Endpoints (Migrated from app.routes.auth)
# ---------------------------------------------------------------------------

from pydantic import BaseModel, EmailStr
from app.core.security import (
    verify_password, create_access_token, create_session_id,
    check_rate_limit, record_failed_attempt, clear_rate_limit, decode_token
)
from db.user_repository import UserRepository

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

@app.post("/api/auth/login")
async def login_endpoint(request: LoginRequest):
    if not request.username or not request.password:
        raise HTTPException(status_code=400, detail="Username and password required")
    
    if len(request.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
        
    if not check_rate_limit(request.username):
        raise HTTPException(status_code=429, detail="Too many failed login attempts. Please try again later.")
        
    user = await UserRepository.get_by_username(request.username)
    if not user or not verify_password(request.password, user.get("password_hash", "")):
        record_failed_attempt(request.username)
        raise HTTPException(status_code=401, detail={"error": "Invalid username or password"})
        
    clear_rate_limit(request.username)
    
    # Session management
    session_id = create_session_id()
    await UserRepository.update_session_id(request.username, session_id)
    
    token_payload = {
        "user_id": str(user["_id"]),
        "username": user["username"],
        "session_id": session_id
    }
    
    access_token = create_access_token(data=token_payload)
    
    # Simple audit log
    db = get_database()
    if db is not None:
        await db.login_audit.insert_one({
            "username": request.username,
            "timestamp": datetime.now(timezone.utc),
            "status": "success"
        })
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "username": user["username"],
            "user_id": str(user["_id"])
        }
    }


@app.post("/api/auth/register", status_code=201)
async def register_endpoint(request: RegisterRequest):
    existing_user = await UserRepository.get_by_username(request.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
        
    user_data = {
        "username": request.username,
        "email": request.email,
        "password": request.password
    }
    
    created_user = await UserRepository.create_user(user_data)
    
    return {
        "user_id": str(created_user["_id"]),
        "username": created_user["username"],
        "email": created_user["email"]
    }



@app.get("/api/auth/me")
async def get_me_endpoint(current_user: Dict = Depends(get_current_active_user)):
    return {
        "user_id": str(current_user["_id"]),
        "username": current_user["username"],
        "email": current_user.get("email", "")
    }


@app.post("/api/auth/logout")
async def logout_endpoint(current_user: Dict = Depends(get_current_active_user)):
    await UserRepository.clear_session(current_user["username"])
    return {"status": "success", "message": "Logged out"}

if __name__ == "__main__":
    import uvicorn
    from config import HOST, PORT, RELOAD
    print(f"RAG Server V2: Starting Uvicorn on {HOST}:{PORT} (reload={RELOAD})...")
    uvicorn.run("api.index:app", host=HOST, port=PORT, reload=RELOAD)
