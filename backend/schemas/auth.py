"""
Authentication request/response schemas.
"""

from typing import Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=8)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    user_id: str
    username: str
    email: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400  # 24 hours
    user: Optional[UserResponse] = None


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


# Aliases for backward compatibility
UserLogin = LoginRequest
UserCreate = RegisterRequest