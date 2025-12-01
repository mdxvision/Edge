import pytest


class TestRunRecommendations:
    
    def test_run_recommendations_client_not_found(self, client):
        response = client.post("/clients/99999/recommendations/run", json={})
        assert response.status_code == 404
        assert "Client not found" in response.json()["detail"]
    
    def test_run_recommendations_success(self, client, created_client):
        client_id = created_client["id"]
        response = client.post(f"/clients/{client_id}/recommendations/run", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["client_id"] == client_id
        assert data["client_name"] == created_client["name"]
        assert "recommendations" in data
        assert "total_recommended_stake" in data
        assert isinstance(data["recommendations"], list)
    
    def test_run_recommendations_with_sports_filter(self, client, created_client):
        client_id = created_client["id"]
        response = client.post(
            f"/clients/{client_id}/recommendations/run",
            json={"sports": ["NFL", "NBA"]}
        )
        assert response.status_code == 200
        data = response.json()
        for rec in data["recommendations"]:
            assert rec["sport"] in ["NFL", "NBA"]
    
    def test_run_recommendations_invalid_sport(self, client, created_client):
        client_id = created_client["id"]
        response = client.post(
            f"/clients/{client_id}/recommendations/run",
            json={"sports": ["INVALID_SPORT"]}
        )
        assert response.status_code == 400
        assert "Invalid sports" in response.json()["detail"]
    
    def test_run_recommendations_with_min_edge(self, client, created_client):
        client_id = created_client["id"]
        response = client.post(
            f"/clients/{client_id}/recommendations/run",
            json={"min_edge": 0.05}
        )
        assert response.status_code == 200
        data = response.json()
        for rec in data["recommendations"]:
            assert rec["edge"] >= 0.05


class TestLatestRecommendations:
    
    def test_get_latest_client_not_found(self, client):
        response = client.get("/clients/99999/recommendations/latest")
        assert response.status_code == 404
        assert "Client not found" in response.json()["detail"]
    
    def test_get_latest_empty(self, client, created_client):
        client_id = created_client["id"]
        response = client.get(f"/clients/{client_id}/recommendations/latest")
        assert response.status_code == 200
        assert response.json() == []
    
    def test_get_latest_after_run(self, client, created_client):
        client_id = created_client["id"]
        client.post(f"/clients/{client_id}/recommendations/run", json={})
        
        response = client.get(f"/clients/{client_id}/recommendations/latest")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_latest_with_limit(self, client, created_client):
        client_id = created_client["id"]
        client.post(f"/clients/{client_id}/recommendations/run", json={})
        
        response = client.get(f"/clients/{client_id}/recommendations/latest?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 5


class TestRecommendationFields:
    
    def test_recommendation_has_required_fields(self, client, created_client):
        client_id = created_client["id"]
        run_response = client.post(f"/clients/{client_id}/recommendations/run", json={})
        assert run_response.status_code == 200
        
        recommendations = run_response.json()["recommendations"]
        if len(recommendations) > 0:
            rec = recommendations[0]
            required_fields = [
                "id", "client_id", "sport", "game_info", "market_type",
                "selection", "sportsbook", "american_odds", "model_probability",
                "implied_probability", "edge", "expected_value", "suggested_stake",
                "explanation"
            ]
            for field in required_fields:
                assert field in rec, f"Missing field: {field}"
    
    def test_recommendation_edge_calculation(self, client, created_client):
        client_id = created_client["id"]
        run_response = client.post(f"/clients/{client_id}/recommendations/run", json={})
        recommendations = run_response.json()["recommendations"]
        
        for rec in recommendations:
            expected_edge = rec["model_probability"] - rec["implied_probability"]
            assert abs(rec["edge"] - expected_edge) < 0.001
    
    def test_recommendation_has_explanation(self, client, created_client):
        client_id = created_client["id"]
        run_response = client.post(f"/clients/{client_id}/recommendations/run", json={})
        recommendations = run_response.json()["recommendations"]
        
        for rec in recommendations:
            assert rec["explanation"] is not None
            assert len(rec["explanation"]) > 0


class TestRecommendationPersistence:
    
    def test_recommendations_persist_after_run(self, client, created_client):
        client_id = created_client["id"]
        run_response = client.post(f"/clients/{client_id}/recommendations/run", json={})
        initial_count = len(run_response.json()["recommendations"])
        
        latest_response = client.get(f"/clients/{client_id}/recommendations/latest")
        assert latest_response.status_code == 200
        assert len(latest_response.json()) == initial_count
    
    def test_multiple_runs_accumulate(self, client, created_client):
        client_id = created_client["id"]
        client.post(f"/clients/{client_id}/recommendations/run", json={})
        client.post(f"/clients/{client_id}/recommendations/run", json={})
        
        latest_response = client.get(f"/clients/{client_id}/recommendations/latest?limit=100")
        assert latest_response.status_code == 200
    
    def test_recommendation_has_timestamp(self, client, created_client):
        client_id = created_client["id"]
        run_response = client.post(f"/clients/{client_id}/recommendations/run", json={})
        recommendations = run_response.json()["recommendations"]
        
        for rec in recommendations:
            assert "created_at" in rec
            assert rec["created_at"] is not None


class TestRecommendationStaking:
    
    def test_suggested_stake_positive(self, client, created_client):
        client_id = created_client["id"]
        run_response = client.post(f"/clients/{client_id}/recommendations/run", json={})
        recommendations = run_response.json()["recommendations"]
        
        for rec in recommendations:
            assert rec["suggested_stake"] >= 0
    
    def test_total_stake_matches_sum(self, client, created_client):
        client_id = created_client["id"]
        run_response = client.post(f"/clients/{client_id}/recommendations/run", json={})
        data = run_response.json()
        
        if len(data["recommendations"]) > 0:
            computed_total = sum(rec["suggested_stake"] for rec in data["recommendations"])
            assert abs(data["total_recommended_stake"] - computed_total) < 0.01
    
    def test_model_probability_within_bounds(self, client, created_client):
        client_id = created_client["id"]
        run_response = client.post(f"/clients/{client_id}/recommendations/run", json={})
        recommendations = run_response.json()["recommendations"]
        
        for rec in recommendations:
            assert 0 <= rec["model_probability"] <= 1
            assert 0 <= rec["implied_probability"] <= 1
