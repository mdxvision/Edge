"""
Email Digest Router

Endpoints for managing daily email digest preferences and sending test digests.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, Field

from app.db import get_db, User
from app.routers.auth import require_auth
from app.services.email_digest import (
    get_or_create_digest_preferences,
    update_digest_preferences,
    send_test_digest,
    generate_digest_content,
    get_top_edges_today,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/digest", tags=["Email Digest"])


class DigestPreferencesUpdate(BaseModel):
    """Request model for updating digest preferences."""
    enabled: Optional[bool] = Field(None, description="Enable/disable daily digest")
    send_hour: Optional[int] = Field(None, ge=0, le=23, description="Hour to send (0-23)")
    send_minute: Optional[int] = Field(None, ge=0, le=59, description="Minute to send (0-59)")
    timezone: Optional[str] = Field(None, description="User timezone (e.g., America/New_York)")
    include_edges: Optional[bool] = Field(None, description="Include top edges in digest")
    include_results: Optional[bool] = Field(None, description="Include yesterday's results")
    include_bankroll: Optional[bool] = Field(None, description="Include bankroll update")
    min_edge_for_digest: Optional[float] = Field(None, ge=0, le=20, description="Minimum edge % to include")


class DigestPreferencesResponse(BaseModel):
    """Response model for digest preferences."""
    enabled: bool
    send_time: str  # "07:00"
    timezone: str
    include_edges: bool
    include_results: bool
    include_bankroll: bool
    min_edge_for_digest: float
    last_sent_at: Optional[str]


@router.get("/preferences")
def get_preferences(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Get current email digest preferences.

    Returns the user's digest settings including:
    - Whether digest is enabled
    - Send time and timezone
    - What content to include
    - Minimum edge threshold
    """
    prefs = get_or_create_digest_preferences(db, user.id)

    return {
        "enabled": prefs.digest_enabled,
        "send_time": f"{prefs.send_hour:02d}:{prefs.send_minute:02d}",
        "send_hour": prefs.send_hour,
        "send_minute": prefs.send_minute,
        "timezone": prefs.timezone,
        "include_edges": prefs.include_edges,
        "include_results": prefs.include_results,
        "include_bankroll": prefs.include_bankroll,
        "min_edge_for_digest": prefs.min_edge_for_digest,
        "last_sent_at": prefs.last_sent_at.isoformat() if prefs.last_sent_at else None
    }


@router.put("/preferences")
def update_preferences(
    update: DigestPreferencesUpdate,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Update email digest preferences.

    Configure when and how you receive your daily digest:
    - **enabled**: Turn digest on/off
    - **send_hour/send_minute**: When to receive (in your timezone)
    - **timezone**: Your timezone (e.g., America/New_York, Europe/London)
    - **include_edges**: Include today's top betting edges
    - **include_results**: Include yesterday's betting results
    - **include_bankroll**: Include bankroll status update
    - **min_edge_for_digest**: Only include edges above this threshold
    """
    prefs = update_digest_preferences(
        db=db,
        user_id=user.id,
        enabled=update.enabled,
        send_hour=update.send_hour,
        send_minute=update.send_minute,
        timezone=update.timezone,
        include_edges=update.include_edges,
        include_results=update.include_results,
        include_bankroll=update.include_bankroll,
        min_edge_for_digest=update.min_edge_for_digest
    )

    return {
        "message": "Preferences updated successfully",
        "preferences": {
            "enabled": prefs.digest_enabled,
            "send_time": f"{prefs.send_hour:02d}:{prefs.send_minute:02d}",
            "timezone": prefs.timezone,
            "include_edges": prefs.include_edges,
            "include_results": prefs.include_results,
            "include_bankroll": prefs.include_bankroll,
            "min_edge_for_digest": prefs.min_edge_for_digest
        }
    }


@router.post("/enable")
def enable_digest(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Enable daily email digest.

    Quick endpoint to turn on the daily digest with current settings.
    """
    prefs = update_digest_preferences(db, user.id, enabled=True)
    return {
        "message": "Daily digest enabled",
        "send_time": f"{prefs.send_hour:02d}:{prefs.send_minute:02d} {prefs.timezone}"
    }


@router.post("/disable")
def disable_digest(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Disable daily email digest.

    Stop receiving daily digest emails. Your preferences are preserved
    and can be re-enabled at any time.
    """
    update_digest_preferences(db, user.id, enabled=False)
    return {"message": "Daily digest disabled"}


@router.post("/test")
async def send_test(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Send a test digest email immediately.

    Use this to preview what your daily digest will look like.
    The email will be sent to your registered email address.

    **Note:** This does not affect your regular digest schedule.
    """
    result = await send_test_digest(db, user.id)

    if not result["success"]:
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to send test digest")
        )

    return {
        "message": "Test digest sent successfully",
        "sent_to": result["email"],
        "content_preview": result["content_preview"]
    }


@router.get("/preview")
def preview_digest(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Preview the current digest content without sending an email.

    Returns what would be included in today's digest based on
    your current preferences. Useful for checking the content
    before enabling the digest.
    """
    prefs = get_or_create_digest_preferences(db, user.id)

    content = generate_digest_content(
        db,
        user,
        include_edges=prefs.include_edges,
        include_results=prefs.include_results,
        include_bankroll=prefs.include_bankroll,
        min_edge=prefs.min_edge_for_digest
    )

    return {
        "generated_at": content["generated_at"],
        "top_edges": content.get("top_edges", []),
        "yesterday_results": content.get("yesterday_results"),
        "bankroll": content.get("bankroll"),
        "preferences": {
            "include_edges": prefs.include_edges,
            "include_results": prefs.include_results,
            "include_bankroll": prefs.include_bankroll,
            "min_edge_for_digest": prefs.min_edge_for_digest
        }
    }


@router.get("/edges/today")
def get_todays_edges(
    limit: int = Query(5, ge=1, le=20, description="Number of edges to return"),
    min_edge: float = Query(0, ge=0, le=20, description="Minimum edge percentage"),
    db: Session = Depends(get_db)
):
    """
    Get today's top betting edges.

    Returns the highest-value edges for today's games, which would
    be included in the daily digest.

    This endpoint is public (no auth required) but shows limited data.
    """
    edges = get_top_edges_today(db, limit=limit)

    # Filter by minimum edge
    if min_edge > 0:
        edges = [e for e in edges if e["edge"] >= min_edge]

    return {
        "date": "today",
        "total_edges": len(edges),
        "edges": edges
    }


@router.get("/timezones")
def list_timezones():
    """
    List common timezones for digest scheduling.

    Returns a list of common timezone names that can be used
    when setting your digest preferences.
    """
    return {
        "timezones": [
            {"value": "America/New_York", "label": "Eastern Time (ET)"},
            {"value": "America/Chicago", "label": "Central Time (CT)"},
            {"value": "America/Denver", "label": "Mountain Time (MT)"},
            {"value": "America/Los_Angeles", "label": "Pacific Time (PT)"},
            {"value": "America/Phoenix", "label": "Arizona (no DST)"},
            {"value": "America/Anchorage", "label": "Alaska Time"},
            {"value": "Pacific/Honolulu", "label": "Hawaii Time"},
            {"value": "Europe/London", "label": "London (GMT/BST)"},
            {"value": "Europe/Paris", "label": "Paris (CET/CEST)"},
            {"value": "Europe/Berlin", "label": "Berlin (CET/CEST)"},
            {"value": "Asia/Tokyo", "label": "Tokyo (JST)"},
            {"value": "Asia/Shanghai", "label": "Shanghai (CST)"},
            {"value": "Australia/Sydney", "label": "Sydney (AEST/AEDT)"},
            {"value": "UTC", "label": "UTC"}
        ]
    }
