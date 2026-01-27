"""
Sportradar API Router

Endpoints for comprehensive sports data:
- Real-time game data
- Player statistics
- Injury reports
- Historical data for backtesting
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date, datetime

from app.db import get_db, User
from app.routers.auth import require_auth
from app.services import sportradar

router = APIRouter(prefix="/sportradar", tags=["Sportradar"])


# =============================================================================
# API Status
# =============================================================================

@router.get("/status")
async def get_sportradar_status():
    """
    Get Sportradar API integration status.

    Returns whether API is enabled and available features.
    """
    return sportradar.get_api_status()


# =============================================================================
# Live Games
# =============================================================================

@router.get("/live/{sport}")
async def get_live_games(
    sport: str,
    user: User = Depends(require_auth)
):
    """
    Get currently live games for a sport.

    Returns real-time game data including scores and game status.

    Supported sports: NFL, NBA, MLB, NHL, SOCCER
    """
    sport = sport.upper()
    if sport not in ["NFL", "NBA", "MLB", "NHL", "SOCCER"]:
        raise HTTPException(status_code=400, detail=f"Unsupported sport: {sport}")

    games = await sportradar.get_live_games(sport)

    return {
        "sport": sport,
        "live_games": games,
        "count": len(games),
        "source": "Sportradar" if sportradar.is_api_enabled() else "Simulated",
    }


@router.get("/boxscore/{sport}/{game_id}")
async def get_game_boxscore(
    sport: str,
    game_id: str,
    user: User = Depends(require_auth)
):
    """
    Get detailed boxscore for a specific game.

    Returns complete game statistics for both teams.
    """
    sport = sport.upper()
    if sport not in ["NFL", "NBA", "MLB", "NHL", "SOCCER"]:
        raise HTTPException(status_code=400, detail=f"Unsupported sport: {sport}")

    boxscore = await sportradar.get_game_boxscore(sport, game_id)

    return boxscore


# =============================================================================
# Schedule
# =============================================================================

@router.get("/schedule/{sport}")
async def get_daily_schedule(
    sport: str,
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    user: User = Depends(require_auth)
):
    """
    Get game schedule for a specific date.

    Returns all games scheduled for the given date with status and times.
    """
    sport = sport.upper()
    if sport not in ["NFL", "NBA", "MLB", "NHL", "SOCCER"]:
        raise HTTPException(status_code=400, detail=f"Unsupported sport: {sport}")

    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        from datetime import date as date_module
        target_date = date_module.today()

    games = await sportradar.get_daily_schedule(sport, target_date)

    return {
        "sport": sport,
        "date": target_date.isoformat(),
        "games": games,
        "count": len(games),
    }


# =============================================================================
# Player Statistics
# =============================================================================

@router.get("/player/{sport}/{player_id}")
async def get_player_profile(
    sport: str,
    player_id: str,
    user: User = Depends(require_auth)
):
    """
    Get detailed player profile and statistics.

    Returns player bio, career stats, and recent performance.
    """
    sport = sport.upper()
    if sport not in ["NFL", "NBA", "MLB", "NHL", "SOCCER"]:
        raise HTTPException(status_code=400, detail=f"Unsupported sport: {sport}")

    profile = await sportradar.get_player_profile(sport, player_id)

    return profile


@router.get("/roster/{sport}/{team_id}")
async def get_team_roster(
    sport: str,
    team_id: str,
    user: User = Depends(require_auth)
):
    """
    Get full team roster with player information.

    Returns all players on the team with their positions and status.
    """
    sport = sport.upper()
    if sport not in ["NFL", "NBA", "MLB", "NHL", "SOCCER"]:
        raise HTTPException(status_code=400, detail=f"Unsupported sport: {sport}")

    roster = await sportradar.get_team_roster(sport, team_id)

    return roster


@router.get("/players/search/{sport}")
async def search_players(
    sport: str,
    q: str = Query(..., min_length=2, description="Search query"),
    position: Optional[str] = Query(None, description="Filter by position"),
    user: User = Depends(require_auth)
):
    """
    Search for players by name.

    Returns matching players with basic info.
    """
    sport = sport.upper()
    if sport not in ["NFL", "NBA", "MLB", "NHL", "SOCCER"]:
        raise HTTPException(status_code=400, detail=f"Unsupported sport: {sport}")

    players = await sportradar.search_players(sport, q, position)

    return {
        "sport": sport,
        "query": q,
        "position_filter": position,
        "players": players,
        "count": len(players),
    }


# =============================================================================
# Injury Reports
# =============================================================================

@router.get("/injuries/{sport}")
async def get_injuries(
    sport: str,
    team: Optional[str] = Query(None, description="Filter by team ID or abbreviation"),
    user: User = Depends(require_auth)
):
    """
    Get current injury report.

    Returns all injured players with status and expected return.

    **Usage:** Factor injuries into betting decisions and lineup analysis.
    """
    sport = sport.upper()
    if sport not in ["NFL", "NBA", "MLB", "NHL"]:
        raise HTTPException(status_code=400, detail=f"Injury reports not available for {sport}")

    if team:
        injuries = await sportradar.get_team_injuries(sport, team)
    else:
        injuries = await sportradar.get_injuries(sport)

    # Group by status
    by_status = {}
    for inj in injuries:
        status = inj.get("status", "Unknown")
        if status not in by_status:
            by_status[status] = []
        by_status[status].append(inj)

    return {
        "sport": sport,
        "team_filter": team,
        "injuries": injuries,
        "total": len(injuries),
        "by_status": {
            status: len(players) for status, players in by_status.items()
        },
        "source": "Sportradar" if sportradar.is_api_enabled() else "Simulated",
    }


@router.get("/injuries/{sport}/impact")
async def get_injury_impact(
    sport: str,
    user: User = Depends(require_auth)
):
    """
    Get injury impact analysis for upcoming games.

    Identifies games where key player injuries may affect outcomes.
    """
    sport = sport.upper()
    if sport not in ["NFL", "NBA", "MLB", "NHL"]:
        raise HTTPException(status_code=400, detail=f"Injury reports not available for {sport}")

    injuries = await sportradar.get_injuries(sport)

    # Identify high-impact injuries (Out status for key positions)
    key_positions = {
        "NFL": ["QB"],
        "NBA": ["PG", "C"],
        "MLB": ["P"],
        "NHL": ["G", "C"],
    }

    high_impact = [
        inj for inj in injuries
        if inj.get("status") in ["Out", "Doubtful"]
        and inj.get("position") in key_positions.get(sport, [])
    ]

    return {
        "sport": sport,
        "high_impact_injuries": high_impact,
        "count": len(high_impact),
        "note": "Key position players ruled Out or Doubtful",
    }


# =============================================================================
# Historical Data
# =============================================================================

@router.get("/historical/{sport}")
async def get_historical_games(
    sport: str,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    team: Optional[str] = Query(None, description="Filter by team"),
    user: User = Depends(require_auth)
):
    """
    Get historical game data for backtesting.

    Returns completed games with final scores and stats.

    **Usage:** Build backtesting datasets for model validation.
    """
    sport = sport.upper()
    if sport not in ["NFL", "NBA", "MLB", "NHL", "SOCCER"]:
        raise HTTPException(status_code=400, detail=f"Unsupported sport: {sport}")

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid start_date format")

    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format")
    else:
        end = start

    # Limit range to prevent excessive API calls
    if (end - start).days > 30:
        raise HTTPException(
            status_code=400,
            detail="Date range cannot exceed 30 days. Use multiple requests for larger ranges."
        )

    games = await sportradar.get_historical_games(sport, start, end, team)

    return {
        "sport": sport,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "team_filter": team,
        "games": games,
        "count": len(games),
    }


# =============================================================================
# Standings
# =============================================================================

@router.get("/standings/{sport}")
async def get_standings(
    sport: str,
    season: Optional[int] = Query(None, description="Season year"),
    season_type: str = Query("REG", description="Season type: PRE, REG, PST"),
    user: User = Depends(require_auth)
):
    """
    Get league standings.

    Returns current standings with win/loss records.
    """
    sport = sport.upper()
    if sport not in ["NFL", "NBA", "MLB", "NHL", "SOCCER"]:
        raise HTTPException(status_code=400, detail=f"Unsupported sport: {sport}")

    if season_type not in ["PRE", "REG", "PST"]:
        raise HTTPException(status_code=400, detail="Invalid season_type. Use: PRE, REG, or PST")

    standings = await sportradar.get_standings(sport, season, season_type)

    return standings


# =============================================================================
# Combined Data Endpoints
# =============================================================================

@router.get("/game-preview/{sport}/{game_id}")
async def get_game_preview(
    sport: str,
    game_id: str,
    user: User = Depends(require_auth)
):
    """
    Get comprehensive game preview.

    Combines schedule, rosters, and injury data for a game.

    **Usage:** Complete pregame analysis for betting research.
    """
    sport = sport.upper()
    if sport not in ["NFL", "NBA", "MLB", "NHL"]:
        raise HTTPException(status_code=400, detail=f"Unsupported sport: {sport}")

    # Get boxscore/game info
    game = await sportradar.get_game_boxscore(sport, game_id)

    # Get injuries for context
    injuries = await sportradar.get_injuries(sport)

    # Extract team names from game
    home_team = game.get("home", {}).get("team", "Unknown")
    away_team = game.get("away", {}).get("team", "Unknown")

    # Filter injuries by team
    home_injuries = [
        inj for inj in injuries
        if home_team.lower() in inj.get("team", "").lower()
    ]
    away_injuries = [
        inj for inj in injuries
        if away_team.lower() in inj.get("team", "").lower()
    ]

    return {
        "sport": sport,
        "game_id": game_id,
        "game": game,
        "injuries": {
            "home": home_injuries,
            "away": away_injuries,
        },
        "injury_summary": {
            "home_out": len([i for i in home_injuries if i.get("status") == "Out"]),
            "away_out": len([i for i in away_injuries if i.get("status") == "Out"]),
        },
    }


@router.get("/team-report/{sport}/{team_id}")
async def get_team_report(
    sport: str,
    team_id: str,
    user: User = Depends(require_auth)
):
    """
    Get comprehensive team report.

    Combines roster, injuries, and recent schedule.
    """
    sport = sport.upper()
    if sport not in ["NFL", "NBA", "MLB", "NHL"]:
        raise HTTPException(status_code=400, detail=f"Unsupported sport: {sport}")

    # Get roster
    roster = await sportradar.get_team_roster(sport, team_id)

    # Get injuries
    injuries = await sportradar.get_team_injuries(sport, team_id)

    # Get recent games (last 7 days)
    from datetime import date as date_module, timedelta
    end = date_module.today()
    start = end - timedelta(days=7)
    recent_games = await sportradar.get_historical_games(sport, start, end, team_id)

    return {
        "sport": sport,
        "team_id": team_id,
        "roster": roster,
        "injuries": injuries,
        "recent_games": recent_games,
        "summary": {
            "roster_size": len(roster.get("players", [])),
            "injured_count": len(injuries),
            "recent_games_count": len(recent_games),
        },
    }
