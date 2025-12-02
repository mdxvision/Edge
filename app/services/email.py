import os
import secrets
import hashlib
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.db import User, PasswordResetToken


SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "noreply@edgebet.app")
APP_URL = os.environ.get("APP_URL", "http://localhost:5000")


def is_email_configured() -> bool:
    return bool(SENDGRID_API_KEY)


async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None
) -> bool:
    if not SENDGRID_API_KEY:
        return False
    
    try:
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {SENDGRID_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "personalizations": [{"to": [{"email": to_email}]}],
                    "from": {"email": FROM_EMAIL, "name": "EdgeBet"},
                    "subject": subject,
                    "content": [
                        {"type": "text/plain", "value": text_content or html_content},
                        {"type": "text/html", "value": html_content}
                    ]
                }
            )
        
        return response.status_code in [200, 201, 202]
    except Exception as e:
        return False


def generate_reset_token(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.is_used == False
    ).update({"is_used": True})
    
    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    db.add(reset_token)
    db.commit()
    
    return token


def verify_reset_token(db: Session, token: str) -> Optional[User]:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    reset = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash,
        PasswordResetToken.is_used == False,
        PasswordResetToken.expires_at > datetime.utcnow()
    ).first()
    
    if not reset:
        return None
    
    user = db.query(User).filter(User.id == reset.user_id).first()
    return user


def use_reset_token(db: Session, token: str) -> bool:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    result = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash,
        PasswordResetToken.is_used == False
    ).update({"is_used": True})
    
    db.commit()
    return result > 0


async def send_verification_email(user: User, verification_token: str) -> bool:
    verify_url = f"{APP_URL}/verify-email?token={verification_token}"
    
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h1 style="color: #2563eb;">Welcome to EdgeBet!</h1>
        <p>Hi {user.username},</p>
        <p>Please verify your email address by clicking the button below:</p>
        <p style="text-align: center;">
            <a href="{verify_url}" style="display: inline-block; padding: 12px 24px; background-color: #2563eb; color: white; text-decoration: none; border-radius: 6px;">
                Verify Email
            </a>
        </p>
        <p>Or copy and paste this link: {verify_url}</p>
        <p>This link expires in 24 hours.</p>
        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">
        <p style="color: #6b7280; font-size: 12px;">
            EdgeBet - Sports Analytics Platform<br>
            This is an automated message, please do not reply.
        </p>
    </body>
    </html>
    """
    
    return await send_email(
        to_email=user.email,
        subject="Verify your EdgeBet account",
        html_content=html
    )


async def send_password_reset_email(user: User, reset_token: str) -> bool:
    reset_url = f"{APP_URL}/reset-password?token={reset_token}"
    
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h1 style="color: #2563eb;">Password Reset Request</h1>
        <p>Hi {user.username},</p>
        <p>We received a request to reset your password. Click the button below to create a new password:</p>
        <p style="text-align: center;">
            <a href="{reset_url}" style="display: inline-block; padding: 12px 24px; background-color: #2563eb; color: white; text-decoration: none; border-radius: 6px;">
                Reset Password
            </a>
        </p>
        <p>Or copy and paste this link: {reset_url}</p>
        <p>This link expires in 1 hour.</p>
        <p>If you didn't request this, you can safely ignore this email.</p>
        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">
        <p style="color: #6b7280; font-size: 12px;">
            EdgeBet - Sports Analytics Platform<br>
            This is an automated message, please do not reply.
        </p>
    </body>
    </html>
    """
    
    return await send_email(
        to_email=user.email,
        subject="Reset your EdgeBet password",
        html_content=html
    )


async def send_alert_notification(
    user: User,
    alert_name: str,
    alert_details: str
) -> bool:
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h1 style="color: #2563eb;">Alert Triggered: {alert_name}</h1>
        <p>Hi {user.username},</p>
        <p>Your alert has been triggered:</p>
        <div style="background-color: #f3f4f6; padding: 16px; border-radius: 8px; margin: 16px 0;">
            {alert_details}
        </div>
        <p style="text-align: center;">
            <a href="{APP_URL}/recommendations" style="display: inline-block; padding: 12px 24px; background-color: #2563eb; color: white; text-decoration: none; border-radius: 6px;">
                View Recommendations
            </a>
        </p>
        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">
        <p style="color: #6b7280; font-size: 12px;">
            EdgeBet - Sports Analytics Platform<br>
            <a href="{APP_URL}/profile/alerts">Manage your alerts</a>
        </p>
    </body>
    </html>
    """
    
    return await send_email(
        to_email=user.email,
        subject=f"EdgeBet Alert: {alert_name}",
        html_content=html
    )


async def send_2fa_enabled_email(user: User) -> bool:
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h1 style="color: #22c55e;">Two-Factor Authentication Enabled</h1>
        <p>Hi {user.username},</p>
        <p>Two-factor authentication has been successfully enabled on your EdgeBet account.</p>
        <p>From now on, you'll need to enter a verification code from your authenticator app when logging in.</p>
        <p style="color: #dc2626;"><strong>Important:</strong> Make sure to keep your backup codes in a safe place!</p>
        <p>If you didn't make this change, please contact us immediately.</p>
        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">
        <p style="color: #6b7280; font-size: 12px;">
            EdgeBet - Sports Analytics Platform
        </p>
    </body>
    </html>
    """
    
    return await send_email(
        to_email=user.email,
        subject="Two-Factor Authentication Enabled",
        html_content=html
    )
