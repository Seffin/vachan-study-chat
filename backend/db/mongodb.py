import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "vachan_study"

class MongoDB:
    client: AsyncIOMotorClient = None
    db = None

db_instance = MongoDB()

async def connect_to_mongo():
    if not MONGO_URI:
        print("MongoDB: MONGO_URI is not set. Running without MongoDB.")
        return
        
    print(f"MongoDB: Connecting to database...")
    db_instance.client = AsyncIOMotorClient(MONGO_URI)
    db_instance.db = db_instance.client[DB_NAME]
    print("MongoDB: Connected.")

async def close_mongo_connection():
    if db_instance.client:
        print("MongoDB: Closing connection...")
        db_instance.client.close()
        print("MongoDB: Connection closed.")

def get_database():
    """Dependency injection to get the MongoDB database instance in FastAPI routes."""
    return db_instance.db
