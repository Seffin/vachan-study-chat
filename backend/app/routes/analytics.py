"""
Analytics routes for tracking usage and study statistics.
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta

from app.core.security import get_current_user
from db.mongodb import get_database

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/usage", response_model=Dict[str, Any])
async def get_usage_stats(current_user: dict = Depends(get_current_user)):
    """
    Get user's usage statistics.

    Returns study time, books accessed, and other metrics.
    """
    db = get_database()
    user_id = str(current_user.get("_id", current_user.get("username", "unknown")))

    if db is None:
        return {
            "user_id": user_id,
            "total_sessions": 0,
            "total_time_minutes": 0,
            "books_accessed": [],
            "most_visited_books": []
        }

    # Query chat_sessions for this user
    sessions = await db.chat_sessions.find({
        "user_id": user_id
    }).to_list(length=1000)

    total_sessions = len(sessions)
    books_accessed = list({s.get("book_code", "") for s in sessions if s.get("book_code")})

    # Estimate study time from message count (avg 30 sec per message pair)
    total_messages = 0
    book_visit_counts = {}
    for s in sessions:
        history = s.get("history", [])
        total_messages += len(history)
        book = s.get("book_code", "Unknown")
        book_visit_counts[book] = book_visit_counts.get(book, 0) + 1

    total_time_minutes = round(total_messages * 0.5)

    # Most visited books (top 5)
    most_visited = sorted(
        [{"book": b, "sessions": c} for b, c in book_visit_counts.items()],
        key=lambda x: x["sessions"],
        reverse=True
    )[:5]

    return {
        "user_id": user_id,
        "total_sessions": total_sessions,
        "total_time_minutes": total_time_minutes,
        "books_accessed": books_accessed,
        "most_visited_books": most_visited
    }


@router.get("/daily", response_model=Dict[str, Any])
async def get_daily_stats(current_user: dict = Depends(get_current_user)):
    """
    Get daily study statistics.
    """
    db = get_database()
    user_id = str(current_user.get("_id", current_user.get("username", "unknown")))

    today = datetime.now(timezone.utc).date()
    today_start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    today_end = today_start + timedelta(days=1)

    if db is None:
        return {
            "date": today.isoformat(),
            "sessions": 0,
            "time_minutes": 0,
            "verses_read": 0
        }

    # Query sessions updated today for this user
    sessions = await db.chat_sessions.find({
        "user_id": user_id,
        "updated_at": {
            "$gte": today_start,
            "$lt": today_end
        }
    }).to_list(length=1000)

    total_messages = 0
    verses_read = 0
    for s in sessions:
        history = s.get("history", [])
        total_messages += len(history)
        for msg in history:
            if msg.get("versesHighlighted"):
                verses_read += len(msg["versesHighlighted"])

    time_minutes = round(total_messages * 0.5)

    return {
        "date": today.isoformat(),
        "sessions": len(sessions),
        "time_minutes": time_minutes,
        "verses_read": verses_read
    }
