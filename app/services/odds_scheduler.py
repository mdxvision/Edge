"""
Odds scheduler service for auto-refreshing odds data.
Provides functionality to periodically fetch and update odds from The Odds API.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from sqlalchemy.orm import Session

from app.db import SessionLocal, Game, Market, Line, OddsSnapshot, LineMovement
from app.services.odds_api import fetch_odds, SPORT_MAPPING


logger = logging.getLogger(__name__)

# Configuration
REFRESH_INTERVAL_MINUTES = 15
SNAPSHOT_INTERVAL_MINUTES = 30
LINE_MOVEMENT_THRESHOLD_PERCENT = 2.0  # Minimum change to record as movement


class OddsScheduler:
    """Scheduler for periodic odds updates."""

    def __init__(self):
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self.last_refresh: Optional[datetime] = None
        self.refresh_count = 0
        self.error_count = 0

    async def start(self):
        """Start the odds refresh scheduler."""
        if self.is_running:
            logger.warning("Odds scheduler is already running")
            return

        self.is_running = True
        self._task = asyncio.create_task(self._run_scheduler())
        logger.info("Odds scheduler started")

    async def stop(self):
        """Stop the odds refresh scheduler."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Odds scheduler stopped")

    async def _run_scheduler(self):
        """Main scheduler loop."""
        while self.is_running:
            try:
                await self.refresh_all_odds()
                self.last_refresh = datetime.utcnow()
                self.refresh_count += 1
            except Exception as e:
                self.error_count += 1
                logger.error(f"Error in odds refresh: {e}")

            # Wait for next refresh interval
            await asyncio.sleep(REFRESH_INTERVAL_MINUTES * 60)

    async def refresh_all_odds(self):
        """Refresh odds for all supported sports."""
        db = SessionLocal()
        try:
            sports = list(SPORT_MAPPING.keys())

            for sport_key in sports:
                try:
                    await self._refresh_sport_odds(db, sport_key)
                except Exception as e:
                    logger.error(f"Error refreshing odds for {sport_key}: {e}")

        finally:
            db.close()

    async def _refresh_sport_odds(self, db: Session, sport_key: str):
        """Refresh odds for a specific sport."""
        odds_data = await fetch_odds(sport_key)

        if not odds_data:
            return

        for game_data in odds_data:
            await self._process_game_odds(db, game_data, sport_key)

        db.commit()

    async def _process_game_odds(self, db: Session, game_data: Dict[str, Any], sport_key: str):
        """Process odds for a single game."""
        game_id = game_data.get('id')
        commence_time = game_data.get('commence_time')
        home_team = game_data.get('home_team')
        away_team = game_data.get('away_team')

        # Find or create game
        game = db.query(Game).filter(
            Game.sport == sport_key,
            Game.start_time == datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
        ).first()

        if not game:
            # Game not in our database yet, skip
            return

        bookmakers = game_data.get('bookmakers', [])

        for bookmaker in bookmakers:
            book_name = bookmaker.get('title', 'Unknown')
            markets = bookmaker.get('markets', [])

            for market in markets:
                market_type = market.get('key')
                outcomes = market.get('outcomes', [])

                for outcome in outcomes:
                    selection = outcome.get('name')
                    price = outcome.get('price')
                    point = outcome.get('point')

                    if price is None:
                        continue

                    # Convert to American odds if decimal
                    american_odds = self._convert_to_american(price)

                    # Record snapshot
                    await self._record_odds_snapshot(
                        db, game.id, market_type, book_name,
                        american_odds, point
                    )

                    # Check for line movement
                    await self._check_line_movement(
                        db, game.id, market_type, book_name,
                        american_odds, point
                    )

    async def _record_odds_snapshot(
        self,
        db: Session,
        game_id: int,
        market_type: str,
        sportsbook: str,
        odds: int,
        line_value: Optional[float]
    ):
        """Record an odds snapshot."""
        snapshot = OddsSnapshot(
            game_id=game_id,
            market_type=market_type,
            sportsbook=sportsbook,
            odds=odds,
            line_value=line_value
        )
        db.add(snapshot)

    async def _check_line_movement(
        self,
        db: Session,
        game_id: int,
        market_type: str,
        sportsbook: str,
        current_odds: int,
        current_line: Optional[float]
    ):
        """Check and record line movements."""
        # Get most recent snapshot for this market
        previous = db.query(OddsSnapshot).filter(
            OddsSnapshot.game_id == game_id,
            OddsSnapshot.market_type == market_type,
            OddsSnapshot.sportsbook == sportsbook
        ).order_by(OddsSnapshot.captured_at.desc()).offset(1).first()

        if not previous:
            return

        # Calculate movement percentage
        if previous.odds != 0:
            movement_pct = abs((current_odds - previous.odds) / abs(previous.odds)) * 100
        else:
            movement_pct = 0

        # Only record significant movements
        if movement_pct < LINE_MOVEMENT_THRESHOLD_PERCENT:
            return

        # Determine movement direction
        direction = self._classify_movement(
            previous.odds, current_odds,
            previous.line_value, current_line
        )

        movement = LineMovement(
            game_id=game_id,
            market_type=market_type,
            sportsbook=sportsbook,
            previous_odds=previous.odds,
            current_odds=current_odds,
            previous_line=previous.line_value,
            current_line=current_line,
            movement_percentage=movement_pct,
            direction=direction
        )
        db.add(movement)

    def _classify_movement(
        self,
        prev_odds: int,
        curr_odds: int,
        prev_line: Optional[float],
        curr_line: Optional[float]
    ) -> str:
        """Classify the type of line movement."""
        # Steam move: rapid movement in one direction (sharp money)
        # Reverse line move: line moves opposite to betting percentages
        # For now, simple classification based on odds direction

        if curr_odds < prev_odds:
            # Odds shortened (more likely outcome)
            return 'sharp'
        elif curr_odds > prev_odds:
            # Odds lengthened (less likely outcome)
            return 'public'
        return 'neutral'

    def _convert_to_american(self, decimal_odds: float) -> int:
        """Convert decimal odds to American format."""
        if decimal_odds >= 2.0:
            return int((decimal_odds - 1) * 100)
        else:
            return int(-100 / (decimal_odds - 1))

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            'is_running': self.is_running,
            'last_refresh': self.last_refresh.isoformat() if self.last_refresh else None,
            'refresh_count': self.refresh_count,
            'error_count': self.error_count,
            'refresh_interval_minutes': REFRESH_INTERVAL_MINUTES
        }


# Global scheduler instance
odds_scheduler = OddsScheduler()


def get_line_movements(
    db: Session,
    game_id: Optional[int] = None,
    sport: Optional[str] = None,
    hours: int = 24,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Get recent line movements."""
    query = db.query(LineMovement)

    if game_id:
        query = query.filter(LineMovement.game_id == game_id)

    since = datetime.utcnow() - timedelta(hours=hours)
    query = query.filter(LineMovement.recorded_at >= since)

    movements = query.order_by(LineMovement.recorded_at.desc()).limit(limit).all()

    return [
        {
            'id': m.id,
            'game_id': m.game_id,
            'market_type': m.market_type,
            'sportsbook': m.sportsbook,
            'previous_odds': m.previous_odds,
            'current_odds': m.current_odds,
            'previous_line': m.previous_line,
            'current_line': m.current_line,
            'movement_percentage': m.movement_percentage,
            'direction': m.direction,
            'recorded_at': m.recorded_at.isoformat()
        }
        for m in movements
    ]


def get_odds_history(
    db: Session,
    game_id: int,
    market_type: Optional[str] = None,
    sportsbook: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get odds history for a game."""
    query = db.query(OddsSnapshot).filter(OddsSnapshot.game_id == game_id)

    if market_type:
        query = query.filter(OddsSnapshot.market_type == market_type)
    if sportsbook:
        query = query.filter(OddsSnapshot.sportsbook == sportsbook)

    snapshots = query.order_by(OddsSnapshot.captured_at.asc()).all()

    return [
        {
            'id': s.id,
            'market_type': s.market_type,
            'sportsbook': s.sportsbook,
            'odds': s.odds,
            'line_value': s.line_value,
            'captured_at': s.captured_at.isoformat()
        }
        for s in snapshots
    ]
