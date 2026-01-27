"""
Tests for Live Betting Model

Tests:
- Win probability calculations for each sport
- Momentum detection
- Edge calculation
- Live alerts
- Router endpoints
"""

import pytest
import uuid
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.services.live_betting import (
    LiveGameState,
    LiveProbability,
    MomentumAnalysis,
    MomentumLevel,
    LiveEdge,
    GameStatus,
    calculate_win_probability,
    calculate_nfl_win_probability,
    calculate_nba_win_probability,
    calculate_mlb_win_probability,
    calculate_nhl_win_probability,
    calculate_soccer_win_probability,
    analyze_momentum,
    calculate_live_edges,
    generate_live_alerts,
    analyze_live_game,
    simulate_live_game,
    _american_to_probability,
    _probability_to_american,
    _parse_time_remaining,
    _parse_mlb_inning,
)


client = TestClient(app)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def auth_headers():
    """Create test user and return auth headers."""
    unique_id = uuid.uuid4().hex[:8]
    response = client.post("/auth/register", json={
        "email": f"livebetting_{unique_id}@example.com",
        "username": f"livebetting{unique_id}",
        "password": "securepass123"
    })
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    # User may already exist, try login
    response = client.post("/auth/login", json={
        "email": f"livebetting_{unique_id}@example.com",
        "password": "securepass123"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def nfl_game_state():
    """Sample NFL game state."""
    return LiveGameState(
        game_id="test_nfl_001",
        sport="NFL",
        home_team="Buffalo Bills",
        away_team="Kansas City Chiefs",
        home_score=21,
        away_score=17,
        period="Q3",
        time_remaining="8:30",
        status=GameStatus.IN_PROGRESS,
        scoring_plays=[
            {"team": "away", "points": 7, "time": "12:00"},
            {"team": "home", "points": 7, "time": "8:00"},
            {"team": "away", "points": 7, "time": "4:00"},
            {"team": "home", "points": 7, "time": "0:30"},
            {"team": "away", "points": 3, "time": "10:00"},
            {"team": "home", "points": 7, "time": "6:00"},
        ]
    )


@pytest.fixture
def nba_game_state():
    """Sample NBA game state."""
    return LiveGameState(
        game_id="test_nba_001",
        sport="NBA",
        home_team="Boston Celtics",
        away_team="Los Angeles Lakers",
        home_score=85,
        away_score=78,
        period="Q3",
        time_remaining="4:15",
        status=GameStatus.IN_PROGRESS,
        scoring_plays=[
            {"team": "home", "points": 2, "time": "11:30"},
            {"team": "home", "points": 3, "time": "10:45"},
            {"team": "away", "points": 2, "time": "10:00"},
            {"team": "home", "points": 2, "time": "9:15"},
            {"team": "home", "points": 3, "time": "8:30"},
        ]
    )


@pytest.fixture
def mlb_game_state():
    """Sample MLB game state."""
    return LiveGameState(
        game_id="test_mlb_001",
        sport="MLB",
        home_team="New York Yankees",
        away_team="Los Angeles Dodgers",
        home_score=4,
        away_score=3,
        period="Bot 6",
        time_remaining="0:00",
        status=GameStatus.IN_PROGRESS,
        scoring_plays=[
            {"team": "home", "points": 1},
            {"team": "away", "points": 1},
            {"team": "home", "points": 2},
            {"team": "away", "points": 2},
            {"team": "home", "points": 1},
        ]
    )


@pytest.fixture
def nhl_game_state():
    """Sample NHL game state."""
    return LiveGameState(
        game_id="test_nhl_001",
        sport="NHL",
        home_team="Boston Bruins",
        away_team="Florida Panthers",
        home_score=3,
        away_score=2,
        period="3rd",
        time_remaining="10:00",
        status=GameStatus.IN_PROGRESS,
        scoring_plays=[
            {"team": "home", "points": 1},
            {"team": "away", "points": 1},
            {"team": "home", "points": 1},
            {"team": "away", "points": 1},
            {"team": "home", "points": 1},
        ]
    )


@pytest.fixture
def soccer_game_state():
    """Sample soccer game state."""
    return LiveGameState(
        game_id="test_soccer_001",
        sport="SOCCER",
        home_team="Manchester City",
        away_team="Arsenal",
        home_score=2,
        away_score=1,
        period="2nd Half",
        time_remaining="60",
        status=GameStatus.IN_PROGRESS,
        scoring_plays=[
            {"team": "home", "points": 1},
            {"team": "away", "points": 1},
            {"team": "home", "points": 1},
        ]
    )


# =============================================================================
# Win Probability Tests
# =============================================================================

class TestNFLWinProbability:
    """Tests for NFL win probability model."""

    def test_home_leading_q3(self, nfl_game_state):
        """Home team leading in Q3 should have higher probability."""
        prob = calculate_nfl_win_probability(nfl_game_state)
        assert prob.home_win_prob > 0.5
        assert prob.away_win_prob < 0.5
        assert prob.model_used == "nfl_time_score"

    def test_home_leading_q4_high_confidence(self):
        """Home team leading late in Q4 should have high probability."""
        state = LiveGameState(
            game_id="test_nfl_q4",
            sport="NFL",
            home_team="Bills",
            away_team="Chiefs",
            home_score=28,
            away_score=14,
            period="Q4",
            time_remaining="2:00",
            status=GameStatus.IN_PROGRESS,
        )
        prob = calculate_nfl_win_probability(state)
        assert prob.home_win_prob > 0.9
        assert prob.confidence > 0.7

    def test_tied_game_neutral(self):
        """Tied game should be close to 50/50 with slight home advantage."""
        state = LiveGameState(
            game_id="test_nfl_tied",
            sport="NFL",
            home_team="Bills",
            away_team="Chiefs",
            home_score=14,
            away_score=14,
            period="Q2",
            time_remaining="5:00",
            status=GameStatus.IN_PROGRESS,
        )
        prob = calculate_nfl_win_probability(state)
        # Should be close to 50% with slight home advantage
        assert 0.45 <= prob.home_win_prob <= 0.60

    def test_final_game_home_wins(self):
        """Final game with home lead should be 100%."""
        state = LiveGameState(
            game_id="test_nfl_final",
            sport="NFL",
            home_team="Bills",
            away_team="Chiefs",
            home_score=24,
            away_score=17,
            period="Q4",
            time_remaining="0:00",
            status=GameStatus.FINAL,
        )
        prob = calculate_nfl_win_probability(state)
        assert prob.home_win_prob == 1.0
        assert prob.away_win_prob == 0.0

    def test_factors_populated(self, nfl_game_state):
        """Factors should be populated with relevant info."""
        prob = calculate_nfl_win_probability(nfl_game_state)
        assert len(prob.factors) >= 2
        assert any("leads" in f.lower() or "remaining" in f.lower() for f in prob.factors)


class TestNBAWinProbability:
    """Tests for NBA win probability model."""

    def test_home_leading_q3(self, nba_game_state):
        """Home team leading in Q3."""
        prob = calculate_nba_win_probability(nba_game_state)
        assert prob.home_win_prob > 0.5
        assert prob.model_used == "nba_possession"

    def test_large_lead_garbage_time(self):
        """Large lead late should trigger garbage time warning."""
        state = LiveGameState(
            game_id="test_nba_garbage",
            sport="NBA",
            home_team="Celtics",
            away_team="Lakers",
            home_score=115,
            away_score=88,
            period="Q4",
            time_remaining="4:00",
            status=GameStatus.IN_PROGRESS,
        )
        prob = calculate_nba_win_probability(state)
        assert prob.home_win_prob > 0.95
        assert any("garbage" in f.lower() for f in prob.factors)

    def test_close_game_late(self):
        """Close game late should have moderate probabilities."""
        state = LiveGameState(
            game_id="test_nba_close",
            sport="NBA",
            home_team="Celtics",
            away_team="Lakers",
            home_score=105,
            away_score=102,
            period="Q4",
            time_remaining="1:30",
            status=GameStatus.IN_PROGRESS,
        )
        prob = calculate_nba_win_probability(state)
        assert 0.55 <= prob.home_win_prob <= 0.85


class TestMLBWinProbability:
    """Tests for MLB win probability model."""

    def test_home_leading_mid_game(self, mlb_game_state):
        """Home team leading in 6th inning."""
        prob = calculate_mlb_win_probability(mlb_game_state)
        assert prob.home_win_prob > 0.5
        assert prob.model_used == "mlb_run_expectancy"

    def test_late_inning_one_run_lead(self):
        """One run lead in 9th should still be uncertain."""
        state = LiveGameState(
            game_id="test_mlb_9th",
            sport="MLB",
            home_team="Yankees",
            away_team="Dodgers",
            home_score=3,
            away_score=2,
            period="Top 9",
            time_remaining="0:00",
            status=GameStatus.IN_PROGRESS,
        )
        prob = calculate_mlb_win_probability(state)
        assert prob.home_win_prob > 0.6  # Home leading but away has chance

    def test_inning_parsing(self):
        """Test various inning formats."""
        assert _parse_mlb_inning("Top 5") == 5
        assert _parse_mlb_inning("Bot 7") == 7
        assert _parse_mlb_inning("Bottom 9") == 9


class TestNHLWinProbability:
    """Tests for NHL win probability model."""

    def test_home_leading_3rd(self, nhl_game_state):
        """Home team leading in 3rd period."""
        prob = calculate_nhl_win_probability(nhl_game_state)
        assert prob.home_win_prob > 0.5
        assert prob.model_used == "nhl_goal_expectancy"

    def test_tied_game_ot_probability(self):
        """Tied game at end of 3rd should be ~50%."""
        state = LiveGameState(
            game_id="test_nhl_tied",
            sport="NHL",
            home_team="Bruins",
            away_team="Panthers",
            home_score=2,
            away_score=2,
            period="3rd",
            time_remaining="0:30",
            status=GameStatus.IN_PROGRESS,
        )
        prob = calculate_nhl_win_probability(state)
        assert 0.45 <= prob.home_win_prob <= 0.55


class TestSoccerWinProbability:
    """Tests for Soccer win probability model."""

    def test_home_leading_2nd_half(self, soccer_game_state):
        """Home team leading in 2nd half."""
        prob = calculate_soccer_win_probability(soccer_game_state)
        assert prob.home_win_prob > 0.4  # Soccer leads are less safe
        assert prob.tie_prob > 0  # Draws are common
        assert prob.model_used == "soccer_poisson"

    def test_draw_probability_exists(self):
        """Tied game should have significant draw probability."""
        state = LiveGameState(
            game_id="test_soccer_tied",
            sport="SOCCER",
            home_team="Man City",
            away_team="Arsenal",
            home_score=1,
            away_score=1,
            period="2nd Half",
            time_remaining="70",
            status=GameStatus.IN_PROGRESS,
        )
        prob = calculate_soccer_win_probability(state)
        assert prob.tie_prob > 0.1


class TestGenericWinProbability:
    """Tests for generic win probability and routing."""

    def test_sport_routing(self):
        """Test that correct model is called for each sport."""
        for sport in ["NFL", "NBA", "MLB", "NHL", "SOCCER"]:
            state = LiveGameState(
                game_id=f"test_{sport.lower()}",
                sport=sport,
                home_team="Home",
                away_team="Away",
                home_score=10,
                away_score=5,
                period="Q2" if sport in ["NFL", "NBA"] else "2nd",
                time_remaining="5:00",
                status=GameStatus.IN_PROGRESS,
            )
            prob = calculate_win_probability(state)
            assert prob.home_win_prob > 0.5

    def test_unknown_sport_uses_generic(self):
        """Unknown sport should use generic model."""
        state = LiveGameState(
            game_id="test_unknown",
            sport="CURLING",
            home_team="Home",
            away_team="Away",
            home_score=5,
            away_score=3,
            period="1st",
            time_remaining="10:00",
            status=GameStatus.IN_PROGRESS,
        )
        prob = calculate_win_probability(state)
        assert prob.model_used == "generic"


# =============================================================================
# Momentum Detection Tests
# =============================================================================

class TestMomentumAnalysis:
    """Tests for momentum detection."""

    def test_strong_home_momentum(self):
        """Test detection of strong home momentum."""
        state = LiveGameState(
            game_id="test_momentum",
            sport="NBA",
            home_team="Home",
            away_team="Away",
            home_score=80,
            away_score=70,
            period="Q3",
            time_remaining="5:00",
            status=GameStatus.IN_PROGRESS,
            scoring_plays=[
                {"team": "home", "points": 3},
                {"team": "home", "points": 2},
                {"team": "home", "points": 3},
                {"team": "home", "points": 2},
                {"team": "away", "points": 2},
            ]
        )
        momentum = analyze_momentum(state)
        assert momentum.score > 0
        assert momentum.level in [MomentumLevel.MODERATE_HOME, MomentumLevel.STRONG_HOME]

    def test_strong_away_momentum(self):
        """Test detection of strong away momentum."""
        state = LiveGameState(
            game_id="test_momentum_away",
            sport="NBA",
            home_team="Home",
            away_team="Away",
            home_score=70,
            away_score=80,
            period="Q3",
            time_remaining="5:00",
            status=GameStatus.IN_PROGRESS,
            scoring_plays=[
                {"team": "away", "points": 3},
                {"team": "away", "points": 2},
                {"team": "away", "points": 3},
                {"team": "away", "points": 2},
                {"team": "home", "points": 2},
            ]
        )
        momentum = analyze_momentum(state)
        assert momentum.score < 0
        assert momentum.level in [MomentumLevel.MODERATE_AWAY, MomentumLevel.STRONG_AWAY]

    def test_neutral_momentum(self):
        """Test detection of neutral momentum."""
        state = LiveGameState(
            game_id="test_momentum_neutral",
            sport="NBA",
            home_team="Home",
            away_team="Away",
            home_score=75,
            away_score=75,
            period="Q3",
            time_remaining="5:00",
            status=GameStatus.IN_PROGRESS,
            scoring_plays=[
                {"team": "home", "points": 2},
                {"team": "away", "points": 2},
                {"team": "home", "points": 3},
                {"team": "away", "points": 3},
            ]
        )
        momentum = analyze_momentum(state)
        assert -30 <= momentum.score <= 30
        assert momentum.level == MomentumLevel.NEUTRAL

    def test_insufficient_data(self):
        """Test with insufficient scoring data."""
        state = LiveGameState(
            game_id="test_momentum_empty",
            sport="NBA",
            home_team="Home",
            away_team="Away",
            home_score=5,
            away_score=3,
            period="Q1",
            time_remaining="10:00",
            status=GameStatus.IN_PROGRESS,
            scoring_plays=[{"team": "home", "points": 2}]
        )
        momentum = analyze_momentum(state)
        assert momentum.level == MomentumLevel.NEUTRAL
        assert "Insufficient" in momentum.key_events[0]


# =============================================================================
# Edge Detection Tests
# =============================================================================

class TestEdgeDetection:
    """Tests for live edge detection."""

    def test_moneyline_edge_detection(self):
        """Test detection of moneyline edge."""
        state = LiveGameState(
            game_id="test_edge",
            sport="NFL",
            home_team="Bills",
            away_team="Chiefs",
            home_score=24,
            away_score=17,
            period="Q4",
            time_remaining="3:00",
            status=GameStatus.IN_PROGRESS,
        )
        prob = calculate_win_probability(state)

        # Set odds that create an edge (home is underpriced)
        current_odds = {
            "home_ml": 100,  # Implied 50%, but model says higher
            "away_ml": -120,
        }

        edges = calculate_live_edges(state, prob, current_odds)

        # Should find home moneyline edge if model prob > 53%
        if prob.home_win_prob > 0.53:
            assert len(edges) >= 1
            home_edge = next((e for e in edges if e.side == "home"), None)
            assert home_edge is not None
            assert home_edge.edge_pct > 0

    def test_no_edge_when_odds_fair(self):
        """Test no edge when odds reflect fair value."""
        state = LiveGameState(
            game_id="test_no_edge",
            sport="NFL",
            home_team="Bills",
            away_team="Chiefs",
            home_score=14,
            away_score=14,
            period="Q2",
            time_remaining="8:00",
            status=GameStatus.IN_PROGRESS,
        )
        prob = calculate_win_probability(state)

        # Set odds that roughly match model probability
        # Tied game should be ~50%
        current_odds = {
            "home_ml": -110,  # Implied ~52%
            "away_ml": -110,
        }

        edges = calculate_live_edges(state, prob, current_odds)

        # Should not find significant edges
        large_edges = [e for e in edges if e.edge_pct >= 5]
        assert len(large_edges) == 0


# =============================================================================
# Helper Function Tests
# =============================================================================

class TestHelperFunctions:
    """Tests for helper functions."""

    def test_american_to_probability_favorite(self):
        """Test converting favorite odds to probability."""
        prob = _american_to_probability(-150)
        assert 0.59 <= prob <= 0.61  # Should be ~60%

    def test_american_to_probability_underdog(self):
        """Test converting underdog odds to probability."""
        prob = _american_to_probability(150)
        assert 0.39 <= prob <= 0.41  # Should be ~40%

    def test_probability_to_american_favorite(self):
        """Test converting high probability to favorite odds."""
        odds = _probability_to_american(0.6)
        assert odds < 0  # Should be negative (favorite)

    def test_probability_to_american_underdog(self):
        """Test converting low probability to underdog odds."""
        odds = _probability_to_american(0.4)
        assert odds > 0  # Should be positive (underdog)

    def test_parse_time_nfl(self):
        """Test parsing NFL time remaining."""
        minutes = _parse_time_remaining("Q1", "10:30", "NFL")
        assert minutes > 50  # Q1 with 10:30 left = 55:30 total

        minutes = _parse_time_remaining("Q4", "2:00", "NFL")
        assert minutes == 2.0

    def test_parse_time_nba(self):
        """Test parsing NBA time remaining."""
        minutes = _parse_time_remaining("Q1", "8:00", "NBA")
        assert minutes > 40  # Q1 with 8:00 left = 44:00 total

    def test_parse_time_soccer(self):
        """Test parsing soccer time remaining."""
        minutes = _parse_time_remaining("1st Half", "30", "SOCCER")
        assert 55 <= minutes <= 65  # 30 minutes played, ~60 left


# =============================================================================
# Simulation Tests
# =============================================================================

class TestSimulation:
    """Tests for game simulation."""

    def test_simulate_nfl(self):
        """Test simulating NFL game."""
        state = simulate_live_game("NFL", "test_sim_nfl")
        assert state.sport == "NFL"
        assert 7 <= state.home_score <= 28
        assert 7 <= state.away_score <= 28
        assert state.period in ["Q1", "Q2", "Q3", "Q4"]

    def test_simulate_nba(self):
        """Test simulating NBA game."""
        state = simulate_live_game("NBA", "test_sim_nba")
        assert state.sport == "NBA"
        assert 45 <= state.home_score <= 95
        assert 45 <= state.away_score <= 95

    def test_simulate_mlb(self):
        """Test simulating MLB game."""
        state = simulate_live_game("MLB", "test_sim_mlb")
        assert state.sport == "MLB"
        assert 0 <= state.home_score <= 7

    def test_simulate_nhl(self):
        """Test simulating NHL game."""
        state = simulate_live_game("NHL", "test_sim_nhl")
        assert state.sport == "NHL"
        assert 0 <= state.home_score <= 4

    def test_simulate_soccer(self):
        """Test simulating soccer game."""
        state = simulate_live_game("SOCCER", "test_sim_soccer")
        assert state.sport == "SOCCER"
        assert 0 <= state.home_score <= 3

    def test_simulation_has_scoring_plays(self):
        """Test that simulation includes scoring plays."""
        state = simulate_live_game("NBA", "test_sim_plays")
        assert len(state.scoring_plays) > 0


# =============================================================================
# Full Analysis Tests
# =============================================================================

class TestFullAnalysis:
    """Tests for complete game analysis."""

    def test_analyze_live_game_complete(self, nfl_game_state):
        """Test complete analysis returns all components."""
        current_odds = {
            "home_ml": -140,
            "away_ml": 120,
            "live_spread": -2.5,
            "live_total": 50.5,
        }

        result = analyze_live_game(nfl_game_state, current_odds)

        assert "probability" in result
        assert "momentum" in result
        assert "edges" in result
        assert "alerts" in result
        assert result["game_id"] == nfl_game_state.game_id
        assert result["sport"] == "NFL"

    def test_analyze_without_odds(self, nfl_game_state):
        """Test analysis without odds still works."""
        result = analyze_live_game(nfl_game_state, None)

        assert "probability" in result
        assert "momentum" in result
        assert result["edges"] == []  # No edges without odds


# =============================================================================
# Router Endpoint Tests
# =============================================================================

class TestLiveBettingRouter:
    """Tests for live betting API endpoints."""

    def test_demo_endpoint_no_auth(self):
        """Demo endpoint should work without auth."""
        response = client.get("/live/demo")
        assert response.status_code == 200
        data = response.json()
        assert data["demo"] is True
        assert "probability" in data
        assert "momentum" in data

    def test_models_endpoint(self):
        """Models endpoint should return model info."""
        response = client.get("/live/models")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert "NFL" in data["models"]
        assert "NBA" in data["models"]

    def test_analyze_requires_auth(self):
        """Analyze endpoint should require auth."""
        response = client.post("/live/analyze", json={
            "game_id": "test",
            "sport": "NFL",
            "home_team": "Bills",
            "away_team": "Chiefs",
            "home_score": 21,
            "away_score": 17,
            "period": "Q3",
            "time_remaining": "5:00"
        })
        assert response.status_code == 401

    def test_analyze_with_auth(self, auth_headers):
        """Test analyze endpoint with auth."""
        response = client.post("/live/analyze", json={
            "game_id": "test_api_001",
            "sport": "NFL",
            "home_team": "Buffalo Bills",
            "away_team": "Kansas City Chiefs",
            "home_score": 21,
            "away_score": 17,
            "period": "Q3",
            "time_remaining": "5:00",
            "home_ml_odds": -140,
            "away_ml_odds": 120
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["game_id"] == "test_api_001"
        assert "probability" in data

    def test_probability_endpoint(self, auth_headers):
        """Test probability endpoint."""
        response = client.post("/live/probability", json={
            "game_id": "test_prob_001",
            "sport": "NBA",
            "home_team": "Celtics",
            "away_team": "Lakers",
            "home_score": 80,
            "away_score": 75,
            "period": "Q3",
            "time_remaining": "6:00"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "probability" in data
        assert data["probability"]["home_win"] > 0.5

    def test_momentum_endpoint(self, auth_headers):
        """Test momentum endpoint."""
        response = client.post("/live/momentum", json={
            "game_id": "test_momentum_001",
            "sport": "NBA",
            "home_team": "Celtics",
            "away_team": "Lakers",
            "home_score": 80,
            "away_score": 75,
            "period": "Q3",
            "time_remaining": "6:00",
            "scoring_plays": [
                {"team": "home", "points": 3},
                {"team": "home", "points": 2},
                {"team": "away", "points": 2},
            ]
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "momentum" in data

    def test_momentum_without_plays(self, auth_headers):
        """Test momentum endpoint without scoring plays."""
        response = client.post("/live/momentum", json={
            "game_id": "test_momentum_empty",
            "sport": "NBA",
            "home_team": "Celtics",
            "away_team": "Lakers",
            "home_score": 10,
            "away_score": 8,
            "period": "Q1",
            "time_remaining": "8:00"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "note" in data

    def test_edges_endpoint(self, auth_headers):
        """Test edges endpoint."""
        response = client.post("/live/edges", json={
            "game_id": "test_edges_001",
            "sport": "NFL",
            "home_team": "Bills",
            "away_team": "Chiefs",
            "home_score": 28,
            "away_score": 14,
            "period": "Q4",
            "time_remaining": "3:00",
            "home_ml_odds": 100,
            "away_ml_odds": -120
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "edges" in data
        assert "model_probability" in data

    def test_edges_requires_odds(self, auth_headers):
        """Test edges endpoint requires odds."""
        response = client.post("/live/edges", json={
            "game_id": "test_edges_no_odds",
            "sport": "NFL",
            "home_team": "Bills",
            "away_team": "Chiefs",
            "home_score": 21,
            "away_score": 17,
            "period": "Q3",
            "time_remaining": "5:00"
        }, headers=auth_headers)
        assert response.status_code == 400

    def test_simulate_endpoint(self, auth_headers):
        """Test simulate endpoint."""
        response = client.get("/live/simulate/NFL", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["simulated"] is True
        assert data["sport"] == "NFL"

    def test_simulate_invalid_sport(self, auth_headers):
        """Test simulate endpoint with invalid sport."""
        response = client.get("/live/simulate/CURLING", headers=auth_headers)
        assert response.status_code == 400

    def test_bulk_analyze(self, auth_headers):
        """Test bulk analyze endpoint."""
        games = [
            {
                "game_id": "bulk_001",
                "sport": "NFL",
                "home_team": "Bills",
                "away_team": "Chiefs",
                "home_score": 21,
                "away_score": 17,
                "period": "Q3",
                "time_remaining": "5:00"
            },
            {
                "game_id": "bulk_002",
                "sport": "NBA",
                "home_team": "Celtics",
                "away_team": "Lakers",
                "home_score": 80,
                "away_score": 75,
                "period": "Q3",
                "time_remaining": "6:00"
            }
        ]
        response = client.post("/live/analyze/bulk", json=games, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["games_analyzed"] == 2
        assert len(data["results"]) == 2

    def test_bulk_analyze_limit(self, auth_headers):
        """Test bulk analyze respects limit."""
        games = [
            {
                "game_id": f"bulk_{i}",
                "sport": "NFL",
                "home_team": "Bills",
                "away_team": "Chiefs",
                "home_score": 21,
                "away_score": 17,
                "period": "Q3",
                "time_remaining": "5:00"
            }
            for i in range(25)  # Over limit
        ]
        response = client.post("/live/analyze/bulk", json=games, headers=auth_headers)
        assert response.status_code == 400

    def test_active_alerts_endpoint(self, auth_headers):
        """Test active alerts endpoint."""
        response = client.get("/live/alerts/active", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "active_alerts" in data

    def test_active_alerts_with_filters(self, auth_headers):
        """Test active alerts with filters."""
        response = client.get(
            "/live/alerts/active?sport=NFL&min_edge=5",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sport_filter"] == "NFL"
        assert data["min_edge"] == 5.0


# =============================================================================
# Alert Generation Tests
# =============================================================================

class TestAlertGeneration:
    """Tests for alert generation."""

    def test_high_edge_alert(self, nfl_game_state):
        """Test that high edges generate alerts."""
        prob = LiveProbability(
            home_win_prob=0.85,
            away_win_prob=0.15,
            confidence=0.8,
            model_used="nfl_time_score",
            factors=["Home leads by 14"]
        )
        momentum = MomentumAnalysis(
            level=MomentumLevel.MODERATE_HOME,
            score=30,
            trend="stable",
            recent_scoring={"home": 14, "away": 7},
            key_events=["Home team on run"]
        )
        edges = [
            LiveEdge(
                game_id="test",
                edge_type="moneyline",
                side="home",
                current_line=-110,
                fair_value=-300,
                edge_pct=8.5,
                confidence=0.8,
                recommendation="BET HOME ML",
                expires_at=datetime.utcnow() + timedelta(minutes=5)
            )
        ]

        alerts = generate_live_alerts(nfl_game_state, prob, momentum, edges)

        edge_alerts = [a for a in alerts if a["type"] == "edge_alert"]
        assert len(edge_alerts) >= 1
        assert edge_alerts[0]["priority"] == "high"

    def test_momentum_alert(self, nfl_game_state):
        """Test that strong momentum generates alerts."""
        prob = LiveProbability(
            home_win_prob=0.65,
            away_win_prob=0.35,
            confidence=0.6,
            model_used="nfl_time_score",
            factors=[]
        )
        momentum = MomentumAnalysis(
            level=MomentumLevel.STRONG_HOME,
            score=75,
            trend="increasing_home",
            recent_scoring={"home": 21, "away": 3},
            key_events=["Home team scored 4 of last 5 plays"]
        )

        alerts = generate_live_alerts(nfl_game_state, prob, momentum, [])

        momentum_alerts = [a for a in alerts if a["type"] == "momentum_alert"]
        assert len(momentum_alerts) >= 1
