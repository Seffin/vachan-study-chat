import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from services.ai_generation import get_active_provider
from services.embedding import get_embeddings_model

provider = get_active_provider()
embeddings = get_embeddings_model(provider)

print("Class:", type(embeddings))
print("Dict:", embeddings.__dict__)
