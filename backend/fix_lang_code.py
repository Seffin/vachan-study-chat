import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import MONGO_URI
from pymongo import MongoClient

client = MongoClient(MONGO_URI)
db = client["vachan_study"]
result = db.qa_dataset.update_many({"lang_code": "eng"}, {"$set": {"lang_code": "en"}})
print(f"Updated {result.modified_count} documents from 'eng' to 'en'!")
