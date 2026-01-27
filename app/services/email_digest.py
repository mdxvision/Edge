"""
Email Digest Service

Daily email summaries with top edges, yesterday's results, and bankroll updates.
"""

import asyncio
import os
from datetime import datetime, timedelta, time
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_

from app.db import (
    SessionLocal, User, Client, TrackedBet, TrackedPick,
    Game, BetRecommendation, EmailDigestPreferences
)
from app.services.email import send_email, is_email_configured, APP_URL
from app.services.bet_tracking import get_user_stats
from app.services.currency import convert_currency
from app.utils.logging import get_logger

logger = get_logger(__name__)


def get_or_create_digest_preferences(db: Session, user_id: int) -> "EmailDigestPreferences":
    """Get or create digest preferences for a user."""
    prefs = db.query(EmailDigestPreferences).filter(
        EmailDigestPreferences.user_id == user_id
    ).first()

    if not prefs:
        prefs = EmailDigestPreferences(user_id=user_id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)

    return prefs


def update_digest_preferences(
    db: Session,
    user_id: int,
    enabled: Optional[bool] = None,
    send_hour: Optional[int] = None,
    send_minute: Optional[int] = None,
    timezone: Optional[str] = None,
    include_edges: Optional[bool] = None,
    include_results: Optional[bool] = None,
    include_bankroll: Optional[bool] = None,
    min_edge_for_digest: Optional[float] = None
) -> "EmailDigestPreferences":
    """Update digest preferences."""
    prefs = get_or_create_digest_preferences(db, user_id)

    if enabled is not None:
        prefs.digest_enabled = enabled
    if send_hour is not None:
        prefs.send_hour = send_hour
    if send_minute is not None:
        prefs.send_minute = send_minute
    if timezone is not None:
        prefs.timezone = timezone
    if include_edges is not None:
        prefs.include_edges = include_edges
    if include_results is not None:
        prefs.include_results = include_results
    if include_bankroll is not None:
        prefs.include_bankroll = include_bankroll
    if min_edge_for_digest is not None:
        prefs.min_edge_for_digest = min_edge_for_digest

    db.commit()
    db.refresh(prefs)
    return prefs


def get_top_edges_today(db: Session, limit: int = 5) -> List[Dict[str, Any]]:
    """Get top edges for today's games."""
    today = datetime.utcnow().date()
    tomorrow = today + timedelta(days=1)

    # Get games for today
    games = db.query(Game).filter(
        Game.start_time >= datetime.combine(today, time.min),
        Game.start_time < datetime.combine(tomorrow, time.min),
        Game.status == "scheduled"
    ).all()

    edges = []

    for game in games:
        # Get recommendations through Line -> Market -> Game relationship
        # BetRecommendation has line_id, Line has market_id, Market has game_id
        from app.db import Line, Market

        recs = db.query(BetRecommendation).join(
            Line, BetRecommendation.line_id == Line.id
        ).join(
            Market, Line.market_id == Market.id
        ).filter(
            Market.game_id == game.id,
            BetRecommendation.edge > 0
        ).order_by(desc(BetRecommendation.edge)).limit(3).all()

        for rec in recs:
            # Get bet type and selection from the line relationship
            bet_type = rec.line.market.market_type if rec.line and rec.line.market else "unknown"
            selection = rec.line.market.selection if rec.line and rec.line.market else "unknown"

            edges.append({
                "game_id": game.id,
                "home_team": game.home_team.name if game.home_team else "TBD",
                "away_team": game.away_team.name if game.away_team else "TBD",
                "sport": game.sport,
                "start_time": game.start_time.isoformat() if game.start_time else None,
                "bet_type": bet_type,
                "selection": selection,
                "edge": round(rec.edge, 2),
                "odds": rec.line.american_odds if rec.line else 0,
                "confidence": rec.model_probability
            })

    # Sort by edge and return top N
    edges.sort(key=lambda x: x["edge"], reverse=True)
    return edges[:limit]


def get_yesterday_results(db: Session, user_id: int, currency: str = "USD") -> Dict[str, Any]:
    """Get yesterday's betting results for a user."""
    yesterday = datetime.utcnow().date() - timedelta(days=1)
    today = datetime.utcnow().date()

    # Get bets settled yesterday
    bets = db.query(TrackedBet).filter(
        TrackedBet.user_id == user_id,
        TrackedBet.status == "settled",
        TrackedBet.settled_at >= datetime.combine(yesterday, time.min),
        TrackedBet.settled_at < datetime.combine(today, time.min)
    ).all()

    if not bets:
        return {
            "total_bets": 0,
            "wins": 0,
            "losses": 0,
            "pushes": 0,
            "profit": 0.0,
            "bets": []
        }

    wins = sum(1 for b in bets if b.result == "won")
    losses = sum(1 for b in bets if b.result == "lost")
    pushes = sum(1 for b in bets if b.result in ["push", "void"])
    profit = sum(convert_currency(b.profit_loss or 0, b.currency, currency) for b in bets)

    bet_details = [
        {
            "sport": b.sport,
            "selection": b.selection,
            "odds": b.odds,
            "stake": convert_currency(b.stake, b.currency, currency),
            "result": b.result,
            "profit_loss": convert_currency(b.profit_loss or 0, b.currency, currency)
        }
        for b in bets
    ]

    return {
        "total_bets": len(bets),
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "win_rate": round(wins / len(bets) * 100, 1) if bets else 0,
        "profit": round(profit, 2),
        "bets": bet_details
    }


def get_bankroll_update(db: Session, user_id: int, currency: str = "USD") -> Dict[str, Any]:
    """Get bankroll update for a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.client_id:
        return {"current": 0, "change_today": 0, "change_week": 0}

    client = db.query(Client).filter(Client.id == user.client_id).first()
    if not client:
        return {"current": 0, "change_today": 0, "change_week": 0}

    current_bankroll = client.bankroll

    # Get today's P&L
    today = datetime.utcnow().date()
    today_bets = db.query(TrackedBet).filter(
        TrackedBet.user_id == user_id,
        TrackedBet.status == "settled",
        TrackedBet.settled_at >= datetime.combine(today, time.min)
    ).all()
    today_pnl = sum(convert_currency(b.profit_loss or 0, b.currency, currency) for b in today_bets)

    # Get this week's P&L
    week_start = today - timedelta(days=today.weekday())
    week_bets = db.query(TrackedBet).filter(
        TrackedBet.user_id == user_id,
        TrackedBet.status == "settled",
        TrackedBet.settled_at >= datetime.combine(week_start, time.min)
    ).all()
    week_pnl = sum(convert_currency(b.profit_loss or 0, b.currency, currency) for b in week_bets)

    # Get overall stats
    stats = get_user_stats(db, user_id, currency)

    return {
        "current": round(current_bankroll, 2),
        "change_today": round(today_pnl, 2),
        "change_week": round(week_pnl, 2),
        "total_profit": stats["total_profit"],
        "roi": stats["roi"],
        "currency": currency
    }


def generate_digest_content(
    db: Session,
    user: User,
    include_edges: bool = True,
    include_results: bool = True,
    include_bankroll: bool = True,
    min_edge: float = 3.0
) -> Dict[str, Any]:
    """Generate all content for the daily digest."""
    content = {
        "user": {
            "username": user.username,
            "email": user.email
        },
        "generated_at": datetime.utcnow().isoformat()
    }

    if include_edges:
        edges = get_top_edges_today(db, limit=5)
        # Filter by minimum edge
        content["top_edges"] = [e for e in edges if e["edge"] >= min_edge]

    if include_results:
        content["yesterday_results"] = get_yesterday_results(db, user.id)

    if include_bankroll:
        content["bankroll"] = get_bankroll_update(db, user.id)

    return content


def generate_digest_html(content: Dict[str, Any]) -> str:
    """Generate HTML email content from digest data."""
    username = content["user"]["username"]

    html_parts = [f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #f9fafb; padding: 20px;">
        <div style="background-color: white; border-radius: 12px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
            <h1 style="color: #1f2937; margin-bottom: 8px;">Daily Edge Summary</h1>
            <p style="color: #6b7280; margin-top: 0;">Good morning, {username}!</p>
    """]

    # Top Edges Section
    if "top_edges" in content and content["top_edges"]:
        html_parts.append("""
            <h2 style="color: #2563eb; border-bottom: 2px solid #e5e7eb; padding-bottom: 8px; margin-top: 24px;">
                Today's Top Edges
            </h2>
        """)

        for i, edge in enumerate(content["top_edges"], 1):
            edge_color = "#22c55e" if edge["edge"] >= 5 else "#f59e0b"
            html_parts.append(f"""
            <div style="background-color: #f3f4f6; border-radius: 8px; padding: 12px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight: bold; color: #1f2937;">
                        #{i} {edge["away_team"]} @ {edge["home_team"]}
                    </span>
                    <span style="background-color: {edge_color}; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;">
                        +{edge["edge"]}% Edge
                    </span>
                </div>
                <div style="color: #6b7280; font-size: 14px; margin-top: 4px;">
                    {edge["sport"]} | {edge["bet_type"]}: {edge["selection"]} ({edge["odds"]:+d})
                </div>
            </div>
            """)
    elif "top_edges" in content:
        html_parts.append("""
            <h2 style="color: #2563eb; border-bottom: 2px solid #e5e7eb; padding-bottom: 8px; margin-top: 24px;">
                Today's Top Edges
            </h2>
            <p style="color: #6b7280;">No significant edges found for today's games.</p>
        """)

    # Yesterday's Results Section
    if "yesterday_results" in content:
        results = content["yesterday_results"]
        if results["total_bets"] > 0:
            profit_color = "#22c55e" if results["profit"] >= 0 else "#ef4444"
            profit_sign = "+" if results["profit"] >= 0 else ""

            html_parts.append(f"""
            <h2 style="color: #2563eb; border-bottom: 2px solid #e5e7eb; padding-bottom: 8px; margin-top: 24px;">
                Yesterday's Results
            </h2>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; text-align: center; margin-bottom: 16px;">
                <div style="background-color: #f3f4f6; padding: 12px; border-radius: 8px;">
                    <div style="font-size: 24px; font-weight: bold; color: #1f2937;">{results["total_bets"]}</div>
                    <div style="font-size: 12px; color: #6b7280;">Bets</div>
                </div>
                <div style="background-color: #dcfce7; padding: 12px; border-radius: 8px;">
                    <div style="font-size: 24px; font-weight: bold; color: #22c55e;">{results["wins"]}</div>
                    <div style="font-size: 12px; color: #6b7280;">Wins</div>
                </div>
                <div style="background-color: #fee2e2; padding: 12px; border-radius: 8px;">
                    <div style="font-size: 24px; font-weight: bold; color: #ef4444;">{results["losses"]}</div>
                    <div style="font-size: 12px; color: #6b7280;">Losses</div>
                </div>
                <div style="background-color: #f3f4f6; padding: 12px; border-radius: 8px;">
                    <div style="font-size: 24px; font-weight: bold; color: {profit_color};">{profit_sign}${abs(results["profit"]):.2f}</div>
                    <div style="font-size: 12px; color: #6b7280;">Profit</div>
                </div>
            </div>
            """)
        else:
            html_parts.append("""
            <h2 style="color: #2563eb; border-bottom: 2px solid #e5e7eb; padding-bottom: 8px; margin-top: 24px;">
                Yesterday's Results
            </h2>
            <p style="color: #6b7280;">No bets were settled yesterday.</p>
            """)

    # Bankroll Section
    if "bankroll" in content:
        bankroll = content["bankroll"]
        today_color = "#22c55e" if bankroll["change_today"] >= 0 else "#ef4444"
        today_sign = "+" if bankroll["change_today"] >= 0 else ""
        week_color = "#22c55e" if bankroll["change_week"] >= 0 else "#ef4444"
        week_sign = "+" if bankroll["change_week"] >= 0 else ""

        html_parts.append(f"""
            <h2 style="color: #2563eb; border-bottom: 2px solid #e5e7eb; padding-bottom: 8px; margin-top: 24px;">
                Bankroll Update
            </h2>
            <div style="background-color: #1f2937; border-radius: 8px; padding: 16px; color: white;">
                <div style="font-size: 32px; font-weight: bold;">${bankroll["current"]:,.2f}</div>
                <div style="font-size: 14px; color: #9ca3af;">Current Bankroll</div>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-top: 12px;">
                    <div>
                        <span style="color: {today_color}; font-weight: bold;">{today_sign}${abs(bankroll["change_today"]):.2f}</span>
                        <span style="color: #9ca3af; font-size: 12px;"> today</span>
                    </div>
                    <div>
                        <span style="color: {week_color}; font-weight: bold;">{week_sign}${abs(bankroll["change_week"]):.2f}</span>
                        <span style="color: #9ca3af; font-size: 12px;"> this week</span>
                    </div>
                </div>
            </div>
        """)

    # Footer
    html_parts.append(f"""
            <div style="margin-top: 24px; text-align: center;">
                <a href="{APP_URL}/recommendations" style="display: inline-block; padding: 12px 24px; background-color: #2563eb; color: white; text-decoration: none; border-radius: 6px; font-weight: bold;">
                    View All Recommendations
                </a>
            </div>
        </div>

        <div style="text-align: center; margin-top: 16px; color: #9ca3af; font-size: 12px;">
            <p>
                EdgeBet - Sports Analytics Platform<br>
                <a href="{APP_URL}/settings/notifications" style="color: #6b7280;">Manage email preferences</a> |
                <a href="{APP_URL}/settings/notifications?unsubscribe=digest" style="color: #6b7280;">Unsubscribe from digest</a>
            </p>
            <p style="color: #d1d5db;">
                DISCLAIMER: For educational purposes only. Not financial advice.
            </p>
        </div>
    </body>
    </html>
    """)

    return "".join(html_parts)


async def send_digest_to_user(db: Session, user: User) -> bool:
    """Send daily digest email to a user."""
    prefs = get_or_create_digest_preferences(db, user.id)

    if not prefs.digest_enabled:
        return False

    content = generate_digest_content(
        db,
        user,
        include_edges=prefs.include_edges,
        include_results=prefs.include_results,
        include_bankroll=prefs.include_bankroll,
        min_edge=prefs.min_edge_for_digest
    )

    html = generate_digest_html(content)

    # Generate plain text version
    text = f"""
Daily Edge Summary for {user.username}

View today's top edges and your results at {APP_URL}/recommendations

This email was sent by EdgeBet. To unsubscribe, visit {APP_URL}/settings/notifications
    """

    success = await send_email(
        to_email=user.email,
        subject=f"EdgeBet Daily Summary - {datetime.utcnow().strftime('%B %d, %Y')}",
        html_content=html,
        text_content=text
    )

    if success:
        prefs.last_sent_at = datetime.utcnow()
        db.commit()
        logger.info(f"Digest sent to {user.email}")
    else:
        logger.warning(f"Failed to send digest to {user.email}")

    return success


class DigestScheduler:
    """Background job for sending daily digest emails."""

    def __init__(self):
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self.check_interval_seconds = 60  # Check every minute
        self.digests_sent_today = 0
        self._last_check_date: Optional[datetime.date] = None

    async def start(self):
        """Start the digest scheduler."""
        if self.is_running:
            return

        self.is_running = True
        self._task = asyncio.create_task(self._run_scheduler())
        logger.info("Digest scheduler started")

    async def stop(self):
        """Stop the digest scheduler."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Digest scheduler stopped")

    async def _run_scheduler(self):
        """Main scheduler loop."""
        while self.is_running:
            try:
                await self._check_and_send_digests()
            except Exception as e:
                logger.error(f"Error in digest scheduler: {e}")

            await asyncio.sleep(self.check_interval_seconds)

    async def _check_and_send_digests(self):
        """Check for users who need digests sent."""
        if not is_email_configured():
            return

        now = datetime.utcnow()
        current_hour = now.hour
        current_minute = now.minute

        # Reset counter at midnight
        if self._last_check_date != now.date():
            self.digests_sent_today = 0
            self._last_check_date = now.date()

        db = SessionLocal()
        try:
            # Find users whose digest time matches current time
            # and haven't received digest today
            today_start = datetime.combine(now.date(), time.min)

            prefs_to_send = db.query(EmailDigestPreferences).filter(
                EmailDigestPreferences.digest_enabled == True,
                EmailDigestPreferences.send_hour == current_hour,
                EmailDigestPreferences.send_minute == current_minute,
                (EmailDigestPreferences.last_sent_at == None) |
                (EmailDigestPreferences.last_sent_at < today_start)
            ).all()

            for pref in prefs_to_send:
                user = db.query(User).filter(User.id == pref.user_id).first()
                if user and user.is_active:
                    try:
                        success = await send_digest_to_user(db, user)
                        if success:
                            self.digests_sent_today += 1
                    except Exception as e:
                        logger.error(f"Error sending digest to user {user.id}: {e}")

        finally:
            db.close()


# Global scheduler instance
digest_scheduler = DigestScheduler()


async def send_test_digest(db: Session, user_id: int) -> Dict[str, Any]:
    """Send a test digest immediately."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"success": False, "error": "User not found"}

    if not is_email_configured():
        return {"success": False, "error": "Email service not configured"}

    # Generate content
    content = generate_digest_content(db, user)
    html = generate_digest_html(content)

    success = await send_email(
        to_email=user.email,
        subject=f"[TEST] EdgeBet Daily Summary - {datetime.utcnow().strftime('%B %d, %Y')}",
        html_content=html
    )

    return {
        "success": success,
        "email": user.email,
        "content_preview": {
            "edges_count": len(content.get("top_edges", [])),
            "yesterday_bets": content.get("yesterday_results", {}).get("total_bets", 0),
            "bankroll": content.get("bankroll", {}).get("current", 0)
        }
    }
