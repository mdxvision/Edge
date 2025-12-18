"""
Age verification middleware for blocking unverified users from betting routes.
"""
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.db import get_db, User
from app.routers.auth import require_auth


def require_age_verified(
    user: User = Depends(require_auth),
) -> User:
    """
    Dependency that requires the user to have verified their age (21+).
    Use this on betting-related routes.
    """
    if not user.is_age_verified:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "age_verification_required",
                "message": "You must verify your age (21+) to access betting features"
            }
        )
    return user


def require_2fa_enabled(
    user: User = Depends(require_auth),
) -> User:
    """
    Dependency that requires the user to have 2FA enabled.
    Use this on sensitive routes (account settings, withdrawals, etc).
    """
    if not user.totp_enabled:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "2fa_required",
                "message": "Two-factor authentication must be enabled to access this feature"
            }
        )
    return user


def require_age_and_2fa(
    user: User = Depends(require_auth),
) -> User:
    """
    Dependency that requires both age verification and 2FA.
    Use this on the most sensitive betting routes.
    """
    if not user.is_age_verified:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "age_verification_required",
                "message": "You must verify your age (21+) to access betting features"
            }
        )

    if not user.totp_enabled:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "2fa_required",
                "message": "Two-factor authentication must be enabled to access this feature"
            }
        )

    return user
