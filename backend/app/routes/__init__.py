"""Routes package for the API."""

from .auth import router as auth_router
from .chat import router as chat_router
from .analytics import router as analytics_router

__all__ = ["auth_router", "chat_router", "analytics_router"]