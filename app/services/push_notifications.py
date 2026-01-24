"""
Push Notifications Service

Handles Firebase Cloud Messaging for mobile and web push notifications.
Includes quiet hours, rate limiting, and configurable thresholds.
"""
import os
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.db import User, UserDevice, NotificationPreferences
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Firebase Admin SDK - optional import
try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    firebase_admin = None
    credentials = None
    messaging = None

# Initialize Firebase
_firebase_initialized = False
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH")
FIREBASE_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS_JSON")  # Alternative: JSON string


def init_firebase():
    """Initialize Firebase Admin SDK."""
    global _firebase_initialized

    if not FIREBASE_AVAILABLE:
        return False

    if _firebase_initialized:
        return True

    try:
        if FIREBASE_CREDENTIALS_PATH and os.path.exists(FIREBASE_CREDENTIALS_PATH):
            cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
        elif FIREBASE_CREDENTIALS_JSON:
            cred_dict = json.loads(FIREBASE_CREDENTIALS_JSON)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
        return _firebase_initialized
    except Exception as e:
        print(f"Firebase initialization error: {e}")
        return False


async def send_push_notification(
    token: str,
    title: str,
    body: str,
    data: Optional[Dict[str, str]] = None,
    image_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send a push notification to a single device.

    Args:
        token: Firebase device token
        title: Notification title
        body: Notification body text
        data: Optional data payload
        image_url: Optional image URL for rich notifications

    Returns:
        Response from Firebase
    """
    if not FIREBASE_AVAILABLE or not init_firebase():
        return {"success": False, "error": "Firebase not configured"}

    notification = messaging.Notification(
        title=title,
        body=body,
        image=image_url
    )

    message = messaging.Message(
        notification=notification,
        data=data or {},
        token=token
    )

    try:
        response = messaging.send(message)
        return {"success": True, "message_id": response}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def send_bulk_notifications(
    tokens: List[str],
    title: str,
    body: str,
    data: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Send push notifications to multiple devices.

    Args:
        tokens: List of Firebase device tokens
        title: Notification title
        body: Notification body text
        data: Optional data payload

    Returns:
        Summary of send results
    """
    if not FIREBASE_AVAILABLE or not init_firebase():
        return {"success": False, "error": "Firebase not configured"}

    if not tokens:
        return {"success": False, "error": "No tokens provided"}

    notification = messaging.Notification(
        title=title,
        body=body
    )

    message = messaging.MulticastMessage(
        notification=notification,
        data=data or {},
        tokens=tokens
    )

    try:
        response = messaging.send_multicast(message)
        return {
            "success": True,
            "success_count": response.success_count,
            "failure_count": response.failure_count,
            "responses": [
                {"success": r.success, "message_id": r.message_id if r.success else None}
                for r in response.responses
            ]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def send_notification_to_user(
    db: Session,
    user_id: int,
    title: str,
    body: str,
    data: Optional[Dict[str, str]] = None,
    notification_type: str = "general"
) -> Dict[str, Any]:
    """
    Send notification to all devices of a specific user.

    Args:
        db: Database session
        user_id: User ID to send notification to
        title: Notification title
        body: Notification body
        data: Optional data payload
        notification_type: Type of notification for filtering
    """
    devices = db.query(UserDevice).filter(
        UserDevice.user_id == user_id,
        UserDevice.is_active == True
    ).all()

    if not devices:
        return {"success": False, "error": "No registered devices"}

    tokens = [d.device_token for d in devices]

    # Add notification type to data
    notification_data = data or {}
    notification_data["type"] = notification_type
    notification_data["timestamp"] = datetime.utcnow().isoformat()

    return await send_bulk_notifications(tokens, title, body, notification_data)


# Notification templates for common events

async def notify_high_edge_bet(
    db: Session,
    user_id: int,
    sport: str,
    matchup: str,
    edge: float,
    bet_type: str
):
    """Notify user of a high edge betting opportunity."""
    title = f"High Edge Alert: {sport}"
    body = f"{matchup} - {edge:.1f}% edge on {bet_type}"
    data = {
        "type": "high_edge",
        "sport": sport,
        "edge": str(edge)
    }
    return await send_notification_to_user(db, user_id, title, body, data, "high_edge")


async def notify_line_movement(
    db: Session,
    user_id: int,
    sport: str,
    matchup: str,
    old_line: str,
    new_line: str
):
    """Notify user of significant line movement."""
    title = f"Line Movement: {sport}"
    body = f"{matchup}: {old_line} -> {new_line}"
    data = {
        "type": "line_movement",
        "sport": sport,
        "old_line": old_line,
        "new_line": new_line
    }
    return await send_notification_to_user(db, user_id, title, body, data, "line_movement")


async def notify_game_start(
    db: Session,
    user_id: int,
    sport: str,
    matchup: str,
    start_time: str
):
    """Notify user that a tracked game is starting."""
    title = f"Game Starting: {sport}"
    body = f"{matchup} starting now"
    data = {
        "type": "game_start",
        "sport": sport,
        "start_time": start_time
    }
    return await send_notification_to_user(db, user_id, title, body, data, "game_start")


async def notify_bet_result(
    db: Session,
    user_id: int,
    result: str,
    matchup: str,
    profit_loss: float
):
    """Notify user of paper trade result."""
    title = f"Bet {result.title()}"
    emoji = "+" if profit_loss > 0 else ""
    body = f"{matchup}: {emoji}${profit_loss:.2f}"
    data = {
        "type": "bet_result",
        "result": result,
        "profit_loss": str(profit_loss)
    }
    return await send_notification_to_user(db, user_id, title, body, data, "bet_result")


# Device management functions

async def register_device(
    db: Session,
    user_id: int,
    device_token: str,
    device_type: str,
    device_name: Optional[str] = None
) -> UserDevice:
    """Register a device for push notifications."""
    # Check if token already exists
    existing = db.query(UserDevice).filter(
        UserDevice.device_token == device_token
    ).first()

    if existing:
        # Update existing device
        existing.user_id = user_id
        existing.device_type = device_type
        existing.device_name = device_name
        existing.is_active = True
        existing.last_used = datetime.utcnow()
        db.commit()
        return existing

    # Create new device
    device = UserDevice(
        user_id=user_id,
        device_token=device_token,
        device_type=device_type,
        device_name=device_name,
        is_active=True
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


async def unregister_device(
    db: Session,
    user_id: int,
    device_token: str
) -> bool:
    """Unregister a device from push notifications."""
    device = db.query(UserDevice).filter(
        UserDevice.user_id == user_id,
        UserDevice.device_token == device_token
    ).first()

    if device:
        device.is_active = False
        db.commit()
        return True
    return False


async def get_user_devices(db: Session, user_id: int) -> List[Dict[str, Any]]:
    """Get all devices registered for a user."""
    devices = db.query(UserDevice).filter(
        UserDevice.user_id == user_id,
        UserDevice.is_active == True
    ).all()

    return [
        {
            "id": d.id,
            "device_type": d.device_type,
            "device_name": d.device_name,
            "last_used": d.last_used.isoformat() if d.last_used else None,
            "created_at": d.created_at.isoformat()
        }
        for d in devices
    ]


# Notification preferences and control functions

def is_in_quiet_hours(prefs: NotificationPreferences) -> bool:
    """Check if current time is within user's quiet hours."""
    if not prefs.quiet_hours_enabled:
        return False

    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(prefs.timezone or "America/New_York")
        now = datetime.now(tz)
        current_hour = now.hour

        start = prefs.quiet_start_hour
        end = prefs.quiet_end_hour

        # Handle overnight quiet hours (e.g., 22:00 to 08:00)
        if start > end:
            return current_hour >= start or current_hour < end
        else:
            return start <= current_hour < end
    except Exception as e:
        logger.warning(f"Error checking quiet hours: {e}")
        return False


def check_rate_limit(db: Session, prefs: NotificationPreferences) -> bool:
    """
    Check if user is under rate limit.

    Returns True if notification can be sent, False if rate limited.
    """
    now = datetime.utcnow()
    hour_ago = now - timedelta(hours=1)

    if prefs.last_notification_at and prefs.last_notification_at > hour_ago:
        if prefs.notifications_this_hour >= prefs.max_notifications_per_hour:
            return False
    else:
        # Reset counter if over an hour has passed
        prefs.notifications_this_hour = 0
        db.commit()

    return True


def record_notification(db: Session, prefs: NotificationPreferences):
    """Record that a notification was sent for rate limiting."""
    now = datetime.utcnow()
    hour_ago = now - timedelta(hours=1)

    if prefs.last_notification_at and prefs.last_notification_at > hour_ago:
        prefs.notifications_this_hour += 1
    else:
        prefs.notifications_this_hour = 1

    prefs.last_notification_at = now
    db.commit()


def can_send_notification(
    db: Session,
    user_id: int,
    notification_type: str = "general",
    sport: Optional[str] = None,
    edge_value: Optional[float] = None,
    arb_value: Optional[float] = None
) -> bool:
    """
    Check if a notification can be sent to a user.

    Checks:
    - Push notifications enabled
    - Quiet hours
    - Rate limit
    - Sport-specific settings
    - Edge/arb thresholds
    """
    prefs = db.query(NotificationPreferences).filter(
        NotificationPreferences.user_id == user_id
    ).first()

    # No preferences = use defaults (allow)
    if not prefs:
        return True

    # Check if push enabled
    if not prefs.push_enabled:
        logger.debug(f"Push disabled for user {user_id}")
        return False

    # Check quiet hours
    if is_in_quiet_hours(prefs):
        logger.debug(f"User {user_id} in quiet hours")
        return False

    # Check rate limit
    if not check_rate_limit(db, prefs):
        logger.debug(f"User {user_id} rate limited")
        return False

    # Check sport-specific settings
    if sport and prefs.sports_enabled:
        try:
            sports_config = json.loads(prefs.sports_enabled)
            if not sports_config.get(sport, True):
                logger.debug(f"Sport {sport} disabled for user {user_id}")
                return False
        except json.JSONDecodeError:
            pass

    # Check edge threshold
    if edge_value is not None and edge_value < prefs.min_edge_threshold:
        logger.debug(f"Edge {edge_value} below threshold {prefs.min_edge_threshold}")
        return False

    # Check arb threshold
    if arb_value is not None and arb_value < prefs.min_arb_threshold:
        logger.debug(f"Arb {arb_value} below threshold {prefs.min_arb_threshold}")
        return False

    return True


async def get_or_create_preferences(db: Session, user_id: int) -> NotificationPreferences:
    """Get user's notification preferences, creating defaults if needed."""
    prefs = db.query(NotificationPreferences).filter(
        NotificationPreferences.user_id == user_id
    ).first()

    if not prefs:
        prefs = NotificationPreferences(
            user_id=user_id,
            push_enabled=True,
            min_edge_threshold=5.0,
            min_arb_threshold=1.0,
        )
        db.add(prefs)
        db.commit()
        db.refresh(prefs)

    return prefs


async def update_preferences(
    db: Session,
    user_id: int,
    **kwargs
) -> NotificationPreferences:
    """Update user's notification preferences."""
    prefs = await get_or_create_preferences(db, user_id)

    for key, value in kwargs.items():
        if hasattr(prefs, key):
            if key == "sports_enabled" and isinstance(value, dict):
                value = json.dumps(value)
            setattr(prefs, key, value)

    db.commit()
    db.refresh(prefs)
    return prefs


# Enhanced notification functions with preference checking

async def notify_edge_alert(
    db: Session,
    user_id: int,
    sport: str,
    matchup: str,
    edge: float,
    pick: str,
    odds: int
) -> Dict[str, Any]:
    """
    Send edge alert with preference checking.

    Respects quiet hours, rate limits, and edge thresholds.
    """
    if not can_send_notification(db, user_id, "edge_alert", sport, edge_value=edge):
        return {"success": False, "reason": "notification_suppressed"}

    title = f"🎯 {sport} Edge Alert"
    body = f"{matchup}: {pick} ({odds:+d}) - {edge:.1f}% edge"
    data = {
        "type": "edge_alert",
        "sport": sport,
        "edge": str(edge),
        "pick": pick,
        "odds": str(odds)
    }

    result = await send_notification_to_user(db, user_id, title, body, data, "edge_alert")

    if result.get("success"):
        prefs = db.query(NotificationPreferences).filter(
            NotificationPreferences.user_id == user_id
        ).first()
        if prefs:
            record_notification(db, prefs)

    return result


async def notify_arb_alert(
    db: Session,
    user_id: int,
    sport: str,
    matchup: str,
    profit_percent: float,
    book1: str,
    book2: str
) -> Dict[str, Any]:
    """
    Send arbitrage alert with preference checking.

    Respects quiet hours, rate limits, and arb thresholds.
    """
    if not can_send_notification(db, user_id, "arb_alert", sport, arb_value=profit_percent):
        return {"success": False, "reason": "notification_suppressed"}

    title = f"💰 Arbitrage Found"
    body = f"{matchup}: {profit_percent:.2f}% profit ({book1} vs {book2})"
    data = {
        "type": "arb_alert",
        "sport": sport,
        "profit": str(profit_percent),
        "book1": book1,
        "book2": book2
    }

    result = await send_notification_to_user(db, user_id, title, body, data, "arb_alert")

    if result.get("success"):
        prefs = db.query(NotificationPreferences).filter(
            NotificationPreferences.user_id == user_id
        ).first()
        if prefs:
            record_notification(db, prefs)

    return result


async def broadcast_edge_alert(
    db: Session,
    sport: str,
    matchup: str,
    edge: float,
    pick: str,
    odds: int
) -> Dict[str, Any]:
    """
    Broadcast edge alert to all eligible users.

    Respects individual user preferences.
    """
    users = db.query(User).filter(User.is_active == True).all()

    sent = 0
    skipped = 0

    for user in users:
        result = await notify_edge_alert(db, user.id, sport, matchup, edge, pick, odds)
        if result.get("success"):
            sent += 1
        else:
            skipped += 1

    logger.info(f"Broadcast edge alert: {sent} sent, {skipped} skipped")
    return {"sent": sent, "skipped": skipped}


async def broadcast_arb_alert(
    db: Session,
    sport: str,
    matchup: str,
    profit_percent: float,
    book1: str,
    book2: str
) -> Dict[str, Any]:
    """
    Broadcast arbitrage alert to all eligible users.

    Respects individual user preferences.
    """
    users = db.query(User).filter(User.is_active == True).all()

    sent = 0
    skipped = 0

    for user in users:
        result = await notify_arb_alert(db, user.id, sport, matchup, profit_percent, book1, book2)
        if result.get("success"):
            sent += 1
        else:
            skipped += 1

    logger.info(f"Broadcast arb alert: {sent} sent, {skipped} skipped")
    return {"sent": sent, "skipped": skipped}
