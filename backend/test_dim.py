import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import GEMINI_API_KEY
from langchain_google_genai import GoogleGenerativeAIEmbeddings

try:
    e = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", google_api_key=GEMINI_API_KEY, output_dimensionality=768)
    vec = e.embed_query("test")
    print("Dim:", len(vec))
except Exception as ex:
    print("Error:", ex)
