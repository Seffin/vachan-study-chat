import asyncio
import os
import sys

# Add backend directory to sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from db.mongodb import connect_to_mongo, close_mongo_connection
from db.user_repository import UserRepository

async def seed_default_user():
    """Seed the default user into the database."""
    print("Connecting to MongoDB...")
    await connect_to_mongo()
    
    print("Checking for default_user...")
    default_user = await UserRepository.get_by_username("default_user")
    
    if not default_user:
        try:
            print("Creating default_user...")
            await UserRepository.create_user({
                "username": "default_user",
                "email": "default@example.com",
                "password": "Default@123"
            })
            print("Successfully seeded default_user with password Default@123")
        except Exception as e:
            print(f"Failed to seed default_user: {e}")
    else:
        print("default_user already exists.")
        
    await close_mongo_connection()
    print("Done.")

if __name__ == "__main__":
    asyncio.run(seed_default_user())
