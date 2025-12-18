"""
Officials (Referees/Umpires) Service

Provides official tendency analysis and impact calculations.
This is another hidden edge - official tendencies significantly impact game totals and outcomes.
"""

from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc
from datetime import datetime, timedelta
import logging

from app.db import Official, OfficialGameLog

logger = logging.getLogger(__name__)


# Sport-specific tendency labels
TENDENCY_LABELS = {
    "MLB": {
        "over": "Big strike zone - more runs",
        "under": "Tight strike zone - fewer runs",
        "neutral": "Average strike zone"
    },
    "NBA": {
        "over": "Whistle-happy - more fouls, free throws",
        "under": "Lets them play - fewer stoppages",
        "neutral": "Average whistle"
    },
    "NFL": {
        "over": "Flag-happy - more penalties, longer games",
        "under": "Pocket-friendly - fewer flags",
        "neutral": "Average flag rate"
    }
}


def get_official_by_id(db: Session, official_id: int) -> Optional[Dict[str, Any]]:
    """Get official by ID with full stats."""
    official = db.query(Official).filter(Official.id == official_id).first()
    if not official:
        return None
    return _format_official(official)


def get_official_by_name(db: Session, name: str, sport: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get official by name (case-insensitive search).

    Args:
        db: Database session
        name: Official name to search
        sport: Optional sport filter

    Returns:
        Official dict with stats and tendencies
    """
    query = db.query(Official).filter(
        func.lower(Official.name).contains(name.lower())
    )

    if sport:
        query = query.filter(Official.sport == sport)

    official = query.first()

    if not official:
        return None

    return _format_official(official)


def _format_official(official: Official) -> Dict[str, Any]:
    """Format official model to response dict."""
    total_ou = official.over_wins + official.under_wins
    over_pct = (official.over_wins / total_ou * 100) if total_ou > 0 else 50.0

    # Determine tendency
    tendency = _get_tendency(official)

    return {
        "id": official.id,
        "name": official.name,
        "sport": official.sport,
        "years_experience": official.years_experience,
        "games_officiated": official.games_officiated,
        "photo_url": official.photo_url,

        # O/U tendency
        "over_percentage": round(over_pct, 1),
        "over_wins": official.over_wins,
        "under_wins": official.under_wins,
        "avg_total_score": official.avg_total_score,

        # Home team stats
        "home_team_win_pct": official.home_team_win_pct,
        "home_team_cover_pct": official.home_team_cover_pct,

        # Sport-specific
        "avg_penalties_per_game": official.avg_penalties_per_game,
        "avg_penalty_yards_per_game": official.avg_penalty_yards_per_game,
        "avg_fouls_per_game": official.avg_fouls_per_game,
        "home_team_foul_differential": official.home_team_foul_differential,
        "strike_zone_runs_per_9": official.strike_zone_runs_per_9,
        "ejection_rate": official.ejection_rate,
        "star_foul_rate": official.star_foul_rate,

        # Analysis
        "tendency": tendency,
        "tendency_label": TENDENCY_LABELS.get(official.sport, {}).get(tendency["direction"], ""),
    }


def _get_tendency(official: Official) -> Dict[str, Any]:
    """Determine official's overall tendency."""
    total_ou = official.over_wins + official.under_wins
    if total_ou < 10:
        return {"direction": "neutral", "strength": 0, "confidence": "low"}

    over_pct = official.over_wins / total_ou * 100

    # Determine direction and strength
    if over_pct >= 55:
        direction = "over"
        strength = min((over_pct - 50) / 10, 1.0)  # 0-1 scale
    elif over_pct <= 45:
        direction = "under"
        strength = min((50 - over_pct) / 10, 1.0)
    else:
        direction = "neutral"
        strength = 0

    # Confidence based on sample size
    if total_ou >= 100:
        confidence = "high"
    elif total_ou >= 50:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "direction": direction,
        "strength": round(strength, 2),
        "confidence": confidence,
        "sample_size": total_ou
    }


def get_official_tendencies(db: Session, official_id: int) -> Dict[str, Any]:
    """
    Get detailed tendencies for an official.

    Returns breakdown of stats and historical performance.
    """
    official = db.query(Official).filter(Official.id == official_id).first()
    if not official:
        return {"error": "Official not found"}

    # Get recent game logs for trend analysis
    recent_logs = db.query(OfficialGameLog).filter(
        OfficialGameLog.official_id == official_id
    ).order_by(desc(OfficialGameLog.game_date)).limit(20).all()

    # Calculate recent trend
    recent_overs = sum(1 for log in recent_logs if log.went_over)
    recent_total = len(recent_logs)
    recent_over_pct = (recent_overs / recent_total * 100) if recent_total > 0 else 50

    # Career vs recent comparison
    career_over_pct = (official.over_wins / (official.over_wins + official.under_wins) * 100) if (official.over_wins + official.under_wins) > 0 else 50

    trend = "improving" if recent_over_pct > career_over_pct + 5 else "declining" if recent_over_pct < career_over_pct - 5 else "stable"

    return {
        "official_id": official.id,
        "name": official.name,
        "sport": official.sport,

        "career_stats": {
            "games": official.games_officiated,
            "over_pct": round(career_over_pct, 1),
            "over_record": f"{official.over_wins}-{official.under_wins}",
            "home_win_pct": official.home_team_win_pct,
            "avg_total": official.avg_total_score
        },

        "recent_stats": {
            "games": recent_total,
            "over_pct": round(recent_over_pct, 1),
            "trend": trend
        },

        "sport_specific": _get_sport_specific_tendencies(official),

        "recommendation": _get_ou_recommendation(official, recent_over_pct)
    }


def _get_sport_specific_tendencies(official: Official) -> Dict[str, Any]:
    """Get sport-specific tendency details."""
    if official.sport == "MLB":
        return {
            "strike_zone": _classify_strike_zone(official.strike_zone_runs_per_9),
            "runs_per_9": official.strike_zone_runs_per_9,
            "ejection_rate": official.ejection_rate,
            "explanation": _get_mlb_explanation(official)
        }
    elif official.sport == "NBA":
        return {
            "fouls_per_game": official.avg_fouls_per_game,
            "home_foul_diff": official.home_team_foul_differential,
            "star_treatment": _classify_star_treatment(official.star_foul_rate),
            "explanation": _get_nba_explanation(official)
        }
    elif official.sport == "NFL":
        return {
            "penalties_per_game": official.avg_penalties_per_game,
            "penalty_yards_per_game": official.avg_penalty_yards_per_game,
            "explanation": _get_nfl_explanation(official)
        }
    return {}


def _classify_strike_zone(runs_per_9: Optional[float]) -> str:
    """Classify MLB umpire strike zone."""
    if runs_per_9 is None:
        return "unknown"
    if runs_per_9 >= 5.0:
        return "small (hitter-friendly)"
    elif runs_per_9 <= 4.0:
        return "large (pitcher-friendly)"
    return "average"


def _classify_star_treatment(star_rate: Optional[float]) -> str:
    """Classify NBA ref star treatment."""
    if star_rate is None:
        return "unknown"
    if star_rate >= 1.1:
        return "tough on stars"
    elif star_rate <= 0.9:
        return "favorable to stars"
    return "neutral"


def _get_mlb_explanation(official: Official) -> str:
    """Generate MLB umpire explanation."""
    parts = []
    if official.strike_zone_runs_per_9:
        if official.strike_zone_runs_per_9 >= 5.0:
            parts.append("Has a tight strike zone leading to more walks and runs")
        elif official.strike_zone_runs_per_9 <= 4.0:
            parts.append("Has a generous strike zone favoring pitchers")

    if official.over_percentage and official.over_percentage >= 55:
        parts.append(f"Games go OVER {official.over_percentage:.0f}% of the time")
    elif official.over_percentage and official.over_percentage <= 45:
        parts.append(f"Games go UNDER {100 - official.over_percentage:.0f}% of the time")

    return ". ".join(parts) if parts else "Average tendencies"


def _get_nba_explanation(official: Official) -> str:
    """Generate NBA referee explanation."""
    parts = []
    if official.avg_fouls_per_game:
        league_avg = 42.0  # Approximate league average
        if official.avg_fouls_per_game >= league_avg + 3:
            parts.append(f"Calls {official.avg_fouls_per_game:.1f} fouls/game (above average)")
        elif official.avg_fouls_per_game <= league_avg - 3:
            parts.append(f"Calls only {official.avg_fouls_per_game:.1f} fouls/game (below average)")

    if official.home_team_foul_differential:
        if official.home_team_foul_differential >= 2:
            parts.append("Tends to favor home teams with foul calls")
        elif official.home_team_foul_differential <= -2:
            parts.append("Tends to call more fouls on home teams")

    return ". ".join(parts) if parts else "Average tendencies"


def _get_nfl_explanation(official: Official) -> str:
    """Generate NFL referee explanation."""
    parts = []
    if official.avg_penalties_per_game:
        league_avg = 12.0
        if official.avg_penalties_per_game >= league_avg + 2:
            parts.append(f"Flag-heavy crew averaging {official.avg_penalties_per_game:.1f} penalties/game")
        elif official.avg_penalties_per_game <= league_avg - 2:
            parts.append(f"Lets them play with only {official.avg_penalties_per_game:.1f} penalties/game")

    if official.avg_penalty_yards_per_game:
        if official.avg_penalty_yards_per_game >= 100:
            parts.append("High penalty yardage affects game flow")

    return ". ".join(parts) if parts else "Average tendencies"


def _get_ou_recommendation(official: Official, recent_over_pct: float) -> Dict[str, Any]:
    """Generate O/U recommendation based on official."""
    total_games = official.over_wins + official.under_wins
    career_over_pct = (official.over_wins / total_games * 100) if total_games > 0 else 50

    # Weight recent more heavily
    weighted_pct = (career_over_pct * 0.4 + recent_over_pct * 0.6)

    if total_games < 20:
        return {
            "direction": "NEUTRAL",
            "confidence": 0,
            "reason": "Insufficient sample size"
        }

    if weighted_pct >= 57:
        return {
            "direction": "LEAN OVER",
            "confidence": min((weighted_pct - 50) / 20, 1.0),
            "reason": f"Official's games go over {career_over_pct:.0f}% of the time"
        }
    elif weighted_pct <= 43:
        return {
            "direction": "LEAN UNDER",
            "confidence": min((50 - weighted_pct) / 20, 1.0),
            "reason": f"Official's games go under {100 - career_over_pct:.0f}% of the time"
        }

    return {
        "direction": "NEUTRAL",
        "confidence": 0,
        "reason": "No significant O/U edge"
    }


def get_official_impact(
    db: Session,
    official_id: int,
    game_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Calculate official's expected impact on a specific game.

    Args:
        db: Database session
        official_id: Official ID
        game_context: Optional context with total line, home team, etc.

    Returns:
        Impact analysis with adjustment recommendations
    """
    official = db.query(Official).filter(Official.id == official_id).first()
    if not official:
        return {"error": "Official not found"}

    total_games = official.over_wins + official.under_wins
    if total_games < 10:
        return {
            "official": official.name,
            "impact": "unknown",
            "adjustment": 0,
            "reason": "Insufficient data"
        }

    over_pct = official.over_wins / total_games * 100

    # Calculate total adjustment
    # If official has 60% over rate, games average ~2 points higher than line
    edge_from_50 = over_pct - 50
    total_adjustment = edge_from_50 * 0.1  # Rough conversion to points

    # Sport-specific adjustments
    sport_adjustment = 0
    sport_notes = []

    if official.sport == "MLB" and official.strike_zone_runs_per_9:
        league_avg_runs = 4.5
        runs_diff = official.strike_zone_runs_per_9 - league_avg_runs
        sport_adjustment = runs_diff * 0.5
        if runs_diff > 0.3:
            sport_notes.append(f"Small strike zone adds ~{runs_diff:.1f} runs")
        elif runs_diff < -0.3:
            sport_notes.append(f"Large strike zone reduces ~{abs(runs_diff):.1f} runs")

    elif official.sport == "NBA" and official.avg_fouls_per_game:
        league_avg_fouls = 42.0
        foul_diff = official.avg_fouls_per_game - league_avg_fouls
        # More fouls = more free throws = slightly higher scoring
        sport_adjustment = foul_diff * 0.15
        if foul_diff > 3:
            sport_notes.append(f"High foul rate adds ~{foul_diff * 0.5:.1f} points via FTs")

    elif official.sport == "NFL" and official.avg_penalties_per_game:
        league_avg_penalties = 12.0
        pen_diff = official.avg_penalties_per_game - league_avg_penalties
        # More penalties = more first downs = mixed effect but slightly higher
        sport_adjustment = pen_diff * 0.3
        if pen_diff > 2:
            sport_notes.append("High penalty rate extends drives")

    combined_adjustment = total_adjustment + sport_adjustment

    # Determine recommendation
    if combined_adjustment >= 1.5:
        recommendation = "LEAN OVER"
        impact = "positive_over"
    elif combined_adjustment <= -1.5:
        recommendation = "LEAN UNDER"
        impact = "positive_under"
    else:
        recommendation = "NEUTRAL"
        impact = "minimal"

    return {
        "official": {
            "id": official.id,
            "name": official.name,
            "sport": official.sport
        },
        "over_percentage": round(over_pct, 1),
        "total_adjustment": round(combined_adjustment, 1),
        "impact": impact,
        "recommendation": recommendation,
        "confidence": _get_tendency(official)["confidence"],
        "notes": sport_notes,
        "tendency_label": TENDENCY_LABELS.get(official.sport, {}).get(
            "over" if combined_adjustment > 0 else "under" if combined_adjustment < 0 else "neutral",
            ""
        )
    }


def get_best_over_officials(
    db: Session,
    sport: Optional[str] = None,
    min_games: int = 30,
    limit: int = 15
) -> List[Dict[str, Any]]:
    """
    Get officials whose games most frequently go over.

    Args:
        db: Database session
        sport: Filter by sport
        min_games: Minimum games officiated
        limit: Max results

    Returns:
        List of officials sorted by over percentage
    """
    query = db.query(Official).filter(
        Official.games_officiated >= min_games,
        (Official.over_wins + Official.under_wins) >= min_games
    )

    if sport:
        query = query.filter(Official.sport == sport)

    officials = query.all()

    # Calculate over percentage and sort
    results = []
    for off in officials:
        total = off.over_wins + off.under_wins
        if total > 0:
            over_pct = off.over_wins / total * 100
            results.append({
                "id": off.id,
                "name": off.name,
                "sport": off.sport,
                "over_percentage": round(over_pct, 1),
                "over_record": f"{off.over_wins}-{off.under_wins}",
                "games": total,
                "avg_total": off.avg_total_score,
                "tendency_label": TENDENCY_LABELS.get(off.sport, {}).get("over", "")
            })

    results.sort(key=lambda x: x["over_percentage"], reverse=True)
    return results[:limit]


def get_best_under_officials(
    db: Session,
    sport: Optional[str] = None,
    min_games: int = 30,
    limit: int = 15
) -> List[Dict[str, Any]]:
    """
    Get officials whose games most frequently go under.
    """
    query = db.query(Official).filter(
        Official.games_officiated >= min_games,
        (Official.over_wins + Official.under_wins) >= min_games
    )

    if sport:
        query = query.filter(Official.sport == sport)

    officials = query.all()

    results = []
    for off in officials:
        total = off.over_wins + off.under_wins
        if total > 0:
            under_pct = off.under_wins / total * 100
            results.append({
                "id": off.id,
                "name": off.name,
                "sport": off.sport,
                "under_percentage": round(under_pct, 1),
                "under_record": f"{off.under_wins}-{off.over_wins}",
                "games": total,
                "avg_total": off.avg_total_score,
                "tendency_label": TENDENCY_LABELS.get(off.sport, {}).get("under", "")
            })

    results.sort(key=lambda x: x["under_percentage"], reverse=True)
    return results[:limit]


def get_home_biased_officials(
    db: Session,
    sport: Optional[str] = None,
    min_games: int = 30,
    limit: int = 15
) -> List[Dict[str, Any]]:
    """
    Get officials who favor home teams (by cover percentage).
    """
    query = db.query(Official).filter(
        Official.games_officiated >= min_games,
        Official.home_team_cover_pct.isnot(None)
    )

    if sport:
        query = query.filter(Official.sport == sport)

    officials = query.order_by(desc(Official.home_team_cover_pct)).limit(limit).all()

    return [
        {
            "id": off.id,
            "name": off.name,
            "sport": off.sport,
            "home_cover_pct": round(off.home_team_cover_pct, 1) if off.home_team_cover_pct else None,
            "home_win_pct": round(off.home_team_win_pct, 1) if off.home_team_win_pct else None,
            "games": off.games_officiated,
            "foul_differential": off.home_team_foul_differential
        }
        for off in officials
    ]


def get_all_officials(
    db: Session,
    sport: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Get all officials, optionally filtered by sport."""
    query = db.query(Official)

    if sport:
        query = query.filter(Official.sport == sport)

    officials = query.order_by(Official.name).limit(limit).all()

    results = []
    for off in officials:
        total = off.over_wins + off.under_wins
        over_pct = (off.over_wins / total * 100) if total > 0 else 50

        results.append({
            "id": off.id,
            "name": off.name,
            "sport": off.sport,
            "years_experience": off.years_experience,
            "games_officiated": off.games_officiated,
            "over_percentage": round(over_pct, 1),
            "tendency": _get_tendency(off)["direction"]
        })

    return results


def get_official_game_history(
    db: Session,
    official_id: int,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Get recent game history for an official."""
    logs = db.query(OfficialGameLog).filter(
        OfficialGameLog.official_id == official_id
    ).order_by(desc(OfficialGameLog.game_date)).limit(limit).all()

    return [
        {
            "game_date": log.game_date.isoformat() if log.game_date else None,
            "matchup": f"{log.away_team} @ {log.home_team}",
            "total_score": log.total_score,
            "ou_line": log.over_under_line,
            "went_over": log.went_over,
            "home_won": log.home_team_won,
            "fouls": log.fouls_called,
            "penalties": log.penalties_called
        }
        for log in logs
    ]


def search_officials(
    db: Session,
    query: str,
    sport: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Search officials by name."""
    q = db.query(Official).filter(
        func.lower(Official.name).contains(query.lower())
    )

    if sport:
        q = q.filter(Official.sport == sport)

    officials = q.limit(limit).all()

    return [
        {
            "id": off.id,
            "name": off.name,
            "sport": off.sport,
            "games": off.games_officiated
        }
        for off in officials
    ]
