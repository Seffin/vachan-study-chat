import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import GEMINI_API_KEY
from langchain_google_genai import GoogleGenerativeAIEmbeddings

try:
    e1 = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=GEMINI_API_KEY)
    print("models/embedding-001 dim:", len(e1.embed_query("test")))
except Exception as e:
    print("models/embedding-001 error:", e)

try:
    e2 = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=GEMINI_API_KEY)
    print("models/text-embedding-004 dim:", len(e2.embed_query("test")))
except Exception as e:
    print("models/text-embedding-004 error:", e)
    
try:
    e3 = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", google_api_key=GEMINI_API_KEY)
    print("models/gemini-embedding-001 dim:", len(e3.embed_query("test")))
except Exception as e:
    print("models/gemini-embedding-001 error:", e)
