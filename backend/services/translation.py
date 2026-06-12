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
    result = llm.invoke(prompt)
    return result.content.strip()


async def translate_to_english(text: str, llm) -> str:
    """Convenience wrapper to translate text to English."""
    prompt = f"Translate the following text to English, output ONLY the translation:\n{text}"
    result = llm.invoke(prompt)
    return result.content.strip()
