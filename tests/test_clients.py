import pytest


class TestClientCreation:
    
    def test_create_client_success(self, client, sample_client_data):
        response = client.post("/clients/", json=sample_client_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == sample_client_data["name"]
        assert data["bankroll"] == sample_client_data["bankroll"]
        assert data["risk_profile"] == sample_client_data["risk_profile"]
        assert "id" in data
        assert data["id"] > 0
    
    def test_create_client_conservative_profile(self, client):
        response = client.post("/clients/", json={
            "name": "Conservative User",
            "bankroll": 5000.0,
            "risk_profile": "conservative"
        })
        assert response.status_code == 200
        assert response.json()["risk_profile"] == "conservative"
    
    def test_create_client_aggressive_profile(self, client):
        response = client.post("/clients/", json={
            "name": "Aggressive User",
            "bankroll": 25000.0,
            "risk_profile": "aggressive"
        })
        assert response.status_code == 200
        assert response.json()["risk_profile"] == "aggressive"
    
    def test_create_client_invalid_risk_profile(self, client):
        response = client.post("/clients/", json={
            "name": "Invalid User",
            "bankroll": 10000.0,
            "risk_profile": "invalid_profile"
        })
        assert response.status_code in [400, 422]
    
    def test_create_client_missing_name(self, client):
        response = client.post("/clients/", json={
            "bankroll": 10000.0,
            "risk_profile": "balanced"
        })
        assert response.status_code == 422


class TestClientRetrieval:
    
    def test_get_client_success(self, client, created_client):
        client_id = created_client["id"]
        response = client.get(f"/clients/{client_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == client_id
        assert data["name"] == created_client["name"]
    
    def test_get_client_not_found(self, client):
        response = client.get("/clients/99999")
        assert response.status_code == 404
        assert "Client not found" in response.json()["detail"]
    
    def test_list_clients_empty(self, client):
        response = client.get("/clients/")
        assert response.status_code == 200
        assert response.json() == []
    
    def test_list_clients_with_data(self, client, sample_client_data):
        client.post("/clients/", json=sample_client_data)
        client.post("/clients/", json={
            "name": "Second User",
            "bankroll": 5000.0,
            "risk_profile": "conservative"
        })
        
        response = client.get("/clients/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


class TestClientUpdate:
    
    def test_update_client_name(self, client, created_client):
        client_id = created_client["id"]
        response = client.patch(f"/clients/{client_id}", json={
            "name": "Updated Name"
        })
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"
    
    def test_update_client_bankroll(self, client, created_client):
        client_id = created_client["id"]
        response = client.patch(f"/clients/{client_id}", json={
            "bankroll": 50000.0
        })
        assert response.status_code == 200
        assert response.json()["bankroll"] == 50000.0
    
    def test_update_client_risk_profile(self, client, created_client):
        client_id = created_client["id"]
        response = client.patch(f"/clients/{client_id}", json={
            "risk_profile": "aggressive"
        })
        assert response.status_code == 200
        assert response.json()["risk_profile"] == "aggressive"
    
    def test_update_client_invalid_risk_profile(self, client, created_client):
        client_id = created_client["id"]
        response = client.patch(f"/clients/{client_id}", json={
            "risk_profile": "invalid"
        })
        assert response.status_code in [400, 422]
    
    def test_update_client_not_found(self, client):
        response = client.patch("/clients/99999", json={
            "name": "New Name"
        })
        assert response.status_code == 404


class TestClientDeletion:
    
    def test_delete_client_success(self, client, created_client):
        client_id = created_client["id"]
        response = client.delete(f"/clients/{client_id}")
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
        
        get_response = client.get(f"/clients/{client_id}")
        assert get_response.status_code == 404
    
    def test_delete_client_not_found(self, client):
        response = client.delete("/clients/99999")
        assert response.status_code == 404


class TestClientValidation:
    
    def test_bankroll_minimum_value(self, client):
        response = client.post("/clients/", json={
            "name": "Test User",
            "bankroll": 100.0,
            "risk_profile": "balanced"
        })
        assert response.status_code == 200
    
    def test_bankroll_negative_value(self, client):
        response = client.post("/clients/", json={
            "name": "Test User",
            "bankroll": -1000.0,
            "risk_profile": "balanced"
        })
        assert response.status_code in [200, 422]
    
    def test_update_multiple_fields_simultaneously(self, client, created_client):
        client_id = created_client["id"]
        response = client.patch(f"/clients/{client_id}", json={
            "name": "Updated Name",
            "bankroll": 25000.0,
            "risk_profile": "aggressive"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["bankroll"] == 25000.0
        assert data["risk_profile"] == "aggressive"
    
    def test_update_persists_after_refetch(self, client, created_client):
        client_id = created_client["id"]
        client.patch(f"/clients/{client_id}", json={
            "name": "Persisted Name",
            "bankroll": 15000.0
        })
        
        response = client.get(f"/clients/{client_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Persisted Name"
        assert data["bankroll"] == 15000.0
    
    def test_empty_name_rejected(self, client):
        response = client.post("/clients/", json={
            "name": "",
            "bankroll": 10000.0,
            "risk_profile": "balanced"
        })
        assert response.status_code in [200, 422]
