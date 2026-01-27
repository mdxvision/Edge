"""
Discord Bot Integration Service

Provides Discord webhook delivery, slash commands, and rich embedded messages.
"""

import os
import httpx
import secrets
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

from app.db import User, DiscordUser, DiscordLinkCode, DiscordWebhook
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Discord configuration
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
DISCORD_CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET")
DISCORD_PUBLIC_KEY = os.environ.get("DISCORD_PUBLIC_KEY")
DISCORD_API_BASE = "https://discord.com/api/v10"

# Link codes expire after 15 minutes
LINK_CODE_EXPIRY_MINUTES = 15

# Color constants for embeds
EMBED_COLORS = {
    "primary": 0x5865F2,    # Discord blurple
    "success": 0x57F287,    # Green
    "warning": 0xFEE75C,    # Yellow
    "danger": 0xED4245,     # Red
    "info": 0x5865F2,       # Blue
    "edge": 0x00D166,       # Edge green
}


def is_discord_configured() -> bool:
    """Check if Discord is properly configured."""
    return bool(DISCORD_BOT_TOKEN or DISCORD_CLIENT_ID)


def is_webhook_configured() -> bool:
    """Check if Discord webhooks can be used (no bot token needed)."""
    return True  # Webhooks don't require bot configuration


def verify_discord_signature(signature: str, timestamp: str, body: bytes) -> bool:
    """Verify Discord interaction signature."""
    if not DISCORD_PUBLIC_KEY:
        return False

    try:
        verify_key = VerifyKey(bytes.fromhex(DISCORD_PUBLIC_KEY))
        verify_key.verify(f"{timestamp}{body.decode()}".encode(), bytes.fromhex(signature))
        return True
    except (BadSignatureError, Exception):
        return False


# =============================================================================
# Link Code Management
# =============================================================================

def generate_link_code() -> str:
    """Generate a random link code."""
    return secrets.token_hex(16)


def create_link_code(db: Session, user_id: int) -> str:
    """Create a new link code persisted to the database."""
    # Clean up any existing unused codes for this user
    db.query(DiscordLinkCode).filter(
        DiscordLinkCode.user_id == user_id,
        DiscordLinkCode.is_used == False
    ).delete()

    # Create new code
    code = generate_link_code()
    expires_at = datetime.utcnow() + timedelta(minutes=LINK_CODE_EXPIRY_MINUTES)

    link_code = DiscordLinkCode(
        user_id=user_id,
        code=code,
        expires_at=expires_at
    )
    db.add(link_code)
    db.commit()

    return code


def verify_link_code(db: Session, code: str) -> Optional[int]:
    """Verify a link code and return the user_id if valid."""
    link_code = db.query(DiscordLinkCode).filter(
        DiscordLinkCode.code == code,
        DiscordLinkCode.is_used == False,
        DiscordLinkCode.expires_at > datetime.utcnow()
    ).first()

    if link_code:
        return link_code.user_id
    return None


def complete_link(
    db: Session,
    code: str,
    discord_user_id: str,
    discord_username: Optional[str] = None,
    discord_discriminator: Optional[str] = None,
    discord_avatar: Optional[str] = None,
    guild_id: Optional[str] = None,
    guild_name: Optional[str] = None
) -> bool:
    """Complete the Discord link process."""
    # Find and validate the link code
    link_code = db.query(DiscordLinkCode).filter(
        DiscordLinkCode.code == code,
        DiscordLinkCode.is_used == False,
        DiscordLinkCode.expires_at > datetime.utcnow()
    ).first()

    if not link_code:
        return False

    user_id = link_code.user_id

    # Mark code as used
    link_code.is_used = True

    # Check if this Discord user is already linked
    existing = db.query(DiscordUser).filter(
        DiscordUser.discord_user_id == discord_user_id
    ).first()

    if existing:
        if existing.user_id != user_id:
            return False
        # Update existing link
        existing.discord_username = discord_username
        existing.discord_discriminator = discord_discriminator
        existing.discord_avatar = discord_avatar
        existing.guild_id = guild_id
        existing.guild_name = guild_name
        db.commit()
        return True

    # Create new Discord user link
    discord_user = DiscordUser(
        user_id=user_id,
        discord_user_id=discord_user_id,
        discord_username=discord_username,
        discord_discriminator=discord_discriminator,
        discord_avatar=discord_avatar,
        guild_id=guild_id,
        guild_name=guild_name
    )
    db.add(discord_user)
    db.commit()

    return True


def cleanup_expired_link_codes(db: Session) -> int:
    """Clean up expired link codes. Returns count of deleted codes."""
    result = db.query(DiscordLinkCode).filter(
        DiscordLinkCode.expires_at < datetime.utcnow()
    ).delete()
    db.commit()
    return result


def get_discord_user(db: Session, user_id: int) -> Optional[DiscordUser]:
    """Get Discord user by EdgeBet user ID."""
    return db.query(DiscordUser).filter(
        DiscordUser.user_id == user_id
    ).first()


def get_discord_user_by_discord_id(db: Session, discord_user_id: str) -> Optional[DiscordUser]:
    """Get Discord user by Discord user ID."""
    return db.query(DiscordUser).filter(
        DiscordUser.discord_user_id == discord_user_id
    ).first()


def unlink_discord(db: Session, user_id: int) -> bool:
    """Unlink Discord account from user."""
    result = db.query(DiscordUser).filter(
        DiscordUser.user_id == user_id
    ).delete()
    db.commit()
    return result > 0


# =============================================================================
# Webhook Management
# =============================================================================

def create_webhook(
    db: Session,
    user_id: int,
    name: str,
    webhook_url: str,
    notify_recommendations: bool = True,
    notify_results: bool = True,
    notify_alerts: bool = True,
    min_edge: float = 3.0,
    sports: Optional[List[str]] = None
) -> DiscordWebhook:
    """Create a new Discord webhook configuration."""
    webhook = DiscordWebhook(
        user_id=user_id,
        name=name,
        webhook_url=webhook_url,
        notify_recommendations=notify_recommendations,
        notify_results=notify_results,
        notify_alerts=notify_alerts,
        min_edge=min_edge,
        sports=json.dumps(sports) if sports else None
    )
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    return webhook


def get_user_webhooks(db: Session, user_id: int) -> List[DiscordWebhook]:
    """Get all webhooks for a user."""
    return db.query(DiscordWebhook).filter(
        DiscordWebhook.user_id == user_id
    ).all()


def get_webhook(db: Session, webhook_id: int, user_id: int) -> Optional[DiscordWebhook]:
    """Get a specific webhook."""
    return db.query(DiscordWebhook).filter(
        DiscordWebhook.id == webhook_id,
        DiscordWebhook.user_id == user_id
    ).first()


def delete_webhook(db: Session, webhook_id: int, user_id: int) -> bool:
    """Delete a webhook."""
    result = db.query(DiscordWebhook).filter(
        DiscordWebhook.id == webhook_id,
        DiscordWebhook.user_id == user_id
    ).delete()
    db.commit()
    return result > 0


# =============================================================================
# Embed Builders
# =============================================================================

def build_recommendation_embed(recommendation: Dict[str, Any]) -> Dict[str, Any]:
    """Build a Discord embed for a betting recommendation."""
    edge = recommendation.get('edge', 0)
    edge_pct = edge * 100 if edge < 1 else edge

    # Color based on edge strength
    if edge_pct >= 7:
        color = EMBED_COLORS["success"]
        edge_label = "STRONG EDGE"
    elif edge_pct >= 5:
        color = EMBED_COLORS["edge"]
        edge_label = "GOOD EDGE"
    else:
        color = EMBED_COLORS["info"]
        edge_label = "EDGE"

    odds = recommendation.get('odds', 0)
    odds_str = f"+{odds}" if odds > 0 else str(odds)

    embed = {
        "title": f"{recommendation.get('sport', 'N/A')} - {edge_label}",
        "description": f"**{recommendation.get('selection', 'N/A')}**",
        "color": color,
        "fields": [
            {
                "name": "Edge",
                "value": f"{edge_pct:.1f}%",
                "inline": True
            },
            {
                "name": "Odds",
                "value": odds_str,
                "inline": True
            },
            {
                "name": "Suggested Stake",
                "value": f"${recommendation.get('stake', 0):.2f}",
                "inline": True
            }
        ],
        "footer": {
            "text": "EdgeBet | SIMULATION ONLY - Not financial advice"
        },
        "timestamp": datetime.utcnow().isoformat()
    }

    if recommendation.get('explanation'):
        embed["fields"].append({
            "name": "Analysis",
            "value": recommendation['explanation'][:1024],  # Discord limit
            "inline": False
        })

    return embed


def build_result_embed(bet: Dict[str, Any]) -> Dict[str, Any]:
    """Build a Discord embed for a bet result."""
    result = bet.get('result', 'unknown')
    profit = bet.get('profit_loss', 0)

    if result == "won":
        color = EMBED_COLORS["success"]
        emoji = "WIN"
    elif result == "lost":
        color = EMBED_COLORS["danger"]
        emoji = "LOSS"
    else:
        color = EMBED_COLORS["warning"]
        emoji = "PUSH"

    profit_str = f"+${profit:.2f}" if profit > 0 else f"-${abs(profit):.2f}" if profit < 0 else "$0.00"

    embed = {
        "title": f"Bet Settled - {emoji}",
        "color": color,
        "fields": [
            {
                "name": "Sport",
                "value": bet.get('sport', 'N/A'),
                "inline": True
            },
            {
                "name": "Selection",
                "value": bet.get('selection', 'N/A'),
                "inline": True
            },
            {
                "name": "P/L",
                "value": profit_str,
                "inline": True
            }
        ],
        "footer": {
            "text": "EdgeBet | Track your bets at edgebet.app"
        },
        "timestamp": datetime.utcnow().isoformat()
    }

    return embed


def build_alert_embed(alert_name: str, alert_details: str, alert_type: str = "info") -> Dict[str, Any]:
    """Build a Discord embed for an alert."""
    color = EMBED_COLORS.get(alert_type, EMBED_COLORS["info"])

    embed = {
        "title": f"Alert: {alert_name}",
        "description": alert_details[:2048],  # Discord limit
        "color": color,
        "footer": {
            "text": "EdgeBet Alerts"
        },
        "timestamp": datetime.utcnow().isoformat()
    }

    return embed


def build_daily_digest_embed(
    top_edges: List[Dict[str, Any]],
    yesterday_results: Optional[Dict[str, Any]] = None,
    bankroll: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Build Discord embeds for daily digest."""
    embeds = []

    # Header embed
    header = {
        "title": "Daily Edge Summary",
        "description": f"Here's your daily betting digest for {datetime.utcnow().strftime('%B %d, %Y')}",
        "color": EMBED_COLORS["primary"],
        "timestamp": datetime.utcnow().isoformat()
    }
    embeds.append(header)

    # Top edges embed
    if top_edges:
        edges_text = ""
        for i, edge in enumerate(top_edges[:5], 1):
            edge_pct = edge.get('edge', 0)
            odds = edge.get('odds', 0)
            odds_str = f"+{odds}" if odds > 0 else str(odds)
            edges_text += f"**{i}. {edge.get('away_team', 'TBD')} @ {edge.get('home_team', 'TBD')}**\n"
            edges_text += f"   {edge.get('sport', '')} | {edge.get('selection', '')} ({odds_str}) | Edge: {edge_pct:.1f}%\n\n"

        edges_embed = {
            "title": "Today's Top Edges",
            "description": edges_text[:2048],
            "color": EMBED_COLORS["edge"]
        }
        embeds.append(edges_embed)

    # Yesterday's results embed
    if yesterday_results and yesterday_results.get('total_bets', 0) > 0:
        profit = yesterday_results.get('profit', 0)
        profit_color = EMBED_COLORS["success"] if profit >= 0 else EMBED_COLORS["danger"]

        results_embed = {
            "title": "Yesterday's Results",
            "color": profit_color,
            "fields": [
                {
                    "name": "Bets",
                    "value": str(yesterday_results.get('total_bets', 0)),
                    "inline": True
                },
                {
                    "name": "Record",
                    "value": f"{yesterday_results.get('wins', 0)}-{yesterday_results.get('losses', 0)}",
                    "inline": True
                },
                {
                    "name": "Profit",
                    "value": f"${profit:+.2f}",
                    "inline": True
                }
            ]
        }
        embeds.append(results_embed)

    # Bankroll embed
    if bankroll and bankroll.get('current', 0) > 0:
        bankroll_embed = {
            "title": "Bankroll Status",
            "color": EMBED_COLORS["info"],
            "fields": [
                {
                    "name": "Current",
                    "value": f"${bankroll.get('current', 0):,.2f}",
                    "inline": True
                },
                {
                    "name": "Today",
                    "value": f"${bankroll.get('change_today', 0):+.2f}",
                    "inline": True
                },
                {
                    "name": "This Week",
                    "value": f"${bankroll.get('change_week', 0):+.2f}",
                    "inline": True
                }
            ]
        }
        embeds.append(bankroll_embed)

    return embeds


# =============================================================================
# Message Sending
# =============================================================================

async def send_webhook_message(
    webhook_url: str,
    content: Optional[str] = None,
    embeds: Optional[List[Dict[str, Any]]] = None,
    username: str = "EdgeBet",
    avatar_url: Optional[str] = None
) -> bool:
    """Send a message to a Discord webhook."""
    if not webhook_url:
        return False

    payload = {
        "username": username
    }

    if avatar_url:
        payload["avatar_url"] = avatar_url

    if content:
        payload["content"] = content

    if embeds:
        payload["embeds"] = embeds[:10]  # Discord limit

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )

        if response.status_code in (200, 204):
            return True
        else:
            logger.warning(f"Discord webhook failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Discord webhook error: {e}")
        return False


async def send_dm(discord_user_id: str, content: str = None, embeds: List[Dict] = None) -> bool:
    """Send a direct message to a Discord user (requires bot token)."""
    if not DISCORD_BOT_TOKEN:
        return False

    try:
        async with httpx.AsyncClient() as client:
            # First, create a DM channel
            dm_response = await client.post(
                f"{DISCORD_API_BASE}/users/@me/channels",
                json={"recipient_id": discord_user_id},
                headers={
                    "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
                    "Content-Type": "application/json"
                }
            )

            if dm_response.status_code != 200:
                return False

            channel_id = dm_response.json().get("id")

            # Send message to DM channel
            payload = {}
            if content:
                payload["content"] = content
            if embeds:
                payload["embeds"] = embeds

            msg_response = await client.post(
                f"{DISCORD_API_BASE}/channels/{channel_id}/messages",
                json=payload,
                headers={
                    "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
                    "Content-Type": "application/json"
                }
            )

            return msg_response.status_code == 200
    except Exception as e:
        logger.error(f"Discord DM error: {e}")
        return False


# =============================================================================
# Notification Functions
# =============================================================================

async def send_recommendation_notification(
    db: Session,
    user: User,
    recommendation: Dict[str, Any]
) -> bool:
    """Send recommendation notification to user's Discord."""
    discord_user = get_discord_user(db, user.id)
    if not discord_user or not discord_user.notify_recommendations:
        return False

    embed = build_recommendation_embed(recommendation)
    return await send_dm(discord_user.discord_user_id, embeds=[embed])


async def send_result_notification(
    db: Session,
    user: User,
    bet: Dict[str, Any]
) -> bool:
    """Send bet result notification to user's Discord."""
    discord_user = get_discord_user(db, user.id)
    if not discord_user or not discord_user.notify_results:
        return False

    embed = build_result_embed(bet)
    return await send_dm(discord_user.discord_user_id, embeds=[embed])


async def send_alert_notification(
    db: Session,
    user: User,
    alert_name: str,
    alert_details: str,
    alert_type: str = "info"
) -> bool:
    """Send alert notification to user's Discord."""
    discord_user = get_discord_user(db, user.id)
    if not discord_user or not discord_user.notify_alerts:
        return False

    embed = build_alert_embed(alert_name, alert_details, alert_type)
    return await send_dm(discord_user.discord_user_id, embeds=[embed])


async def send_webhook_recommendation(
    webhook: DiscordWebhook,
    recommendation: Dict[str, Any]
) -> bool:
    """Send recommendation to a Discord webhook."""
    if not webhook.notify_recommendations or not webhook.is_active:
        return False

    edge = recommendation.get('edge', 0)
    edge_pct = edge * 100 if edge < 1 else edge

    if edge_pct < webhook.min_edge:
        return False

    # Check sport filter
    if webhook.sports:
        allowed_sports = json.loads(webhook.sports)
        if recommendation.get('sport') not in allowed_sports:
            return False

    embed = build_recommendation_embed(recommendation)
    return await send_webhook_message(webhook.webhook_url, embeds=[embed])


async def broadcast_recommendation(db: Session, recommendation: Dict[str, Any]) -> int:
    """Broadcast recommendation to all applicable webhooks. Returns count sent."""
    webhooks = db.query(DiscordWebhook).filter(
        DiscordWebhook.is_active == True,
        DiscordWebhook.notify_recommendations == True
    ).all()

    sent_count = 0
    for webhook in webhooks:
        success = await send_webhook_recommendation(webhook, recommendation)
        if success:
            webhook.last_used = datetime.utcnow()
            webhook.failure_count = 0
            sent_count += 1
        else:
            webhook.failure_count += 1
            if webhook.failure_count >= 5:
                webhook.is_active = False
                logger.warning(f"Discord webhook {webhook.id} disabled after 5 failures")

    db.commit()
    return sent_count


# =============================================================================
# Slash Command Handling
# =============================================================================

def handle_interaction(db: Session, interaction: Dict[str, Any]) -> Dict[str, Any]:
    """Handle Discord slash command interaction."""
    interaction_type = interaction.get("type")

    # Type 1: Ping (for URL verification)
    if interaction_type == 1:
        return {"type": 1}  # Pong

    # Type 2: Application Command
    if interaction_type == 2:
        return handle_application_command(db, interaction)

    return {"type": 4, "data": {"content": "Unknown interaction type"}}


def handle_application_command(db: Session, interaction: Dict[str, Any]) -> Dict[str, Any]:
    """Handle slash commands."""
    data = interaction.get("data", {})
    command_name = data.get("name", "")
    discord_user_id = interaction.get("member", {}).get("user", {}).get("id") or \
                      interaction.get("user", {}).get("id")

    if command_name == "link":
        return handle_link_command(db, interaction, discord_user_id)

    elif command_name == "status":
        return handle_status_command(db, discord_user_id)

    elif command_name == "edges":
        return handle_edges_command(db)

    elif command_name == "help":
        return handle_help_command()

    return {
        "type": 4,
        "data": {
            "content": f"Unknown command: {command_name}",
            "flags": 64  # Ephemeral
        }
    }


def handle_link_command(db: Session, interaction: Dict[str, Any], discord_user_id: str) -> Dict[str, Any]:
    """Handle /link command."""
    options = interaction.get("data", {}).get("options", [])
    code = None
    for opt in options:
        if opt.get("name") == "code":
            code = opt.get("value")
            break

    if not code:
        return {
            "type": 4,
            "data": {
                "content": "Please provide your link code: `/link code:YOUR_CODE`\n\nGet a code from your EdgeBet profile.",
                "flags": 64
            }
        }

    # Get Discord user info
    user_data = interaction.get("member", {}).get("user", {}) or interaction.get("user", {})
    username = user_data.get("username")
    discriminator = user_data.get("discriminator")
    avatar = user_data.get("avatar")
    guild_id = interaction.get("guild_id")

    success = complete_link(
        db, code, discord_user_id,
        discord_username=username,
        discord_discriminator=discriminator,
        discord_avatar=avatar,
        guild_id=guild_id
    )

    if success:
        return {
            "type": 4,
            "data": {
                "embeds": [{
                    "title": "Account Linked!",
                    "description": "Your Discord account is now connected to EdgeBet. You'll receive notifications here.",
                    "color": EMBED_COLORS["success"],
                    "footer": {"text": "Manage settings at edgebet.app"}
                }],
                "flags": 64
            }
        }
    else:
        return {
            "type": 4,
            "data": {
                "content": "Invalid or expired link code. Please get a new code from your EdgeBet profile.",
                "flags": 64
            }
        }


def handle_status_command(db: Session, discord_user_id: str) -> Dict[str, Any]:
    """Handle /status command."""
    discord_user = get_discord_user_by_discord_id(db, discord_user_id)

    if discord_user:
        user = db.query(User).filter(User.id == discord_user.user_id).first()
        if user:
            return {
                "type": 4,
                "data": {
                    "embeds": [{
                        "title": "Account Status",
                        "color": EMBED_COLORS["success"],
                        "fields": [
                            {"name": "Linked To", "value": user.username, "inline": True},
                            {"name": "Recommendations", "value": "" if discord_user.notify_recommendations else "", "inline": True},
                            {"name": "Results", "value": "" if discord_user.notify_results else "", "inline": True},
                            {"name": "Alerts", "value": "" if discord_user.notify_alerts else "", "inline": True}
                        ],
                        "footer": {"text": "Manage at edgebet.app/settings"}
                    }],
                    "flags": 64
                }
            }

    return {
        "type": 4,
        "data": {
            "content": "Your Discord account is not linked to EdgeBet. Use `/link` to connect.",
            "flags": 64
        }
    }


def handle_edges_command(db: Session) -> Dict[str, Any]:
    """Handle /edges command - show today's top edges."""
    from app.services.email_digest import get_top_edges_today

    edges = get_top_edges_today(db, limit=5)

    if not edges:
        return {
            "type": 4,
            "data": {
                "content": "No edges found for today's games yet. Check back later!",
                "flags": 0
            }
        }

    edges_text = ""
    for i, edge in enumerate(edges[:5], 1):
        edge_pct = edge.get('edge', 0)
        odds = edge.get('odds', 0)
        odds_str = f"+{odds}" if odds > 0 else str(odds)
        edges_text += f"**{i}. {edge.get('away_team', 'TBD')} @ {edge.get('home_team', 'TBD')}**\n"
        edges_text += f"   {edge.get('sport', '')} | {edge.get('selection', '')} ({odds_str}) | Edge: {edge_pct:.1f}%\n\n"

    return {
        "type": 4,
        "data": {
            "embeds": [{
                "title": "Today's Top Edges",
                "description": edges_text,
                "color": EMBED_COLORS["edge"],
                "footer": {"text": "EdgeBet | SIMULATION ONLY"},
                "timestamp": datetime.utcnow().isoformat()
            }]
        }
    }


def handle_help_command() -> Dict[str, Any]:
    """Handle /help command."""
    return {
        "type": 4,
        "data": {
            "embeds": [{
                "title": "EdgeBet Bot Commands",
                "description": "Available slash commands:",
                "color": EMBED_COLORS["primary"],
                "fields": [
                    {"name": "/link", "value": "Link your Discord to EdgeBet", "inline": False},
                    {"name": "/status", "value": "Check your linked account", "inline": False},
                    {"name": "/edges", "value": "View today's top betting edges", "inline": False},
                    {"name": "/help", "value": "Show this help message", "inline": False}
                ],
                "footer": {"text": "Visit edgebet.app for more features"}
            }],
            "flags": 64
        }
    }


# =============================================================================
# Bot Registration (for setting up slash commands)
# =============================================================================

async def register_slash_commands(guild_id: Optional[str] = None) -> bool:
    """Register slash commands with Discord."""
    if not DISCORD_BOT_TOKEN or not DISCORD_CLIENT_ID:
        return False

    commands = [
        {
            "name": "link",
            "description": "Link your Discord account to EdgeBet",
            "options": [
                {
                    "name": "code",
                    "description": "Your link code from EdgeBet",
                    "type": 3,  # STRING
                    "required": True
                }
            ]
        },
        {
            "name": "status",
            "description": "Check your EdgeBet account status"
        },
        {
            "name": "edges",
            "description": "View today's top betting edges"
        },
        {
            "name": "help",
            "description": "Get help with EdgeBet bot commands"
        }
    ]

    try:
        async with httpx.AsyncClient() as client:
            if guild_id:
                # Guild-specific commands (instant)
                url = f"{DISCORD_API_BASE}/applications/{DISCORD_CLIENT_ID}/guilds/{guild_id}/commands"
            else:
                # Global commands (can take up to 1 hour to propagate)
                url = f"{DISCORD_API_BASE}/applications/{DISCORD_CLIENT_ID}/commands"

            response = await client.put(
                url,
                json=commands,
                headers={
                    "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
                    "Content-Type": "application/json"
                }
            )

            if response.status_code == 200:
                logger.info(f"Discord slash commands registered successfully")
                return True
            else:
                logger.error(f"Failed to register Discord commands: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        logger.error(f"Error registering Discord commands: {e}")
        return False
