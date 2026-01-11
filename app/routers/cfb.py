"""
College Football (CFB) API Router

Endpoints for NCAA FBS College Football data.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
from typing import Optional, List

from app.db import get_db
from app.services import cfb_stats


def add_time_display(game_date_str: str) -> str:
    """Convert game date to EST display format."""
    try:
        dt = datetime.fromisoformat(game_date_str.replace("Z", "+00:00"))
        est_dt = dt - timedelta(hours=5)
        return est_dt.strftime("%a, %b %d at %I:%M %p") + " EST"
    except:
        return None


router = APIRouter(prefix="/cfb", tags=["College Football"])


@router.get("/teams")
async def get_teams(
    limit: int = Query(150, le=200, description="Maximum number of teams to return"),
    db: Session = Depends(get_db)
):
    """
    Get all FBS college football teams.

    Returns list of teams with ESPN IDs, names, conferences.
    """
    teams = await cfb_stats.get_teams(limit)
    return {
        "count": len(teams),
        "teams": teams
    }


@router.get("/rankings")
async def get_rankings():
    """
    Get current college football rankings.

    Returns CFP, AP Top 25, and Coaches Poll rankings.
    """
    rankings = await cfb_stats.get_rankings()
    return rankings


@router.get("/games")
async def get_todays_games(db: Session = Depends(get_db)):
    """
    Get today's college football games.

    Returns scoreboard with live scores and odds.
    Note: CFB season typically runs Aug-Jan. Returns empty if off-season.
    """
    today = date.today()
    games = await cfb_stats.get_scoreboard(today)

    # Filter out past games (ESPN sometimes returns old bowl games)
    current_games = []
    for game in games:
        utc_date_str = game.get("date")
        if utc_date_str:
            try:
                # Add game_time_display
                time_display = add_time_display(utc_date_str)
                if time_display:
                    game["game_time_display"] = time_display
                
                # Add game_date (local EST date) from UTC source to avoid drift
                dt_obj = datetime.fromisoformat(utc_date_str.replace("Z", "+00:00"))
                est_dt = dt_obj - timedelta(hours=5)
                game["game_date"] = est_dt.strftime("%Y-%m-%d")

                # Filter: Only include games from today or future (local EST)
                if est_dt.date() >= today:
                    current_games.append(game)
            except Exception as e:
                print(f"CFB date error: {e}")
                pass

    # Provide default odds if no real odds available (allows 8-factor analysis)
    for game in current_games:
        if "odds" not in game or not game["odds"] or not game["odds"].get("spread"):
            game["odds"] = {
                "spread": -3.5,  # Default CFB spread
                "total": 52.5,   # Default CFB total
                "details": "N/A"
            }

    return {
        "date": today.isoformat(),
        "count": len(current_games),
        "games": current_games,
        "note": "CFB season typically runs August-January" if len(current_games) == 0 else None
    }


@router.get("/games/{game_date}")
async def get_games_by_date(
    game_date: str,
    db: Session = Depends(get_db)
):
    """
    Get college football games for a specific date.

    Args:
        game_date: Date in YYYY-MM-DD format
    """
    try:
        target_date = datetime.strptime(game_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    games = await cfb_stats.get_scoreboard(target_date)

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


@router.get("/team/{team_id}")
async def get_team(team_id: str, db: Session = Depends(get_db)):
    """
    Get detailed team information.

    Args:
        team_id: ESPN team ID
    """
    team_info = await cfb_stats.get_team_info(team_id)

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
    schedule = await cfb_stats.get_team_schedule(team_id)
    return {
        "team_id": team_id,
        "count": len(schedule),
        "games": schedule
    }


@router.get("/conferences")
async def get_conferences():
    """
    Get all FBS conferences.
    """
    conferences = await cfb_stats.get_conferences()
    return {
        "count": len(conferences),
        "conferences": conferences
    }


@router.post("/refresh")
async def refresh_cfb_data(db: Session = Depends(get_db)):
    """
    Manually trigger a refresh of CFB data.

    Updates teams, rankings, and today's games from ESPN API.
    """
    try:
        result = await cfb_stats.refresh_cfb_data(db)
        return {
            "status": "success",
            "message": "CFB data refreshed successfully",
            "details": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh CFB data: {str(e)}"
        )
