from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date

from app.db import get_db, User, Client
from app.services.auth import validate_session, hash_password
from app.services.email import (
    generate_reset_token, verify_reset_token, use_reset_token,
    send_password_reset_email, is_email_configured
)
from app.services.audit import log_action

router = APIRouter(prefix="/account", tags=["account"])


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.split(" ")[1]
    user = validate_session(db, token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    return user


class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = Field(None, min_length=2, max_length=100)
    preferred_currency: Optional[str] = None


class AgeVerificationRequest(BaseModel):
    date_of_birth: date
    confirm_age: bool = Field(..., description="User confirms they are 21+")


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


class ProfileResponse(BaseModel):
    id: int
    email: str
    username: str
    display_name: Optional[str]
    preferred_currency: str
    is_verified: bool
    is_age_verified: bool
    totp_enabled: bool
    created_at: datetime


@router.get("/profile", response_model=ProfileResponse)
def get_profile(
    user: User = Depends(get_current_user)
):
    return ProfileResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        display_name=user.display_name,
        preferred_currency=user.preferred_currency,
        is_verified=user.is_verified,
        is_age_verified=user.is_age_verified,
        totp_enabled=user.totp_enabled,
        created_at=user.created_at
    )


@router.patch("/profile", response_model=ProfileResponse)
def update_profile(
    data: UpdateProfileRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    old_values = {}
    new_values = {}
    
    if data.display_name is not None:
        old_values["display_name"] = user.display_name
        user.display_name = data.display_name
        new_values["display_name"] = data.display_name
    
    if data.preferred_currency is not None:
        from app.services.currency import get_currency_info
        if not get_currency_info(data.preferred_currency):
            raise HTTPException(status_code=400, detail="Invalid currency")
        old_values["preferred_currency"] = user.preferred_currency
        user.preferred_currency = data.preferred_currency.upper()
        new_values["preferred_currency"] = user.preferred_currency
    
    if new_values:
        user.updated_at = datetime.utcnow()
        db.commit()
        
        log_action(
            db, "profile_updated", user.id,
            ip_address=request.client.host if request.client else None,
            old_value=old_values,
            new_value=new_values
        )
    
    return ProfileResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        display_name=user.display_name,
        preferred_currency=user.preferred_currency,
        is_verified=user.is_verified,
        is_age_verified=user.is_age_verified,
        totp_enabled=user.totp_enabled,
        created_at=user.created_at
    )


@router.post("/verify-age")
def verify_age(
    data: AgeVerificationRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user.is_age_verified:
        raise HTTPException(status_code=400, detail="Age already verified")
    
    if not data.confirm_age:
        raise HTTPException(status_code=400, detail="You must confirm you are 21 or older")
    
    today = date.today()
    age = today.year - data.date_of_birth.year - (
        (today.month, today.day) < (data.date_of_birth.month, data.date_of_birth.day)
    )
    
    if age < 21:
        raise HTTPException(status_code=400, detail="You must be 21 or older to use this platform")
    
    user.date_of_birth = datetime.combine(data.date_of_birth, datetime.min.time())
    user.is_age_verified = True
    user.updated_at = datetime.utcnow()
    db.commit()
    
    log_action(
        db, "age_verified", user.id,
        ip_address=request.client.host if request.client else None
    )
    
    return {"message": "Age verified successfully", "age": age}


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == data.email).first()
    
    if user:
        token = generate_reset_token(db, user)
        
        if is_email_configured():
            await send_password_reset_email(user, token)
        
        log_action(
            db, "password_reset_request", user.id,
            ip_address=request.client.host if request.client else None
        )
    
    return {"message": "If an account exists with that email, a reset link has been sent"}


@router.post("/reset-password")
def reset_password(
    data: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    user = verify_reset_token(db, data.token)
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    from app.services.auth import hash_password, invalidate_all_sessions
    
    user.password_hash = hash_password(data.new_password)
    user.updated_at = datetime.utcnow()
    
    invalidate_all_sessions(db, user.id)
    
    use_reset_token(db, data.token)
    
    db.commit()
    
    log_action(
        db, "password_reset", user.id,
        ip_address=request.client.host if request.client else None
    )
    
    return {"message": "Password reset successfully"}
