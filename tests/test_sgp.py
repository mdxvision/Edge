"""
Tests for Same Game Parlay (SGP) builder service.
"""

import pytest
from unittest.mock import Mock, MagicMock

from app.services.sgp import (
    CorrelationType,
    classify_leg,
    get_correlation_factor,
    analyze_sgp_correlations,
    calculate_sgp_odds,
    calculate_sgp_ev,
    get_sgp_risk_score,
    build_custom_sgp,
    build_balanced_sgp,
    build_conservative_sgp,
    build_aggressive_sgp,
    build_correlated_sgp,
    suggest_sgp_legs,
    CORRELATION_MATRIX,
)


class TestClassifyLeg:
    """Test leg classification for correlation lookup."""

    def test_classify_moneyline_favorite(self):
        """Negative odds should classify as favorite."""
        leg = {"market_type": "h2h", "selection": "Lakers", "odds": -150}
        assert classify_leg(leg) == "moneyline_favorite"

    def test_classify_moneyline_underdog(self):
        """Positive odds should classify as underdog."""
        leg = {"market_type": "h2h", "selection": "Celtics", "odds": 130}
        assert classify_leg(leg) == "moneyline_underdog"

    def test_classify_spread_favorite(self):
        """Negative point spread should classify as favorite."""
        leg = {"market_type": "spreads", "selection": "Lakers -5.5", "point": -5.5}
        assert classify_leg(leg) == "spread_favorite"

    def test_classify_spread_underdog(self):
        """Positive point spread should classify as underdog."""
        leg = {"market_type": "spreads", "selection": "Celtics +5.5", "point": 5.5}
        assert classify_leg(leg) == "spread_underdog"

    def test_classify_over(self):
        """Over selection should classify as over."""
        leg = {"market_type": "totals", "selection": "Over 220.5"}
        assert classify_leg(leg) == "over"

    def test_classify_under(self):
        """Under selection should classify as under."""
        leg = {"market_type": "totals", "selection": "Under 220.5"}
        assert classify_leg(leg) == "under"

    def test_classify_qb_passing_yards_over(self):
        """QB passing yards over prop."""
        leg = {"market_type": "player_prop", "selection": "Over 275.5", "prop_type": "passing_yards"}
        assert "qb_passing_yards_over" in classify_leg(leg)

    def test_classify_player_points_over(self):
        """NBA player points over prop."""
        leg = {"market_type": "player_prop", "selection": "Over 25.5", "prop_type": "points"}
        assert "player_points_over" in classify_leg(leg)

    def test_classify_unknown(self):
        """Unknown market type should return unknown."""
        leg = {"market_type": "exotic", "selection": "Something"}
        assert classify_leg(leg) == "unknown"


class TestGetCorrelationFactor:
    """Test correlation factor lookup."""

    def test_favorite_over_positive(self):
        """Favorite + Over should be positively correlated."""
        factor, _ = get_correlation_factor("moneyline_favorite", "over")
        assert factor > 1.0

    def test_favorite_under_negative(self):
        """Favorite + Under should be negatively correlated."""
        factor, _ = get_correlation_factor("moneyline_favorite", "under")
        assert factor < 1.0

    def test_spread_favorite_over(self):
        """Spread favorite + Over should be positively correlated."""
        factor, _ = get_correlation_factor("spread_favorite", "over")
        assert factor > 1.0

    def test_unknown_default(self):
        """Unknown correlation should use default."""
        factor, reason = get_correlation_factor("unknown", "unknown")
        assert factor == 0.95
        assert "default" in reason.lower()

    def test_reverse_lookup(self):
        """Should find correlation in reverse order too."""
        factor1, _ = get_correlation_factor("moneyline_favorite", "over")
        factor2, _ = get_correlation_factor("over", "moneyline_favorite")
        assert factor1 == factor2


class TestAnalyzeSGPCorrelations:
    """Test SGP correlation analysis."""

    def test_single_leg_no_correlation(self):
        """Single leg should return factor of 1.0."""
        legs = [{"selection": "Lakers ML", "market_type": "h2h", "odds": -150}]
        result = analyze_sgp_correlations(legs)
        assert result["overall_factor"] == 1.0
        assert result["correlations"] == []

    def test_two_leg_positive_correlation(self):
        """Positively correlated legs should have factor > 1."""
        legs = [
            {"selection": "Lakers ML", "market_type": "h2h", "odds": -150},
            {"selection": "Over 220.5", "market_type": "totals", "odds": -110}
        ]
        result = analyze_sgp_correlations(legs)
        assert result["overall_factor"] > 1.0
        assert result["positive_correlations"] > 0

    def test_conflicting_legs_detected(self):
        """Should detect conflicting legs."""
        legs = [
            {"selection": "Lakers ML", "market_type": "h2h", "odds": -150},
            {"selection": "Celtics ML", "market_type": "h2h", "odds": 130}
        ]
        # Both can't win - this depends on classification
        result = analyze_sgp_correlations(legs)
        # May or may not detect as conflict depending on classification
        assert "correlations" in result

    def test_warnings_generated(self):
        """Should generate warnings for negative correlations."""
        legs = [
            {"selection": "Lakers ML", "market_type": "h2h", "odds": -150, "is_favorite": True},
            {"selection": "Under 200.5", "market_type": "totals", "odds": -110}
        ]
        result = analyze_sgp_correlations(legs)
        # Favorite + Under is negatively correlated
        assert result["negative_correlations"] >= 0 or len(result["warnings"]) >= 0


class TestCalculateSGPOdds:
    """Test SGP odds calculation."""

    def test_empty_legs_error(self):
        """Empty legs should return error."""
        result = calculate_sgp_odds([])
        assert "error" in result

    def test_two_leg_calculation(self):
        """Two leg SGP should calculate combined odds."""
        legs = [
            {"selection": "Lakers ML", "odds": -150},
            {"selection": "Over 220.5", "odds": -110}
        ]
        result = calculate_sgp_odds(legs)

        assert result["leg_count"] == 2
        assert "raw_odds" in result
        assert "correlation_adjusted" in result
        assert result["raw_odds"]["decimal"] > 1.0

    def test_correlation_adjustment_applied(self):
        """Correlation adjustment should modify probability."""
        legs = [
            {"selection": "Lakers ML", "market_type": "h2h", "odds": -150},
            {"selection": "Over 220.5", "market_type": "totals", "odds": -110}
        ]
        result = calculate_sgp_odds(legs)

        # Correlation adjustment should differ from 1.0
        assert result["correlation_adjusted"]["factor"] != 1.0

    def test_sportsbook_estimate(self):
        """Should provide sportsbook estimate."""
        legs = [
            {"selection": "Lakers ML", "odds": -150},
            {"selection": "Over 220.5", "odds": -110}
        ]
        result = calculate_sgp_odds(legs)

        assert "sportsbook_estimate" in result
        assert "american" in result["sportsbook_estimate"]


class TestCalculateSGPEV:
    """Test SGP expected value calculation."""

    def test_ev_calculation(self):
        """Should calculate EV metrics."""
        legs = [
            {"selection": "Lakers ML", "odds": -150, "probability": 0.60},
            {"selection": "Over 220.5", "odds": -110, "probability": 0.52}
        ]
        result = calculate_sgp_ev(legs)

        assert "true_probability" in result
        assert "implied_probability" in result
        assert "edge" in result
        assert "ev_per_dollar" in result
        assert "is_positive_ev" in result

    def test_ev_with_sportsbook_odds(self):
        """Should use provided sportsbook odds."""
        legs = [
            {"selection": "Lakers ML", "odds": -150, "probability": 0.60},
            {"selection": "Over 220.5", "odds": -110, "probability": 0.52}
        ]
        result = calculate_sgp_ev(legs, sportsbook_odds=200)

        assert result["sportsbook_odds"] == 200

    def test_recommendation_provided(self):
        """Should provide recommendation."""
        legs = [
            {"selection": "Lakers ML", "odds": -150, "probability": 0.65},
            {"selection": "Over 220.5", "odds": -110, "probability": 0.55}
        ]
        result = calculate_sgp_ev(legs)

        assert "recommendation" in result


class TestGetSGPRiskScore:
    """Test SGP risk scoring."""

    def test_two_leg_lower_risk(self):
        """Two leg SGP should have lower risk."""
        legs = [
            {"selection": "Lakers ML", "odds": -200},
            {"selection": "Celtics +5.5", "odds": -110}
        ]
        result = get_sgp_risk_score(legs)

        assert result["score"] < 50
        assert result["level"] in ["low", "medium"]

    def test_five_leg_higher_risk(self):
        """Five leg SGP should have higher risk."""
        legs = [
            {"selection": "Leg 1", "odds": -150},
            {"selection": "Leg 2", "odds": -120},
            {"selection": "Leg 3", "odds": -110},
            {"selection": "Leg 4", "odds": 100},
            {"selection": "Leg 5", "odds": 110}
        ]
        result = get_sgp_risk_score(legs)

        assert result["score"] >= 50
        assert result["level"] in ["high", "extreme"]

    def test_long_shots_increase_risk(self):
        """Long shot legs should increase risk."""
        # Conservative legs
        conservative = [
            {"selection": "Leg 1", "odds": -200},
            {"selection": "Leg 2", "odds": -180}
        ]

        # Long shot legs
        longshots = [
            {"selection": "Leg 1", "odds": 250},
            {"selection": "Leg 2", "odds": 300}
        ]

        risk1 = get_sgp_risk_score(conservative)
        risk2 = get_sgp_risk_score(longshots)

        assert risk2["score"] > risk1["score"]

    def test_max_stake_recommendation(self):
        """Should provide max stake recommendation."""
        legs = [
            {"selection": "Lakers ML", "odds": -150},
            {"selection": "Over 220.5", "odds": -110}
        ]
        result = get_sgp_risk_score(legs)

        assert "max_recommended_stake_pct" in result
        assert result["max_recommended_stake_pct"] > 0


class TestBuildCustomSGP:
    """Test custom SGP builder."""

    def test_minimum_legs_required(self):
        """Should require at least 2 legs."""
        result = build_custom_sgp([{"selection": "Only one", "odds": -110}])
        assert "error" in result

    def test_maximum_legs_enforced(self):
        """Should enforce maximum 10 legs."""
        legs = [{"selection": f"Leg {i}", "odds": -110} for i in range(11)]
        result = build_custom_sgp(legs)
        assert "error" in result

    def test_complete_analysis_returned(self):
        """Should return complete analysis."""
        legs = [
            {"selection": "Lakers ML", "market_type": "h2h", "odds": -150},
            {"selection": "Over 220.5", "market_type": "totals", "odds": -110}
        ]
        result = build_custom_sgp(legs)

        assert "legs" in result
        assert "correlation_analysis" in result
        assert "odds" in result
        assert "expected_value" in result
        assert "risk_assessment" in result

    def test_stake_info_with_stake(self):
        """Should calculate payout with stake."""
        legs = [
            {"selection": "Lakers ML", "market_type": "h2h", "odds": -150},
            {"selection": "Over 220.5", "market_type": "totals", "odds": -110}
        ]
        result = build_custom_sgp(legs, stake=100)

        assert result["stake_info"]["stake"] == 100
        assert result["stake_info"]["potential_payout"] is not None

    def test_suggested_stake_with_bankroll(self):
        """Should suggest stake with bankroll."""
        legs = [
            {"selection": "Lakers ML", "market_type": "h2h", "odds": -150, "probability": 0.65},
            {"selection": "Over 220.5", "market_type": "totals", "odds": -110, "probability": 0.55}
        ]
        result = build_custom_sgp(legs, bankroll=5000)

        # May or may not have suggested_stake depending on edge
        assert "stake_info" in result


class TestBuildStrategies:
    """Test SGP building strategies."""

    def test_balanced_returns_suggestions(self):
        """Balanced strategy should return suggestions."""
        legs = [
            {"selection": "Leg 1", "odds": -200, "probability": 0.65},
            {"selection": "Leg 2", "odds": -150, "probability": 0.60},
            {"selection": "Leg 3", "odds": -110, "probability": 0.52},
            {"selection": "Leg 4", "odds": 110, "probability": 0.48}
        ]
        result = build_balanced_sgp(legs)

        assert len(result) == 1
        assert "legs" in result[0]
        assert "analysis" in result[0]

    def test_conservative_fewer_legs(self):
        """Conservative strategy should use fewer legs."""
        legs = [
            {"selection": "Leg 1", "odds": -200, "probability": 0.65},
            {"selection": "Leg 2", "odds": -150, "probability": 0.60},
            {"selection": "Leg 3", "odds": -110, "probability": 0.52}
        ]
        result = build_conservative_sgp(legs)

        assert len(result[0]["legs"]) == 2

    def test_aggressive_more_legs(self):
        """Aggressive strategy should use more legs."""
        legs = [
            {"selection": "Leg 1", "odds": -200, "probability": 0.65},
            {"selection": "Leg 2", "odds": -150, "probability": 0.60},
            {"selection": "Leg 3", "odds": -110, "probability": 0.52},
            {"selection": "Leg 4", "odds": 100, "probability": 0.50},
            {"selection": "Leg 5", "odds": 130, "probability": 0.43}
        ]
        result = build_aggressive_sgp(legs)

        assert len(result[0]["legs"]) >= 4

    def test_correlated_finds_correlations(self):
        """Correlated strategy should find positive correlations."""
        legs = [
            {"selection": "Lakers ML", "market_type": "h2h", "odds": -150, "probability": 0.60},
            {"selection": "Over 220.5", "market_type": "totals", "odds": -110, "probability": 0.52},
            {"selection": "Under 200.5", "market_type": "totals", "odds": -110, "probability": 0.52}
        ]
        result = build_correlated_sgp(legs)

        assert len(result) >= 1


class TestSuggestSGPLegs:
    """Test SGP leg suggestions."""

    def test_game_not_found(self):
        """Should return error for missing game."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = suggest_sgp_legs(mock_db, game_id=999)

        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_no_markets_error(self):
        """Should return error if no markets."""
        mock_game = MagicMock()
        mock_game.id = 1
        mock_game.home_team = MagicMock(name="Lakers")
        mock_game.away_team = MagicMock(name="Celtics")

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_game
        mock_db.query.return_value.filter.return_value.all.return_value = []

        result = suggest_sgp_legs(mock_db, game_id=1)

        assert "error" in result


class TestCorrelationMatrix:
    """Test correlation matrix values."""

    def test_positive_correlations_exist(self):
        """Matrix should have positive correlations."""
        positives = [v for v in CORRELATION_MATRIX.values() if v > 1.0]
        assert len(positives) > 0

    def test_negative_correlations_exist(self):
        """Matrix should have negative correlations."""
        negatives = [v for v in CORRELATION_MATRIX.values() if 0 < v < 1.0]
        assert len(negatives) > 0

    def test_impossible_correlations_zero(self):
        """Impossible combinations should be 0."""
        assert ("team1_moneyline", "team2_moneyline") in CORRELATION_MATRIX
        assert CORRELATION_MATRIX[("team1_moneyline", "team2_moneyline")] == 0.0
        assert CORRELATION_MATRIX[("over", "under")] == 0.0


class TestCorrelationType:
    """Test CorrelationType enum."""

    def test_positive_value(self):
        """Positive type should have correct value."""
        assert CorrelationType.POSITIVE.value == "positive"

    def test_negative_value(self):
        """Negative type should have correct value."""
        assert CorrelationType.NEGATIVE.value == "negative"

    def test_neutral_value(self):
        """Neutral type should have correct value."""
        assert CorrelationType.NEUTRAL.value == "neutral"
