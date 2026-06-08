import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "vachan_study"

async def setup_db():
    if not MONGO_URI:
        print("Error: MONGO_URI is not set in .env")
        return
        
    print(f"Connecting to MongoDB at {MONGO_URI}...")
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    
    # Define Schemas
    user_schema = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "created_at"],
            "properties": {
                "user_id": {"bsonType": "string"},
                "created_at": {"bsonType": "date"},
                "preferences": {"bsonType": "object"}
            }
        }
    }
    
    chat_session_schema = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["session_id", "user_id", "book_code", "history"],
            "properties": {
                "session_id": {"bsonType": "string"},
                "user_id": {"bsonType": "string"},
                "book_code": {"bsonType": "string"},
                "history": {
                    "bsonType": "array",
                    "items": {
                        "bsonType": "object",
                        "required": ["sender", "text", "timestamp"],
                        "properties": {
                            "sender": {"enum": ["user", "ai"]},
                            "text": {"bsonType": "string"},
                            "timestamp": {"bsonType": "string"},
                            "versesHighlighted": {"bsonType": "array", "items": {"bsonType": "string"}},
                            "source": {"bsonType": ["string", "null"]}
                        }
                    }
                },
                "created_at": {"bsonType": "date"},
                "updated_at": {"bsonType": "date"}
            }
        }
    }
    
    vector_schema = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["book_code", "lang_code", "reference", "question", "response", "embedding"],
            "properties": {
                "book_code": {"bsonType": "string"},
                "lang_code": {"bsonType": "string"},
                "reference": {"bsonType": "string"},
                "question": {"bsonType": "string"},
                "response": {"bsonType": "string"},
                "embedding": {
                    "bsonType": "array",
                    "items": {"bsonType": "double"}
                }
            }
        }
    }

    scripture_schema = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["book", "chapter", "verses"],
            "properties": {
                "book": {"bsonType": "string"},
                "chapter": {"bsonType": "int"},
                "verses": {
                    "bsonType": "array",
                    "items": {
                        "bsonType": "object",
                        "required": ["verse", "text"],
                        "properties": {
                            "verse": {"bsonType": "int"},
                            "text": {"bsonType": "string"}
                        }
                    }
                }
            }
        }
    }

    print("Configuring collections and schemas...")
    # Create collections with validation
    collections = await db.list_collection_names()
    
    if "users" not in collections:
        await db.create_collection("users", validator=user_schema)
    else:
        await db.command("collMod", "users", validator=user_schema)
        
    if "chat_sessions" not in collections:
        await db.create_collection("chat_sessions", validator=chat_session_schema)
    else:
        await db.command("collMod", "chat_sessions", validator=chat_session_schema)
        
    if "vector_embeddings" not in collections:
        await db.create_collection("vector_embeddings", validator=vector_schema)
    else:
        await db.command("collMod", "vector_embeddings", validator=vector_schema)
        
    if "scripture_text" not in collections:
        await db.create_collection("scripture_text", validator=scripture_schema)
    else:
        await db.command("collMod", "scripture_text", validator=scripture_schema)
        
    print("Creating indexes...")
    # Create indexes
    await db.users.create_index("user_id", unique=True)
    await db.chat_sessions.create_index("session_id", unique=True)
    await db.chat_sessions.create_index("user_id")
    await db.chat_sessions.create_index("book_code")
    await db.vector_embeddings.create_index([("book_code", 1), ("lang_code", 1)])
    await db.scripture_text.create_index([("book", 1), ("chapter", 1)])
    
    print("MongoDB setup complete with schemas and indexes!")

if __name__ == "__main__":
    asyncio.run(setup_db())
