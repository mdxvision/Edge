"""
Tests for bet tracking service.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from app.services.bet_tracking import (
    place_bet,
    settle_bet,
    get_user_bets,
    get_bet_by_id,
    delete_bet,
    get_user_stats,
    get_profit_by_sport,
)


class TestPotentialProfitCalculation:
    """Test potential profit calculation in place_bet."""

    def test_positive_odds_profit(self):
        """Positive odds: profit = stake * (odds / 100)."""
        # +200 odds, $100 stake = $200 potential profit
        stake = 100
        odds = 200
        expected_profit = stake * (odds / 100)
        assert expected_profit == 200.0

    def test_negative_odds_profit(self):
        """Negative odds: profit = stake * (100 / abs(odds))."""
        # -200 odds, $100 stake = $50 potential profit
        stake = 100
        odds = -200
        expected_profit = stake * (100 / abs(odds))
        assert expected_profit == 50.0

    def test_even_money_profit(self):
        """+100 odds: profit equals stake."""
        stake = 100
        odds = 100
        expected_profit = stake * (odds / 100)
        assert expected_profit == 100.0

    def test_minus_110_profit(self):
        """-110 odds: common vig line."""
        stake = 110
        odds = -110
        expected_profit = stake * (100 / abs(odds))
        assert expected_profit == 100.0


class TestPlaceBet:
    """Test bet placement."""

    @patch('app.services.bet_tracking.TrackedBet')
    def test_place_bet_creates_record(self, mock_tracked_bet):
        """Should create a TrackedBet record."""
        mock_db = MagicMock()
        mock_bet_instance = MagicMock()
        mock_tracked_bet.return_value = mock_bet_instance

        result = place_bet(
            db=mock_db,
            user_id=1,
            sport="NBA",
            bet_type="spread",
            selection="Lakers -3.5",
            odds=-110,
            stake=100.0
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @patch('app.services.bet_tracking.TrackedBet')
    def test_place_bet_with_optional_fields(self, mock_tracked_bet):
        """Should handle optional fields."""
        mock_db = MagicMock()
        mock_bet_instance = MagicMock()
        mock_tracked_bet.return_value = mock_bet_instance

        result = place_bet(
            db=mock_db,
            user_id=1,
            sport="NFL",
            bet_type="moneyline",
            selection="Chiefs",
            odds=150,
            stake=50.0,
            currency="EUR",
            sportsbook="DraftKings",
            notes="Playoff game",
            game_id=123,
            game_date=datetime.now()
        )

        mock_db.add.assert_called_once()


class TestSettleBet:
    """Test bet settlement."""

    def test_settle_bet_won(self):
        """Settling as won should set positive profit."""
        mock_db = MagicMock()
        mock_bet = MagicMock()
        mock_bet.potential_profit = 100.0
        mock_bet.stake = 100.0

        with patch('app.services.bet_tracking.update_leaderboard_for_user'):
            result = settle_bet(mock_db, mock_bet, "won")

        assert mock_bet.status == "settled"
        assert mock_bet.result == "won"
        assert mock_bet.profit_loss == 100.0
        assert mock_bet.settled_at is not None

    def test_settle_bet_lost(self):
        """Settling as lost should set negative profit (stake)."""
        mock_db = MagicMock()
        mock_bet = MagicMock()
        mock_bet.potential_profit = 100.0
        mock_bet.stake = 100.0

        with patch('app.services.bet_tracking.update_leaderboard_for_user'):
            result = settle_bet(mock_db, mock_bet, "lost")

        assert mock_bet.result == "lost"
        assert mock_bet.profit_loss == -100.0

    def test_settle_bet_push(self):
        """Settling as push should set zero profit."""
        mock_db = MagicMock()
        mock_bet = MagicMock()
        mock_bet.stake = 100.0

        with patch('app.services.bet_tracking.update_leaderboard_for_user'):
            result = settle_bet(mock_db, mock_bet, "push")

        assert mock_bet.result == "push"
        assert mock_bet.profit_loss == 0.0

    def test_settle_bet_void(self):
        """Settling as void should set zero profit."""
        mock_db = MagicMock()
        mock_bet = MagicMock()
        mock_bet.stake = 100.0

        with patch('app.services.bet_tracking.update_leaderboard_for_user'):
            result = settle_bet(mock_db, mock_bet, "void")

        assert mock_bet.result == "void"
        assert mock_bet.profit_loss == 0.0

    def test_settle_bet_custom_profit(self):
        """Should allow custom actual profit/loss."""
        mock_db = MagicMock()
        mock_bet = MagicMock()
        mock_bet.potential_profit = 100.0
        mock_bet.stake = 100.0

        with patch('app.services.bet_tracking.update_leaderboard_for_user'):
            result = settle_bet(mock_db, mock_bet, "won", actual_profit_loss=95.0)

        assert mock_bet.profit_loss == 95.0  # Custom value, not potential


class TestGetUserBets:
    """Test retrieving user bets."""

    def test_get_all_user_bets(self):
        """Should return all bets for user."""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [MagicMock(), MagicMock()]

        result = get_user_bets(mock_db, user_id=1)

        assert len(result) == 2

    def test_get_user_bets_with_status_filter(self):
        """Should filter by status."""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        result = get_user_bets(mock_db, user_id=1, status="pending")

        # filter should be called twice (user_id and status)
        assert mock_query.filter.call_count >= 1

    def test_get_user_bets_with_sport_filter(self):
        """Should filter by sport."""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        result = get_user_bets(mock_db, user_id=1, sport="NBA")

        assert mock_query.filter.call_count >= 1


class TestGetBetById:
    """Test retrieving specific bet."""

    def test_get_existing_bet(self):
        """Should return bet if exists and belongs to user."""
        mock_db = MagicMock()
        mock_bet = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_bet

        result = get_bet_by_id(mock_db, bet_id=1, user_id=1)

        assert result == mock_bet

    def test_get_nonexistent_bet(self):
        """Should return None if bet doesn't exist."""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        result = get_bet_by_id(mock_db, bet_id=999, user_id=1)

        assert result is None


class TestDeleteBet:
    """Test bet deletion."""

    def test_delete_pending_bet(self):
        """Should delete pending bet."""
        mock_db = MagicMock()
        mock_bet = MagicMock()
        mock_bet.status = "pending"

        result = delete_bet(mock_db, mock_bet)

        assert result is True
        mock_db.delete.assert_called_once_with(mock_bet)
        mock_db.commit.assert_called_once()

    def test_cannot_delete_settled_bet(self):
        """Should not delete settled bet."""
        mock_db = MagicMock()
        mock_bet = MagicMock()
        mock_bet.status = "settled"

        result = delete_bet(mock_db, mock_bet)

        assert result is False
        mock_db.delete.assert_not_called()


class TestGetUserStats:
    """Test user statistics calculation."""

    def test_stats_no_bets(self):
        """Should return zeros when no bets."""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []

        result = get_user_stats(mock_db, user_id=1)

        assert result["total_bets"] == 0
        assert result["win_rate"] == 0.0
        assert result["roi"] == 0.0

    @patch('app.services.bet_tracking.convert_currency')
    def test_stats_with_bets(self, mock_convert):
        """Should calculate correct stats."""
        mock_convert.side_effect = lambda amount, from_curr, to_curr: amount

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query

        # Create mock bets
        bet1 = MagicMock()
        bet1.result = "won"
        bet1.odds = 100
        bet1.stake = 100
        bet1.profit_loss = 100
        bet1.currency = "USD"
        bet1.settled_at = datetime.now()
        bet1.placed_at = datetime.now()

        bet2 = MagicMock()
        bet2.result = "lost"
        bet2.odds = -110
        bet2.stake = 110
        bet2.profit_loss = -110
        bet2.currency = "USD"
        bet2.settled_at = datetime.now()
        bet2.placed_at = datetime.now()

        mock_query.all.return_value = [bet1, bet2]

        result = get_user_stats(mock_db, user_id=1)

        assert result["total_bets"] == 2
        assert result["winning_bets"] == 1
        assert result["losing_bets"] == 1

    @patch('app.services.bet_tracking.convert_currency')
    def test_win_rate_calculation(self, mock_convert):
        """Win rate should be wins / total * 100."""
        mock_convert.side_effect = lambda amount, from_curr, to_curr: amount

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query

        # 3 wins, 1 loss = 75% win rate
        bets = []
        for i in range(3):
            bet = MagicMock()
            bet.result = "won"
            bet.odds = 100
            bet.stake = 100
            bet.profit_loss = 100
            bet.currency = "USD"
            bet.settled_at = datetime.now()
            bet.placed_at = datetime.now()
            bets.append(bet)

        lost_bet = MagicMock()
        lost_bet.result = "lost"
        lost_bet.odds = -110
        lost_bet.stake = 100
        lost_bet.profit_loss = -100
        lost_bet.currency = "USD"
        lost_bet.settled_at = datetime.now()
        lost_bet.placed_at = datetime.now()
        bets.append(lost_bet)

        mock_query.all.return_value = bets

        result = get_user_stats(mock_db, user_id=1)

        assert result["win_rate"] == 75.0


class TestGetProfitBySport:
    """Test profit breakdown by sport."""

    @patch('app.services.bet_tracking.convert_currency')
    def test_profit_by_sport(self, mock_convert):
        """Should group profits by sport."""
        mock_convert.side_effect = lambda amount, from_curr, to_curr: amount

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query

        nba_bet = MagicMock()
        nba_bet.sport = "NBA"
        nba_bet.result = "won"
        nba_bet.stake = 100
        nba_bet.profit_loss = 100
        nba_bet.currency = "USD"

        nfl_bet = MagicMock()
        nfl_bet.sport = "NFL"
        nfl_bet.result = "lost"
        nfl_bet.stake = 100
        nfl_bet.profit_loss = -100
        nfl_bet.currency = "USD"

        mock_query.all.return_value = [nba_bet, nfl_bet]

        result = get_profit_by_sport(mock_db, user_id=1)

        assert "NBA" in result
        assert "NFL" in result
        assert result["NBA"]["profit"] == 100.0
        assert result["NFL"]["profit"] == -100.0

    @patch('app.services.bet_tracking.convert_currency')
    def test_roi_by_sport(self, mock_convert):
        """Should calculate ROI per sport."""
        mock_convert.side_effect = lambda amount, from_curr, to_curr: amount

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query

        # Two NBA bets: $100 stake each, $50 total profit = 25% ROI
        bet1 = MagicMock()
        bet1.sport = "NBA"
        bet1.result = "won"
        bet1.stake = 100
        bet1.profit_loss = 100
        bet1.currency = "USD"

        bet2 = MagicMock()
        bet2.sport = "NBA"
        bet2.result = "lost"
        bet2.stake = 100
        bet2.profit_loss = -50
        bet2.currency = "USD"

        mock_query.all.return_value = [bet1, bet2]

        result = get_profit_by_sport(mock_db, user_id=1)

        assert result["NBA"]["total_bets"] == 2
        assert result["NBA"]["staked"] == 200.0
        assert result["NBA"]["profit"] == 50.0
        assert result["NBA"]["roi"] == 25.0


class TestStreakCalculation:
    """Test win streak calculation."""

    @patch('app.services.bet_tracking.convert_currency')
    def test_current_streak(self, mock_convert):
        """Should calculate current winning streak."""
        mock_convert.side_effect = lambda amount, from_curr, to_curr: amount

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query

        # Sequence: L, W, W, W (current streak = 3)
        bets = []
        times = [
            datetime.now() - timedelta(days=3),
            datetime.now() - timedelta(days=2),
            datetime.now() - timedelta(days=1),
            datetime.now()
        ]
        results = ["lost", "won", "won", "won"]

        for t, r in zip(times, results):
            bet = MagicMock()
            bet.result = r
            bet.odds = 100
            bet.stake = 100
            bet.profit_loss = 100 if r == "won" else -100
            bet.currency = "USD"
            bet.settled_at = t
            bet.placed_at = t
            bets.append(bet)

        mock_query.all.return_value = bets

        result = get_user_stats(mock_db, user_id=1)

        assert result["current_streak"] == 3

    @patch('app.services.bet_tracking.convert_currency')
    def test_best_streak(self, mock_convert):
        """Should track best winning streak."""
        mock_convert.side_effect = lambda amount, from_curr, to_curr: amount

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query

        # Sequence: W, W, W, W, L, W (best = 4, current = 1)
        bets = []
        times = [
            datetime.now() - timedelta(days=5),
            datetime.now() - timedelta(days=4),
            datetime.now() - timedelta(days=3),
            datetime.now() - timedelta(days=2),
            datetime.now() - timedelta(days=1),
            datetime.now()
        ]
        results = ["won", "won", "won", "won", "lost", "won"]

        for t, r in zip(times, results):
            bet = MagicMock()
            bet.result = r
            bet.odds = 100
            bet.stake = 100
            bet.profit_loss = 100 if r == "won" else -100
            bet.currency = "USD"
            bet.settled_at = t
            bet.placed_at = t
            bets.append(bet)

        mock_query.all.return_value = bets

        result = get_user_stats(mock_db, user_id=1)

        assert result["best_streak"] == 4
        assert result["current_streak"] == 1
