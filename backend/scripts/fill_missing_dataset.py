"""
Vachan Study — Fill Missing Dataset Documents (Free Tier Optimized)
Identifies missing Q&A pairs from TSV files and generates embeddings ONLY for
those missing ones, using the 10-key Gemini rotation system.

Usage:
    cd backend
    python scripts/fill_missing_dataset.py

Free Tier Math:
    Missing: ~1,340 embeddings
    10 keys × 15 RPM = 150 RPM max
    Time: ~9 minutes (plus key rotation delays on 429s)
"""

import os
import sys
import time
import pandas as pd
from pathlib import Path
from datetime import datetime
from collections import Counter

SCRIPTS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPTS_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

from pymongo import MongoClient
from services.key_rotation import get_key_rotator

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    print("ERROR: MONGO_URI not found in .env")
    sys.exit(1)

TSV_DIR = BACKEND_DIR / "data" / "en_tq"
OUTPUT_DIM = 768


def get_db():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return client["vachan_study"]


def get_existing_questions(collection, book_code: str) -> set:
    """Get all existing questions for a book to avoid duplicates."""
    docs = collection.find({"book_code": book_code}, {"question": 1, "_id": 0})
    return {d["question"] for d in docs}


def read_tsv_missing(book_code: str, existing: set) -> list:
    """Read TSV and return only documents NOT already in MongoDB."""
    tsv_path = TSV_DIR / f"tq_{book_code}.tsv"
    if not tsv_path.exists():
        return []
    
    df = pd.read_csv(tsv_path, sep="\t")
    missing = []
    
    for _, row in df.iterrows():
        question = str(row.get("Question", "")).strip()
        response = str(row.get("Response", "")).strip()
        reference = str(row.get("Reference", "1:1")).strip()
        
        if not question or not response:
            continue
        
        # Skip if already in MongoDB
        if question in existing:
            continue
        
        chapter = 1
        if ":" in reference:
            try:
                chapter = int(reference.split(":")[0])
            except ValueError:
                chapter = 1
        
        missing.append({
            "book_code": book_code,
            "chapter": chapter,
            "verse": 1,
            "reference": reference,
            "question": question,
            "response": response,
            "lang_code": "en",
            "search_text": f"{reference} {question} {response}",
            "paraphrases": [],
            "metadata": {
                "source": "unfoldingWord_tq",
                "imported_from": "tsv_direct",
                "imported_at": datetime.utcnow().isoformat(),
            }
        })
    
    return missing


def embed_batch(texts: list, rotator) -> list:
    """Generate embeddings using Gemini with automatic key rotation."""
    if not texts:
        return []
    
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    
    max_attempts = max(rotator.total_keys, 1)
    
    for attempt in range(max_attempts):
        key = rotator.get_active_key()
        if not key:
            print(f"  No keys available. Waiting 60s...")
            time.sleep(60)
            continue
        
        try:
            model = GoogleGenerativeAIEmbeddings(
                model="models/gemini-embedding-001",
                google_api_key=key,
                output_dimensionality=OUTPUT_DIM,
            )
            embeddings = model.embed_documents(texts)
            rotator.report_success()
            return embeddings
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "rate limit" in err_str or "quota" in err_str or "exhausted" in err_str:
                rotator.report_rate_limited()
                print(f"  Key rate limited (attempt {attempt + 1}/{max_attempts}). Rotating...")
                time.sleep(5)
            else:
                print(f"  Embedding error: {e}")
                raise
    
    # All keys exhausted
    print(f"  All keys exhausted for this batch. Waiting 60s and retrying...")
    time.sleep(60)
    return embed_batch(texts, rotator)


def main():
    db = get_db()
    collection = db["qa_dataset"]
    rotator = get_key_rotator()
    
    # Ensure indexes
    collection.create_index([("book_code", 1), ("lang_code", 1)])
    collection.create_index([("book_code", 1), ("chapter", 1)])
    
    print("=" * 70)
    print("FILLING MISSING DATASET DOCUMENTS (Free Tier Optimized)")
    print("=" * 70)
    
    # Find all TSV files
    tsv_files = sorted(TSV_DIR.glob("tq_*.tsv"))
    print(f"Found {len(tsv_files)} TSV files\n")
    
    total_missing = 0
    total_inserted = 0
    total_api_calls = 0
    start_time = time.time()
    
    for tsv_path in tsv_files:
        book_code = tsv_path.stem.replace("tq_", "")
        
        # Get existing questions for this book
        existing = get_existing_questions(collection, book_code)
        
        # Find missing documents
        missing_docs = read_tsv_missing(book_code, existing)
        
        if not missing_docs:
            continue
        
        print(f"[{book_code}] Missing: {len(missing_docs):,} docs | Existing: {len(existing):,}")
        
        # Process in batches of 15 (1 RPM per key, 10 keys = safe)
        batch_size = 15
        inserted = 0
        
        for i in range(0, len(missing_docs), batch_size):
            batch = missing_docs[i:i + batch_size]
            texts = [d["search_text"] for d in batch]
            
            # Generate embeddings
            embeddings = embed_batch(texts, rotator)
            total_api_calls += len(batch)
            
            # Attach embeddings and insert
            for j, doc in enumerate(batch):
                doc["embedding"] = embeddings[j]
                
                collection.update_one(
                    {
                        "book_code": doc["book_code"],
                        "lang_code": doc["lang_code"],
                        "question": doc["question"],
                    },
                    {"$set": doc},
                    upsert=True,
                )
                inserted += 1
            
            # Rate limit safety: brief sleep between batches
            time.sleep(0.5)
        
        print(f"  Inserted {inserted} new documents")
        total_missing += len(missing_docs)
        total_inserted += inserted
    
    elapsed = time.time() - start_time
    
    print(f"\n{'='*70}")
    print(f"COMPLETE!")
    print(f"  Missing documents found: {total_missing:,}")
    print(f"  Documents inserted:      {total_inserted:,}")
    print(f"  API calls made:          {total_api_calls:,}")
    print(f"  Time elapsed:            {elapsed/60:.1f} minutes")
    print(f"  Collection total:        {collection.count_documents({}):,} docs")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
