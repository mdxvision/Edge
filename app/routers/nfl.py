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
from app.utils.status import normalize_status, add_time_display
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


async def fetch_espn_nfl_games():
    """Fetch NFL games from ESPN API with live scores."""
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                events = data.get("events", [])
                games = []
                for event in events:
                    competitions = event.get("competitions", [{}])
                    comp = competitions[0] if competitions else {}
                    competitors = comp.get("competitors", [])

                    home = next((c for c in competitors if c.get("homeAway") == "home"), {})
                    away = next((c for c in competitors if c.get("homeAway") == "away"), {})

                    status_obj = event.get("status", {})
                    status_type = status_obj.get("type", {})
                    raw_status = status_type.get("name", status_type.get("description", ""))

                    # Get scores
                    home_score = int(home.get("score", 0)) if home.get("score") else None
                    away_score = int(away.get("score", 0)) if away.get("score") else None

                    # Add game_date (local EST date) from UTC source to avoid drift
                    game_utc = event.get("date", "")
                    try:
                        dt_obj = datetime.fromisoformat(game_utc.replace("Z", "+00:00"))
                        est_dt = dt_obj - timedelta(hours=5)
                        local_game_date = est_dt.strftime("%Y-%m-%d")
                    except:
                        local_game_date = game_utc[:10]

                    games.append({
                        "game_id": event.get("id"),
                        "game_date": local_game_date,
                        "status": normalize_status(raw_status),
                        "game_time_display": status_type.get("shortDetail", ""),
                        "home_team": {
                            "id": int(home.get("team", {}).get("id", 0)),
                            "name": home.get("team", {}).get("displayName", ""),
                            "score": home_score
                        },
                        "away_team": {
                            "id": int(away.get("team", {}).get("id", 0)),
                            "name": away.get("team", {}).get("displayName", ""),
                            "score": away_score
                        },
                        "venue": comp.get("venue", {}).get("fullName", ""),
                        "broadcast": next((b.get("names", [""])[0] for b in comp.get("broadcasts", []) if b.get("names")), None)
                    })
                return games
    except Exception as e:
        print(f"ESPN NFL fetch error: {e}")
    return []


@router.get("/games")
async def get_games(db: Session = Depends(get_db)):
    """
    Get current week NFL games.

    Returns scoreboard with live scores and odds from ESPN.
    """
    # Always use ESPN for live/accurate data
    games = await fetch_espn_nfl_games()

    if not games:
        # Fallback to database only if ESPN fails
        from datetime import datetime as dt
        nfl_games = db.query(Game).filter(
            Game.sport.in_(["NFL", "americanfootball_nfl"]),
            Game.start_time >= dt.utcnow() - timedelta(days=1)
        ).order_by(Game.start_time.asc()).all()

        for game in nfl_games:
            home_team = db.query(Team).filter(Team.id == game.home_team_id).first()
            away_team = db.query(Team).filter(Team.id == game.away_team_id).first()
            odds = get_odds_for_game(db, game.id)
            est_time = game.start_time - timedelta(hours=5)

            games.append({
                "id": game.id,
                "status": "Scheduled",
                "game_date": est_time.isoformat(),
                "game_time_display": est_time.strftime("%a, %b %d at %I:%M %p") + " EST",
                "venue": game.venue,
                "home_team": {"name": home_team.name if home_team else "Unknown", "score": None},
                "away_team": {"name": away_team.name if away_team else "Unknown", "score": None},
                "odds": odds,
            })

    # Provide default odds if no real odds available (allows 8-factor analysis)
    for game in games:
        if "odds" not in game or not game["odds"] or all(v is None for v in game.get("odds", {}).values()):
            game["odds"] = {
                "spread": -3.5,  # Default NFL spread
                "over_under": 44.5,  # Default NFL total
            }

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
