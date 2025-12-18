"""
Historical Head-to-Head (H2H) API Endpoints
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import h2h as h2h_service


router = APIRouter(prefix="/h2h", tags=["Head-to-Head"])


class H2HGameCreate(BaseModel):
    """Schema for creating a new H2H game record"""
    sport: str = Field(..., description="Sport (nfl, nba, mlb, etc.)")
    team1_name: str = Field(..., description="First team name")
    team2_name: str = Field(..., description="Second team name")
    team1_score: int = Field(..., ge=0, description="First team score")
    team2_score: int = Field(..., ge=0, description="Second team score")
    game_date: datetime = Field(..., description="Date of the game")
    season: Optional[str] = Field(None, description="Season identifier")
    spread: Optional[float] = Field(None, description="Point spread (negative = team1 favorite)")
    total_line: Optional[float] = Field(None, description="Over/Under total line")
    venue: Optional[str] = Field(None, description="Game venue")
    is_neutral_site: bool = Field(False, description="Was game at neutral site")
    is_playoff: bool = Field(False, description="Was this a playoff game")
    game_type: str = Field("regular", description="Game type: regular, playoff, championship")


class H2HGameResponse(BaseModel):
    """Schema for H2H game response"""
    id: int
    sport: str
    team1_name: str
    team2_name: str
    team1_score: int
    team2_score: int
    game_date: datetime
    season: Optional[str]
    spread: Optional[float]
    spread_result: Optional[str]
    total_line: Optional[float]
    total_result: Optional[str]
    venue: Optional[str]
    is_neutral_site: bool
    is_playoff: bool
    game_type: Optional[str]

    class Config:
        from_attributes = True


@router.get("/{sport}/{team1}/{team2}")
async def get_h2h_stats(
    sport: str,
    team1: str,
    team2: str,
    limit: int = Query(20, ge=1, le=100, description="Number of games to analyze"),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive head-to-head statistics between two teams.

    Returns detailed matchup history including:
    - Overall series record
    - ATS (against the spread) performance
    - Over/Under trends
    - Scoring averages
    - Last 5 meetings
    - Home/Away splits
    """
    try:
        stats = h2h_service.calculate_h2h_stats(db, sport, team1, team2, limit)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{sport}/{team1}/{team2}/games")
async def get_h2h_games(
    sport: str,
    team1: str,
    team2: str,
    limit: int = Query(20, ge=1, le=100),
    include_playoffs: bool = Query(True, description="Include playoff games"),
    db: Session = Depends(get_db)
):
    """
    Get raw historical games between two teams.
    """
    try:
        games = h2h_service.get_h2h_games(
            db, sport, team1, team2, limit, include_playoffs
        )
        return {
            "team1": team1,
            "team2": team2,
            "sport": sport,
            "total_games": len(games),
            "games": [H2HGameResponse.model_validate(g) for g in games]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{sport}/{team1}/{team2}/summary")
async def get_h2h_summary(
    sport: str,
    team1: str,
    team2: str,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Get a compact H2H summary suitable for game cards.

    Perfect for displaying quick matchup context on game previews.
    """
    try:
        summary = h2h_service.get_h2h_summary(db, sport, team1, team2, limit)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{sport}/game")
async def add_h2h_game(
    sport: str,
    game: H2HGameCreate,
    db: Session = Depends(get_db)
):
    """
    Add a historical H2H game record.

    Spread result and total result are automatically calculated.
    """
    try:
        new_game = h2h_service.add_h2h_game(
            db=db,
            sport=sport,
            team1_name=game.team1_name,
            team2_name=game.team2_name,
            team1_score=game.team1_score,
            team2_score=game.team2_score,
            game_date=game.game_date,
            season=game.season,
            spread=game.spread,
            total_line=game.total_line,
            venue=game.venue,
            is_neutral_site=game.is_neutral_site,
            is_playoff=game.is_playoff,
            game_type=game.game_type
        )
        return H2HGameResponse.model_validate(new_game)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{sport}/seed")
async def seed_h2h_data(
    sport: str,
    db: Session = Depends(get_db)
):
    """
    Seed sample H2H data for demonstration purposes.

    Populates classic rivalry matchups with realistic historical data.
    """
    try:
        result = h2h_service.seed_h2h_data(db, sport)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{sport}/rivalries")
async def get_rivalry_rankings(
    sport: str,
    min_games: int = Query(3, ge=1, description="Minimum games to qualify"),
    db: Session = Depends(get_db)
):
    """
    Get rankings of rivalries by competitiveness.

    Score based on:
    - Balance of series record
    - Percentage of close games
    - Number of meetings
    """
    try:
        rankings = h2h_service.get_rivalry_rankings(db, sport, min_games)
        return {
            "sport": sport,
            "min_games": min_games,
            "rivalries": rankings
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{sport}/team/{team}/trends")
async def get_team_h2h_trends(
    sport: str,
    team: str,
    db: Session = Depends(get_db)
):
    """
    Get recent H2H trends for a specific team against all opponents.

    Useful for understanding a team's recent history in rivalry matchups.
    """
    try:
        trends = h2h_service.get_recent_h2h_trends(db, sport, team)
        return trends
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
