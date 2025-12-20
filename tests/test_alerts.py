"""
Tests for alerts router.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def auth_headers(client: TestClient):
    """Get auth headers from a registered user."""
    response = client.post("/auth/register", json={
        "email": "alerts@example.com",
        "username": "alertsuser",
        "password": "securepass123"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestCreateAlert:
    """Tests for creating alerts."""

    def test_create_edge_alert(self, client: TestClient, auth_headers):
        """Test creating a high edge alert."""
        response = client.post(
            "/alerts",
            headers=auth_headers,
            json={
                "name": "High Edge Alert",
                "alert_type": "high_edge",
                "sport": "NFL",
                "min_edge": 0.05,
                "notify_push": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "High Edge Alert"
        assert data["alert_type"] == "high_edge"
        assert data["is_active"] is True

    def test_create_line_movement_alert(self, client: TestClient, auth_headers):
        """Test creating a line movement alert."""
        response = client.post(
            "/alerts",
            headers=auth_headers,
            json={
                "name": "Line Movement Alert",
                "alert_type": "line_movement",
                "sport": "NBA",
                "min_odds": -200,
                "max_odds": 200,
                "notify_telegram": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Line Movement Alert"

    def test_create_alert_no_auth(self, client: TestClient):
        """Test creating alert without authentication."""
        response = client.post("/alerts", json={
            "name": "Test Alert",
            "alert_type": "high_edge"
        })
        assert response.status_code == 401


class TestGetAlerts:
    """Tests for retrieving alerts."""

    def test_list_alerts(self, client: TestClient, auth_headers):
        """Test listing user alerts."""
        # Create an alert first
        client.post(
            "/alerts",
            headers=auth_headers,
            json={
                "name": "Test Alert",
                "alert_type": "high_edge"
            }
        )

        response = client.get("/alerts", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_single_alert(self, client: TestClient, auth_headers):
        """Test getting a single alert."""
        # Create an alert first
        create_response = client.post(
            "/alerts",
            headers=auth_headers,
            json={
                "name": "Single Alert",
                "alert_type": "high_edge"
            }
        )
        alert_id = create_response.json()["id"]

        response = client.get(f"/alerts/{alert_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Single Alert"


class TestUpdateAlert:
    """Tests for updating alerts."""

    def test_update_alert(self, client: TestClient, auth_headers):
        """Test updating an alert."""
        # Create an alert first
        create_response = client.post(
            "/alerts",
            headers=auth_headers,
            json={
                "name": "Original Name",
                "alert_type": "high_edge"
            }
        )
        alert_id = create_response.json()["id"]

        # Update the alert
        response = client.patch(
            f"/alerts/{alert_id}",
            headers=auth_headers,
            json={"name": "Updated Name"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

    def test_toggle_alert_active(self, client: TestClient, auth_headers):
        """Test toggling alert active status."""
        # Create an alert first
        create_response = client.post(
            "/alerts",
            headers=auth_headers,
            json={
                "name": "Toggle Alert",
                "alert_type": "high_edge"
            }
        )
        alert_id = create_response.json()["id"]

        # Deactivate
        response = client.patch(
            f"/alerts/{alert_id}",
            headers=auth_headers,
            json={"is_active": False}
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False


class TestDeleteAlert:
    """Tests for deleting alerts."""

    def test_delete_alert(self, client: TestClient, auth_headers):
        """Test deleting an alert."""
        # Create an alert first
        create_response = client.post(
            "/alerts",
            headers=auth_headers,
            json={
                "name": "Delete Me",
                "alert_type": "high_edge"
            }
        )
        alert_id = create_response.json()["id"]

        # Delete the alert
        response = client.delete(f"/alerts/{alert_id}", headers=auth_headers)
        assert response.status_code == 200

        # Verify it's deleted
        response = client.get(f"/alerts/{alert_id}", headers=auth_headers)
        assert response.status_code == 404
