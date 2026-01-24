"""
Notifications router for managing push notification settings and devices.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime

from app.db import get_db, User, UserDevice, NotificationPreferences
from app.routers.auth import require_auth
from app.services.push_notifications import (
    register_device,
    unregister_device,
    get_user_devices,
    get_or_create_preferences,
    update_preferences,
    send_push_notification,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


# Request/Response Models

class DeviceRegisterRequest(BaseModel):
    device_token: str = Field(..., min_length=10)
    device_type: str = Field(..., pattern="^(ios|android|web)$")
    device_name: Optional[str] = None


class DeviceResponse(BaseModel):
    id: int
    device_type: str
    device_name: Optional[str]
    last_used: Optional[str]
    created_at: str


class NotificationPrefsRequest(BaseModel):
    push_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    min_edge_threshold: Optional[float] = Field(None, ge=0, le=50)
    min_arb_threshold: Optional[float] = Field(None, ge=0, le=20)
    sports_enabled: Optional[Dict[str, bool]] = None
    quiet_hours_enabled: Optional[bool] = None
    quiet_start_hour: Optional[int] = Field(None, ge=0, le=23)
    quiet_end_hour: Optional[int] = Field(None, ge=0, le=23)
    timezone: Optional[str] = None
    max_notifications_per_hour: Optional[int] = Field(None, ge=1, le=100)


class NotificationPrefsResponse(BaseModel):
    push_enabled: bool
    email_enabled: bool
    min_edge_threshold: float
    min_arb_threshold: float
    sports_enabled: Dict[str, bool]
    quiet_hours_enabled: bool
    quiet_start_hour: int
    quiet_end_hour: int
    timezone: str
    max_notifications_per_hour: int


class TestNotificationRequest(BaseModel):
    title: str = "Test Notification"
    body: str = "This is a test notification from Edge"


# Device Management Endpoints

@router.post("/devices", response_model=DeviceResponse)
async def register_user_device(
    request: DeviceRegisterRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Register a device for push notifications.

    Device types: ios, android, web
    """
    device = await register_device(
        db=db,
        user_id=user.id,
        device_token=request.device_token,
        device_type=request.device_type,
        device_name=request.device_name
    )

    return DeviceResponse(
        id=device.id,
        device_type=device.device_type,
        device_name=device.device_name,
        last_used=device.last_used.isoformat() if device.last_used else None,
        created_at=device.created_at.isoformat()
    )


@router.get("/devices", response_model=List[DeviceResponse])
async def list_user_devices(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """List all registered devices for the current user."""
    devices = await get_user_devices(db, user.id)
    return [DeviceResponse(**d) for d in devices]


@router.delete("/devices/{device_token}")
async def remove_device(
    device_token: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Unregister a device from push notifications."""
    success = await unregister_device(db, user.id, device_token)

    if not success:
        raise HTTPException(status_code=404, detail="Device not found")

    return {"success": True, "message": "Device unregistered"}


# Notification Preferences Endpoints

@router.get("/preferences", response_model=NotificationPrefsResponse)
async def get_notification_preferences(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get notification preferences for the current user."""
    prefs = await get_or_create_preferences(db, user.id)

    # Parse sports_enabled JSON
    sports = {}
    if prefs.sports_enabled:
        try:
            import json
            sports = json.loads(prefs.sports_enabled)
        except:
            pass

    return NotificationPrefsResponse(
        push_enabled=prefs.push_enabled,
        email_enabled=prefs.email_enabled,
        min_edge_threshold=prefs.min_edge_threshold,
        min_arb_threshold=prefs.min_arb_threshold,
        sports_enabled=sports,
        quiet_hours_enabled=prefs.quiet_hours_enabled,
        quiet_start_hour=prefs.quiet_start_hour,
        quiet_end_hour=prefs.quiet_end_hour,
        timezone=prefs.timezone,
        max_notifications_per_hour=prefs.max_notifications_per_hour
    )


@router.put("/preferences", response_model=NotificationPrefsResponse)
async def update_notification_preferences(
    request: NotificationPrefsRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Update notification preferences.

    Only provided fields will be updated.
    """
    update_data = request.model_dump(exclude_none=True)

    prefs = await update_preferences(db, user.id, **update_data)

    # Parse sports_enabled JSON
    sports = {}
    if prefs.sports_enabled:
        try:
            import json
            sports = json.loads(prefs.sports_enabled)
        except:
            pass

    return NotificationPrefsResponse(
        push_enabled=prefs.push_enabled,
        email_enabled=prefs.email_enabled,
        min_edge_threshold=prefs.min_edge_threshold,
        min_arb_threshold=prefs.min_arb_threshold,
        sports_enabled=sports,
        quiet_hours_enabled=prefs.quiet_hours_enabled,
        quiet_start_hour=prefs.quiet_start_hour,
        quiet_end_hour=prefs.quiet_end_hour,
        timezone=prefs.timezone,
        max_notifications_per_hour=prefs.max_notifications_per_hour
    )


@router.post("/preferences/sports/{sport}")
async def enable_sport_notifications(
    sport: str,
    enabled: bool = True,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Enable or disable notifications for a specific sport."""
    import json

    prefs = await get_or_create_preferences(db, user.id)

    sports = {}
    if prefs.sports_enabled:
        try:
            sports = json.loads(prefs.sports_enabled)
        except:
            pass

    sports[sport] = enabled
    prefs.sports_enabled = json.dumps(sports)
    db.commit()

    return {"sport": sport, "enabled": enabled}


# Test Notification Endpoint

@router.post("/test")
async def send_test_notification(
    request: TestNotificationRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Send a test notification to all user's devices.

    Useful for verifying push notification setup.
    """
    from app.services.push_notifications import send_notification_to_user

    result = await send_notification_to_user(
        db=db,
        user_id=user.id,
        title=request.title,
        body=request.body,
        data={"type": "test"},
        notification_type="test"
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Failed to send notification")
        )

    return {
        "success": True,
        "message": "Test notification sent",
        "details": result
    }


# Quiet Hours Endpoints

# Alert Trigger Endpoints

@router.post("/alerts/scan")
async def trigger_alert_scan(
    sports: Optional[List[str]] = None,
    min_edge: float = 5.0,
    min_arb: float = 1.0,
    db: Session = Depends(get_db)
):
    """
    Manually trigger an edge and arbitrage alert scan.

    Sends notifications to all eligible users for opportunities
    meeting the specified thresholds.
    """
    from app.services.edge_alerts import check_and_send_edge_alerts, check_and_send_arb_alerts

    edge_results = await check_and_send_edge_alerts(
        db=db,
        sports=sports,
        min_edge=min_edge,
        broadcast=True
    )

    arb_results = await check_and_send_arb_alerts(
        db=db,
        sports=sports,
        min_profit=min_arb,
        broadcast=True
    )

    return {
        "edge_alerts": edge_results,
        "arb_alerts": arb_results
    }


@router.get("/alerts/scheduler/status")
async def get_alert_scheduler_status():
    """Get the status of the edge alert scheduler."""
    from app.services.edge_alerts import edge_alert_scheduler
    return edge_alert_scheduler.get_status()


@router.post("/alerts/scheduler/start")
async def start_alert_scheduler(interval_minutes: int = 15):
    """Start the edge alert scheduler."""
    from app.services.edge_alerts import edge_alert_scheduler

    if interval_minutes < 5 or interval_minutes > 60:
        raise HTTPException(status_code=400, detail="Interval must be 5-60 minutes")

    edge_alert_scheduler.start(interval_minutes)
    return {"status": "started", "interval_minutes": interval_minutes}


@router.post("/alerts/scheduler/stop")
async def stop_alert_scheduler():
    """Stop the edge alert scheduler."""
    from app.services.edge_alerts import edge_alert_scheduler
    edge_alert_scheduler.stop()
    return {"status": "stopped"}


@router.put("/quiet-hours")
async def set_quiet_hours(
    enabled: bool,
    start_hour: int = 22,
    end_hour: int = 8,
    timezone: str = "America/New_York",
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Configure quiet hours for notifications.

    During quiet hours, no push notifications will be sent.

    Args:
        enabled: Enable/disable quiet hours
        start_hour: Hour to start quiet period (0-23)
        end_hour: Hour to end quiet period (0-23)
        timezone: User's timezone (e.g., "America/New_York")
    """
    if not 0 <= start_hour <= 23 or not 0 <= end_hour <= 23:
        raise HTTPException(status_code=400, detail="Hours must be 0-23")

    prefs = await update_preferences(
        db, user.id,
        quiet_hours_enabled=enabled,
        quiet_start_hour=start_hour,
        quiet_end_hour=end_hour,
        timezone=timezone
    )

    return {
        "quiet_hours_enabled": prefs.quiet_hours_enabled,
        "quiet_start_hour": prefs.quiet_start_hour,
        "quiet_end_hour": prefs.quiet_end_hour,
        "timezone": prefs.timezone
    }
