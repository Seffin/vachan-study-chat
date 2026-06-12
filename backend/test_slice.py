import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import GEMINI_API_KEY
from langchain_google_genai import GoogleGenerativeAIEmbeddings

e_3072 = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", google_api_key=GEMINI_API_KEY)
v_3072 = e_3072.embed_query("test")

e_768 = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", google_api_key=GEMINI_API_KEY, output_dimensionality=768)
v_768 = e_768.embed_query("test")

print("Match:", v_3072[:768] == v_768)
