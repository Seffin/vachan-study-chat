import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import MONGO_URI
from pymongo import MongoClient

client = MongoClient(MONGO_URI)
db = client["vachan_study"]
doc = db.qa_dataset.find_one({"book_code": "GEN"})
if doc:
    print("Doc ID:", doc.get("_id"))
    print("lang_code:", doc.get("lang_code"))
    print("book_code:", doc.get("book_code"))
    print("embedding len:", len(doc.get("embedding", [])))
else:
    print("No document found for GEN")
