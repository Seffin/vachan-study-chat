"""
User repository for managing user accounts in MongoDB.
"""

from typing import Optional, Dict, Any
from .mongodb import get_database

import bcrypt


class UserRepository:
    """Repository for user account management."""

    @staticmethod
    async def get_by_username(username: str) -> Optional[Dict[str, Any]]:
        """Find user by username."""
        db = get_database()
        if db is None:
            return None
        user = await db.users.find_one({"username": username})
        return user

    @staticmethod
    async def get_by_email(email: str) -> Optional[Dict[str, Any]]:
        """Find user by email."""
        db = get_database()
        if db is None:
            return None
        user = await db.users.find_one({"email": email})
        return user

    @staticmethod
    async def get_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        """Find user by ID."""
        db = get_database()
        if db is None:
            return None
        user = await db.users.find_one({"_id": user_id})
        return user

    @staticmethod
    async def create_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new user with hashed password."""
        db = get_database()
        if db is None:
            raise Exception("Database connection not established")
            
        import uuid
        from datetime import datetime, timezone
        
        if "user_id" not in user_data:
            user_data["user_id"] = f"usr_{uuid.uuid4().hex[:12]}"
        if "created_at" not in user_data:
            user_data["created_at"] = datetime.now(timezone.utc)
        
        # Hash password before storing
        if "password" in user_data:
            user_data["password_hash"] = bcrypt.hashpw(
                user_data["password"].encode(), 
                bcrypt.gensalt()
            ).decode()
            del user_data["password"]  # Remove plaintext password
        
        result = await db.users.insert_one(user_data)
        user_data["_id"] = str(result.inserted_id)
        return user_data

    @staticmethod
    async def update_user(user_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update user information."""
        db = get_database()
        if db is None:
            return None
        
        result = await db.users.update_one(
            {"_id": user_id},
            {"$set": update_data}
        )
        
    @staticmethod
    async def update_session_id(username: str, session_id: str) -> bool:
        """Update the active session ID for a user."""
        db = get_database()
        if db is None:
            return False
        
        result = await db.users.update_one(
            {"username": username},
            {"$set": {"session_id": session_id}}
        )
        return result.modified_count > 0

    @staticmethod
    async def clear_session(username: str) -> bool:
        """Clear the active session ID (logout)."""
        db = get_database()
        if db is None:
            return False
        
        result = await db.users.update_one(
            {"username": username},
            {"$unset": {"session_id": ""}}
        )
        return result.modified_count > 0

    @staticmethod
    async def get_session_id(username: str) -> Optional[str]:
        """Get the current active session ID."""
        user = await UserRepository.get_by_username(username)
        if user:
            return user.get("session_id")
        return None