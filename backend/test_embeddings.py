import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import GEMINI_API_KEY, OPENAI_API_KEY
from services.ai_generation import get_active_provider
from services.embedding import get_embeddings_model

print("GEMINI_API_KEY exists:", bool(GEMINI_API_KEY))
print("OPENAI_API_KEY exists:", bool(OPENAI_API_KEY))

provider = get_active_provider()
print("Active Provider:", provider)

embeddings = get_embeddings_model(provider)
if embeddings:
    vec = embeddings.embed_query("test")
    print("Vector Dimension:", len(vec))
else:
    print("Embeddings is None")
