"""
Vachan Study Bible Chatbot — Rate Limiter & Token Tracker Service
Manages Gemini free tier rate limits (15 RPM, 1500 RPD) and token budget tracking.
"""

import os
import json
import time
from config import TOKENS_FILE, RATE_LIMIT_RPM, RATE_LIMIT_RPD, TOKEN_BUDGET_DEFAULT, DATA_DIR

# In-memory backup dictionary to guarantee zero-fail operation
_in_memory_tokens = None


def _get_default_data() -> dict:
    return {
        "total_tokens_used": 0,
        "pending_tokens": TOKEN_BUDGET_DEFAULT,
        "limit": TOKEN_BUDGET_DEFAULT,
        "requests_today": 0,
        "requests_this_minute": 0,
        "last_minute_reset_time": time.time(),
        "last_day_reset_time": time.time()
    }


def load_tokens_data() -> dict:
    """Loads token tracking data from file or in-memory backup."""
    global _in_memory_tokens
    default_data = _get_default_data()

    # Ensure parent directory exists
    tokens_dir = os.path.dirname(TOKENS_FILE)
    if tokens_dir:
        try:
            os.makedirs(tokens_dir, exist_ok=True)
        except Exception as e:
            print(f"RAG System: Failed to create tokens directory {tokens_dir} ({e}). Using in-memory state fallback.")
            if _in_memory_tokens is None:
                _in_memory_tokens = default_data.copy()
            return _in_memory_tokens

    # If already using in-memory backup, return it
    if _in_memory_tokens is not None:
        for key, val in default_data.items():
            if key not in _in_memory_tokens:
                _in_memory_tokens[key] = val
        return _in_memory_tokens

    if not os.path.exists(TOKENS_FILE):
        try:
            with open(TOKENS_FILE, "w", encoding="utf-8") as f:
                json.dump(default_data, f)
            return default_data
        except Exception as e:
            print(f"Error creating tokens file ({e}). Falling back to in-memory dictionary.")
            _in_memory_tokens = default_data.copy()
            return _in_memory_tokens

    try:
        with open(TOKENS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key, val in default_data.items():
            if key not in data:
                data[key] = val
        return data
    except Exception as e:
        print(f"Error loading tokens file ({e}). Falling back to in-memory state.")
        if _in_memory_tokens is None:
            _in_memory_tokens = default_data.copy()
        return _in_memory_tokens


def save_tokens_data(data: dict):
    """Saves token tracking data to file and in-memory backup."""
    global _in_memory_tokens
    _in_memory_tokens = data
    try:
        with open(TOKENS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving tokens file ({e}). Token state is preserved in-memory.")


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
