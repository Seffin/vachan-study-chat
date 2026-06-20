"""
Vachan Study Bible Chatbot — Translation Service
Handles language detection and text translation using LLM providers.
"""

import re
from config import LANGUAGE_MAP

try:
    from langdetect import detect
except ImportError:
    def detect(text): return 'en'

import asyncio


def detect_user_language(message: str) -> tuple:
    """Detects the language of a user message.
    
    Returns:
        tuple: (lang_code, lang_name) e.g. ('ml', 'Malayalam')
    """
    try:
        lang_code = detect(message)
    except Exception:
        lang_code = 'en'
    lang_name = LANGUAGE_MAP.get(lang_code, "English")
    if lang_code not in LANGUAGE_MAP:
        lang_name = f"ISO-{lang_code} language"
    return lang_code, lang_name


async def translate_text(text: str, target_language: str, llm) -> str:
    """Translates text to the target language using the provided LLM instance.
    
    Args:
        text: The text to translate.
        target_language: The target language name (e.g. 'English', 'Malayalam').
        llm: A LangChain LLM instance.
    
    Returns:
        The translated text string.
    """
    prompt = f"Translate the following text to {target_language}. Output ONLY the translation, nothing else:\n\n{text}"
    
    from services.key_rotation import get_key_rotator
    from services.ai_generation import get_llm_instance, _is_rate_limit_error
    
    rotator = get_key_rotator()
    max_attempts = max(rotator.total_keys, 1)
    
    for attempt in range(max_attempts):
        try:
            result = await asyncio.wait_for(llm.ainvoke(prompt), timeout=10.0)
            await asyncio.to_thread(rotator.report_success)
            return result.content.strip() if hasattr(result, 'content') else str(result).strip()
        except asyncio.TimeoutError:
            print(f"Translation Error: Timeout after 10s on attempt {attempt+1}")
            continue
        except Exception as e:
            if _is_rate_limit_error(e):
                await asyncio.to_thread(rotator.report_rate_limited)
                # Rebuild LLM with next key
                llm = await asyncio.to_thread(get_llm_instance, "gemini")
                if not llm:
                    print("Translation: All keys exhausted.")
                    return text # Fallback to original
                continue
            print(f"Translation Error: {e}")
            return text # Fallback to original
            
    return text


async def translate_to_english(text: str, llm) -> str:
    """Convenience wrapper to translate text to English."""
    prompt = f"Translate the following text to English, output ONLY the translation:\n{text}"
    
    from services.key_rotation import get_key_rotator
    from services.ai_generation import get_llm_instance, _is_rate_limit_error
    
    rotator = get_key_rotator()
    max_attempts = max(rotator.total_keys, 1)
    
    for attempt in range(max_attempts):
        try:
            result = await asyncio.wait_for(llm.ainvoke(prompt), timeout=10.0)
            await asyncio.to_thread(rotator.report_success)
            return result.content.strip() if hasattr(result, 'content') else str(result).strip()
        except asyncio.TimeoutError:
            print(f"Translation Error: Timeout after 10s on attempt {attempt+1}")
            continue
        except Exception as e:
            if _is_rate_limit_error(e):
                await asyncio.to_thread(rotator.report_rate_limited)
                # Rebuild LLM with next key
                llm = await asyncio.to_thread(get_llm_instance, "gemini")
                if not llm:
                    print("Translation: All keys exhausted.")
                    return text # Fallback to original
                continue
            print(f"Translation Error: {e}")
            return text # Fallback to original
            
    return text
