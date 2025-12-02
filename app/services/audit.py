import json
from typing import Optional, Any, Dict, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db import AuditLog


def log_action(
    db: Session,
    action: str,
    user_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    old_value: Any = None,
    new_value: Any = None,
    status: str = "success",
    error_message: Optional[str] = None
) -> AuditLog:
    old_val_str = json.dumps(old_value) if old_value is not None else None
    new_val_str = json.dumps(new_value) if new_value is not None else None
    
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        old_value=old_val_str,
        new_value=new_val_str,
        status=status,
        error_message=error_message
    )
    
    db.add(log)
    db.commit()
    db.refresh(log)
    
    return log


def get_user_audit_logs(
    db: Session,
    user_id: int,
    limit: int = 50,
    offset: int = 0,
    action_filter: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[AuditLog]:
    query = db.query(AuditLog).filter(AuditLog.user_id == user_id)
    
    if action_filter:
        query = query.filter(AuditLog.action.ilike(f"%{action_filter}%"))
    
    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)
    
    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)
    
    return query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit).all()


def get_recent_security_events(
    db: Session,
    user_id: int,
    hours: int = 24
) -> List[AuditLog]:
    security_actions = [
        "login", "logout", "login_failed", "password_change",
        "2fa_enabled", "2fa_disabled", "session_revoked",
        "backup_code_used", "password_reset"
    ]
    
    since = datetime.utcnow() - timedelta(hours=hours)
    
    return db.query(AuditLog).filter(
        AuditLog.user_id == user_id,
        AuditLog.action.in_(security_actions),
        AuditLog.created_at >= since
    ).order_by(desc(AuditLog.created_at)).all()


def get_failed_login_attempts(
    db: Session,
    ip_address: str,
    minutes: int = 15
) -> int:
    since = datetime.utcnow() - timedelta(minutes=minutes)
    
    return db.query(AuditLog).filter(
        AuditLog.action == "login_failed",
        AuditLog.ip_address == ip_address,
        AuditLog.created_at >= since
    ).count()


def get_system_audit_logs(
    db: Session,
    limit: int = 100,
    offset: int = 0,
    action_filter: Optional[str] = None
) -> List[AuditLog]:
    query = db.query(AuditLog)
    
    if action_filter:
        query = query.filter(AuditLog.action.ilike(f"%{action_filter}%"))
    
    return query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit).all()


def cleanup_old_logs(db: Session, days: int = 90) -> int:
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    count = db.query(AuditLog).filter(
        AuditLog.created_at < cutoff
    ).delete()
    
    db.commit()
    
    return count


AUDIT_ACTIONS = {
    "AUTH": {
        "login": "User logged in",
        "logout": "User logged out",
        "login_failed": "Failed login attempt",
        "register": "New user registered",
        "password_change": "Password changed",
        "password_reset_request": "Password reset requested",
        "password_reset": "Password was reset",
    },
    "2FA": {
        "2fa_setup_started": "2FA setup initiated",
        "2fa_enabled": "2FA enabled",
        "2fa_disabled": "2FA disabled",
        "2fa_verified": "2FA code verified",
        "2fa_failed": "2FA verification failed",
        "backup_code_used": "Backup code used",
        "backup_codes_regenerated": "Backup codes regenerated",
    },
    "SESSION": {
        "session_created": "New session created",
        "session_revoked": "Session revoked",
        "all_sessions_revoked": "All sessions revoked",
        "session_refreshed": "Session refreshed",
    },
    "PROFILE": {
        "profile_updated": "Profile updated",
        "email_changed": "Email changed",
        "display_name_changed": "Display name changed",
        "currency_changed": "Preferred currency changed",
    },
    "BETTING": {
        "bet_placed": "Bet tracked",
        "bet_settled": "Bet settled",
        "recommendation_generated": "Recommendations generated",
        "parlay_created": "Parlay created",
    },
    "ALERT": {
        "alert_created": "Alert created",
        "alert_updated": "Alert updated",
        "alert_deleted": "Alert deleted",
        "alert_triggered": "Alert triggered",
    },
    "WEBHOOK": {
        "webhook_created": "Webhook created",
        "webhook_updated": "Webhook updated",
        "webhook_deleted": "Webhook deleted",
        "webhook_triggered": "Webhook triggered",
    },
}
