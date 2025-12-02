from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.db import get_db, User, Client
from app.services.auth import (
    create_user,
    authenticate_user,
    create_session,
    validate_session,
    refresh_session,
    invalidate_session,
    update_password,
    get_user_by_id
)

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    initial_bankroll: float = 10000.0
    risk_profile: str = "balanced"


class LoginRequest(BaseModel):
    email_or_username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: str
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    if not credentials:
        return None
    
    user = validate_session(db, credentials.credentials)
    return user


def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = validate_session(db, credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    return user


@router.post("/register", response_model=TokenResponse)
def register(
    request: RegisterRequest,
    req: Request,
    db: Session = Depends(get_db)
):
    if len(request.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    if len(request.username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    
    try:
        user = create_user(
            db=db,
            email=request.email,
            username=request.username,
            password=request.password,
            initial_bankroll=request.initial_bankroll,
            risk_profile=request.risk_profile
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    ip_address = req.client.host if req.client else None
    user_agent = req.headers.get("user-agent")
    
    access_token, refresh_token, expires_at = create_session(
        db=db,
        user=user,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    client = db.query(Client).filter(Client.id == user.client_id).first()
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at.isoformat(),
        user={
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "client_id": user.client_id,
            "client": {
                "id": client.id,
                "name": client.name,
                "bankroll": client.bankroll,
                "risk_profile": client.risk_profile
            } if client else None
        }
    )


@router.post("/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    req: Request,
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, request.email_or_username, request.password)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    ip_address = req.client.host if req.client else None
    user_agent = req.headers.get("user-agent")
    
    access_token, refresh_token, expires_at = create_session(
        db=db,
        user=user,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    client = db.query(Client).filter(Client.id == user.client_id).first()
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at.isoformat(),
        user={
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "client_id": user.client_id,
            "client": {
                "id": client.id,
                "name": client.name,
                "bankroll": client.bankroll,
                "risk_profile": client.risk_profile
            } if client else None
        }
    )


@router.post("/refresh")
def refresh(
    request: RefreshRequest,
    db: Session = Depends(get_db)
):
    result = refresh_session(db, request.refresh_token)
    
    if not result:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    access_token, refresh_token, expires_at = result
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_at": expires_at.isoformat()
    }


@router.post("/logout")
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    success = invalidate_session(db, credentials.credentials)
    
    if not success:
        raise HTTPException(status_code=400, detail="Session not found")
    
    return {"message": "Logged out successfully"}


@router.get("/me")
def get_current_user_info(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == user.client_id).first()
    
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "is_verified": user.is_verified,
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "created_at": user.created_at.isoformat(),
        "client_id": user.client_id,
        "client": {
            "id": client.id,
            "name": client.name,
            "bankroll": client.bankroll,
            "risk_profile": client.risk_profile
        } if client else None
    }


@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    from app.services.auth import verify_password
    
    if not verify_password(user.password_hash, request.current_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    if len(request.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    
    update_password(db, user, request.new_password)
    
    return {"message": "Password changed successfully"}


@router.get("/validate")
def validate_token(
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not user:
        return {"valid": False, "user": None}
    
    client = db.query(Client).filter(Client.id == user.client_id).first()
    
    return {
        "valid": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "client_id": user.client_id,
            "client": {
                "id": client.id,
                "name": client.name,
                "bankroll": client.bankroll,
                "risk_profile": client.risk_profile
            } if client else None
        }
    }
