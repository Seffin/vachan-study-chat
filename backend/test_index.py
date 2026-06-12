import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import MONGO_URI
from pymongo import MongoClient

client = MongoClient(MONGO_URI)
db = client["vachan_study"]

try:
    indexes = list(db.qa_dataset.list_search_indexes())
    print("Search Indexes:", indexes)
except Exception as e:
    print("Error getting search indexes:", e)
