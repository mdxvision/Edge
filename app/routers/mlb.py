"""
MLB API Router

Provides endpoints for MLB real-time data.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import date, datetime

from app.services import mlb_stats
from app.services.data_scheduler import manual_refresh_mlb

router = APIRouter(prefix="/mlb", tags=["MLB"])


@router.get("/teams")
async def get_teams():
    """
    Get all MLB teams.

    Returns list of teams with their MLB IDs, names, and divisions.
    """
    teams = await mlb_stats.get_teams()
    if not teams:
        raise HTTPException(status_code=503, detail="Unable to fetch MLB teams")
    return {"teams": teams, "count": len(teams)}


@router.get("/games/today")
async def get_todays_games():
    """
    Get today's MLB games.

    Returns games scheduled for today with live scores.
    """
    from datetime import date
    today = date.today()
    games = await mlb_stats.get_schedule(today, today)
    return {
        "date": today.isoformat(),
        "count": len(games),
        "games": games
    }


@router.get("/games")
async def get_games(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    team_id: Optional[int] = Query(None, description="Filter by MLB team ID")
):
    """
    Get MLB game schedule.

    Returns upcoming games with probable pitchers and team records.
    """
    from datetime import timedelta

    start = None
    end = None

    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")

    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")

    games = await mlb_stats.get_schedule(start, end, team_id)

    # Add game_time_display in EST for each game
    for game in games:
        game_time = game.get("game_time")
        if game_time:
            try:
                # Parse ISO format datetime
                utc_dt = datetime.fromisoformat(game_time.replace("Z", "+00:00"))
                est_dt = utc_dt - timedelta(hours=5)
                game["game_time_display"] = est_dt.strftime("%a, %b %d at %I:%M %p") + " EST"
            except:
                pass

    return {"games": games, "count": len(games)}


@router.get("/team/{team_id}/stats")
async def get_team_stats(
    team_id: int,
    season: Optional[int] = Query(None, description="Season year (defaults to current)")
):
    """
    Get comprehensive team statistics.

    Returns batting, pitching, and fielding stats for a team.
    """
    stats = await mlb_stats.get_team_stats(team_id, season)
    if "error" in stats:
        raise HTTPException(status_code=404, detail=stats["error"])
    return stats


@router.get("/team/{team_id}/roster")
async def get_team_roster(team_id: int):
    """
    Get current roster for a team.

    Returns list of active players with positions.
    """
    roster = await mlb_stats.get_roster(team_id)
    return {"roster": roster, "count": len(roster)}


@router.get("/player/{player_id}/stats")
async def get_player_stats(
    player_id: int,
    season: Optional[int] = Query(None, description="Season year (defaults to current)")
):
    """
    Get player statistics.

    Returns batting and/or pitching stats depending on player type.
    """
    stats = await mlb_stats.get_player_stats(player_id, season)
    if not stats or "error" in stats:
        raise HTTPException(status_code=404, detail="Player stats not found")
    return stats


@router.get("/player/{player_id}/game-logs")
async def get_pitcher_game_logs(
    player_id: int,
    limit: int = Query(10, ge=1, le=50, description="Number of recent games")
):
    """
    Get recent game logs for a pitcher.

    Returns detailed stats from recent starts.
    """
    logs = await mlb_stats.get_pitcher_game_logs(player_id, limit)
    return {"game_logs": logs, "count": len(logs)}


@router.get("/standings")
async def get_standings(
    season: Optional[int] = Query(None, description="Season year (defaults to current)")
):
    """
    Get current MLB standings.

    Returns standings by division with win/loss records and run differentials.
    """
    standings = await mlb_stats.get_standings(season)
    if not standings:
        raise HTTPException(status_code=503, detail="Unable to fetch standings")
    return standings


@router.get("/ballpark-factors")
async def get_ballpark_factors(
    venue: Optional[str] = Query(None, description="Specific venue name")
):
    """
    Get ballpark factors for run/HR/hit adjustments.

    Higher values indicate more offense-friendly parks.
    """
    factors = await mlb_stats.get_ballpark_factors(venue)
    if venue and not factors:
        raise HTTPException(status_code=404, detail="Venue not found")
    return {"factors": factors}


@router.get("/results")
async def get_game_results(
    season: Optional[int] = Query(None, description="Season year (defaults to current)"),
    team_id: Optional[int] = Query(None, description="Filter by team ID")
):
    """
    Get historical game results.

    Returns completed game results for model training and analysis.
    """
    results = await mlb_stats.get_game_results(season, team_id)
    return {"results": results, "count": len(results)}


@router.get("/search/players")
async def search_players(
    name: str = Query(..., min_length=2, description="Player name to search")
):
    """
    Search for MLB players by name.

    Returns list of matching players with their IDs and teams.
    """
    players = await mlb_stats.search_players(name)
    return {"players": players, "count": len(players)}


@router.post("/refresh")
async def refresh_data():
    """
    Manually trigger MLB data refresh.

    Updates teams, schedule, and standings from MLB API.
    """
    try:
        result = await manual_refresh_mlb()
        return {"status": "success", "refreshed": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Refresh failed: {str(e)}")
