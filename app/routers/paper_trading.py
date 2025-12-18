"""
Paper Trading API Router

Virtual bankroll and bet tracking for strategy validation.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

from app.db import get_db
from app.services import paper_trading

router = APIRouter(prefix="/paper-trading", tags=["paper-trading"])


class PlaceBetRequest(BaseModel):
    sport: str = Field(..., description="Sport code (NFL, NBA, etc.)")
    bet_type: str = Field(..., description="Type: spread, moneyline, total")
    selection: str = Field(..., description="Team name or over/under")
    odds: int = Field(..., description="American odds (-110, +150)")
    stake: float = Field(..., gt=0, description="Amount to wager")
    game_id: Optional[str] = Field(None, description="External game ID")
    game_description: Optional[str] = Field(None, description="Game description")
    line_value: Optional[float] = Field(None, description="Spread/total number")
    game_date: Optional[datetime] = Field(None, description="Game date/time")
    edge_at_placement: Optional[float] = Field(None, description="EdgeBet's edge %")
    notes: Optional[str] = Field(None, description="Notes")


class SettleBetRequest(BaseModel):
    result: str = Field(..., pattern="^(won|lost|push)$", description="Outcome")
    result_score: Optional[str] = Field(None, description="Final score")
    closing_line_value: Optional[float] = Field(None, description="Closing line")


class BankrollResponse(BaseModel):
    bankroll_id: int
    starting_balance: float
    current_balance: float
    high_water_mark: float
    low_water_mark: float
    total_profit_loss: float
    total_wagered: float
    roi_percentage: float
    win_percentage: float
    units_won: float
    stats: dict
    streaks: dict
    created_at: Optional[str]
    last_updated: Optional[str]


@router.get("/bankroll", response_model=BankrollResponse)
def get_bankroll(db: Session = Depends(get_db)):
    """
    Get current bankroll status and performance stats.

    Returns balance, ROI, win rate, and other key metrics.
    """
    return paper_trading.get_bankroll_status(db)


@router.post("/place")
def place_bet(
    request: PlaceBetRequest,
    db: Session = Depends(get_db)
):
    """
    Place a new paper trade.

    Deducts stake from virtual bankroll and creates pending bet.
    """
    result = paper_trading.place_bet(
        db=db,
        sport=request.sport,
        bet_type=request.bet_type,
        selection=request.selection,
        odds=request.odds,
        stake=request.stake,
        game_id=request.game_id,
        game_description=request.game_description,
        line_value=request.line_value,
        game_date=request.game_date,
        edge_at_placement=request.edge_at_placement,
        notes=request.notes,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/settle/{trade_id}")
def settle_bet(
    trade_id: int,
    request: SettleBetRequest,
    db: Session = Depends(get_db)
):
    """
    Settle a pending paper trade.

    Updates bankroll based on win/loss/push result.
    """
    result = paper_trading.settle_bet(
        db=db,
        trade_id=trade_id,
        result=request.result,
        result_score=request.result_score,
        closing_line_value=request.closing_line_value,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/open")
def get_open_bets(
    sport: Optional[str] = Query(None, description="Filter by sport"),
    db: Session = Depends(get_db)
):
    """
    Get all pending (open) paper trades.
    """
    bets = paper_trading.get_open_bets(db, sport=sport)
    return {
        "bets": bets,
        "count": len(bets),
        "sport_filter": sport,
    }


@router.get("/history")
def get_bet_history(
    sport: Optional[str] = Query(None, description="Filter by sport"),
    status: Optional[str] = Query(None, description="Filter by status (won/lost/push)"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Get settled paper trades history.
    """
    bets = paper_trading.get_bet_history(db, sport=sport, status=status, limit=limit)
    return {
        "bets": bets,
        "count": len(bets),
        "sport_filter": sport,
        "status_filter": status,
    }


@router.get("/trade/{trade_id}")
def get_trade(
    trade_id: int,
    db: Session = Depends(get_db)
):
    """
    Get details of a specific paper trade.
    """
    trade = paper_trading.get_trade_by_id(db, trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade


@router.post("/cancel/{trade_id}")
def cancel_bet(
    trade_id: int,
    db: Session = Depends(get_db)
):
    """
    Cancel a pending paper trade and return stake.
    """
    result = paper_trading.cancel_bet(db, trade_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/reset")
def reset_bankroll(db: Session = Depends(get_db)):
    """
    Reset bankroll to $10,000 and delete all trades.

    Use with caution - this cannot be undone.
    """
    return paper_trading.reset_bankroll(db)


@router.get("/chart")
def get_chart_data(
    days: int = Query(30, ge=1, le=365, description="Number of days"),
    db: Session = Depends(get_db)
):
    """
    Get bankroll history for charting.

    Returns daily balance snapshots.
    """
    data = paper_trading.get_bankroll_chart_data(db, days=days)
    return {
        "data": data,
        "days": days,
    }


@router.get("/performance/by-sport")
def get_performance_by_sport(db: Session = Depends(get_db)):
    """
    Get performance breakdown by sport.

    Shows win rate, ROI, and profit/loss per sport.
    """
    return paper_trading.get_performance_by_sport(db)


@router.get("/performance/by-bet-type")
def get_performance_by_bet_type(db: Session = Depends(get_db)):
    """
    Get performance breakdown by bet type.

    Shows win rate, ROI for spreads, moneylines, totals.
    """
    return paper_trading.get_performance_by_bet_type(db)


@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    """
    Get complete paper trading summary.

    Combines bankroll status, open bets, and recent history.
    """
    bankroll = paper_trading.get_bankroll_status(db)
    open_bets = paper_trading.get_open_bets(db)
    recent = paper_trading.get_bet_history(db, limit=10)
    by_sport = paper_trading.get_performance_by_sport(db)
    by_type = paper_trading.get_performance_by_bet_type(db)

    return {
        "bankroll": bankroll,
        "open_bets": {
            "bets": open_bets,
            "count": len(open_bets),
        },
        "recent_history": {
            "bets": recent,
            "count": len(recent),
        },
        "performance": {
            "by_sport": by_sport,
            "by_bet_type": by_type,
        },
    }
