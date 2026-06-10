import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from dotenv import load_dotenv
import certifi

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "vachan_study"

class MongoDB:
    client: AsyncIOMotorClient = None
    db = None
    sync_client: MongoClient = None
    sync_db = None

db_instance = MongoDB()

async def connect_to_mongo():
    if not MONGO_URI:
        print("MongoDB: MONGO_URI is not set. Running without MongoDB.")
        return
        
    print(f"MongoDB: Connecting to database...")
    db_instance.client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
    db_instance.db = db_instance.client[DB_NAME]
    
    db_instance.sync_client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    db_instance.sync_db = db_instance.sync_client[DB_NAME]
    
    print("MongoDB: Connected.")

async def close_mongo_connection():
    if db_instance.client:
        print("MongoDB: Closing connection...")
        db_instance.client.close()
    if db_instance.sync_client:
        db_instance.sync_client.close()
        print("MongoDB: Connection closed.")

def get_database():
    """Dependency injection to get the MongoDB database instance in FastAPI routes."""
    if db_instance.db is None and MONGO_URI:
        print("MongoDB: Lazy connecting to database (Serverless mode)...")
        # Use certifi for Vercel to avoid SSL: CERTIFICATE_VERIFY_FAILED
        db_instance.client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
        db_instance.db = db_instance.client[DB_NAME]
    return db_instance.db

def get_sync_database():
    """Dependency injection to get the synchronous MongoDB database instance."""
    if db_instance.sync_db is None and MONGO_URI:
        db_instance.sync_client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
        db_instance.sync_db = db_instance.sync_client[DB_NAME]
    return db_instance.sync_db
