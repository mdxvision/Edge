"""
Power Ratings Service

Calculates team strength ratings based on:
- Offensive efficiency (points per possession)
- Defensive efficiency (points allowed per possession)
- Recent form (last 5 games weighted 2x)
- Strength of schedule adjustment
- Home/away splits

Scale: 0-100 where 50 is average, 70+ is elite, 30- is poor
"""

from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from datetime import datetime, timedelta
import logging
import json

from app.db import (
    TeamPowerRating, ATSRecord, SituationalTrend, HeadToHeadGame,
    Team, HistoricalGameResult
)

logger = logging.getLogger(__name__)

# Sport-specific configuration
SPORT_CONFIG = {
    "NFL": {
        "home_advantage": 2.5,
        "possessions_per_game": 11,  # Average drives
        "avg_points_per_game": 23,
    },
    "NBA": {
        "home_advantage": 3.0,
        "possessions_per_game": 100,
        "avg_points_per_game": 115,
    },
    "MLB": {
        "home_advantage": 0.5,  # Runs
        "possessions_per_game": 9,  # Innings
        "avg_points_per_game": 4.5,
    },
    "NHL": {
        "home_advantage": 0.3,  # Goals
        "possessions_per_game": 60,  # Shot attempts approx
        "avg_points_per_game": 3.0,
    },
    "NCAA_FOOTBALL": {
        "home_advantage": 3.0,
        "possessions_per_game": 12,
        "avg_points_per_game": 28,
    },
    "NCAA_BASKETBALL": {
        "home_advantage": 3.5,
        "possessions_per_game": 70,
        "avg_points_per_game": 75,
    },
}

CURRENT_SEASON = "2024-25"


def get_current_season() -> str:
    """Get current season string based on date."""
    now = datetime.now()
    if now.month >= 8:
        return f"{now.year}-{str(now.year + 1)[-2:]}"
    return f"{now.year - 1}-{str(now.year)[-2:]}"


def calculate_power_rating(
    offensive_rating: float,
    defensive_rating: float,
    recent_form: float,
    sos_adjustment: float = 0
) -> float:
    """
    Calculate composite power rating.

    Args:
        offensive_rating: Points scored per 100 possessions (normalized)
        defensive_rating: Points allowed per 100 possessions (normalized)
        recent_form: Recent performance adjustment (-10 to +10)
        sos_adjustment: Strength of schedule adjustment (-5 to +5)

    Returns:
        Power rating on 0-100 scale
    """
    # Net rating (off - def), normalized to ~0 baseline
    net_rating = offensive_rating - defensive_rating

    # Base rating: 50 + net_rating (scaled)
    # Net rating of +10 = 60 rating, -10 = 40 rating
    base_rating = 50 + (net_rating * 1.0)

    # Add recent form (weighted 2x in the model)
    rating = base_rating + (recent_form * 0.5)

    # Add SoS adjustment
    rating += sos_adjustment

    # Clamp to 0-100
    return max(0, min(100, rating))


def calculate_ats_percentage(wins: int, losses: int, pushes: int = 0) -> Optional[float]:
    """Calculate ATS win percentage."""
    total = wins + losses
    if total == 0:
        return None
    return round((wins / total) * 100, 1)


def get_power_ratings(
    db: Session,
    sport: str,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Get power ratings for all teams in a sport.

    Returns teams sorted by power rating descending.
    """
    ratings = db.query(TeamPowerRating).filter(
        TeamPowerRating.sport == sport
    ).order_by(desc(TeamPowerRating.power_rating)).limit(limit).all()

    result = []
    for i, r in enumerate(ratings, 1):
        total_ats = r.ats_wins + r.ats_losses
        ats_pct = calculate_ats_percentage(r.ats_wins, r.ats_losses, r.ats_pushes)

        result.append({
            "rank": i,
            "team_name": r.team_name,
            "team_abbrev": r.team_abbrev,
            "power_rating": round(r.power_rating, 1),
            "offensive_rating": round(r.offensive_rating, 1) if r.offensive_rating else None,
            "defensive_rating": round(r.defensive_rating, 1) if r.defensive_rating else None,
            "net_rating": round(r.net_rating, 1) if r.net_rating else None,
            "home_advantage": r.home_field_advantage,
            "record": f"{r.su_wins}-{r.su_losses}",
            "ats_record": f"{r.ats_wins}-{r.ats_losses}-{r.ats_pushes}",
            "ats_percentage": ats_pct,
            "ats_trend": _get_ats_trend(ats_pct),
            "last_5_ats": r.last_5_ats,
            "last_5_su": r.last_5_su,
            "over_under": f"{r.over_wins}-{r.under_wins}",
            "sos_rating": r.sos_rating,
            "sos_rank": r.sos_rank,
            "last_updated": r.last_updated.isoformat() if r.last_updated else None,
        })

    return result


def _get_ats_trend(ats_pct: Optional[float]) -> str:
    """Get ATS trend indicator."""
    if ats_pct is None:
        return "neutral"
    if ats_pct >= 55:
        return "hot"
    if ats_pct <= 45:
        return "cold"
    return "neutral"


def get_team_power_rating(
    db: Session,
    sport: str,
    team_name: str
) -> Optional[Dict[str, Any]]:
    """Get detailed power rating for a single team."""
    rating = db.query(TeamPowerRating).filter(
        TeamPowerRating.sport == sport,
        func.lower(TeamPowerRating.team_name).contains(team_name.lower())
    ).first()

    if not rating:
        return None

    # Get ATS record details
    ats_record = db.query(ATSRecord).filter(
        ATSRecord.sport == sport,
        func.lower(ATSRecord.team_name).contains(team_name.lower()),
        ATSRecord.season == get_current_season()
    ).first()

    ats_pct = calculate_ats_percentage(rating.ats_wins, rating.ats_losses, rating.ats_pushes)

    response = {
        "team_name": rating.team_name,
        "team_abbrev": rating.team_abbrev,
        "sport": rating.sport,
        "power_rating": round(rating.power_rating, 1),
        "power_rank": rating.power_rank,

        "ratings": {
            "offensive": round(rating.offensive_rating, 1) if rating.offensive_rating else None,
            "defensive": round(rating.defensive_rating, 1) if rating.defensive_rating else None,
            "net": round(rating.net_rating, 1) if rating.net_rating else None,
        },

        "home_field_advantage": rating.home_field_advantage,

        "record": {
            "wins": rating.su_wins,
            "losses": rating.su_losses,
            "display": f"{rating.su_wins}-{rating.su_losses}",
        },

        "ats": {
            "wins": rating.ats_wins,
            "losses": rating.ats_losses,
            "pushes": rating.ats_pushes,
            "percentage": ats_pct,
            "display": f"{rating.ats_wins}-{rating.ats_losses}-{rating.ats_pushes}",
            "trend": _get_ats_trend(ats_pct),
        },

        "over_under": {
            "overs": rating.over_wins,
            "unders": rating.under_wins,
            "display": f"{rating.over_wins}-{rating.under_wins}",
        },

        "recent_form": {
            "last_5_ats": rating.last_5_ats,
            "last_5_su": rating.last_5_su,
            "form_rating": rating.recent_form_rating,
        },

        "strength_of_schedule": {
            "rating": rating.sos_rating,
            "rank": rating.sos_rank,
        },

        "last_updated": rating.last_updated.isoformat() if rating.last_updated else None,
    }

    # Add detailed ATS splits if available
    if ats_record:
        response["ats_splits"] = {
            "home": {
                "record": f"{ats_record.home_ats_wins}-{ats_record.home_ats_losses}-{ats_record.home_ats_pushes}",
                "percentage": calculate_ats_percentage(ats_record.home_ats_wins, ats_record.home_ats_losses),
            },
            "away": {
                "record": f"{ats_record.away_ats_wins}-{ats_record.away_ats_losses}-{ats_record.away_ats_pushes}",
                "percentage": calculate_ats_percentage(ats_record.away_ats_wins, ats_record.away_ats_losses),
            },
            "as_favorite": {
                "record": f"{ats_record.as_favorite_wins}-{ats_record.as_favorite_losses}-{ats_record.as_favorite_pushes}",
                "percentage": calculate_ats_percentage(ats_record.as_favorite_wins, ats_record.as_favorite_losses),
            },
            "as_underdog": {
                "record": f"{ats_record.as_underdog_wins}-{ats_record.as_underdog_losses}-{ats_record.as_underdog_pushes}",
                "percentage": calculate_ats_percentage(ats_record.as_underdog_wins, ats_record.as_underdog_losses),
            },
            "last_10": ats_record.last_10_ats,
            "current_streak": ats_record.current_ats_streak,
        }

    return response


def calculate_spread_prediction(
    db: Session,
    sport: str,
    home_team: str,
    away_team: str
) -> Dict[str, Any]:
    """
    Calculate predicted spread based on power ratings.

    Returns predicted spread and comparison.
    """
    home_rating = db.query(TeamPowerRating).filter(
        TeamPowerRating.sport == sport,
        func.lower(TeamPowerRating.team_name).contains(home_team.lower())
    ).first()

    away_rating = db.query(TeamPowerRating).filter(
        TeamPowerRating.sport == sport,
        func.lower(TeamPowerRating.team_name).contains(away_team.lower())
    ).first()

    if not home_rating or not away_rating:
        return {"error": "Could not find both teams"}

    config = SPORT_CONFIG.get(sport, {"home_advantage": 3.0})

    # Predicted spread = Away rating - Home rating - Home advantage
    # Negative = home favorite, positive = away favorite
    rating_diff = away_rating.power_rating - home_rating.power_rating
    home_advantage = home_rating.home_field_advantage or config["home_advantage"]

    predicted_spread = rating_diff - home_advantage

    return {
        "home_team": {
            "name": home_rating.team_name,
            "power_rating": round(home_rating.power_rating, 1),
            "ats_record": f"{home_rating.ats_wins}-{home_rating.ats_losses}-{home_rating.ats_pushes}",
            "home_advantage": home_advantage,
        },
        "away_team": {
            "name": away_rating.team_name,
            "power_rating": round(away_rating.power_rating, 1),
            "ats_record": f"{away_rating.ats_wins}-{away_rating.ats_losses}-{away_rating.ats_pushes}",
        },
        "rating_difference": round(rating_diff, 1),
        "predicted_spread": round(predicted_spread, 1),
        "predicted_favorite": home_rating.team_name if predicted_spread < 0 else away_rating.team_name,
        "spread_display": f"{home_rating.team_name} {predicted_spread:+.1f}" if predicted_spread != 0 else "PICK",
    }


def update_power_rating(
    db: Session,
    sport: str,
    team_name: str,
    stats: Dict[str, Any]
) -> TeamPowerRating:
    """
    Update or create a team's power rating.

    Args:
        db: Database session
        sport: Sport code
        team_name: Team name
        stats: Dict with offensive_rating, defensive_rating, wins, losses, etc.
    """
    rating = db.query(TeamPowerRating).filter(
        TeamPowerRating.sport == sport,
        TeamPowerRating.team_name == team_name
    ).first()

    if not rating:
        rating = TeamPowerRating(
            sport=sport,
            team_name=team_name,
            team_abbrev=stats.get("team_abbrev", team_name[:3].upper()),
            season=get_current_season()
        )
        db.add(rating)

    # Update ratings
    if "offensive_rating" in stats:
        rating.offensive_rating = stats["offensive_rating"]
    if "defensive_rating" in stats:
        rating.defensive_rating = stats["defensive_rating"]

    # Calculate net rating
    if rating.offensive_rating and rating.defensive_rating:
        rating.net_rating = rating.offensive_rating - rating.defensive_rating

    # Update records
    if "su_wins" in stats:
        rating.su_wins = stats["su_wins"]
    if "su_losses" in stats:
        rating.su_losses = stats["su_losses"]
    if "ats_wins" in stats:
        rating.ats_wins = stats["ats_wins"]
    if "ats_losses" in stats:
        rating.ats_losses = stats["ats_losses"]
    if "ats_pushes" in stats:
        rating.ats_pushes = stats["ats_pushes"]

    # Calculate ATS percentage
    total_ats = rating.ats_wins + rating.ats_losses
    if total_ats > 0:
        rating.ats_percentage = (rating.ats_wins / total_ats) * 100

    # Update O/U
    if "over_wins" in stats:
        rating.over_wins = stats["over_wins"]
    if "under_wins" in stats:
        rating.under_wins = stats["under_wins"]

    # Update form
    if "last_5_ats" in stats:
        rating.last_5_ats = stats["last_5_ats"]
    if "last_5_su" in stats:
        rating.last_5_su = stats["last_5_su"]
    if "recent_form_rating" in stats:
        rating.recent_form_rating = stats["recent_form_rating"]

    # Update SoS
    if "sos_rating" in stats:
        rating.sos_rating = stats["sos_rating"]
    if "sos_rank" in stats:
        rating.sos_rank = stats["sos_rank"]

    # Home advantage
    if "home_field_advantage" in stats:
        rating.home_field_advantage = stats["home_field_advantage"]

    # Calculate composite power rating
    off_rating = rating.offensive_rating or 50
    def_rating = rating.defensive_rating or 50
    form_rating = rating.recent_form_rating or 0
    sos_adj = ((rating.sos_rating or 50) - 50) / 10  # Convert SoS to adjustment

    rating.power_rating = calculate_power_rating(
        off_rating, def_rating, form_rating, sos_adj
    )

    rating.last_updated = datetime.utcnow()

    db.commit()
    db.refresh(rating)

    return rating


def recalculate_all_rankings(db: Session, sport: str):
    """Recalculate power rankings for all teams in a sport."""
    ratings = db.query(TeamPowerRating).filter(
        TeamPowerRating.sport == sport
    ).order_by(desc(TeamPowerRating.power_rating)).all()

    for i, rating in enumerate(ratings, 1):
        rating.power_rank = i

    db.commit()


def seed_power_ratings(db: Session, sport: str) -> int:
    """
    Seed initial power ratings for a sport using sample data.

    Returns number of teams created.
    """
    # Sample NFL teams with approximate ratings
    NFL_TEAMS = [
        {"name": "Kansas City Chiefs", "abbrev": "KC", "off": 58, "def": 52, "hfa": 3.0, "ats": (8, 5, 0)},
        {"name": "San Francisco 49ers", "abbrev": "SF", "off": 57, "def": 55, "hfa": 2.5, "ats": (7, 6, 0)},
        {"name": "Buffalo Bills", "abbrev": "BUF", "off": 59, "def": 50, "hfa": 4.0, "ats": (9, 4, 0)},
        {"name": "Philadelphia Eagles", "abbrev": "PHI", "off": 54, "def": 54, "hfa": 3.5, "ats": (6, 7, 0)},
        {"name": "Dallas Cowboys", "abbrev": "DAL", "off": 52, "def": 48, "hfa": 3.0, "ats": (5, 8, 0)},
        {"name": "Miami Dolphins", "abbrev": "MIA", "off": 56, "def": 46, "hfa": 2.0, "ats": (7, 6, 0)},
        {"name": "Detroit Lions", "abbrev": "DET", "off": 58, "def": 48, "hfa": 3.0, "ats": (10, 3, 0)},
        {"name": "Baltimore Ravens", "abbrev": "BAL", "off": 55, "def": 52, "hfa": 2.5, "ats": (8, 5, 0)},
        {"name": "Cleveland Browns", "abbrev": "CLE", "off": 45, "def": 55, "hfa": 4.0, "ats": (5, 8, 0)},
        {"name": "Green Bay Packers", "abbrev": "GB", "off": 51, "def": 48, "hfa": 4.5, "ats": (7, 6, 0)},
        {"name": "Minnesota Vikings", "abbrev": "MIN", "off": 50, "def": 50, "hfa": 3.0, "ats": (6, 7, 0)},
        {"name": "Chicago Bears", "abbrev": "CHI", "off": 42, "def": 48, "hfa": 2.5, "ats": (4, 9, 0)},
        {"name": "Cincinnati Bengals", "abbrev": "CIN", "off": 53, "def": 47, "hfa": 2.5, "ats": (6, 7, 0)},
        {"name": "Pittsburgh Steelers", "abbrev": "PIT", "off": 46, "def": 52, "hfa": 3.5, "ats": (7, 6, 0)},
        {"name": "Los Angeles Rams", "abbrev": "LAR", "off": 49, "def": 46, "hfa": 1.5, "ats": (6, 7, 0)},
        {"name": "Seattle Seahawks", "abbrev": "SEA", "off": 50, "def": 45, "hfa": 4.0, "ats": (5, 8, 0)},
        {"name": "Denver Broncos", "abbrev": "DEN", "off": 44, "def": 52, "hfa": 3.5, "ats": (6, 7, 0)},
        {"name": "Las Vegas Raiders", "abbrev": "LV", "off": 43, "def": 44, "hfa": 2.0, "ats": (4, 9, 0)},
        {"name": "New York Jets", "abbrev": "NYJ", "off": 42, "def": 53, "hfa": 2.5, "ats": (4, 9, 0)},
        {"name": "New England Patriots", "abbrev": "NE", "off": 38, "def": 48, "hfa": 3.0, "ats": (3, 10, 0)},
        {"name": "Houston Texans", "abbrev": "HOU", "off": 51, "def": 47, "hfa": 2.5, "ats": (8, 5, 0)},
        {"name": "Indianapolis Colts", "abbrev": "IND", "off": 48, "def": 48, "hfa": 2.5, "ats": (5, 8, 0)},
        {"name": "Jacksonville Jaguars", "abbrev": "JAX", "off": 45, "def": 44, "hfa": 2.0, "ats": (4, 9, 0)},
        {"name": "Tennessee Titans", "abbrev": "TEN", "off": 40, "def": 46, "hfa": 2.5, "ats": (4, 9, 0)},
        {"name": "Atlanta Falcons", "abbrev": "ATL", "off": 48, "def": 44, "hfa": 2.0, "ats": (6, 7, 0)},
        {"name": "New Orleans Saints", "abbrev": "NO", "off": 47, "def": 46, "hfa": 3.5, "ats": (5, 8, 0)},
        {"name": "Tampa Bay Buccaneers", "abbrev": "TB", "off": 50, "def": 47, "hfa": 2.0, "ats": (7, 6, 0)},
        {"name": "Carolina Panthers", "abbrev": "CAR", "off": 38, "def": 42, "hfa": 2.0, "ats": (3, 10, 0)},
        {"name": "Arizona Cardinals", "abbrev": "ARI", "off": 46, "def": 43, "hfa": 2.0, "ats": (5, 8, 0)},
        {"name": "Los Angeles Chargers", "abbrev": "LAC", "off": 48, "def": 50, "hfa": 1.5, "ats": (6, 7, 0)},
        {"name": "New York Giants", "abbrev": "NYG", "off": 40, "def": 45, "hfa": 2.5, "ats": (3, 10, 0)},
        {"name": "Washington Commanders", "abbrev": "WAS", "off": 52, "def": 46, "hfa": 2.5, "ats": (8, 5, 0)},
    ]

    NBA_TEAMS = [
        {"name": "Boston Celtics", "abbrev": "BOS", "off": 62, "def": 55, "hfa": 3.5, "ats": (25, 12, 0)},
        {"name": "Oklahoma City Thunder", "abbrev": "OKC", "off": 58, "def": 54, "hfa": 3.0, "ats": (22, 15, 0)},
        {"name": "Cleveland Cavaliers", "abbrev": "CLE", "off": 57, "def": 55, "hfa": 3.0, "ats": (26, 11, 0)},
        {"name": "Denver Nuggets", "abbrev": "DEN", "off": 56, "def": 52, "hfa": 4.0, "ats": (18, 19, 0)},
        {"name": "New York Knicks", "abbrev": "NYK", "off": 54, "def": 54, "hfa": 3.5, "ats": (20, 17, 0)},
        {"name": "Milwaukee Bucks", "abbrev": "MIL", "off": 55, "def": 50, "hfa": 3.0, "ats": (16, 21, 0)},
        {"name": "Phoenix Suns", "abbrev": "PHX", "off": 54, "def": 49, "hfa": 2.5, "ats": (17, 20, 0)},
        {"name": "Golden State Warriors", "abbrev": "GSW", "off": 53, "def": 50, "hfa": 3.0, "ats": (15, 22, 0)},
        {"name": "Los Angeles Lakers", "abbrev": "LAL", "off": 52, "def": 50, "hfa": 2.5, "ats": (18, 19, 0)},
        {"name": "Dallas Mavericks", "abbrev": "DAL", "off": 55, "def": 48, "hfa": 2.5, "ats": (19, 18, 0)},
        {"name": "Minnesota Timberwolves", "abbrev": "MIN", "off": 53, "def": 54, "hfa": 3.0, "ats": (17, 20, 0)},
        {"name": "Memphis Grizzlies", "abbrev": "MEM", "off": 51, "def": 50, "hfa": 3.0, "ats": (16, 21, 0)},
        {"name": "Miami Heat", "abbrev": "MIA", "off": 50, "def": 52, "hfa": 3.0, "ats": (15, 22, 0)},
        {"name": "Indiana Pacers", "abbrev": "IND", "off": 56, "def": 46, "hfa": 2.5, "ats": (18, 19, 0)},
        {"name": "Sacramento Kings", "abbrev": "SAC", "off": 54, "def": 47, "hfa": 2.5, "ats": (16, 21, 0)},
        {"name": "Los Angeles Clippers", "abbrev": "LAC", "off": 50, "def": 51, "hfa": 2.0, "ats": (14, 23, 0)},
    ]

    teams_data = {
        "NFL": NFL_TEAMS,
        "NBA": NBA_TEAMS,
    }

    if sport not in teams_data:
        return 0

    count = 0
    for team in teams_data[sport]:
        # Generate sample last 5 ATS
        import random
        last_5 = "".join(random.choices(["W", "L"], k=5))
        wins_in_5 = last_5.count("W")
        form_rating = (wins_in_5 - 2.5) * 2  # -5 to +5

        stats = {
            "team_abbrev": team["abbrev"],
            "offensive_rating": team["off"],
            "defensive_rating": team["def"],
            "home_field_advantage": team["hfa"],
            "ats_wins": team["ats"][0],
            "ats_losses": team["ats"][1],
            "ats_pushes": team["ats"][2],
            "su_wins": team["ats"][0] + random.randint(-2, 2),
            "su_losses": team["ats"][1] + random.randint(-2, 2),
            "over_wins": random.randint(4, 9),
            "under_wins": random.randint(4, 9),
            "last_5_ats": last_5,
            "last_5_su": "".join(random.choices(["W", "L"], k=5)),
            "recent_form_rating": form_rating,
            "sos_rating": random.randint(40, 60),
            "sos_rank": random.randint(1, 32 if sport == "NFL" else 30),
        }

        update_power_rating(db, sport, team["name"], stats)
        count += 1

    # Recalculate rankings
    recalculate_all_rankings(db, sport)

    return count


def get_top_ats_teams(
    db: Session,
    sport: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Get teams with best ATS records."""
    ratings = db.query(TeamPowerRating).filter(
        TeamPowerRating.sport == sport,
        (TeamPowerRating.ats_wins + TeamPowerRating.ats_losses) >= 5  # Min sample
    ).all()

    # Calculate ATS % and sort
    teams = []
    for r in ratings:
        total = r.ats_wins + r.ats_losses
        if total > 0:
            pct = (r.ats_wins / total) * 100
            teams.append({
                "team_name": r.team_name,
                "team_abbrev": r.team_abbrev,
                "ats_record": f"{r.ats_wins}-{r.ats_losses}-{r.ats_pushes}",
                "ats_percentage": round(pct, 1),
                "power_rating": round(r.power_rating, 1),
                "last_5_ats": r.last_5_ats,
                "trend": _get_ats_trend(pct),
            })

    teams.sort(key=lambda x: x["ats_percentage"], reverse=True)
    return teams[:limit]


def get_worst_ats_teams(
    db: Session,
    sport: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Get teams with worst ATS records (fade candidates)."""
    teams = get_top_ats_teams(db, sport, limit=50)
    teams.sort(key=lambda x: x["ats_percentage"])
    return teams[:limit]


def compare_teams(
    db: Session,
    sport: str,
    team1_name: str,
    team2_name: str
) -> Dict[str, Any]:
    """Compare two teams' power ratings and stats."""
    team1 = get_team_power_rating(db, sport, team1_name)
    team2 = get_team_power_rating(db, sport, team2_name)

    if not team1 or not team2:
        return {"error": "Could not find both teams"}

    prediction = calculate_spread_prediction(db, sport, team1_name, team2_name)

    return {
        "team1": team1,
        "team2": team2,
        "prediction": prediction,
        "rating_edge": round(team1["power_rating"] - team2["power_rating"], 1),
        "home_matchup": {
            "home_team": team1["team_name"],
            "away_team": team2["team_name"],
            "predicted_spread": prediction.get("predicted_spread"),
        }
    }
