import pytest


class TestHealthEndpoint:
    
    def test_health_check_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "disclaimer" in data
        assert "SIMULATION ONLY" in data["disclaimer"]
    
    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "EdgeBet - Multi-Sport Betting & DFS Platform"
        assert data["version"] == "2.0.0"
        assert data["status"] == "running"
        assert "docs" in data
        assert "redoc" in data
        assert "disclaimer" in data
        assert data["sports_count"] == 15
