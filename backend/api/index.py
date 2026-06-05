import os
import sys
import json
import time
import csv
import subprocess
import urllib.request
import zipfile
import io
import re
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from langdetect import detect
except ImportError:
    def detect(text): return 'en'

LANGUAGE_MAP = {
    'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German', 'zh-cn': 'Chinese (Simplified)',
    'zh-tw': 'Chinese (Traditional)', 'hi': 'Hindi', 'ar': 'Arabic', 'ru': 'Russian', 'pt': 'Portuguese',
    'ja': 'Japanese', 'ko': 'Korean', 'it': 'Italian', 'nl': 'Dutch', 'tr': 'Turkish',
    'pl': 'Polish', 'vi': 'Vietnamese', 'ml': 'Malayalam', 'ta': 'Tamil', 'te': 'Telugu',
    'kn': 'Kannada', 'bn': 'Bengali', 'ur': 'Urdu', 'gu': 'Gujarati', 'mr': 'Marathi'
}

def detect_user_language(message: str) -> tuple[str, str]:
    try:
        lang_code = detect(message)
    except:
        lang_code = 'en'
    lang_name = LANGUAGE_MAP.get(lang_code, "English")
    if lang_code not in LANGUAGE_MAP:
        lang_name = f"ISO-{lang_code} language"
    return lang_code, lang_name
from dotenv import load_dotenv

# Load environment configurations
load_dotenv()

# Determine directories relative to this file's location (backend/api/index.py)
API_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(API_DIR)
STATIC_DATA_DIR = os.path.join(BACKEND_DIR, "static_data")
DATA_DIR = os.path.join(BACKEND_DIR, "data")

# Add backend directory to sys.path so Uvicorn can import "api.index" correctly
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Initialize FastAPI app
app = FastAPI(
    title="Vachan Study Bible Study Chatbot RAG API",
    description="FastAPI Backend serving retrieval-augmented scripture insights, optimized for Vercel Serverless Functions.",
    version="1.0.0"
)

# CORS Setup to connect seamlessly to React Next.js Frontend
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://192.168.1.101:3000",
]
extra_origins = os.environ.get("ALLOWED_ORIGINS", "")
if extra_origins:
    allowed_origins.extend([o.strip() for o in extra_origins.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment keys and models
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

BIBLE_API_KEY = os.environ.get("BIBLE_API_KEY")
BIBLE_API_URL = os.environ.get("BIBLE_API_URL", "https://rest.api.bible").rstrip('/')
BIBLE_ID = os.environ.get("BIBLE_ID", "de4e12af7af57f50-02")

DISCLAIMER_UNFOLDING = "🤖 *This response based on the unfoldingWord dataset.*"
DISCLAIMER_AI = "🤖 *This is an AI-generated response based on the unfoldingWord dataset.*"

# =====================================================================
# 🧠 OFFLINE SEMANTIC OVERLAP & RETRIEVER INFRASTRUCTURE
# =====================================================================

class Document:
    def __init__(self, page_content: str, metadata: dict):
        self.page_content = page_content
        self.metadata = metadata

class SemanticRetriever:
    """Fallback semantic matcher. Uses basic word overlap score if no active keys are set."""
    def __init__(self, records: List[Dict[str, str]]):
        self.docs = []
        for row in records:
            page_content = f"Reference: {row['Reference']}\nQuestion: {row['Question']}\nResponse: {row['Response']}"
            metadata = {
                "reference": str(row["Reference"]),
                "question": str(row["Question"]),
                "response": str(row["Response"])
            }
            self.docs.append(Document(page_content, metadata))

    def retrieve_with_scores(self, query: str, k: int = 10):
        query_words = set(query.lower().split())
        scored_docs = []
        
        for doc in self.docs:
            content_words = set(doc.page_content.lower().split())
            # Basic overlap scoring
            overlap = len(query_words.intersection(content_words))
            # Boost score if the query words match the metadata question specifically
            q_words = set(doc.metadata["question"].lower().split())
            overlap += len(query_words.intersection(q_words)) * 2
            
            # Massive boost for exact substring matches to ensure Tier 1 catches it
            norm_q = re.sub(r'[^a-z0-9]', '', doc.metadata["question"].lower())
            norm_query = re.sub(r'[^a-z0-9]', '', query.lower())
            if norm_query and norm_q and (norm_query == norm_q or norm_query in norm_q or norm_q in norm_query):
                overlap += 1000
            
            scored_docs.append((doc, overlap))
            
        # Sort by overlap score descending (higher is better for semantic retriever)
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        return scored_docs[:k]

    def retrieve(self, query: str, k: int = 10) -> List[Document]:
        return [doc for doc, _ in self.retrieve_with_scores(query, k)]

    def invoke(self, query: str) -> List[Document]:
        return self.retrieve(query, k=10)

# LangChain prompt template
from langchain_core.prompts import PromptTemplate
prompt_tmpl = PromptTemplate(
    input_variables=["context", "question", "user_language"],
    template="""You are the scholarly Bible Study Chatbot for "Vachan Study".
Please answer the following question strictly IN {user_language}.
Attempt to answer the question using ONLY the provided Context.
If the provided Context does not contain the answer, use your general AI knowledge to answer the question, but you MUST explicitly mention in your response that the answer comes from general knowledge rather than the specific study text.

Context:
{context}

Question: {question}

Answer naturally IN {user_language}.
"""
)

# Dynamic cache for retrievers: {book_code: (retriever_mode, retriever_instance)}
retrievers: Dict[str, tuple] = {}

def get_retriever_for_book(book_code: str, lang_code: str = "en") -> tuple:
    """Loads the book pre-compiled FAISS index or TSV fallback, constructs the retriever, and caches it."""
    book_code = book_code.upper().strip()
    cache_key = f"{book_code}_{lang_code}"
    if cache_key in retrievers:
        return retrievers[cache_key]

    # Resolve active LLM provider mode
    active_provider = None
    embeddings = None
    index_subdir = None

    if GEMINI_KEY:
        try:
            try:
                from langchain_google_genai import GoogleGenerativeAIEmbeddings as GeminiEmbeddings
            except ImportError:
                from langchain_google_genai import GoogleGenAIEmbeddings as GeminiEmbeddings
            embeddings = GeminiEmbeddings(model="models/gemini-embedding-001", google_api_key=GEMINI_KEY)
            index_subdir = "gemini"
            active_provider = "gemini"
        except Exception as e:
            print(f"RAG System: Failed to load Gemini embeddings ({e})")

    if not active_provider and OPENAI_KEY:
        try:
            from langchain_openai import OpenAIEmbeddings
            embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_KEY)
            index_subdir = "openai"
            active_provider = "openai"
        except Exception as e:
            print(f"RAG System: Failed to load OpenAIEmbeddings ({e})")

    # If provider API keys exist, attempt loading pre-compiled FAISS index from static_data/vectorstores
    if active_provider and embeddings and index_subdir:
        try:
            from langchain_community.vectorstores import FAISS
            index_path = os.path.join(STATIC_DATA_DIR, "vectorstores", f"{lang_code}_{index_subdir}", book_code)
            if not os.path.exists(index_path):
                index_path = os.path.join(STATIC_DATA_DIR, "vectorstores", index_subdir, book_code)
            
            if os.path.exists(index_path) and os.path.exists(os.path.join(index_path, "index.faiss")):
                print(f"RAG System: Persistent FAISS Index ({active_provider}) found for '{book_code}' at {index_path}. Loading...")
                vectorstore = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
                book_retriever = vectorstore.as_retriever(search_kwargs={"k": 10})
                retrievers[cache_key] = (active_provider, book_retriever)
                return retrievers[cache_key]
            else:
                print(f"RAG System: Pre-compiled FAISS index not found for '{book_code}' under static_data. Falling back...")
        except Exception as e:
            print(f"RAG System: FAISS index loading failed for '{book_code}' ({e}). Falling back...")

    # Mode 3: Offline Semantic Overlap / TSV fallback
    print(f"RAG System: Initiating Mode 3 (Offline Semantic Overlap) for '{book_code}'...")
    
    # Check paths: 1. data/en_tq/tq_{book}.tsv, 2. static_data/tq_{book}.csv, 3. static_data/tq_MAT.csv
    tsv_filename = f"tq_{book_code}.tsv"
    tsv_path = os.path.join(DATA_DIR, f"{lang_code}_tq", tsv_filename)
    
    if not os.path.exists(tsv_path):
        if lang_code == "en":
            # Look in static_data for book csv
            csv_filename = f"tq_{book_code}.csv"
            csv_path = os.path.join(STATIC_DATA_DIR, csv_filename)
            if os.path.exists(csv_path):
                tsv_path = csv_path
            else:
                # Fall back to Matthew
                tsv_path = os.path.join(STATIC_DATA_DIR, "tq_MAT.csv")
                if not os.path.exists(tsv_path):
                    from scripts.build_vector_db import bootstrap_data
                    bootstrap_data()
                    tsv_path = os.path.join(STATIC_DATA_DIR, "tq_MAT.csv")
        else:
            return "not_found", None

    try:
        is_tsv = tsv_path.endswith('.tsv')
        records = []
        with open(tsv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter='\t' if is_tsv else ',')
            
            # Normalize column names in the header
            normalized_fieldnames = []
            for field in (reader.fieldnames or []):
                field_clean = field.strip()
                if field_clean.lower() == 'reference': field_clean = 'Reference'
                elif field_clean.lower() == 'question': field_clean = 'Question'
                elif field_clean.lower() == 'response': field_clean = 'Response'
                normalized_fieldnames.append(field_clean)
            reader.fieldnames = normalized_fieldnames
            
            for row in reader:
                records.append({
                    "Reference": str(row.get("Reference") or "1:1").strip() or "1:1",
                    "Question": str(row.get("Question") or "").strip(),
                    "Response": str(row.get("Response") or "").strip()
                })
        
        book_retriever = SemanticRetriever(records)
        retrievers[cache_key] = (active_provider if active_provider else "semantic", book_retriever)
        print(f"RAG System: Offline Semantic Retriever cached for '{book_code}' (Inference Mode: {active_provider if active_provider else 'semantic'}).")
        return retrievers[cache_key]
    except Exception as e:
        print(f"RAG System: Failed to build offline semantic retriever for '{book_code}' ({e}). Returning emergency fallback.")
        # Hardcoded emergency fallback
        dummy_records = [{
            "Reference": "1:1",
            "Question": "What is the study book?",
            "Response": "Welcome to Vachan Study Bible Study Chatbot."
        }]
        book_retriever = SemanticRetriever(dummy_records)
        retrievers[cache_key] = (active_provider if active_provider else "semantic", book_retriever)
        return retrievers[cache_key]

# =====================================================================
# 📊 PERSISTENT TOKEN MONITORING & RATE-LIMITS (GEMINI FREE TIER)
# =====================================================================

# Check if running in Vercel (or other serverless environment where file writing might fail)
# On Vercel, /tmp is the only writeable directory.
if os.environ.get("VERCEL") == "1" or os.environ.get("VERCEL_ENV") or not os.access(DATA_DIR, os.W_OK) if os.path.exists(DATA_DIR) else False:
    TOKENS_FILE = "/tmp/tokens.json"
else:
    TOKENS_FILE = os.path.join(DATA_DIR, "tokens.json")

# In-memory backup dictionary to guarantee zero-fail operation
_in_memory_tokens = None

def load_tokens_data() -> dict:
    global _in_memory_tokens
    
    default_data = {
        "total_tokens_used": 0,
        "pending_tokens": 1000000,
        "limit": 1000000,
        "requests_today": 0,
        "requests_this_minute": 0,
        "last_minute_reset_time": time.time(),
        "last_day_reset_time": time.time()
    }
    
    # Ensure parent directory of TOKENS_FILE exists
    tokens_dir = os.path.dirname(TOKENS_FILE)
    if tokens_dir:
        try:
            os.makedirs(tokens_dir, exist_ok=True)
        except Exception as e:
            print(f"RAG System: Failed to create tokens directory {tokens_dir} ({e}). Using in-memory state fallback.")
            if _in_memory_tokens is None:
                _in_memory_tokens = default_data.copy()
            return _in_memory_tokens

    # If already using in-memory backup, return it
    if _in_memory_tokens is not None:
        # Fill in any missing keys
        for key, val in default_data.items():
            if key not in _in_memory_tokens:
                _in_memory_tokens[key] = val
        return _in_memory_tokens

    if not os.path.exists(TOKENS_FILE):
        try:
            with open(TOKENS_FILE, "w", encoding="utf-8") as f:
                json.dump(default_data, f)
            return default_data
        except Exception as e:
            print(f"Error creating tokens file ({e}). Falling back to in-memory dictionary.")
            _in_memory_tokens = default_data.copy()
            return _in_memory_tokens
            
    try:
        with open(TOKENS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Fill in any missing keys
        for key, val in default_data.items():
            if key not in data:
                data[key] = val
        return data
    except Exception as e:
        print(f"Error loading tokens file ({e}). Falling back to in-memory state.")
        if _in_memory_tokens is None:
            _in_memory_tokens = default_data.copy()
        return _in_memory_tokens

def save_tokens_data(data: dict):
    global _in_memory_tokens
    # Always keep in-memory backup updated
    _in_memory_tokens = data
    try:
        with open(TOKENS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving tokens file ({e}). Token state is preserved in-memory.")

def is_rate_limited() -> tuple:
    data = load_tokens_data()
    now = time.time()
    
    # Check day reset
    if now - data.get("last_day_reset_time", 0.0) >= 86400:
        return False, ""
        
    # Check minute reset
    if now - data.get("last_minute_reset_time", 0.0) >= 60:
        return False, ""
        
    if data["requests_this_minute"] >= 15:
        return True, "Gemini free tier rate limit exceeded (15 RPM). Switching to local offline mode."
    if data["requests_today"] >= 1500:
        return True, "Gemini free tier daily limit exceeded (1500 RPD). Switching to local offline mode."
    return False, ""

def check_and_update_rate_limits() -> dict:
    data = load_tokens_data()
    now = time.time()
    
    # Reset day count if needed
    if now - data.get("last_day_reset_time", 0.0) >= 86400:
        data["requests_today"] = 0
        data["last_day_reset_time"] = now
        data["pending_tokens"] = data["limit"] # Refill tokens daily
        
    # Reset minute count if needed
    if now - data.get("last_minute_reset_time", 0.0) >= 60:
        data["requests_this_minute"] = 0
        data["last_minute_reset_time"] = now
        
    # Increment counts for this request
    data["requests_today"] += 1
    data["requests_this_minute"] += 1
    
    save_tokens_data(data)
    return data

def extract_token_usage(llm_result, prompt_str: str) -> dict:
    # Modern LangChain standard (e.g. usage_metadata)
    if hasattr(llm_result, "usage_metadata") and llm_result.usage_metadata:
        return {
            "prompt": llm_result.usage_metadata.get("input_tokens", 0),
            "completion": llm_result.usage_metadata.get("output_tokens", 0),
            "total": llm_result.usage_metadata.get("total_tokens", 0)
        }
    
    # Response metadata standard
    if hasattr(llm_result, "response_metadata") and llm_result.response_metadata:
        meta = llm_result.response_metadata
        if "token_usage" in meta:
            usage = meta["token_usage"]
            if isinstance(usage, dict):
                return {
                    "prompt": usage.get("prompt_tokens", 0),
                    "completion": usage.get("completion_tokens", 0),
                    "total": usage.get("total_tokens", 0)
                }
    
    # Fallback to standard word/character approximate counter (approx. 4 chars per token)
    prompt_chars = len(prompt_str)
    completion_chars = len(llm_result.content) if hasattr(llm_result, "content") else 0
    prompt_tokens = max(1, int(prompt_chars / 4))
    completion_tokens = max(1, int(completion_chars / 4))
    return {
        "prompt": prompt_tokens,
        "completion": completion_tokens,
        "total": prompt_tokens + completion_tokens
    }

# =====================================================================
# 🌐 API SCHEMAS & API ENDPOINTS
# =====================================================================

def normalize_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r'[^a-z0-9]', '', text.lower())

OFFLINE_OVERVIEWS = {
    "MAT": "📖 **Overview of Matthew:** The Gospel of Matthew serves as a legal and theological bridge between the Old and New Testaments. It emphasizes Jesus as the promised Messiah, tracing His royal lineage back to Abraham and David, and highlights the Kingdom of Heaven through key teachings like the Sermon on the Mount.",
    "GEN": "📖 **Overview of Genesis:** Genesis is the book of beginnings. It documents the creation of the universe, the fall of humanity, and the covenant origin of God's chosen people through Abraham, Isaac, Jacob, and Joseph.",
    "LEV": "📖 **Overview of Leviticus:** Leviticus is a handbook for priests and worshipers, focusing on the holiness of God and the purification of His people. It details sacrificial offerings, priestly consecration, laws of clean and unclean, the Day of Atonement, and the holiness code."
}

def is_overview_query(query: str) -> bool:
    if not query:
        return False
    q_lower = query.lower().strip()
    patterns = [
        r'\boverview\b',
        r'\bsummary\b',
        r'\bintroduce\b',
        r'\bintroduction\b',
        r'\boutline\b',
        r'\bthemes\b'
    ]
    for pattern in patterns:
        if re.search(pattern, q_lower):
            if not re.search(r'\b(?:ch|chapter|verse|v)\b|\d+[\s:]\d+', q_lower):
                return True
    return False

class ChatRequest(BaseModel):
    book: str
    message: str
    history: Optional[List[str]] = []

class ChatResponse(BaseModel):
    answer: str
    reference: str
    suggested_questions: List[str]
    is_general_knowledge: bool = False
    tokens_used: int = 0
    total_tokens_used: int = 0
    pending_tokens: int = 0
    requests_today: int = 0
    requests_this_minute: int = 0
    source: Optional[str] = None

def get_llm_instance(provider: str):
    llm = None
    if provider == "gemini" and GEMINI_KEY:
        from langchain_google_genai import ChatGoogleGenerativeAI
        gemini_model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        temperature = float(os.environ.get("OPENAI_TEMPERATURE", "0.1"))
        llm = ChatGoogleGenerativeAI(model=gemini_model, google_api_key=GEMINI_KEY, temperature=temperature)
    elif provider == "openai" and OPENAI_KEY:
        from langchain_openai import ChatOpenAI
        model_name = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        temperature = float(os.environ.get("OPENAI_TEMPERATURE", "0.1"))
        llm = ChatOpenAI(model=model_name, temperature=temperature, openai_api_key=OPENAI_KEY)
    return llm

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    original_query = request.message.strip()
    book_code = request.book.upper().strip()
    if not original_query:
        raise HTTPException(status_code=400, detail="Query message cannot be empty.")
        
    print(f"API Chat Query: '{original_query}' for book '{book_code}'", flush=True)

    lang_code, lang_name = detect_user_language(original_query)
    print(f"Detected Language: {lang_name} ({lang_code})", flush=True)

    rate_limited, limit_msg = is_rate_limited()
    tokens_data = load_tokens_data()
    tokens_used = 0
    stats = load_tokens_data()

    is_overview = is_overview_query(original_query)
    
    answer = ""
    top_ref = "1:1"
    source = "ai_fallback"
    is_general_knowledge = False
    docs = []

    active_provider = "gemini" if GEMINI_KEY else "openai" if OPENAI_KEY else "semantic"

    def get_docs(query, lang):
        rmode, retriever = get_retriever_for_book(book_code, lang_code=lang)
        if not retriever:
            return rmode, []
        
        if hasattr(retriever, "vectorstore"):
            try:
                ds = retriever.vectorstore.similarity_search_with_score(query, k=10)
            except:
                ds = [(d, 0.0) for d in retriever.invoke(query)]
        elif hasattr(retriever, "retrieve_with_scores"):
            ds = retriever.retrieve_with_scores(query, k=10)
        else:
            ds = [(d, 0.0) for d in retriever.invoke(query)]
            
        return rmode, ds

    # --- Step 1: Native Retrieval ---
    retriever_mode, docs_and_scores = get_docs(original_query, lang_code)
    tier_matched = 0
    norm_query = normalize_text(original_query)
    
    if retriever_mode != "not_found" and not is_overview and docs_and_scores:
        for doc, score in docs_and_scores:
            doc_q = normalize_text(doc.metadata.get("question", ""))
            if norm_query and doc_q and (norm_query == doc_q or norm_query in doc_q or doc_q in norm_query):
                answer = doc.metadata.get("response", "")
                top_ref = doc.metadata.get("reference", "1:1")
                tier_matched = 1
                source = "dataset_native"
                break
        if tier_matched == 0:
            top_doc, top_score = docs_and_scores[0]
            is_semantic_match = False
            if retriever_mode == "semantic" and top_score > 6:
                is_semantic_match = True
            elif retriever_mode != "semantic" and top_score < 0.4:
                is_semantic_match = True
                
            if is_semantic_match:
                answer = top_doc.metadata.get("response", "")
                top_ref = top_doc.metadata.get("reference", "1:1")
                tier_matched = 2
                source = "dataset_native"
                
        if tier_matched > 0:
            docs = [d for d, s in docs_and_scores]

    # --- Step 2: English Translation Fallback ---
    if tier_matched == 0 and not is_overview and lang_code != "en" and not rate_limited and tokens_data["pending_tokens"] > 0:
        print("Native dataset missed. Attempting English Translation Fallback...", flush=True)
        llm = get_llm_instance(active_provider)
        if llm:
            try:
                trans_prompt = f"Translate the following text to English, output ONLY the translation:\\n{original_query}"
                trans_res = llm.invoke(trans_prompt)
                translated_query = trans_res.content.strip()
                
                en_rmode, en_docs_and_scores = get_docs(translated_query, "en")
                if en_rmode != "not_found" and en_docs_and_scores:
                    docs = [d for d, s in en_docs_and_scores]
                    context_str = "\\n---\\n".join([d.page_content for d in docs[:4]])
                    
                    formatted_prompt = prompt_tmpl.format(context=context_str, question=original_query, user_language=lang_name)
                    llm_result = llm.invoke(formatted_prompt)
                    answer = llm_result.content.strip()
                    top_ref = docs[0].metadata.get("reference", "1:1")
                    source = "translated_from_en"
                    tier_matched = 3
                    
                    usage = extract_token_usage(llm_result, formatted_prompt)
                    tokens_used += usage["total"]
            except Exception as e:
                print(f"Translation Fallback Failed: {e}", flush=True)

    # --- Step 3: General AI Fallback ---
    if tier_matched == 0:
        if is_overview and book_code in OFFLINE_OVERVIEWS and lang_code == "en":
            answer = OFFLINE_OVERVIEWS[book_code]
            source = "dataset_native"
            is_general_knowledge = True
        else:
            if rate_limited or tokens_data["pending_tokens"] <= 0:
                answer = "Token quota exhausted or rate limit active. Please try again later."
                source = "dataset_native"
            else:
                if active_provider == "gemini" and GEMINI_KEY:
                    import google.generativeai as genai
                    genai.configure(api_key=GEMINI_KEY)
                    gemini_model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
                    # Enable native Google Search Grounding (Disabled due to SDK limitation)
                    model = genai.GenerativeModel(model_name=gemini_model_name)
                    try:
                        if is_overview:
                            formatted_prompt = f"You are the scholarly Bible Study Chatbot for 'Vachan Study'. Please provide a comprehensive, scholarly, and structured overview of the Bible book '{book_code}' strictly IN {lang_name}. Cover Historical Background, Key Themes, and Outline. State at the end: 'Note: This response comes from my general knowledge database.'"
                        else:
                            formatted_prompt = f"You are the scholarly Bible Study Chatbot. Please answer the following question strictly IN {lang_name} using your general knowledge: {original_query}"
                            
                        response = model.generate_content(formatted_prompt)
                        answer = response.text.strip()
                        source = "ai_fallback"
                        is_general_knowledge = True
                        
                        # Approximate tokens
                        tokens_used += max(1, int(len(formatted_prompt)/4)) + max(1, int(len(answer)/4))
                    except Exception as e:
                        print(f"Native Gemini Fallback Failed: {e}", flush=True)
                        if docs_and_scores:
                            answer = docs_and_scores[0][0].metadata.get("response", "")
                            source = "dataset_native"
                else:
                    llm = get_llm_instance(active_provider)
                    if llm:
                        try:
                            if is_overview:
                                formatted_prompt = f"You are the scholarly Bible Study Chatbot for 'Vachan Study'. Please provide a comprehensive, scholarly, and structured overview of the Bible book '{book_code}' strictly IN {lang_name}. Cover Historical Background, Key Themes, and Outline. State at the end: 'Note: This response comes from my general knowledge database.'"
                            else:
                                formatted_prompt = f"You are the scholarly Bible Study Chatbot. Please answer the following question strictly IN {lang_name} using your general knowledge: {original_query}"
                                
                            llm_result = llm.invoke(formatted_prompt)
                            answer = llm_result.content.strip()
                            source = "ai_fallback"
                            is_general_knowledge = True
                            
                            usage = extract_token_usage(llm_result, formatted_prompt)
                            tokens_used += usage["total"]
                        except Exception as e:
                            print(f"AI Fallback Failed: {e}", flush=True)
                            if docs_and_scores:
                                answer = docs_and_scores[0][0].metadata.get("response", "")
                                source = "dataset_native"

    # Clean up disclaimers
    for d in [DISCLAIMER_UNFOLDING, DISCLAIMER_AI, "⚠️ *This is an AI-generated response based on the unfoldingWord dataset.*", "🤖 *This response based on the unfoldingWord dataset.*"]:
        if d in answer:
            answer = answer.replace(d, "").strip()
            
    if tokens_used > 0:
        stats = check_and_update_rate_limits()
        stats["total_tokens_used"] += tokens_used
        stats["pending_tokens"] = max(0, stats["pending_tokens"] - tokens_used)
        save_tokens_data(stats)

    excluded_set = {normalize_text(q) for q in (request.history or []) + [original_query]}
    suggested = []
    for doc in docs:
        q = doc.metadata.get("question")
        if q:
            norm_q = normalize_text(q)
            if norm_q not in excluded_set and q not in suggested:
                suggested.append(q)
                
    defaults = ["What does the text teach?", "Explain the passage further", "What are the key themes?"]
    for d in defaults:
        if len(suggested) >= 3:
            break
        if normalize_text(d) not in excluded_set and d not in suggested:
            suggested.append(d)

    return ChatResponse(
        answer=answer,
        reference=top_ref,
        suggested_questions=suggested[:3],
        is_general_knowledge=is_general_knowledge,
        tokens_used=tokens_used,
        total_tokens_used=stats.get("total_tokens_used", 0),
        pending_tokens=stats.get("pending_tokens", 0),
        requests_today=stats.get("requests_today", 0),
        requests_this_minute=stats.get("requests_this_minute", 0),
        source=source
    )

class QARecord(BaseModel):
    Reference: str
    Question: str
    Response: str

class BookDatasetResponse(BaseModel):
    book: str
    total_questions: int
    data: List[QARecord]

@app.get("/api/dataset/{book}", response_model=BookDatasetResponse)
async def get_book_dataset(book: str):
    book_code = normalize_book_code(book).upper()
    
    # Check paths: 1. data/en_tq/tq_{book}.tsv, 2. static_data/tq_{book}.csv, 3. static_data/tq_MAT.csv
    tsv_filename = f"tq_{book_code}.tsv"
    tsv_path = os.path.join(DATA_DIR, "en_tq", tsv_filename)
    
    if not os.path.exists(tsv_path):
        # Look in static_data for book csv
        csv_filename = f"tq_{book_code}.csv"
        csv_path = os.path.join(STATIC_DATA_DIR, csv_filename)
        if os.path.exists(csv_path):
            tsv_path = csv_path
        else:
            # Fall back to Matthew
            tsv_path = os.path.join(STATIC_DATA_DIR, "tq_MAT.csv")
            
    if not os.path.exists(tsv_path):
        raise HTTPException(status_code=404, detail=f"No dataset found for book {book_code}")
        
    try:
        is_tsv = tsv_path.endswith('.tsv')
        records = []
        with open(tsv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter='\t' if is_tsv else ',')
            
            # Normalize column names
            normalized_fieldnames = []
            for field in (reader.fieldnames or []):
                field_clean = field.strip()
                if field_clean.lower() == 'reference': field_clean = 'Reference'
                elif field_clean.lower() == 'question': field_clean = 'Question'
                elif field_clean.lower() == 'response': field_clean = 'Response'
                normalized_fieldnames.append(field_clean)
            reader.fieldnames = normalized_fieldnames
            
            for row in reader:
                records.append({
                    "Reference": str(row.get("Reference") or "1:1").strip() or "1:1",
                    "Question": str(row.get("Question") or "").strip(),
                    "Response": str(row.get("Response") or "").strip()
                })
            
        return BookDatasetResponse(
            book=book_code,
            total_questions=len(records),
            data=records
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read dataset: {str(e)}")


class TokenStatusResponse(BaseModel):
    total_tokens_used: int
    pending_tokens: int
    limit: int
    requests_today: int
    requests_this_minute: int
    rpm_limit: int = 15
    rpd_limit: int = 1500

@app.get("/api/tokens", response_model=TokenStatusResponse)
async def get_tokens_endpoint():
    # Dry check resets
    data = load_tokens_data()
    now = time.time()
    
    # Check day reset
    if now - data.get("last_day_reset_time", 0.0) >= 86400:
        data["requests_today"] = 0
        data["last_day_reset_time"] = now
        data["pending_tokens"] = data["limit"]
        save_tokens_data(data)
        
    # Check minute reset
    if now - data.get("last_minute_reset_time", 0.0) >= 60:
        data["requests_this_minute"] = 0
        data["last_minute_reset_time"] = now
        save_tokens_data(data)
        
    return TokenStatusResponse(
        total_tokens_used=data["total_tokens_used"],
        pending_tokens=data["pending_tokens"],
        limit=data["limit"],
        requests_today=data["requests_today"],
        requests_this_minute=data["requests_this_minute"]
    )

@app.post("/api/tokens/reset", response_model=TokenStatusResponse)
async def reset_tokens_endpoint():
    default_data = {
        "total_tokens_used": 0,
        "pending_tokens": 1000000,
        "limit": 1000000,
        "requests_today": 0,
        "requests_this_minute": 0,
        "last_minute_reset_time": time.time(),
        "last_day_reset_time": time.time()
    }
    save_tokens_data(default_data)
    print("RAG System: Token metrics reset to defaults successfully.")
    return TokenStatusResponse(
        total_tokens_used=default_data["total_tokens_used"],
        pending_tokens=default_data["pending_tokens"],
        limit=default_data["limit"],
        requests_today=default_data["requests_today"],
        requests_this_minute=default_data["requests_this_minute"]
    )

from dotenv import set_key

class EnvUpdateRequest(BaseModel):
    key: str
    value: str

@app.post("/api/settings/env")
async def update_env(request: EnvUpdateRequest):
    allowed_keys = ["OPENAI_API_KEY", "GEMINI_API_KEY", "OPENAI_MODEL", "GEMINI_MODEL"]
    if request.key not in allowed_keys:
        raise HTTPException(status_code=400, detail="Invalid environment variable key")
    
    env_path = os.path.join(BACKEND_DIR, ".env")
    try:
        set_key(env_path, request.key, request.value)
    except Exception as e:
        print(f"RAG System: Failed to write to .env file ({e})")
        
    os.environ[request.key] = request.value
    
    global GEMINI_KEY, OPENAI_KEY
    if request.key == "GEMINI_API_KEY":
        GEMINI_KEY = request.value
    elif request.key == "OPENAI_API_KEY":
        OPENAI_KEY = request.value
        
    return {"status": "success", "message": f"{request.key} updated successfully"}

def normalize_book_code(book: str) -> str:
    book_clean = book.upper().replace(" ", "").replace("_", "").strip()
    mapping = {
        "GENESIS": "GEN", "EXODUS": "EXO", "LEVITICUS": "LEV", "NUMBERS": "NUM", "DEUTERONOMY": "DEU",
        "JOSHUA": "JOS", "JUDGES": "JDG", "RUTH": "RUT", "1SAMUEL": "1SA", "2SAMUEL": "2SA",
        "1KINGS": "1KI", "2KINGS": "2KI", "1CHRONICLES": "1CH", "2CHRONICLES": "2CH", "EZRA": "EZR",
        "NEHEMIAH": "NEH", "ESTHER": "EST", "JOB": "JOB", "PSALMS": "PSA", "PSALM": "PSA", "PROVERBS": "PRO",
        "ECCLESIASTES": "ECC", "SONGOFSOLOMON": "SNG", "SONGOFSONGS": "SNG", "CANTICLES": "SNG",
        "ISAIAH": "ISA", "JEREMIAH": "JER", "LAMENTATIONS": "LAM", "EZEKIEL": "EZK", "DANIEL": "DAN",
        "HOSEA": "HOS", "JOEL": "JOL", "AMOS": "AMO", "OBADIAH": "OBA", "JONAH": "JON",
        "MICAH": "MIC", "NAHUM": "NAM", "HABAKKUK": "HAB", "ZEPHANIAH": "ZEP", "HAGGAI": "HAG",
        "ZECHARIAH": "ZEC", "MALACHI": "MAL",
        "MATTHEW": "MAT", "MARK": "MRK", "LUKE": "LUK", "JOHN": "JHN", "ACTS": "ACT",
        "ROMANS": "ROM", "1CORINTHIANS": "1CO", "2CORINTHIANS": "2CO", "GALATIANS": "GAL",
        "EPHESIANS": "EPH", "PHILIPPIANS": "PHP", "COLOSSIANS": "COL", "1THESSALONIANS": "1TH",
        "2THESSALONIANS": "2TH", "1TIMOTHY": "1TI", "2TIMOTHY": "2TI", "TITUS": "TIT",
        "PHILEMON": "PHM", "HEBREWS": "HEB", "JAMES": "JAS", "1PETER": "1PE", "2PETER": "2PE",
        "1JOHN": "1JN", "2JOHN": "2JN", "3JOHN": "3JN", "JUDE": "JUD", "REVELATION": "REV", "APOCALYPSE": "REV"
    }
    return mapping.get(book_clean, book_clean[:3])

def parse_html_to_verses(html: str) -> list:
    """Splits API.Bible HTML into verse objects."""
    matches = list(re.finditer(r'<span[^>]*data-number="(\d+)"[^>]*>.*?</span>', html))
    
    if not matches:
        matches = list(re.finditer(r'<span[^>]*class="v"[^>]*>(\d+)</span>', html))
        
    verses = []
    if not matches:
        clean_text = re.sub(r'<[^>]+>', ' ', html).strip()
        clean_text = re.sub(r'\s+', ' ', clean_text)
        if clean_text:
            verses.append({"verse": 1, "text": clean_text})
        return verses
        
    for i, match in enumerate(matches):
        verse_num = int(match.group(1))
        start_pos = match.end()
        end_pos = matches[i+1].start() if i + 1 < len(matches) else len(html)
        
        verse_html = html[start_pos:end_pos]
        verse_text = re.sub(r'<[^>]+>', ' ', verse_html).strip()
        verse_text = re.sub(r'\s+', ' ', verse_text)
        
        if verse_text:
            verses.append({"verse": verse_num, "text": verse_text})
            
    return verses

@app.get("/api/scripture/{book}/{chapter}")
async def get_scripture(book: str, chapter: int):
    print(f"API Scripture Fetch: {book} Chapter {chapter}")
    book_code = normalize_book_code(book)
    
    # 1. Zero-Latency synchronous file read from static_data bundle
    json_filename = f"bible_{book_code}.json"
    json_path = os.path.join(STATIC_DATA_DIR, json_filename)
    
    if os.path.exists(json_path):
        try:
            print(f"Bible Asset Sync Read: Loading pre-compiled '{book_code}' JSON...")
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # If the JSON contains a single chapter matching the requested one
            if isinstance(data, dict):
                if data.get("chapter") == chapter:
                    print(f"Bible Asset Sync Read Success: Loaded '{book_code}' Chapter {chapter}!")
                    return data
                elif "chapters" in data:
                    # Filter and extract specific chapter from multi-chapter book JSON
                    for ch in data["chapters"]:
                        if ch.get("chapter") == chapter:
                            print(f"Bible Asset Sync Read Success: Extracted '{book_code}' Chapter {chapter}!")
                            return {
                                "book": data.get("book", book_code),
                                "chapter": chapter,
                                "reference": ch.get("reference", f"{book_code} {chapter}"),
                                "verses": ch.get("verses", [])
                            }
        except Exception as e:
            print(f"Bible Asset Sync Read Exception ({e}). Falling back to live fetching...")

    # 2. Dynamic failsafe fallback: Fetch from live API.Bible if key is set
    if BIBLE_API_KEY:
        try:
            base_url = BIBLE_API_URL
            if "/v1" not in base_url:
                base_url = f"{base_url}/v1"
                
            api_url = f"{base_url}/bibles/{BIBLE_ID}/chapters/{book_code}.{chapter}?content-type=html&include-notes=false&include-titles=false"
            print(f"Bible API Dynamic Fetch: Requesting live scripture from {api_url}...")
            
            req = urllib.request.Request(
                api_url,
                headers={
                    "api-key": BIBLE_API_KEY,
                    "User-Agent": "VachanStudyBibleChatbot/1.0"
                }
            )
            
            with urllib.request.urlopen(req, timeout=8) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                
            html_content = res_data.get("data", {}).get("content", "")
            reference = res_data.get("data", {}).get("reference", f"{book_code} {chapter}")
            
            if html_content:
                parsed_verses = parse_html_to_verses(html_content)
                if parsed_verses:
                    print(f"Bible API Dynamic Fetch Success: Loaded {len(parsed_verses)} verses dynamically!")
                    return {
                        "book": book_code,
                        "chapter": chapter,
                        "reference": reference,
                        "verses": parsed_verses
                    }
        except Exception as e:
            print(f"Bible API Dynamic Fetch Exception ({e}). Serving placeholder context...")

    # 3. Static placeholder fallback if all else fails
    return {
        "book": book_code,
        "chapter": chapter,
        "reference": f"{book.capitalize()} {chapter}",
        "verses": [
            {"verse": 1, "text": f"This is placeholder scripture context for {book.capitalize()} chapter {chapter} verse 1."},
            {"verse": 2, "text": f"This is placeholder scripture context for {book.capitalize()} chapter {chapter} verse 2."}
        ]
    }

if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    reload_flag = os.environ.get("RELOAD", "True").lower() == "true"
    print(f"RAG Server: Starting Uvicorn on {host}:{port} (reload={reload_flag})...")
    uvicorn.run("api.index:app", host=host, port=port, reload=reload_flag)
