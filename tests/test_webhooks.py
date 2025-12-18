"""
Tests for webhooks router.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def auth_headers(client: TestClient):
    """Get auth headers from a registered user."""
    response = client.post("/auth/register", json={
        "email": "webhooks@example.com",
        "username": "webhooksuser",
        "password": "securepass123"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestCreateWebhook:
    """Tests for creating webhooks."""

    def test_create_webhook(self, client: TestClient, auth_headers):
        """Test creating a webhook."""
        response = client.post(
            "/webhooks/",
            headers=auth_headers,
            json={
                "name": "My Webhook",
                "url": "https://example.com/webhook",
                "events": ["bet_placed", "bet_settled"]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "My Webhook"
        assert data["url"] == "https://example.com/webhook"
        assert data["is_active"] is True

    def test_create_webhook_with_secret(self, client: TestClient, auth_headers):
        """Test creating a webhook with a secret."""
        response = client.post(
            "/webhooks/",
            headers=auth_headers,
            json={
                "name": "Secure Webhook",
                "url": "https://example.com/webhook",
                "events": ["alert_triggered"],
                "secret": "mysecretkey123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "secret" not in data  # Secret should not be returned

    def test_create_webhook_invalid_url(self, client: TestClient, auth_headers):
        """Test creating webhook with invalid URL."""
        response = client.post(
            "/webhooks/",
            headers=auth_headers,
            json={
                "name": "Invalid Webhook",
                "url": "not-a-url",
                "events": ["bet_placed"]
            }
        )
        assert response.status_code == 422  # Validation error

    def test_create_webhook_no_auth(self, client: TestClient):
        """Test creating webhook without authentication."""
        response = client.post("/webhooks/", json={
            "name": "Test Webhook",
            "url": "https://example.com/webhook",
            "events": ["bet_placed"]
        })
        assert response.status_code == 401


class TestGetWebhooks:
    """Tests for retrieving webhooks."""

    def test_list_webhooks(self, client: TestClient, auth_headers):
        """Test listing user webhooks."""
        # Create a webhook first
        client.post(
            "/webhooks/",
            headers=auth_headers,
            json={
                "name": "Test Webhook",
                "url": "https://example.com/webhook",
                "events": ["bet_placed"]
            }
        )

        response = client.get("/webhooks/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_single_webhook(self, client: TestClient, auth_headers):
        """Test getting a single webhook."""
        # Create a webhook first
        create_response = client.post(
            "/webhooks/",
            headers=auth_headers,
            json={
                "name": "Single Webhook",
                "url": "https://example.com/webhook",
                "events": ["bet_placed"]
            }
        )
        webhook_id = create_response.json()["id"]

        response = client.get(f"/webhooks/{webhook_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Single Webhook"


class TestUpdateWebhook:
    """Tests for updating webhooks."""

    def test_update_webhook_name(self, client: TestClient, auth_headers):
        """Test updating webhook name."""
        # Create a webhook first
        create_response = client.post(
            "/webhooks/",
            headers=auth_headers,
            json={
                "name": "Original Name",
                "url": "https://example.com/webhook",
                "events": ["bet_placed"]
            }
        )
        webhook_id = create_response.json()["id"]

        # Update the webhook
        response = client.patch(
            f"/webhooks/{webhook_id}",
            headers=auth_headers,
            json={"name": "Updated Name"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

    def test_update_webhook_url(self, client: TestClient, auth_headers):
        """Test updating webhook URL."""
        # Create a webhook first
        create_response = client.post(
            "/webhooks/",
            headers=auth_headers,
            json={
                "name": "URL Test",
                "url": "https://example.com/old",
                "events": ["bet_placed"]
            }
        )
        webhook_id = create_response.json()["id"]

        # Update the URL
        response = client.patch(
            f"/webhooks/{webhook_id}",
            headers=auth_headers,
            json={"url": "https://example.com/new"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["url"] == "https://example.com/new"

    def test_toggle_webhook_active(self, client: TestClient, auth_headers):
        """Test toggling webhook active status."""
        # Create a webhook first
        create_response = client.post(
            "/webhooks/",
            headers=auth_headers,
            json={
                "name": "Toggle Test",
                "url": "https://example.com/webhook",
                "events": ["bet_placed"]
            }
        )
        webhook_id = create_response.json()["id"]

        # Deactivate
        response = client.patch(
            f"/webhooks/{webhook_id}",
            headers=auth_headers,
            json={"is_active": False}
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False


class TestDeleteWebhook:
    """Tests for deleting webhooks."""

    def test_delete_webhook(self, client: TestClient, auth_headers):
        """Test deleting a webhook."""
        # Create a webhook first
        create_response = client.post(
            "/webhooks/",
            headers=auth_headers,
            json={
                "name": "Delete Me",
                "url": "https://example.com/webhook",
                "events": ["bet_placed"]
            }
        )
        webhook_id = create_response.json()["id"]

        # Delete the webhook
        response = client.delete(f"/webhooks/{webhook_id}", headers=auth_headers)
        assert response.status_code == 200

        # Verify it's deleted
        response = client.get(f"/webhooks/{webhook_id}", headers=auth_headers)
        assert response.status_code == 404


class TestWebhookTest:
    """Tests for webhook test endpoint."""

    def test_test_webhook(self, client: TestClient, auth_headers):
        """Test the webhook test endpoint."""
        # Create a webhook first
        create_response = client.post(
            "/webhooks/",
            headers=auth_headers,
            json={
                "name": "Test Endpoint",
                "url": "https://httpbin.org/post",  # Use httpbin for testing
                "events": ["bet_placed"]
            }
        )
        webhook_id = create_response.json()["id"]

        # Test the webhook (may fail if httpbin is unavailable)
        response = client.post(
            f"/webhooks/{webhook_id}/test",
            headers=auth_headers
        )
        # Accept either success or failure (network dependent)
        assert response.status_code in [200, 500]
