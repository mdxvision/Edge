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


class TestParlayAnalysis:
    """Tests for parlay analysis."""

    def test_analyze_two_leg_parlay(self, client: TestClient):
        """Test analyzing a 2-leg parlay."""
        response = client.post(
            "/parlays/analyze",
            json={
                "legs": [
                    {"selection": "Team A ML", "odds": -110, "probability": 0.55},
                    {"selection": "Team B ML", "odds": 150, "probability": 0.40}
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "combined_odds" in data
        assert "combined_probability" in data
        assert "leg_count" in data
        assert data["leg_count"] == 2

    def test_analyze_three_leg_parlay(self, client: TestClient):
        """Test analyzing a 3-leg parlay."""
        response = client.post(
            "/parlays/analyze",
            json={
                "legs": [
                    {"selection": "Team A ML", "odds": -110, "probability": 0.55},
                    {"selection": "Team B +3.5", "odds": -105, "probability": 0.52},
                    {"selection": "Over 45.5", "odds": -110, "probability": 0.50}
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["leg_count"] == 3

    def test_analyze_parlay_returns_edge(self, client: TestClient):
        """Test that parlay analysis returns edge information."""
        response = client.post(
            "/parlays/analyze",
            json={
                "legs": [
                    {"selection": "Team A ML", "odds": -110, "probability": 0.55},
                    {"selection": "Team A Over", "odds": -110, "probability": 0.50}
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "edge" in data
        assert "is_positive_ev" in data


class TestCreateParlay:
    """Tests for creating parlays."""

    def test_create_parlay(self, client: TestClient, auth_headers):
        """Test creating and saving a parlay."""
        response = client.post(
            "/parlays",
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
        response = client.post("/parlays", json={
            "legs": [
                {"selection": "Team A ML", "odds": -110, "probability": 0.55},
                {"selection": "Team B ML", "odds": 150, "probability": 0.40}
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
            "/parlays",
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

        response = client.get("/parlays", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestParlayValidation:
    """Tests for parlay validation."""

    def test_parlay_requires_minimum_legs(self, client: TestClient):
        """Test that parlay requires at least 2 legs."""
        response = client.post(
            "/parlays/analyze",
            json={
                "legs": [
                    {"selection": "Team A ML", "odds": -110, "probability": 0.55}
                ]
            }
        )
        assert response.status_code == 422  # Validation error

    def test_parlay_probability_must_be_valid(self, client: TestClient):
        """Test that probability must be between 0 and 1."""
        response = client.post(
            "/parlays/analyze",
            json={
                "legs": [
                    {"selection": "Team A ML", "odds": -110, "probability": 1.5},
                    {"selection": "Team B ML", "odds": 150, "probability": 0.40}
                ]
            }
        )
        assert response.status_code == 422  # Validation error
