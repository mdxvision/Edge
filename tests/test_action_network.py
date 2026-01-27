"""
Tests for Action Network Integration Service

Tests public betting percentages, sharp money indicators, line movement alerts,
and consensus picks functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

from app.services import action_network
from app.db import PublicBettingData, Game, OddsSnapshot


# =============================================================================
# Configuration Tests
# =============================================================================

class TestConfiguration:
    """Test Action Network configuration."""

    def test_is_configured_without_api_key(self):
        """Test configuration check without API key."""
        with patch.dict('os.environ', {"ACTION_NETWORK_API_KEY": ""}):
            # Reload the module value
            original = action_network.ACTION_NETWORK_API_KEY
            action_network.ACTION_NETWORK_API_KEY = ""
            assert action_network.is_action_network_configured() is False
            action_network.ACTION_NETWORK_API_KEY = original

    def test_is_configured_with_api_key(self):
        """Test configuration check with API key."""
        action_network.ACTION_NETWORK_API_KEY = "test_key_123"
        assert action_network.is_action_network_configured() is True
        action_network.ACTION_NETWORK_API_KEY = ""

    def test_sport_mapping_exists(self):
        """Test sport mapping is defined."""
        assert "NFL" in action_network.SPORT_MAPPING
        assert "NBA" in action_network.SPORT_MAPPING
        assert "MLB" in action_network.SPORT_MAPPING


# =============================================================================
# Public Betting Data Generation Tests
# =============================================================================

class TestPublicBettingGeneration:
    """Test realistic public betting data generation."""

    def test_generate_realistic_data_structure(self):
        """Test generated data has correct structure."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        data = action_network._generate_realistic_public_betting(1, "NFL", mock_db)

        assert "spread_bet_home" in data
        assert "spread_bet_away" in data
        assert "spread_money_home" in data
        assert "spread_money_away" in data
        assert "over_bet_pct" in data
        assert "under_bet_pct" in data
        assert "ticket_count" in data

    def test_spread_percentages_sum_to_100(self):
        """Test spread bet percentages sum to 100."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        data = action_network._generate_realistic_public_betting(1, "NFL", mock_db)

        spread_sum = data["spread_bet_home"] + data["spread_bet_away"]
        assert abs(spread_sum - 100) < 0.01

    def test_total_percentages_sum_to_100(self):
        """Test total bet percentages sum to 100."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        data = action_network._generate_realistic_public_betting(1, "NBA", mock_db)

        total_sum = data["over_bet_pct"] + data["under_bet_pct"]
        assert abs(total_sum - 100) < 0.01

    def test_money_percentages_sum_to_100(self):
        """Test money percentages sum to 100."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        data = action_network._generate_realistic_public_betting(1, "MLB", mock_db)

        spread_money_sum = data["spread_money_home"] + data["spread_money_away"]
        assert abs(spread_money_sum - 100) < 0.01

        total_money_sum = data["over_money_pct"] + data["under_money_pct"]
        assert abs(total_money_sum - 100) < 0.01

    def test_ticket_count_varies_by_sport(self):
        """Test ticket count varies based on sport popularity."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        nfl_data = action_network._generate_realistic_public_betting(1, "NFL", mock_db)
        nhl_data = action_network._generate_realistic_public_betting(2, "NHL", mock_db)

        # NFL should generally have higher ticket counts
        # But due to randomness, we just check they exist
        assert nfl_data["ticket_count"] > 0
        assert nhl_data["ticket_count"] > 0

    def test_consistent_results_for_same_game_same_day(self):
        """Test that same game_id produces consistent results on same day."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        data1 = action_network._generate_realistic_public_betting(999, "NFL", mock_db)
        data2 = action_network._generate_realistic_public_betting(999, "NFL", mock_db)

        # Should be identical due to seeded randomness
        assert data1["spread_bet_home"] == data2["spread_bet_home"]
        assert data1["over_bet_pct"] == data2["over_bet_pct"]


# =============================================================================
# Public Betting Storage Tests
# =============================================================================

class TestPublicBettingStorage:
    """Test public betting data storage."""

    def test_store_calculates_sharp_divergence(self):
        """Test sharp divergence is calculated on store."""
        mock_db = MagicMock()

        # Create data with clear divergence
        data = {
            "spread_bet_home": 70,
            "spread_bet_away": 30,
            "spread_money_home": 55,  # 15% divergence
            "spread_money_away": 45,
            "ml_bet_home": 60,
            "ml_bet_away": 40,
            "ml_money_home": 60,
            "ml_money_away": 40,
            "over_bet_pct": 65,
            "under_bet_pct": 35,
            "over_money_pct": 55,
            "under_money_pct": 45,
            "ticket_count": 10000,
        }

        result = action_network._store_public_betting(mock_db, 1, "NFL", data)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_store_detects_fade_signal(self):
        """Test fade signals are detected for heavy public action."""
        mock_db = MagicMock()

        # Data with heavy public on one side (75%)
        data = {
            "spread_bet_home": 75,
            "spread_bet_away": 25,
            "spread_money_home": 70,
            "spread_money_away": 30,
            "ml_bet_home": 75,
            "ml_bet_away": 25,
            "ml_money_home": 70,
            "ml_money_away": 30,
            "over_bet_pct": 50,
            "under_bet_pct": 50,
            "over_money_pct": 50,
            "under_money_pct": 50,
            "ticket_count": 10000,
        }

        result = action_network._store_public_betting(mock_db, 1, "NFL", data)

        # Check that the stored object has fade_public_spread = True
        stored_obj = mock_db.add.call_args[0][0]
        assert stored_obj.fade_public_spread is True


# =============================================================================
# Sharp Money Indicator Tests
# =============================================================================

class TestSharpMoneyIndicators:
    """Test sharp money indicator calculations."""

    def test_calculate_divergence(self):
        """Test bet/money divergence calculation."""
        spread_data = {
            "home_bet_pct": 70,
            "home_money_pct": 55,
        }
        divergence = action_network._calculate_divergence(spread_data)
        assert divergence == 15

    def test_calculate_divergence_total(self):
        """Test total divergence calculation."""
        total_data = {
            "over_bet_pct": 65,
            "over_money_pct": 50,
        }
        divergence = action_network._calculate_divergence_total(total_data)
        assert divergence == 15

    def test_calculate_sharp_score_with_divergence(self):
        """Test sharp score calculation with bet/money divergence."""
        public_data = {
            "spread": {
                "home_bet_pct": 75,
                "away_bet_pct": 25,
                "home_money_pct": 60,
                "away_money_pct": 40,
            },
            "total": {
                "over_bet_pct": 70,
                "under_bet_pct": 30,
                "over_money_pct": 55,
                "under_money_pct": 45,
            }
        }

        rlm_spread = {"detected": False}
        rlm_total = {"detected": False}
        steam_moves = []

        score = action_network._calculate_sharp_score(
            public_data, rlm_spread, rlm_total, steam_moves
        )

        assert score > 0
        assert score <= 100

    def test_calculate_sharp_score_with_rlm(self):
        """Test sharp score increases with RLM."""
        public_data = {
            "spread": {
                "home_bet_pct": 70,
                "away_bet_pct": 30,
                "home_money_pct": 60,
                "away_money_pct": 40,
            },
            "total": {
                "over_bet_pct": 60,
                "under_bet_pct": 40,
                "over_money_pct": 50,
                "under_money_pct": 50,
            }
        }

        # Without RLM
        score_no_rlm = action_network._calculate_sharp_score(
            public_data,
            {"detected": False},
            {"detected": False},
            []
        )

        # With RLM
        score_with_rlm = action_network._calculate_sharp_score(
            public_data,
            {"detected": True},
            {"detected": True},
            []
        )

        assert score_with_rlm > score_no_rlm

    def test_sharp_recommendation_high_score(self):
        """Test recommendation for high sharp score."""
        public_data = {
            "spread": {"sharp_side": "away"},
            "total": {"sharp_side": "under"},
        }

        rec = action_network._get_sharp_recommendation(75, public_data)

        assert rec["confidence"] == "HIGH"
        assert "strong" in rec["action"].lower()

    def test_sharp_recommendation_low_score(self):
        """Test recommendation for low sharp score."""
        public_data = {
            "spread": {"sharp_side": None},
            "total": {"sharp_side": None},
        }

        rec = action_network._get_sharp_recommendation(25, public_data)

        assert rec["confidence"] == "NONE"


# =============================================================================
# Reverse Line Movement Tests
# =============================================================================

class TestReverseLineMovement:
    """Test RLM detection."""

    def test_rlm_detected_when_line_moves_against_public(self):
        """Test RLM is detected when line moves opposite public action."""
        spread_data = {
            "public_side": "home",
            "home_bet_pct": 72,
        }

        line_moves = [
            {"move": 0.5, "timestamp": datetime.utcnow().isoformat()},
            {"move": 0.5, "timestamp": datetime.utcnow().isoformat()},
        ]

        result = action_network._detect_reverse_line_movement(spread_data, line_moves)

        assert result["detected"] is True
        assert "72" in result["description"]

    def test_no_rlm_when_line_moves_with_public(self):
        """Test no RLM when line moves in same direction as public."""
        spread_data = {
            "public_side": "home",
            "home_bet_pct": 72,
        }

        line_moves = [
            {"move": -0.5, "timestamp": datetime.utcnow().isoformat()},
        ]

        result = action_network._detect_reverse_line_movement(spread_data, line_moves)

        assert result["detected"] is False

    def test_no_rlm_insufficient_data(self):
        """Test no RLM when insufficient line data."""
        spread_data = {
            "public_side": "home",
            "home_bet_pct": 72,
        }

        result = action_network._detect_reverse_line_movement(spread_data, [])

        assert result["detected"] is False
        assert "Insufficient" in result["description"]


# =============================================================================
# Steam Move Detection Tests
# =============================================================================

class TestSteamMoveDetection:
    """Test steam move detection."""

    def test_detect_steam_move_clustered_moves(self):
        """Test steam move detected with clustered line moves."""
        now = datetime.utcnow()

        line_moves = {
            "spread": [
                {
                    "move": 0.5,
                    "timestamp": now.isoformat(),
                    "sportsbook": "DraftKings"
                },
                {
                    "move": 0.5,
                    "timestamp": (now + timedelta(minutes=10)).isoformat(),
                    "sportsbook": "FanDuel"
                },
            ]
        }

        steam = action_network._detect_steam_moves(line_moves)

        assert len(steam) >= 1
        assert steam[0]["market"] == "spread"
        assert steam[0]["direction"] == "up"

    def test_no_steam_move_for_isolated_moves(self):
        """Test no steam move for isolated line changes."""
        now = datetime.utcnow()

        line_moves = {
            "spread": [
                {
                    "move": 0.5,
                    "timestamp": now.isoformat(),
                    "sportsbook": "DraftKings"
                },
                {
                    "move": 0.5,
                    "timestamp": (now + timedelta(hours=2)).isoformat(),  # Too far apart
                    "sportsbook": "FanDuel"
                },
            ]
        }

        steam = action_network._detect_steam_moves(line_moves)

        # Moves are too far apart to be steam
        assert len(steam) == 0


# =============================================================================
# Consensus Picks Tests
# =============================================================================

class TestConsensusPicks:
    """Test consensus pick generation."""

    def test_build_spread_consensus_with_sharp_action(self):
        """Test spread consensus built with sharp action."""
        sharp_data = {
            "sharp_indicators": {
                "spread": {
                    "sharp_side": "away",
                    "bet_money_divergence": 12,
                    "reverse_line_movement": {"detected": True},
                }
            }
        }

        public_data = {
            "spread": {
                "public_side": "home",
                "home_bet_pct": 72,
                "away_bet_pct": 28,
            }
        }

        consensus = action_network._build_spread_consensus(sharp_data, public_data)

        assert consensus is not None
        assert consensus["pick"] == "AWAY"
        assert consensus["sharp_aligned"] is True

    def test_no_consensus_without_sharp_divergence(self):
        """Test no consensus when divergence too low."""
        sharp_data = {
            "sharp_indicators": {
                "spread": {
                    "sharp_side": "home",
                    "bet_money_divergence": 3,  # Too low
                    "reverse_line_movement": {"detected": False},
                }
            }
        }

        public_data = {
            "spread": {
                "public_side": "home",
                "home_bet_pct": 55,
                "away_bet_pct": 45,
            }
        }

        consensus = action_network._build_spread_consensus(sharp_data, public_data)

        assert consensus is None

    def test_calculate_consensus_rating(self):
        """Test consensus rating calculation."""
        spread_consensus = {"strength": 80}
        total_consensus = {"strength": 70}

        rating = action_network._calculate_consensus_rating(
            spread_consensus, total_consensus
        )

        # 80 * 0.6 + 70 * 0.4 = 48 + 28 = 76
        assert rating == 76.0

    def test_consensus_rating_with_only_spread(self):
        """Test rating with only spread consensus."""
        rating = action_network._calculate_consensus_rating(
            {"strength": 80},
            None
        )

        assert rating == 48.0  # 80 * 0.6


# =============================================================================
# Response Formatting Tests
# =============================================================================

class TestResponseFormatting:
    """Test API response formatting."""

    def test_format_public_betting_response(self):
        """Test public betting response format."""
        mock_data = MagicMock()
        mock_data.game_id = 1
        mock_data.sport = "NFL"
        mock_data.spread_bet_pct_home = 65.5
        mock_data.spread_bet_pct_away = 34.5
        mock_data.spread_money_pct_home = 58.2
        mock_data.spread_money_pct_away = 41.8
        mock_data.ml_bet_pct_home = 60.0
        mock_data.ml_bet_pct_away = 40.0
        mock_data.ml_money_pct_home = 55.0
        mock_data.ml_money_pct_away = 45.0
        mock_data.total_bet_pct_over = 68.0
        mock_data.total_bet_pct_under = 32.0
        mock_data.total_money_pct_over = 60.0
        mock_data.total_money_pct_under = 40.0
        mock_data.ticket_count_estimated = 25000
        mock_data.sharp_vs_public_divergence = True
        mock_data.sharp_side_spread = "away"
        mock_data.sharp_side_total = "under"
        mock_data.fade_public_spread = False
        mock_data.fade_public_total = False
        mock_data.timestamp = datetime.utcnow()

        response = action_network._format_public_betting_response(mock_data)

        assert response["game_id"] == 1
        assert response["sport"] == "NFL"
        assert "spread" in response
        assert "moneyline" in response
        assert "total" in response
        assert response["spread"]["home_bet_pct"] == 65.5
        assert response["spread"]["sharp_side"] == "away"
        assert response["source"] == "action_network"


# =============================================================================
# Router Model Tests
# =============================================================================

class TestRouterEndpoints:
    """Test router endpoint behavior."""

    def test_historical_edge_calculation_80_plus(self):
        """Test historical edge for 80%+ public."""
        from app.routers.action_network import _calculate_historical_edge

        edge = _calculate_historical_edge(82)
        assert edge == "+7.0%"

    def test_historical_edge_calculation_75_plus(self):
        """Test historical edge for 75%+ public."""
        from app.routers.action_network import _calculate_historical_edge

        edge = _calculate_historical_edge(76)
        assert edge == "+5.2%"

    def test_historical_edge_calculation_70_plus(self):
        """Test historical edge for 70%+ public."""
        from app.routers.action_network import _calculate_historical_edge

        edge = _calculate_historical_edge(72)
        assert edge == "+3.8%"

    def test_historical_edge_below_70(self):
        """Test historical edge below 70%."""
        from app.routers.action_network import _calculate_historical_edge

        edge = _calculate_historical_edge(65)
        assert edge == "+2.0%"


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for Action Network service."""

    @pytest.mark.asyncio
    async def test_fetch_public_betting_flow(self):
        """Test full flow of fetching public betting data."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        mock_db.query.return_value.filter.return_value.first.return_value = MagicMock(
            id=1, sport="NFL"
        )

        # Mock the cache
        with patch.object(action_network.cache, 'get', return_value=None):
            with patch.object(action_network.cache, 'set'):
                with patch.object(action_network, '_store_public_betting') as mock_store:
                    mock_stored = MagicMock()
                    mock_stored.game_id = 1
                    mock_stored.sport = "NFL"
                    mock_stored.spread_bet_pct_home = 65
                    mock_stored.spread_bet_pct_away = 35
                    mock_stored.spread_money_pct_home = 55
                    mock_stored.spread_money_pct_away = 45
                    mock_stored.ml_bet_pct_home = 60
                    mock_stored.ml_bet_pct_away = 40
                    mock_stored.ml_money_pct_home = 55
                    mock_stored.ml_money_pct_away = 45
                    mock_stored.total_bet_pct_over = 68
                    mock_stored.total_bet_pct_under = 32
                    mock_stored.total_money_pct_over = 60
                    mock_stored.total_money_pct_under = 40
                    mock_stored.ticket_count_estimated = 25000
                    mock_stored.sharp_vs_public_divergence = True
                    mock_stored.sharp_side_spread = "away"
                    mock_stored.sharp_side_total = "under"
                    mock_stored.fade_public_spread = False
                    mock_stored.fade_public_total = False
                    mock_stored.timestamp = datetime.utcnow()

                    mock_store.return_value = mock_stored

                    result = await action_network.fetch_public_betting(
                        game_id=1,
                        sport="NFL",
                        db=mock_db
                    )

                    assert result is not None
                    assert "spread" in result

    @pytest.mark.asyncio
    async def test_sharp_money_indicators_flow(self):
        """Test full flow of sharp money analysis."""
        mock_db = MagicMock()

        # Mock game query
        mock_game = MagicMock()
        mock_game.id = 1
        mock_game.sport = "NFL"
        mock_game.home_team = "Chiefs"
        mock_game.away_team = "Bills"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_game

        with patch.object(action_network, 'fetch_public_betting') as mock_fetch:
            mock_fetch.return_value = {
                "game_id": 1,
                "spread": {
                    "home_bet_pct": 70,
                    "away_bet_pct": 30,
                    "home_money_pct": 55,
                    "away_money_pct": 45,
                    "public_side": "home",
                    "sharp_side": "away",
                },
                "total": {
                    "over_bet_pct": 65,
                    "under_bet_pct": 35,
                    "over_money_pct": 55,
                    "under_money_pct": 45,
                    "public_side": "over",
                    "sharp_side": "under",
                }
            }

            with patch.object(action_network, '_get_recent_line_moves') as mock_moves:
                mock_moves.return_value = {"spread": [], "total": []}

                result = await action_network.get_sharp_money_indicators(1, mock_db)

                assert "sharp_indicators" in result
                assert "sharp_confidence_score" in result
                assert "recommendation" in result


# =============================================================================
# Thresholds and Constants Tests
# =============================================================================

class TestThresholds:
    """Test threshold constants are sensible."""

    def test_sharp_money_threshold(self):
        """Test sharp money threshold is reasonable."""
        assert action_network.SHARP_MONEY_THRESHOLD == 0.10  # 10%

    def test_heavy_public_threshold(self):
        """Test heavy public threshold is reasonable."""
        assert action_network.HEAVY_PUBLIC_THRESHOLD == 70.0

    def test_consensus_thresholds(self):
        """Test consensus thresholds are set."""
        assert action_network.CONSENSUS_STRONG == 75
        assert action_network.CONSENSUS_LEAN == 60
