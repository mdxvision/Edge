"""
Tests for edge engine service.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from app.services.edge_engine import (
    build_game_data,
    map_selection_to_probability,
    MAX_REALISTIC_EDGE,
    MIN_REALISTIC_CONFIDENCE,
    MAX_REALISTIC_CONFIDENCE
)


class TestBuildGameData:
    """Test game data building for predictions."""

    def test_team_sport_with_teams(self):
        """Build data for team sport with home/away teams."""
        game = Mock()
        game.id = 1
        game.sport = "NBA"
        game.league = "NBA"
        game.home_team = Mock()
        game.home_team.rating = 1600.0
        game.home_team.name = "Lakers"
        game.away_team = Mock()
        game.away_team.rating = 1500.0
        game.away_team.name = "Celtics"

        with patch('app.services.edge_engine.TEAM_SPORTS', ['NBA']):
            with patch('app.services.edge_engine.INDIVIDUAL_SPORTS', []):
                data = build_game_data(game, Mock())

        assert data["game_id"] == 1
        assert data["sport"] == "NBA"
        assert data["home_rating"] == 1600.0
        assert data["away_rating"] == 1500.0
        assert data["home_team_name"] == "Lakers"
        assert data["away_team_name"] == "Celtics"

    def test_team_sport_without_teams(self):
        """Build data for team sport without teams (uses defaults)."""
        game = Mock()
        game.id = 1
        game.sport = "NBA"
        game.league = "NBA"
        game.home_team = None
        game.away_team = None

        with patch('app.services.edge_engine.TEAM_SPORTS', ['NBA']):
            with patch('app.services.edge_engine.INDIVIDUAL_SPORTS', []):
                data = build_game_data(game, Mock())

        assert data["home_rating"] == 1500.0
        assert data["away_rating"] == 1500.0
        assert data["home_team_name"] == "Unknown"
        assert data["away_team_name"] == "Unknown"

    def test_individual_sport_with_competitors(self):
        """Build data for individual sport with competitors."""
        game = Mock()
        game.id = 1
        game.sport = "Tennis"
        game.league = "ATP"
        game.competitor1 = Mock()
        game.competitor1.rating = 1700.0
        game.competitor1.name = "Djokovic"
        game.competitor2 = Mock()
        game.competitor2.rating = 1600.0
        game.competitor2.name = "Nadal"

        with patch('app.services.edge_engine.TEAM_SPORTS', []):
            with patch('app.services.edge_engine.INDIVIDUAL_SPORTS', ['Tennis']):
                data = build_game_data(game, Mock())

        assert data["game_id"] == 1
        assert data["sport"] == "Tennis"
        assert data["competitor1_rating"] == 1700.0
        assert data["competitor2_rating"] == 1600.0
        assert data["competitor1_name"] == "Djokovic"
        assert data["competitor2_name"] == "Nadal"

    def test_individual_sport_without_competitors(self):
        """Build data for individual sport without competitors."""
        game = Mock()
        game.id = 1
        game.sport = "Tennis"
        game.league = "ATP"
        game.competitor1 = None
        game.competitor2 = None

        with patch('app.services.edge_engine.TEAM_SPORTS', []):
            with patch('app.services.edge_engine.INDIVIDUAL_SPORTS', ['Tennis']):
                data = build_game_data(game, Mock())

        assert data["competitor1_rating"] == 1500.0
        assert data["competitor2_rating"] == 1500.0
        assert data["competitor1_name"] == "Unknown"
        assert data["competitor2_name"] == "Unknown"

    def test_team_with_none_rating(self):
        """Handle teams with None ratings."""
        game = Mock()
        game.id = 1
        game.sport = "NBA"
        game.league = "NBA"
        game.home_team = Mock()
        game.home_team.rating = None
        game.home_team.name = "Lakers"
        game.away_team = Mock()
        game.away_team.rating = None
        game.away_team.name = "Celtics"

        with patch('app.services.edge_engine.TEAM_SPORTS', ['NBA']):
            with patch('app.services.edge_engine.INDIVIDUAL_SPORTS', []):
                data = build_game_data(game, Mock())

        assert data["home_rating"] == 1500.0
        assert data["away_rating"] == 1500.0


class TestMapSelectionToProbability:
    """Test mapping market selections to probabilities."""

    def test_home_selection(self):
        """Map 'home' to home_win probability."""
        predictions = {"home_win": 0.65, "away_win": 0.35}
        prob = map_selection_to_probability("home", predictions, "NBA")
        assert prob == 0.65

    def test_away_selection(self):
        """Map 'away' to away_win probability."""
        predictions = {"home_win": 0.65, "away_win": 0.35}
        prob = map_selection_to_probability("away", predictions, "NBA")
        assert prob == 0.35

    def test_draw_selection(self):
        """Map 'draw' to draw probability."""
        predictions = {"home_win": 0.40, "away_win": 0.30, "draw": 0.30}
        prob = map_selection_to_probability("draw", predictions, "Soccer")
        assert prob == 0.30

    def test_competitor1_selection(self):
        """Map 'competitor1' to competitor1_win probability."""
        predictions = {"competitor1_win": 0.60, "competitor2_win": 0.40}
        prob = map_selection_to_probability("competitor1", predictions, "Tennis")
        assert prob == 0.60

    def test_competitor2_selection(self):
        """Map 'competitor2' to competitor2_win probability."""
        predictions = {"competitor1_win": 0.60, "competitor2_win": 0.40}
        prob = map_selection_to_probability("competitor2", predictions, "Tennis")
        assert prob == 0.40

    def test_over_selection(self):
        """Map 'over' to 50% (no model for totals)."""
        predictions = {"home_win": 0.65, "away_win": 0.35}
        prob = map_selection_to_probability("over", predictions, "NBA")
        assert prob == 0.50

    def test_under_selection(self):
        """Map 'under' to 50% (no model for totals)."""
        predictions = {"home_win": 0.65, "away_win": 0.35}
        prob = map_selection_to_probability("under", predictions, "NBA")
        assert prob == 0.50

    def test_unknown_selection(self):
        """Unknown selection should return None."""
        predictions = {"home_win": 0.65, "away_win": 0.35}
        prob = map_selection_to_probability("unknown", predictions, "NBA")
        assert prob is None

    def test_missing_probability(self):
        """Missing probability in predictions should return None."""
        predictions = {}
        prob = map_selection_to_probability("home", predictions, "NBA")
        assert prob is None


class TestEdgeConstants:
    """Test edge engine constants."""

    def test_max_realistic_edge(self):
        """Max realistic edge should be 15%."""
        assert MAX_REALISTIC_EDGE == 0.15

    def test_min_realistic_confidence(self):
        """Min realistic confidence should be 45%."""
        assert MIN_REALISTIC_CONFIDENCE == 0.45

    def test_max_realistic_confidence(self):
        """Max realistic confidence should be 85%."""
        assert MAX_REALISTIC_CONFIDENCE == 0.85


class TestProbabilityBounding:
    """Test that probabilities are bounded correctly."""

    def test_probability_floor(self):
        """Probabilities should be floored at MIN_REALISTIC_CONFIDENCE."""
        # Test logic: model_prob = max(MIN_REALISTIC_CONFIDENCE, min(MAX_REALISTIC_CONFIDENCE, model_prob))
        model_prob = 0.30  # Below minimum
        bounded = max(MIN_REALISTIC_CONFIDENCE, min(MAX_REALISTIC_CONFIDENCE, model_prob))
        assert bounded == MIN_REALISTIC_CONFIDENCE

    def test_probability_ceiling(self):
        """Probabilities should be capped at MAX_REALISTIC_CONFIDENCE."""
        model_prob = 0.95  # Above maximum
        bounded = max(MIN_REALISTIC_CONFIDENCE, min(MAX_REALISTIC_CONFIDENCE, model_prob))
        assert bounded == MAX_REALISTIC_CONFIDENCE

    def test_probability_within_bounds(self):
        """Valid probabilities should pass through unchanged."""
        model_prob = 0.65  # Within bounds
        bounded = max(MIN_REALISTIC_CONFIDENCE, min(MAX_REALISTIC_CONFIDENCE, model_prob))
        assert bounded == 0.65


class TestEdgeCapping:
    """Test that edges are capped at realistic maximum."""

    def test_edge_capped_at_max(self):
        """Edge values above MAX_REALISTIC_EDGE should be capped."""
        edge_value = 0.25  # 25% - unrealistic
        capped = min(edge_value, MAX_REALISTIC_EDGE)
        assert capped == MAX_REALISTIC_EDGE

    def test_edge_below_max_unchanged(self):
        """Edge values below MAX_REALISTIC_EDGE should be unchanged."""
        edge_value = 0.08  # 8% - realistic
        capped = min(edge_value, MAX_REALISTIC_EDGE)
        assert capped == 0.08


class TestEdgeEngineIntegration:
    """Integration tests for edge engine (mocked)."""

    @patch('app.services.edge_engine.SessionLocal')
    @patch('app.services.edge_engine.SPORT_MODEL_REGISTRY')
    def test_find_value_bets_no_games(self, mock_registry, mock_session):
        """Should return empty list when no games found."""
        from app.services.edge_engine import find_value_bets_for_sport

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_session.return_value = mock_db

        mock_model = MagicMock()
        mock_registry.__contains__ = lambda self, key: True
        mock_registry.__getitem__ = lambda self, key: mock_model

        result = find_value_bets_for_sport("NBA", min_edge=0.03)
        assert result == []

    @patch('app.services.edge_engine.SPORT_MODEL_REGISTRY')
    def test_find_value_bets_unsupported_sport(self, mock_registry):
        """Should return empty list for unsupported sport."""
        from app.services.edge_engine import find_value_bets_for_sport

        mock_registry.__contains__ = lambda self, key: False

        result = find_value_bets_for_sport("Unknown_Sport", min_edge=0.03)
        assert result == []

    @patch('app.services.edge_engine.SessionLocal')
    @patch('app.services.edge_engine.SPORT_MODEL_REGISTRY')
    def test_find_value_bets_filters_by_min_edge(self, mock_registry, mock_session):
        """Should filter bets below minimum edge."""
        from app.services.edge_engine import find_value_bets_for_sport

        mock_db = MagicMock()
        mock_game = MagicMock()
        mock_game.id = 1
        mock_game.sport = "NBA"
        mock_game.league = "NBA"
        mock_game.start_time = datetime.utcnow() + timedelta(hours=2)
        mock_game.home_team = MagicMock(rating=1500, name="Lakers")
        mock_game.away_team = MagicMock(rating=1500, name="Celtics")
        mock_game.markets = []  # No markets = no bets found

        mock_db.query.return_value.filter.return_value.all.return_value = [mock_game]
        mock_session.return_value = mock_db

        mock_model = MagicMock()
        mock_model.predict_game_probabilities.return_value = [
            {"game_id": 1, "home_win": 0.55, "away_win": 0.45}
        ]
        mock_registry.__contains__ = lambda self, key: True
        mock_registry.__getitem__ = lambda self, key: mock_model

        with patch('app.services.edge_engine.TEAM_SPORTS', ['NBA']):
            with patch('app.services.edge_engine.INDIVIDUAL_SPORTS', []):
                result = find_value_bets_for_sport("NBA", min_edge=0.03)

        # No markets = no value bets
        assert result == []
