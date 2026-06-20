"""
Authentication routes: login, register.
"""

import sys
import os

from fastapi import APIRouter, HTTPException, Request, status

# Use absolute imports — schemas/ and db/ sit alongside app/ under backend/
from schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    ErrorResponse,
)
from app.core.security import (
    verify_password,
    hash_password,
    create_access_token,
    create_session_id,
    check_rate_limit,
    record_failed_attempt,
    clear_rate_limit,
)
from app.core.config import settings
from db.user_repository import UserRepository

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
async def login(request: Request):
    """
    Authenticate user and return JWT token.

    - Validates credentials
    - Enforces rate limiting (5 attempts / 15 min)
    - Returns JWT on success
    """
    # Parse body manually so we can return 400 instead of Pydantic's 422
    body = await request.json()
    username = body.get("username", "")
    password = body.get("password", "")

    # Validate empty fields → 400
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required",
        )

    # Validate password length → 400
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )

    # Check rate limit → 429
    if not check_rate_limit(username):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

    # Find user
    user = await UserRepository.get_by_username(username)

    if not user or not verify_password(password, user["password_hash"]):
        record_failed_attempt(username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Clear rate limit on success
    clear_rate_limit(username)

    # Session management — enforce single active session
    session_id = create_session_id()
    await UserRepository.update_session_id(username, session_id)

    # Create token with session_id
    token = create_access_token(
        {"user_id": str(user["_id"]), "username": user["username"], "session_id": session_id}
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse(
            user_id=str(user["_id"]),
            username=user["username"],
            email=user.get("email", ""),
        ),
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(request: RegisterRequest):
    """
    Register a new user.

    - Creates user with hashed password
    - Returns user info (no token — must login)
    """
    # Check if username exists
    existing = await UserRepository.get_by_username(request.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    # Check if email exists
    existing_email = await UserRepository.get_by_email(request.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user
    user = await UserRepository.create_user(
        {
            "username": request.username,
            "email": request.email,
            "password_hash": hash_password(request.password),
        }
    )

    return UserResponse(
        user_id=str(user["_id"]),
        username=user["username"],
        email=user["email"],
    )