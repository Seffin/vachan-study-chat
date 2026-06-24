"""
Vachan Study Bible Chatbot — Re-ranker Service
Handles Cross-Encoder re-ranking and LLM semantic verification.
"""

import re
from typing import List, Dict, Any, Optional
from config import RERANK_HIGH_THRESHOLD, RERANK_MEDIUM_THRESHOLD


def rerank_candidates(query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Re-ranks search candidates using a Cross-Encoder model.
    
    This function currently serves as a placeholder for a self-hosted BGE-Reranker.
    If a reranker is not available, it uses the real Atlas Vector Search score
    to determine confidence, allowing high-scoring matches to bypass LLM verification.
    """
    if not candidates:
        return []
        
    # Placeholder for self-hosted bge-reranker-v2-m3
    # try:
    #     from sentence_transformers import CrossEncoder
    #     model = CrossEncoder('BAAI/bge-reranker-v2-m3')
    #     pairs = [[query, c["question"]] for c in candidates]
    #     scores = model.predict(pairs)
    #     for i, c in enumerate(candidates):
    #         c["rerank_score"] = float(scores[i])
    #     candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
    #     return candidates
    # except ImportError:
    #     pass
    
    # Use the real Atlas Vector Search score if available.
    # This allows high-confidence matches (≥0.85) to skip LLM verification entirely.
    for c in candidates:
        atlas_score = c.get("score", 0.0)
        if atlas_score > 0:
            c["rerank_score"] = atlas_score
        else:
            # No real score available — assign medium so LLM verifier handles it
            c["rerank_score"] = 0.60
    
    # Sort by rerank_score descending (best match first)
    candidates.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        
    return candidates


async def verify_match_llm(query: str, candidate_question: str, llm) -> bool:
    """Uses an LLM to verify if a candidate question is semantically identical to the user query."""
    if not llm:
        return False
        
    prompt = f"""You are a semantic matching verification engine. 
Are these two questions asking for the exact same information?
Two questions are SEMANTICALLY EQUIVALENT if they ask about the same thing, even if:
- One is active voice, the other passive
- Word order, synonyms, or phrasing differs
- One is in a different language

Query 1: {query}
Query 2: {candidate_question}

Respond with ONLY "YES" if they are semantically equivalent, or "NO" if they are not."""

    from services.key_rotation import get_key_rotator
    from services.ai_generation import get_llm_instance, get_active_provider, _is_rate_limit_error
    import asyncio
    
    active_provider = get_active_provider()
    rotator = get_key_rotator()
    max_attempts = max(rotator.total_keys, 1)
    
    if active_provider == "gemini":
        from google import genai
        from config import GEMINI_MODEL
        for attempt in range(max_attempts):
            key = rotator.get_active_key()
            if not key: break
            try:
                client = genai.Client(api_key=key)
                result = await asyncio.wait_for(
                    client.aio.models.generate_content(model=GEMINI_MODEL, contents=prompt),
                    timeout=8.0
                )
                if result.text:
                    rotator.report_success()
                    return "YES" in result.text.strip().upper()
            except asyncio.TimeoutError:
                print(f"LLM Verification Error: Timeout after 8s on attempt {attempt+1}. Rotating key...")
                rotator.report_rate_limited()
                continue
            except Exception as e:
                if _is_rate_limit_error(e):
                    rotator.report_rate_limited()
                    continue
                print(f"LLM Verification Error: {e}")
                return False
        return False

    for attempt in range(max_attempts):
        try:
            result = await asyncio.wait_for(llm.ainvoke(prompt), timeout=8.0)
            text = result.content.strip().upper()
            await asyncio.to_thread(rotator.report_success)
            return "YES" in text
        except asyncio.TimeoutError:
            print(f"LLM Verification Error: Timeout after 8s on attempt {attempt+1}")
            await asyncio.to_thread(rotator.report_rate_limited)
            llm = await asyncio.to_thread(get_llm_instance, "gemini")
            if not llm: return False
            continue
        except Exception as e:
            if _is_rate_limit_error(e):
                await asyncio.to_thread(rotator.report_rate_limited)
                llm = await asyncio.to_thread(get_llm_instance, "gemini")
                if not llm:
                    print(f"LLM Verification: All keys exhausted.")
                    return False
                continue
            print(f"LLM Verification Error: {e}")
            return False
    
    return False


from app.models import ResponseMode

async def decide_best_match(
    query: str,
    candidates: List[Dict[str, Any]],
    llm,
    is_followup: bool = False
) -> tuple[Optional[Dict[str, Any]], str, int, ResponseMode]:
    """Decides the best match based on re-ranker scores and LLM verification.
    Converts direct-hit answers into elaboration workflow if follow-up intent is detected,
    without discarding direct-hit grounding context.
    
    Returns:
        tuple: (best_candidate, source_label, tokens_used, ResponseMode)
    """
    if not candidates:
        mode = ResponseMode.ELABORATE if is_followup else ResponseMode.GENERATE
        return None, "no_match", 0, mode
        
    best = candidates[0]
    score = best.get("rerank_score", 0.0)
    tokens_used = 0
    
    # HIGH confidence
    if score >= RERANK_HIGH_THRESHOLD:
        print(f"Re-ranker HIGH confidence ({score:.2f}) for: {best['question']}")
        mode = ResponseMode.ELABORATE if is_followup else ResponseMode.DIRECT_HIT
        print(f"Reranker: ResponseMode decision -> {mode.value}", flush=True)
        return best, "dataset_native", tokens_used, mode
        
    # MEDIUM confidence
    if score >= RERANK_MEDIUM_THRESHOLD:
        print(f"Re-ranker MEDIUM confidence ({score:.2f}). Running LLM Verification...")
        is_match = await verify_match_llm(query, best["question"], llm)
        
        # Approximate tokens for LLM Verification
        prompt_len = 500 + len(query) + len(best["question"])
        tokens_used += max(1, int(prompt_len / 4)) + 10
        
        if is_match:
            print(f"LLM Verification Confirmed match for: {best['question']}")
            mode = ResponseMode.ELABORATE if is_followup else ResponseMode.DIRECT_HIT
            print(f"Reranker: ResponseMode decision -> {mode.value}", flush=True)
            return best, "dataset_verified", tokens_used, mode
        else:
            print("LLM Verification Rejected match.")
            
    # LOW confidence
    mode = ResponseMode.ELABORATE if is_followup else ResponseMode.GENERATE
    print(f"Reranker: ResponseMode decision -> {mode.value}", flush=True)
    return None, "no_match", tokens_used, mode

