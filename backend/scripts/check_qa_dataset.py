"""
Quick script to check how many books are in MongoDB qa_dataset collection.
Usage:
    cd backend
    python scripts/check_qa_dataset.py
"""

import os
import sys
from pathlib import Path
from collections import Counter

SCRIPTS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPTS_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    print("ERROR: MONGO_URI not found in .env")
    sys.exit(1)

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client["vachan_study"]
collection = db["qa_dataset"]

total_docs = collection.count_documents({})
books = collection.distinct("book_code")
lang_codes = collection.distinct("lang_code")

print(f"=" * 60)
print(f"QA_DATASET COLLECTION REPORT")
print(f"=" * 60)
print(f"Total documents:     {total_docs:,}")
print(f"Unique books:          {len(books)}/66")
print(f"Languages:             {', '.join(lang_codes)}")
print(f"")

if books:
    # Count per book
    pipeline = [
        {"$group": {"_id": "$book_code", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    book_counts = list(collection.aggregate(pipeline))
    
    print(f"Documents per book:")
    print(f"-" * 60)
    for item in book_counts:
        print(f"  {item['_id']:>5s}: {item['count']:>6,} docs")
    
    # Check if embeddings exist
    sample_with_embedding = collection.count_documents({"embedding": {"$exists": True}})
    sample_without_embedding = collection.count_documents({"embedding": {"$exists": False}})
    
    print(f"")
    print(f"Documents WITH embeddings:    {sample_with_embedding:,}")
    print(f"Documents WITHOUT embeddings: {sample_without_embedding:,}")
    
    # Check if vector search index exists
    indexes = collection.list_indexes()
    vector_index = [i for i in indexes if "vector" in str(i.get("key", {}))]
    text_index = [i for i in indexes if "text" in str(i.get("key", {}))]
    
    print(f"")
    print(f"Search indexes:")
    print(f"  Vector search index: {'FOUND' if vector_index else 'MISSING'}")
    print(f"  Text search index:   {'FOUND' if text_index else 'MISSING'}")
else:
    print("No books found in qa_dataset. Collection is empty.")

print(f"=" * 60)

client.close()
