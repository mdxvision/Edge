import pytest
from app.config import SUPPORTED_SPORTS, TEAM_SPORTS


class TestGamesList:
    
    def test_list_games_empty(self, client):
        response = client.get("/games/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_list_games_with_limit(self, client):
        response = client.get("/games/?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 10
    
    def test_list_games_invalid_limit(self, client):
        response = client.get("/games/?limit=0")
        assert response.status_code == 422
    
    def test_list_games_limit_too_high(self, client):
        response = client.get("/games/?limit=200")
        assert response.status_code == 422


class TestSportsList:
    
    def test_list_sports(self, client):
        response = client.get("/games/sports")
        assert response.status_code == 200
        data = response.json()
        assert "supported_sports" in data
        assert "team_sports" in data
        assert "individual_sports" in data
        assert len(data["supported_sports"]) > 0
    
    def test_sports_include_expected_sports(self, client):
        response = client.get("/games/sports")
        data = response.json()
        expected_sports = ["NFL", "NBA", "MLB", "NHL", "SOCCER", "TENNIS"]
        for sport in expected_sports:
            assert sport in data["supported_sports"]
    
    def test_team_sports_subset_of_supported(self, client):
        response = client.get("/games/sports")
        data = response.json()
        for team_sport in data["team_sports"]:
            assert team_sport in data["supported_sports"]
    
    def test_individual_sports_not_in_team_sports(self, client):
        response = client.get("/games/sports")
        data = response.json()
        for individual_sport in data["individual_sports"]:
            assert individual_sport not in data["team_sports"]


class TestTeamsList:
    
    def test_list_teams_empty(self, client):
        response = client.get("/games/teams")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestCompetitorsList:
    
    def test_list_competitors_empty(self, client):
        response = client.get("/games/competitors")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
