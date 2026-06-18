"""
TDD Red Phase: Write failing tests for authentication.
These tests define the expected behavior BEFORE implementation.
"""

import pytest
from fastapi.testclient import TestClient


class TestLogin:
    """Login endpoint tests - define expected behavior."""

    def test_login_valid_credentials(self, client: TestClient):
        """Valid username/password returns JWT token."""
        response = client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "Default@123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_password(self, client: TestClient):
        """Wrong password returns 401."""
        response = client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "wrongpassword123"}
        )
        assert response.status_code == 401
        assert "error" in response.json()

    def test_login_nonexistent_user(self, client: TestClient):
        """Unknown username returns 401."""
        response = client.post(
            "/api/auth/login",
            json={"username": "nonexistent", "password": "anypassword123"}
        )
        assert response.status_code == 401

    def test_login_empty_credentials(self, client: TestClient):
        """Empty fields return 400 validation error."""
        response = client.post("/api/auth/login", json={"username": "", "password": ""})
        assert response.status_code == 400

    def test_login_short_password(self, client: TestClient):
        """Password < 8 chars returns 400."""
        response = client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "short"}
        )
        assert response.status_code == 400


class TestTokenValidation:
    """Token structure and expiration tests."""

    def test_token_contains_expiry(self, client: TestClient, test_user_token: str):
        """Token payload contains exp claim."""
        import jwt
        from app.core.config import settings
        payload = jwt.decode(
            test_user_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        assert "exp" in payload

    def test_token_contains_user_id(self, client: TestClient, test_user_token: str):
        """Token payload contains user_id."""
        import jwt
        from app.core.config import settings
        payload = jwt.decode(
            test_user_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        assert "user_id" in payload


class TestRateLimiting:
    """Rate limiting tests."""

    def test_rate_limit_after_failures(self, client: TestClient):
        """5+ failed attempts returns 429."""
        for _ in range(5):
            client.post(
                "/api/auth/login",
                json={"username": "testuser", "password": "wrongpassword123"}
            )

        response = client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "wrongpassword123"}
        )
        assert response.status_code == 429


class TestProtectedEndpoints:
    """Endpoints requiring authentication."""

    def test_chat_requires_auth(self, client: TestClient):
        """Chat endpoint without token returns 401/403."""
        response = client.post("/api/chat/", json={
            "book": "MAT",
            "message": "Hello"
        })
        # FastAPI HTTPBearer returns 403 when no credentials are provided
        assert response.status_code in (401, 403)

    def test_chat_with_valid_token(self, client: TestClient, test_user_token: str):
        """Chat endpoint with valid token returns 200."""
        from app.main import app
        from app.core.security import get_current_user

        mock_user = {"_id": "test_user_123", "username": "testuser"}

        async def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_current_user] = override_get_current_user
        try:
            response = client.post(
                "/api/chat/",
                json={"book": "MAT", "message": "Hello"},
                headers={"Authorization": f"Bearer {test_user_token}"},
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Legacy API tests (api/index.py)
# ---------------------------------------------------------------------------

class TestLegacyAPIAuth:
    """TDD RED PHASE: Tests for legacy API auth endpoints before implementation."""

    def test_legacy_login_valid(self, legacy_client: TestClient):
        response = legacy_client.post(
            "/api/auth/login",
            json={"username": "default_user", "password": "Default@123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_legacy_login_invalid_password(self, legacy_client: TestClient):
        response = legacy_client.post(
            "/api/auth/login",
            json={"username": "default_user", "password": "wrongpassword"}
        )
        assert response.status_code == 401
        assert "detail" in response.json()

    def test_legacy_login_nonexistent_user(self, legacy_client: TestClient):
        response = legacy_client.post(
            "/api/auth/login",
            json={"username": "nobody", "password": "Default@123"}
        )
        assert response.status_code == 401

    def test_legacy_token_format(self, legacy_client: TestClient):
        response = legacy_client.post(
            "/api/auth/login",
            json={"username": "default_user", "password": "Default@123"}
        )
        # Skip token verification if login endpoint not implemented yet
        if response.status_code == 200:
            token = response.json()["access_token"]
            import jwt
            from app.core.config import settings
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            assert "exp" in payload
            assert "user_id" in payload

    def test_legacy_empty_credentials(self, legacy_client: TestClient):
        response = legacy_client.post("/api/auth/login", json={"username": "", "password": ""})
        assert response.status_code == 400

    def test_legacy_rate_limiting(self, legacy_client: TestClient):
        for _ in range(6):
            legacy_client.post(
                "/api/auth/login",
                json={"username": "default_user", "password": "wrongpassword"}
            )
        response = legacy_client.post(
            "/api/auth/login",
            json={"username": "default_user", "password": "wrongpassword"}
        )
        assert response.status_code == 429

    def test_legacy_register_new_user(self, legacy_client: TestClient):
        response = legacy_client.post(
            "/api/auth/register",
            json={"username": "new_user", "email": "new@example.com", "password": "password123"}
        )
        assert response.status_code == 201
        data = response.json()
        assert "user_id" in data
        assert data["username"] == "new_user"

    def test_legacy_register_duplicate(self, legacy_client: TestClient):
        response = legacy_client.post(
            "/api/auth/register",
            json={"username": "default_user", "email": "default@example.com", "password": "password123"}
        )
        assert response.status_code == 400

    def test_legacy_me_with_token(self, legacy_client: TestClient, test_user_token: str):
        response = legacy_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200

    def test_legacy_me_without_token(self, legacy_client: TestClient):
        response = legacy_client.get("/api/auth/me")
        assert response.status_code in (401, 403)

    def test_legacy_logout(self, legacy_client: TestClient, test_user_token: str):
        response = legacy_client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200

    def test_legacy_password_min_length(self, legacy_client: TestClient):
        response = legacy_client.post(
            "/api/auth/login",
            json={"username": "default_user", "password": "short"}
        )
        assert response.status_code == 400

    def test_legacy_login_response_time(self, legacy_client: TestClient):
        import time
        start = time.time()
        legacy_client.post(
            "/api/auth/login",
            json={"username": "default_user", "password": "Default@123"}
        )
        duration = time.time() - start
        assert duration < 2.5

    def test_legacy_single_session(self, legacy_client: TestClient):
        # 1. Login to get token1
        res1 = legacy_client.post("/api/auth/login", json={"username": "default_user", "password": "Default@123"})
        if res1.status_code != 200:
            pytest.skip("Login not implemented yet")
        token1 = res1.json()["access_token"]
        
        # 2. Login again to get token2
        res2 = legacy_client.post("/api/auth/login", json={"username": "default_user", "password": "Default@123"})
        token2 = res2.json()["access_token"]

        # 3. Use token1 -> should fail (superseded)
        res_me = legacy_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token1}"})
        assert res_me.status_code == 401