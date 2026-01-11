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


async def refresh_nhl_data_task():
    """Task to refresh NHL data."""
    from app.db import SessionLocal
    from app.services.nhl_stats import refresh_nhl_data

    db = SessionLocal()
    try:
        result = await refresh_nhl_data(db)
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

    # Schedule NHL data refresh at 11 AM and 6 PM daily
    _scheduled_tasks["nhl_morning"] = asyncio.create_task(
        run_daily_at(11, 0, refresh_nhl_data_task, "NHL Morning Refresh")
    )
    _scheduled_tasks["nhl_evening"] = asyncio.create_task(
        run_daily_at(18, 0, refresh_nhl_data_task, "NHL Evening Refresh")
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

    # NEW: High-frequency live score tracking
    _scheduled_tasks["nba_live_tracker"] = asyncio.create_task(
        run_every_minutes(1, refresh_nba_live_scores_task, "NBA Live Score Polling")
    )
    _scheduled_tasks["nhl_live_tracker"] = asyncio.create_task(
        run_every_minutes(1, refresh_nhl_live_scores_task, "NHL Live Score Polling")
    )
    _scheduled_tasks["nfl_live_tracker"] = asyncio.create_task(
        run_every_minutes(1, refresh_nfl_live_scores_task, "NFL Live Score Polling")
    )
    _scheduled_tasks["cbb_live_tracker"] = asyncio.create_task(
        run_every_minutes(1, refresh_cbb_live_scores_task, "CBB Live Score Polling")
    )


async def refresh_nba_live_scores_task():
    """Task to poll live NBA scores every minute."""
    from app.db import SessionLocal, Game, Team
    from app.services.nba_stats import get_live_nba_scores, get_teams
    from datetime import datetime
    
    # This keeps 'Game' table updated with live scores
    db = SessionLocal()
    try:
        live_data = get_live_nba_scores()
        if not live_data:
            return {"live_games_updated": 0}

        # Build mapping of NBA ID to Team Name from static data
        # This is needed because our DB doesn't store NBA ID
        all_teams = get_teams()
        nba_id_to_name = {t["nba_id"]: t["name"] for t in all_teams}
        
        updated_count = 0
        
        for data in live_data:
            home_nba_id = data.get("home_team_id")
            away_nba_id = data.get("away_team_id")
            
            home_name = nba_id_to_name.get(home_nba_id)
            away_name = nba_id_to_name.get(away_nba_id)
            
            if not home_name or not away_name:
                continue
                
            # Find teams in DB
            home_team = db.query(Team).filter(Team.sport == "NBA", Team.name == home_name).first()
            away_team = db.query(Team).filter(Team.sport == "NBA", Team.name == away_name).first()
            
            if not home_team or not away_team:
                continue
                
            # Find the active game
            # We look for games starting today (or essentially active now)
            # Since live polling happens during the game, checking date similarity is usually enough
            today_start = datetime.utcnow().date()
            
            game = db.query(Game).filter(
                Game.sport == "NBA",
                Game.home_team_id == home_team.id,
                Game.away_team_id == away_team.id
                # Removing strict date check to allow for late night games spilling over or timezone diffs
                # ideally we check if start_time is within last 12 hours
            ).order_by(Game.start_time.desc()).first()
            
            if game:
                # Check if game is recent enough (within 24 hours) to be the live one
                time_diff = datetime.utcnow() - game.start_time
                if abs(time_diff.total_seconds()) < 86400: # 24 hours
                    game.status = data['status']
                    game.current_score = f"{data['home_score']}-{data['away_score']}"
                    updated_count += 1

        db.commit()
        return {"live_games_updated": updated_count}

    except Exception as e:
        logger.error(f"Error in live score task: {e}")
        return {"error": str(e)}
    finally:
        db.close()



async def refresh_nhl_live_scores_task():
    """Task to poll live NHL scores every minute."""
    from app.db import SessionLocal
    from app.services.nhl_stats import get_scoreboard, store_nhl_game
    
    db = SessionLocal()
    try:
        games = await get_scoreboard()
        if not games:
             return {"live_games_updated": 0}

        updated_count = 0
        for game_data in games:
            # Only update active games or final games to capture score
            # store_nhl_game handles logic
            game = store_nhl_game(db, game_data)
            if game:
                updated_count += 1
        
        db.commit()
        return {"live_games_updated": updated_count}
    except Exception as e:
        logger.error(f"Error in NHL live score task: {e}")
        return {"error": str(e)}
    finally:
        db.close()


async def refresh_nfl_live_scores_task():
    """Task to poll live NFL scores every minute."""
    from app.db import SessionLocal
    # We can reuse get_scoreboard but need a store function or just direct update
    # nfl_stats.refresh_nfl_data is daily. Let's look at get_scoreboard usage.
    # nfl_stats.refresh_nfl_data calls get_current_week_games which calls get_scoreboard(None).
    # We can just use refresh_nfl_data but it might be heavy (updates teams too).
    # Better to just fetch scoreboard and update existing games.
    from app.services.nfl_stats import get_scoreboard
    from app.db import NFLGame
    
    db = SessionLocal()
    try:
        games = await get_scoreboard()
        if not games:
             return {"live_games_updated": 0}

        updated_count = 0
        for game_data in games:
            espn_id = game_data.get("espn_id")
            if not espn_id: continue
            
            existing = db.query(NFLGame).filter(NFLGame.espn_id == espn_id).first()
            if existing:
                # Update live fields
                existing.status = game_data.get("status", existing.status)
                existing.home_score = game_data.get("home_team", {}).get("score")
                existing.away_score = game_data.get("away_team", {}).get("score")
                existing.time_remaining = game_data.get("time_remaining")
                existing.quarter = game_data.get("quarter")
                updated_count += 1
        
        db.commit()
        return {"live_games_updated": updated_count}
    except Exception as e:
        logger.error(f"Error in NFL live score task: {e}")
        return {"error": str(e)}
    finally:
        db.close()


async def refresh_cbb_live_scores_task():
    """Task to poll live CBB scores every minute."""
    from app.db import SessionLocal
    from app.services.cbb_stats import get_scoreboard, store_cbb_game
    
    db = SessionLocal()
    try:
        games = await get_scoreboard()
        if not games:
             return {"live_games_updated": 0}

        updated_count = 0
        for game_data in games:
            # store_cbb_game handles logic
            game = store_cbb_game(db, game_data)
            if game:
                updated_count += 1
        
        db.commit()
        return {"live_games_updated": updated_count}
    except Exception as e:
        logger.error(f"Error in CBB live score task: {e}")
        return {"error": str(e)}
    finally:
        db.close()


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


async def manual_refresh_nhl() -> Dict[str, Any]:
    """Manually trigger NHL data refresh."""
    return await refresh_nhl_data_task()


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
