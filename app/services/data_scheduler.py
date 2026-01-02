"""
Data Scheduler Service

Handles scheduled data refreshes for MLB, NBA, CBB, and Soccer real-time data.
"""

import asyncio
from datetime import datetime, time
from typing import Dict, Any, Callable
import logging

logger = logging.getLogger(__name__)

# Store scheduled tasks
_scheduled_tasks: Dict[str, asyncio.Task] = {}


async def run_daily_at(hour: int, minute: int, task: Callable, task_name: str):
    """
    Run a task daily at a specific time.

    Args:
        hour: Hour to run (0-23)
        minute: Minute to run (0-59)
        task: Async callable to execute
        task_name: Name for logging
    """
    while True:
        now = datetime.now()
        target = datetime.combine(now.date(), time(hour, minute))

        # If we've passed the target time today, schedule for tomorrow
        if now >= target:
            target = datetime.combine(
                now.date().replace(day=now.day + 1),
                time(hour, minute)
            )

        sleep_seconds = (target - now).total_seconds()
        logger.info(f"Scheduled {task_name} to run in {sleep_seconds:.0f} seconds")

        await asyncio.sleep(sleep_seconds)

        try:
            logger.info(f"Running scheduled task: {task_name}")
            result = await task()
            logger.info(f"Completed {task_name}: {result}")
        except Exception as e:
            logger.error(f"Error in scheduled task {task_name}: {e}")


async def run_every_minutes(minutes: int, task: Callable, task_name: str):
    """
    Run a task every N minutes.

    Args:
        minutes: Interval in minutes
        task: Async callable to execute
        task_name: Name for logging
    """
    while True:
        try:
            logger.info(f"Running scheduled task: {task_name}")
            result = await task()
            logger.info(f"Completed {task_name}: {result}")
        except Exception as e:
            logger.error(f"Error in scheduled task {task_name}: {e}")

        await asyncio.sleep(minutes * 60)


async def refresh_mlb_data_task():
    """Task to refresh MLB data."""
    from app.db import SessionLocal
    from app.services.mlb_stats import refresh_mlb_data

    db = SessionLocal()
    try:
        result = await refresh_mlb_data(db)
        return result
    finally:
        db.close()


def refresh_nba_data_task():
    """Task to refresh NBA data (sync version)."""
    from app.db import SessionLocal
    from app.services.nba_stats import refresh_nba_data

    db = SessionLocal()
    try:
        result = refresh_nba_data(db)
        return result
    finally:
        db.close()


async def refresh_nba_data_async():
    """Async wrapper for NBA data refresh."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, refresh_nba_data_task)


async def refresh_cbb_data_task():
    """Task to refresh College Basketball data."""
    from app.db import SessionLocal
    from app.services.cbb_stats import refresh_cbb_data

    db = SessionLocal()
    try:
        result = await refresh_cbb_data(db)
        return result
    finally:
        db.close()


async def refresh_soccer_data_task():
    """Task to refresh Soccer data."""
    from app.db import SessionLocal
    from app.services.soccer_stats import refresh_soccer_data

    db = SessionLocal()
    try:
        result = await refresh_soccer_data(db)
        return result
    finally:
        db.close()


async def refresh_nfl_data_task():
    """Task to refresh NFL data."""
    from app.db import SessionLocal
    from app.services.nfl_stats import refresh_nfl_data

    db = SessionLocal()
    try:
        result = await refresh_nfl_data(db)
        return result
    finally:
        db.close()


def start_schedulers():
    """
    Start all data refresh schedulers.
    Called during application startup.
    """
    logger.info("Starting data refresh schedulers...")

    # Schedule MLB data refresh at 6 AM and 6 PM daily
    _scheduled_tasks["mlb_morning"] = asyncio.create_task(
        run_daily_at(6, 0, refresh_mlb_data_task, "MLB Morning Refresh")
    )
    _scheduled_tasks["mlb_evening"] = asyncio.create_task(
        run_daily_at(18, 0, refresh_mlb_data_task, "MLB Evening Refresh")
    )

    # Schedule NBA data refresh at 10 AM and 8 PM daily
    _scheduled_tasks["nba_morning"] = asyncio.create_task(
        run_daily_at(10, 0, refresh_nba_data_async, "NBA Morning Refresh")
    )
    _scheduled_tasks["nba_evening"] = asyncio.create_task(
        run_daily_at(20, 0, refresh_nba_data_async, "NBA Evening Refresh")
    )

    # Schedule CBB data refresh at 7 AM and 9 PM daily (season: November-April)
    _scheduled_tasks["cbb_morning"] = asyncio.create_task(
        run_daily_at(7, 0, refresh_cbb_data_task, "CBB Morning Refresh")
    )
    _scheduled_tasks["cbb_evening"] = asyncio.create_task(
        run_daily_at(21, 0, refresh_cbb_data_task, "CBB Evening Refresh")
    )

    # Schedule Soccer data refresh at 8 AM and 4 PM daily (covers European matches)
    _scheduled_tasks["soccer_morning"] = asyncio.create_task(
        run_daily_at(8, 0, refresh_soccer_data_task, "Soccer Morning Refresh")
    )
    _scheduled_tasks["soccer_afternoon"] = asyncio.create_task(
        run_daily_at(16, 0, refresh_soccer_data_task, "Soccer Afternoon Refresh")
    )

    # Schedule NFL data refresh at 9 AM and 5 PM daily (covers game days)
    _scheduled_tasks["nfl_morning"] = asyncio.create_task(
        run_daily_at(9, 0, refresh_nfl_data_task, "NFL Morning Refresh")
    )
    _scheduled_tasks["nfl_evening"] = asyncio.create_task(
        run_daily_at(17, 0, refresh_nfl_data_task, "NFL Evening Refresh")
    )

    # Schedule line movement snapshots every 15 minutes
    # This enables steam move and RLM detection
    _scheduled_tasks["line_snapshots"] = asyncio.create_task(
        run_every_minutes(15, snapshot_lines_task, "Line Movement Snapshot")
    )

    # Track opening lines once per hour (for new games)
    _scheduled_tasks["opening_lines"] = asyncio.create_task(
        run_every_minutes(60, track_opening_lines_task, "Opening Lines Tracker")
    )

    logger.info("Data refresh schedulers started")


def stop_schedulers():
    """
    Stop all scheduled tasks.
    Called during application shutdown.
    """
    logger.info("Stopping data refresh schedulers...")

    for name, task in _scheduled_tasks.items():
        task.cancel()
        logger.info(f"Cancelled scheduler: {name}")

    _scheduled_tasks.clear()
    logger.info("All schedulers stopped")


async def manual_refresh_mlb() -> Dict[str, Any]:
    """Manually trigger MLB data refresh."""
    return await refresh_mlb_data_task()


async def manual_refresh_nba() -> Dict[str, Any]:
    """Manually trigger NBA data refresh."""
    return await refresh_nba_data_async()


async def manual_refresh_cbb() -> Dict[str, Any]:
    """Manually trigger CBB data refresh."""
    return await refresh_cbb_data_task()


async def manual_refresh_soccer() -> Dict[str, Any]:
    """Manually trigger Soccer data refresh."""
    return await refresh_soccer_data_task()


async def manual_refresh_nfl() -> Dict[str, Any]:
    """Manually trigger NFL data refresh."""
    return await refresh_nfl_data_task()


async def snapshot_lines_task():
    """
    Task to snapshot current lines for all upcoming games.
    Tracks line movement for steam move and RLM detection.
    """
    from app.db import SessionLocal, Game
    from app.services.odds_api import fetch_and_store_odds, is_odds_api_configured
    from datetime import datetime, timedelta

    if not is_odds_api_configured():
        logger.warning("Odds API not configured, skipping line snapshot")
        return {"error": "Odds API not configured"}

    db = SessionLocal()
    try:
        # Get upcoming games (next 7 days)
        cutoff = datetime.utcnow() + timedelta(days=7)
        upcoming_games = db.query(Game).filter(
            Game.start_time >= datetime.utcnow(),
            Game.start_time <= cutoff
        ).all()

        logger.info(f"Snapshotting lines for {len(upcoming_games)} upcoming games")

        # Fetch and store odds for all major sports
        sports_to_refresh = ["NBA", "NFL", "NCAA_BASKETBALL", "NHL", "MLB", "SOCCER"]
        results = {}
        total_updated = 0

        for sport in sports_to_refresh:
            try:
                count = await fetch_and_store_odds(db, sport)
                results[sport] = count
                total_updated += count
                logger.info(f"  {sport}: {count} games updated")
            except Exception as e:
                logger.error(f"  Error refreshing {sport}: {e}")
                results[sport] = f"error: {str(e)}"

        return {
            "games_checked": len(upcoming_games),
            "total_updated": total_updated,
            "by_sport": results
        }
    except Exception as e:
        logger.error(f"Error snapshotting lines: {e}")
        return {"error": str(e)}
    finally:
        db.close()


async def track_opening_lines_task():
    """
    Task to capture opening lines for new games.
    Opening lines are important for calculating total movement.
    """
    from app.db import SessionLocal, Game, LineMovementSummary
    from datetime import datetime, timedelta

    db = SessionLocal()
    try:
        # Find games that appeared in last 24 hours without opening lines
        cutoff = datetime.utcnow() - timedelta(hours=24)

        # Get games without line summaries
        games_needing_opening = db.query(Game).filter(
            Game.start_time >= datetime.utcnow()
        ).outerjoin(
            LineMovementSummary, Game.id == LineMovementSummary.game_id
        ).filter(
            LineMovementSummary.id.is_(None)
        ).all()

        logger.info(f"Found {len(games_needing_opening)} games needing opening lines")

        # Opening lines will be captured when odds are first fetched
        return {"games_needing_opening": len(games_needing_opening)}

    except Exception as e:
        logger.error(f"Error tracking opening lines: {e}")
        return {"error": str(e)}
    finally:
        db.close()


def get_scheduler_status() -> Dict[str, Any]:
    """Get status of all schedulers."""
    status = {}
    for name, task in _scheduled_tasks.items():
        status[name] = {
            "running": not task.done(),
            "cancelled": task.cancelled() if task.done() else False
        }
    return status
