"""
Chat routes for Bible study interactions.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from app.core.security import get_current_user
from schemas.requests import ChatRequest
from db.mongodb import get_database
from db.repositories import ChatSessionRepository, DatasetRepository
from config import normalize_book_code, RERANK_HIGH_THRESHOLD, RERANK_MEDIUM_THRESHOLD

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("/", response_model=Dict[str, Any])
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Process a chat message and return AI response.

    Requires authentication via JWT token.
    """
    original_query = request.message.strip()
    book_code = normalize_book_code(request.book)

    if not original_query:
        raise HTTPException(status_code=400, detail="Query message cannot be empty.")

    # 1. Language detection
    try:
        from services.translation import detect_user_language
        lang_code, lang_name = detect_user_language(original_query)
    except Exception:
        lang_code, lang_name = "en", "English"

    # 2. Get active provider and embedding model
    from services.ai_generation import get_active_provider, get_llm_instance
    from services.embedding import get_embeddings_model
    from services.retrieval import hybrid_search
    from services.reranker import rerank_candidates, decide_best_match

    active_provider = get_active_provider()
    llm = get_llm_instance(active_provider)
    embeddings_model = get_embeddings_model(active_provider)

    answer = ""
    top_ref = "1:1"
    source = "ai_general"
    tokens_used = 0

    try:
        # 3. Generate embedding and run hybrid search
        query_embedding = []
        if embeddings_model:
            try:
                query_embedding = embeddings_model.embed_query(original_query)
            except Exception as e:
                print(f"Embedding generation failed: {e}")

        candidates = await hybrid_search(original_query, query_embedding, book_code, lang_code, k=10)

        # 4. Re-rank
        ranked = rerank_candidates(original_query, candidates)

        # 5. Decide best match
        best_match, source_label, verify_tokens = await decide_best_match(original_query, ranked, llm)
        tokens_used += verify_tokens

        if best_match:
            answer = best_match["response"]
            top_ref = best_match.get("reference", "1:1")
            source = source_label
        else:
            # Fallback: AI generation
            if llm and lang_code != "en":
                # Try English translation fallback
                try:
                    from services.translation import translate_to_english
                    en_query = await translate_to_english(original_query, llm)
                    en_embedding = embeddings_model.embed_query(en_query) if embeddings_model else []
                    en_candidates = await hybrid_search(en_query, en_embedding, book_code, "en", k=10)
                    en_ranked = rerank_candidates(en_query, en_candidates)
                    en_best, en_source, en_tokens = await decide_best_match(en_query, en_ranked, llm)
                    tokens_used += en_tokens

                    if en_best:
                        from services.translation import translate_text
                        answer = await translate_text(en_best["response"], lang_name, llm)
                        top_ref = en_best.get("reference", "1:1")
                        source = "dataset_translated"
                        tokens_used += max(1, int(len(en_best["response"]) / 4)) + max(1, int(len(answer) / 4))
                    else:
                        raise Exception("No English match")
                except Exception:
                    from services.ai_generation import generate_ai_answer
                    answer, ai_tokens = await generate_ai_answer(original_query, lang_name, book_code, False, active_provider)
                    source = "ai_general"
                    tokens_used += ai_tokens
            else:
                from services.ai_generation import generate_ai_answer
                answer, ai_tokens = await generate_ai_answer(original_query, lang_name, book_code, False, active_provider)
                source = "ai_general"
                tokens_used += ai_tokens

    except Exception as e:
        print(f"Chat error: {e}")
        answer = "⚠️ An error occurred while processing your question. Please try again."
        source = "ai_general"

    # 6. Generate suggested questions
    suggested = []
    records = DatasetRepository.load_dataset_records(book_code)
    if records:
        asked_set = {original_query.lower().strip()}
        valid_records = [r for r in records if r["Question"].lower().strip() not in asked_set]
        if valid_records:
            suggested = [r["Question"] for r in valid_records[:3]]

    if len(suggested) < 3:
        suggested = ["What does this passage mean?", "How can I apply this?", "Tell me more about the context."]

    # 7. Save to MongoDB
    user_id = current_user.get("username", "unknown")
    await ChatSessionRepository.save_turn(book_code, original_query, answer, top_ref, source, diagram=None, user_id=user_id)

    return {
        "response": answer,
        "book": book_code,
        "source": source,
        "reference": top_ref,
        "verses_highlighted": [top_ref.split(":")[1]] if ":" in top_ref else [],
        "diagram": None,
        "suggested_questions": suggested[:3],
    }


@router.get("/history/{book_code}")
async def get_history(
    book_code: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get chat history for a specific book.

    Requires authentication via JWT token.
    """
    user_id = current_user.get("username", "unknown")
    history = await ChatSessionRepository.get_history(book_code, user_id=user_id)
    return {"history": history}
