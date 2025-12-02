import json
import hmac
import hashlib
import secrets
import httpx
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.db import Webhook


WEBHOOK_EVENTS = [
    "recommendation.created",
    "bet.placed",
    "bet.won",
    "bet.lost",
    "alert.triggered",
    "parlay.created",
    "session.created",
]


def create_webhook(
    db: Session,
    user_id: int,
    name: str,
    url: str,
    events: List[str],
    generate_secret: bool = True
) -> Webhook:
    secret = secrets.token_hex(32) if generate_secret else None
    
    webhook = Webhook(
        user_id=user_id,
        name=name,
        url=url,
        secret=secret,
        events=json.dumps(events)
    )
    
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    
    return webhook


def get_user_webhooks(db: Session, user_id: int) -> List[Webhook]:
    return db.query(Webhook).filter(
        Webhook.user_id == user_id
    ).order_by(Webhook.created_at.desc()).all()


def get_webhook_by_id(db: Session, webhook_id: int, user_id: int) -> Optional[Webhook]:
    return db.query(Webhook).filter(
        Webhook.id == webhook_id,
        Webhook.user_id == user_id
    ).first()


def update_webhook(
    db: Session,
    webhook: Webhook,
    updates: Dict[str, Any]
) -> Webhook:
    if "events" in updates:
        updates["events"] = json.dumps(updates["events"])
    
    for key, value in updates.items():
        if hasattr(webhook, key) and key not in ["id", "user_id", "secret"]:
            setattr(webhook, key, value)
    
    webhook.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(webhook)
    
    return webhook


def delete_webhook(db: Session, webhook: Webhook) -> bool:
    db.delete(webhook)
    db.commit()
    return True


def regenerate_secret(db: Session, webhook: Webhook) -> str:
    new_secret = secrets.token_hex(32)
    webhook.secret = new_secret
    webhook.updated_at = datetime.utcnow()
    db.commit()
    return new_secret


def generate_signature(payload: str, secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


async def send_webhook(
    db: Session,
    webhook: Webhook,
    event: str,
    data: Dict[str, Any]
) -> bool:
    events = json.loads(webhook.events)
    if event not in events:
        return False
    
    payload = {
        "event": event,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": data
    }
    
    payload_str = json.dumps(payload)
    
    headers = {
        "Content-Type": "application/json",
        "X-EdgeBet-Event": event,
        "X-EdgeBet-Timestamp": payload["timestamp"]
    }
    
    if webhook.secret:
        signature = generate_signature(payload_str, webhook.secret)
        headers["X-EdgeBet-Signature"] = f"sha256={signature}"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                webhook.url,
                content=payload_str,
                headers=headers
            )
        
        webhook.last_triggered = datetime.utcnow()
        webhook.last_status = response.status_code
        
        if response.status_code >= 400:
            webhook.failure_count += 1
        else:
            webhook.failure_count = 0
        
        db.commit()
        
        return response.status_code < 400
        
    except Exception as e:
        webhook.last_triggered = datetime.utcnow()
        webhook.last_status = 0
        webhook.failure_count += 1
        db.commit()
        return False


def get_webhooks_for_event(db: Session, user_id: int, event: str) -> List[Webhook]:
    webhooks = db.query(Webhook).filter(
        Webhook.user_id == user_id,
        Webhook.is_active == True
    ).all()
    
    matching = []
    for webhook in webhooks:
        events = json.loads(webhook.events)
        if event in events:
            matching.append(webhook)
    
    return matching


def get_available_events() -> List[str]:
    return WEBHOOK_EVENTS
