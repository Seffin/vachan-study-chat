"""
Import missing books into MongoDB from FAISS vectorstores.
Handles the 3 books that had wrong codes in the diagnostic: Ezekiel (EZK), Joel (JOL), Nahum (NAM).

Usage:
    cd backend
    python scripts/import_missing_books.py
"""

import os
import sys
import pickle
import time
from pathlib import Path
from datetime import datetime

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

VECTORSTORE_DIR = BACKEND_DIR / "static_data" / "vectorstores" / "gemini"

# These 3 books had data but were missed due to code mismatch
MISSING_BOOKS = ["EZK", "JOL", "NAM"]  # Ezekiel, Joel, Nahum


def get_db():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return client["vachan_study"]


def load_faiss_book(book_code: str):
    """Load FAISS index and pickle for a specific book."""
    book_dir = VECTORSTORE_DIR / book_code
    faiss_path = book_dir / "index.faiss"
    pkl_path = book_dir / "index.pkl"
    
    if not faiss_path.exists() or not pkl_path.exists():
        print(f"  {book_code}: FAISS files missing")
        return [], []
    
    try:
        import faiss
        index = faiss.read_index(str(faiss_path))
        
        embeddings = []
        for i in range(index.ntotal):
            vec = index.reconstruct(i)
            embeddings.append(vec.tolist())
        
        with open(pkl_path, "rb") as f:
            metadata = pickle.load(f)
        
        docs = []
        if isinstance(metadata, list):
            docs = metadata
        elif isinstance(metadata, dict):
            docstore = metadata.get("docstore", metadata)
            if hasattr(docstore, "_dict"):
                docs = list(docstore._dict.values())
            elif isinstance(docstore, dict):
                docs = list(docstore.values())
            else:
                docs = [metadata]
        
        # Validate counts
        if len(embeddings) != len(docs):
            count = min(len(embeddings), len(docs))
            embeddings = embeddings[:count]
            docs = docs[:count]
        
        return embeddings, docs
        
    except Exception as e:
        print(f"  ERROR loading {book_code}: {e}")
        return [], []


def parse_doc(doc, book_code: str) -> dict:
    """Parse a FAISS document into MongoDB schema."""
    if isinstance(doc, dict):
        page_content = doc.get("page_content", doc.get("content", ""))
        metadata = doc.get("metadata", {})
    else:
        page_content = getattr(doc, "page_content", str(doc))
        metadata = getattr(doc, "metadata", {})
    
    question = ""
    response = ""
    
    if "Question:" in page_content and "Answer:" in page_content:
        q_part = page_content.split("Answer:")[0]
        question = q_part.replace("Question:", "").strip()
        response = page_content.split("Answer:", 1)[1].strip()
    else:
        question = page_content[:200]
        response = page_content
    
    reference = metadata.get("reference", metadata.get("Reference", "1:1"))
    
    chapter = 1
    if ":" in str(reference):
        try:
            chapter = int(str(reference).split(":")[0])
        except ValueError:
            chapter = 1
    
    return {
        "book_code": book_code,
        "chapter": chapter,
        "verse": 1,  # default, will be refined from reference
        "reference": str(reference) if reference else "1:1",
        "question": question,
        "response": response,
        "lang_code": "en",
        "search_text": page_content,
        "paraphrases": [],
        "metadata": {
            "source": "unfoldingWord_tq",
            "imported_from": "faiss_vectorstore",
            "imported_at": datetime.utcnow().isoformat(),
        }
    }


def import_book(collection, book_code: str) -> int:
    """Import one book from FAISS to MongoDB. Returns count inserted."""
    print(f"\n[{book_code}] Loading FAISS...")
    embeddings, docs = load_faiss_book(book_code)
    
    if not embeddings or not docs:
        print(f"  No data found. Skipping.")
        return 0
    
    print(f"  Loaded {len(docs)} docs with {len(embeddings)} embeddings")
    
    mongo_docs = []
    for i, doc in enumerate(docs):
        mongo_doc = parse_doc(doc, book_code)
        mongo_doc["embedding"] = embeddings[i]
        mongo_docs.append(mongo_doc)
    
    inserted = 0
    for doc in mongo_docs:
        result = collection.update_one(
            {
                "book_code": doc["book_code"],
                "lang_code": doc["lang_code"],
                "question": doc["question"],
            },
            {"$set": doc},
            upsert=True,
        )
        if result.upserted_id:
            inserted += 1
    
    print(f"  Inserted {inserted} new, updated {len(mongo_docs) - inserted} existing")
    return inserted


def main():
    db = get_db()
    collection = db["qa_dataset"]
    
    # Ensure indexes
    collection.create_index([("book_code", 1), ("lang_code", 1)])
    collection.create_index([("book_code", 1), ("chapter", 1)])
    
    print("=" * 60)
    print("IMPORTING MISSING BOOKS FROM FAISS TO MONGODB")
    print("=" * 60)
    
    # Check current counts before import
    print("\nBefore import:")
    for book in MISSING_BOOKS:
        count = collection.count_documents({"book_code": book})
        print(f"  {book}: {count} docs")
    
    total_inserted = 0
    for book in MISSING_BOOKS:
        total_inserted += import_book(collection, book)
    
    print("\n" + "=" * 60)
    print("After import:")
    for book in MISSING_BOOKS:
        count = collection.count_documents({"book_code": book})
        print(f"  {book}: {count} docs")
    
    print(f"\nTotal new documents inserted: {total_inserted}")
    print(f"Collection total: {collection.count_documents({}):,} docs")
    print("=" * 60)


if __name__ == "__main__":
    main()
