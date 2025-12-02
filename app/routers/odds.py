from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.db import get_db
from app.services.odds_api import (
    is_odds_api_configured, fetch_and_store_odds,
    get_line_movement, detect_significant_movement
)
from app.config import SUPPORTED_SPORTS

router = APIRouter(prefix="/odds", tags=["odds"])


class OddsStatusResponse(BaseModel):
    configured: bool
    message: str


class RefreshResponse(BaseModel):
    sport: str
    games_updated: int


@router.get("/status", response_model=OddsStatusResponse)
def get_odds_status():
    configured = is_odds_api_configured()
    return OddsStatusResponse(
        configured=configured,
        message="The Odds API is configured and ready" if configured else "THE_ODDS_API_KEY not configured"
    )


@router.post("/refresh/{sport}", response_model=RefreshResponse)
async def refresh_odds(
    sport: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    if sport not in SUPPORTED_SPORTS:
        raise HTTPException(status_code=400, detail=f"Unsupported sport: {sport}")
    
    if not is_odds_api_configured():
        raise HTTPException(status_code=503, detail="Odds API not configured")
    
    count = await fetch_and_store_odds(db, sport)
    
    return RefreshResponse(sport=sport, games_updated=count)


@router.post("/refresh-all")
async def refresh_all_odds(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    if not is_odds_api_configured():
        raise HTTPException(status_code=503, detail="Odds API not configured")
    
    results = {}
    for sport in ["NFL", "NBA", "MLB", "NHL"]:
        count = await fetch_and_store_odds(db, sport)
        results[sport] = count
    
    return {"results": results}


@router.get("/movement/{game_id}")
def get_movement(
    game_id: int,
    market_type: str = "h2h",
    sportsbook: Optional[str] = None,
    db: Session = Depends(get_db)
):
    movement = get_line_movement(db, game_id, market_type, sportsbook)
    return {"game_id": game_id, "movement": movement}


@router.get("/alerts/{game_id}")
def get_movement_alerts(
    game_id: int,
    threshold: int = 20,
    db: Session = Depends(get_db)
):
    significant = detect_significant_movement(db, game_id, threshold)
    return {
        "game_id": game_id,
        "threshold": threshold,
        "significant_movements": significant
    }
