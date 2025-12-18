"""
Officials (Referees/Umpires) API Router

Provides endpoints for official tendency analysis and impact calculations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.db import get_db
from app.services import officials

router = APIRouter(prefix="/officials", tags=["officials"])


@router.get("")
def list_officials(
    sport: Optional[str] = Query(None, description="Filter by sport (MLB, NBA, NFL)"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    List all officials, optionally filtered by sport.

    Returns basic info for each official including O/U tendency.
    """
    officials_list = officials.get_all_officials(db, sport=sport, limit=limit)
    return {
        "officials": officials_list,
        "count": len(officials_list),
        "sport_filter": sport
    }


@router.get("/search")
def search_officials(
    q: str = Query(..., min_length=2, description="Search query"),
    sport: Optional[str] = Query(None, description="Filter by sport"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Search for officials by name.

    Case-insensitive partial match search.
    """
    results = officials.search_officials(db, q, sport=sport, limit=limit)
    return {
        "results": results,
        "count": len(results),
        "query": q
    }


@router.get("/leaderboard/over")
def get_over_leaderboard(
    sport: Optional[str] = Query(None, description="Filter by sport"),
    min_games: int = Query(30, ge=1, description="Minimum games officiated"),
    limit: int = Query(15, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Get leaderboard of officials whose games most frequently go OVER.

    Returns officials ranked by over percentage.
    """
    leaderboard = officials.get_best_over_officials(
        db, sport=sport, min_games=min_games, limit=limit
    )
    return {
        "leaderboard": leaderboard,
        "count": len(leaderboard),
        "sport_filter": sport,
        "min_games": min_games,
        "description": "Officials whose games go OVER most frequently"
    }


@router.get("/leaderboard/under")
def get_under_leaderboard(
    sport: Optional[str] = Query(None, description="Filter by sport"),
    min_games: int = Query(30, ge=1, description="Minimum games officiated"),
    limit: int = Query(15, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Get leaderboard of officials whose games most frequently go UNDER.

    Returns officials ranked by under percentage.
    """
    leaderboard = officials.get_best_under_officials(
        db, sport=sport, min_games=min_games, limit=limit
    )
    return {
        "leaderboard": leaderboard,
        "count": len(leaderboard),
        "sport_filter": sport,
        "min_games": min_games,
        "description": "Officials whose games go UNDER most frequently"
    }


@router.get("/leaderboard/home-bias")
def get_home_bias_leaderboard(
    sport: Optional[str] = Query(None, description="Filter by sport"),
    min_games: int = Query(30, ge=1, description="Minimum games officiated"),
    limit: int = Query(15, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Get leaderboard of officials who favor home teams.

    Returns officials ranked by home team cover percentage.
    """
    leaderboard = officials.get_home_biased_officials(
        db, sport=sport, min_games=min_games, limit=limit
    )
    return {
        "leaderboard": leaderboard,
        "count": len(leaderboard),
        "sport_filter": sport,
        "min_games": min_games,
        "description": "Officials who favor home teams (by ATS record)"
    }


@router.get("/{official_id}")
def get_official(
    official_id: int,
    db: Session = Depends(get_db)
):
    """
    Get official details with all tendencies.
    """
    official = officials.get_official_by_id(db, official_id)
    if not official:
        raise HTTPException(status_code=404, detail="Official not found")
    return official


@router.get("/{official_id}/tendencies")
def get_official_tendencies(
    official_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed tendency breakdown for an official.

    Returns career stats, recent trends, and sport-specific analysis.
    """
    tendencies = officials.get_official_tendencies(db, official_id)
    if "error" in tendencies:
        raise HTTPException(status_code=404, detail=tendencies["error"])
    return tendencies


@router.get("/{official_id}/impact")
def get_official_impact(
    official_id: int,
    total_line: Optional[float] = Query(None, description="Game total line"),
    db: Session = Depends(get_db)
):
    """
    Calculate official's expected impact on a game.

    Returns adjustment recommendations for O/U.
    """
    game_context = {}
    if total_line:
        game_context["total_line"] = total_line

    impact = officials.get_official_impact(db, official_id, game_context)
    if "error" in impact:
        raise HTTPException(status_code=404, detail=impact["error"])
    return impact


@router.get("/{official_id}/history")
def get_official_history(
    official_id: int,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get recent game history for an official.

    Returns recent games with scores, O/U results, and stats.
    """
    # First verify official exists
    official = officials.get_official_by_id(db, official_id)
    if not official:
        raise HTTPException(status_code=404, detail="Official not found")

    history = officials.get_official_game_history(db, official_id, limit=limit)
    return {
        "official_id": official_id,
        "official_name": official["name"],
        "games": history,
        "count": len(history)
    }


@router.get("/game/{game_id}")
def get_game_official(
    game_id: int,
    db: Session = Depends(get_db)
):
    """
    Get assigned official for a specific game.

    Note: This endpoint returns data if official assignment is known.
    Official assignments are typically announced 1-3 days before games.
    """
    # This would need to be populated from external sources
    # For now, return a placeholder response
    return {
        "game_id": game_id,
        "official": None,
        "message": "Official assignment not yet available. Assignments typically announced 1-3 days before game."
    }


@router.get("/by-name/{name}")
def get_official_by_name(
    name: str,
    sport: Optional[str] = Query(None, description="Filter by sport"),
    db: Session = Depends(get_db)
):
    """
    Get official by name (case-insensitive search).
    """
    official = officials.get_official_by_name(db, name, sport=sport)
    if not official:
        raise HTTPException(status_code=404, detail=f"No official found matching '{name}'")
    return official
