from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.db import get_db, User
from app.services.auth import validate_session
from app.services.telegram_bot import (
    is_telegram_configured, create_link_code,
    get_telegram_user, unlink_telegram, process_webhook_update
)
from app.services.audit import log_action

router = APIRouter(prefix="/telegram", tags=["telegram"])


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.split(" ")[1]
    user = validate_session(db, token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    return user


class TelegramStatusResponse(BaseModel):
    configured: bool
    linked: bool
    username: Optional[str] = None
    notify_recommendations: bool = False
    notify_results: bool = False
    notify_alerts: bool = False


class LinkCodeResponse(BaseModel):
    code: str
    bot_url: str
    deep_link: str


class UpdateNotificationsRequest(BaseModel):
    notify_recommendations: Optional[bool] = None
    notify_results: Optional[bool] = None
    notify_alerts: Optional[bool] = None


@router.get("/status", response_model=TelegramStatusResponse)
def get_telegram_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    configured = is_telegram_configured()
    telegram_user = get_telegram_user(db, user.id) if configured else None
    
    return TelegramStatusResponse(
        configured=configured,
        linked=telegram_user is not None,
        username=telegram_user.telegram_username if telegram_user else None,
        notify_recommendations=telegram_user.notify_recommendations if telegram_user else False,
        notify_results=telegram_user.notify_results if telegram_user else False,
        notify_alerts=telegram_user.notify_alerts if telegram_user else False
    )


@router.post("/link", response_model=LinkCodeResponse)
def generate_link_code(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not is_telegram_configured():
        raise HTTPException(status_code=503, detail="Telegram bot not configured")
    
    existing = get_telegram_user(db, user.id)
    if existing:
        raise HTTPException(status_code=400, detail="Telegram already linked")
    
    code = create_link_code(user.id)
    
    import os
    bot_username = os.environ.get("TELEGRAM_BOT_USERNAME", "EdgeBetBot")
    
    return LinkCodeResponse(
        code=code,
        bot_url=f"https://t.me/{bot_username}",
        deep_link=f"https://t.me/{bot_username}?start={code}"
    )


@router.delete("/unlink")
def unlink_telegram_account(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not unlink_telegram(db, user.id):
        raise HTTPException(status_code=404, detail="No Telegram account linked")
    
    log_action(
        db, "telegram_unlinked", user.id,
        ip_address=request.client.host if request.client else None
    )
    
    return {"message": "Telegram account unlinked"}


@router.patch("/notifications", response_model=TelegramStatusResponse)
def update_notifications(
    data: UpdateNotificationsRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    telegram_user = get_telegram_user(db, user.id)
    if not telegram_user:
        raise HTTPException(status_code=404, detail="Telegram not linked")
    
    if data.notify_recommendations is not None:
        telegram_user.notify_recommendations = data.notify_recommendations
    if data.notify_results is not None:
        telegram_user.notify_results = data.notify_results
    if data.notify_alerts is not None:
        telegram_user.notify_alerts = data.notify_alerts
    
    db.commit()
    
    return TelegramStatusResponse(
        configured=True,
        linked=True,
        username=telegram_user.telegram_username,
        notify_recommendations=telegram_user.notify_recommendations,
        notify_results=telegram_user.notify_results,
        notify_alerts=telegram_user.notify_alerts
    )


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        update = await request.json()
        result = await process_webhook_update(db, update)
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}
