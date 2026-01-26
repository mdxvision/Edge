"""
Tests for odds utility functions.
"""

import pytest
from app.utils.odds import (
    american_to_implied_probability,
    american_to_probability,
    american_to_decimal,
    decimal_to_american,
    implied_probability_to_american,
    calculate_payout,
    expected_value,
    edge,
    is_value_bet,
    kelly_criterion
)


class TestAmericanToImpliedProbability:
    """Test converting American odds to implied probability."""

    def test_favorite_minus_110(self):
        """Standard -110 favorite should be ~52.4%."""
        prob = american_to_implied_probability(-110)
        assert 0.52 < prob < 0.53

    def test_favorite_minus_200(self):
        """Heavy -200 favorite should be ~66.7%."""
        prob = american_to_implied_probability(-200)
        assert 0.66 < prob < 0.67

    def test_favorite_minus_300(self):
        """Very heavy -300 favorite should be 75%."""
        prob = american_to_implied_probability(-300)
        assert prob == 0.75

    def test_underdog_plus_110(self):
        """Standard +110 underdog should be ~47.6%."""
        prob = american_to_implied_probability(+110)
        assert 0.47 < prob < 0.48

    def test_underdog_plus_200(self):
        """Heavy +200 underdog should be ~33.3%."""
        prob = american_to_implied_probability(+200)
        assert 0.33 < prob < 0.34

    def test_underdog_plus_300(self):
        """Very heavy +300 underdog should be 25%."""
        prob = american_to_implied_probability(+300)
        assert prob == 0.25

    def test_even_money_plus_100(self):
        """+100 (even money) should be 50%."""
        prob = american_to_implied_probability(+100)
        assert prob == 0.5

    def test_even_money_minus_100(self):
        """-100 should also be 50%."""
        prob = american_to_implied_probability(-100)
        assert prob == 0.5


class TestAmericanToProbability:
    """Test that american_to_probability is an alias."""

    def test_is_alias(self):
        """Should return same result as american_to_implied_probability."""
        assert american_to_probability(-110) == american_to_implied_probability(-110)
        assert american_to_probability(+150) == american_to_implied_probability(+150)


class TestAmericanToDecimal:
    """Test converting American odds to decimal odds."""

    def test_minus_110(self):
        """-110 should be ~1.91."""
        decimal = american_to_decimal(-110)
        assert 1.90 < decimal < 1.92

    def test_plus_100(self):
        """+100 should be 2.0."""
        decimal = american_to_decimal(+100)
        assert decimal == 2.0

    def test_plus_200(self):
        """+200 should be 3.0."""
        decimal = american_to_decimal(+200)
        assert decimal == 3.0

    def test_minus_200(self):
        """-200 should be 1.5."""
        decimal = american_to_decimal(-200)
        assert decimal == 1.5

    def test_plus_500(self):
        """+500 should be 6.0."""
        decimal = american_to_decimal(+500)
        assert decimal == 6.0


class TestDecimalToAmerican:
    """Test converting decimal odds to American odds."""

    def test_decimal_2_0(self):
        """2.0 should be +100."""
        american = decimal_to_american(2.0)
        assert american == 100

    def test_decimal_3_0(self):
        """3.0 should be +200."""
        american = decimal_to_american(3.0)
        assert american == 200

    def test_decimal_1_5(self):
        """1.5 should be -200."""
        american = decimal_to_american(1.5)
        assert american == -200

    def test_decimal_1_91(self):
        """~1.91 should be around -110."""
        american = decimal_to_american(1.909)
        assert -115 < american < -105


class TestImpliedProbabilityToAmerican:
    """Test converting implied probability to American odds."""

    def test_50_percent(self):
        """50% should be +100 or -100."""
        american = implied_probability_to_american(0.5)
        assert american in [100, -100]

    def test_66_percent(self):
        """66.7% should be around -200."""
        american = implied_probability_to_american(0.667)
        assert -210 < american < -190

    def test_33_percent(self):
        """33.3% should be around +200."""
        american = implied_probability_to_american(0.333)
        assert 190 < american < 210

    def test_invalid_zero(self):
        """0% should raise ValueError."""
        with pytest.raises(ValueError):
            implied_probability_to_american(0)

    def test_invalid_one(self):
        """100% should raise ValueError."""
        with pytest.raises(ValueError):
            implied_probability_to_american(1)

    def test_invalid_negative(self):
        """Negative should raise ValueError."""
        with pytest.raises(ValueError):
            implied_probability_to_american(-0.1)


class TestCalculatePayout:
    """Test payout calculation."""

    def test_plus_100_payout(self):
        """+100 with $100 stake should win $100."""
        payout = calculate_payout(+100, 100)
        assert payout == 100

    def test_plus_200_payout(self):
        """+200 with $100 stake should win $200."""
        payout = calculate_payout(+200, 100)
        assert payout == 200

    def test_minus_110_payout(self):
        """-110 with $110 stake should win ~$100."""
        payout = calculate_payout(-110, 110)
        assert 99 < payout < 101

    def test_minus_200_payout(self):
        """-200 with $100 stake should win $50."""
        payout = calculate_payout(-200, 100)
        assert payout == 50

    def test_default_stake(self):
        """Default stake should be 1.0."""
        payout = calculate_payout(+100)
        assert payout == 1.0


class TestExpectedValue:
    """Test expected value calculation."""

    def test_ev_fair_bet(self):
        """Fair bet (50% at +100) should have EV of 0."""
        ev = expected_value(0.5, +100, 100)
        assert -1 < ev < 1  # Allow for floating point

    def test_ev_positive_edge(self):
        """55% chance at +100 should have positive EV."""
        ev = expected_value(0.55, +100, 100)
        assert ev > 0

    def test_ev_negative_edge(self):
        """45% chance at +100 should have negative EV."""
        ev = expected_value(0.45, +100, 100)
        assert ev < 0

    def test_ev_heavy_favorite(self):
        """True 75% at -300 is breakeven."""
        ev = expected_value(0.75, -300, 100)
        assert -5 < ev < 5  # Near breakeven


class TestEdge:
    """Test edge calculation."""

    def test_positive_edge(self):
        """Model 60% vs implied 50% = 10% edge."""
        e = edge(0.60, 0.50)
        assert abs(e - 0.10) < 0.0001

    def test_negative_edge(self):
        """Model 45% vs implied 50% = -5% edge."""
        e = edge(0.45, 0.50)
        assert abs(e - (-0.05)) < 0.0001

    def test_zero_edge(self):
        """Same probability = 0 edge."""
        e = edge(0.50, 0.50)
        assert e == 0.0


class TestIsValueBet:
    """Test value bet detection."""

    def test_value_bet_found(self):
        """55% model vs +100 odds should be value."""
        assert is_value_bet(0.55, +100, min_edge=0.03) is True

    def test_not_value_bet(self):
        """50% model vs +100 odds should not be value."""
        assert is_value_bet(0.50, +100, min_edge=0.03) is False

    def test_marginal_edge(self):
        """53% model vs +100 odds (3% edge) is value at 3% threshold."""
        assert is_value_bet(0.53, +100, min_edge=0.03) is True

    def test_below_threshold(self):
        """52% model vs +100 odds (2% edge) is not value at 3% threshold."""
        assert is_value_bet(0.52, +100, min_edge=0.03) is False


class TestKellyCriterion:
    """Test Kelly criterion stake sizing."""

    def test_no_edge_zero_kelly(self):
        """50% probability at +100 should return 0 or near-zero Kelly."""
        kelly = kelly_criterion(0.50, +100)
        assert kelly <= 0.01  # No edge, no bet

    def test_positive_edge_positive_kelly(self):
        """60% probability at +100 should return positive Kelly."""
        kelly = kelly_criterion(0.60, +100)
        assert kelly > 0

    def test_fractional_kelly(self):
        """Kelly should be reduced by fraction (default 0.25)."""
        full_kelly = kelly_criterion(0.60, +100, fraction=1.0)
        quarter_kelly = kelly_criterion(0.60, +100, fraction=0.25)
        assert abs(quarter_kelly - full_kelly * 0.25) < 0.001

    def test_negative_edge_zero_kelly(self):
        """Negative edge should return 0."""
        kelly = kelly_criterion(0.40, +100)
        assert kelly == 0.0

    def test_heavy_underdog_with_edge(self):
        """35% at +250 (implies 28.5%) should have positive Kelly."""
        kelly = kelly_criterion(0.35, +250)
        assert kelly > 0


class TestOddsConversionRoundTrip:
    """Test round-trip conversions maintain accuracy."""

    def test_american_decimal_roundtrip_positive(self):
        """Convert +150 to decimal and back."""
        original = +150
        decimal = american_to_decimal(original)
        converted = decimal_to_american(decimal)
        assert abs(converted - original) <= 1

    def test_american_decimal_roundtrip_negative(self):
        """Convert -150 to decimal and back."""
        original = -150
        decimal = american_to_decimal(original)
        converted = decimal_to_american(decimal)
        assert abs(converted - original) <= 1

    def test_probability_american_roundtrip(self):
        """Convert 0.6 to American and back to probability."""
        original = 0.6
        american = implied_probability_to_american(original)
        prob = american_to_implied_probability(american)
        assert abs(prob - original) < 0.02
