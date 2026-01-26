"""
Pinnacle Sharp Lines Router

Endpoints for accessing Pinnacle (sharp) lines and market efficiency analysis.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List

from app.db import get_db
from app.services.pinnacle import (
    get_pinnacle_lines,
    compare_to_pinnacle,
    get_pinnacle_closing_line,
    calculate_clv_vs_pinnacle,
    get_market_efficiency,
    store_pinnacle_odds,
    get_pinnacle_line_history,
    detect_sharp_line_movement,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/pinnacle", tags=["Pinnacle Sharp Lines"])


@router.get("/lines/{sport}")
async def get_sharp_lines(
    sport: str,
):
    """
    Get current Pinnacle (sharp) lines for a sport.

    Pinnacle is the market-setting sportsbook - their lines represent
    the sharpest odds available and the closest to true probabilities.

    **Supported Sports**: NFL, NBA, MLB, NHL, NCAA_FOOTBALL, NCAA_BASKETBALL

    Returns markets with vig calculations and no-vig fair odds.
    """
    sport_upper = sport.upper()
    valid_sports = ["NFL", "NBA", "MLB", "NHL", "NCAA_FOOTBALL", "NCAA_BASKETBALL", "SOCCER"]

    if sport_upper not in valid_sports:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sport. Supported: {', '.join(valid_sports)}"
        )

    lines = await get_pinnacle_lines(sport_upper)

    return {
        "sport": sport_upper,
        "count": len(lines),
        "games": lines,
        "note": "Pinnacle lines represent the sharpest market"
    }


@router.get("/compare/{sport}/{sportsbook}")
async def compare_sportsbook_to_pinnacle(
    sport: str,
    sportsbook: str,
    db: Session = Depends(get_db),
):
    """
    Compare a sportsbook's lines to Pinnacle.

    Finds value opportunities where the target sportsbook offers
    better odds than Pinnacle (the sharp line).

    A positive edge vs Pinnacle indicates potential value.

    **Example**: `/pinnacle/compare/NBA/DraftKings`
    """
    sport_upper = sport.upper()

    opportunities = await compare_to_pinnacle(sport_upper, sportsbook, db)

    return {
        "sport": sport_upper,
        "vs_sportsbook": sportsbook,
        "value_opportunities": len(opportunities),
        "opportunities": opportunities,
        "note": "Opportunities sorted by edge vs Pinnacle (highest first)"
    }


@router.get("/closing-line/{game_id}")
def get_game_closing_line(
    game_id: int,
    market_type: str = Query("h2h", description="Market type (h2h, spreads, totals)"),
    db: Session = Depends(get_db),
):
    """
    Get the Pinnacle closing line for a game.

    The closing line is the final line before game start.
    This is the gold standard for CLV (Closing Line Value) calculation.
    """
    closing = get_pinnacle_closing_line(db, game_id, market_type)

    if not closing:
        raise HTTPException(
            status_code=404,
            detail="No Pinnacle closing line found for this game"
        )

    return {
        "game_id": game_id,
        "market_type": market_type,
        "closing_line": closing
    }


@router.post("/clv/calculate")
def calculate_clv_endpoint(
    bet_odds: int = Query(..., description="Your bet odds (American format, e.g., +150)"),
    pinnacle_closing: int = Query(..., description="Pinnacle closing odds"),
):
    """
    Calculate CLV (Closing Line Value) against Pinnacle.

    CLV measures how good your bet odds were compared to the closing line.
    Positive CLV = you got better odds than the market closed at.

    Consistently beating Pinnacle's closing line is the hallmark of sharp betting.

    **Example**:
    - You bet at +155, Pinnacle closed at +140
    - Positive CLV = you had value
    """
    result = calculate_clv_vs_pinnacle(bet_odds, pinnacle_closing)

    if result["is_positive_clv"]:
        result["interpretation"] = f"You beat the closing line by {result['clv_percentage']:.2f}%"
    else:
        result["interpretation"] = f"The line moved against you by {abs(result['clv_percentage']):.2f}%"

    return result


@router.get("/market-efficiency/{game_id}")
def analyze_market_efficiency(
    game_id: int,
    market_type: str = Query("h2h", description="Market type"),
    db: Session = Depends(get_db),
):
    """
    Analyze market efficiency for a game.

    Compares all sportsbooks to Pinnacle (the benchmark).

    Returns:
    - Deviation from Pinnacle for each book
    - Overall market efficiency rating
    - Value opportunities (books with better odds than Pinnacle)
    """
    analysis = get_market_efficiency(db, game_id, market_type)

    if "error" in analysis:
        raise HTTPException(status_code=404, detail=analysis["error"])

    return {
        "game_id": game_id,
        "market_type": market_type,
        "analysis": analysis
    }


@router.post("/refresh/{sport}")
async def refresh_pinnacle_odds(
    sport: str,
    db: Session = Depends(get_db),
):
    """
    Fetch and store latest Pinnacle odds.

    Creates snapshots for CLV tracking and line movement analysis.
    Should be called periodically (every 5-15 minutes for active games).
    """
    sport_upper = sport.upper()

    result = await store_pinnacle_odds(db, sport_upper)

    return {
        "status": "success",
        "sport": sport_upper,
        **result
    }


@router.get("/line-history/{game_id}")
def get_line_history(
    game_id: int,
    market_type: str = Query("h2h", description="Market type"),
    db: Session = Depends(get_db),
):
    """
    Get Pinnacle line movement history for a game.

    Shows how the sharp line has moved over time.
    Useful for understanding where sharp money has been bet.
    """
    history = get_pinnacle_line_history(db, game_id, market_type)

    if not history:
        raise HTTPException(
            status_code=404,
            detail="No Pinnacle line history found for this game"
        )

    return {
        "game_id": game_id,
        "market_type": market_type,
        "snapshots": len(history),
        "history": history
    }


@router.get("/sharp-movement/{sport}")
def get_sharp_movements(
    sport: str,
    threshold: int = Query(10, description="Minimum movement in cents (default: 10)"),
    db: Session = Depends(get_db),
):
    """
    Detect significant Pinnacle line movements.

    Sharp money causes Pinnacle to move their lines. Large movements
    (10+ cents) typically indicate professional betting action.

    **Use case**: Identify games where sharps are betting heavily.
    """
    sport_upper = sport.upper()

    movements = detect_sharp_line_movement(db, sport_upper, threshold)

    return {
        "sport": sport_upper,
        "threshold_cents": threshold,
        "significant_moves": len(movements),
        "movements": movements,
        "note": "Large movements suggest sharp action"
    }


@router.get("/summary/{sport}")
async def get_pinnacle_summary(
    sport: str,
    db: Session = Depends(get_db),
):
    """
    Get a summary of Pinnacle market data for a sport.

    Includes:
    - Number of games with Pinnacle lines
    - Average vig
    - Recent sharp movements
    """
    sport_upper = sport.upper()

    lines = await get_pinnacle_lines(sport_upper)
    movements = detect_sharp_line_movement(db, sport_upper, threshold_cents=10)

    # Calculate average vig
    vigs = []
    for game in lines:
        for market_name, market_data in game.get("markets", {}).items():
            if "vig" in market_data:
                vigs.append(market_data["vig"])

    avg_vig = sum(vigs) / len(vigs) if vigs else None

    return {
        "sport": sport_upper,
        "games_with_pinnacle": len(lines),
        "average_vig": round(avg_vig, 2) if avg_vig else None,
        "vig_description": "Pinnacle typically has <2.5% vig (very competitive)",
        "sharp_movements_24h": len(movements),
        "top_movements": movements[:5] if movements else [],
    }
