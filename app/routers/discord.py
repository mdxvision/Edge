"""
Discord Integration Router

API endpoints for Discord bot integration, webhooks, and slash commands.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
import json

from app.db import get_db, User
from app.routers.auth import require_auth
from app.services.discord_bot import (
    is_discord_configured,
    is_webhook_configured,
    verify_discord_signature,
    create_link_code,
    get_discord_user,
    unlink_discord,
    create_webhook,
    get_user_webhooks,
    get_webhook,
    delete_webhook,
    send_webhook_message,
    build_recommendation_embed,
    handle_interaction,
    register_slash_commands,
    DISCORD_CLIENT_ID,
)
from app.services.audit import log_action
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/discord", tags=["Discord"])


# =============================================================================
# Request/Response Models
# =============================================================================

class DiscordStatusResponse(BaseModel):
    configured: bool
    linked: bool
    username: Optional[str] = None
    discriminator: Optional[str] = None
    avatar_url: Optional[str] = None
    notify_recommendations: bool = False
    notify_results: bool = False
    notify_alerts: bool = False


class LinkCodeResponse(BaseModel):
    code: str
    bot_invite_url: str
    instructions: str


class UpdateNotificationsRequest(BaseModel):
    notify_recommendations: Optional[bool] = None
    notify_results: Optional[bool] = None
    notify_alerts: Optional[bool] = None


class WebhookCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    webhook_url: str = Field(..., min_length=1)
    notify_recommendations: bool = True
    notify_results: bool = True
    notify_alerts: bool = True
    min_edge: float = Field(3.0, ge=0, le=20)
    sports: Optional[List[str]] = None


class WebhookUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    notify_recommendations: Optional[bool] = None
    notify_results: Optional[bool] = None
    notify_alerts: Optional[bool] = None
    min_edge: Optional[float] = Field(None, ge=0, le=20)
    sports: Optional[List[str]] = None
    is_active: Optional[bool] = None


class WebhookResponse(BaseModel):
    id: int
    name: str
    webhook_url: str
    notify_recommendations: bool
    notify_results: bool
    notify_alerts: bool
    min_edge: float
    sports: Optional[List[str]]
    is_active: bool
    last_used: Optional[str]


class TestWebhookRequest(BaseModel):
    webhook_url: str


# =============================================================================
# User Account Linking
# =============================================================================

@router.get("/status", response_model=DiscordStatusResponse)
def get_discord_status(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Get Discord connection status.

    Returns whether Discord is configured and if the user has linked their account.
    """
    configured = is_discord_configured()
    discord_user = get_discord_user(db, user.id) if configured else None

    avatar_url = None
    if discord_user and discord_user.discord_avatar:
        avatar_url = f"https://cdn.discordapp.com/avatars/{discord_user.discord_user_id}/{discord_user.discord_avatar}.png"

    return DiscordStatusResponse(
        configured=configured,
        linked=discord_user is not None,
        username=discord_user.discord_username if discord_user else None,
        discriminator=discord_user.discord_discriminator if discord_user else None,
        avatar_url=avatar_url,
        notify_recommendations=discord_user.notify_recommendations if discord_user else False,
        notify_results=discord_user.notify_results if discord_user else False,
        notify_alerts=discord_user.notify_alerts if discord_user else False
    )


@router.post("/link", response_model=LinkCodeResponse)
def generate_link_code_endpoint(
    request: Request,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Generate a link code for Discord account linking.

    Use this code with the `/link` slash command in Discord to connect your account.
    """
    if not is_discord_configured():
        raise HTTPException(status_code=503, detail="Discord bot not configured")

    existing = get_discord_user(db, user.id)
    if existing:
        raise HTTPException(status_code=400, detail="Discord already linked")

    code = create_link_code(db, user.id)

    bot_invite_url = f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&permissions=2048&scope=bot%20applications.commands" if DISCORD_CLIENT_ID else ""

    return LinkCodeResponse(
        code=code,
        bot_invite_url=bot_invite_url,
        instructions="1. Add EdgeBet bot to your server\n2. Use `/link code:YOUR_CODE` in Discord\n3. Your accounts will be connected!"
    )


@router.delete("/unlink")
def unlink_discord_account(
    request: Request,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Unlink Discord account.

    Removes the connection between your EdgeBet and Discord accounts.
    """
    if not unlink_discord(db, user.id):
        raise HTTPException(status_code=404, detail="No Discord account linked")

    log_action(
        db, "discord_unlinked", user.id,
        ip_address=request.client.host if request.client else None
    )

    return {"message": "Discord account unlinked"}


@router.patch("/notifications", response_model=DiscordStatusResponse)
def update_discord_notifications(
    data: UpdateNotificationsRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Update Discord notification preferences.

    Control what notifications you receive via Discord DMs.
    """
    discord_user = get_discord_user(db, user.id)
    if not discord_user:
        raise HTTPException(status_code=404, detail="Discord not linked")

    if data.notify_recommendations is not None:
        discord_user.notify_recommendations = data.notify_recommendations
    if data.notify_results is not None:
        discord_user.notify_results = data.notify_results
    if data.notify_alerts is not None:
        discord_user.notify_alerts = data.notify_alerts

    db.commit()

    avatar_url = None
    if discord_user.discord_avatar:
        avatar_url = f"https://cdn.discordapp.com/avatars/{discord_user.discord_user_id}/{discord_user.discord_avatar}.png"

    return DiscordStatusResponse(
        configured=True,
        linked=True,
        username=discord_user.discord_username,
        discriminator=discord_user.discord_discriminator,
        avatar_url=avatar_url,
        notify_recommendations=discord_user.notify_recommendations,
        notify_results=discord_user.notify_results,
        notify_alerts=discord_user.notify_alerts
    )


# =============================================================================
# Webhook Management
# =============================================================================

@router.get("/webhooks")
def list_webhooks(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    List all Discord webhooks.

    Returns all configured Discord webhooks for sending notifications to channels.
    """
    webhooks = get_user_webhooks(db, user.id)

    return {
        "webhooks": [
            {
                "id": w.id,
                "name": w.name,
                "webhook_url": w.webhook_url[:50] + "..." if len(w.webhook_url) > 50 else w.webhook_url,
                "notify_recommendations": w.notify_recommendations,
                "notify_results": w.notify_results,
                "notify_alerts": w.notify_alerts,
                "min_edge": w.min_edge,
                "sports": json.loads(w.sports) if w.sports else None,
                "is_active": w.is_active,
                "last_used": w.last_used.isoformat() if w.last_used else None
            }
            for w in webhooks
        ],
        "total": len(webhooks)
    }


@router.post("/webhooks")
def create_discord_webhook(
    data: WebhookCreateRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Create a Discord webhook.

    Configure a webhook to receive notifications in a Discord channel.

    **Getting a Webhook URL:**
    1. Go to your Discord server settings
    2. Navigate to Integrations > Webhooks
    3. Create a new webhook or copy an existing URL
    """
    # Validate webhook URL format
    if not data.webhook_url.startswith("https://discord.com/api/webhooks/"):
        raise HTTPException(
            status_code=400,
            detail="Invalid Discord webhook URL. Must start with https://discord.com/api/webhooks/"
        )

    # Limit webhooks per user
    existing = get_user_webhooks(db, user.id)
    if len(existing) >= 10:
        raise HTTPException(status_code=400, detail="Maximum 10 webhooks allowed")

    webhook = create_webhook(
        db=db,
        user_id=user.id,
        name=data.name,
        webhook_url=data.webhook_url,
        notify_recommendations=data.notify_recommendations,
        notify_results=data.notify_results,
        notify_alerts=data.notify_alerts,
        min_edge=data.min_edge,
        sports=data.sports
    )

    return {
        "message": "Webhook created successfully",
        "webhook": {
            "id": webhook.id,
            "name": webhook.name,
            "is_active": webhook.is_active
        }
    }


@router.get("/webhooks/{webhook_id}")
def get_webhook_details(
    webhook_id: int,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get details of a specific webhook."""
    webhook = get_webhook(db, webhook_id, user.id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    return {
        "id": webhook.id,
        "name": webhook.name,
        "webhook_url": webhook.webhook_url,
        "notify_recommendations": webhook.notify_recommendations,
        "notify_results": webhook.notify_results,
        "notify_alerts": webhook.notify_alerts,
        "min_edge": webhook.min_edge,
        "sports": json.loads(webhook.sports) if webhook.sports else None,
        "is_active": webhook.is_active,
        "failure_count": webhook.failure_count,
        "last_used": webhook.last_used.isoformat() if webhook.last_used else None,
        "created_at": webhook.created_at.isoformat()
    }


@router.patch("/webhooks/{webhook_id}")
def update_webhook(
    webhook_id: int,
    data: WebhookUpdateRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Update a Discord webhook configuration."""
    webhook = get_webhook(db, webhook_id, user.id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    if data.name is not None:
        webhook.name = data.name
    if data.notify_recommendations is not None:
        webhook.notify_recommendations = data.notify_recommendations
    if data.notify_results is not None:
        webhook.notify_results = data.notify_results
    if data.notify_alerts is not None:
        webhook.notify_alerts = data.notify_alerts
    if data.min_edge is not None:
        webhook.min_edge = data.min_edge
    if data.sports is not None:
        webhook.sports = json.dumps(data.sports)
    if data.is_active is not None:
        webhook.is_active = data.is_active
        if data.is_active:
            webhook.failure_count = 0  # Reset on re-enable

    db.commit()

    return {"message": "Webhook updated", "id": webhook.id}


@router.delete("/webhooks/{webhook_id}")
def delete_discord_webhook(
    webhook_id: int,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Delete a Discord webhook."""
    if not delete_webhook(db, webhook_id, user.id):
        raise HTTPException(status_code=404, detail="Webhook not found")

    return {"message": "Webhook deleted"}


@router.post("/webhooks/{webhook_id}/test")
async def test_webhook(
    webhook_id: int,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Test a Discord webhook.

    Sends a test message to verify the webhook is working correctly.
    """
    webhook = get_webhook(db, webhook_id, user.id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    test_embed = {
        "title": "EdgeBet Test Message",
        "description": "Your webhook is configured correctly!",
        "color": 0x5865F2,
        "fields": [
            {"name": "Webhook", "value": webhook.name, "inline": True},
            {"name": "Status", "value": "Connected", "inline": True}
        ],
        "footer": {"text": "EdgeBet | You'll receive notifications here"}
    }

    success = await send_webhook_message(webhook.webhook_url, embeds=[test_embed])

    if success:
        return {"success": True, "message": "Test message sent successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send test message")


@router.post("/webhooks/test-url")
async def test_webhook_url(
    data: TestWebhookRequest,
    user: User = Depends(require_auth)
):
    """
    Test a webhook URL before saving.

    Validates that the webhook URL is working.
    """
    if not data.webhook_url.startswith("https://discord.com/api/webhooks/"):
        raise HTTPException(
            status_code=400,
            detail="Invalid Discord webhook URL"
        )

    test_embed = {
        "title": "EdgeBet Webhook Test",
        "description": "Testing webhook connection...",
        "color": 0x5865F2,
        "footer": {"text": "This is a test message"}
    }

    success = await send_webhook_message(data.webhook_url, embeds=[test_embed])

    if success:
        return {"valid": True, "message": "Webhook URL is valid"}
    else:
        raise HTTPException(status_code=400, detail="Webhook URL is invalid or not accessible")


# =============================================================================
# Discord Interactions (Slash Commands)
# =============================================================================

@router.post("/interactions")
async def discord_interactions(
    request: Request,
    db: Session = Depends(get_db),
    x_signature_ed25519: str = Header(None),
    x_signature_timestamp: str = Header(None)
):
    """
    Discord Interactions endpoint.

    Handles slash commands from Discord. This endpoint should be configured
    as the Interactions Endpoint URL in your Discord application settings.
    """
    body = await request.body()

    # Verify signature
    if x_signature_ed25519 and x_signature_timestamp:
        if not verify_discord_signature(x_signature_ed25519, x_signature_timestamp, body):
            raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        interaction = await request.json()
        response = handle_interaction(db, interaction)
        return response
    except Exception as e:
        logger.error(f"Discord interaction error: {e}")
        return {"type": 4, "data": {"content": "An error occurred", "flags": 64}}


# =============================================================================
# Admin Endpoints
# =============================================================================

@router.post("/register-commands")
async def register_commands(
    guild_id: Optional[str] = None,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Register slash commands with Discord.

    **Note:** This requires bot token configuration. Global commands may take
    up to 1 hour to propagate. Guild-specific commands are instant.
    """
    # Only allow admins (simplified check - could be more robust)
    if user.subscription_tier != "pro":
        raise HTTPException(status_code=403, detail="Admin access required")

    if not is_discord_configured():
        raise HTTPException(status_code=503, detail="Discord bot not configured")

    success = await register_slash_commands(guild_id)

    if success:
        return {"message": "Slash commands registered successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to register commands")


@router.get("/invite-url")
def get_invite_url():
    """
    Get the bot invite URL.

    Use this URL to add the EdgeBet bot to your Discord server.
    """
    if not DISCORD_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Discord bot not configured")

    # Permissions: Send Messages (2048), Use Slash Commands (implied with scope)
    invite_url = f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&permissions=2048&scope=bot%20applications.commands"

    return {
        "invite_url": invite_url,
        "permissions": ["Send Messages", "Use Slash Commands"],
        "instructions": "Click the link to add EdgeBet bot to your server"
    }
