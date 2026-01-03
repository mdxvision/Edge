"""
NFL API Router

Endpoints for NFL real-time data from ESPN.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
from typing import Optional

from app.db import get_db, NFLTeam, NFLGame, Game, Team, Market, Line, OddsSnapshot
from app.services import nfl_stats
from sqlalchemy import desc

router = APIRouter(prefix="/nfl", tags=["NFL"])


def get_odds_for_game(db: Session, game_id: int):
    """
    Look up odds from the OddsSnapshot table for a specific game.
    Returns the latest spread and over/under.
    """
    odds = {
        "spread": None,
        "over_under": None
    }

    # Get latest spread snapshot for this game
    spread_snapshot = db.query(OddsSnapshot).filter(
        OddsSnapshot.game_id == game_id,
        OddsSnapshot.market_type == 'spreads'
    ).order_by(desc(OddsSnapshot.captured_at)).first()

    if spread_snapshot and spread_snapshot.line_value is not None:
        odds["spread"] = spread_snapshot.line_value

    # Get latest totals snapshot for this game
    totals_snapshot = db.query(OddsSnapshot).filter(
        OddsSnapshot.game_id == game_id,
        OddsSnapshot.market_type == 'totals'
    ).order_by(desc(OddsSnapshot.captured_at)).first()

    if totals_snapshot and totals_snapshot.line_value is not None:
        odds["over_under"] = totals_snapshot.line_value

    return odds if (odds["spread"] is not None or odds["over_under"] is not None) else None


@router.get("/teams")
async def get_teams(db: Session = Depends(get_db)):
    """
    Get all NFL teams.

    Returns list of teams with ESPN IDs, names, and divisions.
    """
    # Try database first
    db_teams = db.query(NFLTeam).all()
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
                    "logo_url": team.logo_url,
                    "conference": team.conference,
                    "division": team.division,
                    "record": f"{team.wins}-{team.losses}" + (f"-{team.ties}" if team.ties else "")
                }
                for team in db_teams
            ]
        }

    # Fetch from ESPN API
    teams = await nfl_stats.get_teams()
    return {
        "count": len(teams),
        "teams": teams
    }


@router.get("/games")
async def get_games(db: Session = Depends(get_db)):
    """
    Get current week NFL games.

    Returns scoreboard with live scores and odds.
    """
    # First check the generic Game table (has fresh Odds API data)
    from datetime import datetime as dt
    nfl_games = db.query(Game).filter(
        Game.sport.in_(["NFL", "americanfootball_nfl"]),
        Game.start_time >= dt.utcnow() - timedelta(days=1)  # Include recent/upcoming
    ).order_by(Game.start_time.asc()).all()

    if nfl_games:
        games_list = []
        for game in nfl_games:
            home_team = db.query(Team).filter(Team.id == game.home_team_id).first()
            away_team = db.query(Team).filter(Team.id == game.away_team_id).first()

            # Get odds from OddsSnapshot table
            odds = get_odds_for_game(db, game.id)

            # Convert UTC to EST for display
            est_time = game.start_time - timedelta(hours=5)

            # Format as readable EST string
            est_display = est_time.strftime("%a, %b %d at %I:%M %p") + " EST"

            games_list.append({
                "id": game.id,
                "status": "Scheduled",
                "game_date": est_time.isoformat(),
                "game_time_display": est_display,
                "venue": game.venue,
                "home_team": {
                    "name": home_team.name if home_team else "Unknown",
                    "score": None,
                },
                "away_team": {
                    "name": away_team.name if away_team else "Unknown",
                    "score": None,
                },
                "odds": odds,
            })

        return {
            "date": date.today().isoformat(),
            "count": len(games_list),
            "games": games_list
        }

    # Fallback: Try NFLGame table
    try:
        db_games = db.query(NFLGame).order_by(NFLGame.game_date.asc()).limit(20).all()

        if db_games:
            games_list = []
            for game in db_games:
                # First try to get odds from NFLGame table
                game_odds = None
                if game.spread or game.over_under:
                    game_odds = {
                        "spread": game.spread,
                        "over_under": game.over_under
                    }
                # If no odds in NFLGame, try to get from The Odds API data
                elif game.home_team_name and game.away_team_name and game.game_date:
                    api_odds = get_odds_from_odds_api(
                        db,
                        game.home_team_name,
                        game.away_team_name,
                        game.game_date.date() if hasattr(game.game_date, 'date') else game.game_date
                    )
                    if api_odds:
                        game_odds = api_odds

                games_list.append({
                    "id": game.id,
                    "espn_id": game.espn_id,
                    "status": game.status,
                    "game_date": game.game_date.isoformat() if game.game_date else None,
                    "venue": game.venue,
                    "week": game.week,
                    "home_team": {
                        "name": game.home_team_name,
                        "score": game.home_score,
                    },
                    "away_team": {
                        "name": game.away_team_name,
                        "score": game.away_score,
                    },
                    "odds": game_odds,
                    "broadcast": game.broadcast,
                    "quarter": game.quarter,
                    "time_remaining": game.time_remaining
                })

            return {
                "date": date.today().isoformat(),
                "count": len(games_list),
                "games": games_list
            }
    except Exception:
        # Database table may not exist, fall through to API
        pass

    # Fetch from ESPN API
    games = await nfl_stats.get_current_week_games()

    # Enrich ESPN API results with odds from The Odds API data
    for game in games:
        if not game.get("odds"):
            home_name = game.get("home_team", {}).get("name", "")
            away_name = game.get("away_team", {}).get("name", "")
            game_date_str = game.get("game_date", "")

            if home_name and away_name and game_date_str:
                try:
                    game_date_obj = datetime.fromisoformat(game_date_str.replace("Z", "+00:00")).date()
                    api_odds = get_odds_from_odds_api(db, home_name, away_name, game_date_obj)
                    if api_odds:
                        game["odds"] = api_odds
                except (ValueError, TypeError):
                    pass

    return {
        "date": date.today().isoformat(),
        "count": len(games),
        "games": games
    }


@router.get("/games/{game_date}")
async def get_games_by_date(
    game_date: str,
    db: Session = Depends(get_db)
):
    """
    Get NFL games for a specific date.

    Args:
        game_date: Date in YYYY-MM-DD format
    """
    try:
        target_date = datetime.strptime(game_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    games = await nfl_stats.get_scoreboard(target_date)
    return {
        "date": game_date,
        "count": len(games),
        "games": games
    }


@router.get("/standings")
async def get_standings():
    """
    Get current NFL standings.

    Returns standings by conference and division.
    """
    standings = await nfl_stats.get_standings()
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
    # Check database
    db_team = db.query(NFLTeam).filter(NFLTeam.espn_id == team_id).first()

    # Fetch from ESPN API for full details
    team_info = await nfl_stats.get_team_info(team_id)

    if not team_info and not db_team:
        raise HTTPException(status_code=404, detail="Team not found")

    if db_team and team_info:
        team_info["db_id"] = db_team.id
        team_info["wins"] = db_team.wins
        team_info["losses"] = db_team.losses
        team_info["ties"] = db_team.ties

    return team_info or {
        "id": db_team.espn_id,
        "name": db_team.name,
        "abbreviation": db_team.abbreviation,
        "location": db_team.location,
        "wins": db_team.wins,
        "losses": db_team.losses,
        "ties": db_team.ties
    }


@router.get("/team/{team_id}/schedule")
async def get_team_schedule(team_id: str):
    """
    Get team schedule.

    Args:
        team_id: ESPN team ID
    """
    schedule = await nfl_stats.get_team_schedule(team_id)
    return {
        "team_id": team_id,
        "count": len(schedule),
        "games": schedule
    }


@router.post("/refresh")
async def refresh_nfl_data(db: Session = Depends(get_db)):
    """
    Manually trigger a refresh of NFL data.

    Updates teams, standings, and current week games from ESPN API.
    """
    try:
        result = await nfl_stats.refresh_nfl_data(db)
        return {
            "status": "success",
            "message": "NFL data refreshed successfully",
            "details": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh NFL data: {str(e)}"
        )
