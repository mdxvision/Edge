"""
Tests for P&L Dashboard service.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from app.services.pnl_dashboard import (
    TimeFrame,
    StreakInfo,
    get_timeframe_dates,
    get_pnl_summary,
    get_roi_by_market_type,
    get_roi_by_sport,
    get_roi_by_sportsbook,
    get_streak_analysis,
    get_unit_tracking,
    export_bets_csv,
    get_performance_by_odds_range,
    get_dashboard_summary,
    _calculate_summary,
    _get_daily_breakdown,
    _calc_pct_change,
    _streak_to_dict,
    _dedupe_periods,
)


class TestTimeFrame:
    """Test TimeFrame enum."""

    def test_today_value(self):
        """Today timeframe has correct value."""
        assert TimeFrame.TODAY.value == "today"

    def test_all_time_value(self):
        """All time timeframe has correct value."""
        assert TimeFrame.ALL_TIME.value == "all_time"

    def test_last_30_days_value(self):
        """Last 30 days timeframe has correct value."""
        assert TimeFrame.LAST_30_DAYS.value == "last_30_days"


class TestGetTimeframeDates:
    """Test timeframe date calculation."""

    def test_all_time_returns_none(self):
        """All time should return None for both dates."""
        start, end = get_timeframe_dates(TimeFrame.ALL_TIME)
        assert start is None
        assert end is None

    def test_today_returns_today(self):
        """Today should return today's start to now."""
        start, end = get_timeframe_dates(TimeFrame.TODAY)
        now = datetime.utcnow()
        assert start.date() == now.date()
        assert end is not None

    def test_last_30_days(self):
        """Last 30 days should return 30 day range."""
        start, end = get_timeframe_dates(TimeFrame.LAST_30_DAYS)
        diff = (end - start).days
        assert diff == 30

    def test_last_90_days(self):
        """Last 90 days should return 90 day range."""
        start, end = get_timeframe_dates(TimeFrame.LAST_90_DAYS)
        diff = (end - start).days
        assert diff == 90

    def test_this_month_starts_at_first(self):
        """This month should start on the 1st."""
        start, end = get_timeframe_dates(TimeFrame.THIS_MONTH)
        assert start.day == 1


class TestCalculateSummary:
    """Test summary calculation."""

    def test_empty_bets(self):
        """Empty list should return zeros."""
        bets = []
        # _calculate_summary requires bets, so we test via get_pnl_summary
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        result = get_pnl_summary(mock_db, 1, TimeFrame.ALL_TIME, "USD")
        assert result["summary"]["total_bets"] == 0

    def test_calculates_win_rate(self):
        """Should calculate correct win rate."""
        mock_bet1 = MagicMock()
        mock_bet1.result = "won"
        mock_bet1.stake = 100
        mock_bet1.profit_loss = 91
        mock_bet1.currency = "USD"
        mock_bet1.odds = -110
        mock_bet1.settled_at = datetime.utcnow()

        mock_bet2 = MagicMock()
        mock_bet2.result = "lost"
        mock_bet2.stake = 100
        mock_bet2.profit_loss = -100
        mock_bet2.currency = "USD"
        mock_bet2.odds = -110
        mock_bet2.settled_at = datetime.utcnow()

        bets = [mock_bet1, mock_bet2]
        summary = _calculate_summary(bets, "USD")

        assert summary["total_bets"] == 2
        assert summary["wins"] == 1
        assert summary["losses"] == 1
        assert summary["win_rate"] == 50.0

    def test_calculates_roi(self):
        """Should calculate correct ROI."""
        mock_bet = MagicMock()
        mock_bet.result = "won"
        mock_bet.stake = 100
        mock_bet.profit_loss = 100
        mock_bet.currency = "USD"
        mock_bet.odds = 100
        mock_bet.settled_at = datetime.utcnow()

        summary = _calculate_summary([mock_bet], "USD")

        assert summary["roi"] == 100.0  # 100% ROI

    def test_tracks_biggest_win_loss(self):
        """Should track biggest win and loss."""
        mock_win = MagicMock()
        mock_win.result = "won"
        mock_win.stake = 100
        mock_win.profit_loss = 500
        mock_win.currency = "USD"
        mock_win.odds = 500
        mock_win.settled_at = datetime.utcnow()

        mock_loss = MagicMock()
        mock_loss.result = "lost"
        mock_loss.stake = 200
        mock_loss.profit_loss = -200
        mock_loss.currency = "USD"
        mock_loss.odds = -110
        mock_loss.settled_at = datetime.utcnow()

        summary = _calculate_summary([mock_win, mock_loss], "USD")

        assert summary["biggest_win"] == 500.0
        assert summary["biggest_loss"] == -200.0


class TestGetDailyBreakdown:
    """Test daily breakdown calculation."""

    def test_groups_by_date(self):
        """Should group bets by date."""
        today = datetime.utcnow()
        yesterday = today - timedelta(days=1)

        mock_bet1 = MagicMock()
        mock_bet1.result = "won"
        mock_bet1.stake = 100
        mock_bet1.profit_loss = 100
        mock_bet1.currency = "USD"
        mock_bet1.settled_at = today

        mock_bet2 = MagicMock()
        mock_bet2.result = "lost"
        mock_bet2.stake = 100
        mock_bet2.profit_loss = -100
        mock_bet2.currency = "USD"
        mock_bet2.settled_at = yesterday

        daily = _get_daily_breakdown([mock_bet2, mock_bet1], "USD")

        assert len(daily) == 2

    def test_cumulative_profit(self):
        """Should track cumulative profit."""
        now = datetime.utcnow()

        mock_bet1 = MagicMock()
        mock_bet1.result = "won"
        mock_bet1.stake = 100
        mock_bet1.profit_loss = 100
        mock_bet1.currency = "USD"
        mock_bet1.settled_at = now

        mock_bet2 = MagicMock()
        mock_bet2.result = "won"
        mock_bet2.stake = 100
        mock_bet2.profit_loss = 50
        mock_bet2.currency = "USD"
        mock_bet2.settled_at = now

        daily = _get_daily_breakdown([mock_bet1, mock_bet2], "USD")

        assert daily[0]["cumulative"] == 150.0


class TestCalcPctChange:
    """Test percentage change calculation."""

    def test_positive_change(self):
        """Should calculate positive change."""
        change = _calc_pct_change(100, 150)
        assert change == 50.0

    def test_negative_change(self):
        """Should calculate negative change."""
        change = _calc_pct_change(100, 50)
        assert change == -50.0

    def test_zero_old_value(self):
        """Should handle zero old value."""
        change = _calc_pct_change(0, 100)
        assert change == 100.0

    def test_zero_to_zero(self):
        """Zero to zero should be zero change."""
        change = _calc_pct_change(0, 0)
        assert change == 0.0


class TestGetRoiByMarketType:
    """Test ROI by market type."""

    def test_groups_by_bet_type(self):
        """Should group results by bet type."""
        mock_spread = MagicMock()
        mock_spread.bet_type = "spread"
        mock_spread.result = "won"
        mock_spread.stake = 100
        mock_spread.profit_loss = 91
        mock_spread.currency = "USD"
        mock_spread.settled_at = datetime.utcnow()

        mock_ml = MagicMock()
        mock_ml.bet_type = "moneyline"
        mock_ml.result = "lost"
        mock_ml.stake = 100
        mock_ml.profit_loss = -100
        mock_ml.currency = "USD"
        mock_ml.settled_at = datetime.utcnow()

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_spread, mock_ml]

        result = get_roi_by_market_type(mock_db, 1, TimeFrame.ALL_TIME, "USD")

        assert "spread" in result
        assert "moneyline" in result
        assert result["spread"]["win_rate"] == 100.0
        assert result["moneyline"]["win_rate"] == 0.0


class TestGetRoiBySport:
    """Test ROI by sport."""

    def test_groups_by_sport(self):
        """Should group results by sport."""
        mock_nba = MagicMock()
        mock_nba.sport = "NBA"
        mock_nba.result = "won"
        mock_nba.stake = 100
        mock_nba.profit_loss = 100
        mock_nba.currency = "USD"
        mock_nba.settled_at = datetime.utcnow()

        mock_nfl = MagicMock()
        mock_nfl.sport = "NFL"
        mock_nfl.result = "lost"
        mock_nfl.stake = 100
        mock_nfl.profit_loss = -100
        mock_nfl.currency = "USD"
        mock_nfl.settled_at = datetime.utcnow()

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_nba, mock_nfl]

        result = get_roi_by_sport(mock_db, 1, TimeFrame.ALL_TIME, "USD")

        assert "NBA" in result
        assert "NFL" in result


class TestGetRoiBySportsbook:
    """Test ROI by sportsbook."""

    def test_groups_by_sportsbook(self):
        """Should group results by sportsbook."""
        mock_dk = MagicMock()
        mock_dk.sportsbook = "DraftKings"
        mock_dk.result = "won"
        mock_dk.stake = 100
        mock_dk.profit_loss = 100
        mock_dk.currency = "USD"
        mock_dk.settled_at = datetime.utcnow()

        mock_fd = MagicMock()
        mock_fd.sportsbook = "FanDuel"
        mock_fd.result = "lost"
        mock_fd.stake = 100
        mock_fd.profit_loss = -100
        mock_fd.currency = "USD"
        mock_fd.settled_at = datetime.utcnow()

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_dk, mock_fd]

        result = get_roi_by_sportsbook(mock_db, 1, TimeFrame.ALL_TIME, "USD")

        assert "DraftKings" in result
        assert "FanDuel" in result

    def test_handles_null_sportsbook(self):
        """Should handle null sportsbook."""
        mock_bet = MagicMock()
        mock_bet.sportsbook = None
        mock_bet.result = "won"
        mock_bet.stake = 100
        mock_bet.profit_loss = 100
        mock_bet.currency = "USD"
        mock_bet.settled_at = datetime.utcnow()

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_bet]

        result = get_roi_by_sportsbook(mock_db, 1, TimeFrame.ALL_TIME, "USD")

        assert "unspecified" in result


class TestGetStreakAnalysis:
    """Test streak analysis."""

    def test_empty_bets(self):
        """Empty bets should return null streaks."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        result = get_streak_analysis(mock_db, 1, "USD")

        assert result["current_streak"]["type"] is None
        assert result["best_win_streak"] is None

    def test_identifies_win_streak(self):
        """Should identify winning streaks."""
        now = datetime.utcnow()
        bets = []

        for i in range(5):
            mock_bet = MagicMock()
            mock_bet.id = i
            mock_bet.result = "won"
            mock_bet.stake = 100
            mock_bet.profit_loss = 91
            mock_bet.currency = "USD"
            mock_bet.settled_at = now + timedelta(hours=i)
            bets.append(mock_bet)

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = bets

        result = get_streak_analysis(mock_db, 1, "USD")

        assert result["current_streak"]["type"] == "win"
        assert result["current_streak"]["length"] == 5

    def test_identifies_lose_streak(self):
        """Should identify losing streaks."""
        now = datetime.utcnow()
        bets = []

        for i in range(3):
            mock_bet = MagicMock()
            mock_bet.id = i
            mock_bet.result = "lost"
            mock_bet.stake = 100
            mock_bet.profit_loss = -100
            mock_bet.currency = "USD"
            mock_bet.settled_at = now + timedelta(hours=i)
            bets.append(mock_bet)

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = bets

        result = get_streak_analysis(mock_db, 1, "USD")

        assert result["current_streak"]["type"] == "lose"
        assert result["current_streak"]["length"] == 3


class TestStreakToDict:
    """Test streak conversion to dict."""

    def test_converts_correctly(self):
        """Should convert StreakInfo to dict."""
        now = datetime.utcnow()
        streak = StreakInfo(
            streak_type="win",
            length=5,
            start_date=now,
            end_date=now + timedelta(days=1),
            profit_loss=500.0,
            bets=[1, 2, 3, 4, 5]
        )

        result = _streak_to_dict(streak)

        assert result["type"] == "win"
        assert result["length"] == 5
        assert result["profit"] == 500.0


class TestDedupePeriods:
    """Test period deduplication."""

    def test_empty_list(self):
        """Empty list should return empty."""
        result = _dedupe_periods([])
        assert result == []

    def test_removes_overlaps(self):
        """Should remove overlapping periods."""
        periods = [
            {"start_date": "2024-01-01", "end_date": "2024-01-10", "profit": 100},
            {"start_date": "2024-01-05", "end_date": "2024-01-15", "profit": 50},  # Overlaps
        ]

        result = _dedupe_periods(periods)

        assert len(result) == 1
        assert result[0]["profit"] == 100  # Keeps the better one


class TestGetUnitTracking:
    """Test unit tracking."""

    def test_empty_bets(self):
        """Empty bets should return zeros."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        result = get_unit_tracking(mock_db, 1, 100.0, TimeFrame.ALL_TIME, "USD")

        assert result["net_units"] == 0.0
        assert result["total_units_wagered"] == 0.0

    def test_calculates_units(self):
        """Should calculate units correctly."""
        mock_bet = MagicMock()
        mock_bet.stake = 250  # 2.5 units at $100 base
        mock_bet.profit_loss = 200
        mock_bet.currency = "USD"
        mock_bet.settled_at = datetime.utcnow()
        mock_bet.id = 1

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_bet]

        result = get_unit_tracking(mock_db, 1, 100.0, TimeFrame.ALL_TIME, "USD")

        assert result["total_units_wagered"] == 2.5
        assert result["net_units"] == 2.0  # 200/100


class TestExportBetsCsv:
    """Test CSV export."""

    def test_creates_csv(self):
        """Should create valid CSV."""
        mock_bet = MagicMock()
        mock_bet.id = 1
        mock_bet.placed_at = datetime(2024, 1, 15, 10, 30)
        mock_bet.settled_at = datetime(2024, 1, 15, 12, 30)
        mock_bet.sport = "NBA"
        mock_bet.bet_type = "spread"
        mock_bet.selection = "Lakers -5.5"
        mock_bet.odds = -110
        mock_bet.stake = 100
        mock_bet.currency = "USD"
        mock_bet.potential_profit = 91
        mock_bet.status = "settled"
        mock_bet.result = "won"
        mock_bet.profit_loss = 91
        mock_bet.sportsbook = "DraftKings"
        mock_bet.notes = "Test bet"

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_bet]

        csv_data = export_bets_csv(mock_db, 1, TimeFrame.ALL_TIME, False)

        assert "ID" in csv_data  # Header
        assert "NBA" in csv_data
        assert "Lakers -5.5" in csv_data
        assert "DraftKings" in csv_data


class TestGetPerformanceByOddsRange:
    """Test odds range performance."""

    def test_groups_by_odds(self):
        """Should group bets by odds range."""
        mock_favorite = MagicMock()
        mock_favorite.odds = -150
        mock_favorite.result = "won"
        mock_favorite.stake = 100
        mock_favorite.profit_loss = 67
        mock_favorite.currency = "USD"
        mock_favorite.settled_at = datetime.utcnow()

        mock_underdog = MagicMock()
        mock_underdog.odds = 200
        mock_underdog.result = "lost"
        mock_underdog.stake = 100
        mock_underdog.profit_loss = -100
        mock_underdog.currency = "USD"
        mock_underdog.settled_at = datetime.utcnow()

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_favorite, mock_underdog]

        result = get_performance_by_odds_range(mock_db, 1, TimeFrame.ALL_TIME, "USD")

        # Should have entries for different odds ranges
        assert len(result) >= 2

        # Find the moderate favorites range
        mod_fav = next((r for r in result if "Moderate Favorites" in r["odds_range"]), None)
        assert mod_fav is not None
        assert mod_fav["total_bets"] == 1


class TestGetDashboardSummary:
    """Test full dashboard summary."""

    def test_returns_all_sections(self):
        """Should return all dashboard sections."""
        mock_db = MagicMock()
        # Setup empty returns for all queries
        mock_db.query.return_value.filter.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.all.return_value = []

        result = get_dashboard_summary(mock_db, 1, "USD")

        assert "all_time" in result
        assert "this_month" in result
        assert "last_30_days" in result
        assert "by_sport" in result
        assert "by_market_type" in result
        assert "by_sportsbook" in result
        assert "by_odds_range" in result
        assert "streaks" in result
        assert "units" in result


class TestIntegration:
    """Integration tests for P&L dashboard."""

    def test_full_workflow(self):
        """Test complete workflow with realistic data."""
        now = datetime.utcnow()
        bets = []

        # Create a week of betting data
        for i in range(10):
            mock_bet = MagicMock()
            mock_bet.id = i + 1
            mock_bet.sport = "NBA" if i % 2 == 0 else "NFL"
            mock_bet.bet_type = "spread" if i % 3 == 0 else "moneyline"
            mock_bet.sportsbook = "DraftKings" if i % 2 == 0 else "FanDuel"
            mock_bet.result = "won" if i % 2 == 0 else "lost"
            mock_bet.odds = -110 if i % 2 == 0 else 150
            mock_bet.stake = 100
            mock_bet.profit_loss = 91 if i % 2 == 0 else -100
            mock_bet.currency = "USD"
            mock_bet.settled_at = now - timedelta(days=i)
            mock_bet.placed_at = now - timedelta(days=i, hours=2)
            mock_bet.potential_profit = 91 if i % 2 == 0 else 150
            mock_bet.status = "settled"
            mock_bet.selection = f"Team {i}"
            mock_bet.notes = None
            bets.append(mock_bet)

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = bets
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = bets
        mock_db.query.return_value.filter.return_value.all.return_value = bets

        # Test P&L summary
        summary = get_pnl_summary(mock_db, 1, TimeFrame.LAST_30_DAYS, "USD")
        assert summary["summary"]["total_bets"] == 10
        assert summary["summary"]["wins"] == 5  # Every other bet

        # Test ROI by sport
        sport_roi = get_roi_by_sport(mock_db, 1, TimeFrame.ALL_TIME, "USD")
        assert "NBA" in sport_roi
        assert "NFL" in sport_roi

        # Test ROI by market
        market_roi = get_roi_by_market_type(mock_db, 1, TimeFrame.ALL_TIME, "USD")
        assert "spread" in market_roi or "moneyline" in market_roi

        # Test streaks
        streaks = get_streak_analysis(mock_db, 1, "USD")
        assert streaks["current_streak"] is not None

        # Test units
        units = get_unit_tracking(mock_db, 1, 100.0, TimeFrame.ALL_TIME, "USD")
        assert units["total_units_wagered"] == 10.0  # 10 bets at $100

        # Test CSV export - uses different query chain
        mock_csv_db = MagicMock()
        mock_csv_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = bets
        csv = export_bets_csv(mock_csv_db, 1, TimeFrame.ALL_TIME, False)
        assert "ID" in csv
        assert "NBA" in csv or "NFL" in csv
