"""
Chat routes for Bible study interactions.
"""

from fastapi import APIRouter, Depends

from app.core.security import get_current_user

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("/")
async def chat(
    request: dict,
    current_user: dict = Depends(get_current_user),
):
    """
    Process a chat message and return AI response.

    Requires authentication via JWT token.
    """
    book = request.get("book", "")
    message = request.get("message", "")

    # TODO: Integrate with existing chat logic in services/
    return {
        "response": "This is a placeholder response. Integrate with your existing chat logic.",
        "book": book,
        "source": "dataset_native",
        "verses_highlighted": [],
        "diagram": None,
    }


@router.get("/history/{book_code}")
async def get_history(
    book_code: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get chat history for a specific book.

    Requires authentication via JWT token.
    """
    # TODO: Implement history retrieval
    return []