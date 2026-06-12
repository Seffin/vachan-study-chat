"""
Vachan Study Bible Chatbot — Migration Script
Migrates dataset from CSV to MongoDB `qa_dataset` collection.
Initializes structure for paraphrases and multi-embeddings.
"""

import os
import sys
import pandas as pd
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPTS_DIR)
DATA_DIR = os.path.join(BACKEND_DIR, "data")
STATIC_DATA_DIR = os.path.join(BACKEND_DIR, "static_data")

MONGO_URI = os.getenv("MONGO_URI")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

if not MONGO_URI:
    print("Error: MONGO_URI is missing in .env")
    sys.exit(1)


def get_embeddings_model():
    if not GEMINI_KEY:
        print("Warning: GEMINI_API_KEY is missing. Skipping embedding generation.")
        return None
    try:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        return GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", google_api_key=GEMINI_KEY)
    except ImportError:
        from langchain_google_genai import GoogleGenAIEmbeddings
        return GoogleGenAIEmbeddings(model="models/gemini-embedding-001", google_api_key=GEMINI_KEY)


def migrate_vectors():
    print("Connecting to MongoDB Atlas...")
    client = MongoClient(MONGO_URI)
    db = client["vachan_study"]
    collection = db["qa_dataset"]
    
    embeddings_model = get_embeddings_model()
    
    # We will migrate MAT (Matthew) first as a proof of concept.
    book_code = "MAT"
    lang_code = "en"
    
    csv_path = os.path.join(STATIC_DATA_DIR, f"tq_{book_code}.csv")
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        sys.exit(1)
        
    print(f"Reading data from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    docs_to_insert = []
    
    for index, row in df.iterrows():
        question = str(row.get("Question", "")).strip()
        response = str(row.get("Response", "")).strip()
        reference = str(row.get("Reference", "1:1")).strip()
        
        if not question or not response:
            continue
            
        # Parse chapter and verse
        chapter = 1
        verse = 1
        if ":" in reference:
            parts = reference.split(":")
            chapter = int(parts[0]) if parts[0].isdigit() else 1
            verse = int(parts[1]) if parts[1].isdigit() else 1
            
        doc = {
            "book_code": book_code,
            "lang_code": lang_code,
            "reference": reference,
            "chapter": chapter,
            "verse": verse,
            "question": question,
            "response": response,
            "paraphrases": [],
            "search_text": question, # Initial search text is just the question
            "metadata": {
                "source": "unfoldingWord_tq"
            }
        }
        docs_to_insert.append(doc)

    print(f"Total documents to process: {len(docs_to_insert)}")
    
    if embeddings_model:
        import time
        batch_size = 20
        i = 0
        while i < len(docs_to_insert):
            batch = docs_to_insert[i:i+batch_size]
            texts = [f"Question: {d['question']}\nAnswer: {d['response']}" for d in batch]
            print(f"Embedding batch {i} to {i+len(batch)}...")
            
            success = False
            retries = 0
            while not success and retries < 5:
                try:
                    vectors = embeddings_model.embed_documents(texts)
                    for j, doc in enumerate(batch):
                        doc["embedding"] = vectors[j]
                        
                    success = True
                    i += batch_size
                    time.sleep(6)
                except Exception as e:
                    retries += 1
                    wait_time = 15 * retries
                    print(f"Network or API Error ({e}). Sleeping {wait_time}s before retry {retries}/5...")
                    time.sleep(wait_time)
                    
            if not success:
                print(f"Failed to embed batch {i} after 5 retries. Aborting.")
                sys.exit(1)
        
    if docs_to_insert:
        print(f"Inserting {len(docs_to_insert)} documents into MongoDB Atlas 'qa_dataset'...")
        for doc in docs_to_insert:
            collection.update_one(
                {"book_code": doc["book_code"], "lang_code": doc["lang_code"], "question": doc["question"]},
                {"$set": doc},
                upsert=True
            )
        print("Migration complete!")
    else:
        print("No documents to insert.")

if __name__ == "__main__":
    migrate_vectors()
