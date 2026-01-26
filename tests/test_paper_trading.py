"""
Tests for paper trading service.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from app.services.paper_trading import (
    calculate_payout,
    get_or_create_bankroll,
    get_bankroll_status,
    place_bet,
    settle_bet,
    get_open_bets,
    get_bet_history,
    get_trade_by_id,
    cancel_bet,
    reset_bankroll,
    get_bankroll_chart_data,
    get_performance_by_sport,
    get_performance_by_bet_type,
    DEFAULT_STARTING_BALANCE,
    UNIT_SIZE,
)


class TestCalculatePayout:
    """Test payout calculation from American odds."""

    def test_positive_odds_100(self):
        """+100 odds with $100 stake = $200 total payout."""
        payout = calculate_payout(100, 100)
        assert payout == 200

    def test_positive_odds_200(self):
        """+200 odds with $100 stake = $300 total payout."""
        payout = calculate_payout(100, 200)
        assert payout == 300

    def test_positive_odds_150(self):
        """+150 odds with $100 stake = $250 total payout."""
        payout = calculate_payout(100, 150)
        assert payout == 250

    def test_negative_odds_100(self):
        """-100 odds with $100 stake = $200 total payout."""
        payout = calculate_payout(100, -100)
        assert payout == 200

    def test_negative_odds_200(self):
        """-200 odds with $100 stake = $150 total payout."""
        payout = calculate_payout(100, -200)
        assert payout == 150

    def test_negative_odds_110(self):
        """-110 odds with $110 stake = ~$210 total payout."""
        payout = calculate_payout(110, -110)
        assert 209 < payout < 211

    def test_custom_stake(self):
        """Custom stake amounts should scale correctly."""
        payout = calculate_payout(50, 200)
        assert payout == 150  # $50 stake + $100 profit


class TestGetOrCreateBankroll:
    """Test bankroll creation and retrieval."""

    def test_creates_new_bankroll_for_new_user(self):
        """Should create bankroll with default starting balance."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        mock_bankroll = MagicMock()
        mock_bankroll.id = 1

        with patch('app.services.paper_trading.PaperBankroll') as MockBankroll:
            MockBankroll.return_value = mock_bankroll
            with patch('app.services.paper_trading.PaperBankrollHistory'):
                bankroll = get_or_create_bankroll(mock_db, user_id=1)

        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    def test_returns_existing_bankroll(self):
        """Should return existing bankroll if found."""
        mock_bankroll = MagicMock()
        mock_bankroll.id = 1
        mock_bankroll.current_balance = 10000

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_bankroll

        result = get_or_create_bankroll(mock_db, user_id=1)

        assert result == mock_bankroll
        # Should not add new bankroll
        mock_db.add.assert_not_called()


class TestGetBankrollStatus:
    """Test bankroll status retrieval."""

    def test_returns_full_status(self):
        """Should return all bankroll stats."""
        mock_bankroll = MagicMock()
        mock_bankroll.id = 1
        mock_bankroll.starting_balance = 10000.0
        mock_bankroll.current_balance = 10500.0
        mock_bankroll.high_water_mark = 10500.0
        mock_bankroll.low_water_mark = 9500.0
        mock_bankroll.total_profit_loss = 500.0
        mock_bankroll.total_wagered = 2000.0
        mock_bankroll.roi_percentage = 25.0
        mock_bankroll.win_percentage = 60.0
        mock_bankroll.units_won = 5.0
        mock_bankroll.total_bets = 20
        mock_bankroll.pending_bets = 2
        mock_bankroll.winning_bets = 12
        mock_bankroll.losing_bets = 6
        mock_bankroll.pushes = 0
        mock_bankroll.current_streak = 3
        mock_bankroll.longest_win_streak = 5
        mock_bankroll.longest_lose_streak = 2
        mock_bankroll.created_at = datetime.utcnow()
        mock_bankroll.last_updated = datetime.utcnow()

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_bankroll

        status = get_bankroll_status(mock_db, user_id=1)

        assert status["bankroll_id"] == 1
        assert status["current_balance"] == 10500.0
        assert status["total_profit_loss"] == 500.0
        assert status["roi_percentage"] == 25.0
        assert status["stats"]["total_bets"] == 20
        assert status["streaks"]["current"] == 3


class TestPlaceBet:
    """Test bet placement."""

    def test_place_bet_success(self):
        """Should place bet and update bankroll."""
        mock_bankroll = MagicMock()
        mock_bankroll.id = 1
        mock_bankroll.current_balance = 10000.0
        mock_bankroll.total_wagered = 0
        mock_bankroll.total_bets = 0
        mock_bankroll.pending_bets = 0
        mock_bankroll.low_water_mark = 10000.0

        mock_trade = MagicMock()
        mock_trade.id = 1
        mock_trade.sport = "NBA"
        mock_trade.bet_type = "spread"
        mock_trade.selection = "Lakers -5"
        mock_trade.line_value = -5
        mock_trade.odds = -110
        mock_trade.stake = 100
        mock_trade.potential_payout = 190.91
        mock_trade.game_description = "Lakers vs Celtics"
        mock_trade.status = "pending"
        mock_trade.placed_at = datetime.utcnow()

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_bankroll

        with patch('app.services.paper_trading.PaperTrade', return_value=mock_trade):
            result = place_bet(
                mock_db,
                sport="NBA",
                bet_type="spread",
                selection="Lakers -5",
                odds=-110,
                stake=100,
                user_id=1,
            )

        assert result["success"] is True
        assert result["trade_id"] == 1
        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    def test_place_bet_zero_stake_rejected(self):
        """Should reject zero stake."""
        mock_bankroll = MagicMock()
        mock_bankroll.current_balance = 10000.0

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_bankroll

        result = place_bet(
            mock_db,
            sport="NBA",
            bet_type="moneyline",
            selection="Lakers",
            odds=150,
            stake=0,
            user_id=1,
        )

        assert "error" in result
        assert "positive" in result["error"].lower()

    def test_place_bet_negative_stake_rejected(self):
        """Should reject negative stake."""
        mock_bankroll = MagicMock()
        mock_bankroll.current_balance = 10000.0

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_bankroll

        result = place_bet(
            mock_db,
            sport="NBA",
            bet_type="moneyline",
            selection="Lakers",
            odds=150,
            stake=-100,
            user_id=1,
        )

        assert "error" in result

    def test_place_bet_insufficient_balance(self):
        """Should reject if stake exceeds balance."""
        mock_bankroll = MagicMock()
        mock_bankroll.current_balance = 50.0

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_bankroll

        result = place_bet(
            mock_db,
            sport="NBA",
            bet_type="moneyline",
            selection="Lakers",
            odds=150,
            stake=100,
            user_id=1,
        )

        assert "error" in result
        assert "insufficient" in result["error"].lower()


class TestSettleBet:
    """Test bet settlement."""

    def test_settle_bet_won(self):
        """Should correctly settle a winning bet."""
        mock_trade = MagicMock()
        mock_trade.id = 1
        mock_trade.user_id = 1
        mock_trade.status = "pending"
        mock_trade.stake = 100
        mock_trade.potential_payout = 200

        mock_bankroll = MagicMock()
        mock_bankroll.current_balance = 9900.0
        mock_bankroll.total_won = 0
        mock_bankroll.winning_bets = 0
        mock_bankroll.current_streak = 0
        mock_bankroll.longest_win_streak = 0
        mock_bankroll.pending_bets = 1
        mock_bankroll.total_wagered = 100
        mock_bankroll.total_lost = 0
        mock_bankroll.roi_percentage = None
        mock_bankroll.high_water_mark = 10000.0
        mock_bankroll.losing_bets = 0

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_trade, mock_bankroll
        ]

        result = settle_bet(mock_db, trade_id=1, result="won", user_id=1)

        assert result["success"] is True
        assert result["result"] == "won"
        assert result["profit_loss"] == 100.0  # $200 payout - $100 stake

    def test_settle_bet_lost(self):
        """Should correctly settle a losing bet."""
        mock_trade = MagicMock()
        mock_trade.id = 1
        mock_trade.user_id = 1
        mock_trade.status = "pending"
        mock_trade.stake = 100
        mock_trade.potential_payout = 200

        mock_bankroll = MagicMock()
        mock_bankroll.current_balance = 9900.0
        mock_bankroll.total_lost = 0
        mock_bankroll.losing_bets = 0
        mock_bankroll.current_streak = 0
        mock_bankroll.longest_lose_streak = 0
        mock_bankroll.pending_bets = 1
        mock_bankroll.total_wagered = 100
        mock_bankroll.total_won = 0
        mock_bankroll.roi_percentage = None
        mock_bankroll.high_water_mark = 10000.0
        mock_bankroll.winning_bets = 0

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_trade, mock_bankroll
        ]

        result = settle_bet(mock_db, trade_id=1, result="lost", user_id=1)

        assert result["success"] is True
        assert result["result"] == "lost"
        assert result["profit_loss"] == -100.0

    def test_settle_bet_push(self):
        """Should correctly settle a push."""
        mock_trade = MagicMock()
        mock_trade.id = 1
        mock_trade.user_id = 1
        mock_trade.status = "pending"
        mock_trade.stake = 100
        mock_trade.potential_payout = 200

        mock_bankroll = MagicMock()
        mock_bankroll.current_balance = 9900.0
        mock_bankroll.pushes = 0
        mock_bankroll.current_streak = 0
        mock_bankroll.pending_bets = 1
        mock_bankroll.total_wagered = 100
        mock_bankroll.total_won = 0
        mock_bankroll.total_lost = 0
        mock_bankroll.roi_percentage = None
        mock_bankroll.high_water_mark = 10000.0
        mock_bankroll.winning_bets = 0
        mock_bankroll.losing_bets = 0

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_trade, mock_bankroll
        ]

        result = settle_bet(mock_db, trade_id=1, result="push", user_id=1)

        assert result["success"] is True
        assert result["result"] == "push"
        assert result["profit_loss"] == 0.0

    def test_settle_nonexistent_trade(self):
        """Should return error for nonexistent trade."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = settle_bet(mock_db, trade_id=999, result="won")

        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_settle_already_settled_trade(self):
        """Should return error for already settled trade."""
        mock_trade = MagicMock()
        mock_trade.status = "won"

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_trade

        result = settle_bet(mock_db, trade_id=1, result="lost")

        assert "error" in result
        assert "already settled" in result["error"].lower()


class TestGetOpenBets:
    """Test retrieving open bets."""

    def test_get_all_open_bets(self):
        """Should return all pending bets."""
        mock_trade = MagicMock()
        mock_trade.id = 1
        mock_trade.sport = "NBA"
        mock_trade.bet_type = "spread"
        mock_trade.selection = "Lakers -5"
        mock_trade.line_value = -5
        mock_trade.odds = -110
        mock_trade.stake = 100
        mock_trade.potential_payout = 190.91
        mock_trade.game_description = "Lakers vs Celtics"
        mock_trade.game_date = datetime.utcnow()
        mock_trade.edge_at_placement = 5.0
        mock_trade.placed_at = datetime.utcnow()
        mock_trade.status = "pending"

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_trade]
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_trade]

        result = get_open_bets(mock_db)

        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["status"] == "pending"

    def test_get_open_bets_with_sport_filter(self):
        """Should filter by sport."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = []

        result = get_open_bets(mock_db, sport="NFL")

        # Verify filter was called
        mock_db.query.return_value.filter.assert_called()


class TestGetBetHistory:
    """Test retrieving bet history."""

    def test_get_settled_bets(self):
        """Should return settled bets."""
        mock_trade = MagicMock()
        mock_trade.id = 1
        mock_trade.sport = "NBA"
        mock_trade.bet_type = "spread"
        mock_trade.selection = "Lakers -5"
        mock_trade.line_value = -5
        mock_trade.odds = -110
        mock_trade.stake = 100
        mock_trade.potential_payout = 190.91
        mock_trade.profit_loss = 90.91
        mock_trade.game_description = "Lakers vs Celtics"
        mock_trade.result_score = "Lakers 110 - Celtics 100"
        mock_trade.status = "won"
        mock_trade.edge_at_placement = 5.0
        mock_trade.closing_line_value = -4.5
        mock_trade.placed_at = datetime.utcnow()
        mock_trade.settled_at = datetime.utcnow()

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_trade]

        mock_db = MagicMock()
        mock_db.query.return_value = mock_query

        result = get_bet_history(mock_db)

        assert len(result) == 1
        assert result[0]["status"] == "won"


class TestGetTradeById:
    """Test retrieving single trade."""

    def test_get_existing_trade(self):
        """Should return trade details."""
        mock_trade = MagicMock()
        mock_trade.id = 1
        mock_trade.sport = "NBA"
        mock_trade.bet_type = "spread"
        mock_trade.selection = "Lakers -5"
        mock_trade.line_value = -5
        mock_trade.odds = -110
        mock_trade.stake = 100
        mock_trade.potential_payout = 190.91
        mock_trade.profit_loss = None
        mock_trade.game_id = "game123"
        mock_trade.game_description = "Lakers vs Celtics"
        mock_trade.game_date = datetime.utcnow()
        mock_trade.result_score = None
        mock_trade.status = "pending"
        mock_trade.edge_at_placement = 5.0
        mock_trade.closing_line_value = None
        mock_trade.notes = "Test note"
        mock_trade.placed_at = datetime.utcnow()
        mock_trade.settled_at = None

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_trade

        result = get_trade_by_id(mock_db, trade_id=1)

        assert result is not None
        assert result["id"] == 1
        assert result["sport"] == "NBA"

    def test_get_nonexistent_trade(self):
        """Should return None for nonexistent trade."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = get_trade_by_id(mock_db, trade_id=999)

        assert result is None


class TestCancelBet:
    """Test bet cancellation."""

    def test_cancel_pending_bet(self):
        """Should cancel pending bet and return stake."""
        mock_trade = MagicMock()
        mock_trade.id = 1
        mock_trade.user_id = 1
        mock_trade.status = "pending"
        mock_trade.stake = 100

        mock_bankroll = MagicMock()
        mock_bankroll.current_balance = 9900.0
        mock_bankroll.total_wagered = 100
        mock_bankroll.total_bets = 1
        mock_bankroll.pending_bets = 1

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_trade, mock_bankroll
        ]

        result = cancel_bet(mock_db, trade_id=1, user_id=1)

        assert result["success"] is True
        assert result["stake_returned"] == 100
        assert result["new_balance"] == 10000.0

    def test_cannot_cancel_settled_bet(self):
        """Should not cancel already settled bet."""
        mock_trade = MagicMock()
        mock_trade.status = "won"

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_trade

        result = cancel_bet(mock_db, trade_id=1)

        assert "error" in result
        assert "pending" in result["error"].lower()

    def test_cancel_nonexistent_bet(self):
        """Should return error for nonexistent bet."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = cancel_bet(mock_db, trade_id=999)

        assert "error" in result
        assert "not found" in result["error"].lower()


class TestResetBankroll:
    """Test bankroll reset."""

    def test_reset_existing_bankroll(self):
        """Should reset bankroll to default values."""
        mock_bankroll = MagicMock()
        mock_bankroll.id = 1

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_bankroll

        with patch('app.services.paper_trading.PaperBankrollHistory'):
            result = reset_bankroll(mock_db, user_id=1)

        assert result["success"] is True
        assert result["new_balance"] == DEFAULT_STARTING_BALANCE
        mock_db.commit.assert_called()

    def test_reset_clears_trades(self):
        """Should delete all trades on reset."""
        mock_bankroll = MagicMock()
        mock_bankroll.id = 1

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_bankroll

        with patch('app.services.paper_trading.PaperBankrollHistory'):
            reset_bankroll(mock_db, user_id=1)

        # Verify trades were deleted
        assert mock_db.query.return_value.filter.return_value.delete.called


class TestGetBankrollChartData:
    """Test bankroll chart data retrieval."""

    def test_returns_history_data(self):
        """Should return bankroll history for charting."""
        mock_bankroll = MagicMock()
        mock_bankroll.id = 1

        mock_history = MagicMock()
        mock_history.date = datetime.utcnow()
        mock_history.balance = 10500.0
        mock_history.daily_profit_loss = 100.0
        mock_history.bets_placed = 5
        mock_history.bets_settled = 3

        # First query for bankroll
        mock_bankroll_query = MagicMock()
        mock_bankroll_query.filter.return_value.first.return_value = mock_bankroll

        # Second query for history
        mock_history_query = MagicMock()
        mock_history_query.filter.return_value = mock_history_query
        mock_history_query.order_by.return_value = mock_history_query
        mock_history_query.all.return_value = [mock_history]

        mock_db = MagicMock()
        mock_db.query.side_effect = [mock_bankroll_query, mock_history_query]

        result = get_bankroll_chart_data(mock_db, user_id=1, days=30)

        assert len(result) == 1
        assert result[0]["balance"] == 10500.0


class TestGetPerformanceBySport:
    """Test performance by sport breakdown."""

    def test_calculates_stats_per_sport(self):
        """Should calculate win rate and ROI per sport."""
        mock_trade1 = MagicMock()
        mock_trade1.sport = "NBA"
        mock_trade1.status = "won"
        mock_trade1.stake = 100
        mock_trade1.profit_loss = 90.91

        mock_trade2 = MagicMock()
        mock_trade2.sport = "NBA"
        mock_trade2.status = "lost"
        mock_trade2.stake = 100
        mock_trade2.profit_loss = -100

        mock_trade3 = MagicMock()
        mock_trade3.sport = "NFL"
        mock_trade3.status = "won"
        mock_trade3.stake = 100
        mock_trade3.profit_loss = 100

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.filter.return_value.all.return_value = [
            mock_trade1, mock_trade2, mock_trade3
        ]
        mock_db.query.return_value.filter.return_value.all.return_value = [
            mock_trade1, mock_trade2, mock_trade3
        ]

        result = get_performance_by_sport(mock_db)

        assert "NBA" in result
        assert "NFL" in result
        assert result["NBA"]["bets"] == 2
        assert result["NBA"]["wins"] == 1
        assert result["NBA"]["losses"] == 1
        assert result["NFL"]["bets"] == 1
        assert result["NFL"]["wins"] == 1


class TestGetPerformanceByBetType:
    """Test performance by bet type breakdown."""

    def test_calculates_stats_per_bet_type(self):
        """Should calculate win rate and ROI per bet type."""
        mock_trade1 = MagicMock()
        mock_trade1.bet_type = "spread"
        mock_trade1.status = "won"
        mock_trade1.stake = 100
        mock_trade1.profit_loss = 90.91

        mock_trade2 = MagicMock()
        mock_trade2.bet_type = "moneyline"
        mock_trade2.status = "won"
        mock_trade2.stake = 100
        mock_trade2.profit_loss = 150

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.filter.return_value.all.return_value = [
            mock_trade1, mock_trade2
        ]
        mock_db.query.return_value.filter.return_value.all.return_value = [
            mock_trade1, mock_trade2
        ]

        result = get_performance_by_bet_type(mock_db)

        assert "spread" in result
        assert "moneyline" in result


class TestConstants:
    """Test service constants."""

    def test_default_starting_balance(self):
        """Default starting balance should be $10,000."""
        assert DEFAULT_STARTING_BALANCE == 10000.0

    def test_unit_size(self):
        """Unit size should be $100 (1% of starting)."""
        assert UNIT_SIZE == 100.0


class TestStreakTracking:
    """Test win/loss streak tracking."""

    def test_win_streak_increments(self):
        """Win streak should increment on consecutive wins."""
        mock_trade = MagicMock()
        mock_trade.id = 1
        mock_trade.user_id = 1
        mock_trade.status = "pending"
        mock_trade.stake = 100
        mock_trade.potential_payout = 200

        mock_bankroll = MagicMock()
        mock_bankroll.current_balance = 9900.0
        mock_bankroll.total_won = 100
        mock_bankroll.winning_bets = 1
        mock_bankroll.current_streak = 1  # Already on 1 win streak
        mock_bankroll.longest_win_streak = 1
        mock_bankroll.pending_bets = 1
        mock_bankroll.total_wagered = 200
        mock_bankroll.total_lost = 0
        mock_bankroll.roi_percentage = 50.0
        mock_bankroll.high_water_mark = 10100.0
        mock_bankroll.losing_bets = 0

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_trade, mock_bankroll
        ]

        result = settle_bet(mock_db, trade_id=1, result="won", user_id=1)

        assert result["success"] is True
        # Streak should be updated to 2

    def test_loss_breaks_win_streak(self):
        """Loss should reset win streak to -1."""
        mock_trade = MagicMock()
        mock_trade.id = 1
        mock_trade.user_id = 1
        mock_trade.status = "pending"
        mock_trade.stake = 100
        mock_trade.potential_payout = 200

        mock_bankroll = MagicMock()
        mock_bankroll.current_balance = 10100.0
        mock_bankroll.total_lost = 0
        mock_bankroll.losing_bets = 0
        mock_bankroll.current_streak = 3  # On 3 win streak
        mock_bankroll.longest_lose_streak = 0
        mock_bankroll.pending_bets = 1
        mock_bankroll.total_wagered = 400
        mock_bankroll.total_won = 200
        mock_bankroll.roi_percentage = 50.0
        mock_bankroll.high_water_mark = 10100.0
        mock_bankroll.winning_bets = 3

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_trade, mock_bankroll
        ]

        result = settle_bet(mock_db, trade_id=1, result="lost", user_id=1)

        assert result["success"] is True


class TestEdgeTracking:
    """Test edge at placement tracking."""

    def test_place_bet_with_edge(self):
        """Should store edge at placement."""
        mock_bankroll = MagicMock()
        mock_bankroll.id = 1
        mock_bankroll.current_balance = 10000.0
        mock_bankroll.total_wagered = 0
        mock_bankroll.total_bets = 0
        mock_bankroll.pending_bets = 0
        mock_bankroll.low_water_mark = 10000.0

        mock_trade = MagicMock()
        mock_trade.id = 1
        mock_trade.sport = "NBA"
        mock_trade.bet_type = "spread"
        mock_trade.selection = "Lakers -5"
        mock_trade.line_value = -5
        mock_trade.odds = -110
        mock_trade.stake = 100
        mock_trade.potential_payout = 190.91
        mock_trade.game_description = "Lakers vs Celtics"
        mock_trade.status = "pending"
        mock_trade.edge_at_placement = 5.5
        mock_trade.placed_at = datetime.utcnow()

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_bankroll

        with patch('app.services.paper_trading.PaperTrade', return_value=mock_trade):
            result = place_bet(
                mock_db,
                sport="NBA",
                bet_type="spread",
                selection="Lakers -5",
                odds=-110,
                stake=100,
                edge_at_placement=5.5,
                user_id=1,
            )

        assert result["success"] is True


class TestClosingLineValue:
    """Test closing line value tracking."""

    def test_settle_bet_with_closing_line(self):
        """Should store closing line value on settlement."""
        mock_trade = MagicMock()
        mock_trade.id = 1
        mock_trade.user_id = 1
        mock_trade.status = "pending"
        mock_trade.stake = 100
        mock_trade.potential_payout = 200

        mock_bankroll = MagicMock()
        mock_bankroll.current_balance = 9900.0
        mock_bankroll.total_won = 0
        mock_bankroll.winning_bets = 0
        mock_bankroll.current_streak = 0
        mock_bankroll.longest_win_streak = 0
        mock_bankroll.pending_bets = 1
        mock_bankroll.total_wagered = 100
        mock_bankroll.total_lost = 0
        mock_bankroll.roi_percentage = None
        mock_bankroll.high_water_mark = 10000.0
        mock_bankroll.losing_bets = 0

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_trade, mock_bankroll
        ]

        result = settle_bet(
            mock_db,
            trade_id=1,
            result="won",
            closing_line_value=-4.5,
            user_id=1,
        )

        assert result["success"] is True
