from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime

from app.db import get_db, User
from app.services.auth import validate_session
from app.services.webhooks import (
    create_webhook, get_user_webhooks, get_webhook_by_id,
    update_webhook, delete_webhook, regenerate_secret, get_available_events
)
from app.services.audit import log_action

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.split(" ")[1]
    user = validate_session(db, token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    return user


class CreateWebhookRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    url: str
    events: List[str]


class UpdateWebhookRequest(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    events: Optional[List[str]] = None
    is_active: Optional[bool] = None


class WebhookResponse(BaseModel):
    id: int
    name: str
    url: str
    events: List[str]
    is_active: bool
    last_triggered: Optional[datetime]
    last_status: Optional[int]
    failure_count: int
    created_at: datetime


class WebhookWithSecretResponse(WebhookResponse):
    secret: Optional[str]


@router.get("/events")
def list_events():
    return {"events": get_available_events()}


@router.post("", response_model=WebhookWithSecretResponse)
def create_webhook_endpoint(
    data: CreateWebhookRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    available = get_available_events()
    invalid = [e for e in data.events if e not in available]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid events: {', '.join(invalid)}"
        )
    
    webhook = create_webhook(
        db=db,
        user_id=user.id,
        name=data.name,
        url=data.url,
        events=data.events
    )
    
    log_action(
        db, "webhook_created", user.id,
        resource_type="webhook",
        resource_id=webhook.id,
        ip_address=request.client.host if request.client else None
    )
    
    import json
    return WebhookWithSecretResponse(
        id=webhook.id,
        name=webhook.name,
        url=webhook.url,
        events=json.loads(webhook.events),
        is_active=webhook.is_active,
        last_triggered=webhook.last_triggered,
        last_status=webhook.last_status,
        failure_count=webhook.failure_count,
        created_at=webhook.created_at,
        secret=webhook.secret
    )


@router.get("", response_model=List[WebhookResponse])
def list_webhooks(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    webhooks = get_user_webhooks(db, user.id)
    
    import json
    return [
        WebhookResponse(
            id=w.id,
            name=w.name,
            url=w.url,
            events=json.loads(w.events),
            is_active=w.is_active,
            last_triggered=w.last_triggered,
            last_status=w.last_status,
            failure_count=w.failure_count,
            created_at=w.created_at
        )
        for w in webhooks
    ]


@router.get("/{webhook_id}", response_model=WebhookResponse)
def get_webhook(
    webhook_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    webhook = get_webhook_by_id(db, webhook_id, user.id)
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    import json
    return WebhookResponse(
        id=webhook.id,
        name=webhook.name,
        url=webhook.url,
        events=json.loads(webhook.events),
        is_active=webhook.is_active,
        last_triggered=webhook.last_triggered,
        last_status=webhook.last_status,
        failure_count=webhook.failure_count,
        created_at=webhook.created_at
    )


@router.patch("/{webhook_id}", response_model=WebhookResponse)
def update_webhook_endpoint(
    webhook_id: int,
    data: UpdateWebhookRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    webhook = get_webhook_by_id(db, webhook_id, user.id)
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    if data.events:
        available = get_available_events()
        invalid = [e for e in data.events if e not in available]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid events: {', '.join(invalid)}"
            )
    
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    webhook = update_webhook(db, webhook, updates)
    
    log_action(
        db, "webhook_updated", user.id,
        resource_type="webhook",
        resource_id=webhook.id,
        ip_address=request.client.host if request.client else None
    )
    
    import json
    return WebhookResponse(
        id=webhook.id,
        name=webhook.name,
        url=webhook.url,
        events=json.loads(webhook.events),
        is_active=webhook.is_active,
        last_triggered=webhook.last_triggered,
        last_status=webhook.last_status,
        failure_count=webhook.failure_count,
        created_at=webhook.created_at
    )


@router.post("/{webhook_id}/regenerate-secret")
def regenerate_secret_endpoint(
    webhook_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    webhook = get_webhook_by_id(db, webhook_id, user.id)
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    new_secret = regenerate_secret(db, webhook)
    
    log_action(
        db, "webhook_secret_regenerated", user.id,
        resource_type="webhook",
        resource_id=webhook.id,
        ip_address=request.client.host if request.client else None
    )
    
    return {"secret": new_secret}


@router.delete("/{webhook_id}")
def delete_webhook_endpoint(
    webhook_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    webhook = get_webhook_by_id(db, webhook_id, user.id)
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    delete_webhook(db, webhook)
    
    log_action(
        db, "webhook_deleted", user.id,
        resource_type="webhook",
        resource_id=webhook_id,
        ip_address=request.client.host if request.client else None
    )
    
    return {"message": "Webhook deleted"}
