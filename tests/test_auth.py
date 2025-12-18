"""
Tests for authentication router.
"""
import pytest
from fastapi.testclient import TestClient


class TestAuthRegister:
    """Tests for user registration."""

    def test_register_success(self, client: TestClient):
        """Test successful user registration."""
        response = client.post("/auth/register", json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "securepass123",
            "initial_bankroll": 10000.0,
            "risk_profile": "balanced"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "test@example.com"
        assert data["user"]["username"] == "testuser"

    def test_register_short_password(self, client: TestClient):
        """Test registration with too short password."""
        response = client.post("/auth/register", json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "short",
            "initial_bankroll": 10000.0,
            "risk_profile": "balanced"
        })
        assert response.status_code == 400
        assert "8 characters" in response.json()["detail"]

    def test_register_short_username(self, client: TestClient):
        """Test registration with too short username."""
        response = client.post("/auth/register", json={
            "email": "test@example.com",
            "username": "ab",
            "password": "securepass123",
            "initial_bankroll": 10000.0,
            "risk_profile": "balanced"
        })
        assert response.status_code == 400
        assert "3 characters" in response.json()["detail"]

    def test_register_duplicate_email(self, client: TestClient):
        """Test registration with duplicate email."""
        # First registration
        client.post("/auth/register", json={
            "email": "test@example.com",
            "username": "testuser1",
            "password": "securepass123"
        })
        # Duplicate email
        response = client.post("/auth/register", json={
            "email": "test@example.com",
            "username": "testuser2",
            "password": "securepass123"
        })
        assert response.status_code == 400

    def test_register_duplicate_username(self, client: TestClient):
        """Test registration with duplicate username."""
        # First registration
        client.post("/auth/register", json={
            "email": "test1@example.com",
            "username": "testuser",
            "password": "securepass123"
        })
        # Duplicate username
        response = client.post("/auth/register", json={
            "email": "test2@example.com",
            "username": "testuser",
            "password": "securepass123"
        })
        assert response.status_code == 400


class TestAuthLogin:
    """Tests for user login."""

    @pytest.fixture
    def registered_user(self, client: TestClient):
        """Create a registered user."""
        response = client.post("/auth/register", json={
            "email": "login@example.com",
            "username": "loginuser",
            "password": "securepass123"
        })
        return response.json()

    def test_login_with_email(self, client: TestClient, registered_user):
        """Test login with email."""
        response = client.post("/auth/login", json={
            "email_or_username": "login@example.com",
            "password": "securepass123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_login_with_username(self, client: TestClient, registered_user):
        """Test login with username."""
        response = client.post("/auth/login", json={
            "email_or_username": "loginuser",
            "password": "securepass123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_login_wrong_password(self, client: TestClient, registered_user):
        """Test login with wrong password."""
        response = client.post("/auth/login", json={
            "email_or_username": "login@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with nonexistent user."""
        response = client.post("/auth/login", json={
            "email_or_username": "nonexistent@example.com",
            "password": "anypassword"
        })
        assert response.status_code == 401


class TestAuthSession:
    """Tests for session management."""

    @pytest.fixture
    def auth_tokens(self, client: TestClient):
        """Get auth tokens from registration."""
        response = client.post("/auth/register", json={
            "email": "session@example.com",
            "username": "sessionuser",
            "password": "securepass123"
        })
        return response.json()

    def test_get_current_user(self, client: TestClient, auth_tokens):
        """Test getting current user info."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "session@example.com"

    def test_get_current_user_no_auth(self, client: TestClient):
        """Test getting current user without auth."""
        response = client.get("/auth/me")
        assert response.status_code == 401

    def test_get_current_user_invalid_token(self, client: TestClient):
        """Test getting current user with invalid token."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401

    def test_validate_token(self, client: TestClient, auth_tokens):
        """Test token validation."""
        response = client.get(
            "/auth/validate",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True

    def test_validate_invalid_token(self, client: TestClient):
        """Test validation with invalid token."""
        response = client.get(
            "/auth/validate",
            headers={"Authorization": "Bearer invalid"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False

    def test_refresh_token(self, client: TestClient, auth_tokens):
        """Test token refresh."""
        response = client.post("/auth/refresh", json={
            "refresh_token": auth_tokens["refresh_token"]
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_logout(self, client: TestClient, auth_tokens):
        """Test logout."""
        response = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
        )
        assert response.status_code == 200

        # Token should be invalid after logout
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
        )
        assert response.status_code == 401


class TestChangePassword:
    """Tests for password change."""

    @pytest.fixture
    def auth_tokens(self, client: TestClient):
        """Get auth tokens from registration."""
        response = client.post("/auth/register", json={
            "email": "password@example.com",
            "username": "passworduser",
            "password": "oldpassword123"
        })
        return response.json()

    def test_change_password_success(self, client: TestClient, auth_tokens):
        """Test successful password change."""
        response = client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"},
            json={
                "current_password": "oldpassword123",
                "new_password": "newpassword456"
            }
        )
        assert response.status_code == 200

        # Login with new password
        response = client.post("/auth/login", json={
            "email_or_username": "password@example.com",
            "password": "newpassword456"
        })
        assert response.status_code == 200

    def test_change_password_wrong_current(self, client: TestClient, auth_tokens):
        """Test password change with wrong current password."""
        response = client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"},
            json={
                "current_password": "wrongpassword",
                "new_password": "newpassword456"
            }
        )
        assert response.status_code == 400

    def test_change_password_short_new(self, client: TestClient, auth_tokens):
        """Test password change with too short new password."""
        response = client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"},
            json={
                "current_password": "oldpassword123",
                "new_password": "short"
            }
        )
        assert response.status_code == 400
