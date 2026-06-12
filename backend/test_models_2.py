import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import GEMINI_API_KEY
from langchain_google_genai import GoogleGenerativeAIEmbeddings

models_to_test = [
    "embedding-001",
    "text-embedding-004",
    "models/text-embedding-004",
]

for m in models_to_test:
    try:
        e = GoogleGenerativeAIEmbeddings(model=m, google_api_key=GEMINI_API_KEY)
        print(f"Model {m} dim:", len(e.embed_query("test")))
    except Exception as ex:
        print(f"Model {m} error:", ex)
