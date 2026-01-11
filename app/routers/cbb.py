"""
College Basketball (CBB) API Router

Endpoints for NCAA Men's College Basketball data.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
from typing import Optional, List

from app.db import get_db, CBBTeam, CBBGame, CBBRanking
from app.services import cbb_stats
from app.utils.status import normalize_status, add_time_display as util_add_time_display


def add_time_display(game_date_str: str) -> str:
    """Convert game date to EST display format."""
    try:
        dt = datetime.fromisoformat(game_date_str.replace("Z", "+00:00"))
        est_dt = dt - timedelta(hours=5)
        return est_dt.strftime("%a, %b %d at %I:%M %p") + " EST"
    except:
        return None

router = APIRouter(prefix="/cbb", tags=["College Basketball"])


@router.get("/teams")
async def get_teams(
    limit: int = Query(400, le=400, description="Maximum number of teams to return"),
    db: Session = Depends(get_db)
):
    """
    Get all D1 college basketball teams.

    Returns list of teams with ESPN IDs, names, conferences.
    """
    # Try database first
    db_teams = db.query(CBBTeam).limit(limit).all()
    if db_teams:
        return {
            "count": len(db_teams),
            "teams": [
                {
                    "id": team.id,
                    "espn_id": team.espn_id,
                    "name": team.name,
                    "short_name": team.short_name,
                    "abbreviation": team.abbreviation,
                    "location": team.location,
                    "conference_id": team.conference_id,
                    "logo_url": team.logo_url,
                    "ap_rank": team.ap_rank,
                    "net_rank": team.net_rank,
                    "record": f"{team.wins}-{team.losses}" if team.wins or team.losses else None
                }
                for team in db_teams
            ]
        }

    # Fetch from ESPN API
    teams = await cbb_stats.get_teams(limit)
    return {
        "count": len(teams),
        "teams": teams
    }


@router.get("/rankings")
async def get_rankings():
    """
    Get current college basketball rankings.

    Returns AP Top 25, Coaches Poll, and NET rankings when available.
    """
    rankings = await cbb_stats.get_rankings()
    return rankings


@router.get("/games")
async def get_todays_games(db: Session = Depends(get_db)):
    """
    Get today's college basketball games.

    Returns scoreboard with live scores and odds.
    """
    today = date.today()

    # Always fetch from ESPN API for fresh live data
    games = await cbb_stats.get_scoreboard(today)

    # Add game_time_display and normalize status
    for game in games:
        game_date = game.get("game_date") or game.get("date")
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
                "spread": -4.5,  # Default CBB spread
                "total": 142.5,  # Default CBB total
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
    Get college basketball games for a specific date.

    Args:
        game_date: Date in YYYY-MM-DD format
    """
    try:
        target_date = datetime.strptime(game_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    games = await cbb_stats.get_scoreboard(target_date)

    # Add game_time_display to each game
    for game in games:
        game_date_str = game.get("game_date") or game.get("date")
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
    # Check database
    db_team = db.query(CBBTeam).filter(CBBTeam.espn_id == team_id).first()

    # Fetch from ESPN API for full details
    team_info = await cbb_stats.get_team_info(team_id)

    if not team_info and not db_team:
        raise HTTPException(status_code=404, detail="Team not found")

    if db_team:
        team_info["db_id"] = db_team.id
        team_info["ap_rank"] = db_team.ap_rank
        team_info["net_rank"] = db_team.net_rank

    return team_info


@router.get("/team/{team_id}/stats")
async def get_team_stats(team_id: str):
    """
    Get team statistics.

    Args:
        team_id: ESPN team ID
    """
    stats = await cbb_stats.get_team_stats(team_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Team stats not found")
    return stats


@router.get("/team/{team_id}/schedule")
async def get_team_schedule(team_id: str):
    """
    Get team schedule.

    Args:
        team_id: ESPN team ID
    """
    schedule = await cbb_stats.get_team_schedule(team_id)
    return {
        "team_id": team_id,
        "count": len(schedule),
        "games": schedule
    }


@router.get("/game/{game_id}")
async def get_game_details(game_id: str):
    """
    Get detailed game information.

    Args:
        game_id: ESPN game ID
    """
    game = await cbb_stats.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


@router.get("/conferences")
async def get_conferences():
    """
    Get all D1 conferences.
    """
    conferences = await cbb_stats.get_conferences()
    return {
        "count": len(conferences),
        "conferences": conferences
    }


@router.get("/conference/{conference_id}/standings")
async def get_conference_standings(conference_id: str):
    """
    Get standings for a conference.

    Args:
        conference_id: ESPN conference ID
    """
    standings = await cbb_stats.get_conference_standings(conference_id)
    return {
        "conference_id": conference_id,
        "count": len(standings),
        "standings": standings
    }


@router.post("/refresh")
async def refresh_cbb_data(db: Session = Depends(get_db)):
    """
    Manually trigger a refresh of CBB data.

    Updates teams, rankings, and today's games from ESPN API.
    """
    try:
        result = await cbb_stats.refresh_cbb_data(db)
        return {
            "status": "success",
            "message": "CBB data refreshed successfully",
            "details": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh CBB data: {str(e)}"
        )
