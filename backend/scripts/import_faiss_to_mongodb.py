"""
Vachan Study — Import Existing FAISS Vectorstores into MongoDB
Reads pre-built FAISS indexes (index.faiss + index.pkl) from
backend/static_data/vectorstores/gemini/ and imports all Q&A pairs
with their embeddings into MongoDB `qa_dataset`.

No API calls. No embedding regeneration. Fast.

Usage:
    cd backend
    python scripts/import_faiss_to_mongodb.py

Requires:
    - MONGO_URI in .env
    - faiss-cpu installed (pip install faiss-cpu)
    - Pickle files contain the expected metadata format
"""

import os
import sys
import pickle
import time
from pathlib import Path
from datetime import datetime

# Add backend to path
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

BOOK_CODES = [
    "GEN", "EXO", "LEV", "NUM", "DEU", "JOS", "JDG", "RUT", "1SA", "2SA",
    "1KI", "2KI", "1CH", "2CH", "EZR", "NEH", "EST", "JOB", "PSA", "PRO",
    "ECC", "SNG", "ISA", "JER", "LAM", "EZE", "DAN", "HOS", "JOE", "AMO",
    "OBA", "JON", "MIC", "NAH", "HAB", "ZEP", "HAG", "ZEC", "MAL",
    "MAT", "MRK", "LUK", "JHN", "ACT", "ROM", "1CO", "2CO", "GAL", "EPH",
    "PHP", "COL", "1TH", "2TH", "1TI", "2TI", "TIT", "PHM", "HEB", "JAS",
    "1PE", "2PE", "1JN", "2JN", "3JN", "JUD", "REV"
]


def get_db():
    """Get MongoDB database connection."""
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return client["vachan_study"]


def load_faiss_data(book_code: str):
    """Load FAISS index and pickle metadata for a book.
    
    Returns: (embeddings_list, metadata_list) or ([], []) if files missing.
    """
    book_dir = VECTORSTORE_DIR / book_code
    faiss_path = book_dir / "index.faiss"
    pkl_path = book_dir / "index.pkl"
    
    if not faiss_path.exists() or not pkl_path.exists():
        print(f"  {book_code}: Missing FAISS files. faiss={faiss_path.exists()}, pkl={pkl_path.exists()}")
        return [], []
    
    try:
        # Load FAISS index
        import faiss
        index = faiss.read_index(str(faiss_path))
        
        # Extract all embeddings from the index
        total = index.ntotal
        embeddings = []
        for i in range(total):
            vec = index.reconstruct(i)
            embeddings.append(vec.tolist())
        
        # Load metadata from pickle
        with open(pkl_path, "rb") as f:
            metadata = pickle.load(f)
        
        # The pickle might be a list of dicts or a FAISS-compatible docstore
        docs = []
        if isinstance(metadata, list):
            docs = metadata
        elif isinstance(metadata, dict):
            # FAISS docstore format: {docstore: {data: {...}}}
            docstore = metadata.get("docstore", metadata)
            if hasattr(docstore, "_dict"):
                docs = list(docstore._dict.values())
            elif isinstance(docstore, dict):
                docs = list(docstore.values())
            else:
                docs = [metadata]
        else:
            docs = []
        
        # Validate counts match
        if len(embeddings) != len(docs):
            print(f"  WARNING: {book_code} embedding count ({len(embeddings)}) != doc count ({len(docs)}). Using min.")
            count = min(len(embeddings), len(docs))
            embeddings = embeddings[:count]
            docs = docs[:count]
        
        return embeddings, docs
        
    except Exception as e:
        print(f"  ERROR loading {book_code}: {e}")
        return [], []


def parse_doc(doc, book_code: str) -> dict:
    """Parse a FAISS document into the MongoDB schema."""
    # Handle different formats
    if isinstance(doc, dict):
        page_content = doc.get("page_content", doc.get("content", ""))
        metadata = doc.get("metadata", {})
    else:
        # LangChain Document object
        page_content = getattr(doc, "page_content", str(doc))
        metadata = getattr(doc, "metadata", {})
    
    # Parse page_content format: "Question: ...\nAnswer: ..."
    question = ""
    response = ""
    
    if "Question:" in page_content and "Answer:" in page_content:
        q_part = page_content.split("Answer:")[0]
        question = q_part.replace("Question:", "").strip()
        response = page_content.split("Answer:", 1)[1].strip()
    else:
        # Fallback: use the whole content as question
        question = page_content[:200]
        response = page_content
    
    # Extract reference from metadata or question
    reference = metadata.get("reference", metadata.get("Reference", "1:1"))
    if not reference and ":" in question:
        # Try to extract from question like "What did God create in the beginning? (Genesis 1:1)"
        pass
    
    # Parse chapter
    chapter = 1
    if ":" in str(reference):
        try:
            chapter = int(str(reference).split(":")[0])
        except ValueError:
            chapter = 1
    
    return {
        "book": book_code,
        "chapter": chapter,
        "verse": str(reference) if reference else "1:1",
        "question": question,
        "response": response,
        "lang_code": "en",
        "search_text": question,
        "metadata": {
            "source": "unfoldingWord_tq",
            "imported_from": "faiss_vectorstore",
            "imported_at": datetime.utcnow().isoformat(),
        }
    }


def import_all_books():
    """Main import loop: all 66 books from FAISS to MongoDB."""
    db = get_db()
    collection = db["qa_dataset"]
    
    # Ensure indexes
    collection.create_index([("book", 1), ("lang_code", 1)])
    collection.create_index([("book", 1), ("chapter", 1)])
    print("Indexes ensured on (book, lang_code) and (book, chapter)")
    
    total_inserted = 0
    total_books = 0
    total_errors = 0
    start_time = time.time()
    
    for book_code in BOOK_CODES:
        print(f"\n[{book_code}] Loading FAISS data...")
        embeddings, docs = load_faiss_data(book_code)
        
        if not embeddings or not docs:
            print(f"  Skipping {book_code} (no data)")
            total_errors += 1
            continue
        
        print(f"  Loaded {len(docs)} docs with {len(embeddings)} embeddings")
        
        # Build MongoDB documents
        mongo_docs = []
        for i, doc in enumerate(docs):
            mongo_doc = parse_doc(doc, book_code)
            mongo_doc["embedding"] = embeddings[i]
            mongo_docs.append(mongo_doc)
        
        # Upsert in batches
        batch_size = 100
        inserted_count = 0
        
        for i in range(0, len(mongo_docs), batch_size):
            batch = mongo_docs[i:i + batch_size]
            
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
        
        print(f"  ✓ Imported {inserted_count} documents for {book_code}")
        total_inserted += inserted_count
        total_books += 1
    
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"Import complete!")
    print(f"  Books imported: {total_books}/{len(BOOK_CODES)}")
    print(f"  Total documents: {total_inserted}")
    print(f"  Books skipped: {total_errors}")
    print(f"  Time elapsed: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
    print(f"{'='*60}")


if __name__ == "__main__":
    import_all_books()
