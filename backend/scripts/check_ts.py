import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load explicitly from the backend directory
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

async def check():
    uri = os.getenv("MONGO_URI")
    if not uri:
        print("MONGO_URI not found.")
        return
        
    client = AsyncIOMotorClient(uri)
    db = client["vachan_study"]
    collections = await db.list_collections()
    async for c in collections:
        name = c["name"]
        options = c.get("options", {})
        if "timeseries" in options:
            print(f"[TS] {name} is a TIME SERIES collection.")
        else:
            print(f"[OK] {name} is a standard collection.")

if __name__ == "__main__":
    asyncio.run(check())
