"""
Vachan Study Bible Chatbot — Rate Limiter & Token Tracker Service
Manages Gemini free tier rate limits (15 RPM, 1500 RPD) and token budget tracking.
"""

import time
from config import RATE_LIMIT_RPM, RATE_LIMIT_RPD
from db.repositories import MetricsRepository


def load_tokens_data() -> dict:
    """Loads global token tracking data from MongoDB."""
    return MetricsRepository.get_metrics()


def save_tokens_data(data: dict):
    """Saves global token tracking data to MongoDB."""
    MetricsRepository.save_metrics(data)


def is_rate_limited() -> tuple:
    """Checks if the current request would exceed rate limits.
    
    Returns:
        tuple: (is_limited: bool, message: str)
    """
    data = load_tokens_data()
    now = time.time()

    if now - data.get("last_day_reset_time", 0.0) >= 86400:
        return False, ""
    if now - data.get("last_minute_reset_time", 0.0) >= 60:
        return False, ""

    if data["requests_this_minute"] >= RATE_LIMIT_RPM:
        return True, f"Gemini free tier rate limit exceeded ({RATE_LIMIT_RPM} RPM). Switching to local offline mode."
    if data["requests_today"] >= RATE_LIMIT_RPD:
        return True, f"Gemini free tier daily limit exceeded ({RATE_LIMIT_RPD} RPD). Switching to local offline mode."
    return False, ""


def check_and_update_rate_limits() -> dict:
    """Increments request counters and resets if time windows have elapsed."""
    data = load_tokens_data()
    now = time.time()

    if now - data.get("last_day_reset_time", 0.0) >= 86400:
        data["requests_today"] = 0
        data["last_day_reset_time"] = now
        data["pending_tokens"] = data["limit"]

    if now - data.get("last_minute_reset_time", 0.0) >= 60:
        data["requests_this_minute"] = 0
        data["last_minute_reset_time"] = now

    data["requests_today"] += 1
    data["requests_this_minute"] += 1

    save_tokens_data(data)
    return data


def extract_token_usage(llm_result, prompt_str: str) -> dict:
    """Extracts token usage from an LLM result, falling back to character-based estimation."""
    # Modern LangChain standard (usage_metadata)
    if hasattr(llm_result, "usage_metadata") and llm_result.usage_metadata:
        return {
            "prompt": llm_result.usage_metadata.get("input_tokens", 0),
            "completion": llm_result.usage_metadata.get("output_tokens", 0),
            "total": llm_result.usage_metadata.get("total_tokens", 0)
        }

    # Response metadata standard
    if hasattr(llm_result, "response_metadata") and llm_result.response_metadata:
        meta = llm_result.response_metadata
        if "token_usage" in meta:
            usage = meta["token_usage"]
            if isinstance(usage, dict):
                return {
                    "prompt": usage.get("prompt_tokens", 0),
                    "completion": usage.get("completion_tokens", 0),
                    "total": usage.get("total_tokens", 0)
                }

    # Fallback: approximate 4 chars per token
    prompt_chars = len(prompt_str)
    completion_chars = len(llm_result.content) if hasattr(llm_result, "content") else 0
    prompt_tokens = max(1, int(prompt_chars / 4))
    completion_tokens = max(1, int(completion_chars / 4))
    return {
        "prompt": prompt_tokens,
        "completion": completion_tokens,
        "total": prompt_tokens + completion_tokens
    }
