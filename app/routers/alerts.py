from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime

from app.db import get_db, User
from app.services.auth import validate_session
from app.services.alerts import (
    create_alert, get_user_alerts, get_alert_by_id,
    update_alert, delete_alert, toggle_alert, get_alert_types
)
from app.services.audit import log_action

router = APIRouter(prefix="/alerts", tags=["alerts"])


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.split(" ")[1]
    user = validate_session(db, token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    return user


class CreateAlertRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    alert_type: str
    sport: Optional[str] = None
    team_id: Optional[int] = None
    min_edge: Optional[float] = Field(None, ge=0, le=1)
    max_odds: Optional[int] = None
    min_odds: Optional[int] = None
    notify_email: bool = False
    notify_push: bool = True
    notify_telegram: bool = False


class UpdateAlertRequest(BaseModel):
    name: Optional[str] = None
    sport: Optional[str] = None
    min_edge: Optional[float] = None
    max_odds: Optional[int] = None
    min_odds: Optional[int] = None
    notify_email: Optional[bool] = None
    notify_push: Optional[bool] = None
    notify_telegram: Optional[bool] = None
    is_active: Optional[bool] = None


class AlertResponse(BaseModel):
    id: int
    name: str
    alert_type: str
    sport: Optional[str]
    team_id: Optional[int]
    min_edge: Optional[float]
    max_odds: Optional[int]
    min_odds: Optional[int]
    notify_email: bool
    notify_push: bool
    notify_telegram: bool
    is_active: bool
    last_triggered: Optional[datetime]
    trigger_count: int
    created_at: datetime


@router.get("/types")
def get_types():
    return get_alert_types()


@router.post("", response_model=AlertResponse)
def create_alert_endpoint(
    data: CreateAlertRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    alert_types = get_alert_types()
    if data.alert_type not in alert_types:
        raise HTTPException(status_code=400, detail="Invalid alert type")
    
    alert = create_alert(
        db=db,
        user_id=user.id,
        name=data.name,
        alert_type=data.alert_type,
        sport=data.sport,
        team_id=data.team_id,
        min_edge=data.min_edge,
        max_odds=data.max_odds,
        min_odds=data.min_odds,
        notify_email=data.notify_email,
        notify_push=data.notify_push,
        notify_telegram=data.notify_telegram
    )
    
    log_action(
        db, "alert_created", user.id,
        resource_type="alert",
        resource_id=alert.id,
        ip_address=request.client.host if request.client else None
    )
    
    return AlertResponse(
        id=alert.id,
        name=alert.name,
        alert_type=alert.alert_type,
        sport=alert.sport,
        team_id=alert.team_id,
        min_edge=alert.min_edge,
        max_odds=alert.max_odds,
        min_odds=alert.min_odds,
        notify_email=alert.notify_email,
        notify_push=alert.notify_push,
        notify_telegram=alert.notify_telegram,
        is_active=alert.is_active,
        last_triggered=alert.last_triggered,
        trigger_count=alert.trigger_count,
        created_at=alert.created_at
    )


@router.get("", response_model=List[AlertResponse])
def list_alerts(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    alerts = get_user_alerts(db, user.id)
    
    return [
        AlertResponse(
            id=a.id,
            name=a.name,
            alert_type=a.alert_type,
            sport=a.sport,
            team_id=a.team_id,
            min_edge=a.min_edge,
            max_odds=a.max_odds,
            min_odds=a.min_odds,
            notify_email=a.notify_email,
            notify_push=a.notify_push,
            notify_telegram=a.notify_telegram,
            is_active=a.is_active,
            last_triggered=a.last_triggered,
            trigger_count=a.trigger_count,
            created_at=a.created_at
        )
        for a in alerts
    ]


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(
    alert_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    alert = get_alert_by_id(db, alert_id, user.id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return AlertResponse(
        id=alert.id,
        name=alert.name,
        alert_type=alert.alert_type,
        sport=alert.sport,
        team_id=alert.team_id,
        min_edge=alert.min_edge,
        max_odds=alert.max_odds,
        min_odds=alert.min_odds,
        notify_email=alert.notify_email,
        notify_push=alert.notify_push,
        notify_telegram=alert.notify_telegram,
        is_active=alert.is_active,
        last_triggered=alert.last_triggered,
        trigger_count=alert.trigger_count,
        created_at=alert.created_at
    )


@router.patch("/{alert_id}", response_model=AlertResponse)
def update_alert_endpoint(
    alert_id: int,
    data: UpdateAlertRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    alert = get_alert_by_id(db, alert_id, user.id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    alert = update_alert(db, alert, updates)
    
    log_action(
        db, "alert_updated", user.id,
        resource_type="alert",
        resource_id=alert.id,
        ip_address=request.client.host if request.client else None
    )
    
    return AlertResponse(
        id=alert.id,
        name=alert.name,
        alert_type=alert.alert_type,
        sport=alert.sport,
        team_id=alert.team_id,
        min_edge=alert.min_edge,
        max_odds=alert.max_odds,
        min_odds=alert.min_odds,
        notify_email=alert.notify_email,
        notify_push=alert.notify_push,
        notify_telegram=alert.notify_telegram,
        is_active=alert.is_active,
        last_triggered=alert.last_triggered,
        trigger_count=alert.trigger_count,
        created_at=alert.created_at
    )


@router.post("/{alert_id}/toggle", response_model=AlertResponse)
def toggle_alert_endpoint(
    alert_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    alert = get_alert_by_id(db, alert_id, user.id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert = toggle_alert(db, alert)
    
    return AlertResponse(
        id=alert.id,
        name=alert.name,
        alert_type=alert.alert_type,
        sport=alert.sport,
        team_id=alert.team_id,
        min_edge=alert.min_edge,
        max_odds=alert.max_odds,
        min_odds=alert.min_odds,
        notify_email=alert.notify_email,
        notify_push=alert.notify_push,
        notify_telegram=alert.notify_telegram,
        is_active=alert.is_active,
        last_triggered=alert.last_triggered,
        trigger_count=alert.trigger_count,
        created_at=alert.created_at
    )


@router.delete("/{alert_id}")
def delete_alert_endpoint(
    alert_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    alert = get_alert_by_id(db, alert_id, user.id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    delete_alert(db, alert)
    
    log_action(
        db, "alert_deleted", user.id,
        resource_type="alert",
        resource_id=alert_id,
        ip_address=request.client.host if request.client else None
    )
    
    return {"message": "Alert deleted"}
