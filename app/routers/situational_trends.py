"""
Situational Trends API Endpoints
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import situational_trends as trends_service


router = APIRouter(prefix="/situational-trends", tags=["Situational Trends"])


class GameAnalysisRequest(BaseModel):
    """Schema for analyzing game situations"""
    home_team: str = Field(..., description="Home team name")
    away_team: str = Field(..., description="Away team name")
    spread: float = Field(..., description="Point spread (negative = home favorite)")
    total: float = Field(..., description="Over/Under total")
    is_primetime: bool = Field(False, description="Is this a primetime game")
    is_division: bool = Field(False, description="Is this a division game")
    home_days_rest: int = Field(7, ge=0, description="Home team days of rest")
    away_days_rest: int = Field(7, ge=0, description="Away team days of rest")
    home_last_result: Optional[str] = Field(None, description="Home team last result: win, loss, blowout_win, close_loss")
    away_last_result: Optional[str] = Field(None, description="Away team last result")
    season: Optional[str] = Field(None, description="Season to query")


@router.get("/{sport}/team/{team_name}")
async def get_team_trends(
    sport: str,
    team_name: str,
    season: Optional[str] = Query(None, description="Season to filter"),
    min_games: int = Query(3, ge=1, description="Minimum games to qualify"),
    db: Session = Depends(get_db)
):
    """
    Get all situational trends for a specific team.

    Returns ATS records, O/U records, and edges for each situation type.
    """
    try:
        trends = trends_service.get_team_trends(db, sport, team_name, season, min_games)
        return {
            "team": team_name,
            "sport": sport,
            "season": season or "all",
            "trends": trends,
            "count": len(trends)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{sport}/profitable")
async def get_profitable_situations(
    sport: str,
    min_games: int = Query(5, ge=1, description="Minimum games to qualify"),
    min_cover_pct: float = Query(55.0, ge=50, le=100, description="Minimum cover percentage"),
    season: Optional[str] = Query(None, description="Season to filter"),
    db: Session = Depends(get_db)
):
    """
    Find profitable betting situations across all teams.

    Returns situations with cover percentage above the threshold.
    """
    try:
        situations = trends_service.get_profitable_situations(
            db, sport, min_games, min_cover_pct, season
        )
        return {
            "sport": sport,
            "min_games": min_games,
            "min_cover_pct": min_cover_pct,
            "situations": situations,
            "count": len(situations)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{sport}/fade")
async def get_fade_situations(
    sport: str,
    min_games: int = Query(5, ge=1, description="Minimum games to qualify"),
    max_cover_pct: float = Query(45.0, ge=0, le=50, description="Maximum cover percentage (to fade)"),
    season: Optional[str] = Query(None, description="Season to filter"),
    db: Session = Depends(get_db)
):
    """
    Find situations to fade (bet against).

    Returns situations with cover percentage below the threshold.
    """
    try:
        situations = trends_service.get_fade_situations(
            db, sport, min_games, max_cover_pct, season
        )
        return {
            "sport": sport,
            "min_games": min_games,
            "max_cover_pct": max_cover_pct,
            "fade_situations": situations,
            "count": len(situations)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{sport}/analyze")
async def analyze_game_situations(
    sport: str,
    request: GameAnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    Analyze applicable situational trends for a specific matchup.

    Identifies which situations apply to each team and calculates
    combined edges to determine betting lean.
    """
    try:
        analysis = trends_service.analyze_game_situations(
            db=db,
            sport=sport,
            home_team=request.home_team,
            away_team=request.away_team,
            spread=request.spread,
            total=request.total,
            is_primetime=request.is_primetime,
            is_division=request.is_division,
            home_days_rest=request.home_days_rest,
            away_days_rest=request.away_days_rest,
            home_last_result=request.home_last_result,
            away_last_result=request.away_last_result,
            season=request.season
        )
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{sport}/seed")
async def seed_situational_trends(
    sport: str,
    db: Session = Depends(get_db)
):
    """
    Seed sample situational trends data for demonstration.
    """
    try:
        result = trends_service.seed_situational_trends(db, sport)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/situations")
async def get_all_situations():
    """
    Get list of all supported situation types.

    Returns situation codes and their display names.
    """
    situations = trends_service.get_all_situations()
    return {
        "situations": situations,
        "count": len(situations)
    }
