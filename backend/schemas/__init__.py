"""Schemas package for request/response models."""

from .auth import (
    LoginRequest, RegisterRequest, TokenResponse,
    UserResponse, ErrorResponse,
    UserLogin, UserCreate,  # Aliases
)
from .requests import ChatRequest, ChatMessage
from .responses import ChatResponse

__all__ = [
    "LoginRequest", "RegisterRequest", "TokenResponse",
    "UserResponse", "ErrorResponse",
    "UserLogin", "UserCreate",
    "ChatRequest", "ChatMessage", "ChatResponse",
]
