"""
Compare Q&A counts across three sources:
1. TSV files (source of truth)
2. FAISS indexes (pre-built)
3. MongoDB qa_dataset (deployed)

Shows which books are missing documents and by how much.
"""

import os
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPTS_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

from pymongo import MongoClient
import pandas as pd

MONGO_URI = os.getenv("MONGO_URI")
TSV_DIR = BACKEND_DIR / "data" / "en_tq"
FAISS_DIR = BACKEND_DIR / "static_data" / "vectorstores" / "gemini"

BOOK_CODES = [
    "GEN", "EXO", "LEV", "NUM", "DEU", "JOS", "JDG", "RUT", "1SA", "2SA",
    "1KI", "2KI", "1CH", "2CH", "EZR", "NEH", "EST", "JOB", "PSA", "PRO",
    "ECC", "SNG", "ISA", "JER", "LAM", "EZE", "DAN", "HOS", "JOE", "AMO",
    "OBA", "JON", "MIC", "NAH", "HAB", "ZEP", "HAG", "ZEC", "MAL",
    "MAT", "MRK", "LUK", "JHN", "ACT", "ROM", "1CO", "2CO", "GAL", "EPH",
    "PHP", "COL", "1TH", "2TH", "1TI", "2TI", "TIT", "PHM", "HEB", "JAS",
    "1PE", "2PE", "1JN", "2JN", "3JN", "JUD", "REV"
]

def count_tsv(book_code):
    tsv_path = TSV_DIR / f"tq_{book_code}.tsv"
    if not tsv_path.exists():
        return 0
    try:
        df = pd.read_csv(tsv_path, sep="\t")
        return len(df)
    except Exception:
        return 0

def count_faiss(book_code):
    faiss_path = FAISS_DIR / book_code / "index.faiss"
    if not faiss_path.exists():
        return 0
    try:
        import faiss
        index = faiss.read_index(str(faiss_path))
        return index.ntotal
    except Exception:
        return 0

def count_mongodb(collection, book_code):
    return collection.count_documents({"book_code": book_code})

def main():
    if not MONGO_URI:
        print("ERROR: MONGO_URI not found in .env")
        sys.exit(1)

    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client["vachan_study"]
    collection = db["qa_dataset"]

    print(f"{'='*80}")
    print(f"Q&A COUNT COMPARISON: TSV vs FAISS vs MongoDB")
    print(f"{'='*80}")
    print(f"{'Book':>5s} | {'TSV':>6s} | {'FAISS':>6s} | {'MongoDB':>8s} | {'TSV-FAISS':>10s} | {'FAISS-Mongo':>12s} | Status")
    print(f"-"*80)

    total_tsv = 0
    total_faiss = 0
    total_mongo = 0
    total_tsv_faiss_loss = 0
    total_faiss_mongo_loss = 0
    missing_books = []

    for book in BOOK_CODES:
        tsv_count = count_tsv(book)
        faiss_count = count_faiss(book)
        mongo_count = count_mongodb(collection, book)

        tsv_faiss_diff = tsv_count - faiss_count
        faiss_mongo_diff = faiss_count - mongo_count

        total_tsv += tsv_count
        total_faiss += faiss_count
        total_mongo += mongo_count
        total_tsv_faiss_loss += max(0, tsv_faiss_diff)
        total_faiss_mongo_loss += max(0, faiss_mongo_diff)

        if tsv_count == 0 and faiss_count == 0 and mongo_count == 0:
            status = "NO DATA"
            missing_books.append(book)
        elif tsv_faiss_diff > 0 or faiss_mongo_diff > 0:
            status = "MISMATCH"
        else:
            status = "OK"

        print(f"{book:>5s} | {tsv_count:>6,} | {faiss_count:>6,} | {mongo_count:>8,} | {tsv_faiss_diff:>+10,} | {faiss_mongo_diff:>+12,} | {status}")

    print(f"-"*80)
    print(f"{'TOTAL':>5s} | {total_tsv:>6,} | {total_faiss:>6,} | {total_mongo:>8,} | {total_tsv_faiss_loss:>+10,} | {total_faiss_mongo_loss:>+12,} |")
    print(f"{'='*80}")

    if missing_books:
        print(f"\nBooks with NO DATA at all: {', '.join(missing_books)}")

    print(f"\nBreakdown:")
    print(f"  TSV total:        {total_tsv:,}")
    print(f"  FAISS total:      {total_faiss:,}")
    print(f"  MongoDB total:    {total_mongo:,}")
    print(f"")
    print(f"  Lost TSV->FAISS:  {total_tsv_faiss_loss:,} (filtered during FAISS creation)")
    print(f"  Lost FAISS->Mongo: {total_faiss_mongo_loss:,} (skipped during import)")
    print(f"  Missing total:    {total_tsv - total_mongo:,} out of {total_tsv:,} ({(total_tsv - total_mongo)/total_tsv*100:.1f}%)")

    if total_faiss_mongo_loss > 0:
        print(f"\n  → Run the import script again to fix FAISS→MongoDB gap:")
        print(f"    python backend/scripts/import_faiss_to_mongodb.py")

    client.close()

if __name__ == "__main__":
    main()
