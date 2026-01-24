"""
Edge Alert Trigger System

Monitors for high-edge opportunities and arbitrage, sending push notifications
to eligible users based on their preferences.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.db import SessionLocal, User, NotificationPreferences
from app.services.edge_engine import find_value_bets_for_sport
from app.services.arbitrage import scan_for_arbitrage
from app.services.push_notifications import (
    notify_edge_alert,
    notify_arb_alert,
    broadcast_edge_alert,
    broadcast_arb_alert,
)
from app.utils.logging import get_logger
from app.config import SUPPORTED_SPORTS

logger = get_logger(__name__)


# Track recently sent alerts to avoid duplicates
_recent_alerts: Dict[str, datetime] = {}
ALERT_COOLDOWN_MINUTES = 30  # Don't send same alert within 30 minutes


def _get_alert_key(alert_type: str, game_id: int, market: str) -> str:
    """Generate a unique key for an alert to track duplicates."""
    return f"{alert_type}:{game_id}:{market}"


def _is_alert_recent(key: str) -> bool:
    """Check if an alert was recently sent."""
    if key not in _recent_alerts:
        return False

    last_sent = _recent_alerts[key]
    return datetime.utcnow() - last_sent < timedelta(minutes=ALERT_COOLDOWN_MINUTES)


def _mark_alert_sent(key: str):
    """Mark an alert as sent."""
    _recent_alerts[key] = datetime.utcnow()

    # Clean up old entries
    cutoff = datetime.utcnow() - timedelta(hours=2)
    keys_to_remove = [k for k, v in _recent_alerts.items() if v < cutoff]
    for k in keys_to_remove:
        del _recent_alerts[k]


async def check_and_send_edge_alerts(
    db: Session,
    sports: Optional[List[str]] = None,
    min_edge: float = 5.0,
    broadcast: bool = True
) -> Dict[str, Any]:
    """
    Check for high-edge opportunities and send notifications.

    Args:
        db: Database session
        sports: List of sports to check (defaults to all)
        min_edge: Minimum edge % to trigger alert
        broadcast: If True, send to all eligible users. If False, just return opportunities.

    Returns:
        Summary of alerts sent
    """
    if sports is None:
        sports = SUPPORTED_SPORTS

    logger.info(f"Checking edge alerts for {len(sports)} sports (min_edge={min_edge}%)")

    results = {
        "opportunities_found": 0,
        "alerts_sent": 0,
        "by_sport": {}
    }

    for sport in sports:
        try:
            # Find value bets for this sport
            value_bets = find_value_bets_for_sport(
                sport=sport,
                min_edge=min_edge / 100,  # Convert to decimal
                db=db
            )

            sport_alerts = 0

            for bet in value_bets:
                edge_pct = bet.edge * 100

                # Check if this alert was recently sent
                alert_key = _get_alert_key("edge", bet.game_id, bet.selection)
                if _is_alert_recent(alert_key):
                    continue

                results["opportunities_found"] += 1

                # Build matchup string
                if bet.home_team_name and bet.away_team_name:
                    matchup = f"{bet.away_team_name} @ {bet.home_team_name}"
                else:
                    matchup = f"Game {bet.game_id}"

                # Build pick string
                pick = bet.selection
                if bet.line_value:
                    pick = f"{bet.selection} {bet.line_value:+.1f}"

                if broadcast:
                    result = await broadcast_edge_alert(
                        db=db,
                        sport=sport,
                        matchup=matchup,
                        edge=edge_pct,
                        pick=pick,
                        odds=bet.american_odds
                    )
                    sport_alerts += result.get("sent", 0)
                    _mark_alert_sent(alert_key)

            results["by_sport"][sport] = {
                "opportunities": len(value_bets),
                "alerts_sent": sport_alerts
            }
            results["alerts_sent"] += sport_alerts

        except Exception as e:
            logger.error(f"Error checking edge alerts for {sport}: {e}")
            results["by_sport"][sport] = {"error": str(e)}

    logger.info(f"Edge alert check complete: {results['opportunities_found']} opportunities, {results['alerts_sent']} alerts sent")
    return results


async def check_and_send_arb_alerts(
    db: Session,
    sports: Optional[List[str]] = None,
    min_profit: float = 1.0,
    broadcast: bool = True
) -> Dict[str, Any]:
    """
    Check for arbitrage opportunities and send notifications.

    Args:
        db: Database session
        sports: List of sports to check (defaults to all)
        min_profit: Minimum profit % to trigger alert
        broadcast: If True, send to all eligible users.

    Returns:
        Summary of alerts sent
    """
    logger.info(f"Checking arb alerts (min_profit={min_profit}%)")

    results = {
        "opportunities_found": 0,
        "alerts_sent": 0,
        "arbs": []
    }

    try:
        # Scan for arbitrage opportunities
        opportunities = scan_for_arbitrage(
            db=db,
            sport=sports[0] if sports and len(sports) == 1 else None,
            min_profit=min_profit
        )

        for arb in opportunities:
            # Filter by sport if specified
            if sports and arb.sport not in sports:
                continue

            # Check if this alert was recently sent
            alert_key = _get_alert_key("arb", arb.game_id, arb.market_type)
            if _is_alert_recent(alert_key):
                continue

            results["opportunities_found"] += 1

            matchup = f"{arb.away_team} @ {arb.home_team}"

            results["arbs"].append({
                "sport": arb.sport,
                "matchup": matchup,
                "profit": arb.profit_margin,
                "books": [arb.bet1_sportsbook, arb.bet2_sportsbook]
            })

            if broadcast:
                result = await broadcast_arb_alert(
                    db=db,
                    sport=arb.sport,
                    matchup=matchup,
                    profit_percent=arb.profit_margin,
                    book1=arb.bet1_sportsbook,
                    book2=arb.bet2_sportsbook
                )
                results["alerts_sent"] += result.get("sent", 0)
                _mark_alert_sent(alert_key)

    except Exception as e:
        logger.error(f"Error checking arb alerts: {e}")
        results["error"] = str(e)

    logger.info(f"Arb alert check complete: {results['opportunities_found']} opportunities, {results['alerts_sent']} alerts sent")
    return results


async def run_alert_scan(
    sports: Optional[List[str]] = None,
    min_edge: float = 5.0,
    min_arb: float = 1.0
) -> Dict[str, Any]:
    """
    Run a full alert scan for edges and arbitrage.

    This is the main entry point for scheduled alert checks.
    """
    db = SessionLocal()
    try:
        edge_results = await check_and_send_edge_alerts(
            db=db,
            sports=sports,
            min_edge=min_edge,
            broadcast=True
        )

        arb_results = await check_and_send_arb_alerts(
            db=db,
            sports=sports,
            min_profit=min_arb,
            broadcast=True
        )

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "edge_alerts": edge_results,
            "arb_alerts": arb_results
        }

    finally:
        db.close()


# Scheduler integration

class EdgeAlertScheduler:
    """
    Scheduler for periodic edge alert checks.
    """

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._interval_minutes = 15
        self._last_run: Optional[datetime] = None
        self._run_count = 0

    async def _run_loop(self):
        """Main scheduler loop."""
        while self._running:
            try:
                logger.info("Running scheduled edge alert scan")
                results = await run_alert_scan()
                self._last_run = datetime.utcnow()
                self._run_count += 1
                logger.info(f"Alert scan complete: {results.get('edge_alerts', {}).get('alerts_sent', 0)} edge, {results.get('arb_alerts', {}).get('alerts_sent', 0)} arb alerts")
            except Exception as e:
                logger.error(f"Error in alert scheduler: {e}")

            await asyncio.sleep(self._interval_minutes * 60)

    def start(self, interval_minutes: int = 15):
        """Start the scheduler."""
        if self._running:
            return

        self._interval_minutes = interval_minutes
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Edge alert scheduler started (interval={interval_minutes}min)")

    def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("Edge alert scheduler stopped")

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            "running": self._running,
            "interval_minutes": self._interval_minutes,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "run_count": self._run_count
        }


# Global scheduler instance
edge_alert_scheduler = EdgeAlertScheduler()
