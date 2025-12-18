"""
Background jobs service for EdgeBet.
Handles scheduled tasks like alert checking, bet settlement, notifications, and odds refresh.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db import (
    SessionLocal, User, UserAlert, TrackedBet, Game,
    OddsSnapshot, BankrollHistory, Client, TrackedPick
)
from app.services.odds_scheduler import odds_scheduler
from app.services.telegram_bot import (
    send_alert_notification, send_result_notification
)


logger = logging.getLogger(__name__)


class AlertScheduler:
    """Background job for checking and triggering alerts."""

    def __init__(self):
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self.check_interval_seconds = 60
        self.alerts_triggered = 0

    async def start(self):
        """Start the alert scheduler."""
        if self.is_running:
            return

        self.is_running = True
        self._task = asyncio.create_task(self._run_scheduler())
        logger.info("Alert scheduler started")

    async def stop(self):
        """Stop the alert scheduler."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Alert scheduler stopped")

    async def _run_scheduler(self):
        """Main scheduler loop."""
        while self.is_running:
            try:
                await self._check_alerts()
            except Exception as e:
                logger.error(f"Error in alert check: {e}")

            await asyncio.sleep(self.check_interval_seconds)

    async def _check_alerts(self):
        """Check all active alerts."""
        db = SessionLocal()
        try:
            alerts = db.query(UserAlert).filter(UserAlert.is_active == True).all()

            for alert in alerts:
                try:
                    triggered = await self._evaluate_alert(db, alert)
                    if triggered:
                        self.alerts_triggered += 1
                except Exception as e:
                    logger.error(f"Error evaluating alert {alert.id}: {e}")

            db.commit()
        finally:
            db.close()

    async def _evaluate_alert(self, db: Session, alert: UserAlert) -> bool:
        """Evaluate a single alert and trigger if conditions are met."""
        # Get user
        user = db.query(User).filter(User.id == alert.user_id).first()
        if not user:
            return False

        # Check alert conditions based on type
        if alert.alert_type == 'edge_threshold':
            return await self._check_edge_alert(db, alert, user)
        elif alert.alert_type == 'odds_movement':
            return await self._check_odds_movement_alert(db, alert, user)
        elif alert.alert_type == 'game_start':
            return await self._check_game_start_alert(db, alert, user)

        return False

    async def _check_edge_alert(self, db: Session, alert: UserAlert, user: User) -> bool:
        """Check for edge threshold alerts."""
        from app.services.edge_engine import calculate_edge

        # Get recent games for the sport
        if alert.sport:
            games = db.query(Game).filter(
                Game.sport == alert.sport,
                Game.start_time > datetime.utcnow()
            ).limit(10).all()

            for game in games:
                # Check if edge exceeds threshold
                # This is simplified - in production would check actual recommendations
                if alert.min_edge:
                    # Trigger notification
                    await send_alert_notification(
                        db, user,
                        alert.name,
                        f"High edge opportunity detected in {alert.sport}"
                    )
                    alert.last_triggered = datetime.utcnow()
                    alert.trigger_count += 1
                    return True

        return False

    async def _check_odds_movement_alert(self, db: Session, alert: UserAlert, user: User) -> bool:
        """Check for significant odds movements."""
        # Check recent line movements
        from app.db import LineMovement

        recent = db.query(LineMovement).filter(
            LineMovement.recorded_at > datetime.utcnow() - timedelta(hours=1),
            LineMovement.movement_percentage >= 5.0  # Significant movement
        ).first()

        if recent:
            await send_alert_notification(
                db, user,
                alert.name,
                f"Significant line movement detected: {recent.movement_percentage:.1f}%"
            )
            alert.last_triggered = datetime.utcnow()
            alert.trigger_count += 1
            return True

        return False

    async def _check_game_start_alert(self, db: Session, alert: UserAlert, user: User) -> bool:
        """Check for games about to start."""
        upcoming = db.query(Game).filter(
            Game.start_time.between(
                datetime.utcnow(),
                datetime.utcnow() + timedelta(minutes=30)
            )
        )

        if alert.sport:
            upcoming = upcoming.filter(Game.sport == alert.sport)

        game = upcoming.first()

        if game:
            await send_alert_notification(
                db, user,
                alert.name,
                f"Game starting soon: {game.sport}"
            )
            alert.last_triggered = datetime.utcnow()
            alert.trigger_count += 1
            return True

        return False


class AutoSettlementChecker:
    """Background job for auto-settling bets based on game results."""

    def __init__(self):
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self.check_interval_seconds = 300  # 5 minutes
        self.bets_settled = 0

    async def start(self):
        """Start the settlement checker."""
        if self.is_running:
            return

        self.is_running = True
        self._task = asyncio.create_task(self._run_scheduler())
        logger.info("Auto-settlement checker started")

    async def stop(self):
        """Stop the settlement checker."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Auto-settlement checker stopped")

    async def _run_scheduler(self):
        """Main scheduler loop."""
        while self.is_running:
            try:
                await self._check_settlements()
            except Exception as e:
                logger.error(f"Error in settlement check: {e}")

            await asyncio.sleep(self.check_interval_seconds)

    async def _check_settlements(self):
        """Check for bets that can be auto-settled."""
        db = SessionLocal()
        try:
            # Get pending bets with game dates in the past
            pending_bets = db.query(TrackedBet).filter(
                TrackedBet.status == 'pending',
                TrackedBet.game_date.isnot(None),
                TrackedBet.game_date < datetime.utcnow() - timedelta(hours=3)
            ).limit(50).all()

            for bet in pending_bets:
                try:
                    # Check if game result is available
                    if bet.game_id:
                        result = await self._get_game_result(db, bet.game_id)
                        if result:
                            await self._settle_bet(db, bet, result)
                            self.bets_settled += 1
                except Exception as e:
                    logger.error(f"Error settling bet {bet.id}: {e}")

            # Also settle EdgeTracker picks
            await self._check_tracker_settlements()

            db.commit()
        finally:
            db.close()

    async def _check_tracker_settlements(self):
        """Check for EdgeTracker picks that can be auto-settled."""
        try:
            from app.services.auto_settler import run_auto_settlement
            result = await run_auto_settlement()
            if result.get("settled", 0) > 0:
                logger.info(f"EdgeTracker auto-settlement: {result}")
                self.bets_settled += result.get("settled", 0)
        except Exception as e:
            logger.error(f"Error in EdgeTracker settlement: {e}")

    async def _get_game_result(self, db: Session, game_id: int) -> Optional[Dict[str, Any]]:
        """Get game result from historical data."""
        from app.db import HistoricalGameResult

        result = db.query(HistoricalGameResult).filter(
            HistoricalGameResult.game_id == game_id
        ).first()

        if result and result.winner:
            return {
                'winner': result.winner,
                'home_score': result.home_score,
                'away_score': result.away_score,
                'margin': result.margin,
                'total': result.total_points
            }

        return None

    async def _settle_bet(self, db: Session, bet: TrackedBet, game_result: Dict[str, Any]):
        """Settle a bet based on game result."""
        # Determine bet result based on bet type and selection
        # This is simplified - production would have more complex logic

        bet_won = False  # Default to loss

        if bet.bet_type == 'moneyline':
            # Check if selected team won
            bet_won = bet.selection.lower() in game_result['winner'].lower()
        elif bet.bet_type == 'spread':
            # Check spread coverage (simplified)
            pass
        elif bet.bet_type == 'total':
            # Check over/under (simplified)
            pass

        # Calculate profit/loss
        if bet_won:
            bet.result = 'won'
            if bet.odds > 0:
                bet.profit_loss = bet.stake * (bet.odds / 100)
            else:
                bet.profit_loss = bet.stake * (100 / abs(bet.odds))
        else:
            bet.result = 'lost'
            bet.profit_loss = -bet.stake

        bet.status = 'settled'
        bet.settled_at = datetime.utcnow()

        # Update bankroll
        await self._update_bankroll(db, bet)

        # Send notification
        user = db.query(User).filter(User.id == bet.user_id).first()
        if user:
            await send_result_notification(db, user, {
                'sport': bet.sport,
                'selection': bet.selection,
                'result': bet.result,
                'profit_loss': bet.profit_loss
            })

    async def _update_bankroll(self, db: Session, bet: TrackedBet):
        """Update user's bankroll after bet settlement."""
        user = db.query(User).filter(User.id == bet.user_id).first()
        if not user or not user.client_id:
            return

        client = db.query(Client).filter(Client.id == user.client_id).first()
        if not client:
            return

        # Update bankroll
        old_bankroll = client.bankroll
        client.bankroll += bet.profit_loss

        # Record history
        history = BankrollHistory(
            user_id=bet.user_id,
            bankroll_value=client.bankroll,
            change_amount=bet.profit_loss,
            change_reason='bet_won' if bet.result == 'won' else 'bet_lost',
            bet_id=bet.id
        )
        db.add(history)


class NotificationQueue:
    """Background job for processing notification queue."""

    def __init__(self):
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self.queue: List[Dict[str, Any]] = []
        self.process_interval_seconds = 10
        self.notifications_sent = 0

    async def start(self):
        """Start the notification processor."""
        if self.is_running:
            return

        self.is_running = True
        self._task = asyncio.create_task(self._process_queue())
        logger.info("Notification queue started")

    async def stop(self):
        """Stop the notification processor."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Notification queue stopped")

    def add_notification(self, notification: Dict[str, Any]):
        """Add a notification to the queue."""
        self.queue.append(notification)

    async def _process_queue(self):
        """Process queued notifications."""
        while self.is_running:
            try:
                while self.queue:
                    notification = self.queue.pop(0)
                    await self._send_notification(notification)
                    self.notifications_sent += 1
            except Exception as e:
                logger.error(f"Error processing notification: {e}")

            await asyncio.sleep(self.process_interval_seconds)

    async def _send_notification(self, notification: Dict[str, Any]):
        """Send a single notification."""
        db = SessionLocal()
        try:
            notification_type = notification.get('type')
            user_id = notification.get('user_id')

            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return

            if notification_type == 'alert':
                await send_alert_notification(
                    db, user,
                    notification.get('title', 'Alert'),
                    notification.get('message', '')
                )
            elif notification_type == 'result':
                await send_result_notification(db, user, notification.get('bet', {}))

        finally:
            db.close()


class OddsRefreshJob:
    """Background job wrapper for odds refresh."""

    def __init__(self):
        self.scheduler = odds_scheduler

    async def start(self):
        """Start odds refresh job."""
        await self.scheduler.start()

    async def stop(self):
        """Stop odds refresh job."""
        await self.scheduler.stop()

    def get_status(self) -> Dict[str, Any]:
        """Get job status."""
        return self.scheduler.get_status()


# Global instances
alert_scheduler = AlertScheduler()
auto_settlement = AutoSettlementChecker()
notification_queue = NotificationQueue()
odds_refresh_job = OddsRefreshJob()


async def start_all_jobs():
    """Start all background jobs."""
    await alert_scheduler.start()
    await auto_settlement.start()
    await notification_queue.start()
    await odds_refresh_job.start()
    logger.info("All background jobs started")


async def stop_all_jobs():
    """Stop all background jobs."""
    await alert_scheduler.stop()
    await auto_settlement.stop()
    await notification_queue.stop()
    await odds_refresh_job.stop()
    logger.info("All background jobs stopped")


def get_jobs_status() -> Dict[str, Any]:
    """Get status of all background jobs."""
    return {
        'alert_scheduler': {
            'is_running': alert_scheduler.is_running,
            'alerts_triggered': alert_scheduler.alerts_triggered
        },
        'auto_settlement': {
            'is_running': auto_settlement.is_running,
            'bets_settled': auto_settlement.bets_settled
        },
        'notification_queue': {
            'is_running': notification_queue.is_running,
            'queue_size': len(notification_queue.queue),
            'notifications_sent': notification_queue.notifications_sent
        },
        'odds_refresh': odds_refresh_job.get_status()
    }
