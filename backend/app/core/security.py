"""
Security utilities: JWT tokens, password hashing, rate limiting, auth dependency.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
import jwt
import bcrypt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .config import settings


# ---------------------------------------------------------------------------
# In-memory rate limit store (use Redis in production)
# ---------------------------------------------------------------------------
_rate_limit_store: Dict[str, list] = {}

security_scheme = HTTPBearer()


def create_session_id() -> str:
    """Generate a unique session ID."""
    import uuid
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


# Aliases used by test_auth_system and core/__init__
get_password_hash = hash_password


# ---------------------------------------------------------------------------
# JWT tokens
# ---------------------------------------------------------------------------

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> dict:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


# Alias used by conftest / tests
verify_token = decode_token


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

def check_rate_limit(user_identifier: str) -> bool:
    """
    Check if user has exceeded rate limit.
    Returns True if allowed, False if rate limited.
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=settings.LOGIN_RATE_LIMIT_WINDOW_MINUTES)

    # Get or initialize attempts list
    if user_identifier not in _rate_limit_store:
        _rate_limit_store[user_identifier] = []

    # Filter out old attempts
    _rate_limit_store[user_identifier] = [
        attempt for attempt in _rate_limit_store[user_identifier]
        if attempt > window_start
    ]

    # Check if limit exceeded
    if len(_rate_limit_store[user_identifier]) >= settings.LOGIN_RATE_LIMIT_ATTEMPTS:
        return False

    return True


def record_failed_attempt(user_identifier: str) -> None:
    """Record a failed login attempt."""
    now = datetime.now(timezone.utc)

    if user_identifier not in _rate_limit_store:
        _rate_limit_store[user_identifier] = []

    _rate_limit_store[user_identifier].append(now)


def clear_rate_limit(user_identifier: str) -> None:
    """Clear rate limit after successful login."""
    if user_identifier in _rate_limit_store:
        del _rate_limit_store[user_identifier]


def reset_rate_limit_store() -> None:
    """Reset entire rate limit store (for testing)."""
    _rate_limit_store.clear()


# ---------------------------------------------------------------------------
# Auth dependency — extracts current user from JWT
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> dict:
    """FastAPI dependency: get current authenticated user from JWT."""
    payload = decode_token(credentials.credentials)

    # Lazy import to avoid circular dependency
    from db.user_repository import UserRepository

    user = await UserRepository.get_by_id(payload.get("user_id", ""))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user