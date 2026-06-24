"""
Vachan Study Bible Chatbot RAG API
FastAPI Backend serving retrieval-augmented scripture insights.
Refactored to use Clean Architecture and Hybrid Search (BM25 + Vector).
"""

import os
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')
import asyncio
import time
import json
import re
import urllib.request
import base64

from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
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
from services.rate_limiter import is_rate_limited_async, check_and_update_rate_limits_async, load_tokens_data_async, save_tokens_data_async
from services.ai_generation import generate_ai_answer, get_active_provider_async, get_llm_instance_async, transcribe_audio, rewrite_query_with_context
from services.embedding import get_embeddings_model_async
from services.retrieval import hybrid_search
from services.reranker import rerank_candidates, decide_best_match

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


# ── IP-Based Rate Limiting (per-function-instance, Vercel Free Tier safe) ──
_ip_rate_store: Dict[str, list] = {}  # {ip: [timestamp1, ...]}

def is_ip_rate_limited(ip: str, max_requests: int = 30, window: int = 60) -> bool:
    """Simple in-memory rate limiter. Resets per function cold start."""
    now = time.time()
    requests = _ip_rate_store.get(ip, [])
    requests = [t for t in requests if now - t < window]
    _ip_rate_store[ip] = requests
    if len(requests) >= max_requests:
        return True
    requests.append(now)
    return False


app = FastAPI(
    title="Vachan Study Bible Study Chatbot RAG API",
    description="FastAPI Backend serving retrieval-augmented scripture insights using Hybrid Search.",
    version="2.0.0",
)

# ── Startup diagnostics ──
_mongo_uri = os.environ.get("MONGO_URI", "")
if not _mongo_uri:
    print("STARTUP WARNING: MONGO_URI environment variable is NOT SET.", flush=True)
    print("The backend will run in DEGRADED mode (no DB, no auth, no history).", flush=True)
else:
    print(f"STARTUP: MONGO_URI is set (length {len(_mongo_uri)} chars).", flush=True)
    # Try a quick connection test
    try:
        from db.mongodb import get_database
        _test_db = get_database()
        if _test_db is not None:
            print("STARTUP: MongoDB lazy connection object created successfully.", flush=True)
        else:
            print("STARTUP: MongoDB lazy connection returned None (MONGO_URI may be invalid).", flush=True)
    except Exception as e:
        print(f"STARTUP ERROR: MongoDB connection test failed: {e}", flush=True)

# ── CORS: locked to known origins ──
_origins = get_allowed_origins()

# ALWAYS include the production frontend URL (your app won't work without this)
_prod_frontend = "https://vachan-study-chat-snpm.vercel.app"
_main_frontend = "https://vachan-study-chat.vercel.app"
if _prod_frontend not in _origins:
    _origins.append(_prod_frontend)
if _main_frontend not in _origins:
    _origins.append(_main_frontend)

# Vercel preview deployments get a dynamic URL
_vercel_env = os.environ.get("VERCEL_ENV", "")
if _vercel_env == "preview":
    preview_url = os.environ.get("VERCEL_URL", "")
    if preview_url and f"https://{preview_url}" not in _origins:
        _origins.append(f"https://{preview_url}")

# Local development: allow all localhost origins for convenience
if not os.environ.get("VERCEL") and not os.environ.get("VERCEL_ENV"):
    _local_origins = [
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:3001", "http://127.0.0.1:3001",
        "http://localhost:3002", "http://127.0.0.1:3002",
        "http://localhost:3003", "http://127.0.0.1:3003",
        "http://localhost:3004", "http://127.0.0.1:3004",
    ]
    for o in _local_origins:
        if o not in _origins:
            _origins.append(o)
    # Also include any extra origins from env
    extra = os.environ.get("ALLOWED_ORIGINS", "")
    if extra:
        for o in extra.split(","):
            o = o.strip()
            if o and o not in _origins:
                _origins.append(o)

print(f"CORS configured origins: {_origins}", flush=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def fix_vercel_path(request: Request, call_next):
    """
    Vercel strips the /api prefix when routing to api/index.py.
    This middleware prepends /api to the internal path so that
    FastAPI's @app.get("/api/...") routes match correctly in production.
    """
    if not request.scope.get("path", "").startswith("/api"):
        # Don't prepend /api for the root path so the welcome message works
        if request.scope.get("path") != "/":
            request.scope["path"] = "/api" + request.scope.get("path", "")
    return await call_next(request)

def normalize_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r'[^a-z0-9]', '', text.lower())


async def execute_with_heartbeat(coro, message: str, timeout: float = 100.0):
    """
    Executes a coroutine while yielding an SSE heartbeat every 2 seconds.
    This prevents Vercel Serverless from killing the connection during heavy tasks (like translation/LLM).
    """
    task = asyncio.create_task(coro)
    start_time = time.time()
    
    while not task.done():
        elapsed = time.time() - start_time
        if elapsed > timeout:
            task.cancel()
            raise asyncio.TimeoutError(f"Timeout: {message} took longer than {timeout}s")
            
        done, _ = await asyncio.wait([task], timeout=2.0)
        if not done:
            yield f"event: status\ndata: {message}...\n\n"
            
    yield {"result": task.result()}


def is_overview_query(query: str) -> bool:
    if not query:
        return False
    q_lower = query.lower().strip()
    patterns = [
        r'\boverview\b', r'\bsummary\b', r'\bintroduce\b',
        r'\bintroduction\b', r'\boutline\b', r'\bthemes\b', r'\bbackground\b',
        r'പശ്ചാത്തലം', r'വിവരണം', r'അവലോകനം', r'ആമുഖം', r'സംഗ്രഹം', r'ചുരുക്കം'
    ]
    for pattern in patterns:
        if re.search(pattern, q_lower):
            if not re.search(r'\b(?:ch|chapter|verse|v)\b|\d+[\s:]\d+', q_lower):
                return True
    return False


def is_diagram_query(query: str) -> bool:
    if not query: return False
    q = query.lower()
    keywords = ["diagram", "timeline", "family tree", "genealogy", "lineage", "chart", "flowchart"]
    return any(k in q for k in keywords)

async def generate_mermaid_diagram(query: str, book: str, lang_name: str, llm) -> dict:
    if not is_diagram_query(query):
        return None
        
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
async def chat_endpoint(request: ChatRequest, req: Request, current_user: Dict = Depends(get_current_active_user)):
    """SSE streaming chat endpoint. Sends real-time status events, then a final JSON result."""
    from fastapi.responses import StreamingResponse
    
    # IP-based rate limiting
    client_ip = req.headers.get("x-forwarded-for", req.client.host)
    if is_ip_rate_limited(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")
    
    async def event_stream():
      try:
        start_time = time.time()
        # Vercel Free Tier max is typically 10s to 60s depending on config.
        MAX_DURATION = float(os.environ.get("SSE_MAX_DURATION", "100.0"))
        if os.environ.get("VERCEL_ENV") not in ("production", "preview"):
            MAX_DURATION = float(os.environ.get("SSE_MAX_DURATION", "100.0"))
        print(f"SSE timeout guard: {MAX_DURATION}s", flush=True)

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

        # Use the fully async MongoDB operations (no thread pool needed, no blocking)
        rate_limited, limit_msg = await is_rate_limited_async()
        tokens_data = await load_tokens_data_async()
        tokens_used = 0
        stats = await load_tokens_data_async()

        active_provider = await get_active_provider_async()
        llm = await get_llm_instance_async(active_provider)
        embeddings_model = await get_embeddings_model_async(active_provider)
        print(f"Active provider: {active_provider}, LLM ready: {llm is not None}, Embeddings ready: {embeddings_model is not None}", flush=True)

        from app.models import ConversationState, ResponseMode
        from services.followup_detector import FollowupDetector
        from services.ai_generation import generate_ai_elaboration

        c_state = None
        if request.conversation_state:
            c_state = ConversationState.from_dict(request.conversation_state)
        elif request.history:
            # Dynamic Reconstruction for legacy requests without ConversationState
            last_user = ""
            last_asst = ""
            orig_q = ""
            for msg in request.history:
                if msg.role == "user":
                    if not orig_q:
                        orig_q = msg.content
                    last_user = msg.content
                elif msg.role == "assistant":
                    last_asst = msg.content
            c_state = ConversationState(
                original_question=orig_q or original_query,
                last_user_question=last_user or original_query,
                previous_assistant_answer=last_asst,
                dataset_answer_reference=None,
                elaboration_depth=0,
                detected_language=lang_code
            )

        # Check Dataset Fast Path (Suggested Question ID & Exact Match Lookup)
        dataset_fast_match = None
        dataset_records = DatasetRepository.load_dataset_records(book_code)
        if getattr(request, 'suggested_question_id', None):
            for rec in dataset_records:
                if rec.get("id") == request.suggested_question_id:
                    dataset_fast_match = rec
                    break
        if not dataset_fast_match:
            clean_query = original_query.strip().lower()
            for rec in dataset_records:
                if rec.get("Question", "").strip().lower() == clean_query:
                    dataset_fast_match = rec
                    break

        # FollowupDetector (Phase 1)
        if dataset_fast_match:
            is_followup = False
            followup_meta = {
                "is_followup": False,
                "intent": "none",
                "confidence": 0.0,
                "matched_layer": "none",
                "detected_language": lang_code,
                "requires_elaboration": False
            }
            print("STRUCTURED LOG [Dataset Fast Path]: Exact match found, bypassing FollowupDetector.", flush=True)
        else:
            followup_meta = FollowupDetector.detect(
                original_query=original_query,
                conversation_state=c_state,
                history=request.history,
                detected_language=lang_code
            )
            is_followup = followup_meta["is_followup"]

        print(f"STRUCTURED LOG [Follow-Up Detection]: {json.dumps(followup_meta)}", flush=True)
        if c_state:
            print(f"STRUCTURED LOG [ConversationState]: original_question='{c_state.original_question}', last_user_question='{c_state.last_user_question}', elaboration_depth={c_state.elaboration_depth}", flush=True)

        if is_followup and c_state and c_state.elaboration_depth >= 2:
            print("STRUCTURED LOG [Elaboration Depth Protection]: max_elaboration_depth=2 reached. Resetting follow-up intent to fresh generation clarification fallback.", flush=True)
            is_followup = False
            c_state.elaboration_depth = 0

        # Intercept and rewrite query using history
        active_query = original_query
        if not dataset_fast_match and (request.history or c_state) and not rate_limited and tokens_data["pending_tokens"] > 0:
            yield f"event: status\ndata: Analyzing conversation context...\n\n"
            async for item in execute_with_heartbeat(rewrite_query_with_context(original_query, request.history, llm, conversation_state=c_state, followup_metadata=followup_meta), "Analyzing context", 100.0):
                if isinstance(item, dict) and "result" in item:
                    active_query = item["result"]
                else:
                    yield item
            
            if active_query != original_query:
                print(f"Rewritten Query: '{active_query}'", flush=True)
                yield f"event: status\ndata: Understood as: '{active_query}'\n\n"

            if time.time() - start_time > MAX_DURATION:
                    error_payload = {
                        "answer": "⚠️ Request is taking too long. Please try a simpler question.",
                        "reference": "1:1",
                        "suggested_questions": ["What does this passage mean?", "How can I apply this?", "Tell me more about the context."],
                        "diagram": None,
                        "is_general_knowledge": False,
                        "tokens_used": 0,
                        "total_tokens_used": 0,
                        "pending_tokens": 0,
                        "requests_today": 0,
                        "requests_this_minute": 0,
                        "source": "ai_general",
                        "error": {"status": True, "tag": "timeout", "message": "Request took too long."}
                    }
                    yield f"event: result\ndata: {json.dumps(error_payload)}\n\n"
                    return

        # Translation & FollowupDetector (Phase 2 Enhancement)
        if lang_code != "en" and not is_followup and not rate_limited and tokens_data["pending_tokens"] > 0 and llm:
            async for item in execute_with_heartbeat(translate_to_english(active_query, llm), "Translating to English for detector enhancement", 100.0):
                if isinstance(item, dict) and "result" in item:
                    en_query_detect = item["result"]
                    followup_meta = FollowupDetector.detect(
                        original_query=original_query,
                        translated_query=en_query_detect,
                        conversation_state=c_state,
                        history=request.history,
                        detected_language=lang_code
                    )
                    is_followup = followup_meta["is_followup"]
                else:
                    yield item

        is_overview = is_overview_query(active_query)
        
        answer = ""
        top_ref = "1:1"
        source = "ai_general"
        is_general_knowledge = False
        error_obj = ChatError(status=False)
        r_mode = ResponseMode.GENERATE
        
        # Only spawn diagram generation if the query looks like it needs one
        diagram_task = None
        if is_diagram_query(active_query):
            diagram_task = asyncio.create_task(generate_mermaid_diagram(active_query, book_code, lang_name, llm))

        try:
            # Step 0: Overview Fast-Path
            if is_overview and book_code in OFFLINE_OVERVIEWS and lang_code == "en":
                yield f"event: status\ndata: Loading cached overview...\n\n"
                answer = OFFLINE_OVERVIEWS[book_code]
                source = "dataset_native"
                is_general_knowledge = True
                r_mode = ResponseMode.DIRECT_HIT
                
            # Step 0.5: Dataset Fast Path (Suggested Question ID & Exact Match Lookup)
            elif dataset_fast_match:
                yield f"event: status\ndata: ✅ Dataset fast match found...\n\n"
                answer = dataset_fast_match["Response"]
                top_ref = dataset_fast_match["Reference"]
                source = "suggested_question"
                r_mode = ResponseMode.DIRECT_HIT
                rec_id = dataset_fast_match.get("id", "unknown")
                print(f"source=suggested_question\ndataset_match=true\ndataset_id={rec_id}\nresponse_mode=direct_hit", flush=True)
                if not c_state:
                    c_state = ConversationState(original_question=original_query, last_user_question=original_query, previous_assistant_answer=answer, dataset_answer_reference=answer, elaboration_depth=0, detected_language=lang_code)
                else:
                    c_state.previous_assistant_answer = answer
                    c_state.dataset_answer_reference = answer
                    c_state.last_user_question = original_query

            # Grounding Context Assembly & Retrieval Drift Mitigation
            elif is_followup and c_state and (c_state.previous_assistant_answer or c_state.dataset_answer_reference):
                yield f"event: status\ndata: Sufficient grounding context found. Elaborating...\n\n"
                print("Retrieval Drift Mitigation: Sufficient grounding context found. Skipping fresh retrieval.", flush=True)
                r_mode = ResponseMode.ELABORATE
                async for item in execute_with_heartbeat(generate_ai_elaboration(original_query, lang_name, c_state, request.history, active_provider), "Elaborating on previous answer", 100.0):
                    if isinstance(item, dict) and "result" in item:
                        answer, ai_tokens = item["result"]
                        tokens_used += ai_tokens
                    else:
                        yield item
                source = "ai_elaboration"
                c_state.elaboration_depth += 1
                c_state.last_user_question = original_query

            else:
                # Generate Embedding for Hybrid Search
                query_embedding = []
                if embeddings_model and not rate_limited and tokens_data["pending_tokens"] > 0:
                    yield f"event: status\ndata: Generating query embedding...\n\n"
                    try:
                        async for item in execute_with_heartbeat(embeddings_model.aembed_query(active_query), "Embedding query", 10.0):
                            if isinstance(item, dict) and "result" in item:
                                query_embedding = item["result"]
                            else:
                                yield item
                    except Exception as e:
                        print(f"Embedding generation failed: {e}")
                
                if time.time() - start_time > MAX_DURATION:
                    yield f"event: error\ndata: Request is taking too long. Please try a simpler question.\n\n"
                    return
                
                # Step 1: Native Language Hybrid Search
                yield f"event: status\ndata: Searching {lang_name} dataset...\n\n"
                candidates = await hybrid_search(active_query, query_embedding, book_code, lang_code, k=10)
                
                # Step 2: Re-rank Candidates
                if candidates:
                    yield f"event: status\ndata: Ranking {len(candidates)} candidates...\n\n"
                ranked_candidates = rerank_candidates(active_query, candidates)
                
                # Step 3: Confidence Decision
                best_match, source_label, verify_tokens, r_mode = None, "no_match", 0, ResponseMode.GENERATE
                async for item in execute_with_heartbeat(decide_best_match(active_query, ranked_candidates, llm, is_followup=is_followup), "Verifying matches", 100.0):
                    if isinstance(item, dict) and "result" in item:
                        best_match, source_label, verify_tokens, r_mode = item["result"]
                    else:
                        yield item
                        
                tokens_used += verify_tokens
                
                if time.time() - start_time > MAX_DURATION:
                    yield f"event: error\ndata: Request is taking too long. Please try a simpler question.\n\n"
                    return
                
                if best_match:
                    score = best_match.get("rerank_score", 0)
                    yield f"event: status\ndata: ✅ Match found (confidence: {score:.0%})\n\n"
                    top_ref = best_match["reference"]
                    source = source_label
                    if not c_state:
                        c_state = ConversationState(original_question=original_query, last_user_question=original_query, previous_assistant_answer="", dataset_answer_reference=best_match["response"], elaboration_depth=0, detected_language=lang_code)
                    else:
                        c_state.dataset_answer_reference = best_match["response"]

                    if r_mode == ResponseMode.ELABORATE:
                        yield f"event: status\ndata: Elaborating on matched context...\n\n"
                        async for item in execute_with_heartbeat(generate_ai_elaboration(original_query, lang_name, c_state, request.history, active_provider), "Elaborating on matched context", 100.0):
                            if isinstance(item, dict) and "result" in item:
                                answer, ai_tokens = item["result"]
                                tokens_used += ai_tokens
                            else:
                                yield item
                        source = "ai_elaboration"
                        c_state.elaboration_depth += 1
                        c_state.last_user_question = original_query
                    else:
                        answer = best_match["response"]
                        c_state.previous_assistant_answer = answer
                        c_state.last_user_question = original_query
                    
                else:
                    # Step 4: Translation Fallback OR AI Generation
                    if time.time() - start_time > MAX_DURATION:
                        yield f"event: error\ndata: Request is taking too long. Please try a simpler question.\n\n"
                        return
                    
                    if lang_code != "en" and not rate_limited and tokens_data["pending_tokens"] > 0 and llm:
                        yield f"event: status\ndata: Native search missed. Attempting English fallback...\n\n"
                        print("Native search missed. Attempting English Translation Fallback...", flush=True)
                        
                        # Translate query to English
                        yield f"event: status\ndata: Translating query to English...\n\n"
                        async for item in execute_with_heartbeat(translate_to_english(active_query, llm), "Translating to English", 100.0):
                            if isinstance(item, dict) and "result" in item:
                                en_query = item["result"]
                            else:
                                yield item
                                
                        tokens_used += max(1, int(len(active_query)/4)) + 10
                        
                        # English Embedding & Hybrid Search
                        en_embedding = []
                        if embeddings_model:
                            try:
                                async for item in execute_with_heartbeat(embeddings_model.aembed_query(en_query), "Embedding English query", 10.0):
                                    if isinstance(item, dict) and "result" in item:
                                        en_embedding = item["result"]
                                    else:
                                        yield item
                            except Exception:
                                pass
                        
                        yield f"event: status\ndata: Searching English dataset...\n\n"
                        en_candidates = await hybrid_search(en_query, en_embedding, book_code, "en", k=10)
                        en_ranked = rerank_candidates(en_query, en_candidates)
                        
                        en_best, en_source, en_verify_tokens, r_mode = None, "no_match", 0, ResponseMode.GENERATE
                        async for item in execute_with_heartbeat(decide_best_match(en_query, en_ranked, llm, is_followup=is_followup), "Verifying English matches", 100.0):
                            if isinstance(item, dict) and "result" in item:
                                en_best, en_source, en_verify_tokens, r_mode = item["result"]
                            else:
                                yield item
                                
                        tokens_used += en_verify_tokens
                        
                        if time.time() - start_time > MAX_DURATION:
                            yield f"event: error\ndata: Request is taking too long. Please try a simpler question.\n\n"
                            return
                        
                        if en_best:
                            score = en_best.get("rerank_score", 0)
                            yield f"event: status\ndata: ✅ English match found (confidence: {score:.0%}). Translating to {lang_name}...\n\n"
                            print("Match found in English dataset. Translating answer to native language...")
                            async for item in execute_with_heartbeat(translate_text(en_best["response"], lang_name, llm), "Translating answer", 100.0):
                                if isinstance(item, dict) and "result" in item:
                                    translated_ans = item["result"]
                                else:
                                    yield item
                            top_ref = en_best["reference"]
                            source = "dataset_translated"
                            tokens_used += max(1, int(len(en_best["response"])/4)) + max(1, int(len(translated_ans)/4))
                            
                            if not c_state:
                                c_state = ConversationState(original_question=original_query, last_user_question=original_query, previous_assistant_answer="", dataset_answer_reference=translated_ans, elaboration_depth=0, detected_language=lang_code)
                            else:
                                c_state.dataset_answer_reference = translated_ans

                            if r_mode == ResponseMode.ELABORATE:
                                yield f"event: status\ndata: Elaborating on translated match...\n\n"
                                async for item in execute_with_heartbeat(generate_ai_elaboration(original_query, lang_name, c_state, request.history, active_provider), "Elaborating on translated match", 100.0):
                                    if isinstance(item, dict) and "result" in item:
                                        answer, ai_tokens = item["result"]
                                        tokens_used += ai_tokens
                                    else:
                                        yield item
                                source = "ai_elaboration"
                                c_state.elaboration_depth += 1
                                c_state.last_user_question = original_query
                            else:
                                answer = translated_ans
                                c_state.previous_assistant_answer = answer
                                c_state.last_user_question = original_query
                        else:
                            yield f"event: status\ndata: No dataset match. Generating AI response...\n\n"
                            print("English dataset missed. Falling back to AI Generation...")
                            async for item in execute_with_heartbeat(generate_ai_answer(active_query, lang_name, book_code, is_overview, active_provider), "Generating AI answer", 100.0):
                                if isinstance(item, dict) and "result" in item:
                                    answer, ai_tokens = item["result"]
                                else:
                                    yield item
                            source = "ai_general"
                            tokens_used += ai_tokens
                            if not c_state:
                                c_state = ConversationState(original_question=original_query, last_user_question=original_query, previous_assistant_answer=answer, dataset_answer_reference=None, elaboration_depth=0, detected_language=lang_code)
                            else:
                                c_state.previous_assistant_answer = answer
                                c_state.last_user_question = original_query
                    else:
                        # English or rate-limited: Fall back directly to AI Generation
                        if rate_limited or tokens_data["pending_tokens"] <= 0:
                            answer = "Token quota exhausted or rate limit active. Please try again later."
                            source = "dataset_native"
                        else:
                            yield f"event: status\ndata: No dataset match. Generating AI response...\n\n"
                            print("Falling back to AI Generation...")
                            async for item in execute_with_heartbeat(generate_ai_answer(active_query, lang_name, book_code, is_overview, active_provider), "Generating AI answer", 100.0):
                                if isinstance(item, dict) and "result" in item:
                                    answer, ai_tokens = item["result"]
                                else:
                                    yield item
                            source = "ai_general"
                            is_general_knowledge = True
                            tokens_used += ai_tokens
                            if not c_state:
                                c_state = ConversationState(original_question=original_query, last_user_question=original_query, previous_assistant_answer=answer, dataset_answer_reference=None, elaboration_depth=0, detected_language=lang_code)
                            else:
                                c_state.previous_assistant_answer = answer
                                c_state.last_user_question = original_query

            # Clean up disclaimers
            for d in ALL_DISCLAIMERS:
                if d in answer:
                    answer = answer.replace(d, "").strip()

            # Update Token Status
            if tokens_used > 0:
                stats = await check_and_update_rate_limits_async()
                stats["total_tokens_used"] += tokens_used
                stats["pending_tokens"] = max(0, stats["pending_tokens"] - tokens_used)
                await save_tokens_data_async(stats)

        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "503" in err_str or "unavailable" in err_str or "high traffic" in err_str or "rate-limited" in err_str or "rate_limited" in err_str:
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
        if diagram_task:
            try:
                diagram_result = await diagram_task
            except Exception as e:
                print(f"Diagram task error: {e}")

        # MongoDB Persistence (non-blocking: don't let save failure kill the response)
        try:
            await ChatSessionRepository.save_turn(book_code, original_query, answer, top_ref, source, diagram_result, user_id=current_user["username"])
        except Exception as e:
            print(f"MongoDB save_turn failed (non-fatal): {e}", flush=True)

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
            "error": {"status": error_obj.status, "tag": error_obj.tag, "message": error_obj.message},
            "conversation_state": c_state.to_dict() if c_state else None,
            "response_mode": r_mode.value if hasattr(r_mode, "value") else str(r_mode)
        }
        yield f"event: result\ndata: {json.dumps(result)}\n\n"

      except Exception as fatal_err:
        # Top-level safety net: ensure the frontend ALWAYS gets a response
        print(f"FATAL SSE ERROR: {fatal_err}", flush=True)
        error_payload = {
            "answer": "⚠️ An unexpected error occurred. Please try again later.",
            "reference": "1:1",
            "suggested_questions": ["What does this passage mean?", "How can I apply this?", "Tell me more about the context."],
            "diagram": None,
            "is_general_knowledge": False,
            "tokens_used": 0,
            "total_tokens_used": 0,
            "pending_tokens": 0,
            "requests_today": 0,
            "requests_this_minute": 0,
            "source": "ai_general",
            "error": {"status": True, "tag": "system error", "message": str(fatal_err)}
        }
        yield f"event: result\ndata: {json.dumps(error_payload)}\n\n"

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
    data = await load_tokens_data_async()
    # Dry check resets (handled in check_and_update_rate_limits, but for read-only here)
    import time
    now = time.time()
    if now - data.get("last_day_reset_time", 0.0) >= 86400:
        data["requests_today"] = 0
        data["last_day_reset_time"] = now
        data["pending_tokens"] = data["limit"]
        await save_tokens_data_async(data)
    if now - data.get("last_minute_reset_time", 0.0) >= 60:
        data["requests_this_minute"] = 0
        data["last_minute_reset_time"] = now
        await save_tokens_data_async(data)
        
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
    await save_tokens_data_async(default_data)
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
        response = JSONResponse(content=doc)
        response.headers["Cache-Control"] = "public, max-age=3600"
        return response
        
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
                    response = JSONResponse(content={
                        "book": book_code,
                        "chapter": chapter,
                        "reference": reference,
                        "verses": parsed_verses
                    })
                    response.headers["Cache-Control"] = "public, max-age=3600"
                    return response
        except Exception as e:
            print(f"Bible API Fetch Exception ({e}).")
    
    fallback = {
        "book": book_code,
        "chapter": chapter,
        "reference": f"{book.capitalize()} {chapter}",
        "verses": [
            {"verse": 1, "text": f"This is placeholder scripture context for {book.capitalize()} chapter {chapter} verse 1."},
            {"verse": 2, "text": f"This is placeholder scripture context for {book.capitalize()} chapter {chapter} verse 2."}
        ]
    }
    response = JSONResponse(content=fallback)
    response.headers["Cache-Control"] = "public, max-age=300"
    return response


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


# ── Root route ──
@app.get("/")
async def root():
    return {
        "message": "Vachan Study Bible Chatbot API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/api/health"
    }


# ── Health Check ──
@app.get("/api/health")
async def health_check():
    """Public health check endpoint for monitoring and uptime verification."""
    from db.mongodb import MONGO_URI
    db = get_database()
    db_ping = "unknown"
    if db is not None:
        try:
            # Lightweight ping to verify actual connectivity
            await db.command("ping")
            db_ping = "ok"
        except Exception as e:
            db_ping = f"error: {str(e)[:100]}"
    
    return {
        "status": "healthy" if db_ping == "ok" else "degraded",
        "version": "2.0.0",
        "database": {
            "uri_configured": bool(MONGO_URI),
            "uri_length": len(MONGO_URI) if MONGO_URI else 0,
            "connection": db_ping,
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


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


# ── Global Exception Handler ──
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catches any unhandled exception and returns a structured JSON error."""
    print(f"UNHANDLED ERROR: {exc}", flush=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    from config import HOST, PORT, RELOAD
    print(f"RAG Server V2: Starting Uvicorn on {HOST}:{PORT} (reload={RELOAD})...")
    uvicorn.run("api.index:app", host=HOST, port=PORT, reload=RELOAD)
