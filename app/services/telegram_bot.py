import os
import httpx
import secrets
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session

from app.db import User, TelegramUser


TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_BASE = "https://api.telegram.org/bot"


def is_telegram_configured() -> bool:
    return bool(TELEGRAM_BOT_TOKEN)


def get_bot_url() -> str:
    return f"{TELEGRAM_API_BASE}{TELEGRAM_BOT_TOKEN}"


async def send_message(chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
    if not TELEGRAM_BOT_TOKEN:
        return False
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{get_bot_url()}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode
                }
            )
        
        return response.status_code == 200
    except Exception:
        return False


def generate_link_code() -> str:
    return secrets.token_hex(16)


_pending_links: Dict[str, int] = {}


def create_link_code(user_id: int) -> str:
    code = generate_link_code()
    _pending_links[code] = user_id
    return code


def verify_link_code(code: str) -> Optional[int]:
    return _pending_links.get(code)


def complete_link(db: Session, code: str, telegram_chat_id: str, telegram_username: Optional[str] = None) -> bool:
    user_id = _pending_links.pop(code, None)
    if not user_id:
        return False
    
    existing = db.query(TelegramUser).filter(
        TelegramUser.telegram_chat_id == telegram_chat_id
    ).first()
    
    if existing:
        if existing.user_id != user_id:
            return False
        return True
    
    telegram_user = TelegramUser(
        user_id=user_id,
        telegram_chat_id=telegram_chat_id,
        telegram_username=telegram_username
    )
    db.add(telegram_user)
    db.commit()
    
    return True


def get_telegram_user(db: Session, user_id: int) -> Optional[TelegramUser]:
    return db.query(TelegramUser).filter(
        TelegramUser.user_id == user_id
    ).first()


def unlink_telegram(db: Session, user_id: int) -> bool:
    result = db.query(TelegramUser).filter(
        TelegramUser.user_id == user_id
    ).delete()
    db.commit()
    return result > 0


async def send_recommendation_notification(
    db: Session,
    user: User,
    recommendation: Dict[str, Any]
) -> bool:
    telegram_user = get_telegram_user(db, user.id)
    if not telegram_user or not telegram_user.notify_recommendations:
        return False
    
    message = f"""
<b>New Recommendation</b>

<b>Sport:</b> {recommendation.get('sport', 'N/A')}
<b>Selection:</b> {recommendation.get('selection', 'N/A')}
<b>Edge:</b> {recommendation.get('edge', 0) * 100:.2f}%
<b>Odds:</b> {recommendation.get('odds', 'N/A')}
<b>Suggested Stake:</b> ${recommendation.get('stake', 0):.2f}

<i>{recommendation.get('explanation', '')}</i>
"""
    
    return await send_message(telegram_user.telegram_chat_id, message)


async def send_result_notification(
    db: Session,
    user: User,
    bet: Dict[str, Any]
) -> bool:
    telegram_user = get_telegram_user(db, user.id)
    if not telegram_user or not telegram_user.notify_results:
        return False
    
    result = bet.get('result', 'unknown')
    emoji = "✅" if result == "won" else "❌" if result == "lost" else "➖"
    profit = bet.get('profit_loss', 0)
    profit_str = f"+${profit:.2f}" if profit > 0 else f"-${abs(profit):.2f}" if profit < 0 else "$0.00"
    
    message = f"""
{emoji} <b>Bet Settled</b>

<b>Sport:</b> {bet.get('sport', 'N/A')}
<b>Selection:</b> {bet.get('selection', 'N/A')}
<b>Result:</b> {result.upper()}
<b>Profit/Loss:</b> {profit_str}
"""
    
    return await send_message(telegram_user.telegram_chat_id, message)


async def send_alert_notification(
    db: Session,
    user: User,
    alert_name: str,
    alert_details: str
) -> bool:
    telegram_user = get_telegram_user(db, user.id)
    if not telegram_user or not telegram_user.notify_alerts:
        return False
    
    message = f"""
🔔 <b>Alert: {alert_name}</b>

{alert_details}
"""
    
    return await send_message(telegram_user.telegram_chat_id, message)


async def process_webhook_update(db: Session, update: Dict[str, Any]) -> Dict[str, Any]:
    if "message" not in update:
        return {"status": "no_message"}
    
    message = update["message"]
    chat = message.get("chat", {})
    chat_id = str(chat.get("id", ""))
    text = message.get("text", "")
    username = message.get("from", {}).get("username")
    
    if not text:
        return {"status": "no_text"}
    
    if text.startswith("/start"):
        parts = text.split(" ")
        if len(parts) > 1:
            code = parts[1]
            if complete_link(db, code, chat_id, username):
                await send_message(chat_id, "✅ <b>Account linked successfully!</b>\n\nYou'll now receive notifications here.")
                return {"status": "linked"}
            else:
                await send_message(chat_id, "❌ Invalid or expired link code. Please try again from the EdgeBet app.")
                return {"status": "invalid_code"}
        else:
            await send_message(chat_id, """
<b>Welcome to EdgeBet Bot!</b>

To link your account, go to your EdgeBet profile and click "Link Telegram".

<b>Commands:</b>
/status - Check your account status
/help - Show this message
""")
            return {"status": "start"}
    
    elif text == "/status":
        telegram_user = db.query(TelegramUser).filter(
            TelegramUser.telegram_chat_id == chat_id
        ).first()
        
        if telegram_user:
            user = db.query(User).filter(User.id == telegram_user.user_id).first()
            if user:
                await send_message(chat_id, f"✅ Linked to: <b>{user.username}</b>\n\nNotifications are enabled.")
            else:
                await send_message(chat_id, "⚠️ Account not found.")
        else:
            await send_message(chat_id, "❌ Not linked to any account. Use /start to link.")
        return {"status": "status_checked"}
    
    elif text == "/help":
        await send_message(chat_id, """
<b>EdgeBet Bot Help</b>

/start - Start the bot or link your account
/status - Check your linked account
/help - Show this message

Visit edgebet.app to manage your settings.
""")
        return {"status": "help"}
    
    return {"status": "unknown_command"}
