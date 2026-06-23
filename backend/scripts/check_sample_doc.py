"""
Quick diagnostic: inspect a sample document from qa_dataset to see what fields exist.
"""

import os
import sys
from pathlib import Path
from pprint import pprint

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

print(f"Total documents: {collection.count_documents({}):,}")
print()

# Get a sample document
sample = collection.find_one()
if not sample:
    print("Collection is truly empty (no documents at all).")
    sys.exit(0)

print("SAMPLE DOCUMENT KEYS:")
print("-" * 60)
for key in sorted(sample.keys()):
    value = sample[key]
    type_name = type(value).__name__
    if key == "embedding":
        preview = f"list of {len(value)} floats (first 3: {value[:3]})"
    elif isinstance(value, str):
        preview = f"'{value[:100]}{'...' if len(value) > 100 else ''}'"
    else:
        preview = str(value)[:100]
    print(f"  {key:20s} ({type_name:>12s}): {preview}")

print()
print("SAMPLE DOCUMENT (full):")
print("-" * 60)
# Remove embedding for readability
sample_readable = {k: v for k, v in sample.items() if k != "embedding"}
pprint(sample_readable, width=120)

client.close()
