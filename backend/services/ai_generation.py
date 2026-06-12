"""
Vachan Study Bible Chatbot — AI Generation Service
Handles general AI answer generation when no dataset match is found.
Supports both Gemini and OpenAI providers, with automatic Gemini key rotation.
"""

import os
from config import GEMINI_API_KEY, OPENAI_API_KEY, GEMINI_MODEL, OPENAI_MODEL, LLM_TEMPERATURE
from services.key_rotation import get_key_rotator


def get_llm_instance(provider: str, api_key_override: str = None):
    """Creates and returns a LangChain LLM instance for the specified provider.
    
    Args:
        provider: 'gemini' or 'openai'
        api_key_override: Optional specific API key to use (for key rotation)
    
    Returns:
        A LangChain chat model instance, or None if the provider is unavailable.
    """
    if provider == "gemini":
        key = api_key_override or get_key_rotator().get_active_key()
        if key:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=GEMINI_MODEL,
                google_api_key=key,
                temperature=LLM_TEMPERATURE
            )
    elif provider == "openai" and OPENAI_API_KEY:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=OPENAI_MODEL,
            temperature=LLM_TEMPERATURE,
            openai_api_key=OPENAI_API_KEY
        )
    return None


def get_active_provider() -> str:
    """Returns the name of the currently active LLM provider."""
    rotator = get_key_rotator()
    if rotator.get_active_key():
        return "gemini"
    elif OPENAI_API_KEY:
        return "openai"
    return "semantic"


def _is_rate_limit_error(e: Exception) -> bool:
    """Checks if an exception is a rate-limit (429), quota-exhausted, invalid key (400), or server error (503)."""
    err_str = str(e).lower()
    return any(keyword in err_str for keyword in [
        "429", "resource_exhausted", "quota", 
        "400", "invalid_argument", "api key not found", "api_key_invalid",
        "503", "unavailable"
    ])


async def generate_ai_answer(
    query: str,
    lang_name: str,
    book_code: str = "",
    is_overview: bool = False,
    provider: str = "gemini"
) -> tuple:
    """Generates an AI answer using the specified provider.
    With Gemini, automatically retries with rotated keys on rate-limit errors.
    
    Returns:
        tuple: (answer: str, tokens_used: int)
    """
    if provider == "gemini":
        return await _generate_gemini_with_rotation(query, lang_name, book_code, is_overview)
    else:
        return await _generate_langchain(query, lang_name, book_code, is_overview, provider)


async def _generate_gemini_with_rotation(query: str, lang_name: str, book_code: str, is_overview: bool) -> tuple:
    """Generates answer using native Gemini SDK with automatic key rotation on 429."""
    from google import genai
    
    rotator = get_key_rotator()
    
    if is_overview:
        prompt = (
            f"You are the scholarly Bible Study Chatbot for 'Vachan Study'. "
            f"Please provide a comprehensive, scholarly, and structured overview of the Bible book '{book_code}' "
            f"strictly IN {lang_name}. Cover Historical Background, Key Themes, and Outline. "
            f"State at the end: 'Note: This response comes from my general knowledge database.'"
        )
    else:
        prompt = (
            f"You are the scholarly Bible Study Chatbot. "
            f"Please answer the following question strictly IN {lang_name} using your general knowledge: {query}"
        )
    
    # Try up to N keys (one attempt per key)
    max_attempts = max(rotator.total_keys, 1)
    last_error = None
    
    for attempt in range(max_attempts):
        key = rotator.get_active_key()
        if not key:
            break
        
        try:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
            )
            answer = response.text.strip()
            tokens_used = max(1, int(len(prompt) / 4)) + max(1, int(len(answer) / 4))
            rotator.report_success()
            return answer, tokens_used
        except Exception as e:
            last_error = e
            if _is_rate_limit_error(e):
                rotator.report_rate_limited()
                continue  # Try next key
            else:
                raise  # Non-rate-limit error, propagate immediately
    
    # All keys exhausted
    raise last_error or Exception("All Gemini API keys are rate-limited.")


async def _generate_langchain(query: str, lang_name: str, book_code: str, is_overview: bool, provider: str) -> tuple:
    """Generates answer using LangChain LLM wrapper (OpenAI or Gemini via LangChain)."""
    from services.rate_limiter import extract_token_usage

    llm = get_llm_instance(provider)
    if not llm:
        return "⚠️ No AI provider is configured.", 0

    if is_overview:
        prompt = (
            f"You are the scholarly Bible Study Chatbot for 'Vachan Study'. "
            f"Please provide a comprehensive, scholarly, and structured overview of the Bible book '{book_code}' "
            f"strictly IN {lang_name}. Cover Historical Background, Key Themes, and Outline. "
            f"State at the end: 'Note: This response comes from my general knowledge database.'"
        )
    else:
        prompt = (
            f"You are the scholarly Bible Study Chatbot. "
            f"Please answer the following question strictly IN {lang_name} using your general knowledge: {query}"
        )

    llm_result = llm.invoke(prompt)
    answer = llm_result.content.strip()
    usage = extract_token_usage(llm_result, prompt)
    return answer, usage["total"]
