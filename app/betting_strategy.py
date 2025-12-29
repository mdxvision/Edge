"""
Betting Strategy Configuration

Based on performance analysis:
- Favorites: 5-14 (26%) → -10.62u
- Underdogs: 1-1 (50%) → +0.00u
- Large spreads (>7): 0-3 (0%)
- Small spreads (≤4): 3-3 (50%)

Key learnings:
1. Stop betting large spreads - they don't cover
2. Avoid heavy ML favorites - they lose outright too often
3. Focus on small spreads and plus-money dogs
"""

from dataclasses import dataclass
from typing import Optional, Dict, List


@dataclass
class SportStrategy:
    """Strategy configuration for a specific sport."""

    # Spread limits
    max_spread: float = 6.0          # Don't bet spreads larger than this
    min_spread: float = 0.0          # Minimum spread (0 = allow pick'em)

    # Odds limits
    max_favorite_odds: int = -150    # Don't bet favorites juicier than this
    min_underdog_odds: int = 100     # Minimum underdog odds to consider
    max_underdog_odds: int = 250     # Maximum underdog odds (avoid long shots)

    # Unit sizing
    favorite_max_units: float = 1.0  # Max units on favorites
    underdog_max_units: float = 1.5  # Max units on underdogs (better value)
    small_spread_max_units: float = 1.5  # Small spreads get more units
    large_spread_max_units: float = 0.5  # Large spreads get fewer units

    # Confidence thresholds
    min_confidence: float = 0.52     # Minimum model confidence
    favorite_min_confidence: float = 0.58  # Higher bar for favorites

    # Edge requirements
    min_edge: float = 0.03           # 3% minimum edge
    favorite_min_edge: float = 0.05  # 5% min edge for favorites (higher bar)


# Sport-specific strategies based on our performance data
SPORT_STRATEGIES: Dict[str, SportStrategy] = {
    "NBA": SportStrategy(
        max_spread=6.0,              # No spreads > 6 (0-3 on large spreads)
        max_favorite_odds=-150,      # No heavy chalk (Celtics -250 lost)
        min_underdog_odds=100,
        max_underdog_odds=200,
        favorite_max_units=0.75,     # Reduce exposure on favorites
        underdog_max_units=1.5,      # Underdogs 1-1, give more action
        small_spread_max_units=1.5,  # Small spreads are 3-3
        large_spread_max_units=0.0,  # NO large spreads
        min_confidence=0.52,
        favorite_min_confidence=0.60,
        min_edge=0.03,
        favorite_min_edge=0.06,      # Need bigger edge on favorites
    ),
    "NFL": SportStrategy(
        max_spread=7.0,              # NFL spreads can be larger
        max_favorite_odds=-175,
        min_underdog_odds=100,
        max_underdog_odds=200,
        favorite_max_units=1.0,
        underdog_max_units=1.5,
        small_spread_max_units=1.5,
        large_spread_max_units=0.75,
        min_confidence=0.52,
        favorite_min_confidence=0.58,
        min_edge=0.03,
        favorite_min_edge=0.05,
    ),
    "DEFAULT": SportStrategy(
        max_spread=6.0,
        max_favorite_odds=-150,
        min_underdog_odds=100,
        max_underdog_odds=200,
        favorite_max_units=1.0,
        underdog_max_units=1.5,
        small_spread_max_units=1.5,
        large_spread_max_units=0.5,
        min_confidence=0.52,
        favorite_min_confidence=0.58,
        min_edge=0.03,
        favorite_min_edge=0.05,
    ),
}


def get_strategy(sport: str) -> SportStrategy:
    """Get the betting strategy for a sport."""
    return SPORT_STRATEGIES.get(sport, SPORT_STRATEGIES["DEFAULT"])


def filter_pick(
    sport: str,
    odds: int,
    spread: Optional[float],
    pick_type: str,
    confidence: float,
    edge: float
) -> Dict:
    """
    Filter a pick based on strategy rules.

    Returns:
        Dict with 'allowed' bool and 'reason' if rejected,
        plus 'recommended_units' if allowed.
    """
    strategy = get_strategy(sport)

    is_favorite = odds < 0
    is_spread_bet = pick_type.lower() == "spread"
    spread_size = abs(spread) if spread else 0

    # Check spread limits
    if is_spread_bet and spread_size > strategy.max_spread:
        return {
            "allowed": False,
            "reason": f"Spread {spread_size} exceeds max {strategy.max_spread}"
        }

    # Check favorite odds limits
    if is_favorite and odds < strategy.max_favorite_odds:
        return {
            "allowed": False,
            "reason": f"Favorite odds {odds} too juicy (limit: {strategy.max_favorite_odds})"
        }

    # Check underdog limits
    if not is_favorite:
        if odds < strategy.min_underdog_odds:
            return {
                "allowed": False,
                "reason": f"Underdog odds {odds} below minimum {strategy.min_underdog_odds}"
            }
        if odds > strategy.max_underdog_odds:
            return {
                "allowed": False,
                "reason": f"Underdog odds {odds} too long (max: {strategy.max_underdog_odds})"
            }

    # Check confidence thresholds
    min_conf = strategy.favorite_min_confidence if is_favorite else strategy.min_confidence
    if confidence < min_conf:
        return {
            "allowed": False,
            "reason": f"Confidence {confidence:.1%} below threshold {min_conf:.1%}"
        }

    # Check edge requirements
    min_edge_req = strategy.favorite_min_edge if is_favorite else strategy.min_edge
    if edge < min_edge_req:
        return {
            "allowed": False,
            "reason": f"Edge {edge:.1%} below threshold {min_edge_req:.1%}"
        }

    # Calculate recommended units
    if is_spread_bet:
        if spread_size <= 4:
            units = strategy.small_spread_max_units
        else:
            units = strategy.large_spread_max_units
    elif is_favorite:
        units = strategy.favorite_max_units
    else:
        units = strategy.underdog_max_units

    # Adjust units based on edge (higher edge = more units)
    edge_multiplier = min(1.5, 1.0 + (edge - 0.03) * 5)  # +0.5 units per 10% extra edge
    units = round(units * edge_multiplier, 1)

    return {
        "allowed": True,
        "recommended_units": units,
        "edge_multiplier": round(edge_multiplier, 2)
    }


def get_strategy_summary(sport: str) -> str:
    """Get a human-readable summary of the strategy for a sport."""
    s = get_strategy(sport)
    return f"""
{sport} Betting Strategy:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Spreads:     Max {s.max_spread} points
ML Favorites: No juicier than {s.max_favorite_odds}
ML Underdogs: {s.min_underdog_odds} to {s.max_underdog_odds}
Max Units:   Favorites {s.favorite_max_units}u, Dogs {s.underdog_max_units}u
Min Edge:    Favorites {s.favorite_min_edge:.0%}, Others {s.min_edge:.0%}
"""
