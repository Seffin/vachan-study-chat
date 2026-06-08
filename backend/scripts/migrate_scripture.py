import os
import sys
import json
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPTS_DIR)
STATIC_DATA_DIR = os.path.join(BACKEND_DIR, "static_data")

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    print("Error: MONGO_URI is missing in .env")
    sys.exit(1)

def migrate_scripture():
    print("Connecting to MongoDB Atlas...")
    client = MongoClient(MONGO_URI)
    db = client["vachan_study"]
    collection = db["scripture_text"]
    
    # We will migrate MAT (Matthew)
    book_code = "MAT"
    
    json_path = os.path.join(STATIC_DATA_DIR, f"bible_{book_code}.json")
    if not os.path.exists(json_path):
        print(f"File not found: {json_path}")
        sys.exit(1)
        
    print(f"Reading data from {json_path}...")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    docs_to_insert = []
    
    if isinstance(data, dict):
        if "chapter" in data:
            # Single chapter JSON format
            doc = {
                "book": book_code,
                "chapter": data["chapter"],
                "verses": data.get("verses", [])
            }
            docs_to_insert.append(doc)
        elif "chapters" in data:
            # Multi-chapter JSON format
            for ch in data["chapters"]:
                doc = {
                    "book": book_code,
                    "chapter": ch.get("chapter"),
                    "verses": ch.get("verses", [])
                }
                docs_to_insert.append(doc)
                
    if docs_to_insert:
        print(f"Inserting {len(docs_to_insert)} chapters into MongoDB Atlas...")
        for doc in docs_to_insert:
            collection.update_one(
                {"book": doc["book"], "chapter": doc["chapter"]},
                {"$set": doc},
                upsert=True
            )
        print("Scripture migration complete!")
    else:
        print("No scripture documents found to insert.")

if __name__ == "__main__":
    migrate_scripture()
