import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import MONGO_URI
from pymongo import MongoClient

client = MongoClient(MONGO_URI)
db = client["vachan_study"]
db.qa_dataset.drop()
print("qa_dataset successfully dropped!")
