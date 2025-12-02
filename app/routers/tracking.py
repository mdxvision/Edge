from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.db import get_db, User
from app.services.auth import validate_session
from app.services.bet_tracking import (
    place_bet, settle_bet, get_user_bets, get_bet_by_id,
    delete_bet, get_user_stats, get_profit_by_period,
    get_profit_by_sport, get_leaderboard
)
from app.services.audit import log_action

router = APIRouter(prefix="/tracking", tags=["tracking"])


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.split(" ")[1]
    user = validate_session(db, token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    return user


class PlaceBetRequest(BaseModel):
    sport: str
    bet_type: str
    selection: str
    odds: int
    stake: float = Field(..., gt=0)
    currency: str = "USD"
    sportsbook: Optional[str] = None
    notes: Optional[str] = None
    game_id: Optional[int] = None
    game_date: Optional[datetime] = None
    recommendation_id: Optional[int] = None


class BetResponse(BaseModel):
    id: int
    sport: str
    bet_type: str
    selection: str
    odds: int
    stake: float
    currency: str
    potential_profit: float
    status: str
    result: Optional[str]
    profit_loss: Optional[float]
    placed_at: datetime
    settled_at: Optional[datetime]
    sportsbook: Optional[str]


class SettleBetRequest(BaseModel):
    result: str = Field(..., pattern="^(won|lost|push|void)$")
    actual_profit_loss: Optional[float] = None


class StatsResponse(BaseModel):
    total_bets: int
    winning_bets: int
    losing_bets: int
    push_bets: int
    win_rate: float
    total_staked: float
    total_profit: float
    roi: float
    average_odds: int
    best_win: float
    worst_loss: float
    current_streak: int
    best_streak: int
    currency: str


@router.post("/bets", response_model=BetResponse)
def create_bet(
    data: PlaceBetRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    bet = place_bet(
        db=db,
        user_id=user.id,
        sport=data.sport,
        bet_type=data.bet_type,
        selection=data.selection,
        odds=data.odds,
        stake=data.stake,
        currency=data.currency,
        sportsbook=data.sportsbook,
        notes=data.notes,
        game_id=data.game_id,
        game_date=data.game_date,
        recommendation_id=data.recommendation_id
    )
    
    log_action(
        db, "bet_placed", user.id,
        resource_type="bet",
        resource_id=bet.id,
        ip_address=request.client.host if request.client else None,
        new_value={"sport": data.sport, "stake": data.stake, "odds": data.odds}
    )
    
    return BetResponse(
        id=bet.id,
        sport=bet.sport,
        bet_type=bet.bet_type,
        selection=bet.selection,
        odds=bet.odds,
        stake=bet.stake,
        currency=bet.currency,
        potential_profit=bet.potential_profit,
        status=bet.status,
        result=bet.result,
        profit_loss=bet.profit_loss,
        placed_at=bet.placed_at,
        settled_at=bet.settled_at,
        sportsbook=bet.sportsbook
    )


@router.get("/bets", response_model=List[BetResponse])
def list_bets(
    status: Optional[str] = None,
    sport: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    bets = get_user_bets(db, user.id, status, sport, limit, offset)
    
    return [
        BetResponse(
            id=b.id,
            sport=b.sport,
            bet_type=b.bet_type,
            selection=b.selection,
            odds=b.odds,
            stake=b.stake,
            currency=b.currency,
            potential_profit=b.potential_profit,
            status=b.status,
            result=b.result,
            profit_loss=b.profit_loss,
            placed_at=b.placed_at,
            settled_at=b.settled_at,
            sportsbook=b.sportsbook
        )
        for b in bets
    ]


@router.get("/bets/{bet_id}", response_model=BetResponse)
def get_bet(
    bet_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    bet = get_bet_by_id(db, bet_id, user.id)
    
    if not bet:
        raise HTTPException(status_code=404, detail="Bet not found")
    
    return BetResponse(
        id=bet.id,
        sport=bet.sport,
        bet_type=bet.bet_type,
        selection=bet.selection,
        odds=bet.odds,
        stake=bet.stake,
        currency=bet.currency,
        potential_profit=bet.potential_profit,
        status=bet.status,
        result=bet.result,
        profit_loss=bet.profit_loss,
        placed_at=bet.placed_at,
        settled_at=bet.settled_at,
        sportsbook=bet.sportsbook
    )


@router.post("/bets/{bet_id}/settle", response_model=BetResponse)
def settle_bet_endpoint(
    bet_id: int,
    data: SettleBetRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    bet = get_bet_by_id(db, bet_id, user.id)
    
    if not bet:
        raise HTTPException(status_code=404, detail="Bet not found")
    
    if bet.status == "settled":
        raise HTTPException(status_code=400, detail="Bet already settled")
    
    bet = settle_bet(db, bet, data.result, data.actual_profit_loss)
    
    log_action(
        db, "bet_settled", user.id,
        resource_type="bet",
        resource_id=bet.id,
        ip_address=request.client.host if request.client else None,
        new_value={"result": data.result, "profit_loss": bet.profit_loss}
    )
    
    return BetResponse(
        id=bet.id,
        sport=bet.sport,
        bet_type=bet.bet_type,
        selection=bet.selection,
        odds=bet.odds,
        stake=bet.stake,
        currency=bet.currency,
        potential_profit=bet.potential_profit,
        status=bet.status,
        result=bet.result,
        profit_loss=bet.profit_loss,
        placed_at=bet.placed_at,
        settled_at=bet.settled_at,
        sportsbook=bet.sportsbook
    )


@router.delete("/bets/{bet_id}")
def delete_bet_endpoint(
    bet_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    bet = get_bet_by_id(db, bet_id, user.id)
    
    if not bet:
        raise HTTPException(status_code=404, detail="Bet not found")
    
    if not delete_bet(db, bet):
        raise HTTPException(status_code=400, detail="Cannot delete settled bets")
    
    return {"message": "Bet deleted"}


@router.get("/stats", response_model=StatsResponse)
def get_stats(
    currency: str = "USD",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    stats = get_user_stats(db, user.id, currency)
    return StatsResponse(**stats)


@router.get("/profit/daily")
def get_daily_profit(
    days: int = 30,
    currency: str = "USD",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_profit_by_period(db, user.id, days, currency)


@router.get("/profit/by-sport")
def get_sport_profit(
    currency: str = "USD",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_profit_by_sport(db, user.id, currency)


class LeaderboardEntryResponse(BaseModel):
    rank: int
    display_name: str
    total_bets: int
    winning_bets: int
    total_profit: float
    roi_percentage: float
    current_streak: int


@router.get("/leaderboard", response_model=List[LeaderboardEntryResponse])
def get_leaderboard_endpoint(
    sort_by: str = "total_profit",
    limit: int = 50,
    db: Session = Depends(get_db)
):
    entries = get_leaderboard(db, sort_by, limit)
    
    return [
        LeaderboardEntryResponse(
            rank=e.rank or 0,
            display_name=e.display_name,
            total_bets=e.total_bets,
            winning_bets=e.winning_bets,
            total_profit=e.total_profit,
            roi_percentage=e.roi_percentage,
            current_streak=e.current_streak
        )
        for e in entries
    ]
