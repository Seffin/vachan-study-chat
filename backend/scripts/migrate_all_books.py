"""
Vachan Study — Full Dataset Migration Script
Migrates ALL 66 Bible books from TSV/CSV into MongoDB `qa_dataset` collection.
Generates 768-dim embeddings using Gemini with key rotation.

Usage:
    cd backend
    python scripts/migrate_all_books.py

Requires:
    - MONGO_URI in .env
    - GEMINI_API_KEY in .env (or 10 keys already in MongoDB api_keys)
    - TSV files in data/en_tq/ or CSV files in static_data/

Time estimate: ~2-3 hours for 18,000 Q&A pairs on free tier (10 keys × 15 RPM).
"""

import os
import sys
import time
import pandas as pd
from datetime import datetime
from pathlib import Path

# Add backend to path
SCRIPTS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPTS_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

from pymongo import MongoClient
from google import genai

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    print("ERROR: MONGO_URI not found in .env")
    sys.exit(1)

# Book code mapping (3-letter codes to names)
BOOK_CODES = [
    "GEN", "EXO", "LEV", "NUM", "DEU", "JOS", "JDG", "RUT", "1SA", "2SA",
    "1KI", "2KI", "1CH", "2CH", "EZR", "NEH", "EST", "JOB", "PSA", "PRO",
    "ECC", "SOS", "ISA", "JER", "LAM", "EZE", "DAN", "HOS", "JOE", "AMO",
    "OBA", "JON", "MIC", "NAH", "HAB", "ZEP", "HAG", "ZEC", "MAL",
    "MAT", "MRK", "LUK", "JHN", "ACT", "ROM", "1CO", "2CO", "GAL", "EPH",
    "PHP", "COL", "1TH", "2TH", "1TI", "2TI", "TIT", "PHM", "HEB", "JAS",
    "1PE", "2PE", "1JN", "2JN", "3JN", "JUD", "REV"
]

# Gemini embedding model
EMBEDDING_MODEL = "models/gemini-embedding-001"
OUTPUT_DIM = 768  # Matryoshka truncation


def get_db():
    """Get MongoDB database connection."""
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return client["vachan_study"]


def get_gemini_keys():
    """Fetch Gemini API keys from MongoDB. Fallback to env var."""
    db = get_db()
    keys = list(db["api_keys"].find({"provider": "gemini"}, {"key": 1, "_id": 0}))
    if keys:
        return [k["key"] for k in keys]
    
    # Fallback to env var
    env_key = os.getenv("GEMINI_API_KEY", "")
    if env_key:
        return [env_key]
    
    print("ERROR: No Gemini API keys found in MongoDB or .env")
    sys.exit(1)


def embed_with_rotation(texts: list, keys: list, key_index: int = 0) -> tuple:
    """Generate embeddings using Gemini with key rotation on 429.
    
    Uses LangChain GoogleGenerativeAIEmbeddings to match the deployed codebase.
    
    Returns: (embeddings_list, next_key_index, success)
    """
    if not texts:
        return [], key_index, True
    
    for attempt in range(len(keys)):
        current_key = keys[key_index % len(keys)]
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            model = GoogleGenerativeAIEmbeddings(
                model="models/gemini-embedding-001",
                google_api_key=current_key,
                output_dimensionality=OUTPUT_DIM,
            )
            embeddings = model.embed_documents(texts)
            return embeddings, key_index, True
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "rate limit" in err_str or "quota" in err_str or "exhausted" in err_str:
                print(f"  Key {key_index % len(keys)} rate limited. Rotating...")
                key_index = (key_index + 1) % len(keys)
                time.sleep(5)  # Brief cooldown before next key
            else:
                print(f"  Embedding error: {e}")
                raise
    
    # All keys exhausted
    return [], key_index, False


def read_book_data(book_code: str) -> list:
    """Read Q&A data for a book from TSV or CSV."""
    # Try TSV first (source of truth)
    tsv_path = BACKEND_DIR / "data" / "en_tq" / f"tq_{book_code}.tsv"
    csv_path = BACKEND_DIR / "static_data" / f"tq_{book_code}.csv"
    
    if tsv_path.exists():
        df = pd.read_csv(tsv_path, sep="\t")
    elif csv_path.exists():
        df = pd.read_csv(csv_path)
    else:
        print(f"  WARNING: No data file found for {book_code}")
        return []
    
    docs = []
    for _, row in df.iterrows():
        question = str(row.get("Question", "")).strip()
        response = str(row.get("Response", "")).strip()
        reference = str(row.get("Reference", "1:1")).strip()
        
        if not question or not response:
            continue
        
        # Parse chapter
        chapter = 1
        if ":" in reference:
            try:
                chapter = int(reference.split(":")[0])
            except ValueError:
                chapter = 1
        
        docs.append({
            "book": book_code,
            "chapter": chapter,
            "verse": reference,
            "question": question,
            "response": response,
            "lang_code": "en",
        })
    
    return docs


def migrate_all_books():
    """Main migration loop: all 66 books."""
    db = get_db()
    collection = db["qa_dataset"]
    
    # Ensure indexes exist
    collection.create_index([("book", 1), ("lang_code", 1)])
    collection.create_index([("book", 1), ("chapter", 1)])
    print("Indexes ensured on (book, lang_code) and (book, chapter)")
    
    keys = get_gemini_keys()
    print(f"Loaded {len(keys)} Gemini API keys for rotation")
    
    key_index = 0
    total_inserted = 0
    total_skipped = 0
    start_time = time.time()
    
    for book_code in BOOK_CODES:
        print(f"\n[{book_code}] Reading data...")
        docs = read_book_data(book_code)
        
        if not docs:
            print(f"  No data found. Skipping.")
            total_skipped += 1
            continue
        
        print(f"  Found {len(docs)} Q&A pairs. Generating embeddings...")
        
        # Process in batches of 20
        batch_size = 20
        inserted_count = 0
        
        for i in range(0, len(docs), batch_size):
            batch = docs[i:i + batch_size]
            texts = [f"Question: {d['question']}\nAnswer: {d['response']}" for d in batch]
            
            # Generate embeddings with key rotation
            embeddings, key_index, success = embed_with_rotation(texts, keys, key_index)
            
            if not success:
                print(f"  FAILED: All keys exhausted for batch {i}. Waiting 60s...")
                time.sleep(60)
                embeddings, key_index, success = embed_with_rotation(texts, keys, key_index)
                if not success:
                    print(f"  ABORTING {book_code} at batch {i}")
                    break
            
            # Add embeddings to docs
            for j, doc in enumerate(batch):
                doc["embedding"] = embeddings[j]
                doc["search_text"] = doc["question"]
                doc["metadata"] = {"source": "unfoldingWord_tq", "migrated_at": datetime.utcnow().isoformat()}
            
            # Upsert into MongoDB
            for doc in batch:
                collection.update_one(
                    {
                        "book": doc["book"],
                        "lang_code": doc["lang_code"],
                        "question": doc["question"],
                    },
                    {"$set": doc},
                    upsert=True,
                )
            
            inserted_count += len(batch)
            
            # Rate limit safety: sleep between batches
            time.sleep(1)
        
        print(f"  ✓ Inserted/updated {inserted_count} documents for {book_code}")
        total_inserted += inserted_count
    
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"Migration complete!")
    print(f"  Books processed: {len(BOOK_CODES) - total_skipped}/{len(BOOK_CODES)}")
    print(f"  Total documents: {total_inserted}")
    print(f"  Time elapsed: {elapsed/60:.1f} minutes")
    print(f"{'='*60}")


if __name__ == "__main__":
    migrate_all_books()
