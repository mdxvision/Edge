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

    # Try database first
    try:
        db_games = db.query(CBBGame).filter(
            CBBGame.game_date >= datetime.combine(today, datetime.min.time()),
            CBBGame.game_date <= datetime.combine(today, datetime.max.time())
        ).all()

        if db_games:
            games_list = []
            for game in db_games:
                game_date_iso = game.game_date.isoformat()
                est_dt = game.game_date - timedelta(hours=5)
                games_list.append({
                    "id": game.id,
                    "game_id": game.espn_id,
                    "espn_id": game.espn_id,
                    "status": game.status,
                    "date": game_date_iso,
                    "game_date": game_date_iso,
                    "game_time_display": est_dt.strftime("%a, %b %d at %I:%M %p") + " EST",
                    "name": f"{game.away_team_name} at {game.home_team_name}",
                    "short_name": f"{game.away_team_name} @ {game.home_team_name}",
                    "status_detail": game.status,
                    "venue": game.venue,
                    "home_team": {
                        "id": str(game.home_team_id) if game.home_team_id else None,
                        "name": game.home_team_name,
                        "abbreviation": game.home_team_name[:3].upper() if game.home_team_name else "",
                        "score": game.home_score or 0,
                        "rank": game.home_team_rank,
                        "record": None
                    },
                    "away_team": {
                        "id": str(game.away_team_id) if game.away_team_id else None,
                        "name": game.away_team_name,
                        "abbreviation": game.away_team_name[:3].upper() if game.away_team_name else "",
                        "score": game.away_score or 0,
                        "rank": game.away_team_rank,
                        "record": None
                    },
                    "odds": {
                        "spread": game.spread,
                        "over_under": game.over_under
                    } if game.spread or game.over_under else None,
                    "is_conference_game": game.is_conference_game,
                    "broadcast": game.broadcast
                })
            return {
                "date": today.isoformat(),
                "count": len(games_list),
                "games": games_list
            }
    except Exception:
        # Database table may not exist, fall through to API
        pass

    # Fetch from ESPN API
    games = await cbb_stats.get_scoreboard(today)

    # Add game_time_display to each game
    for game in games:
        game_date = game.get("game_date") or game.get("date")
        if game_date:
            time_display = add_time_display(game_date)
            if time_display:
                game["game_time_display"] = time_display

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
