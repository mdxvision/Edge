"""
API Keys Router

Manages API keys for pro users to access the EdgeBet API programmatically.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import secrets
import hashlib

from app.db import get_db, User, APIKey, APIUsage
from app.routers.auth import require_auth
from app.routers.billing import require_subscription

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


class CreateKeyRequest(BaseModel):
    name: str


class APIKeyResponse(BaseModel):
    id: int
    name: str
    prefix: str
    is_active: bool
    rate_limit: int
    monthly_limit: int
    current_month_usage: int
    last_used: Optional[str]
    created_at: str


class APIKeyCreatedResponse(BaseModel):
    api_key: str  # Full key - only shown once
    prefix: str
    name: str
    message: str


class UsageStatsResponse(BaseModel):
    total_requests: int
    requests_today: int
    requests_this_month: int
    monthly_limit: int
    remaining: int
    rate_limit_per_minute: int


@router.post("", response_model=APIKeyCreatedResponse)
async def create_api_key(
    request: CreateKeyRequest,
    user: User = Depends(require_subscription("pro")),
    db: Session = Depends(get_db)
):
    """
    Generate a new API key for programmatic access.

    Note: The full API key is only shown once. Store it securely.
    """
    # Check existing keys count (limit to 5 per user)
    existing_count = db.query(APIKey).filter(
        APIKey.user_id == user.id,
        APIKey.is_active == True
    ).count()

    if existing_count >= 5:
        raise HTTPException(
            status_code=400,
            detail="Maximum of 5 active API keys allowed. Please revoke an existing key."
        )

    # Generate secure API key
    raw_key = f"eb_live_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:16]

    # Create API key record
    api_key = APIKey(
        user_id=user.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=request.name,
        is_active=True,
        rate_limit=100,  # 100 requests per minute for pro
        monthly_limit=50000
    )
    db.add(api_key)
    db.commit()

    return APIKeyCreatedResponse(
        api_key=raw_key,
        prefix=key_prefix,
        name=request.name,
        message="API key created. Store this key securely - it won't be shown again."
    )


@router.get("", response_model=List[APIKeyResponse])
async def list_api_keys(
    user: User = Depends(require_subscription("pro")),
    db: Session = Depends(get_db)
):
    """List all API keys for the current user."""
    keys = db.query(APIKey).filter(
        APIKey.user_id == user.id
    ).order_by(APIKey.created_at.desc()).all()

    return [
        APIKeyResponse(
            id=key.id,
            name=key.name,
            prefix=key.key_prefix,
            is_active=key.is_active,
            rate_limit=key.rate_limit,
            monthly_limit=key.monthly_limit,
            current_month_usage=key.current_month_usage,
            last_used=key.last_used.isoformat() if key.last_used else None,
            created_at=key.created_at.isoformat()
        )
        for key in keys
    ]


@router.delete("/{key_prefix}")
async def revoke_api_key(
    key_prefix: str,
    user: User = Depends(require_subscription("pro")),
    db: Session = Depends(get_db)
):
    """Revoke an API key."""
    key = db.query(APIKey).filter(
        APIKey.user_id == user.id,
        APIKey.key_prefix == key_prefix
    ).first()

    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    key.is_active = False
    db.commit()

    return {"message": "API key revoked successfully"}


@router.get("/usage", response_model=UsageStatsResponse)
async def get_api_usage(
    user: User = Depends(require_subscription("pro")),
    db: Session = Depends(get_db)
):
    """Get API usage statistics for current billing period."""
    # Get all active keys for user
    keys = db.query(APIKey).filter(
        APIKey.user_id == user.id,
        APIKey.is_active == True
    ).all()

    if not keys:
        return UsageStatsResponse(
            total_requests=0,
            requests_today=0,
            requests_this_month=0,
            monthly_limit=50000,
            remaining=50000,
            rate_limit_per_minute=100
        )

    key_ids = [k.id for k in keys]

    # Calculate usage stats
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_requests = db.query(APIUsage).filter(
        APIUsage.api_key_id.in_(key_ids)
    ).count()

    requests_today = db.query(APIUsage).filter(
        APIUsage.api_key_id.in_(key_ids),
        APIUsage.timestamp >= today_start
    ).count()

    requests_this_month = sum(k.current_month_usage for k in keys)
    monthly_limit = keys[0].monthly_limit if keys else 50000

    return UsageStatsResponse(
        total_requests=total_requests,
        requests_today=requests_today,
        requests_this_month=requests_this_month,
        monthly_limit=monthly_limit,
        remaining=max(0, monthly_limit - requests_this_month),
        rate_limit_per_minute=100
    )


@router.get("/usage/history")
async def get_usage_history(
    days: int = 30,
    user: User = Depends(require_subscription("pro")),
    db: Session = Depends(get_db)
):
    """Get daily API usage history."""
    from datetime import timedelta
    from sqlalchemy import func

    keys = db.query(APIKey).filter(
        APIKey.user_id == user.id
    ).all()

    if not keys:
        return {"history": []}

    key_ids = [k.id for k in keys]
    start_date = datetime.utcnow() - timedelta(days=days)

    # Get daily counts
    daily_usage = db.query(
        func.date(APIUsage.timestamp).label("date"),
        func.count(APIUsage.id).label("count")
    ).filter(
        APIUsage.api_key_id.in_(key_ids),
        APIUsage.timestamp >= start_date
    ).group_by(
        func.date(APIUsage.timestamp)
    ).order_by("date").all()

    return {
        "history": [
            {"date": str(row.date), "requests": row.count}
            for row in daily_usage
        ]
    }


# API Key Authentication Middleware
async def authenticate_api_key(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Authenticate request using API key.

    Usage: Include header `Authorization: Bearer eb_live_xxx...`
    """
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer eb_"):
        return None

    api_key = auth_header.replace("Bearer ", "")
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    # Find API key
    key_record = db.query(APIKey).filter(
        APIKey.key_hash == key_hash,
        APIKey.is_active == True
    ).first()

    if not key_record:
        return None

    # Check rate limits
    from datetime import timedelta
    one_minute_ago = datetime.utcnow() - timedelta(minutes=1)

    recent_requests = db.query(APIUsage).filter(
        APIUsage.api_key_id == key_record.id,
        APIUsage.timestamp >= one_minute_ago
    ).count()

    if recent_requests >= key_record.rate_limit:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please wait before making more requests."
        )

    # Check monthly limit
    if key_record.current_month_usage >= key_record.monthly_limit:
        raise HTTPException(
            status_code=429,
            detail="Monthly API limit reached. Please upgrade or wait for reset."
        )

    # Update usage
    key_record.last_used = datetime.utcnow()
    key_record.current_month_usage += 1

    # Log usage
    usage = APIUsage(
        api_key_id=key_record.id,
        endpoint=str(request.url.path),
        method=request.method,
        status_code=200
    )
    db.add(usage)
    db.commit()

    # Get user
    user = db.query(User).filter(User.id == key_record.user_id).first()
    return user
