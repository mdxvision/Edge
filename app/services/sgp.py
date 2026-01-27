"""
Same Game Parlay (SGP) Builder Service

AI-assisted SGP construction with correlation analysis.
Identifies correlated legs within a single game to build
smarter same-game parlays.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from dataclasses import dataclass
from enum import Enum

from app.db import Game, Market, Line, Team
from app.utils.odds import american_to_probability, american_to_decimal
from app.utils.logging import get_logger

logger = get_logger(__name__)


class CorrelationType(str, Enum):
    """Types of leg correlations."""
    POSITIVE = "positive"  # Legs tend to win together
    NEGATIVE = "negative"  # Legs tend to oppose each other
    NEUTRAL = "neutral"    # Legs are independent


@dataclass
class SGPLeg:
    """Represents a single leg in an SGP."""
    market_type: str
    selection: str
    odds: int
    probability: float
    point: Optional[float] = None
    player_name: Optional[str] = None
    prop_type: Optional[str] = None


@dataclass
class CorrelationResult:
    """Result of correlation analysis between two legs."""
    leg1_desc: str
    leg2_desc: str
    correlation_type: CorrelationType
    correlation_factor: float  # 0.5-1.5, where 1.0 = independent
    reason: str


# Correlation factors for common SGP leg combinations
# < 1.0 = negative correlation (less likely to hit together)
# = 1.0 = independent
# > 1.0 = positive correlation (more likely to hit together)
CORRELATION_MATRIX = {
    # Team performance correlations
    ("moneyline_favorite", "over"): 1.15,  # Favorites winning often means more points
    ("moneyline_favorite", "under"): 0.85,
    ("moneyline_underdog", "over"): 0.90,
    ("moneyline_underdog", "under"): 1.10,
    ("spread_favorite", "over"): 1.10,
    ("spread_favorite", "under"): 0.90,
    ("spread_underdog", "over"): 0.95,
    ("spread_underdog", "under"): 1.05,

    # Same team correlations
    ("team_total_over", "team_spread_cover"): 1.20,  # Team scoring + covering
    ("team_total_under", "team_spread_cover"): 0.80,
    ("team_total_over", "team_moneyline"): 1.15,
    ("team_total_under", "team_moneyline"): 0.85,

    # Player prop correlations
    ("qb_passing_yards_over", "team_total_over"): 1.25,
    ("qb_passing_yards_under", "team_total_under"): 1.20,
    ("qb_passing_tds_over", "team_total_over"): 1.30,
    ("qb_passing_tds_under", "team_total_under"): 1.25,
    ("rb_rushing_yards_over", "team_moneyline"): 1.15,
    ("rb_rushing_yards_over", "spread_favorite"): 1.10,
    ("wr_receiving_yards_over", "team_total_over"): 1.20,
    ("player_points_over", "team_total_over"): 1.25,  # NBA
    ("player_rebounds_over", "game_total_over"): 1.05,
    ("player_assists_over", "team_total_over"): 1.15,

    # Negative correlations
    ("team1_moneyline", "team2_moneyline"): 0.0,  # Impossible
    ("over", "under"): 0.0,  # Impossible same market
    ("qb_interceptions_over", "team_moneyline"): 0.75,  # INTs hurt team
    ("qb_interceptions_over", "team_total_over"): 0.80,
}


def get_correlation_factor(leg1_type: str, leg2_type: str) -> Tuple[float, str]:
    """
    Get correlation factor between two leg types.

    Returns:
        Tuple of (factor, reason)
    """
    # Check direct match
    key = (leg1_type.lower(), leg2_type.lower())
    if key in CORRELATION_MATRIX:
        factor = CORRELATION_MATRIX[key]
        return factor, f"Known correlation: {leg1_type} + {leg2_type}"

    # Check reverse
    reverse_key = (leg2_type.lower(), leg1_type.lower())
    if reverse_key in CORRELATION_MATRIX:
        factor = CORRELATION_MATRIX[reverse_key]
        return factor, f"Known correlation: {leg2_type} + {leg1_type}"

    # Default: slight negative correlation for same-game bets
    # (sportsbooks build in correlation adjustment)
    return 0.95, "Default same-game correlation adjustment"


def classify_leg(leg: Dict[str, Any]) -> str:
    """Classify a leg for correlation lookup."""
    market_type = leg.get("market_type", "").lower()
    selection = leg.get("selection", "").lower()
    point = leg.get("point")

    # Moneyline
    if market_type == "h2h" or "moneyline" in market_type:
        if leg.get("is_favorite", False) or (leg.get("odds", 0) < 0):
            return "moneyline_favorite"
        return "moneyline_underdog"

    # Spread
    if market_type == "spreads" or "spread" in market_type:
        if point and point < 0:
            return "spread_favorite"
        return "spread_underdog"

    # Totals
    if market_type == "totals" or "total" in market_type:
        if "over" in selection:
            return "over"
        return "under"

    # Team totals
    if "team_total" in market_type or "team total" in selection:
        if "over" in selection:
            return "team_total_over"
        return "team_total_under"

    # Player props
    prop_type = leg.get("prop_type", "").lower()
    if prop_type or "player" in market_type:
        if "passing" in prop_type and "yard" in prop_type:
            return f"qb_passing_yards_{'over' if 'over' in selection else 'under'}"
        if "passing" in prop_type and "td" in prop_type:
            return f"qb_passing_tds_{'over' if 'over' in selection else 'under'}"
        if "rushing" in prop_type:
            return f"rb_rushing_yards_{'over' if 'over' in selection else 'under'}"
        if "receiving" in prop_type:
            return f"wr_receiving_yards_{'over' if 'over' in selection else 'under'}"
        if "points" in prop_type:
            return f"player_points_{'over' if 'over' in selection else 'under'}"
        if "rebound" in prop_type:
            return f"player_rebounds_{'over' if 'over' in selection else 'under'}"
        if "assist" in prop_type:
            return f"player_assists_{'over' if 'over' in selection else 'under'}"
        if "interception" in prop_type:
            return f"qb_interceptions_{'over' if 'over' in selection else 'under'}"

    return "unknown"


def analyze_sgp_correlations(legs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze correlations between all legs in an SGP.

    Returns detailed correlation analysis including:
    - Pairwise correlations
    - Overall correlation adjustment
    - Warnings for conflicting legs
    """
    if len(legs) < 2:
        return {
            "correlations": [],
            "overall_factor": 1.0,
            "warnings": [],
            "has_conflicts": False
        }

    correlations = []
    warnings = []
    has_conflicts = False
    overall_factor = 1.0

    # Analyze all pairs
    for i, leg1 in enumerate(legs):
        leg1_type = classify_leg(leg1)
        leg1_desc = leg1.get("selection", f"Leg {i+1}")

        for j, leg2 in enumerate(legs[i+1:], i+1):
            leg2_type = classify_leg(leg2)
            leg2_desc = leg2.get("selection", f"Leg {j+1}")

            factor, reason = get_correlation_factor(leg1_type, leg2_type)

            # Determine correlation type
            if factor == 0.0:
                corr_type = CorrelationType.NEGATIVE
                has_conflicts = True
                warnings.append(f"CONFLICT: '{leg1_desc}' and '{leg2_desc}' cannot both win")
            elif factor < 0.9:
                corr_type = CorrelationType.NEGATIVE
                warnings.append(f"Warning: '{leg1_desc}' negatively correlated with '{leg2_desc}'")
            elif factor > 1.1:
                corr_type = CorrelationType.POSITIVE
            else:
                corr_type = CorrelationType.NEUTRAL

            correlations.append({
                "leg1": leg1_desc,
                "leg2": leg2_desc,
                "leg1_type": leg1_type,
                "leg2_type": leg2_type,
                "correlation_type": corr_type.value,
                "factor": round(factor, 3),
                "reason": reason
            })

            # Apply to overall factor (geometric mean approach)
            if factor > 0:
                overall_factor *= factor ** 0.5  # Square root for averaging effect

    return {
        "correlations": correlations,
        "overall_factor": round(overall_factor, 4),
        "warnings": warnings,
        "has_conflicts": has_conflicts,
        "positive_correlations": len([c for c in correlations if c["correlation_type"] == "positive"]),
        "negative_correlations": len([c for c in correlations if c["correlation_type"] == "negative"])
    }


def calculate_sgp_odds(legs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate SGP combined odds with correlation adjustment.

    Sportsbooks typically reduce SGP payouts due to correlations.
    We calculate both raw and adjusted odds.
    """
    if not legs:
        return {"error": "No legs provided"}

    # Calculate raw combined odds (treating as independent)
    combined_decimal = 1.0
    combined_prob = 1.0

    for leg in legs:
        odds = leg.get("odds", -110)
        decimal_odds = american_to_decimal(odds)
        prob = leg.get("probability", american_to_probability(odds))

        combined_decimal *= decimal_odds
        combined_prob *= prob

    # Convert to American
    if combined_decimal >= 2.0:
        raw_american = int((combined_decimal - 1) * 100)
    else:
        raw_american = int(-100 / (combined_decimal - 1))

    # Get correlation adjustment
    correlation = analyze_sgp_correlations(legs)
    adj_factor = correlation["overall_factor"]

    # Adjust probability
    adjusted_prob = combined_prob * adj_factor
    adjusted_decimal = 1 / adjusted_prob if adjusted_prob > 0 else 999

    # Convert adjusted to American
    if adjusted_decimal >= 2.0:
        adjusted_american = int((adjusted_decimal - 1) * 100)
    else:
        adjusted_american = int(-100 / (adjusted_decimal - 1)) if adjusted_decimal > 1 else -10000

    return {
        "leg_count": len(legs),
        "raw_odds": {
            "american": raw_american,
            "decimal": round(combined_decimal, 2),
            "probability": round(combined_prob * 100, 2)
        },
        "correlation_adjusted": {
            "factor": adj_factor,
            "american": adjusted_american,
            "decimal": round(adjusted_decimal, 2),
            "probability": round(adjusted_prob * 100, 2)
        },
        "sportsbook_estimate": {
            # Sportsbooks typically use ~0.90 correlation factor
            "american": calculate_book_odds(legs, 0.90),
            "note": "Estimated sportsbook SGP odds (they reduce for correlation)"
        }
    }


def calculate_book_odds(legs: List[Dict[str, Any]], correlation_factor: float) -> int:
    """Estimate what sportsbook would offer for this SGP."""
    combined_prob = 1.0
    for leg in legs:
        odds = leg.get("odds", -110)
        prob = american_to_probability(odds)
        combined_prob *= prob

    # Apply book's correlation factor
    adjusted_prob = combined_prob * (correlation_factor ** len(legs))
    adjusted_decimal = 1 / adjusted_prob if adjusted_prob > 0 else 999

    if adjusted_decimal >= 2.0:
        return int((adjusted_decimal - 1) * 100)
    else:
        return int(-100 / (adjusted_decimal - 1)) if adjusted_decimal > 1 else -10000


def calculate_sgp_ev(
    legs: List[Dict[str, Any]],
    sportsbook_odds: Optional[int] = None
) -> Dict[str, Any]:
    """
    Calculate expected value of an SGP.

    Args:
        legs: List of leg dictionaries
        sportsbook_odds: Actual odds offered by sportsbook (if known)
    """
    correlation = analyze_sgp_correlations(legs)

    # Our estimated true probability
    true_prob = 1.0
    for leg in legs:
        prob = leg.get("probability", american_to_probability(leg.get("odds", -110)))
        true_prob *= prob

    true_prob *= correlation["overall_factor"]

    # If we have actual sportsbook odds, compare against those
    if sportsbook_odds:
        implied_prob = american_to_probability(sportsbook_odds)
        decimal_odds = american_to_decimal(sportsbook_odds)
    else:
        # Estimate sportsbook odds
        estimated = calculate_book_odds(legs, 0.90)
        implied_prob = american_to_probability(estimated)
        decimal_odds = american_to_decimal(estimated)
        sportsbook_odds = estimated

    # Calculate EV
    edge = true_prob - implied_prob
    ev_per_dollar = (true_prob * decimal_odds) - 1

    return {
        "sportsbook_odds": sportsbook_odds,
        "true_probability": round(true_prob * 100, 2),
        "implied_probability": round(implied_prob * 100, 2),
        "edge": round(edge * 100, 2),
        "ev_per_dollar": round(ev_per_dollar * 100, 2),
        "is_positive_ev": edge > 0,
        "recommendation": get_ev_recommendation(edge, len(legs))
    }


def get_ev_recommendation(edge: float, leg_count: int) -> str:
    """Get recommendation based on edge and leg count."""
    if edge < -0.05:
        return "Avoid - significant negative expected value"
    elif edge < 0:
        return "Not recommended - negative expected value"
    elif edge < 0.02:
        return "Marginal - small positive edge but high variance"
    elif edge < 0.05 and leg_count <= 3:
        return "Consider - decent edge with manageable legs"
    elif edge >= 0.05:
        return "Good value - strong positive edge"
    else:
        return "Proceed with caution - high variance"


def get_sgp_risk_score(legs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate risk score for an SGP.

    Higher score = higher risk.
    """
    base_risk = 0

    # Leg count risk
    leg_count = len(legs)
    if leg_count <= 2:
        base_risk += 10
    elif leg_count == 3:
        base_risk += 25
    elif leg_count == 4:
        base_risk += 40
    elif leg_count == 5:
        base_risk += 60
    else:
        base_risk += 80

    # Correlation risk
    correlation = analyze_sgp_correlations(legs)
    if correlation["has_conflicts"]:
        base_risk += 50

    negative_corr = correlation["negative_correlations"]
    base_risk += negative_corr * 10

    # Long shot legs
    for leg in legs:
        odds = leg.get("odds", -110)
        if odds > 200:  # Big underdog
            base_risk += 15
        elif odds > 150:
            base_risk += 10

    # Probability risk
    combined_prob = 1.0
    for leg in legs:
        prob = leg.get("probability", american_to_probability(leg.get("odds", -110)))
        combined_prob *= prob

    if combined_prob < 0.05:
        base_risk += 30
    elif combined_prob < 0.10:
        base_risk += 20
    elif combined_prob < 0.20:
        base_risk += 10

    # Cap at 100
    risk_score = min(100, base_risk)

    # Determine risk level
    if risk_score <= 25:
        level = "low"
    elif risk_score <= 50:
        level = "medium"
    elif risk_score <= 75:
        level = "high"
    else:
        level = "extreme"

    return {
        "score": risk_score,
        "level": level,
        "leg_count": leg_count,
        "combined_probability": round(combined_prob * 100, 2),
        "has_conflicts": correlation["has_conflicts"],
        "max_recommended_stake_pct": {
            "low": 3.0,
            "medium": 2.0,
            "high": 1.0,
            "extreme": 0.5
        }.get(level, 1.0)
    }


def suggest_sgp_legs(
    db: Session,
    game_id: int,
    strategy: str = "balanced"
) -> Dict[str, Any]:
    """
    Suggest SGP legs for a game based on strategy.

    Strategies:
    - balanced: Mix of favorites and reasonable odds
    - aggressive: Higher odds, more legs
    - conservative: Safer legs, higher probability
    - correlated: Positively correlated legs
    """
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        return {"error": "Game not found"}

    # Get all markets for the game
    markets = db.query(Market).filter(Market.game_id == game_id).all()
    if not markets:
        return {"error": "No markets found for game"}

    available_legs = []
    for market in markets:
        for line in market.lines:
            available_legs.append({
                "market_id": market.id,
                "market_type": market.market_type,
                "selection": market.selection,
                "odds": line.american_odds,
                "sportsbook": line.sportsbook,
                "probability": american_to_probability(line.american_odds)
            })

    if not available_legs:
        return {"error": "No lines available"}

    # Build suggestions based on strategy
    if strategy == "conservative":
        suggestions = build_conservative_sgp(available_legs)
    elif strategy == "aggressive":
        suggestions = build_aggressive_sgp(available_legs)
    elif strategy == "correlated":
        suggestions = build_correlated_sgp(available_legs)
    else:  # balanced
        suggestions = build_balanced_sgp(available_legs)

    return {
        "game_id": game_id,
        "home_team": game.home_team.name if game.home_team else "Unknown",
        "away_team": game.away_team.name if game.away_team else "Unknown",
        "strategy": strategy,
        "suggestions": suggestions
    }


def build_balanced_sgp(legs: List[Dict]) -> List[Dict]:
    """Build a balanced 2-3 leg SGP."""
    # Sort by probability (most likely first)
    sorted_legs = sorted(legs, key=lambda x: x["probability"], reverse=True)

    # Pick top favorite + 1-2 moderate legs
    selected = []

    # Get one favorite
    favorites = [l for l in sorted_legs if l["probability"] > 0.55]
    if favorites:
        selected.append(favorites[0])

    # Get one moderate
    moderates = [l for l in sorted_legs if 0.40 < l["probability"] < 0.55 and l not in selected]
    if moderates:
        selected.append(moderates[0])

    # Maybe one more
    others = [l for l in sorted_legs if l not in selected and l["probability"] > 0.35]
    if others and len(selected) < 3:
        selected.append(others[0])

    if len(selected) < 2:
        selected = sorted_legs[:2]

    analysis = analyze_sgp_correlations(selected)
    odds = calculate_sgp_odds(selected)

    return [{
        "name": "Balanced SGP",
        "legs": selected,
        "analysis": analysis,
        "odds": odds,
        "risk": get_sgp_risk_score(selected)
    }]


def build_conservative_sgp(legs: List[Dict]) -> List[Dict]:
    """Build a conservative 2-leg SGP with high probability."""
    sorted_legs = sorted(legs, key=lambda x: x["probability"], reverse=True)

    # Take top 2 most likely legs
    selected = sorted_legs[:2]

    analysis = analyze_sgp_correlations(selected)
    odds = calculate_sgp_odds(selected)

    return [{
        "name": "Conservative SGP",
        "legs": selected,
        "analysis": analysis,
        "odds": odds,
        "risk": get_sgp_risk_score(selected)
    }]


def build_aggressive_sgp(legs: List[Dict]) -> List[Dict]:
    """Build aggressive 4-5 leg SGP with bigger payout."""
    sorted_legs = sorted(legs, key=lambda x: x["probability"], reverse=True)

    # Mix of favorites and underdogs
    favorites = [l for l in sorted_legs if l["probability"] > 0.50][:2]
    underdogs = [l for l in sorted_legs if 0.30 < l["probability"] < 0.45][:2]

    selected = favorites + underdogs

    if len(selected) < 4:
        remaining = [l for l in sorted_legs if l not in selected]
        selected.extend(remaining[:4 - len(selected)])

    analysis = analyze_sgp_correlations(selected)
    odds = calculate_sgp_odds(selected)

    return [{
        "name": "Aggressive SGP",
        "legs": selected,
        "analysis": analysis,
        "odds": odds,
        "risk": get_sgp_risk_score(selected)
    }]


def build_correlated_sgp(legs: List[Dict]) -> List[Dict]:
    """Build SGP with positively correlated legs."""
    # Find pairs with positive correlation
    best_pairs = []

    for i, leg1 in enumerate(legs):
        leg1_type = classify_leg(leg1)
        for leg2 in legs[i+1:]:
            leg2_type = classify_leg(leg2)
            factor, _ = get_correlation_factor(leg1_type, leg2_type)
            if factor > 1.05:  # Positively correlated
                best_pairs.append({
                    "legs": [leg1, leg2],
                    "factor": factor
                })

    if not best_pairs:
        # Fall back to balanced
        return build_balanced_sgp(legs)

    # Sort by correlation factor
    best_pairs.sort(key=lambda x: x["factor"], reverse=True)
    selected = best_pairs[0]["legs"]

    analysis = analyze_sgp_correlations(selected)
    odds = calculate_sgp_odds(selected)

    return [{
        "name": "Correlated SGP",
        "legs": selected,
        "analysis": analysis,
        "odds": odds,
        "risk": get_sgp_risk_score(selected),
        "correlation_factor": best_pairs[0]["factor"]
    }]


def build_custom_sgp(
    legs: List[Dict[str, Any]],
    stake: Optional[float] = None,
    bankroll: Optional[float] = None
) -> Dict[str, Any]:
    """
    Build and analyze a custom SGP from provided legs.

    Returns full analysis including correlations, odds, EV, and risk.
    """
    if len(legs) < 2:
        return {"error": "SGP requires at least 2 legs"}

    if len(legs) > 10:
        return {"error": "Maximum 10 legs allowed"}

    correlation = analyze_sgp_correlations(legs)

    if correlation["has_conflicts"]:
        return {
            "error": "SGP contains conflicting legs that cannot both win",
            "conflicts": correlation["warnings"]
        }

    odds = calculate_sgp_odds(legs)
    ev = calculate_sgp_ev(legs)
    risk = get_sgp_risk_score(legs)

    # Calculate potential payout
    payout = None
    suggested_stake = None

    if stake:
        decimal = odds["correlation_adjusted"]["decimal"]
        payout = round(stake * decimal, 2)

    if bankroll and ev["edge"] > 0:
        # Kelly-based suggestion
        kelly = ev["edge"] / (odds["correlation_adjusted"]["decimal"] - 1)
        suggested_stake = round(min(bankroll * kelly * 0.25, bankroll * risk["max_recommended_stake_pct"] / 100), 2)

    return {
        "legs": [{
            "selection": leg.get("selection", "Unknown"),
            "market_type": leg.get("market_type", "Unknown"),
            "odds": leg.get("odds"),
            "probability": round(leg.get("probability", 0) * 100, 2) if leg.get("probability") else None
        } for leg in legs],
        "correlation_analysis": correlation,
        "odds": odds,
        "expected_value": ev,
        "risk_assessment": risk,
        "stake_info": {
            "stake": stake,
            "potential_payout": payout,
            "suggested_stake": suggested_stake,
            "bankroll": bankroll
        } if stake or bankroll else None
    }
