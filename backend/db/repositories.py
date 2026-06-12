"""
Vachan Study Bible Chatbot — MongoDB Repositories
Data access layer for MongoDB collections.
"""

import csv
import os
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from config import DATA_DIR, STATIC_DATA_DIR, normalize_book_code
from db.mongodb import get_database


class ChatSessionRepository:
    """Repository for managing chat sessions and history."""
    
    @staticmethod
    async def get_history(book_code: str, user_id: str = "default_user") -> List[Dict[str, Any]]:
        db = get_database()
        if db is None:
            return []
            
        session_id = f"{user_id}_{book_code}"
        session = await db.chat_sessions.find_one({"session_id": session_id})
        
        if session and "history" in session:
            history = session["history"]
            frontend_messages = []
            for i, msg in enumerate(history):
                frontend_messages.append({
                    "id": f"{msg['sender']}-{session_id}-{i}",
                    "sender": msg["sender"],
                    "text": msg["text"],
                    "timestamp": msg.get("timestamp", ""),
                    "versesHighlighted": msg.get("versesHighlighted", []),
                    "source": msg.get("source", "dataset_native")
                })
            return frontend_messages
        return []

    @staticmethod
    async def save_turn(book_code: str, user_query: str, answer: str, top_ref: str, source: str, user_id: str = "default_user"):
        db = get_database()
        if db is None:
            return
            
        session_id = f"{user_id}_{book_code}"
        iso_timestamp = datetime.now(timezone.utc).isoformat()
        
        turn_history = [
            {
                "sender": "user",
                "text": user_query,
                "timestamp": iso_timestamp
            },
            {
                "sender": "ai",
                "text": answer,
                "timestamp": iso_timestamp,
                "versesHighlighted": [top_ref.split(":")[1]] if ":" in top_ref else [],
                "source": source
            }
        ]
        
        await db.chat_sessions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "user_id": user_id,
                    "book_code": book_code,
                    "updated_at": datetime.now(timezone.utc)
                },
                "$setOnInsert": {
                    "created_at": datetime.now(timezone.utc)
                },
                "$push": {
                    "history": {"$each": turn_history}
                }
            },
            upsert=True
        )

    @staticmethod
    async def delete_history(book_code: str, user_id: str = "default_user") -> bool:
        db = get_database()
        if db is None:
            raise Exception("Database connection not established.")
            
        session_id = f"{user_id}_{book_code}"
        result = await db.chat_sessions.delete_one({"session_id": session_id})
        return result.deleted_count > 0


class ScriptureRepository:
    """Repository for fetching and caching scripture text."""
    
    @staticmethod
    async def get_scripture(book_code: str, chapter: int) -> Optional[Dict[str, Any]]:
        db = get_database()
        if db is None:
            return None
            
        collection = db["scripture_text"]
        doc = await collection.find_one({"book": book_code, "chapter": chapter})
        
        if doc and "verses" in doc:
            return {
                "book": book_code,
                "chapter": chapter,
                "verses": doc["verses"],
                "source": "mongodb"
            }
        return None

    @staticmethod
    async def cache_scripture(book_code: str, chapter: int, reference: str, verses: List[Dict[str, Any]]):
        db = get_database()
        if db is None:
            return
            
        collection = db["scripture_text"]
        await collection.update_one(
            {"book": book_code, "chapter": chapter},
            {"$set": {
                "book": book_code,
                "chapter": chapter,
                "reference": reference,
                "verses": verses,
                "cached_at": datetime.now(timezone.utc)
            }},
            upsert=True
        )


class DatasetRepository:
    """Repository for offline dataset records (CSV/TSV fallback)."""
    
    @staticmethod
    def load_dataset_records(book_code: str) -> list:
        book_code = normalize_book_code(book_code).upper()
        tsv_filename = f"tq_{book_code}.tsv"
        tsv_path = os.path.join(DATA_DIR, "en_tq", tsv_filename)
        
        if not os.path.exists(tsv_path):
            csv_filename = f"tq_{book_code}.csv"
            csv_path = os.path.join(STATIC_DATA_DIR, csv_filename)
            if os.path.exists(csv_path):
                tsv_path = csv_path
            else:
                tsv_path = os.path.join(STATIC_DATA_DIR, "tq_MAT.csv")
                
        if not os.path.exists(tsv_path):
            return []
            
        try:
            is_tsv = tsv_path.endswith('.tsv')
            records = []
            with open(tsv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter='\t' if is_tsv else ',')
                
                normalized_fieldnames = []
                for field in (reader.fieldnames or []):
                    field_clean = field.strip()
                    if field_clean.lower() == 'reference': field_clean = 'Reference'
                    elif field_clean.lower() == 'question': field_clean = 'Question'
                    elif field_clean.lower() == 'response': field_clean = 'Response'
                    normalized_fieldnames.append(field_clean)
                reader.fieldnames = normalized_fieldnames
                
                for row in reader:
                    records.append({
                        "Reference": str(row.get("Reference") or "1:1").strip() or "1:1",
                        "Question": str(row.get("Question") or "").strip(),
                        "Response": str(row.get("Response") or "").strip()
                    })
            return records
        except Exception as e:
            print(f"Error loading dataset records: {e}")
            return []


class KeyRepository:
    """Repository for managing API keys and rate limit cooldowns in MongoDB."""
    
    @staticmethod
    def get_all_keys() -> List[Dict[str, Any]]:
        from db.mongodb import get_sync_database
        db = get_sync_database()
        if db is None:
            return []
            
        collection = db["api_keys"]
        keys = list(collection.find({"provider": "gemini"}))
        return keys

    @staticmethod
    def add_key(token: str) -> bool:
        from db.mongodb import get_sync_database
        db = get_sync_database()
        if db is None:
            return False
            
        collection = db["api_keys"]
        result = collection.update_one(
            {"token": token, "provider": "gemini"},
            {"$setOnInsert": {
                "token": token,
                "provider": "gemini",
                "cooldown_until": 0.0,
                "created_at": datetime.now(timezone.utc)
            }},
            upsert=True
        )
        return result.upserted_id is not None or result.matched_count > 0

    @staticmethod
    def mark_rate_limited(token: str, cooldown_seconds: int = 60) -> bool:
        import time
        from db.mongodb import get_sync_database
        db = get_sync_database()
        if db is None:
            return False
            
        collection = db["api_keys"]
        cooldown_timestamp = time.time() + cooldown_seconds
        result = collection.update_one(
            {"token": token, "provider": "gemini"},
            {"$set": {"cooldown_until": cooldown_timestamp}}
        )
        return result.modified_count > 0

    @staticmethod
    def report_success(token: str) -> bool:
        from db.mongodb import get_sync_database
        db = get_sync_database()
        if db is None:
            return False
            
        collection = db["api_keys"]
        result = collection.update_one(
            {"token": token, "provider": "gemini"},
            {"$set": {"cooldown_until": 0.0}}
        )
        return result.modified_count > 0


class MetricsRepository:
    """Repository for managing global AI token usage and system limits."""
    
    @staticmethod
    def _get_default_data() -> Dict[str, Any]:
        import time
        from config import TOKEN_BUDGET_DEFAULT
        return {
            "total_tokens_used": 0,
            "pending_tokens": TOKEN_BUDGET_DEFAULT,
            "limit": TOKEN_BUDGET_DEFAULT,
            "requests_today": 0,
            "requests_this_minute": 0,
            "last_minute_reset_time": time.time(),
            "last_day_reset_time": time.time()
        }

    @staticmethod
    def get_metrics() -> Dict[str, Any]:
        from db.mongodb import get_sync_database
        db = get_sync_database()
        default_data = MetricsRepository._get_default_data()
        
        if db is None:
            return default_data
            
        collection = db["system_metrics"]
        doc = collection.find_one({"_id": "global_metrics"})
        
        if not doc:
            # Create default document if it doesn't exist
            default_data["_id"] = "global_metrics"
            try:
                collection.insert_one(default_data)
            except Exception:
                pass
            return default_data
            
        # Ensure all default keys exist
        for key, val in default_data.items():
            if key not in doc:
                doc[key] = val
                
        return doc

    @staticmethod
    def save_metrics(data: Dict[str, Any]) -> bool:
        from db.mongodb import get_sync_database
        db = get_sync_database()
        if db is None:
            return False
            
        collection = db["system_metrics"]
        
        # Ensure _id is set correctly
        update_data = data.copy()
        if "_id" in update_data:
            del update_data["_id"]
            
        result = collection.update_one(
            {"_id": "global_metrics"},
            {"$set": update_data},
            upsert=True
        )
        return result.upserted_id is not None or result.modified_count > 0
