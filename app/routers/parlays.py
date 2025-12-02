from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.db import get_db, User, Client
from app.services.auth import validate_session
from app.services.parlay import (
    analyze_parlay, create_parlay, get_user_parlays,
    settle_parlay, build_parlay_from_recommendations
)
from app.services.audit import log_action

router = APIRouter(prefix="/parlays", tags=["parlays"])


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.split(" ")[1]
    user = validate_session(db, token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    return user


class ParlayLeg(BaseModel):
    selection: str
    odds: int
    probability: float = Field(..., ge=0, le=1)
    game_id: Optional[int] = None
    sport: Optional[str] = None
    recommendation_id: Optional[int] = None


class AnalyzeParlayRequest(BaseModel):
    legs: List[ParlayLeg] = Field(..., min_length=2, max_length=15)


class CreateParlayRequest(BaseModel):
    legs: List[ParlayLeg] = Field(..., min_length=2, max_length=15)
    name: Optional[str] = None
    stake: Optional[float] = None


class BuildFromRecommendationsRequest(BaseModel):
    recommendation_ids: List[int] = Field(..., min_length=2, max_length=15)
    name: Optional[str] = None


class ParlayResponse(BaseModel):
    id: int
    name: Optional[str]
    leg_count: int
    combined_odds: int
    combined_probability: float
    correlation_adjustment: float
    adjusted_probability: float
    edge: Optional[float]
    suggested_stake: Optional[float]
    potential_profit: Optional[float]
    status: str
    result: Optional[str]
    profit_loss: Optional[float]
    created_at: datetime


class ParlayAnalysis(BaseModel):
    leg_count: int
    combined_odds: int
    combined_probability: float
    correlation_adjustment: float
    adjusted_probability: float
    implied_probability: float
    edge: float
    ev_per_dollar: float
    is_positive_ev: bool
    legs: List[Dict[str, Any]]
    risk_assessment: Dict[str, Any]


@router.post("/analyze", response_model=ParlayAnalysis)
def analyze_parlay_endpoint(
    data: AnalyzeParlayRequest,
    db: Session = Depends(get_db)
):
    legs = [leg.model_dump() for leg in data.legs]
    analysis = analyze_parlay(legs, db)
    return ParlayAnalysis(**analysis)


@router.post("", response_model=ParlayResponse)
def create_parlay_endpoint(
    data: CreateParlayRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == user.client_id).first() if user.client_id else None
    bankroll = client.bankroll if client else None
    
    legs = [leg.model_dump() for leg in data.legs]
    parlay = create_parlay(
        db=db,
        user_id=user.id,
        leg_data=legs,
        name=data.name,
        stake=data.stake,
        bankroll=bankroll
    )
    
    log_action(
        db, "parlay_created", user.id,
        resource_type="parlay",
        resource_id=parlay.id,
        ip_address=request.client.host if request.client else None,
        new_value={"leg_count": parlay.leg_count, "combined_odds": parlay.combined_odds}
    )
    
    return ParlayResponse(
        id=parlay.id,
        name=parlay.name,
        leg_count=parlay.leg_count,
        combined_odds=parlay.combined_odds,
        combined_probability=parlay.combined_probability,
        correlation_adjustment=parlay.correlation_adjustment,
        adjusted_probability=parlay.adjusted_probability,
        edge=parlay.edge,
        suggested_stake=parlay.suggested_stake,
        potential_profit=parlay.potential_profit,
        status=parlay.status,
        result=parlay.result,
        profit_loss=parlay.profit_loss,
        created_at=parlay.created_at
    )


@router.post("/from-recommendations")
def build_from_recommendations(
    data: BuildFromRecommendationsRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    result = build_parlay_from_recommendations(
        db=db,
        recommendation_ids=data.recommendation_ids,
        user_id=user.id,
        name=data.name
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("", response_model=List[ParlayResponse])
def list_parlays(
    status: Optional[str] = None,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    parlays = get_user_parlays(db, user.id, status, limit)
    
    return [
        ParlayResponse(
            id=p.id,
            name=p.name,
            leg_count=p.leg_count,
            combined_odds=p.combined_odds,
            combined_probability=p.combined_probability,
            correlation_adjustment=p.correlation_adjustment,
            adjusted_probability=p.adjusted_probability,
            edge=p.edge,
            suggested_stake=p.suggested_stake,
            potential_profit=p.potential_profit,
            status=p.status,
            result=p.result,
            profit_loss=p.profit_loss,
            created_at=p.created_at
        )
        for p in parlays
    ]


class SettleParlayRequest(BaseModel):
    result: str = Field(..., pattern="^(won|lost|push)$")
    profit_loss: Optional[float] = None


@router.post("/{parlay_id}/settle", response_model=ParlayResponse)
def settle_parlay_endpoint(
    parlay_id: int,
    data: SettleParlayRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from app.db import Parlay
    
    parlay = db.query(Parlay).filter(
        Parlay.id == parlay_id,
        Parlay.user_id == user.id
    ).first()
    
    if not parlay:
        raise HTTPException(status_code=404, detail="Parlay not found")
    
    if parlay.status == "settled":
        raise HTTPException(status_code=400, detail="Parlay already settled")
    
    parlay = settle_parlay(db, parlay, data.result, data.profit_loss)
    
    log_action(
        db, "parlay_settled", user.id,
        resource_type="parlay",
        resource_id=parlay.id,
        ip_address=request.client.host if request.client else None,
        new_value={"result": data.result}
    )
    
    return ParlayResponse(
        id=parlay.id,
        name=parlay.name,
        leg_count=parlay.leg_count,
        combined_odds=parlay.combined_odds,
        combined_probability=parlay.combined_probability,
        correlation_adjustment=parlay.correlation_adjustment,
        adjusted_probability=parlay.adjusted_probability,
        edge=parlay.edge,
        suggested_stake=parlay.suggested_stake,
        potential_profit=parlay.potential_profit,
        status=parlay.status,
        result=parlay.result,
        profit_loss=parlay.profit_loss,
        created_at=parlay.created_at
    )
