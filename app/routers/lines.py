"""
Line Movement API Router

Provides endpoints for line movement analysis, steam moves, and sharp money detection.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.db import get_db
from app.services import line_movement

router = APIRouter(prefix="/lines", tags=["lines"])


class CLVRequest(BaseModel):
    bet_line: float
    market_type: str = "spread"


@router.get("/game/{game_id}")
def get_game_lines(
    game_id: int,
    db: Session = Depends(get_db)
):
    """
    Get current lines from all books for a game.

    Returns the latest line value from each tracked sportsbook.
    """
    history = line_movement.get_line_history(db, game_id)

    # Group by sportsbook, get latest for each
    latest_by_book = {}
    for entry in history:
        book = entry["sportsbook"]
        if book not in latest_by_book:
            latest_by_book[book] = entry

    return {
        "game_id": game_id,
        "lines": list(latest_by_book.values()),
        "book_count": len(latest_by_book)
    }


@router.get("/game/{game_id}/history")
def get_line_history(
    game_id: int,
    market_type: Optional[str] = Query(None, description="Filter by market type"),
    sportsbook: Optional[str] = Query(None, description="Filter by sportsbook"),
    db: Session = Depends(get_db)
):
    """
    Get full line movement history for a game.

    Returns chronological list of all line changes.
    """
    history = line_movement.get_line_history(
        db, game_id, market_type=market_type, sportsbook=sportsbook
    )

    return {
        "game_id": game_id,
        "history": history,
        "count": len(history),
        "filters": {
            "market_type": market_type,
            "sportsbook": sportsbook
        }
    }


@router.get("/game/{game_id}/analysis")
def get_line_analysis(
    game_id: int,
    market_type: str = Query("spread", description="Market type to analyze"),
    public_bet_pct: Optional[float] = Query(None, description="Public betting percentage (0-100)"),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive line movement analysis for a game.

    Returns movement data, alerts (RLM, steam, sharp), and recommendations.

    Response includes:
    - Opening and current lines
    - Total movement and direction
    - Alerts for reverse line movement, steam moves, sharp book action
    - Betting recommendation based on indicators
    """
    analysis = line_movement.get_movement_analysis(
        db, game_id, market_type=market_type, public_bet_pct=public_bet_pct
    )

    return analysis


@router.get("/game/{game_id}/movement")
def get_total_movement(
    game_id: int,
    market_type: str = Query("spread", description="Market type"),
    db: Session = Depends(get_db)
):
    """
    Calculate total line movement from opening to current.
    """
    movement = line_movement.calculate_total_movement(db, game_id, market_type)
    return movement


@router.get("/alerts")
def get_movement_alerts(
    sport: Optional[str] = Query(None, description="Filter by sport"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type: steam, rlm, sharp"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get games with significant line movement alerts.

    Returns games where steam moves, reverse line movement, or
    sharp book action has been detected.
    """
    alerts = line_movement.get_games_with_alerts(
        db, sport=sport, alert_type=alert_type, limit=limit
    )

    return {
        "alerts": alerts,
        "count": len(alerts),
        "filters": {
            "sport": sport,
            "alert_type": alert_type
        }
    }


@router.get("/steam-moves")
def get_steam_moves(
    sport: Optional[str] = Query(None, description="Filter by sport"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get recent steam moves detected.

    Steam moves are rapid, coordinated line movements across multiple
    sportsbooks, indicating sharp/syndicate action.
    """
    alerts = line_movement.get_games_with_alerts(
        db, sport=sport, alert_type="steam", limit=limit
    )

    return {
        "steam_moves": alerts,
        "count": len(alerts),
        "description": "Rapid coordinated line movement across multiple books",
        "implication": "Strong indicator of sharp money - consider following"
    }


@router.get("/reverse-movement")
def get_reverse_line_movement(
    sport: Optional[str] = Query(None, description="Filter by sport"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get games with reverse line movement.

    RLM occurs when lines move opposite to public betting percentage.
    E.g., 75% on Team A but line moves toward Team B = sharp money on B.
    """
    alerts = line_movement.get_games_with_alerts(
        db, sport=sport, alert_type="rlm", limit=limit
    )

    return {
        "rlm_games": alerts,
        "count": len(alerts),
        "description": "Line moved opposite to public betting percentage",
        "implication": "Sharp money betting against the public"
    }


@router.get("/sharp-action")
def get_sharp_action(
    sport: Optional[str] = Query(None, description="Filter by sport"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get games with sharp money indicators.

    Includes games where sharp books (Pinnacle, Circa) moved first,
    or where multiple sharp indicators are present.
    """
    alerts = line_movement.get_games_with_alerts(
        db, sport=sport, alert_type="sharp", limit=limit
    )

    return {
        "sharp_action": alerts,
        "count": len(alerts),
        "sharp_books": ["Pinnacle", "Circa", "Betcris", "Bookmaker"],
        "description": "Sharp/limit books moved first",
        "implication": "Professional money - market will likely follow"
    }


@router.get("/game/{game_id}/rlm")
def check_reverse_line_movement(
    game_id: int,
    market_type: str = Query("spread", description="Market type"),
    public_bet_pct: Optional[float] = Query(None, description="Public betting % (0-100)"),
    db: Session = Depends(get_db)
):
    """
    Check for reverse line movement on a specific game.
    """
    rlm = line_movement.detect_reverse_line_movement(
        db, game_id, public_bet_pct, market_type
    )
    return rlm


@router.get("/game/{game_id}/steam")
def check_steam_move(
    game_id: int,
    market_type: str = Query("spread", description="Market type"),
    db: Session = Depends(get_db)
):
    """
    Check for steam move on a specific game.
    """
    steam = line_movement.detect_steam_move(db, game_id, market_type)
    return steam


@router.get("/game/{game_id}/sharp")
def check_sharp_book_movement(
    game_id: int,
    market_type: str = Query("spread", description="Market type"),
    db: Session = Depends(get_db)
):
    """
    Check sharp book movement analysis for a specific game.
    """
    sharp = line_movement.get_sharp_book_movement(db, game_id, market_type)
    return sharp


@router.post("/game/{game_id}/clv")
def calculate_clv_potential(
    game_id: int,
    request: CLVRequest,
    db: Session = Depends(get_db)
):
    """
    Calculate closing line value potential.

    CLV is the difference between your bet line and the projected closing line.
    Positive CLV indicates value even if the bet loses.
    """
    clv = line_movement.calculate_clv_potential(
        db, game_id, request.bet_line, request.market_type
    )
    return clv


@router.get("/game/{game_id}/clv")
def get_clv_potential(
    game_id: int,
    bet_line: float = Query(..., description="Line at which you would bet"),
    market_type: str = Query("spread", description="Market type"),
    db: Session = Depends(get_db)
):
    """
    Calculate closing line value potential (GET version).
    """
    clv = line_movement.calculate_clv_potential(db, game_id, bet_line, market_type)
    return clv
