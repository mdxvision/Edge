"""
Live Betting Model Service

Real-time probability updates during games:
- Live score integration
- Win probability recalculation
- Momentum detection
- Live edge alerts
"""

import math
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field

from app.utils.logging import get_logger
from app.utils.cache import cache, TTL_SHORT

logger = get_logger(__name__)


# =============================================================================
# Data Models
# =============================================================================

class GameStatus(str, Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    HALFTIME = "halftime"
    FINAL = "final"
    DELAYED = "delayed"


class MomentumLevel(str, Enum):
    STRONG_HOME = "strong_home"
    MODERATE_HOME = "moderate_home"
    NEUTRAL = "neutral"
    MODERATE_AWAY = "moderate_away"
    STRONG_AWAY = "strong_away"


@dataclass
class LiveGameState:
    """Current state of a live game."""
    game_id: str
    sport: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    period: str  # Q1, Q2, H1, 3rd, etc.
    time_remaining: str  # "5:30", "12:00", etc.
    status: GameStatus
    last_updated: datetime = field(default_factory=datetime.utcnow)

    # Scoring history for momentum
    scoring_plays: List[Dict] = field(default_factory=list)

    # Pre-game data
    home_spread: float = 0.0
    total_line: float = 0.0
    home_ml_odds: int = 0
    away_ml_odds: int = 0


@dataclass
class LiveProbability:
    """Win probability calculation result."""
    home_win_prob: float
    away_win_prob: float
    tie_prob: float = 0.0
    confidence: float = 0.5
    model_used: str = "basic"
    factors: List[str] = field(default_factory=list)


@dataclass
class MomentumAnalysis:
    """Momentum detection result."""
    level: MomentumLevel
    score: float  # -100 to 100 (negative = away, positive = home)
    trend: str  # "increasing", "stable", "decreasing"
    recent_scoring: Dict[str, int] = field(default_factory=dict)
    key_events: List[str] = field(default_factory=list)


@dataclass
class LiveEdge:
    """Live betting edge opportunity."""
    game_id: str
    edge_type: str  # "moneyline", "spread", "total"
    side: str  # "home", "away", "over", "under"
    current_line: float
    fair_value: float
    edge_pct: float
    confidence: float
    recommendation: str
    expires_at: datetime


# =============================================================================
# Win Probability Models
# =============================================================================

def calculate_nfl_win_probability(state: LiveGameState) -> LiveProbability:
    """
    Calculate NFL win probability using score differential and time remaining.

    Based on historical NFL data and game theory models.
    """
    score_diff = state.home_score - state.away_score

    # Parse time remaining
    minutes_left = _parse_time_remaining(state.period, state.time_remaining, "NFL")
    total_minutes = 60.0

    # Time factor (0 = game over, 1 = full game)
    time_factor = max(0, min(1, minutes_left / total_minutes))

    # Base probability from score differential
    # Approximate: each point is worth ~2.5% win probability at game start
    # This regresses as time runs out
    point_value = 0.025 * time_factor + 0.05 * (1 - time_factor)

    # Logistic model for win probability
    if time_factor > 0:
        # Adjusted score differential accounting for expected scoring
        adjusted_diff = score_diff / (1 + time_factor * 0.5)
        home_win_prob = 1 / (1 + math.exp(-adjusted_diff * point_value * 20))
    else:
        # Game over
        if score_diff > 0:
            home_win_prob = 1.0
        elif score_diff < 0:
            home_win_prob = 0.0
        else:
            home_win_prob = 0.5  # Overtime scenario simplified

    # Account for home field advantage (~2.5 points)
    if time_factor > 0.5:
        home_win_prob = min(0.99, home_win_prob + 0.03 * time_factor)

    factors = []
    if score_diff > 0:
        factors.append(f"Home leads by {score_diff}")
    elif score_diff < 0:
        factors.append(f"Away leads by {abs(score_diff)}")
    factors.append(f"{minutes_left:.1f} minutes remaining")

    confidence = 0.5 + (1 - time_factor) * 0.4  # More confident as game progresses

    return LiveProbability(
        home_win_prob=round(home_win_prob, 4),
        away_win_prob=round(1 - home_win_prob, 4),
        confidence=round(confidence, 2),
        model_used="nfl_time_score",
        factors=factors
    )


def calculate_nba_win_probability(state: LiveGameState) -> LiveProbability:
    """
    Calculate NBA win probability.

    NBA games have higher variance and more scoring,
    so leads are less safe than NFL.
    """
    score_diff = state.home_score - state.away_score

    minutes_left = _parse_time_remaining(state.period, state.time_remaining, "NBA")
    total_minutes = 48.0

    time_factor = max(0, min(1, minutes_left / total_minutes))

    # NBA: each point worth less due to high scoring
    # Approximate: 1 point = 1% at game start
    if time_factor > 0:
        # NBA-specific model: leads can evaporate quickly
        possession_value = 2.0  # Average points per possession
        possessions_left = minutes_left * 2  # Approximate possessions remaining

        # Standard deviation of score differential
        std_dev = math.sqrt(possessions_left * 4)  # Variance per possession

        if std_dev > 0:
            z_score = score_diff / std_dev
            # Use normal CDF approximation
            home_win_prob = 0.5 * (1 + math.erf(z_score / math.sqrt(2)))
        else:
            home_win_prob = 1.0 if score_diff > 0 else (0.0 if score_diff < 0 else 0.5)
    else:
        home_win_prob = 1.0 if score_diff > 0 else (0.0 if score_diff < 0 else 0.5)

    # Home court advantage (~3 points)
    if time_factor > 0.5:
        home_win_prob = min(0.99, home_win_prob + 0.025 * time_factor)

    factors = []
    if score_diff > 0:
        factors.append(f"Home leads by {score_diff}")
    elif score_diff < 0:
        factors.append(f"Away leads by {abs(score_diff)}")
    factors.append(f"{minutes_left:.1f} minutes remaining")

    if abs(score_diff) > 20 and minutes_left < 6:
        factors.append("Garbage time risk")

    confidence = 0.5 + (1 - time_factor) * 0.35

    return LiveProbability(
        home_win_prob=round(home_win_prob, 4),
        away_win_prob=round(1 - home_win_prob, 4),
        confidence=round(confidence, 2),
        model_used="nba_possession",
        factors=factors
    )


def calculate_mlb_win_probability(state: LiveGameState) -> LiveProbability:
    """
    Calculate MLB win probability.

    MLB uses run expectancy and leverage index concepts.
    """
    score_diff = state.home_score - state.away_score

    # Parse inning
    inning = _parse_mlb_inning(state.period)
    is_top = "top" in state.period.lower()

    total_half_innings = 18  # 9 innings * 2
    current_half_inning = (inning - 1) * 2 + (0 if is_top else 1)
    half_innings_left = max(0, total_half_innings - current_half_inning - 1)

    time_factor = half_innings_left / total_half_innings

    if time_factor > 0:
        # MLB run expectancy model
        runs_per_half_inning = 0.5  # Average
        expected_runs_remaining = half_innings_left * runs_per_half_inning
        std_dev = math.sqrt(half_innings_left * 0.8)

        if std_dev > 0:
            z_score = score_diff / std_dev
            home_win_prob = 0.5 * (1 + math.erf(z_score / math.sqrt(2)))
        else:
            home_win_prob = 1.0 if score_diff > 0 else (0.0 if score_diff < 0 else 0.5)

        # Home team bats last advantage in close games
        if not is_top and score_diff >= 0:
            home_win_prob = min(0.99, home_win_prob + 0.02)
    else:
        home_win_prob = 1.0 if score_diff > 0 else (0.0 if score_diff < 0 else 0.5)

    factors = []
    if score_diff > 0:
        factors.append(f"Home leads by {score_diff}")
    elif score_diff < 0:
        factors.append(f"Away leads by {abs(score_diff)}")
    factors.append(f"{'Top' if is_top else 'Bottom'} of inning {inning}")

    confidence = 0.5 + (1 - time_factor) * 0.4

    return LiveProbability(
        home_win_prob=round(home_win_prob, 4),
        away_win_prob=round(1 - home_win_prob, 4),
        confidence=round(confidence, 2),
        model_used="mlb_run_expectancy",
        factors=factors
    )


def calculate_nhl_win_probability(state: LiveGameState) -> LiveProbability:
    """
    Calculate NHL win probability.

    NHL has low scoring so each goal is significant.
    """
    score_diff = state.home_score - state.away_score

    minutes_left = _parse_time_remaining(state.period, state.time_remaining, "NHL")
    total_minutes = 60.0

    time_factor = max(0, min(1, minutes_left / total_minutes))

    if time_factor > 0:
        # NHL: goals are rare, each one is ~15% swing
        goals_expected_remaining = minutes_left / 10  # ~6 goals per game / 60 min
        std_dev = math.sqrt(goals_expected_remaining * 0.8)

        if std_dev > 0:
            z_score = score_diff / std_dev
            home_win_prob = 0.5 * (1 + math.erf(z_score / math.sqrt(2)))
        else:
            home_win_prob = 1.0 if score_diff > 0 else (0.0 if score_diff < 0 else 0.5)
    else:
        # Could go to OT if tied
        if score_diff > 0:
            home_win_prob = 1.0
        elif score_diff < 0:
            home_win_prob = 0.0
        else:
            home_win_prob = 0.5  # OT is coin flip

    # Home ice advantage
    if time_factor > 0.5:
        home_win_prob = min(0.99, home_win_prob + 0.02 * time_factor)

    factors = []
    if score_diff > 0:
        factors.append(f"Home leads by {score_diff}")
    elif score_diff < 0:
        factors.append(f"Away leads by {abs(score_diff)}")
    factors.append(f"{minutes_left:.1f} minutes remaining")

    confidence = 0.5 + (1 - time_factor) * 0.4

    return LiveProbability(
        home_win_prob=round(home_win_prob, 4),
        away_win_prob=round(1 - home_win_prob, 4),
        confidence=round(confidence, 2),
        model_used="nhl_goal_expectancy",
        factors=factors
    )


def calculate_soccer_win_probability(state: LiveGameState) -> LiveProbability:
    """
    Calculate soccer win probability.

    Very low scoring, draws are common.
    """
    score_diff = state.home_score - state.away_score

    minutes_left = _parse_time_remaining(state.period, state.time_remaining, "SOCCER")
    total_minutes = 90.0

    time_factor = max(0, min(1, minutes_left / total_minutes))

    # Soccer: low scoring, draws common
    goals_expected = minutes_left / 30  # ~3 goals per game

    if time_factor > 0 and goals_expected > 0:
        # Poisson-ish model for remaining goals
        if score_diff > 0:
            # Leader needs to hold
            home_win_prob = 0.5 + score_diff * 0.15 * (1 - time_factor)
            tie_prob = 0.2 * time_factor
        elif score_diff < 0:
            home_win_prob = 0.5 - abs(score_diff) * 0.15 * (1 - time_factor)
            tie_prob = 0.2 * time_factor
        else:
            home_win_prob = 0.4  # Slight home advantage
            tie_prob = 0.35 * (1 - time_factor * 0.5)

        home_win_prob = max(0.01, min(0.99, home_win_prob))
        tie_prob = max(0, min(0.5, tie_prob))
    else:
        if score_diff > 0:
            home_win_prob = 1.0
            tie_prob = 0
        elif score_diff < 0:
            home_win_prob = 0.0
            tie_prob = 0
        else:
            home_win_prob = 0.0
            tie_prob = 1.0

    away_win_prob = max(0, 1 - home_win_prob - tie_prob)

    factors = []
    if score_diff > 0:
        factors.append(f"Home leads by {score_diff}")
    elif score_diff < 0:
        factors.append(f"Away leads by {abs(score_diff)}")
    else:
        factors.append("Match tied")
    factors.append(f"{minutes_left:.0f} minutes remaining")

    confidence = 0.45 + (1 - time_factor) * 0.35

    return LiveProbability(
        home_win_prob=round(home_win_prob, 4),
        away_win_prob=round(away_win_prob, 4),
        tie_prob=round(tie_prob, 4),
        confidence=round(confidence, 2),
        model_used="soccer_poisson",
        factors=factors
    )


def calculate_win_probability(state: LiveGameState) -> LiveProbability:
    """Calculate win probability based on sport."""
    sport = state.sport.upper()

    if sport == "NFL":
        return calculate_nfl_win_probability(state)
    elif sport == "NBA":
        return calculate_nba_win_probability(state)
    elif sport == "MLB":
        return calculate_mlb_win_probability(state)
    elif sport == "NHL":
        return calculate_nhl_win_probability(state)
    elif sport == "SOCCER":
        return calculate_soccer_win_probability(state)
    else:
        # Generic model
        return _calculate_generic_win_probability(state)


def _calculate_generic_win_probability(state: LiveGameState) -> LiveProbability:
    """Generic win probability for unsupported sports."""
    score_diff = state.home_score - state.away_score

    # Simple logistic model
    home_win_prob = 1 / (1 + math.exp(-score_diff * 0.1))
    home_win_prob = min(0.95, max(0.05, home_win_prob))

    return LiveProbability(
        home_win_prob=round(home_win_prob, 4),
        away_win_prob=round(1 - home_win_prob, 4),
        confidence=0.4,
        model_used="generic",
        factors=[f"Score differential: {score_diff}"]
    )


# =============================================================================
# Momentum Detection
# =============================================================================

def analyze_momentum(state: LiveGameState) -> MomentumAnalysis:
    """
    Analyze game momentum based on recent scoring.

    Looks at:
    - Recent scoring runs
    - Time between scores
    - Score differential trend
    """
    scoring_plays = state.scoring_plays or []

    # Default values
    if len(scoring_plays) < 2:
        return MomentumAnalysis(
            level=MomentumLevel.NEUTRAL,
            score=0,
            trend="stable",
            recent_scoring={"home": 0, "away": 0},
            key_events=["Insufficient data for momentum analysis"]
        )

    # Analyze last 5 scoring plays
    recent = scoring_plays[-5:] if len(scoring_plays) >= 5 else scoring_plays

    home_recent = sum(1 for p in recent if p.get("team") == "home")
    away_recent = sum(1 for p in recent if p.get("team") == "away")

    # Points in recent plays
    home_points = sum(p.get("points", 0) for p in recent if p.get("team") == "home")
    away_points = sum(p.get("points", 0) for p in recent if p.get("team") == "away")

    # Calculate momentum score (-100 to 100)
    if home_recent + away_recent > 0:
        momentum_score = ((home_recent - away_recent) / (home_recent + away_recent)) * 50
        momentum_score += ((home_points - away_points) / max(home_points + away_points, 1)) * 50
    else:
        momentum_score = 0

    momentum_score = max(-100, min(100, momentum_score))

    # Determine level
    if momentum_score >= 60:
        level = MomentumLevel.STRONG_HOME
    elif momentum_score >= 25:
        level = MomentumLevel.MODERATE_HOME
    elif momentum_score <= -60:
        level = MomentumLevel.STRONG_AWAY
    elif momentum_score <= -25:
        level = MomentumLevel.MODERATE_AWAY
    else:
        level = MomentumLevel.NEUTRAL

    # Determine trend by comparing to earlier
    if len(scoring_plays) >= 8:
        earlier = scoring_plays[-8:-5]
        earlier_home = sum(1 for p in earlier if p.get("team") == "home")
        earlier_away = sum(1 for p in earlier if p.get("team") == "away")

        if earlier_home + earlier_away > 0:
            earlier_score = ((earlier_home - earlier_away) / (earlier_home + earlier_away)) * 100
        else:
            earlier_score = 0

        if momentum_score > earlier_score + 20:
            trend = "increasing_home"
        elif momentum_score < earlier_score - 20:
            trend = "increasing_away"
        else:
            trend = "stable"
    else:
        trend = "stable"

    # Key events
    key_events = []
    if home_recent >= 4:
        key_events.append(f"Home team scored {home_recent} of last {len(recent)} plays")
    if away_recent >= 4:
        key_events.append(f"Away team scored {away_recent} of last {len(recent)} plays")
    if abs(home_points - away_points) >= 10:
        leader = "Home" if home_points > away_points else "Away"
        key_events.append(f"{leader} outscored opponent {max(home_points, away_points)}-{min(home_points, away_points)} recently")

    if not key_events:
        key_events.append("Balanced scoring recently")

    return MomentumAnalysis(
        level=level,
        score=round(momentum_score, 1),
        trend=trend,
        recent_scoring={"home": home_points, "away": away_points},
        key_events=key_events
    )


# =============================================================================
# Live Edge Detection
# =============================================================================

def calculate_live_edges(
    state: LiveGameState,
    probability: LiveProbability,
    current_odds: Dict[str, Any]
) -> List[LiveEdge]:
    """
    Calculate live betting edges by comparing model probabilities to current odds.

    Args:
        state: Current game state
        probability: Calculated win probabilities
        current_odds: Current sportsbook odds

    Returns:
        List of edge opportunities
    """
    edges = []

    # Moneyline edges
    home_ml = current_odds.get("home_ml", 0)
    away_ml = current_odds.get("away_ml", 0)

    if home_ml != 0:
        implied_home = _american_to_probability(home_ml)
        edge_home = (probability.home_win_prob - implied_home) * 100

        if edge_home >= 3:  # 3% minimum edge
            edges.append(LiveEdge(
                game_id=state.game_id,
                edge_type="moneyline",
                side="home",
                current_line=home_ml,
                fair_value=_probability_to_american(probability.home_win_prob),
                edge_pct=round(edge_home, 2),
                confidence=probability.confidence,
                recommendation=f"BET HOME ML ({home_ml})" if edge_home >= 5 else f"Consider home ML",
                expires_at=datetime.utcnow() + timedelta(minutes=5)
            ))

    if away_ml != 0:
        implied_away = _american_to_probability(away_ml)
        edge_away = (probability.away_win_prob - implied_away) * 100

        if edge_away >= 3:
            edges.append(LiveEdge(
                game_id=state.game_id,
                edge_type="moneyline",
                side="away",
                current_line=away_ml,
                fair_value=_probability_to_american(probability.away_win_prob),
                edge_pct=round(edge_away, 2),
                confidence=probability.confidence,
                recommendation=f"BET AWAY ML ({away_ml})" if edge_away >= 5 else f"Consider away ML",
                expires_at=datetime.utcnow() + timedelta(minutes=5)
            ))

    # Live spread edges (if available)
    live_spread = current_odds.get("live_spread")
    if live_spread is not None:
        score_diff = state.home_score - state.away_score
        adjusted_spread = live_spread + score_diff

        # If home is favored more than our model suggests
        if probability.home_win_prob < 0.5 and adjusted_spread < -3:
            edges.append(LiveEdge(
                game_id=state.game_id,
                edge_type="spread",
                side="away",
                current_line=live_spread,
                fair_value=adjusted_spread,
                edge_pct=round(abs(adjusted_spread - live_spread) * 2, 2),
                confidence=probability.confidence * 0.8,
                recommendation=f"Consider AWAY +{abs(live_spread)}",
                expires_at=datetime.utcnow() + timedelta(minutes=5)
            ))

    # Live total edges
    live_total = current_odds.get("live_total")
    if live_total is not None:
        current_total = state.home_score + state.away_score
        pace = _estimate_final_total(state)

        if pace and abs(pace - live_total) >= 3:
            side = "over" if pace > live_total else "under"
            edge_pct = abs(pace - live_total) * 1.5

            edges.append(LiveEdge(
                game_id=state.game_id,
                edge_type="total",
                side=side,
                current_line=live_total,
                fair_value=pace,
                edge_pct=round(edge_pct, 2),
                confidence=probability.confidence * 0.7,
                recommendation=f"Consider {side.upper()} {live_total}",
                expires_at=datetime.utcnow() + timedelta(minutes=5)
            ))

    # Sort by edge percentage
    edges.sort(key=lambda x: x.edge_pct, reverse=True)

    return edges


def generate_live_alerts(
    state: LiveGameState,
    probability: LiveProbability,
    momentum: MomentumAnalysis,
    edges: List[LiveEdge]
) -> List[Dict[str, Any]]:
    """
    Generate alerts for significant live betting opportunities.
    """
    alerts = []

    # High edge alerts
    for edge in edges:
        if edge.edge_pct >= 5:
            alerts.append({
                "type": "edge_alert",
                "priority": "high" if edge.edge_pct >= 8 else "medium",
                "game_id": state.game_id,
                "message": f"Live edge: {edge.recommendation}",
                "details": {
                    "edge_type": edge.edge_type,
                    "side": edge.side,
                    "edge_pct": edge.edge_pct,
                    "current_line": edge.current_line,
                    "fair_value": edge.fair_value,
                },
                "expires_at": edge.expires_at.isoformat(),
            })

    # Momentum shift alerts
    if momentum.level in (MomentumLevel.STRONG_HOME, MomentumLevel.STRONG_AWAY):
        direction = "Home" if momentum.level == MomentumLevel.STRONG_HOME else "Away"
        alerts.append({
            "type": "momentum_alert",
            "priority": "medium",
            "game_id": state.game_id,
            "message": f"Strong {direction} momentum detected",
            "details": {
                "momentum_score": momentum.score,
                "trend": momentum.trend,
                "recent_scoring": momentum.recent_scoring,
            },
            "expires_at": (datetime.utcnow() + timedelta(minutes=10)).isoformat(),
        })

    # Probability swing alerts
    cache_key = f"live_prob:{state.game_id}"
    prev_prob = cache.get(cache_key)

    if prev_prob:
        prob_change = abs(probability.home_win_prob - prev_prob.get("home_win_prob", 0.5))
        if prob_change >= 0.10:  # 10% swing
            alerts.append({
                "type": "probability_swing",
                "priority": "high",
                "game_id": state.game_id,
                "message": f"Win probability shifted {prob_change*100:.1f}%",
                "details": {
                    "previous": prev_prob.get("home_win_prob"),
                    "current": probability.home_win_prob,
                    "change": round(prob_change, 4),
                },
                "expires_at": (datetime.utcnow() + timedelta(minutes=5)).isoformat(),
            })

    # Store current probability for next comparison
    cache.set(cache_key, {
        "home_win_prob": probability.home_win_prob,
        "timestamp": datetime.utcnow().isoformat()
    }, ttl=TTL_SHORT)

    return alerts


# =============================================================================
# Helper Functions
# =============================================================================

def _parse_time_remaining(period: str, time_str: str, sport: str) -> float:
    """Parse time remaining in minutes."""
    try:
        # Handle common formats
        if ":" in time_str:
            parts = time_str.split(":")
            minutes = int(parts[0])
            seconds = int(parts[1]) if len(parts) > 1 else 0
            current_time = minutes + seconds / 60
        else:
            current_time = float(time_str)

        # Calculate total time remaining based on period
        period_lower = period.lower()

        if sport == "NFL":
            period_minutes = 15
            if "1" in period_lower or "q1" in period_lower:
                periods_left = 3
            elif "2" in period_lower or "q2" in period_lower:
                periods_left = 2
            elif "3" in period_lower or "q3" in period_lower:
                periods_left = 1
            elif "4" in period_lower or "q4" in period_lower:
                periods_left = 0
            elif "ot" in period_lower:
                return 10  # OT is 10 minutes
            else:
                periods_left = 0
            return current_time + periods_left * period_minutes

        elif sport == "NBA":
            period_minutes = 12
            if "1" in period_lower:
                periods_left = 3
            elif "2" in period_lower:
                periods_left = 2
            elif "3" in period_lower:
                periods_left = 1
            elif "4" in period_lower:
                periods_left = 0
            elif "ot" in period_lower:
                return 5  # OT is 5 minutes
            else:
                periods_left = 0
            return current_time + periods_left * period_minutes

        elif sport == "NHL":
            period_minutes = 20
            if "1" in period_lower:
                periods_left = 2
            elif "2" in period_lower:
                periods_left = 1
            elif "3" in period_lower:
                periods_left = 0
            elif "ot" in period_lower:
                return 5
            else:
                periods_left = 0
            return current_time + periods_left * period_minutes

        elif sport == "SOCCER":
            # Soccer uses cumulative time
            if "+" in time_str:
                # Stoppage time (e.g., "45+3")
                base, added = time_str.split("+")
                played = int(base) + int(added)
            else:
                played = current_time

            if "1" in period_lower or "first" in period_lower:
                return max(0, 90 - played)
            else:
                return max(0, 90 - played)

        return current_time

    except (ValueError, IndexError):
        return 30  # Default to mid-game


def _parse_mlb_inning(period: str) -> int:
    """Parse MLB inning number."""
    try:
        # Extract number from period string
        import re
        numbers = re.findall(r'\d+', period)
        if numbers:
            return int(numbers[0])
        return 5  # Default to mid-game
    except:
        return 5


def _american_to_probability(american_odds: int) -> float:
    """Convert American odds to implied probability."""
    if american_odds > 0:
        return 100 / (american_odds + 100)
    else:
        return abs(american_odds) / (abs(american_odds) + 100)


def _probability_to_american(prob: float) -> int:
    """Convert probability to American odds."""
    if prob <= 0 or prob >= 1:
        return 0
    if prob >= 0.5:
        return int(-100 * prob / (1 - prob))
    else:
        return int(100 * (1 - prob) / prob)


def _estimate_final_total(state: LiveGameState) -> Optional[float]:
    """Estimate final total based on current pace."""
    current_total = state.home_score + state.away_score

    sport = state.sport.upper()
    minutes_left = _parse_time_remaining(state.period, state.time_remaining, sport)

    if sport == "NFL":
        total_minutes = 60
        minutes_played = total_minutes - minutes_left
        if minutes_played > 10:
            pace = current_total / minutes_played * total_minutes
            return round(pace, 1)

    elif sport == "NBA":
        total_minutes = 48
        minutes_played = total_minutes - minutes_left
        if minutes_played > 10:
            pace = current_total / minutes_played * total_minutes
            return round(pace, 1)

    elif sport == "NHL":
        total_minutes = 60
        minutes_played = total_minutes - minutes_left
        if minutes_played > 15:
            pace = current_total / minutes_played * total_minutes
            return round(pace, 1)

    return None


# =============================================================================
# Main Analysis Function
# =============================================================================

def analyze_live_game(
    state: LiveGameState,
    current_odds: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Perform complete live game analysis.

    Args:
        state: Current game state
        current_odds: Current sportsbook odds (optional)

    Returns:
        Complete analysis including probability, momentum, edges, and alerts
    """
    # Calculate win probability
    probability = calculate_win_probability(state)

    # Analyze momentum
    momentum = analyze_momentum(state)

    # Calculate edges if odds provided
    edges = []
    if current_odds:
        edges = calculate_live_edges(state, probability, current_odds)

    # Generate alerts
    alerts = generate_live_alerts(state, probability, momentum, edges)

    return {
        "game_id": state.game_id,
        "sport": state.sport,
        "matchup": f"{state.away_team} @ {state.home_team}",
        "score": {
            "home": state.home_score,
            "away": state.away_score,
        },
        "period": state.period,
        "time_remaining": state.time_remaining,
        "status": state.status.value,
        "probability": {
            "home_win": probability.home_win_prob,
            "away_win": probability.away_win_prob,
            "tie": probability.tie_prob,
            "confidence": probability.confidence,
            "model": probability.model_used,
            "factors": probability.factors,
        },
        "momentum": {
            "level": momentum.level.value,
            "score": momentum.score,
            "trend": momentum.trend,
            "recent_scoring": momentum.recent_scoring,
            "key_events": momentum.key_events,
        },
        "edges": [
            {
                "type": e.edge_type,
                "side": e.side,
                "current_line": e.current_line,
                "fair_value": e.fair_value,
                "edge_pct": e.edge_pct,
                "confidence": e.confidence,
                "recommendation": e.recommendation,
            }
            for e in edges
        ],
        "alerts": alerts,
        "last_updated": state.last_updated.isoformat(),
    }


# =============================================================================
# Simulation Functions
# =============================================================================

def simulate_live_game(sport: str, game_id: str) -> LiveGameState:
    """Generate a simulated live game state for testing."""
    import random

    teams = {
        "NFL": [("Chiefs", "Bills"), ("Eagles", "Cowboys"), ("49ers", "Ravens")],
        "NBA": [("Celtics", "Lakers"), ("Nuggets", "Heat"), ("Bucks", "Warriors")],
        "MLB": [("Yankees", "Dodgers"), ("Braves", "Astros"), ("Phillies", "Rangers")],
        "NHL": [("Bruins", "Panthers"), ("Oilers", "Stars"), ("Avalanche", "Knights")],
        "SOCCER": [("Man City", "Arsenal"), ("Liverpool", "Chelsea"), ("Real Madrid", "Barcelona")],
    }

    sport = sport.upper()
    team_pair = random.choice(teams.get(sport, [("Home", "Away")]))

    # Generate realistic scores based on sport
    if sport == "NFL":
        home_score = random.randint(7, 28)
        away_score = random.randint(7, 28)
        period = random.choice(["Q1", "Q2", "Q3", "Q4"])
        time_remaining = f"{random.randint(0, 14)}:{random.randint(0, 59):02d}"
    elif sport == "NBA":
        home_score = random.randint(45, 95)
        away_score = random.randint(45, 95)
        period = random.choice(["Q1", "Q2", "Q3", "Q4"])
        time_remaining = f"{random.randint(0, 11)}:{random.randint(0, 59):02d}"
    elif sport == "MLB":
        home_score = random.randint(0, 7)
        away_score = random.randint(0, 7)
        period = random.choice(["Top 4", "Bot 5", "Top 6", "Bot 7", "Top 8"])
        time_remaining = "0:00"
    elif sport == "NHL":
        home_score = random.randint(0, 4)
        away_score = random.randint(0, 4)
        period = random.choice(["1st", "2nd", "3rd"])
        time_remaining = f"{random.randint(0, 19)}:{random.randint(0, 59):02d}"
    else:
        home_score = random.randint(0, 3)
        away_score = random.randint(0, 3)
        period = random.choice(["1st Half", "2nd Half"])
        time_remaining = f"{random.randint(1, 45)}'"

    # Generate scoring plays for momentum
    scoring_plays = []
    num_plays = home_score + away_score
    for i in range(min(num_plays, 10)):
        team = "home" if random.random() < home_score / max(home_score + away_score, 1) else "away"
        if sport == "NFL":
            points = random.choice([3, 7, 7, 7])
        elif sport == "NBA":
            points = random.choice([2, 2, 2, 3])
        else:
            points = 1
        scoring_plays.append({"team": team, "points": points, "time": f"{i*5}:00"})

    return LiveGameState(
        game_id=game_id,
        sport=sport,
        home_team=team_pair[0],
        away_team=team_pair[1],
        home_score=home_score,
        away_score=away_score,
        period=period,
        time_remaining=time_remaining,
        status=GameStatus.IN_PROGRESS,
        scoring_plays=scoring_plays,
        home_spread=-3.5 if sport in ("NFL", "NBA") else 0,
        total_line=45.5 if sport == "NFL" else (220.5 if sport == "NBA" else 8.5),
        home_ml_odds=-150,
        away_ml_odds=130,
    )
