"""
Stripe Subscription Service

Handles subscription management, checkout sessions, and webhook processing.
"""
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

# Stripe import - will work if stripe is installed
try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    stripe = None

from app.db import User, PaymentHistory

# Stripe configuration
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

if STRIPE_AVAILABLE and STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

# Subscription tier configuration
SUBSCRIPTION_TIERS = {
    "free": {
        "price": 0,
        "features": [
            "basic_odds",
            "limited_predictions_5_per_day",
            "single_sport"
        ],
        "prediction_limit": 5,
        "sports_limit": 1
    },
    "premium": {
        "price_monthly": 2900,  # $29.00 in cents
        "price_yearly": 29000,  # $290.00 (2 months free)
        "stripe_price_id_monthly": os.getenv("STRIPE_PRICE_PREMIUM_MONTHLY", "price_premium_monthly"),
        "stripe_price_id_yearly": os.getenv("STRIPE_PRICE_PREMIUM_YEARLY", "price_premium_yearly"),
        "features": [
            "all_odds",
            "unlimited_predictions",
            "all_sports",
            "paper_trading",
            "situational_trends",
            "power_ratings",
            "coach_dna",
            "line_movement"
        ],
        "prediction_limit": None,  # Unlimited
        "sports_limit": None  # All sports
    },
    "pro": {
        "price_monthly": 9900,  # $99.00
        "price_yearly": 99000,  # $990.00
        "stripe_price_id_monthly": os.getenv("STRIPE_PRICE_PRO_MONTHLY", "price_pro_monthly"),
        "stripe_price_id_yearly": os.getenv("STRIPE_PRICE_PRO_YEARLY", "price_pro_yearly"),
        "features": [
            "everything_in_premium",
            "api_access",
            "custom_alerts",
            "priority_support",
            "white_label_reports",
            "advanced_analytics",
            "webhook_integrations"
        ],
        "prediction_limit": None,
        "sports_limit": None,
        "api_access": True,
        "api_rate_limit": 100,  # requests per minute
        "api_monthly_limit": 50000
    }
}

TIER_LEVELS = {"free": 0, "premium": 1, "pro": 2}


def get_tier_features(tier: str) -> Dict[str, Any]:
    """Get features for a subscription tier."""
    return SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS["free"])


def check_feature_access(user: User, feature: str) -> bool:
    """Check if user has access to a specific feature."""
    tier = user.subscription_tier or "free"
    tier_config = SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS["free"])

    # Check if subscription is active
    if tier != "free":
        if user.subscription_status != "active":
            tier = "free"
            tier_config = SUBSCRIPTION_TIERS["free"]

    return feature in tier_config.get("features", [])


def check_tier_access(user: User, required_tier: str) -> bool:
    """Check if user's tier meets the required level."""
    user_tier = user.subscription_tier or "free"

    # Check if subscription is active
    if user_tier != "free" and user.subscription_status != "active":
        user_tier = "free"

    return TIER_LEVELS.get(user_tier, 0) >= TIER_LEVELS.get(required_tier, 0)


async def create_checkout_session(
    db: Session,
    user: User,
    price_id: str,
    billing_period: str = "monthly"
) -> Dict[str, Any]:
    """Create a Stripe checkout session for subscription."""
    if not STRIPE_AVAILABLE or not STRIPE_SECRET_KEY:
        raise ValueError("Stripe is not configured. Please set STRIPE_SECRET_KEY.")

    # Get or create Stripe customer
    customer_id = user.stripe_customer_id
    if not customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            metadata={"user_id": str(user.id), "username": user.username}
        )
        customer_id = customer.id
        user.stripe_customer_id = customer_id
        db.commit()

    # Create checkout session
    checkout_session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=f"{FRONTEND_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{FRONTEND_URL}/pricing?canceled=true",
        metadata={
            "user_id": str(user.id),
            "billing_period": billing_period
        },
        subscription_data={
            "metadata": {
                "user_id": str(user.id)
            }
        }
    )

    return {
        "checkout_url": checkout_session.url,
        "session_id": checkout_session.id
    }


async def create_portal_session(user: User) -> Dict[str, str]:
    """Create a Stripe billing portal session."""
    if not STRIPE_AVAILABLE or not STRIPE_SECRET_KEY:
        raise ValueError("Stripe is not configured.")

    if not user.stripe_customer_id:
        raise ValueError("No active subscription found.")

    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=f"{FRONTEND_URL}/settings"
    )

    return {"portal_url": session.url}


async def handle_webhook_event(
    db: Session,
    payload: bytes,
    sig_header: str
) -> Dict[str, str]:
    """Handle Stripe webhook events."""
    if not STRIPE_AVAILABLE or not STRIPE_WEBHOOK_SECRET:
        raise ValueError("Stripe webhook not configured.")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise ValueError("Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise ValueError("Invalid signature")

    event_type = event["type"]
    event_data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        await handle_checkout_completed(db, event_data)

    elif event_type == "customer.subscription.created":
        await handle_subscription_created(db, event_data)

    elif event_type == "customer.subscription.updated":
        await handle_subscription_updated(db, event_data)

    elif event_type == "customer.subscription.deleted":
        await handle_subscription_deleted(db, event_data)

    elif event_type == "invoice.payment_succeeded":
        await handle_payment_succeeded(db, event_data)

    elif event_type == "invoice.payment_failed":
        await handle_payment_failed(db, event_data)

    return {"status": "success", "event_type": event_type}


async def handle_checkout_completed(db: Session, session: Dict[str, Any]):
    """Handle successful checkout."""
    user_id = session.get("metadata", {}).get("user_id")
    subscription_id = session.get("subscription")

    if user_id and subscription_id:
        user = db.query(User).filter(User.id == int(user_id)).first()
        if user:
            # Get subscription details
            subscription = stripe.Subscription.retrieve(subscription_id)
            tier = determine_tier_from_subscription(subscription)

            user.subscription_id = subscription_id
            user.subscription_tier = tier
            user.subscription_status = "active"
            user.subscription_expires = datetime.fromtimestamp(
                subscription.current_period_end
            )
            db.commit()


async def handle_subscription_created(db: Session, subscription: Dict[str, Any]):
    """Handle new subscription creation."""
    user_id = subscription.get("metadata", {}).get("user_id")
    if user_id:
        user = db.query(User).filter(User.id == int(user_id)).first()
        if user:
            tier = determine_tier_from_subscription(subscription)
            user.subscription_id = subscription["id"]
            user.subscription_tier = tier
            user.subscription_status = subscription["status"]
            if subscription.get("current_period_end"):
                user.subscription_expires = datetime.fromtimestamp(
                    subscription["current_period_end"]
                )
            db.commit()


async def handle_subscription_updated(db: Session, subscription: Dict[str, Any]):
    """Handle subscription updates (plan changes, status changes)."""
    # Find user by subscription ID
    user = db.query(User).filter(
        User.subscription_id == subscription["id"]
    ).first()

    if user:
        tier = determine_tier_from_subscription(subscription)
        user.subscription_tier = tier
        user.subscription_status = subscription["status"]
        if subscription.get("current_period_end"):
            user.subscription_expires = datetime.fromtimestamp(
                subscription["current_period_end"]
            )
        db.commit()


async def handle_subscription_deleted(db: Session, subscription: Dict[str, Any]):
    """Handle subscription cancellation."""
    user = db.query(User).filter(
        User.subscription_id == subscription["id"]
    ).first()

    if user:
        user.subscription_tier = "free"
        user.subscription_status = "canceled"
        user.subscription_id = None
        db.commit()


async def handle_payment_succeeded(db: Session, invoice: Dict[str, Any]):
    """Handle successful payment."""
    customer_id = invoice.get("customer")
    user = db.query(User).filter(
        User.stripe_customer_id == customer_id
    ).first()

    if user:
        # Record payment history
        payment = PaymentHistory(
            user_id=user.id,
            stripe_payment_id=invoice.get("payment_intent"),
            stripe_invoice_id=invoice.get("id"),
            amount=invoice.get("amount_paid", 0),
            currency=invoice.get("currency", "usd"),
            status="succeeded",
            description=invoice.get("description") or "Subscription payment",
            tier=user.subscription_tier,
            billing_period="monthly"  # TODO: Detect from invoice
        )
        db.add(payment)
        db.commit()


async def handle_payment_failed(db: Session, invoice: Dict[str, Any]):
    """Handle failed payment."""
    customer_id = invoice.get("customer")
    user = db.query(User).filter(
        User.stripe_customer_id == customer_id
    ).first()

    if user:
        # Update subscription status
        user.subscription_status = "past_due"

        # Record failed payment
        payment = PaymentHistory(
            user_id=user.id,
            stripe_payment_id=invoice.get("payment_intent"),
            stripe_invoice_id=invoice.get("id"),
            amount=invoice.get("amount_due", 0),
            currency=invoice.get("currency", "usd"),
            status="failed",
            description="Payment failed",
            tier=user.subscription_tier
        )
        db.add(payment)
        db.commit()


def determine_tier_from_subscription(subscription: Dict[str, Any]) -> str:
    """Determine subscription tier from Stripe subscription object."""
    if isinstance(subscription, dict):
        items = subscription.get("items", {}).get("data", [])
    else:
        items = subscription.get("items", {}).get("data", [])

    if not items:
        return "free"

    price_id = items[0].get("price", {}).get("id", "")

    # Match price ID to tier
    for tier, config in SUBSCRIPTION_TIERS.items():
        if tier == "free":
            continue
        if price_id in [
            config.get("stripe_price_id_monthly"),
            config.get("stripe_price_id_yearly")
        ]:
            return tier

    # Default to premium if we can't determine
    return "premium"


def get_subscription_status(user: User) -> Dict[str, Any]:
    """Get user's subscription status and details."""
    tier = user.subscription_tier or "free"
    tier_config = SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS["free"])

    return {
        "tier": tier,
        "status": user.subscription_status or "inactive",
        "expires_at": user.subscription_expires.isoformat() if user.subscription_expires else None,
        "stripe_customer_id": user.stripe_customer_id,
        "features": tier_config.get("features", []),
        "limits": {
            "predictions": tier_config.get("prediction_limit"),
            "sports": tier_config.get("sports_limit"),
            "api_access": tier_config.get("api_access", False)
        }
    }


async def cancel_subscription(db: Session, user: User) -> Dict[str, str]:
    """Cancel user's subscription at end of billing period."""
    if not STRIPE_AVAILABLE or not user.subscription_id:
        raise ValueError("No active subscription to cancel.")

    subscription = stripe.Subscription.modify(
        user.subscription_id,
        cancel_at_period_end=True
    )

    return {
        "message": "Subscription will be canceled at end of billing period",
        "cancel_at": datetime.fromtimestamp(subscription.cancel_at).isoformat() if subscription.cancel_at else None
    }
