"""
Analytics router for advanced betting analytics endpoints.
Includes CLV analysis, line movements, and bankroll tracking.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.db import get_db, User, BankrollHistory, TrackedBet, Client
from app.routers.auth import require_auth
from app.services.clv_analysis import (
    get_user_clv_stats,
    get_clv_leaderboard,
    analyze_bet_timing,
    get_sharp_vs_public_analysis
)
from app.services.odds_scheduler import (
    odds_scheduler,
    get_line_movements,
    get_odds_history
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


# CLV Analysis Endpoints

class CLVStatsResponse(BaseModel):
    total_bets_with_clv: int
    average_clv: float
    positive_clv_rate: float
    total_clv_edge: float
    clv_by_sport: Dict[str, Any]
    clv_trend: List[Dict[str, Any]]


@router.get("/clv/stats", response_model=CLVStatsResponse)
def get_clv_stats(
    days: int = Query(90, ge=7, le=365),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get CLV statistics for the authenticated user."""
    stats = get_user_clv_stats(db, user.id, days)
    return CLVStatsResponse(**stats)


class CLVLeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    display_name: str
    bet_count: int
    average_clv: float
    positive_clv_rate: float


@router.get("/clv/leaderboard", response_model=List[CLVLeaderboardEntry])
def get_clv_leaderboard_endpoint(
    min_bets: int = Query(20, ge=5, le=100),
    days: int = Query(30, ge=7, le=365),
    limit: int = Query(50, ge=10, le=100),
    db: Session = Depends(get_db)
):
    """Get CLV leaderboard - users ranked by average CLV."""
    return get_clv_leaderboard(db, min_bets, days, limit)


class TimingAnalysisResponse(BaseModel):
    optimal_timing: str
    timing_analysis: List[Dict[str, Any]]
    recommendation: str


@router.get("/clv/timing", response_model=TimingAnalysisResponse)
def get_timing_analysis(
    days: int = Query(90, ge=30, le=365),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Analyze bet timing to identify optimal betting patterns."""
    return analyze_bet_timing(db, user.id, days)


class SharpAnalysisResponse(BaseModel):
    classification: str
    sharp_tendency: float
    average_clv: float
    total_bets_analyzed: int
    positive_clv_bets: int
    analysis: str


@router.get("/clv/sharp-analysis", response_model=SharpAnalysisResponse)
def get_sharp_analysis(
    days: int = Query(90, ge=30, le=365),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Analyze whether user bets align with sharp or public money."""
    result = get_sharp_vs_public_analysis(db, user.id, days)
    return SharpAnalysisResponse(**result)


# Line Movement Endpoints

class LineMovementResponse(BaseModel):
    id: int
    game_id: int
    market_type: str
    sportsbook: str
    previous_odds: Optional[int]
    current_odds: int
    previous_line: Optional[float]
    current_line: Optional[float]
    movement_percentage: Optional[float]
    direction: Optional[str]
    recorded_at: str


@router.get("/line-movements", response_model=List[LineMovementResponse])
def get_line_movements_endpoint(
    game_id: Optional[int] = None,
    sport: Optional[str] = None,
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(100, ge=10, le=500),
    db: Session = Depends(get_db)
):
    """Get recent line movements."""
    movements = get_line_movements(db, game_id, sport, hours, limit)
    return [LineMovementResponse(**m) for m in movements]


class OddsHistoryResponse(BaseModel):
    id: int
    market_type: str
    sportsbook: str
    odds: int
    line_value: Optional[float]
    captured_at: str


@router.get("/odds-history/{game_id}", response_model=List[OddsHistoryResponse])
def get_odds_history_endpoint(
    game_id: int,
    market_type: Optional[str] = None,
    sportsbook: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get odds history for a specific game."""
    history = get_odds_history(db, game_id, market_type, sportsbook)
    return [OddsHistoryResponse(**h) for h in history]


# Odds Scheduler Status

class SchedulerStatusResponse(BaseModel):
    is_running: bool
    last_refresh: Optional[str]
    refresh_count: int
    error_count: int
    refresh_interval_minutes: int


@router.get("/scheduler/status", response_model=SchedulerStatusResponse)
def get_scheduler_status():
    """Get odds scheduler status."""
    status = odds_scheduler.get_status()
    return SchedulerStatusResponse(**status)


@router.post("/scheduler/refresh-now")
async def trigger_manual_refresh(db: Session = Depends(get_db)):
    """
    Manually trigger an immediate odds refresh for all sports.

    Fetches latest odds from The Odds API and updates line movement data.
    """
    from app.services.odds_api import fetch_and_store_odds, is_odds_api_configured

    if not is_odds_api_configured():
        raise HTTPException(status_code=503, detail="Odds API not configured")

    sports = ["NBA", "NFL", "NCAA_BASKETBALL", "NHL", "MLB", "SOCCER"]
    results = {}
    total = 0

    for sport in sports:
        try:
            count = await fetch_and_store_odds(db, sport)
            results[sport] = count
            total += count
        except Exception as e:
            results[sport] = f"error: {str(e)}"

    return {
        "status": "completed",
        "total_games_updated": total,
        "by_sport": results,
        "timestamp": datetime.utcnow().isoformat()
    }


# Bankroll History Endpoints

class BankrollHistoryEntry(BaseModel):
    id: int
    bankroll_value: float
    change_amount: Optional[float]
    change_reason: Optional[str]
    recorded_at: str


@router.get("/bankroll/history", response_model=List[BankrollHistoryEntry])
def get_bankroll_history(
    days: int = Query(30, ge=7, le=365),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get bankroll history for the authenticated user."""
    from datetime import timedelta
    since = datetime.utcnow() - timedelta(days=days)

    history = db.query(BankrollHistory).filter(
        BankrollHistory.user_id == user.id,
        BankrollHistory.recorded_at >= since
    ).order_by(BankrollHistory.recorded_at.asc()).all()

    return [
        BankrollHistoryEntry(
            id=h.id,
            bankroll_value=h.bankroll_value,
            change_amount=h.change_amount,
            change_reason=h.change_reason,
            recorded_at=h.recorded_at.isoformat()
        )
        for h in history
    ]


class ROIBySportResponse(BaseModel):
    sport: str
    total_bets: int
    winning_bets: int
    total_staked: float
    total_profit: float
    roi_percentage: float


@router.get("/roi/by-sport", response_model=List[ROIBySportResponse])
def get_roi_by_sport(
    days: int = Query(90, ge=7, le=365),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get ROI breakdown by sport."""
    from datetime import timedelta
    from sqlalchemy import func

    since = datetime.utcnow() - timedelta(days=days)

    results = db.query(
        TrackedBet.sport,
        func.count(TrackedBet.id).label('total_bets'),
        func.sum(func.case((TrackedBet.result == 'won', 1), else_=0)).label('winning_bets'),
        func.sum(TrackedBet.stake).label('total_staked'),
        func.sum(TrackedBet.profit_loss).label('total_profit')
    ).filter(
        TrackedBet.user_id == user.id,
        TrackedBet.status == 'settled',
        TrackedBet.placed_at >= since
    ).group_by(TrackedBet.sport).all()

    return [
        ROIBySportResponse(
            sport=r.sport,
            total_bets=r.total_bets,
            winning_bets=r.winning_bets or 0,
            total_staked=r.total_staked or 0,
            total_profit=r.total_profit or 0,
            roi_percentage=round((r.total_profit or 0) / (r.total_staked or 1) * 100, 2)
        )
        for r in results
    ]


class PerformanceSummaryResponse(BaseModel):
    total_bets: int
    win_rate: float
    total_profit: float
    roi_percentage: float
    average_clv: float
    best_sport: Optional[str]
    worst_sport: Optional[str]
    current_bankroll: float
    peak_bankroll: float
    current_streak: int


@router.get("/performance/summary", response_model=PerformanceSummaryResponse)
def get_performance_summary(
    days: int = Query(90, ge=7, le=365),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get comprehensive performance summary."""
    from datetime import timedelta
    from sqlalchemy import func

    since = datetime.utcnow() - timedelta(days=days)

    # Basic stats
    stats = db.query(
        func.count(TrackedBet.id).label('total_bets'),
        func.sum(func.case((TrackedBet.result == 'won', 1), else_=0)).label('wins'),
        func.sum(TrackedBet.stake).label('total_staked'),
        func.sum(TrackedBet.profit_loss).label('total_profit'),
        func.avg(TrackedBet.clv_percentage).label('avg_clv')
    ).filter(
        TrackedBet.user_id == user.id,
        TrackedBet.status == 'settled',
        TrackedBet.placed_at >= since
    ).first()

    # Get client for bankroll
    client = db.query(Client).filter(Client.id == user.client_id).first()
    current_bankroll = client.bankroll if client else 0

    # Peak bankroll
    peak = db.query(func.max(BankrollHistory.bankroll_value)).filter(
        BankrollHistory.user_id == user.id
    ).scalar() or current_bankroll

    # Best/worst sport by ROI
    sport_roi = db.query(
        TrackedBet.sport,
        (func.sum(TrackedBet.profit_loss) / func.sum(TrackedBet.stake) * 100).label('roi')
    ).filter(
        TrackedBet.user_id == user.id,
        TrackedBet.status == 'settled',
        TrackedBet.placed_at >= since
    ).group_by(TrackedBet.sport).having(
        func.count(TrackedBet.id) >= 5
    ).all()

    best_sport = None
    worst_sport = None
    if sport_roi:
        sorted_sports = sorted(sport_roi, key=lambda x: x.roi or 0, reverse=True)
        best_sport = sorted_sports[0].sport if sorted_sports[0].roi > 0 else None
        worst_sport = sorted_sports[-1].sport if sorted_sports[-1].roi < 0 else None

    # Current streak
    recent_bets = db.query(TrackedBet).filter(
        TrackedBet.user_id == user.id,
        TrackedBet.status == 'settled'
    ).order_by(TrackedBet.settled_at.desc()).limit(20).all()

    streak = 0
    if recent_bets:
        first_result = recent_bets[0].result
        if first_result in ['won', 'lost']:
            for bet in recent_bets:
                if bet.result == first_result:
                    streak += 1 if first_result == 'won' else -1
                else:
                    break

    total_bets = stats.total_bets or 0
    wins = stats.wins or 0
    total_staked = stats.total_staked or 0
    total_profit = stats.total_profit or 0

    return PerformanceSummaryResponse(
        total_bets=total_bets,
        win_rate=round(wins / total_bets * 100, 1) if total_bets > 0 else 0,
        total_profit=round(total_profit, 2),
        roi_percentage=round(total_profit / total_staked * 100, 2) if total_staked > 0 else 0,
        average_clv=round(float(stats.avg_clv or 0), 2),
        best_sport=best_sport,
        worst_sport=worst_sport,
        current_bankroll=round(current_bankroll, 2),
        peak_bankroll=round(peak, 2),
        current_streak=streak
    )
