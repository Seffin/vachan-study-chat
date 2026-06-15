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


async def rewrite_query_with_context(query: str, history: list, llm) -> str:
    """Rewrites a user's query into a standalone query using the chat history."""
    if not history or not llm:
        return query
        
    history_text = ""
    for msg in history[-4:]: # Only take the last 4 turns for context
        role = "User" if msg.role == "user" else "AI"
        history_text += f"{role}: {msg.content}\n"
        
    prompt = f"""Given the following conversation history, rewrite the final User question into a standalone, context-independent query that can be understood without the conversation history.
If the final user question is already standalone and does not contain any pronouns (like 'this', 'he', 'it', 'passage', 'here'), return it EXACTLY as it is.
Do NOT answer the question. ONLY return the rewritten question.

Conversation History:
{history_text}

Final User Question: {query}
Rewritten Query:"""

    try:
        active_provider = get_active_provider()
        if active_provider == "gemini":
            from services.key_rotation import get_key_rotator
            from google import genai
            from config import GEMINI_MODEL
            rotator = get_key_rotator()
            max_attempts = max(rotator.total_keys, 1)
            
            for attempt in range(max_attempts):
                key = rotator.get_active_key()
                if not key: break
                try:
                    client = genai.Client(api_key=key)
                    response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
                    rewritten = response.text.strip() if response.text else query
                    rotator.report_success()
                    return rewritten
                except Exception as e:
                    if _is_rate_limit_error(e):
                        rotator.report_rate_limited()
                        continue
                    break
        else:
            response = await llm.ainvoke(prompt)
            return response.content.strip() if hasattr(response, 'content') else str(response).strip()
    except Exception as e:
        print(f"Query rewrite failed: {e}")
        
    return query


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
            answer = response.text.strip() if response.text else ""
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


async def transcribe_audio(audio_bytes: bytes, mime_type: str = "audio/webm") -> str:
    """Transcribes audio using Gemini 2.5 Flash natively with automatic key rotation.
    
    Returns the transcription text, or empty string if no speech detected.
    """
    from google import genai
    from google.genai import types
    
    audio_size_kb = len(audio_bytes) / 1024
    print(f"Transcription: Received {audio_size_kb:.1f} KB of {mime_type} audio", flush=True)
    
    # Very small files (< 100 bytes) are likely empty/corrupt
    if len(audio_bytes) < 100:
        print("Transcription: Audio too small (< 100 bytes), likely empty.", flush=True)
        return ""
    
    rotator = get_key_rotator()
    
    # A more specific prompt that prevents hallucination on noise/silence
    prompt = (
        "You are a speech-to-text transcription engine. "
        "Listen carefully to the audio and transcribe ONLY the words that were actually spoken. "
        "If the audio contains only silence, noise, or unintelligible sound, respond with exactly: [NO_SPEECH] "
        "Do not invent, guess, or hallucinate any words. "
        "Return ONLY the verbatim transcription, nothing else."
    )
    
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
                contents=[
                    prompt,
                    types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
                ]
            )
            
            raw = response.text.strip() if response.text else ""
            print(f"Transcription raw result: '{raw}'", flush=True)
            
            # Detect the sentinel we told Gemini to use for silence
            if not raw or "[NO_SPEECH]" in raw.upper():
                rotator.report_success()
                return ""
            
            rotator.report_success()
            return raw
        except Exception as e:
            last_error = e
            if _is_rate_limit_error(e):
                rotator.report_rate_limited()
                continue
            else:
                raise
                
    raise last_error or Exception("All Gemini API keys are rate-limited for transcription.")

