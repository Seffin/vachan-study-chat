"""
Vachan Study Bible Chatbot RAG API
FastAPI Backend serving retrieval-augmented scripture insights.
Refactored to use Clean Architecture and Hybrid Search (BM25 + Vector).
"""

import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone

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
from services.ai_generation import generate_ai_answer, get_active_provider, get_llm_instance, transcribe_audio
from services.embedding import get_embeddings_model
from services.retrieval import hybrid_search
from services.reranker import rerank_candidates, decide_best_match

import urllib.request
import json
import re


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
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


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
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

        is_overview = is_overview_query(original_query)
        
        answer = ""
        top_ref = "1:1"
        source = "ai_general"
        is_general_knowledge = False
        error_obj = ChatError(status=False)
        
        active_provider = get_active_provider()
        llm = get_llm_instance(active_provider)
        embeddings_model = get_embeddings_model(active_provider)

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
                        query_embedding = embeddings_model.embed_query(original_query)
                    except Exception as e:
                        print(f"Embedding generation failed: {e}")
                
                # Step 1: Native Language Hybrid Search
                yield f"event: status\ndata: Searching {lang_name} dataset...\n\n"
                candidates = await hybrid_search(original_query, query_embedding, book_code, lang_code, k=10)
                
                # Step 2: Re-rank Candidates
                if candidates:
                    yield f"event: status\ndata: Ranking {len(candidates)} candidates...\n\n"
                ranked_candidates = rerank_candidates(original_query, candidates)
                
                # Step 3: Confidence Decision
                best_match, source_label, verify_tokens = await decide_best_match(original_query, ranked_candidates, llm)
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
                        en_query = await translate_to_english(original_query, llm)
                        tokens_used += max(1, int(len(original_query)/4)) + 10
                        
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
                            answer, ai_tokens = await generate_ai_answer(original_query, lang_name, book_code, is_overview, active_provider)
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
                            answer, ai_tokens = await generate_ai_answer(original_query, lang_name, book_code, is_overview, active_provider)
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
                    asked_set.add(normalize_text(h))
            
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

        # MongoDB Persistence
        await ChatSessionRepository.save_turn(book_code, original_query, answer, top_ref, source)

        # Final result event
        result = {
            "answer": answer,
            "reference": top_ref,
            "suggested_questions": suggested[:3],
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
async def get_history(book: str):
    book_code = normalize_book_code(book)
    history = await ChatSessionRepository.get_history(book_code)
    return {"history": history}


@app.delete("/api/history/{book}")
async def delete_history(book: str):
    book_code = normalize_book_code(book)
    deleted = await ChatSessionRepository.delete_history(book_code)
    if deleted:
        return {"status": "success", "message": f"Chat history for {book} deleted successfully."}
    return {"status": "success", "message": "No chat history found to delete."}

@app.get("/api/tts")
async def text_to_speech(text: str, lang: str = "en"):
    """Generates MP3 audio using gTTS to bypass browser restrictions."""
    try:
        from fastapi.responses import StreamingResponse
        import io
        from gtts import gTTS
        
        if not text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        tts = gTTS(text=text, lang=lang, slow=False)
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        audio_fp.seek(0)
        
        return StreamingResponse(audio_fp, media_type="audio/mpeg")
    except Exception as e:
        print(f"TTS Error: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))
if __name__ == "__main__":
    import uvicorn
    from config import HOST, PORT, RELOAD
    print(f"RAG Server V2: Starting Uvicorn on {HOST}:{PORT} (reload={RELOAD})...")
    uvicorn.run("api.index:app", host=HOST, port=PORT, reload=RELOAD)
