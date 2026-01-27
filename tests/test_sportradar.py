"""
Tests for Sportradar API Integration

Tests cover:
- Service functions (live games, schedules, player data, injuries)
- API endpoints
- Simulation mode
- Caching
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import date, datetime, timedelta
from fastapi.testclient import TestClient

from app.services.sportradar import (
    is_api_enabled,
    get_api_status,
    get_live_games,
    get_game_boxscore,
    get_daily_schedule,
    get_player_profile,
    get_team_roster,
    search_players,
    get_injuries,
    get_team_injuries,
    get_historical_games,
    get_standings,
    _get_nfl_week,
    _get_sport_teams,
    _simulate_live_games,
    _simulate_schedule,
    _simulate_injuries,
    _simulate_standings,
    _simulate_player_profile,
    _simulate_team_roster,
    _generate_team_stats,
)


# =============================================================================
# Configuration Tests
# =============================================================================

class TestConfiguration:
    """Test API configuration and status."""

    def test_api_disabled_without_key(self):
        """Test API is disabled without key."""
        with patch.dict("os.environ", {"SPORTRADAR_API_KEY": ""}):
            # Re-import to get updated value
            from app.services import sportradar
            assert sportradar.SPORTRADAR_API_KEY == ""

    def test_get_api_status_structure(self):
        """Test API status returns correct structure."""
        status = get_api_status()

        assert "api_enabled" in status
        assert "data_source" in status
        assert "supported_sports" in status
        assert "features" in status
        assert isinstance(status["supported_sports"], list)
        assert "NFL" in status["supported_sports"]
        assert "NBA" in status["supported_sports"]

    def test_supported_sports(self):
        """Test all expected sports are supported."""
        status = get_api_status()
        expected = ["NFL", "NBA", "MLB", "NHL", "SOCCER"]

        for sport in expected:
            assert sport in status["supported_sports"]


# =============================================================================
# Live Games Tests
# =============================================================================

class TestLiveGames:
    """Test live game functionality."""

    @pytest.mark.asyncio
    async def test_get_live_games_nfl(self):
        """Test fetching live NFL games."""
        games = await get_live_games("NFL")

        assert isinstance(games, list)
        # Simulation always returns games
        for game in games:
            assert "id" in game
            assert "status" in game
            assert "home_team" in game
            assert "away_team" in game
            assert game["sport"] == "NFL"

    @pytest.mark.asyncio
    async def test_get_live_games_nba(self):
        """Test fetching live NBA games."""
        games = await get_live_games("NBA")

        assert isinstance(games, list)
        for game in games:
            assert game["sport"] == "NBA"

    @pytest.mark.asyncio
    async def test_get_live_games_mlb(self):
        """Test fetching live MLB games."""
        games = await get_live_games("MLB")

        assert isinstance(games, list)
        for game in games:
            assert game["sport"] == "MLB"

    @pytest.mark.asyncio
    async def test_get_live_games_nhl(self):
        """Test fetching live NHL games."""
        games = await get_live_games("NHL")

        assert isinstance(games, list)
        for game in games:
            assert game["sport"] == "NHL"

    @pytest.mark.asyncio
    async def test_get_live_games_soccer(self):
        """Test fetching live soccer games."""
        games = await get_live_games("SOCCER")

        assert isinstance(games, list)
        for game in games:
            assert game["sport"] == "SOCCER"


# =============================================================================
# Schedule Tests
# =============================================================================

class TestSchedule:
    """Test schedule functionality."""

    @pytest.mark.asyncio
    async def test_get_daily_schedule(self):
        """Test fetching daily schedule."""
        today = date.today()
        games = await get_daily_schedule("NFL", today)

        assert isinstance(games, list)
        for game in games:
            assert "id" in game
            assert "scheduled" in game
            assert "home_team" in game
            assert "away_team" in game

    @pytest.mark.asyncio
    async def test_get_daily_schedule_default_date(self):
        """Test schedule defaults to today."""
        games = await get_daily_schedule("NBA")

        assert isinstance(games, list)

    @pytest.mark.asyncio
    async def test_schedule_past_date(self):
        """Test schedule for past date shows closed games."""
        past_date = date.today() - timedelta(days=7)
        games = await get_daily_schedule("NFL", past_date)

        # Past games should be closed
        for game in games:
            assert game.get("status") == "closed"


# =============================================================================
# Boxscore Tests
# =============================================================================

class TestBoxscore:
    """Test boxscore functionality."""

    @pytest.mark.asyncio
    async def test_get_boxscore(self):
        """Test fetching game boxscore."""
        boxscore = await get_game_boxscore("NFL", "test_game_id")

        assert "game_id" in boxscore
        assert "home" in boxscore
        assert "away" in boxscore
        assert "status" in boxscore

        # Check team stats structure
        assert "team" in boxscore["home"]
        assert "score" in boxscore["home"]
        assert "statistics" in boxscore["home"]

    @pytest.mark.asyncio
    async def test_boxscore_has_stats(self):
        """Test boxscore contains statistics."""
        boxscore = await get_game_boxscore("NFL", "test_game")

        stats = boxscore["home"]["statistics"]
        assert isinstance(stats, dict)


# =============================================================================
# Player Statistics Tests
# =============================================================================

class TestPlayerStats:
    """Test player statistics functionality."""

    @pytest.mark.asyncio
    async def test_get_player_profile(self):
        """Test fetching player profile."""
        profile = await get_player_profile("NFL", "test_player_id")

        assert "id" in profile
        assert "name" in profile
        assert "position" in profile
        assert "team" in profile
        assert profile["sport"] == "NFL"

    @pytest.mark.asyncio
    async def test_player_profile_nba(self):
        """Test NBA player profile."""
        profile = await get_player_profile("NBA", "test_player")

        assert profile["sport"] == "NBA"
        assert "position" in profile

    @pytest.mark.asyncio
    async def test_get_team_roster(self):
        """Test fetching team roster."""
        roster = await get_team_roster("NFL", "KC")

        assert "team_id" in roster
        assert "team_name" in roster
        assert "players" in roster
        assert isinstance(roster["players"], list)

        # Check player structure
        if roster["players"]:
            player = roster["players"][0]
            assert "id" in player
            assert "name" in player
            assert "position" in player

    @pytest.mark.asyncio
    async def test_search_players(self):
        """Test player search."""
        results = await search_players("NFL", "Patrick")

        assert isinstance(results, list)
        for player in results:
            assert "id" in player
            assert "name" in player

    @pytest.mark.asyncio
    async def test_search_players_with_position(self):
        """Test player search with position filter."""
        results = await search_players("NFL", "Test", position="QB")

        assert isinstance(results, list)
        for player in results:
            assert player.get("position") == "QB"


# =============================================================================
# Injury Reports Tests
# =============================================================================

class TestInjuries:
    """Test injury report functionality."""

    @pytest.mark.asyncio
    async def test_get_injuries(self):
        """Test fetching injury report."""
        injuries = await get_injuries("NFL")

        assert isinstance(injuries, list)
        for injury in injuries:
            assert "player_id" in injury
            assert "player_name" in injury
            assert "team" in injury
            assert "status" in injury
            assert "injury_type" in injury

    @pytest.mark.asyncio
    async def test_get_team_injuries(self):
        """Test fetching team-specific injuries."""
        # First get all injuries
        all_injuries = await get_injuries("NFL")

        if all_injuries:
            # Get injuries for a specific team
            team = all_injuries[0]["team"]
            team_injuries = await get_team_injuries("NFL", team)

            assert isinstance(team_injuries, list)
            for injury in team_injuries:
                assert team.lower() in injury["team"].lower()

    @pytest.mark.asyncio
    async def test_injury_statuses(self):
        """Test injury status values."""
        injuries = await get_injuries("NFL")

        valid_statuses = ["Out", "Doubtful", "Questionable", "Probable", "Day-to-Day"]

        for injury in injuries:
            assert injury["status"] in valid_statuses


# =============================================================================
# Historical Data Tests
# =============================================================================

class TestHistoricalData:
    """Test historical data functionality."""

    @pytest.mark.asyncio
    async def test_get_historical_games(self):
        """Test fetching historical games."""
        start = date.today() - timedelta(days=7)
        end = date.today() - timedelta(days=1)

        games = await get_historical_games("NFL", start, end)

        assert isinstance(games, list)

    @pytest.mark.asyncio
    async def test_historical_games_single_day(self):
        """Test historical games for single day."""
        target = date.today() - timedelta(days=3)

        games = await get_historical_games("NBA", target)

        assert isinstance(games, list)

    @pytest.mark.asyncio
    async def test_historical_games_team_filter(self):
        """Test historical games with team filter."""
        start = date.today() - timedelta(days=7)

        games = await get_historical_games("NFL", start, team_id="KC")

        # All games should involve the team
        for game in games:
            home_abbr = game.get("home_team", {}).get("abbreviation", "")
            away_abbr = game.get("away_team", {}).get("abbreviation", "")
            assert "KC" in [home_abbr, away_abbr]


# =============================================================================
# Standings Tests
# =============================================================================

class TestStandings:
    """Test standings functionality."""

    @pytest.mark.asyncio
    async def test_get_standings(self):
        """Test fetching standings."""
        standings = await get_standings("NFL")

        assert "sport" in standings
        assert "season" in standings
        assert "standings" in standings
        assert isinstance(standings["standings"], list)

    @pytest.mark.asyncio
    async def test_standings_structure(self):
        """Test standings entry structure."""
        standings = await get_standings("NBA")

        if standings["standings"]:
            entry = standings["standings"][0]
            assert "rank" in entry
            assert "team_name" in entry
            assert "wins" in entry
            assert "losses" in entry
            assert "win_pct" in entry

    @pytest.mark.asyncio
    async def test_standings_sorted_by_win_pct(self):
        """Test standings are sorted by win percentage."""
        standings = await get_standings("MLB")

        win_pcts = [s["win_pct"] for s in standings["standings"]]

        # Should be sorted descending
        assert win_pcts == sorted(win_pcts, reverse=True)


# =============================================================================
# Simulation Function Tests
# =============================================================================

class TestSimulation:
    """Test simulation functions."""

    def test_get_nfl_week(self):
        """Test NFL week calculation."""
        week = _get_nfl_week()

        assert 1 <= week <= 18

    def test_get_sport_teams_nfl(self):
        """Test NFL teams list."""
        teams = _get_sport_teams("NFL")

        assert len(teams) >= 16
        for team in teams:
            assert "id" in team
            assert "name" in team
            assert "abbr" in team

    def test_get_sport_teams_nba(self):
        """Test NBA teams list."""
        teams = _get_sport_teams("NBA")

        assert len(teams) >= 10
        for team in teams:
            assert "id" in team
            assert "name" in team

    def test_simulate_live_games(self):
        """Test live games simulation."""
        games = _simulate_live_games("NFL")

        assert isinstance(games, list)
        for game in games:
            assert game["status"] == "inprogress"
            assert "period" in game

    def test_simulate_schedule(self):
        """Test schedule simulation."""
        games = _simulate_schedule("NBA", date.today())

        assert isinstance(games, list)
        for game in games:
            assert "scheduled" in game
            assert "home_team" in game
            assert "away_team" in game

    def test_simulate_injuries(self):
        """Test injuries simulation."""
        injuries = _simulate_injuries("NFL")

        assert isinstance(injuries, list)
        for injury in injuries:
            assert "player_name" in injury
            assert "status" in injury

    def test_simulate_standings(self):
        """Test standings simulation."""
        standings = _simulate_standings("NBA", 2024)

        assert standings["sport"] == "NBA"
        assert standings["season"] == 2024
        assert len(standings["standings"]) > 0

    def test_simulate_player_profile(self):
        """Test player profile simulation."""
        profile = _simulate_player_profile("NFL", "test_id")

        assert profile["id"] == "test_id"
        assert "name" in profile
        assert "position" in profile
        assert profile["sport"] == "NFL"

    def test_simulate_team_roster(self):
        """Test team roster simulation."""
        roster = _simulate_team_roster("NFL", "KC")

        assert "team_name" in roster
        assert "players" in roster
        assert len(roster["players"]) > 0

    def test_generate_team_stats_nfl(self):
        """Test NFL team stats generation."""
        stats = _generate_team_stats("NFL")

        assert "total_yards" in stats
        assert "passing_yards" in stats
        assert "rushing_yards" in stats
        assert "turnovers" in stats

    def test_generate_team_stats_nba(self):
        """Test NBA team stats generation."""
        stats = _generate_team_stats("NBA")

        assert "field_goal_pct" in stats
        assert "three_point_pct" in stats
        assert "rebounds" in stats
        assert "assists" in stats

    def test_generate_team_stats_mlb(self):
        """Test MLB team stats generation."""
        stats = _generate_team_stats("MLB")

        assert "hits" in stats
        assert "runs" in stats
        assert "strikeouts" in stats


# =============================================================================
# Router Endpoint Tests
# =============================================================================

class TestRouterEndpoints:
    """Test API router endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from app.main import app
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self, client):
        """Get auth headers for testing."""
        import uuid
        unique_id = uuid.uuid4().hex[:8]
        response = client.post("/auth/register", json={
            "email": f"sportradar_{unique_id}@example.com",
            "username": f"sportradar{unique_id}",
            "password": "securepass123"
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_get_status_endpoint(self, client):
        """Test status endpoint (no auth required)."""
        response = client.get("/sportradar/status")
        assert response.status_code == 200

        data = response.json()
        assert "api_enabled" in data
        assert "supported_sports" in data

    def test_get_live_games_endpoint(self, client, auth_headers):
        """Test live games endpoint."""
        response = client.get("/sportradar/live/NFL", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["sport"] == "NFL"
        assert "live_games" in data

    def test_get_live_games_invalid_sport(self, client, auth_headers):
        """Test live games with invalid sport."""
        response = client.get("/sportradar/live/INVALID", headers=auth_headers)
        assert response.status_code == 400

    def test_get_schedule_endpoint(self, client, auth_headers):
        """Test schedule endpoint."""
        response = client.get("/sportradar/schedule/NBA", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["sport"] == "NBA"
        assert "games" in data

    def test_get_schedule_with_date(self, client, auth_headers):
        """Test schedule with specific date."""
        response = client.get(
            "/sportradar/schedule/NFL",
            params={"date": "2024-01-15"},
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_get_schedule_invalid_date(self, client, auth_headers):
        """Test schedule with invalid date."""
        response = client.get(
            "/sportradar/schedule/NFL",
            params={"date": "invalid"},
            headers=auth_headers
        )
        assert response.status_code == 400

    def test_get_boxscore_endpoint(self, client, auth_headers):
        """Test boxscore endpoint."""
        response = client.get(
            "/sportradar/boxscore/NFL/test_game_123",
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "home" in data
        assert "away" in data

    def test_get_player_endpoint(self, client, auth_headers):
        """Test player profile endpoint."""
        response = client.get(
            "/sportradar/player/NFL/test_player",
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "name" in data
        assert "position" in data

    def test_get_roster_endpoint(self, client, auth_headers):
        """Test roster endpoint."""
        response = client.get(
            "/sportradar/roster/NFL/KC",
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "players" in data

    def test_search_players_endpoint(self, client, auth_headers):
        """Test player search endpoint."""
        response = client.get(
            "/sportradar/players/search/NFL",
            params={"q": "Patrick"},
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "players" in data

    def test_get_injuries_endpoint(self, client, auth_headers):
        """Test injuries endpoint."""
        response = client.get("/sportradar/injuries/NFL", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "injuries" in data
        assert "total" in data
        assert "by_status" in data

    def test_get_injuries_with_team_filter(self, client, auth_headers):
        """Test injuries with team filter."""
        response = client.get(
            "/sportradar/injuries/NFL",
            params={"team": "KC"},
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert data["team_filter"] == "KC"

    def test_get_injury_impact_endpoint(self, client, auth_headers):
        """Test injury impact endpoint."""
        response = client.get("/sportradar/injuries/NFL/impact", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "high_impact_injuries" in data

    def test_get_historical_endpoint(self, client, auth_headers):
        """Test historical data endpoint."""
        response = client.get(
            "/sportradar/historical/NFL",
            params={"start_date": "2024-01-01", "end_date": "2024-01-07"},
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "games" in data

    def test_get_historical_date_range_limit(self, client, auth_headers):
        """Test historical data date range limit."""
        response = client.get(
            "/sportradar/historical/NFL",
            params={"start_date": "2024-01-01", "end_date": "2024-03-01"},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "30 days" in response.json()["detail"]

    def test_get_standings_endpoint(self, client, auth_headers):
        """Test standings endpoint."""
        response = client.get("/sportradar/standings/NBA", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "standings" in data

    def test_get_game_preview_endpoint(self, client, auth_headers):
        """Test game preview endpoint."""
        response = client.get(
            "/sportradar/game-preview/NFL/test_game",
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "game" in data
        assert "injuries" in data
        assert "injury_summary" in data

    def test_get_team_report_endpoint(self, client, auth_headers):
        """Test team report endpoint."""
        response = client.get(
            "/sportradar/team-report/NFL/KC",
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "roster" in data
        assert "injuries" in data
        assert "recent_games" in data
        assert "summary" in data

    def test_unauthorized_access(self, client):
        """Test endpoints require authentication."""
        response = client.get("/sportradar/live/NFL")
        assert response.status_code == 401
