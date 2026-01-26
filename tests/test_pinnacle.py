"""
Tests for Pinnacle sharp lines service.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch, AsyncMock

from app.services.pinnacle import (
    american_to_decimal,
    american_to_implied_prob,
    calculate_vig,
    calculate_no_vig_odds,
    fetch_pinnacle_odds,
    get_pinnacle_lines,
    compare_to_pinnacle,
    get_pinnacle_closing_line,
    calculate_clv_vs_pinnacle,
    get_market_efficiency,
    get_pinnacle_line_history,
    detect_sharp_line_movement,
    PINNACLE_SPORTSBOOK,
)


class TestAmericanToDecimal:
    """Test American to decimal odds conversion."""

    def test_positive_100(self):
        """+100 should be 2.0 decimal."""
        assert american_to_decimal(100) == 2.0

    def test_positive_200(self):
        """+200 should be 3.0 decimal."""
        assert american_to_decimal(200) == 3.0

    def test_negative_100(self):
        """-100 should be 2.0 decimal."""
        assert american_to_decimal(-100) == 2.0

    def test_negative_200(self):
        """-200 should be 1.5 decimal."""
        assert american_to_decimal(-200) == 1.5


class TestAmericanToImpliedProb:
    """Test American odds to implied probability conversion."""

    def test_positive_100(self):
        """+100 should be 50%."""
        assert american_to_implied_prob(100) == 0.5

    def test_negative_100(self):
        """-100 should be 50%."""
        assert american_to_implied_prob(-100) == 0.5

    def test_positive_200(self):
        """+200 should be ~33.3%."""
        result = american_to_implied_prob(200)
        assert abs(result - 0.333) < 0.01

    def test_negative_200(self):
        """-200 should be ~66.7%."""
        result = american_to_implied_prob(-200)
        assert abs(result - 0.667) < 0.01


class TestCalculateVig:
    """Test vigorish calculation."""

    def test_standard_vig(self):
        """-110/-110 should have ~4.5% vig."""
        vig = calculate_vig(-110, -110)
        assert 4 < vig < 5

    def test_pinnacle_low_vig(self):
        """-105/-105 should have ~2.4% vig (Pinnacle-like)."""
        vig = calculate_vig(-105, -105)
        assert 2 < vig < 3

    def test_no_vig_at_100(self):
        """+100/+100 should have 0% vig."""
        vig = calculate_vig(100, 100)
        assert abs(vig) < 0.1

    def test_heavy_vig(self):
        """-120/-120 should have higher vig."""
        vig = calculate_vig(-120, -120)
        assert vig > 5


class TestCalculateNoVigOdds:
    """Test no-vig (fair) odds calculation."""

    def test_equal_odds_50_50(self):
        """-110/-110 should be ~50/50 no-vig."""
        result = calculate_no_vig_odds(-110, -110)
        assert 49 < result["fair_prob1"] < 51
        assert 49 < result["fair_prob2"] < 51

    def test_probabilities_sum_to_100(self):
        """Fair probabilities should sum to 100%."""
        result = calculate_no_vig_odds(-150, 130)
        total = result["fair_prob1"] + result["fair_prob2"]
        assert 99 < total < 101

    def test_heavy_favorite(self):
        """-300/+250 should show heavy favorite."""
        result = calculate_no_vig_odds(-300, 250)
        assert result["fair_prob1"] > 60  # Favorite
        assert result["fair_prob2"] < 40  # Underdog


class TestCalculateCLVVsPinnacle:
    """Test CLV calculation against Pinnacle."""

    def test_positive_clv(self):
        """Bet at +150, closed at +130 = positive CLV."""
        result = calculate_clv_vs_pinnacle(150, 130)
        assert result["is_positive_clv"] is True
        assert result["clv_percentage"] > 0

    def test_negative_clv(self):
        """Bet at +130, closed at +150 = negative CLV."""
        result = calculate_clv_vs_pinnacle(130, 150)
        assert result["is_positive_clv"] is False
        assert result["clv_percentage"] < 0

    def test_same_odds_zero_clv(self):
        """Same odds should be zero CLV."""
        result = calculate_clv_vs_pinnacle(150, 150)
        assert abs(result["clv_percentage"]) < 0.1

    def test_favorite_positive_clv(self):
        """Bet at -110, closed at -120 = positive CLV."""
        result = calculate_clv_vs_pinnacle(-110, -120)
        assert result["is_positive_clv"] is True


class TestGetPinnacleClosingLine:
    """Test Pinnacle closing line retrieval."""

    def test_returns_closing_snapshot(self):
        """Should return last snapshot before game start."""
        mock_game = MagicMock()
        mock_game.start_time = datetime.utcnow()

        mock_snapshot = MagicMock()
        mock_snapshot.odds = -110
        mock_snapshot.line_value = -3.5
        mock_snapshot.captured_at = datetime.utcnow() - timedelta(hours=1)

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_game
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_snapshot

        result = get_pinnacle_closing_line(mock_db, game_id=1, market_type="spreads")

        assert result is not None
        assert result["odds"] == -110

    def test_returns_none_for_missing_game(self):
        """Should return None if game not found."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = get_pinnacle_closing_line(mock_db, game_id=999, market_type="h2h")

        assert result is None


class TestGetMarketEfficiency:
    """Test market efficiency analysis."""

    def test_returns_error_for_missing_market(self):
        """Should return error if no market found."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = get_market_efficiency(mock_db, game_id=1)

        assert "error" in result

    def test_returns_error_without_pinnacle_line(self):
        """Should return error if no Pinnacle line."""
        mock_market = MagicMock()
        mock_line = MagicMock()
        mock_line.sportsbook = "DraftKings"  # Not Pinnacle
        mock_line.american_odds = -110
        mock_market.lines = [mock_line]

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_market

        result = get_market_efficiency(mock_db, game_id=1)

        assert "error" in result

    def test_calculates_deviations(self):
        """Should calculate deviations from Pinnacle."""
        mock_market = MagicMock()

        mock_pinn_line = MagicMock()
        mock_pinn_line.sportsbook = PINNACLE_SPORTSBOOK
        mock_pinn_line.american_odds = -105

        mock_dk_line = MagicMock()
        mock_dk_line.sportsbook = "DraftKings"
        mock_dk_line.american_odds = -110

        mock_market.lines = [mock_pinn_line, mock_dk_line]

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_market

        result = get_market_efficiency(mock_db, game_id=1)

        assert "pinnacle_baseline" in result
        assert "sportsbook_comparisons" in result
        assert len(result["sportsbook_comparisons"]) == 1


class TestGetPinnacleLineHistory:
    """Test line history retrieval."""

    def test_returns_ordered_history(self):
        """Should return snapshots in chronological order."""
        mock_snap1 = MagicMock()
        mock_snap1.odds = -105
        mock_snap1.line_value = -3.0
        mock_snap1.captured_at = datetime.utcnow() - timedelta(hours=2)

        mock_snap2 = MagicMock()
        mock_snap2.odds = -110
        mock_snap2.line_value = -3.5
        mock_snap2.captured_at = datetime.utcnow() - timedelta(hours=1)

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_snap1, mock_snap2]

        result = get_pinnacle_line_history(mock_db, game_id=1)

        assert len(result) == 2
        assert result[0]["movement"] is None  # First has no previous
        assert result[1]["movement"] == -5  # -110 - (-105) = -5

    def test_empty_history(self):
        """Should return empty list if no history."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        result = get_pinnacle_line_history(mock_db, game_id=1)

        assert result == []


class TestDetectSharpLineMovement:
    """Test sharp line movement detection."""

    def test_detects_significant_movement(self):
        """Should detect movements above threshold."""
        mock_game = MagicMock()
        mock_game.id = 1
        mock_game.sport = "NBA"
        mock_game.home_team = MagicMock(name="Lakers")
        mock_game.away_team = MagicMock(name="Celtics")
        mock_game.start_time = datetime.utcnow() + timedelta(hours=5)
        mock_game.status = "scheduled"

        mock_snap1 = MagicMock()
        mock_snap1.odds = -105
        mock_snap1.market_type = "h2h"
        mock_snap1.captured_at = datetime.utcnow() - timedelta(hours=12)

        mock_snap2 = MagicMock()
        mock_snap2.odds = -120  # 15 cent movement
        mock_snap2.market_type = "h2h"
        mock_snap2.captured_at = datetime.utcnow() - timedelta(hours=1)

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_game]
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_snap1, mock_snap2]

        result = detect_sharp_line_movement(mock_db, sport="NBA", threshold_cents=10)

        assert len(result) == 1
        assert result[0]["movement"] == -15

    def test_ignores_small_movements(self):
        """Should ignore movements below threshold."""
        mock_game = MagicMock()
        mock_game.id = 1
        mock_game.sport = "NBA"
        mock_game.home_team = MagicMock(name="Lakers")
        mock_game.away_team = MagicMock(name="Celtics")
        mock_game.start_time = datetime.utcnow() + timedelta(hours=5)
        mock_game.status = "scheduled"

        mock_snap1 = MagicMock()
        mock_snap1.odds = -105
        mock_snap1.market_type = "h2h"
        mock_snap1.captured_at = datetime.utcnow() - timedelta(hours=12)

        mock_snap2 = MagicMock()
        mock_snap2.odds = -108  # Only 3 cent movement
        mock_snap2.market_type = "h2h"
        mock_snap2.captured_at = datetime.utcnow() - timedelta(hours=1)

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_game]
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_snap1, mock_snap2]

        result = detect_sharp_line_movement(mock_db, sport="NBA", threshold_cents=10)

        assert len(result) == 0


class TestFetchPinnacleOdds:
    """Test Pinnacle odds fetching."""

    @pytest.mark.asyncio
    async def test_returns_empty_when_api_not_configured(self):
        """Should return empty list if API not configured."""
        with patch('app.services.pinnacle.is_odds_api_configured', return_value=False):
            result = await fetch_pinnacle_odds("NBA")
            assert result == []

    @pytest.mark.asyncio
    async def test_filters_for_pinnacle_only(self):
        """Should only return games with Pinnacle odds."""
        mock_odds_data = [
            {
                "id": "game1",
                "home_team": "Lakers",
                "away_team": "Celtics",
                "commence_time": "2024-01-15T19:00:00Z",
                "bookmakers": [
                    {
                        "title": "Pinnacle",
                        "markets": [{"key": "h2h", "outcomes": []}],
                        "last_update": "2024-01-15T18:00:00Z"
                    }
                ]
            },
            {
                "id": "game2",
                "home_team": "Warriors",
                "away_team": "Heat",
                "commence_time": "2024-01-15T20:00:00Z",
                "bookmakers": [
                    {
                        "title": "DraftKings",  # No Pinnacle
                        "markets": []
                    }
                ]
            }
        ]

        # Clear any cached data first
        from app.utils.cache import cache
        cache.clear()

        with patch('app.services.pinnacle.is_odds_api_configured', return_value=True):
            with patch('app.services.pinnacle.fetch_odds', new_callable=AsyncMock, return_value=mock_odds_data):
                result = await fetch_pinnacle_odds("NBA")

        assert len(result) == 1  # Only game1 has Pinnacle
        assert result[0]["home_team"] == "Lakers"


class TestGetPinnacleLines:
    """Test formatted Pinnacle lines."""

    @pytest.mark.asyncio
    async def test_formats_with_vig_calculation(self):
        """Should include vig for two-way markets."""
        mock_pinnacle_data = [
            {
                "home_team": "Lakers",
                "away_team": "Celtics",
                "commence_time": "2024-01-15T19:00:00Z",
                "pinnacle_markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Lakers", "price": -105},
                            {"name": "Celtics", "price": -105}
                        ]
                    }
                ]
            }
        ]

        with patch('app.services.pinnacle.fetch_pinnacle_odds', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_pinnacle_data
            result = await get_pinnacle_lines("NBA")

        assert len(result) == 1
        assert "vig" in result[0]["markets"]["h2h"]
        assert "no_vig" in result[0]["markets"]["h2h"]


class TestCompareTopinnacle:
    """Test sportsbook comparison to Pinnacle."""

    @pytest.mark.asyncio
    async def test_finds_value_opportunities(self):
        """Should identify when other book offers better odds."""
        mock_pinnacle_games = [
            {
                "home_team": "Lakers",
                "away_team": "Celtics",
                "commence_time": "2024-01-15T19:00:00Z",
                "pinnacle_markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Lakers", "price": -110},
                            {"name": "Celtics", "price": 100}
                        ]
                    }
                ]
            }
        ]

        mock_all_odds = [
            {
                "home_team": "Lakers",
                "away_team": "Celtics",
                "bookmakers": [
                    {
                        "title": "DraftKings",
                        "markets": [
                            {
                                "key": "h2h",
                                "outcomes": [
                                    {"name": "Lakers", "price": -105},  # Better than Pinnacle!
                                    {"name": "Celtics", "price": 100}
                                ]
                            }
                        ]
                    }
                ]
            }
        ]

        mock_db = MagicMock()

        with patch('app.services.pinnacle.fetch_pinnacle_odds', new_callable=AsyncMock) as mock_pinn:
            with patch('app.services.pinnacle.fetch_odds', new_callable=AsyncMock) as mock_all:
                mock_pinn.return_value = mock_pinnacle_games
                mock_all.return_value = mock_all_odds

                result = await compare_to_pinnacle("NBA", "DraftKings", mock_db)

        assert len(result) == 1
        assert result[0]["selection"] == "Lakers"
        assert result[0]["edge_vs_pinnacle"] > 0


class TestConstants:
    """Test service constants."""

    def test_pinnacle_sportsbook_name(self):
        """Sportsbook name should be 'Pinnacle'."""
        assert PINNACLE_SPORTSBOOK == "Pinnacle"
