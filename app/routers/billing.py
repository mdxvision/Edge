"""
Billing Router

Handles Stripe subscription management, checkout, and webhooks.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import os

from app.db import get_db, User
from app.routers.auth import require_auth
from app.services.subscription import (
    create_checkout_session,
    create_portal_session,
    handle_webhook_event,
    get_subscription_status,
    cancel_subscription,
    SUBSCRIPTION_TIERS,
    TIER_LEVELS,
    check_tier_access
)

router = APIRouter(prefix="/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    price_id: str
    billing_period: str = "monthly"  # monthly or yearly


class SubscriptionResponse(BaseModel):
    tier: str
    status: str
    expires_at: Optional[str]
    features: list[str]


# Feature gating dependency
def require_subscription(required_tier: str = "premium"):
    """Dependency that checks subscription tier."""
    async def dependency(user: User = Depends(require_auth)):
        if not check_tier_access(user, required_tier):
            raise HTTPException(
                status_code=403,
                detail=f"This feature requires a {required_tier} subscription. Please upgrade to access."
            )
        return user
    return dependency


@router.get("/plans")
def get_subscription_plans():
    """Get available subscription plans with pricing."""
    plans = []
    for tier, config in SUBSCRIPTION_TIERS.items():
        plan = {
            "tier": tier,
            "features": config.get("features", []),
        }
        if tier != "free":
            plan["price_monthly"] = config.get("price_monthly", 0) / 100  # Convert cents to dollars
            plan["price_yearly"] = config.get("price_yearly", 0) / 100
            plan["stripe_price_id_monthly"] = config.get("stripe_price_id_monthly")
            plan["stripe_price_id_yearly"] = config.get("stripe_price_id_yearly")
        plans.append(plan)
    return {"plans": plans}


@router.get("/subscription")
async def get_current_subscription(
    user: User = Depends(require_auth)
):
    """Get current user's subscription status."""
    return get_subscription_status(user)


@router.post("/create-checkout-session")
async def create_checkout(
    request: CheckoutRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Create a Stripe checkout session for subscription purchase."""
    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    if not stripe_key:
        raise HTTPException(
            status_code=503,
            detail="Payment processing is not configured. Please contact support."
        )

    try:
        result = await create_checkout_session(
            db=db,
            user=user,
            price_id=request.price_id,
            billing_period=request.billing_period
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.post("/create-portal-session")
async def create_billing_portal(
    user: User = Depends(require_auth)
):
    """Create a Stripe billing portal session for managing subscription."""
    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    if not stripe_key:
        raise HTTPException(
            status_code=503,
            detail="Payment processing is not configured."
        )

    try:
        result = await create_portal_session(user)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create portal session")


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle Stripe webhook events."""
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook not configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing signature header")

    try:
        result = await handle_webhook_event(db, payload, sig_header)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Webhook processing failed")


@router.post("/cancel")
async def cancel_user_subscription(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Cancel subscription at end of billing period."""
    if user.subscription_tier == "free" or not user.subscription_id:
        raise HTTPException(status_code=400, detail="No active subscription to cancel")

    try:
        result = await cancel_subscription(db, user)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/success")
async def checkout_success(session_id: str):
    """Handle successful checkout redirect."""
    return {
        "status": "success",
        "message": "Subscription activated successfully!",
        "session_id": session_id
    }
