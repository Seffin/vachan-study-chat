"""
Vachan Study Bible Chatbot — Embedding Service
Provides access to the configured embedding models (Gemini, OpenAI, or BGE-M3).
Uses the key rotator for Gemini to automatically use the active API key.
"""

from config import OPENAI_API_KEY
from services.key_rotation import get_key_rotator

def get_embeddings_model(provider: str):
    """Returns a LangChain embeddings model instance for the given provider.
    
    Args:
        provider: 'gemini', 'openai', or 'bge-m3'
        
    Returns:
        Embeddings model instance or None.
    """
    if provider == "gemini":
        key = get_key_rotator().get_active_key()
        if key:
            try:
                try:
                    from langchain_google_genai import GoogleGenerativeAIEmbeddings as GeminiEmbeddings
                except ImportError:
                    from langchain_google_genai import GoogleGenAIEmbeddings as GeminiEmbeddings
                return GeminiEmbeddings(
                    model="models/gemini-embedding-001", 
                    google_api_key=key, 
                    output_dimensionality=768
                )
            except Exception as e:
                print(f"RAG System: Failed to load Gemini embeddings ({e})")
            
    elif provider == "openai" and OPENAI_API_KEY:
        try:
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        except Exception as e:
            print(f"RAG System: Failed to load OpenAIEmbeddings ({e})")
            
    elif provider == "bge-m3":
        # Placeholder for self-hosted BGE-M3 implementation if deployed
        # Requires: from langchain_community.embeddings import HuggingFaceBgeEmbeddings
        # return HuggingFaceBgeEmbeddings(model_name="BAAI/bge-m3")
        print("RAG System: bge-m3 is not yet configured for Serverless.")
        
    return None

async def get_embeddings_model_async(provider: str):
    if provider == "gemini":
        key = await get_key_rotator().get_active_key_async()
        if key:
            try:
                try:
                    from langchain_google_genai import GoogleGenerativeAIEmbeddings as GeminiEmbeddings
                except ImportError:
                    from langchain_google_genai import GoogleGenAIEmbeddings as GeminiEmbeddings
                return GeminiEmbeddings(
                    model="models/gemini-embedding-001", 
                    google_api_key=key, 
                    output_dimensionality=768
                )
            except Exception as e:
                print(f"RAG System: Failed to load Gemini embeddings ({e})")
            
    elif provider == "openai" and OPENAI_API_KEY:
        try:
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        except Exception as e:
            print(f"RAG System: Failed to load OpenAIEmbeddings ({e})")
            
    return None
