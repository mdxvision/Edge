"""
Tests for arbitrage detection service.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from app.services.arbitrage import (
    american_to_decimal,
    american_to_implied_prob,
    calculate_arb_margin,
    calculate_stakes,
    calculate_guaranteed_profit,
    calculate_arb_stakes,
    ArbOpportunity,
)


class TestAmericanToDecimal:
    """Test American to decimal odds conversion."""

    def test_plus_100(self):
        """+100 should be 2.0 decimal."""
        assert american_to_decimal(100) == 2.0

    def test_plus_200(self):
        """+200 should be 3.0 decimal."""
        assert american_to_decimal(200) == 3.0

    def test_plus_150(self):
        """+150 should be 2.5 decimal."""
        assert american_to_decimal(150) == 2.5

    def test_minus_100(self):
        """-100 should be 2.0 decimal."""
        assert american_to_decimal(-100) == 2.0

    def test_minus_200(self):
        """-200 should be 1.5 decimal."""
        assert american_to_decimal(-200) == 1.5

    def test_minus_110(self):
        """-110 should be ~1.91 decimal."""
        result = american_to_decimal(-110)
        assert 1.90 < result < 1.92


class TestAmericanToImpliedProb:
    """Test American odds to implied probability conversion."""

    def test_plus_100(self):
        """+100 should be 50%."""
        assert american_to_implied_prob(100) == 0.5

    def test_minus_100(self):
        """-100 should be 50%."""
        assert american_to_implied_prob(-100) == 0.5

    def test_plus_200(self):
        """+200 should be ~33.3%."""
        result = american_to_implied_prob(200)
        assert abs(result - 0.333) < 0.01

    def test_minus_200(self):
        """-200 should be ~66.7%."""
        result = american_to_implied_prob(-200)
        assert abs(result - 0.667) < 0.01

    def test_plus_110(self):
        """+110 should be ~47.6%."""
        result = american_to_implied_prob(110)
        assert 0.47 < result < 0.48

    def test_minus_110(self):
        """-110 should be ~52.4%."""
        result = american_to_implied_prob(-110)
        assert 0.52 < result < 0.53


class TestCalculateArbMargin:
    """Test arbitrage margin calculation."""

    def test_no_arb_standard_vig(self):
        """Standard -110/-110 has positive margin (no arb)."""
        margin = calculate_arb_margin([-110, -110])
        # Both at -110 implies ~52.4% each = 104.8% total = 4.8% margin
        assert margin > 0
        assert 4 < margin < 5

    def test_no_arb_heavy_vig(self):
        """Heavy vig has larger positive margin."""
        margin = calculate_arb_margin([-120, -120])
        assert margin > 5

    def test_arb_exists(self):
        """Arbitrage exists when margin is negative."""
        # +110 on both sides creates arb
        margin = calculate_arb_margin([110, 110])
        # Both at +110 implies ~47.6% each = 95.2% total = -4.8% margin
        assert margin < 0

    def test_break_even(self):
        """Exactly +100/+100 should be break-even (0% margin)."""
        margin = calculate_arb_margin([100, 100])
        assert abs(margin) < 0.1

    def test_three_way_market(self):
        """Three-way market (soccer) margin calculation."""
        # Typical soccer odds
        margin = calculate_arb_margin([150, 300, 200])
        assert isinstance(margin, float)


class TestCalculateStakes:
    """Test optimal stake distribution calculation."""

    def test_equal_odds_equal_stakes(self):
        """+100/+100 should give equal stakes."""
        stakes = calculate_stakes([100, 100], 100)
        assert abs(stakes[0] - stakes[1]) < 0.01
        assert abs(stakes[0] - 50) < 0.01

    def test_total_equals_stake(self):
        """Total stakes should equal requested stake."""
        stakes = calculate_stakes([110, -110], 100)
        assert abs(sum(stakes) - 100) < 0.01

    def test_favorite_gets_more(self):
        """Favorite (negative odds) should get larger stake."""
        stakes = calculate_stakes([200, -200], 100)
        # -200 side needs more stake to balance payouts
        assert stakes[1] > stakes[0]

    def test_three_way_stakes(self):
        """Three-way market stakes should sum to total."""
        stakes = calculate_stakes([150, 300, 200], 100)
        assert len(stakes) == 3
        assert abs(sum(stakes) - 100) < 0.01

    def test_custom_total_stake(self):
        """Should scale to custom total stake."""
        stakes = calculate_stakes([100, 100], 1000)
        assert abs(sum(stakes) - 1000) < 0.01


class TestCalculateGuaranteedProfit:
    """Test guaranteed profit calculation."""

    def test_arb_profit_positive(self):
        """Arbitrage should yield positive profit."""
        odds_list = [110, 110]  # Arb exists
        stakes = calculate_stakes(odds_list, 100)
        profit = calculate_guaranteed_profit(odds_list, stakes)
        assert profit > 0

    def test_no_arb_profit_negative(self):
        """Non-arb should yield negative profit (vig)."""
        odds_list = [-110, -110]  # No arb
        stakes = calculate_stakes(odds_list, 100)
        profit = calculate_guaranteed_profit(odds_list, stakes)
        assert profit < 0

    def test_break_even(self):
        """+100/+100 should be approximately break-even."""
        odds_list = [100, 100]
        stakes = calculate_stakes(odds_list, 100)
        profit = calculate_guaranteed_profit(odds_list, stakes)
        assert abs(profit) < 0.01


class TestCalculateArbStakes:
    """Test the main arb stake calculator function."""

    def test_arb_detected(self):
        """Should detect valid arbitrage."""
        result = calculate_arb_stakes(110, 110, 100)
        assert result["is_arb"] is True
        assert result["profit"] > 0

    def test_no_arb_detected(self):
        """Should detect when no arb exists."""
        result = calculate_arb_stakes(-110, -110, 100)
        assert result["is_arb"] is False
        assert "message" in result

    def test_returns_stakes(self):
        """Should return stake amounts."""
        result = calculate_arb_stakes(110, 110, 100)
        assert "stakes" in result
        assert len(result["stakes"]) == 2
        assert abs(sum(result["stakes"]) - 100) < 0.1

    def test_returns_payout(self):
        """Should return guaranteed payout."""
        result = calculate_arb_stakes(110, 110, 100)
        assert "guaranteed_payout" in result
        assert result["guaranteed_payout"] > 100  # More than stake

    def test_returns_roi(self):
        """Should return ROI percentage."""
        result = calculate_arb_stakes(110, 110, 100)
        assert "roi_percent" in result
        assert result["roi_percent"] > 0

    def test_three_way_arb(self):
        """Should handle three-way markets."""
        # Create odds that might have arb
        result = calculate_arb_stakes(150, 300, 100, odds3=200)
        assert "is_arb" in result

    def test_custom_stake_amount(self):
        """Should work with custom stake amounts."""
        result = calculate_arb_stakes(110, 110, 1000)
        if result["is_arb"]:
            assert result["total_stake"] == 1000


class TestArbOpportunity:
    """Test ArbOpportunity dataclass."""

    def test_create_two_way(self):
        """Should create two-way arb opportunity."""
        arb = ArbOpportunity(
            game_id=1,
            sport="NBA",
            home_team="Lakers",
            away_team="Celtics",
            market_type="h2h",
            start_time=datetime.now(),
            profit_margin=2.5,
            bet1_selection="home",
            bet1_sportsbook="DraftKings",
            bet1_odds=110,
            bet1_stake_pct=48.5,
            bet2_selection="away",
            bet2_sportsbook="FanDuel",
            bet2_odds=115,
            bet2_stake_pct=51.5,
        )
        assert arb.game_id == 1
        assert arb.profit_margin == 2.5
        assert arb.bet3_selection is None

    def test_create_three_way(self):
        """Should create three-way arb opportunity (soccer)."""
        arb = ArbOpportunity(
            game_id=2,
            sport="Soccer",
            home_team="Liverpool",
            away_team="Chelsea",
            market_type="h2h",
            start_time=datetime.now(),
            profit_margin=1.8,
            bet1_selection="home",
            bet1_sportsbook="Bet365",
            bet1_odds=150,
            bet1_stake_pct=35.0,
            bet2_selection="away",
            bet2_sportsbook="Betway",
            bet2_odds=200,
            bet2_stake_pct=30.0,
            bet3_selection="draw",
            bet3_sportsbook="Pinnacle",
            bet3_odds=250,
            bet3_stake_pct=35.0,
        )
        assert arb.bet3_selection == "draw"
        assert arb.bet3_odds == 250


class TestArbMathConsistency:
    """Test mathematical consistency of arbitrage calculations."""

    def test_payout_equality(self):
        """All outcomes should yield same payout in true arb."""
        odds_list = [110, 110]
        stakes = calculate_stakes(odds_list, 100)
        decimal_odds = [american_to_decimal(o) for o in odds_list]

        payout1 = stakes[0] * decimal_odds[0]
        payout2 = stakes[1] * decimal_odds[1]

        # Payouts should be equal (or very close)
        assert abs(payout1 - payout2) < 0.01

    def test_margin_matches_profit(self):
        """Margin should approximately match profit percentage."""
        odds_list = [110, 110]
        margin = calculate_arb_margin(odds_list)
        stakes = calculate_stakes(odds_list, 100)
        profit = calculate_guaranteed_profit(odds_list, stakes)

        # Profit percentage should be close to negative margin
        profit_pct = profit  # Already as percentage of 100
        assert abs(profit_pct - (-margin)) < 0.5

    def test_implied_probs_sum(self):
        """Implied probabilities should sum to margin + 100%."""
        odds_list = [-110, -110]
        margin = calculate_arb_margin(odds_list)

        implied_sum = sum(american_to_implied_prob(o) for o in odds_list)
        expected_sum = (margin / 100) + 1

        assert abs(implied_sum - expected_sum) < 0.001
