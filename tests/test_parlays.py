"""
Tests for parlays router.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def auth_headers(client: TestClient):
    """Get auth headers from a registered user."""
    response = client.post("/auth/register", json={
        "email": "parlays@example.com",
        "username": "parlaysuser",
        "password": "securepass123"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestParlayCalculation:
    """Tests for parlay calculation."""

    def test_calculate_two_leg_parlay(self, client: TestClient, auth_headers):
        """Test calculating a 2-leg parlay."""
        response = client.post(
            "/parlays/calculate",
            headers=auth_headers,
            json={
                "legs": [
                    {"selection": "Team A ML", "odds": -110, "probability": 0.55},
                    {"selection": "Team B ML", "odds": 150, "probability": 0.40}
                ],
                "stake": 100
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "combined_odds" in data
        assert "combined_probability" in data
        assert "potential_payout" in data

    def test_calculate_three_leg_parlay(self, client: TestClient, auth_headers):
        """Test calculating a 3-leg parlay."""
        response = client.post(
            "/parlays/calculate",
            headers=auth_headers,
            json={
                "legs": [
                    {"selection": "Team A ML", "odds": -110, "probability": 0.55},
                    {"selection": "Team B +3.5", "odds": -105, "probability": 0.52},
                    {"selection": "Over 45.5", "odds": -110, "probability": 0.50}
                ],
                "stake": 50
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["leg_count"] == 3

    def test_calculate_correlated_parlay(self, client: TestClient, auth_headers):
        """Test calculating a correlated parlay."""
        response = client.post(
            "/parlays/calculate",
            headers=auth_headers,
            json={
                "legs": [
                    {"selection": "Team A ML", "odds": -110, "probability": 0.55},
                    {"selection": "Team A Over", "odds": -110, "probability": 0.50}
                ],
                "stake": 100,
                "same_game": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        # Correlation should affect probability
        assert "correlation_adjustment" in data


class TestCreateParlay:
    """Tests for creating parlays."""

    def test_create_parlay(self, client: TestClient, auth_headers):
        """Test creating and saving a parlay."""
        response = client.post(
            "/parlays/",
            headers=auth_headers,
            json={
                "name": "My Parlay",
                "legs": [
                    {"selection": "Team A ML", "odds": -110, "probability": 0.55},
                    {"selection": "Team B ML", "odds": 150, "probability": 0.40}
                ],
                "stake": 100
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "My Parlay"
        assert "id" in data

    def test_create_parlay_no_auth(self, client: TestClient):
        """Test creating parlay without authentication."""
        response = client.post("/parlays/", json={
            "legs": [
                {"selection": "Team A ML", "odds": -110, "probability": 0.55}
            ],
            "stake": 100
        })
        assert response.status_code == 401


class TestGetParlays:
    """Tests for retrieving parlays."""

    def test_list_parlays(self, client: TestClient, auth_headers):
        """Test listing user parlays."""
        # Create a parlay first
        client.post(
            "/parlays/",
            headers=auth_headers,
            json={
                "name": "Test Parlay",
                "legs": [
                    {"selection": "Team A ML", "odds": -110, "probability": 0.55},
                    {"selection": "Team B ML", "odds": 150, "probability": 0.40}
                ],
                "stake": 100
            }
        )

        response = client.get("/parlays/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestParlayOddsConversion:
    """Tests for odds conversion in parlays."""

    def test_convert_american_to_decimal(self, client: TestClient):
        """Test converting American odds to decimal."""
        response = client.get("/parlays/convert-odds", params={
            "odds": -110,
            "format": "decimal"
        })
        assert response.status_code == 200
        data = response.json()
        assert "decimal" in data
        assert data["decimal"] == pytest.approx(1.91, 0.01)

    def test_convert_positive_american_to_decimal(self, client: TestClient):
        """Test converting positive American odds to decimal."""
        response = client.get("/parlays/convert-odds", params={
            "odds": 150,
            "format": "decimal"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["decimal"] == pytest.approx(2.5, 0.01)
