from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.db import get_db, User, UserSession, AuditLog
from app.services.auth import validate_session, hash_token
from app.services.totp import (
    setup_2fa, enable_2fa, disable_2fa, verify_2fa,
    regenerate_backup_codes, get_remaining_backup_codes
)
from app.services.audit import log_action, get_user_audit_logs, get_recent_security_events

router = APIRouter(prefix="/security", tags=["security"])


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.split(" ")[1]
    user = validate_session(db, token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    return user


class Setup2FAResponse(BaseModel):
    secret: str
    qr_code: str
    backup_codes: List[str]
    uri: str


class Verify2FARequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=8)


class TwoFAStatusResponse(BaseModel):
    enabled: bool
    verified_at: Optional[datetime] = None
    backup_codes_remaining: int


@router.get("/2fa/status", response_model=TwoFAStatusResponse)
def get_2fa_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return TwoFAStatusResponse(
        enabled=user.totp_enabled or False,  # Handle None case
        verified_at=user.totp_verified_at,
        backup_codes_remaining=get_remaining_backup_codes(user)
    )


@router.post("/2fa/setup", response_model=Setup2FAResponse)
def setup_2fa_endpoint(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is already enabled")
    
    result = setup_2fa(db, user)
    
    log_action(
        db, "2fa_setup_started", user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent")
    )
    
    return Setup2FAResponse(**result)


@router.post("/2fa/enable")
def enable_2fa_endpoint(
    data: Verify2FARequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is already enabled")
    
    if not user.totp_secret:
        raise HTTPException(status_code=400, detail="Please set up 2FA first")
    
    success = enable_2fa(db, user, data.code)
    
    if not success:
        log_action(
            db, "2fa_failed", user.id,
            ip_address=request.client.host if request.client else None,
            status="failed"
        )
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    log_action(
        db, "2fa_enabled", user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent")
    )
    
    return {"message": "2FA enabled successfully"}


@router.post("/2fa/disable")
def disable_2fa_endpoint(
    data: Verify2FARequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled")
    
    success = disable_2fa(db, user, data.code)
    
    if not success:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    log_action(
        db, "2fa_disabled", user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent")
    )
    
    return {"message": "2FA disabled successfully"}


@router.post("/2fa/backup-codes/regenerate")
def regenerate_backup_codes_endpoint(
    data: Verify2FARequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled")
    
    new_codes = regenerate_backup_codes(db, user, data.code)
    
    if not new_codes:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    log_action(
        db, "backup_codes_regenerated", user.id,
        ip_address=request.client.host if request.client else None
    )
    
    return {"backup_codes": new_codes}


class SessionResponse(BaseModel):
    id: int
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime
    expires_at: datetime
    is_current: bool


@router.get("/sessions", response_model=List[SessionResponse])
def get_sessions(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    auth_header = request.headers.get("Authorization", "")
    current_token = auth_header.split(" ")[1] if " " in auth_header else ""
    current_token_hash = hash_token(current_token) if current_token else ""
    
    sessions = db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.is_valid == True
    ).order_by(UserSession.created_at.desc()).all()
    
    return [
        SessionResponse(
            id=s.id,
            ip_address=s.ip_address,
            user_agent=s.user_agent,
            created_at=s.created_at,
            expires_at=s.expires_at,
            is_current=s.session_token == current_token_hash
        )
        for s in sessions
    ]


@router.delete("/sessions/{session_id}")
def revoke_session(
    session_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(UserSession).filter(
        UserSession.id == session_id,
        UserSession.user_id == user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.is_valid = False
    db.commit()
    
    log_action(
        db, "session_revoked", user.id,
        resource_type="session",
        resource_id=session_id,
        ip_address=request.client.host if request.client else None
    )
    
    return {"message": "Session revoked"}


@router.delete("/sessions")
def revoke_all_sessions(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    auth_header = request.headers.get("Authorization", "")
    current_token = auth_header.split(" ")[1] if " " in auth_header else ""
    current_token_hash = hash_token(current_token) if current_token else ""
    
    count = db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.is_valid == True,
        UserSession.session_token != current_token_hash
    ).update({"is_valid": False})
    
    db.commit()
    
    log_action(
        db, "all_sessions_revoked", user.id,
        ip_address=request.client.host if request.client else None,
        new_value={"revoked_count": count}
    )
    
    return {"message": f"Revoked {count} sessions"}


class AuditLogResponse(BaseModel):
    id: int
    action: str
    resource_type: Optional[str]
    ip_address: Optional[str]
    status: str
    created_at: datetime


@router.get("/audit-logs", response_model=List[AuditLogResponse])
def get_audit_logs(
    limit: int = 50,
    offset: int = 0,
    action: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logs = get_user_audit_logs(db, user.id, limit, offset, action)
    
    return [
        AuditLogResponse(
            id=log.id,
            action=log.action,
            resource_type=log.resource_type,
            ip_address=log.ip_address,
            status=log.status,
            created_at=log.created_at
        )
        for log in logs
    ]


@router.get("/security-events", response_model=List[AuditLogResponse])
def get_security_events(
    hours: int = 24,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    events = get_recent_security_events(db, user.id, hours)
    
    return [
        AuditLogResponse(
            id=e.id,
            action=e.action,
            resource_type=e.resource_type,
            ip_address=e.ip_address,
            status=e.status,
            created_at=e.created_at
        )
        for e in events
    ]
