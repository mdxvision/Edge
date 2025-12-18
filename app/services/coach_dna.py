"""
Coach DNA Service

Provides coach behavioral analysis and situational record calculations.
This is EdgeBet's secret weapon - structured coach behavioral data.
"""

from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging

from app.db import Coach, CoachSituationalRecord, CoachTendency

logger = logging.getLogger(__name__)

# All possible situations to track
SITUATIONS = [
    # Favorite/Underdog situations
    "as_favorite",
    "as_underdog",
    "as_home_favorite",
    "as_road_favorite",
    "as_home_underdog",
    "as_road_underdog",
    "as_big_favorite",      # Spread -7 or better
    "as_big_underdog",      # Spread +7 or worse
    "as_small_favorite",    # Spread -1 to -6.5
    "as_small_underdog",    # Spread +1 to +6.5

    # Recent performance situations
    "after_bye_week",
    "after_loss",
    "after_win",
    "after_blowout_loss",   # Lost by 17+
    "after_blowout_win",    # Won by 17+
    "after_close_loss",     # Lost by 3 or less
    "after_close_win",      # Won by 3 or less

    # Game timing situations
    "primetime",
    "monday_night",
    "thursday_night",
    "sunday_night",
    "saturday",
    "early_window",         # 1pm ET games
    "late_window",          # 4pm ET games

    # Opponent situations
    "vs_division",
    "vs_conference",
    "vs_non_conference",
    "vs_former_team",
    "vs_winning_team",      # Opponent has winning record
    "vs_losing_team",       # Opponent has losing record
    "in_rivalry_game",

    # Season situations
    "first_game_of_season",
    "last_game_of_season",
    "in_playoffs",
    "elimination_game",
    "clinched_playoff_spot",

    # NBA-specific situations
    "back_to_back",
    "three_in_four_nights",
    "four_in_five_nights",
    "home_stand",           # 3+ consecutive home games
    "road_trip",            # 3+ consecutive road games

    # Other situations
    "at_home",
    "on_road",
    "neutral_site",
    "indoor",
    "outdoor",
    "cold_weather",         # Under 40F
    "hot_weather",          # Over 85F
]

# Situation display names
SITUATION_DISPLAY_NAMES = {
    "as_favorite": "As Favorite",
    "as_underdog": "As Underdog",
    "as_home_favorite": "Home Favorite",
    "as_road_favorite": "Road Favorite",
    "as_home_underdog": "Home Underdog",
    "as_road_underdog": "Road Underdog",
    "as_big_favorite": "Big Favorite (-7+)",
    "as_big_underdog": "Big Underdog (+7+)",
    "as_small_favorite": "Small Favorite",
    "as_small_underdog": "Small Underdog",
    "after_bye_week": "After Bye Week",
    "after_loss": "After Loss",
    "after_win": "After Win",
    "after_blowout_loss": "After Blowout Loss",
    "after_blowout_win": "After Blowout Win",
    "after_close_loss": "After Close Loss",
    "after_close_win": "After Close Win",
    "primetime": "Primetime",
    "monday_night": "Monday Night",
    "thursday_night": "Thursday Night",
    "sunday_night": "Sunday Night",
    "saturday": "Saturday",
    "early_window": "Early Window",
    "late_window": "Late Window",
    "vs_division": "Vs Division",
    "vs_conference": "Vs Conference",
    "vs_non_conference": "Vs Non-Conference",
    "vs_former_team": "Vs Former Team",
    "vs_winning_team": "Vs Winning Team",
    "vs_losing_team": "Vs Losing Team",
    "in_rivalry_game": "Rivalry Game",
    "first_game_of_season": "Season Opener",
    "last_game_of_season": "Season Finale",
    "in_playoffs": "Playoffs",
    "elimination_game": "Elimination Game",
    "clinched_playoff_spot": "Clinched Playoffs",
    "back_to_back": "Back-to-Back",
    "three_in_four_nights": "3 in 4 Nights",
    "four_in_five_nights": "4 in 5 Nights",
    "home_stand": "Home Stand",
    "road_trip": "Road Trip",
    "at_home": "At Home",
    "on_road": "On Road",
    "neutral_site": "Neutral Site",
    "indoor": "Indoor",
    "outdoor": "Outdoor",
    "cold_weather": "Cold Weather",
    "hot_weather": "Hot Weather",
}


def get_coach_by_name(db: Session, name: str) -> Optional[Dict[str, Any]]:
    """
    Get coach with all situational records by name.

    Args:
        db: Database session
        name: Coach name (case-insensitive search)

    Returns:
        Coach dict with all situational records and tendencies
    """
    coach = db.query(Coach).filter(
        func.lower(Coach.name).contains(name.lower())
    ).first()

    if not coach:
        return None

    return _format_coach_response(coach)


def get_coach_by_id(db: Session, coach_id: int) -> Optional[Dict[str, Any]]:
    """
    Get coach by ID with all situational records.
    """
    coach = db.query(Coach).filter(Coach.id == coach_id).first()

    if not coach:
        return None

    return _format_coach_response(coach)


def _format_coach_response(coach: Coach) -> Dict[str, Any]:
    """Format coach model to response dict."""
    total_ats = coach.career_ats_wins + coach.career_ats_losses + coach.career_ats_pushes
    ats_win_pct = (coach.career_ats_wins / total_ats * 100) if total_ats > 0 else 0

    return {
        "id": coach.id,
        "name": coach.name,
        "sport": coach.sport,
        "current_team": coach.current_team,
        "years_experience": coach.years_experience,
        "career_record": f"{coach.career_wins}-{coach.career_losses}",
        "career_ats": f"{coach.career_ats_wins}-{coach.career_ats_losses}-{coach.career_ats_pushes}",
        "career_ats_pct": round(ats_win_pct, 1),
        "career_over_wins": coach.career_over_wins,
        "career_under_wins": coach.career_under_wins,
        "situational_records": [
            _format_situational_record(sr) for sr in coach.situational_records
        ],
        "tendencies": [
            {
                "type": t.tendency_type,
                "value": t.value,
                "league_average": t.league_average,
                "percentile": t.percentile,
                "notes": t.notes
            }
            for t in coach.tendencies
        ]
    }


def _format_situational_record(sr: CoachSituationalRecord) -> Dict[str, Any]:
    """Format situational record to response dict."""
    total_ats = sr.ats_wins + sr.ats_losses
    ats_win_pct = (sr.ats_wins / total_ats * 100) if total_ats > 0 else 0
    edge = ats_win_pct - 50  # Edge vs 50% baseline

    return {
        "situation": sr.situation,
        "display_name": SITUATION_DISPLAY_NAMES.get(sr.situation, sr.situation.replace("_", " ").title()),
        "record": f"{sr.wins}-{sr.losses}" + (f"-{sr.pushes}" if sr.pushes else ""),
        "ats_record": f"{sr.ats_wins}-{sr.ats_losses}",
        "ats_wins": sr.ats_wins,
        "ats_losses": sr.ats_losses,
        "total_games": sr.total_games,
        "win_pct": round(ats_win_pct, 1),
        "edge": round(edge, 1),
        "roi_percentage": sr.roi_percentage
    }


def get_coach_situational_record(
    db: Session,
    coach_id: int,
    situation: str
) -> Optional[Dict[str, Any]]:
    """
    Get a single situational record for a coach.
    """
    record = db.query(CoachSituationalRecord).filter(
        CoachSituationalRecord.coach_id == coach_id,
        CoachSituationalRecord.situation == situation
    ).first()

    if not record:
        return None

    coach = db.query(Coach).filter(Coach.id == coach_id).first()

    return {
        "coach_name": coach.name if coach else "Unknown",
        "coach_team": coach.current_team if coach else None,
        **_format_situational_record(record)
    }


def get_coach_edge(
    db: Session,
    coach_id: int,
    game_context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate edge for a specific game context.

    Args:
        db: Database session
        coach_id: Coach ID
        game_context: Dict with game details:
            - is_favorite: bool
            - spread: float (negative for favorite)
            - is_home: bool
            - is_primetime: bool (optional)
            - is_monday_night: bool (optional)
            - is_thursday_night: bool (optional)
            - is_sunday_night: bool (optional)
            - previous_result: str ("win", "loss", "blowout_win", "blowout_loss")
            - is_after_bye: bool (optional)
            - is_division_game: bool (optional)
            - is_conference_game: bool (optional)
            - is_playoff: bool (optional)
            - is_back_to_back: bool (optional, NBA)
            - days_rest: int (optional)

    Returns:
        Edge analysis with applicable situations and combined edge
    """
    coach = db.query(Coach).filter(Coach.id == coach_id).first()
    if not coach:
        return {"error": "Coach not found"}

    # Determine applicable situations
    applicable_situations = _determine_applicable_situations(game_context)

    # Get records for each applicable situation
    situation_edges = []
    total_weighted_edge = 0
    total_weight = 0

    for situation in applicable_situations:
        record = db.query(CoachSituationalRecord).filter(
            CoachSituationalRecord.coach_id == coach_id,
            CoachSituationalRecord.situation == situation
        ).first()

        if record and record.total_games >= 5:  # Minimum sample size
            total_ats = record.ats_wins + record.ats_losses
            if total_ats > 0:
                ats_win_pct = record.ats_wins / total_ats * 100
                edge = ats_win_pct - 50

                # Weight by sample size (more games = more reliable)
                weight = min(record.total_games / 20, 2.0)  # Cap at 2x weight
                total_weighted_edge += edge * weight
                total_weight += weight

                situation_edges.append({
                    "situation": SITUATION_DISPLAY_NAMES.get(situation, situation.replace("_", " ").title()),
                    "record": f"{record.ats_wins}-{record.ats_losses} ATS",
                    "win_pct": round(ats_win_pct, 1),
                    "edge": f"{'+' if edge >= 0 else ''}{round(edge, 1)}%",
                    "sample_size": record.total_games
                })

    # Calculate combined edge
    combined_edge = total_weighted_edge / total_weight if total_weight > 0 else 0

    # Calculate confidence score (0-1 based on sample sizes and consistency)
    confidence = _calculate_confidence(situation_edges, total_weight)

    # Generate recommendation
    recommendation = _generate_recommendation(coach, game_context, combined_edge, confidence)

    # Format spread for display
    spread = game_context.get("spread", 0)
    spread_display = f"{'+' if spread > 0 else ''}{spread}" if spread != 0 else "PK"

    total_ats = coach.career_ats_wins + coach.career_ats_losses + coach.career_ats_pushes
    career_ats_pct = (coach.career_ats_wins / total_ats * 100) if total_ats > 0 else 0

    return {
        "coach": {
            "id": coach.id,
            "name": coach.name,
            "team": coach.current_team,
            "career_ats": f"{coach.career_ats_wins}-{coach.career_ats_losses}-{coach.career_ats_pushes} ({round(career_ats_pct, 1)}%)"
        },
        "game_context": {
            "spread": spread_display,
            "is_home": game_context.get("is_home", True),
            "is_primetime": game_context.get("is_primetime", False),
            "previous_result": game_context.get("previous_result", "unknown")
        },
        "applicable_situations": situation_edges,
        "combined_edge": f"{'+' if combined_edge >= 0 else ''}{round(combined_edge, 1)}%",
        "combined_edge_value": round(combined_edge, 2),
        "confidence": round(confidence, 2),
        "recommendation": recommendation
    }


def _determine_applicable_situations(context: Dict[str, Any]) -> List[str]:
    """Determine which situations apply based on game context."""
    situations = []

    spread = context.get("spread", 0)
    is_home = context.get("is_home", True)

    # Favorite/Underdog
    if spread < 0:  # Favorite
        situations.append("as_favorite")
        if is_home:
            situations.append("as_home_favorite")
        else:
            situations.append("as_road_favorite")
        if spread <= -7:
            situations.append("as_big_favorite")
        else:
            situations.append("as_small_favorite")
    elif spread > 0:  # Underdog
        situations.append("as_underdog")
        if is_home:
            situations.append("as_home_underdog")
        else:
            situations.append("as_road_underdog")
        if spread >= 7:
            situations.append("as_big_underdog")
        else:
            situations.append("as_small_underdog")

    # Home/Road
    if is_home:
        situations.append("at_home")
    else:
        situations.append("on_road")

    # Primetime
    if context.get("is_primetime"):
        situations.append("primetime")
    if context.get("is_monday_night"):
        situations.append("monday_night")
    if context.get("is_thursday_night"):
        situations.append("thursday_night")
    if context.get("is_sunday_night"):
        situations.append("sunday_night")

    # Previous result
    prev_result = context.get("previous_result", "").lower()
    if prev_result == "loss":
        situations.append("after_loss")
    elif prev_result == "win":
        situations.append("after_win")
    elif prev_result == "blowout_loss":
        situations.append("after_blowout_loss")
        situations.append("after_loss")
    elif prev_result == "blowout_win":
        situations.append("after_blowout_win")
        situations.append("after_win")

    # Bye week
    if context.get("is_after_bye"):
        situations.append("after_bye_week")

    # Division/Conference
    if context.get("is_division_game"):
        situations.append("vs_division")
    if context.get("is_conference_game"):
        situations.append("vs_conference")
    elif context.get("is_division_game") is False and context.get("is_conference_game") is False:
        situations.append("vs_non_conference")

    # Playoffs
    if context.get("is_playoff"):
        situations.append("in_playoffs")
    if context.get("is_elimination"):
        situations.append("elimination_game")

    # NBA-specific
    if context.get("is_back_to_back"):
        situations.append("back_to_back")

    days_rest = context.get("days_rest", 2)
    if days_rest == 0:
        situations.append("back_to_back")

    # Opponent record
    if context.get("opponent_winning"):
        situations.append("vs_winning_team")
    elif context.get("opponent_losing"):
        situations.append("vs_losing_team")

    return situations


def _calculate_confidence(situation_edges: List[Dict], total_weight: float) -> float:
    """Calculate confidence score based on data quality and consistency."""
    if not situation_edges:
        return 0.0

    # Base confidence from number of applicable situations with data
    base = min(len(situation_edges) / 5, 0.4)  # Up to 0.4 for having 5+ situations

    # Add confidence for sample size (total weight)
    sample_bonus = min(total_weight / 10, 0.3)  # Up to 0.3 for high sample sizes

    # Add confidence for consistency (all edges same direction)
    edges = [float(s["edge"].replace("%", "").replace("+", "")) for s in situation_edges]
    if edges:
        all_positive = all(e > 0 for e in edges)
        all_negative = all(e < 0 for e in edges)
        consistency_bonus = 0.3 if (all_positive or all_negative) else 0.1
    else:
        consistency_bonus = 0

    return min(base + sample_bonus + consistency_bonus, 1.0)


def _generate_recommendation(
    coach: Coach,
    context: Dict[str, Any],
    combined_edge: float,
    confidence: float
) -> str:
    """Generate betting recommendation based on edge and confidence."""
    spread = context.get("spread", 0)
    team = coach.current_team or coach.name

    # Format the spread line
    if spread > 0:
        line = f"{team} +{spread}"
    elif spread < 0:
        line = f"{team} {spread}"
    else:
        line = f"{team} PK"

    # Determine recommendation strength
    if combined_edge >= 8 and confidence >= 0.7:
        return f"STRONG BET: {line}"
    elif combined_edge >= 5 and confidence >= 0.5:
        return f"BET: {line}"
    elif combined_edge >= 3 and confidence >= 0.4:
        return f"LEAN: {line}"
    elif combined_edge <= -8 and confidence >= 0.7:
        return f"STRONG FADE: {line}"
    elif combined_edge <= -5 and confidence >= 0.5:
        return f"FADE: {line}"
    elif combined_edge <= -3 and confidence >= 0.4:
        return f"LEAN FADE: {line}"
    else:
        return f"NO EDGE: {line}"


def get_best_coaches_for_situation(
    db: Session,
    situation: str,
    sport: Optional[str] = None,
    min_games: int = 10
) -> List[Dict[str, Any]]:
    """
    Get leaderboard of coaches for a specific situation.

    Args:
        db: Database session
        situation: Situation to rank
        sport: Optional sport filter
        min_games: Minimum games required

    Returns:
        List of coaches ranked by ATS win percentage
    """
    query = db.query(CoachSituationalRecord, Coach).join(
        Coach, CoachSituationalRecord.coach_id == Coach.id
    ).filter(
        CoachSituationalRecord.situation == situation,
        CoachSituationalRecord.total_games >= min_games
    )

    if sport:
        query = query.filter(Coach.sport == sport)

    results = query.all()

    leaderboard = []
    for record, coach in results:
        total_ats = record.ats_wins + record.ats_losses
        if total_ats > 0:
            ats_pct = record.ats_wins / total_ats * 100
            edge = ats_pct - 50
            leaderboard.append({
                "coach_id": coach.id,
                "coach_name": coach.name,
                "team": coach.current_team,
                "sport": coach.sport,
                "ats_record": f"{record.ats_wins}-{record.ats_losses}",
                "win_pct": round(ats_pct, 1),
                "edge": round(edge, 1),
                "total_games": record.total_games,
                "roi_percentage": record.roi_percentage
            })

    # Sort by win percentage (descending)
    leaderboard.sort(key=lambda x: x["win_pct"], reverse=True)

    return leaderboard


def get_worst_coaches_for_situation(
    db: Session,
    situation: str,
    sport: Optional[str] = None,
    min_games: int = 10
) -> List[Dict[str, Any]]:
    """
    Get fade list of coaches for a specific situation.
    Same as leaderboard but sorted ascending (worst first).
    """
    leaderboard = get_best_coaches_for_situation(db, situation, sport, min_games)
    leaderboard.sort(key=lambda x: x["win_pct"])
    return leaderboard


def compare_coaches(
    db: Session,
    coach1_id: int,
    coach2_id: int,
    game_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Compare two coaches head-to-head.

    Args:
        db: Database session
        coach1_id: First coach ID
        coach2_id: Second coach ID
        game_context: Optional game context for specific comparison

    Returns:
        Comparison analysis
    """
    coach1 = get_coach_by_id(db, coach1_id)
    coach2 = get_coach_by_id(db, coach2_id)

    if not coach1 or not coach2:
        return {"error": "One or both coaches not found"}

    comparison = {
        "coach1": {
            "name": coach1["name"],
            "team": coach1["current_team"],
            "career_ats": coach1["career_ats"],
            "career_ats_pct": coach1["career_ats_pct"]
        },
        "coach2": {
            "name": coach2["name"],
            "team": coach2["current_team"],
            "career_ats": coach2["career_ats"],
            "career_ats_pct": coach2["career_ats_pct"]
        },
        "situation_comparison": []
    }

    # If game context provided, compare edges
    if game_context:
        edge1 = get_coach_edge(db, coach1_id, game_context)
        edge2 = get_coach_edge(db, coach2_id, game_context)

        comparison["coach1"]["edge"] = edge1.get("combined_edge", "N/A")
        comparison["coach1"]["confidence"] = edge1.get("confidence", 0)
        comparison["coach2"]["edge"] = edge2.get("combined_edge", "N/A")
        comparison["coach2"]["confidence"] = edge2.get("confidence", 0)

        # Determine advantage
        edge1_val = edge1.get("combined_edge_value", 0)
        edge2_val = edge2.get("combined_edge_value", 0)

        if abs(edge1_val - edge2_val) < 1:
            comparison["advantage"] = "Even"
        elif edge1_val > edge2_val:
            comparison["advantage"] = coach1["name"]
            comparison["advantage_margin"] = round(edge1_val - edge2_val, 1)
        else:
            comparison["advantage"] = coach2["name"]
            comparison["advantage_margin"] = round(edge2_val - edge1_val, 1)

    # Compare common situations
    coach1_situations = {sr["situation"]: sr for sr in coach1["situational_records"]}
    coach2_situations = {sr["situation"]: sr for sr in coach2["situational_records"]}

    common_situations = set(coach1_situations.keys()) & set(coach2_situations.keys())

    for situation in common_situations:
        s1 = coach1_situations[situation]
        s2 = coach2_situations[situation]

        comparison["situation_comparison"].append({
            "situation": s1["display_name"],
            "coach1_record": s1["ats_record"],
            "coach1_pct": s1["win_pct"],
            "coach2_record": s2["ats_record"],
            "coach2_pct": s2["win_pct"],
            "advantage": coach1["name"] if s1["win_pct"] > s2["win_pct"] else coach2["name"]
        })

    return comparison


def get_all_coaches(
    db: Session,
    sport: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Get all coaches, optionally filtered by sport."""
    query = db.query(Coach)

    if sport:
        query = query.filter(Coach.sport == sport)

    coaches = query.limit(limit).all()

    return [
        {
            "id": c.id,
            "name": c.name,
            "sport": c.sport,
            "current_team": c.current_team,
            "years_experience": c.years_experience,
            "career_record": f"{c.career_wins}-{c.career_losses}",
            "career_ats_wins": c.career_ats_wins,
            "career_ats_losses": c.career_ats_losses,
            "career_ats_pct": round(
                c.career_ats_wins / (c.career_ats_wins + c.career_ats_losses + c.career_ats_pushes) * 100, 1
            ) if (c.career_ats_wins + c.career_ats_losses + c.career_ats_pushes) > 0 else 0
        }
        for c in coaches
    ]


def analyze_matchup(
    db: Session,
    coach1_id: int,
    coach2_id: int,
    spread: float,
    is_coach1_home: bool,
    additional_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Full matchup analysis between two coaches.

    Args:
        db: Database session
        coach1_id: Home/featured coach ID
        coach2_id: Away/opponent coach ID
        spread: Spread from coach1's perspective
        is_coach1_home: Whether coach1 is home team
        additional_context: Additional game context

    Returns:
        Comprehensive matchup analysis
    """
    context1 = {
        "spread": spread,
        "is_home": is_coach1_home,
        **(additional_context or {})
    }

    context2 = {
        "spread": -spread,  # Opposite spread for coach2
        "is_home": not is_coach1_home,
        **(additional_context or {})
    }

    edge1 = get_coach_edge(db, coach1_id, context1)
    edge2 = get_coach_edge(db, coach2_id, context2)

    if "error" in edge1 or "error" in edge2:
        return {"error": "Could not analyze one or both coaches"}

    # Calculate combined analysis
    edge1_val = edge1.get("combined_edge_value", 0)
    edge2_val = edge2.get("combined_edge_value", 0)

    # Net edge (coach1 edge minus coach2 edge)
    net_edge = edge1_val - edge2_val

    # Combined confidence
    avg_confidence = (edge1.get("confidence", 0) + edge2.get("confidence", 0)) / 2

    # Determine recommendation
    coach1_name = edge1["coach"]["name"]
    coach2_name = edge2["coach"]["name"]

    if net_edge >= 5 and avg_confidence >= 0.5:
        pick = f"BET {coach1_name}"
    elif net_edge >= 2:
        pick = f"LEAN {coach1_name}"
    elif net_edge <= -5 and avg_confidence >= 0.5:
        pick = f"BET {coach2_name}"
    elif net_edge <= -2:
        pick = f"LEAN {coach2_name}"
    else:
        pick = "NO CLEAR EDGE"

    return {
        "coach1_analysis": edge1,
        "coach2_analysis": edge2,
        "net_edge": round(net_edge, 1),
        "combined_confidence": round(avg_confidence, 2),
        "recommendation": pick,
        "summary": f"{coach1_name} ({edge1['combined_edge']}) vs {coach2_name} ({edge2['combined_edge']})"
    }


def get_available_situations() -> List[Dict[str, str]]:
    """Get list of all available situations with display names."""
    return [
        {"value": s, "label": SITUATION_DISPLAY_NAMES.get(s, s.replace("_", " ").title())}
        for s in SITUATIONS
    ]
