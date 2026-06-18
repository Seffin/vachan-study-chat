"""
Pytest fixtures for authentication tests.
"""

import pytest
import time
import jwt
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.security import create_access_token, hash_password, reset_rate_limit_store


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

TEST_USER = {
    "_id": "test_user_123",
    "username": "testuser",
    "email": "test@example.com",
    "password_hash": hash_password("Default@123"),
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_rate_limits():
    """Reset rate limit store before each test."""
    reset_rate_limit_store()
    yield
    reset_rate_limit_store()


@pytest.fixture
def client():
    """FastAPI test client with mocked UserRepository."""
    _app_session_store: dict = {}
    
    mock_get_by_username = AsyncMock(
        side_effect=lambda username: {**TEST_USER, "session_id": _app_session_store.get(username)} if username == "testuser" else None
    )
    mock_get_by_id = AsyncMock(
        side_effect=lambda uid: TEST_USER if uid == "test_user_123" else None
    )
    mock_update_session_id = AsyncMock(
        side_effect=lambda username, session_id: _app_session_store.update({username: session_id}) or True
    )

    with patch("app.routes.auth.UserRepository") as mock_repo:
        mock_repo.get_by_username = mock_get_by_username
        mock_repo.get_by_id = mock_get_by_id
        mock_repo.update_session_id = mock_update_session_id
        yield TestClient(app)


@pytest.fixture
def legacy_client():
    """FastAPI test client for the legacy api/index.py backend with stateful session tracking."""
    from api.index import app as legacy_app
    
    # Mutable state to track session_id per user (simulates real DB behavior)
    _session_store: dict = {}
    
    class MockUserRepository:
        @staticmethod
        async def get_by_username(username):
            if username == "testuser":
                user = {**TEST_USER}
            elif username == "default_user":
                user = {**TEST_USER, "username": "default_user", "password_hash": hash_password("Default@123")}
            else:
                return None
            # Attach current session_id from store
            if username in _session_store:
                user["session_id"] = _session_store[username]
            return user
            
        @staticmethod
        async def get_by_id(uid):
            return TEST_USER if uid == "test_user_123" else None
            
        @staticmethod
        async def create_user(data):
            return {**data, "_id": "new_user_123"}
            
        @staticmethod
        async def update_session_id(username, session_id):
            _session_store[username] = session_id
            return True
            
        @staticmethod
        async def clear_session(username):
            _session_store.pop(username, None)
            return True
            
        @staticmethod
        async def get_session_id(username):
            return _session_store.get(username)

    with patch("api.index.UserRepository", new=MockUserRepository):
        with patch("api.index.get_database") as mock_api_db:
            from unittest.mock import MagicMock
            mock_db = MagicMock()
            mock_api_db.return_value = mock_db
            
            async def mock_insert_one(*args, **kwargs):
                return type('obj', (object,), {'inserted_id': 'new_user_123'})
            mock_db.login_audit.insert_one = mock_insert_one
            
            yield TestClient(legacy_app)


@pytest.fixture
def test_user_token(legacy_client):
    """Returns a valid token obtained via actual login flow (with real session_id)."""
    response = legacy_client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "Default@123"}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    # Fallback for non-legacy tests
    payload = {
        "user_id": "test_user_123",
        "username": "testuser",
        "session_id": "test_session_123",
        "exp": int(time.time()) + 3600
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)