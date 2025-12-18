"""
Power Ratings API Router

Endpoints for team power ratings and ATS analysis.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from app.db import get_db
from app.services import power_ratings

router = APIRouter(prefix="/power-ratings", tags=["power-ratings"])


class PowerRatingResponse(BaseModel):
    rank: int
    team_name: str
    team_abbrev: Optional[str]
    power_rating: float
    offensive_rating: Optional[float]
    defensive_rating: Optional[float]
    net_rating: Optional[float]
    home_advantage: Optional[float]
    record: str
    ats_record: str
    ats_percentage: Optional[float]
    ats_trend: str
    last_5_ats: Optional[str]
    last_5_su: Optional[str]
    over_under: str
    sos_rating: Optional[float]
    sos_rank: Optional[int]
    last_updated: Optional[str]


class SpreadPredictionResponse(BaseModel):
    home_team: dict
    away_team: dict
    rating_difference: float
    predicted_spread: float
    predicted_favorite: str
    spread_display: str


@router.get("/{sport}")
def get_power_ratings(
    sport: str,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get power ratings for all teams in a sport.

    Returns teams ranked by power rating with ATS records.

    Supported sports: NFL, NBA, MLB, NHL, NCAA_FOOTBALL, NCAA_BASKETBALL
    """
    sport = sport.upper()
    ratings = power_ratings.get_power_ratings(db, sport, limit=limit)

    if not ratings:
        # Try to seed data if none exists
        count = power_ratings.seed_power_ratings(db, sport)
        if count > 0:
            ratings = power_ratings.get_power_ratings(db, sport, limit=limit)
        else:
            return {
                "sport": sport,
                "ratings": [],
                "count": 0,
                "message": f"No power ratings available for {sport}"
            }

    return {
        "sport": sport,
        "ratings": ratings,
        "count": len(ratings),
        "season": power_ratings.get_current_season()
    }


@router.get("/{sport}/{team}")
def get_team_power_rating(
    sport: str,
    team: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed power rating for a single team.

    Includes ATS splits by home/away and favorite/underdog.
    """
    sport = sport.upper()
    rating = power_ratings.get_team_power_rating(db, sport, team)

    if not rating:
        raise HTTPException(status_code=404, detail=f"Team '{team}' not found in {sport}")

    return rating


@router.get("/{sport}/predict/spread")
def predict_spread(
    sport: str,
    home_team: str = Query(..., description="Home team name"),
    away_team: str = Query(..., description="Away team name"),
    db: Session = Depends(get_db)
):
    """
    Calculate predicted spread based on power ratings.

    Takes home team advantage into account.
    """
    sport = sport.upper()
    prediction = power_ratings.calculate_spread_prediction(db, sport, home_team, away_team)

    if "error" in prediction:
        raise HTTPException(status_code=404, detail=prediction["error"])

    return prediction


@router.get("/{sport}/compare")
def compare_teams(
    sport: str,
    team1: str = Query(..., description="First team name"),
    team2: str = Query(..., description="Second team name"),
    db: Session = Depends(get_db)
):
    """
    Compare two teams' power ratings and stats.

    Returns head-to-head comparison with predicted spread.
    """
    sport = sport.upper()
    comparison = power_ratings.compare_teams(db, sport, team1, team2)

    if "error" in comparison:
        raise HTTPException(status_code=404, detail=comparison["error"])

    return comparison


@router.get("/{sport}/ats/best")
def get_best_ats_teams(
    sport: str,
    limit: int = Query(10, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """
    Get teams with best ATS records.

    Returns teams ranked by ATS win percentage.
    """
    sport = sport.upper()
    teams = power_ratings.get_top_ats_teams(db, sport, limit=limit)

    return {
        "sport": sport,
        "category": "best_ats",
        "teams": teams,
        "count": len(teams),
        "description": f"Top {len(teams)} teams by ATS percentage"
    }


@router.get("/{sport}/ats/worst")
def get_worst_ats_teams(
    sport: str,
    limit: int = Query(10, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """
    Get teams with worst ATS records (fade candidates).

    Returns teams ranked by lowest ATS win percentage.
    """
    sport = sport.upper()
    teams = power_ratings.get_worst_ats_teams(db, sport, limit=limit)

    return {
        "sport": sport,
        "category": "worst_ats",
        "teams": teams,
        "count": len(teams),
        "description": f"Bottom {len(teams)} teams by ATS percentage (fade candidates)"
    }


@router.post("/{sport}/seed")
def seed_power_ratings(
    sport: str,
    db: Session = Depends(get_db)
):
    """
    Seed initial power ratings data for a sport.

    Creates sample data for testing.
    """
    sport = sport.upper()
    count = power_ratings.seed_power_ratings(db, sport)

    if count == 0:
        raise HTTPException(
            status_code=400,
            detail=f"Could not seed data for {sport}. Sport may not be supported."
        )

    return {
        "sport": sport,
        "teams_created": count,
        "message": f"Successfully seeded {count} teams for {sport}"
    }


@router.post("/{sport}/recalculate")
def recalculate_rankings(
    sport: str,
    db: Session = Depends(get_db)
):
    """
    Recalculate power rankings for all teams in a sport.
    """
    sport = sport.upper()
    power_ratings.recalculate_all_rankings(db, sport)

    return {
        "sport": sport,
        "message": f"Rankings recalculated for {sport}"
    }
