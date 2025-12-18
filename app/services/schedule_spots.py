"""
Schedule Spots Detection Service

Detects profitable scheduling situations:
- Lookahead spots (big game coming)
- Letdown spots (after emotional game)
- Sandwich spots (weak team between two tough games)
- Trap games (public overvaluing favorites)
"""

from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

from app.db import Game, GameSituation

logger = logging.getLogger(__name__)


# Known strong teams by sport (for detecting lookahead/sandwich spots)
STRONG_TEAMS = {
    "NBA": [
        "Celtics", "Nuggets", "Thunder", "Timberwolves", "Knicks",
        "Cavaliers", "Bucks", "76ers", "Heat", "Lakers", "Suns",
        "Warriors", "Mavericks", "Clippers"
    ],
    "NFL": [
        "Chiefs", "Ravens", "49ers", "Bills", "Cowboys", "Lions",
        "Eagles", "Dolphins", "Packers", "Browns", "Texans"
    ],
    "MLB": [
        "Dodgers", "Braves", "Phillies", "Astros", "Rangers",
        "Orioles", "Rays", "Twins", "Yankees", "Diamondbacks"
    ],
}

# Known weaker teams
WEAK_TEAMS = {
    "NBA": [
        "Wizards", "Pistons", "Hornets", "Spurs", "Trail Blazers",
        "Raptors", "Jazz", "Rockets"
    ],
    "NFL": [
        "Panthers", "Cardinals", "Patriots", "Giants", "Commanders",
        "Bears", "Titans", "Raiders"
    ],
    "MLB": [
        "Athletics", "Rockies", "Royals", "White Sox", "Marlins",
        "Angels", "Tigers"
    ],
}

# Major rivalry matchups (for detecting lookahead)
MAJOR_MATCHUPS = {
    "NBA": [
        ("Lakers", "Celtics"), ("Warriors", "Lakers"), ("Knicks", "Nets"),
        ("Celtics", "76ers"), ("Heat", "Knicks"), ("Bulls", "Pistons"),
        ("Mavericks", "Spurs"), ("Lakers", "Clippers")
    ],
    "NFL": [
        ("Cowboys", "Eagles"), ("Cowboys", "Giants"), ("Packers", "Bears"),
        ("Steelers", "Ravens"), ("Chiefs", "Raiders"), ("49ers", "Seahawks"),
        ("Bills", "Dolphins"), ("Patriots", "Jets")
    ],
    "MLB": [
        ("Yankees", "Red Sox"), ("Dodgers", "Giants"), ("Cubs", "Cardinals"),
        ("Mets", "Phillies"), ("Astros", "Rangers")
    ],
}


def is_strong_team(team: str, sport: str) -> bool:
    """Check if a team is considered strong."""
    strong = STRONG_TEAMS.get(sport, [])
    return any(s.lower() in team.lower() for s in strong)


def is_weak_team(team: str, sport: str) -> bool:
    """Check if a team is considered weak."""
    weak = WEAK_TEAMS.get(sport, [])
    return any(w.lower() in team.lower() for w in weak)


def is_major_matchup(team1: str, team2: str, sport: str) -> bool:
    """Check if this is a major rivalry matchup."""
    matchups = MAJOR_MATCHUPS.get(sport, [])
    for t1, t2 in matchups:
        if (t1.lower() in team1.lower() or t1.lower() in team2.lower()) and \
           (t2.lower() in team1.lower() or t2.lower() in team2.lower()):
            return True
    return False


def detect_lookahead(
    team: str,
    current_opponent: str,
    next_opponent: str,
    sport: str
) -> Dict[str, Any]:
    """
    Detect lookahead spots where a team might be looking past current game.

    A lookahead spot occurs when:
    1. Current opponent is weak
    2. Next opponent is a rival or strong team
    3. Team is favored in current game
    """
    is_current_weak = is_weak_team(current_opponent, sport)
    is_next_strong = is_strong_team(next_opponent, sport) or \
                     is_major_matchup(team, next_opponent, sport)

    detected = is_current_weak and is_next_strong

    confidence = 0.0
    if detected:
        confidence = 0.6
        if is_major_matchup(team, next_opponent, sport):
            confidence = 0.8
        if is_strong_team(team, sport):
            confidence += 0.1

    return {
        "detected": detected,
        "team": team if detected else None,
        "current_opponent": current_opponent,
        "next_opponent": next_opponent if detected else None,
        "reason": f"{team} playing weak {current_opponent} before big game vs {next_opponent}" if detected else None,
        "confidence": round(confidence, 2),
        "fade_recommendation": f"Fade {team} - potential lookahead spot" if detected else None,
        "edge_percentage": 2.5 if detected else 0
    }


def detect_letdown(
    team: str,
    previous_opponent: str,
    previous_game_type: str,
    sport: str
) -> Dict[str, Any]:
    """
    Detect letdown spots where a team might have emotional hangover.

    A letdown spot occurs after:
    1. Big rivalry game
    2. Overtime thriller
    3. Playoff clinching game
    4. National TV spotlight game
    5. Big upset win
    """
    letdown_triggers = [
        "overtime", "rivalry", "clinch", "national_tv", "upset",
        "playoff", "comeback", "buzzer_beater"
    ]

    is_letdown = any(trigger in previous_game_type.lower() for trigger in letdown_triggers)

    # Also check if previous opponent was a rival
    is_letdown = is_letdown or is_major_matchup(team, previous_opponent, sport)

    confidence = 0.0
    reason = None

    if is_letdown:
        confidence = 0.65
        if "overtime" in previous_game_type.lower():
            confidence = 0.75
            reason = f"{team} coming off OT thriller vs {previous_opponent}"
        elif "clinch" in previous_game_type.lower():
            confidence = 0.80
            reason = f"{team} after clinching game - motivation drop"
        elif is_major_matchup(team, previous_opponent, sport):
            confidence = 0.70
            reason = f"{team} letdown after big rivalry game vs {previous_opponent}"
        else:
            reason = f"{team} potential letdown after emotional game vs {previous_opponent}"

    return {
        "detected": is_letdown,
        "team": team if is_letdown else None,
        "previous_opponent": previous_opponent,
        "previous_game_type": previous_game_type,
        "reason": reason,
        "confidence": round(confidence, 2),
        "fade_recommendation": f"Fade {team} - letdown spot" if is_letdown else None,
        "edge_percentage": 1.8 if is_letdown else 0
    }


def detect_sandwich(
    team: str,
    previous_opponent: str,
    current_opponent: str,
    next_opponent: str,
    sport: str
) -> Dict[str, Any]:
    """
    Detect sandwich spots - weak opponent between two tough games.

    Classic trap game scenario where favorites often fail to cover.
    """
    is_prev_strong = is_strong_team(previous_opponent, sport)
    is_current_weak = is_weak_team(current_opponent, sport)
    is_next_strong = is_strong_team(next_opponent, sport)

    # Classic sandwich: strong - weak - strong
    detected = is_prev_strong and is_current_weak and is_next_strong

    # Also detect: any tough game before and rivalry after
    if not detected:
        detected = is_prev_strong and is_current_weak and \
                   is_major_matchup(team, next_opponent, sport)

    confidence = 0.0
    if detected:
        confidence = 0.72
        if is_major_matchup(team, next_opponent, sport):
            confidence = 0.82

    return {
        "detected": detected,
        "team": team if detected else None,
        "previous_opponent": previous_opponent,
        "current_opponent": current_opponent,
        "next_opponent": next_opponent,
        "reason": f"{team} in sandwich spot: {previous_opponent} → {current_opponent} → {next_opponent}" if detected else None,
        "confidence": round(confidence, 2),
        "fade_recommendation": f"Strong fade on {team} - classic sandwich spot" if detected else None,
        "edge_percentage": 3.0 if detected else 0
    }


def detect_trap_game(
    favorite: str,
    underdog: str,
    sport: str,
    spread: float,
    is_home_favorite: bool = True,
    previous_opponent: Optional[str] = None,
    next_opponent: Optional[str] = None
) -> Dict[str, Any]:
    """
    Detect trap games where public is overvaluing the favorite.

    Trap game indicators:
    1. Big spread (-7 or more)
    2. Favorite against weak team
    3. Favorite has tough game coming up
    4. Favorite coming off big win (letdown potential)
    """
    indicators = []
    trap_score = 0

    # Big spread
    if abs(spread) >= 10:
        indicators.append("Large spread (public inflated)")
        trap_score += 2
    elif abs(spread) >= 7:
        indicators.append("Moderate to large spread")
        trap_score += 1

    # Favorite vs weak team
    if is_weak_team(underdog, sport):
        indicators.append(f"{underdog} is perceived as weak - public piling on favorite")
        trap_score += 1

    # Lookahead element
    if next_opponent and (is_strong_team(next_opponent, sport) or
                          is_major_matchup(favorite, next_opponent, sport)):
        indicators.append(f"Favorite has tough game vs {next_opponent} coming up")
        trap_score += 2

    # Letdown element
    if previous_opponent and (is_strong_team(previous_opponent, sport) or
                              is_major_matchup(favorite, previous_opponent, sport)):
        indicators.append(f"Favorite coming off big game vs {previous_opponent}")
        trap_score += 1

    detected = trap_score >= 3
    confidence = min(0.5 + trap_score * 0.08, 0.85) if detected else 0

    return {
        "detected": detected,
        "favorite": favorite,
        "underdog": underdog,
        "spread": spread,
        "indicators": indicators,
        "trap_score": trap_score,
        "confidence": round(confidence, 2),
        "recommendation": f"Consider {underdog} +{abs(spread)} - trap game indicators present" if detected else None,
        "edge_percentage": trap_score * 0.8 if detected else 0
    }


def get_schedule_spot_alerts(
    db: Session,
    sport: Optional[str] = None,
    date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """
    Get all notable schedule spots for a given date.

    Scans games and detects:
    - Lookahead spots
    - Letdown spots
    - Sandwich spots
    - Trap games
    """
    if date is None:
        date = datetime.utcnow()

    alerts = []

    # Get games from database for the date
    start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    query = db.query(Game).filter(
        Game.start_time >= start_of_day,
        Game.start_time < end_of_day
    )

    if sport:
        query = query.filter(Game.sport == sport)

    games = query.all()

    for game in games:
        home_team = game.home_team or ""
        away_team = game.away_team or ""
        game_sport = game.sport or "NBA"

        # For each game, we would need schedule context (previous/next games)
        # Since we may not have full schedule data, we'll provide analysis framework

        alert = {
            "game_id": game.id,
            "matchup": f"{away_team} @ {home_team}",
            "sport": game_sport,
            "time": game.start_time.isoformat() if game.start_time else None,
            "spots": []
        }

        # Check if either team is strong playing a weak team (potential trap)
        if is_strong_team(home_team, game_sport) and is_weak_team(away_team, game_sport):
            alert["spots"].append({
                "type": "POTENTIAL_TRAP",
                "team": home_team,
                "description": f"{home_team} (strong) vs {away_team} (weak) - watch for trap indicators",
                "confidence": 0.5
            })

        if is_strong_team(away_team, game_sport) and is_weak_team(home_team, game_sport):
            alert["spots"].append({
                "type": "POTENTIAL_TRAP",
                "team": away_team,
                "description": f"{away_team} (strong) on road vs {home_team} (weak) - possible trap",
                "confidence": 0.55
            })

        # Check for rivalry
        if is_major_matchup(home_team, away_team, game_sport):
            alert["spots"].append({
                "type": "RIVALRY",
                "description": f"Major rivalry matchup - both teams motivated",
                "confidence": 0.7
            })

        if alert["spots"]:
            alerts.append(alert)

    return alerts


def analyze_schedule_context(
    team: str,
    previous_game: Optional[Dict[str, Any]] = None,
    current_game: Dict[str, Any] = None,
    next_game: Optional[Dict[str, Any]] = None,
    sport: str = "NBA"
) -> Dict[str, Any]:
    """
    Analyze full schedule context for a team in a specific game.

    Returns all detected schedule spots.
    """
    if not current_game:
        return {"error": "Current game required"}

    current_opponent = current_game.get("opponent", "")
    spots = []
    total_edge = 0

    # Check lookahead
    if next_game:
        next_opponent = next_game.get("opponent", "")
        lookahead = detect_lookahead(team, current_opponent, next_opponent, sport)
        if lookahead["detected"]:
            spots.append(lookahead)
            total_edge -= lookahead["edge_percentage"]  # Negative for the team

    # Check letdown
    if previous_game:
        prev_opponent = previous_game.get("opponent", "")
        prev_type = previous_game.get("game_type", "")
        letdown = detect_letdown(team, prev_opponent, prev_type, sport)
        if letdown["detected"]:
            spots.append(letdown)
            total_edge -= letdown["edge_percentage"]

    # Check sandwich
    if previous_game and next_game:
        prev_opponent = previous_game.get("opponent", "")
        next_opponent = next_game.get("opponent", "")
        sandwich = detect_sandwich(team, prev_opponent, current_opponent, next_opponent, sport)
        if sandwich["detected"]:
            spots.append(sandwich)
            total_edge -= sandwich["edge_percentage"]

    # Overall assessment
    has_spots = len(spots) > 0
    avg_confidence = sum(s["confidence"] for s in spots) / len(spots) if spots else 0

    return {
        "team": team,
        "current_game": current_game,
        "spots_detected": len(spots),
        "spots": spots,
        "total_edge_against": round(total_edge, 1),
        "confidence": round(avg_confidence, 2),
        "recommendation": f"FADE {team}" if total_edge <= -2 else "No strong schedule spot" if not has_spots else f"Minor schedule concern for {team}"
    }


def get_todays_lookahead_spots(db: Session, sport: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all lookahead spots for today's games."""
    # This would require full schedule data to properly detect
    # For now, return framework structure
    return []


def get_todays_letdown_spots(db: Session, sport: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all letdown spots for today's games."""
    # This would require game results data to properly detect
    return []


def get_todays_sandwich_spots(db: Session, sport: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all sandwich spots for today's games."""
    return []


def get_todays_trap_games(db: Session, sport: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all trap games for today."""
    return []
