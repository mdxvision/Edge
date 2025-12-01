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
        assert data["name"] == "Multi-Sport Betting & DFS Recommendation Agent"
        assert data["version"] == "1.0.0"
        assert data["status"] == "running"
        assert "docs" in data
        assert "disclaimer" in data
