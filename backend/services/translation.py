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
    """Translates text to the target language using the provided LLM instance."""
    prompt = f"Translate the following text to {target_language}. Output ONLY the translation, nothing else:\n\n{text}"
    
    from services.key_rotation import get_key_rotator
    from services.ai_generation import get_llm_instance, get_active_provider, _is_rate_limit_error
    
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
                    timeout=20.0
                )
                if result.text:
                    rotator.report_success()
                    return result.text.strip()
            except asyncio.TimeoutError:
                print(f"Translation Error: Timeout after 20s on attempt {attempt+1}. Rotating key...")
                rotator.report_rate_limited()
                continue
            except Exception as e:
                if _is_rate_limit_error(e):
                    rotator.report_rate_limited()
                    continue
                print(f"Translation Error: {e}")
                return text
        return text

    for attempt in range(max_attempts):
        try:
            result = await asyncio.wait_for(llm.ainvoke(prompt), timeout=20.0)
            await asyncio.to_thread(rotator.report_success)
            return result.content.strip() if hasattr(result, 'content') else str(result).strip()
        except asyncio.TimeoutError:
            print(f"Translation Error: Timeout after 20s on attempt {attempt+1}")
            await asyncio.to_thread(rotator.report_rate_limited)
            llm = await asyncio.to_thread(get_llm_instance, "gemini")
            if not llm: return text
            continue
        except Exception as e:
            if _is_rate_limit_error(e):
                await asyncio.to_thread(rotator.report_rate_limited)
                llm = await asyncio.to_thread(get_llm_instance, "gemini")
                if not llm: return text
                continue
            print(f"Translation Error: {e}")
            return text
            
    return text


async def translate_to_english(text: str, llm) -> str:
    """Convenience wrapper to translate text to English."""
    prompt = f"Translate the following text to English, output ONLY the translation:\n{text}"
    
    from services.key_rotation import get_key_rotator
    from services.ai_generation import get_llm_instance, get_active_provider, _is_rate_limit_error
    
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
                    timeout=20.0
                )
                if result.text:
                    rotator.report_success()
                    return result.text.strip()
            except asyncio.TimeoutError:
                print(f"Translation Error: Timeout after 20s on attempt {attempt+1}. Rotating key...")
                rotator.report_rate_limited()
                continue
            except Exception as e:
                if _is_rate_limit_error(e):
                    rotator.report_rate_limited()
                    continue
                print(f"Translation Error: {e}")
                return text
        return text

    for attempt in range(max_attempts):
        try:
            result = await asyncio.wait_for(llm.ainvoke(prompt), timeout=20.0)
            await asyncio.to_thread(rotator.report_success)
            return result.content.strip() if hasattr(result, 'content') else str(result).strip()
        except asyncio.TimeoutError:
            print(f"Translation Error: Timeout after 20s on attempt {attempt+1}")
            await asyncio.to_thread(rotator.report_rate_limited)
            llm = await asyncio.to_thread(get_llm_instance, "gemini")
            if not llm: return text
            continue
        except Exception as e:
            if _is_rate_limit_error(e):
                await asyncio.to_thread(rotator.report_rate_limited)
                llm = await asyncio.to_thread(get_llm_instance, "gemini")
                if not llm: return text
                continue
            print(f"Translation Error: {e}")
            return text
            
    return text
