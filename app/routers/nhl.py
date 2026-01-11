"""
NHL API Router

Endpoints for NHL real-time data from ESPN.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
from typing import Optional

from app.db import get_db
from app.services import nhl_stats


def add_time_display(game_date_str: str) -> str:
    """Convert game date to EST display format."""
    try:
        dt = datetime.fromisoformat(game_date_str.replace("Z", "+00:00"))
        est_dt = dt - timedelta(hours=5)
        return est_dt.strftime("%a, %b %d at %I:%M %p") + " EST"
    except:
        return None


def normalize_status(status: str) -> str:
    """Convert ESPN status codes to user-friendly labels."""
    if not status:
        return "Scheduled"

    status_lower = status.lower()

    # Live game indicators
    if any(x in status_lower for x in ['in_progress', 'in progress', 'status_in_progress']):
        return "LIVE"
    if 'end_period' in status_lower or 'halftime' in status_lower or 'intermission' in status_lower:
        return "LIVE"  # Between periods/halves is still live
    if any(x in status_lower for x in ['1st', '2nd', '3rd', 'ot', 'overtime']):
        return "LIVE"

    # Final game indicators
    if any(x in status_lower for x in ['final', 'finished', 'status_final', 'complete']):
        return "Final"

    # Scheduled
    if any(x in status_lower for x in ['scheduled', 'pre', 'status_scheduled']):
        return "Scheduled"

    # If contains time, it's scheduled
    if 'pm' in status_lower or 'am' in status_lower:
        return status  # Keep the time display

    return status


router = APIRouter(prefix="/nhl", tags=["NHL"])


@router.get("/teams")
async def get_teams(db: Session = Depends(get_db)):
    """
    Get all NHL teams.

    Returns list of teams with ESPN IDs, names, and divisions.
    """
    teams = await nhl_stats.get_teams()
    return {
        "count": len(teams),
        "teams": teams
    }


@router.get("/games")
async def get_todays_games(db: Session = Depends(get_db)):
    """
    Get today's NHL games.

    Returns scoreboard with live scores and odds.
    """
    today = date.today()
    games = await nhl_stats.get_scoreboard(today)

    # Add game_time_display and normalize status
    for game in games:
        game_date = game.get("date")
        if game_date:
            time_display = add_time_display(game_date)
            if time_display:
                game["game_time_display"] = time_display

        # Normalize status
        game["status"] = normalize_status(game.get("status", ""))

        # Add game_date (local EST date)
        # Use 'date' (UTC) as source to avoid drift if 'game_date' was already set in cache
        utc_date_str = game.get("date")
        if utc_date_str:
            try:
                dt_obj = datetime.fromisoformat(utc_date_str.replace("Z", "+00:00"))
                est_dt = dt_obj - timedelta(hours=5)
                game["game_date"] = est_dt.strftime("%Y-%m-%d")
            except:
                game["game_date"] = today.isoformat()

    # Provide default odds if no real odds available (allows 8-factor analysis)
    for game in games:
        if "odds" not in game or not game["odds"] or all(v is None for v in game.get("odds", {}).values()):
            game["odds"] = {
                "spread": -1.5,  # Default NHL puck line
                "total": 6.5,    # Default NHL total
            }

    return {
        "date": today.isoformat(),
        "count": len(games),
        "games": games
    }


@router.get("/games/{game_date}")
async def get_games_by_date(
    game_date: str,
    db: Session = Depends(get_db)
):
    """
    Get NHL games for a specific date.

    Args:
        game_date: Date in YYYY-MM-DD format
    """
    try:
        target_date = datetime.strptime(game_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    games = await nhl_stats.get_scoreboard(target_date)

    # Add game_time_display to each game
    for game in games:
        game_date_str = game.get("date")
        if game_date_str:
            time_display = add_time_display(game_date_str)
            if time_display:
                game["game_time_display"] = time_display

    return {
        "date": game_date,
        "count": len(games),
        "games": games
    }


@router.get("/standings")
async def get_standings():
    """
    Get current NHL standings.

    Returns standings by conference and division.
    """
    standings = await nhl_stats.get_standings()
    if "error" in standings:
        raise HTTPException(status_code=503, detail=standings["error"])
    return standings


@router.get("/team/{team_id}")
async def get_team(team_id: str, db: Session = Depends(get_db)):
    """
    Get detailed team information.

    Args:
        team_id: ESPN team ID
    """
    team_info = await nhl_stats.get_team_info(team_id)

    if not team_info:
        raise HTTPException(status_code=404, detail="Team not found")

    return team_info


@router.get("/team/{team_id}/schedule")
async def get_team_schedule(team_id: str):
    """
    Get team schedule.

    Args:
        team_id: ESPN team ID
    """
    schedule = await nhl_stats.get_team_schedule(team_id)
    return {
        "team_id": team_id,
        "count": len(schedule),
        "games": schedule
    }


@router.post("/refresh")
async def refresh_nhl_data(db: Session = Depends(get_db)):
    """
    Manually trigger a refresh of NHL data.

    Updates teams and today's games from ESPN API.
    """
    try:
        result = await nhl_stats.refresh_nhl_data(db)
        return {
            "status": "success",
            "message": "NHL data refreshed successfully",
            "details": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh NHL data: {str(e)}"
        )
