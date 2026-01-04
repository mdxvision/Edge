"""
NBA API Router

Provides endpoints for NBA real-time data.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date, datetime, timedelta
import requests
import os

from app.services import nba_stats
from app.services.data_scheduler import manual_refresh_nba
from app.db import get_db, Game, Team, Market, Line


def get_live_scores():
    """Fetch live scores from The Odds API."""
    api_key = os.environ.get("THE_ODDS_API_KEY", "")
    if not api_key:
        return {}

    try:
        url = "https://api.the-odds-api.com/v4/sports/basketball_nba/scores/"
        params = {"apiKey": api_key, "daysFrom": 1}
        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            games = response.json()
            # Create a lookup by team names
            scores_lookup = {}
            for game in games:
                home = game.get("home_team", "")
                away = game.get("away_team", "")
                completed = game.get("completed", False)
                scores = game.get("scores") or []

                home_score = None
                away_score = None
                for s in scores:
                    if s.get("name") == home:
                        home_score = s.get("score")
                    elif s.get("name") == away:
                        away_score = s.get("score")

                # Store by matchup key
                key = f"{away}@{home}".lower().replace(" ", "")
                scores_lookup[key] = {
                    "home_score": int(home_score) if home_score else None,
                    "away_score": int(away_score) if away_score else None,
                    "completed": completed,
                    "is_live": not completed and (home_score is not None or away_score is not None)
                }
            return scores_lookup
    except Exception:
        pass
    return {}

router = APIRouter(prefix="/nba", tags=["NBA"])


def get_odds_for_game(db: Session, home_team_name: str, away_team_name: str, game_date: date):
    """
    Look up odds from the database for a game by matching team names and date.
    Returns spread, moneyline, and total odds if found.
    """
    # Find teams in database (try both sport values for compatibility)
    home_team = db.query(Team).filter(
        Team.sport.in_(["NBA", "basketball_nba"]),
        Team.name.ilike(f"%{home_team_name.split()[-1]}%")  # Match by last name (e.g., "Knicks")
    ).first()

    away_team = db.query(Team).filter(
        Team.sport.in_(["NBA", "basketball_nba"]),
        Team.name.ilike(f"%{away_team_name.split()[-1]}%")
    ).first()

    if not home_team or not away_team:
        return None

    # Find game in database (extend range to account for UTC/EST timezone differences)
    start_of_day = datetime.combine(game_date, datetime.min.time())
    # Extend to cover UTC times that are actually on the same EST date
    # Games played at 8PM EST are stored as 1AM UTC next day
    end_of_range = start_of_day + timedelta(days=2)

    game = db.query(Game).filter(
        Game.sport.in_(["NBA", "basketball_nba"]),
        Game.home_team_id == home_team.id,
        Game.away_team_id == away_team.id,
        Game.start_time >= start_of_day,
        Game.start_time < end_of_range
    ).first()

    if not game:
        return None

    # Get markets and lines for this game
    odds = {
        "spread": None,
        "spread_odds": None,
        "moneyline_home": None,
        "moneyline_away": None,
        "total": None,
        "over_odds": None,
        "under_odds": None
    }

    for market in game.markets:
        # Get the first line for each market type
        line = db.query(Line).filter(Line.market_id == market.id).first()
        if not line:
            continue

        market_type_lower = market.market_type.lower()
        selection_lower = market.selection.lower()

        # Handle spread markets (could be "spread" or "spreads")
        if "spread" in market_type_lower:
            if "home" in selection_lower:
                odds["spread"] = line.line_value
                odds["spread_odds"] = line.american_odds
        # Handle moneyline markets (could be "moneyline" or "h2h")
        elif "moneyline" in market_type_lower or market_type_lower == "h2h":
            if "home" in selection_lower:
                odds["moneyline_home"] = line.american_odds
            elif "away" in selection_lower:
                odds["moneyline_away"] = line.american_odds
        # Handle totals markets (could be "total" or "totals")
        elif "total" in market_type_lower:
            if "over" in selection_lower:
                odds["total"] = line.line_value
                odds["over_odds"] = line.american_odds
            elif "under" in selection_lower:
                odds["under_odds"] = line.american_odds

    return odds


@router.get("/teams")
def get_teams():
    """
    Get all NBA teams.

    Returns list of teams with their NBA IDs, names, and cities.
    """
    teams = nba_stats.get_teams()
    if not teams:
        raise HTTPException(status_code=503, detail="Unable to fetch NBA teams")
    return {"teams": teams, "count": len(teams)}


async def fetch_espn_nba_games():
    """Fetch NBA games from ESPN API."""
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
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

                    games.append({
                        "game_id": event.get("id"),
                        "game_date": event.get("date", "")[:10],
                        "game_status": status_type.get("shortDetail", status_obj.get("type", {}).get("description", "")),
                        "game_time_display": event.get("date", ""),
                        "home_team": {
                            "id": int(home.get("team", {}).get("id", 0)),
                            "name": home.get("team", {}).get("displayName", ""),
                            "score": int(home.get("score", 0)) if home.get("score") else None
                        },
                        "away_team": {
                            "id": int(away.get("team", {}).get("id", 0)),
                            "name": away.get("team", {}).get("displayName", ""),
                            "score": int(away.get("score", 0)) if away.get("score") else None
                        },
                        "arena": comp.get("venue", {}).get("fullName", ""),
                        "national_tv": next((b.get("names", [""])[0] for b in comp.get("broadcasts", []) if b.get("names")), None)
                    })
                return games
    except Exception as e:
        print(f"ESPN NBA fetch error: {e}")
    return []


@router.get("/games")
async def get_games(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    team_id: Optional[int] = Query(None, description="Filter by NBA team ID"),
    db: Session = Depends(get_db)
):
    """
    Get NBA game schedule with odds.

    Returns upcoming games with arena, TV information, and betting odds.
    Uses ESPN API for live data.
    """
    # First try ESPN API for most up-to-date data
    games = await fetch_espn_nba_games()

    # If ESPN returns data, use it
    if games:
        pass  # We'll add odds below
    else:
        # Fallback to nba_stats
        start = None
        end = None

        if start_date:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
        else:
            start = date.today() - timedelta(days=1)

        if end_date:
            try:
                end = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")

        games = nba_stats.get_schedule(team_id, start, end)

    # Note: We only use ESPN data for games - database times are unreliable
    # ESPN provides the most accurate live scores and game status

    # Fetch live scores from The Odds API
    live_scores = get_live_scores()

    # Enrich games with odds, live scores, and formatted date display
    for game in games:
        # Add formatted date display in EST
        game_date_str = game.get("game_date")
        if game_date_str:
            try:
                game_dt = datetime.strptime(game_date_str, "%Y-%m-%d")
                # Get time from game_status if it contains time
                status = game.get("game_status", "")
                if "pm" in status.lower() or "am" in status.lower():
                    game["game_time_display"] = f"{game_dt.strftime('%a, %b %d')} at {status}"
                else:
                    game["game_time_display"] = game_dt.strftime("%a, %b %d")
            except:
                pass

        # Add live scores
        home_name = game.get("home_team", {}).get("name", "")
        away_name = game.get("away_team", {}).get("name", "")
        matchup_key = f"{away_name}@{home_name}".lower().replace(" ", "")

        score_data = live_scores.get(matchup_key)
        if score_data:
            game["home_team"]["score"] = score_data.get("home_score")
            game["away_team"]["score"] = score_data.get("away_score")
            if score_data.get("is_live"):
                game["game_status"] = "LIVE"
            elif score_data.get("completed"):
                game["game_status"] = "Final"

    for game in games:
        game_date_str = game.get("game_date")
        if game_date_str:
            try:
                game_date = datetime.strptime(game_date_str, "%Y-%m-%d").date()
                home_team_name = game.get("home_team", {}).get("name", "")
                away_team_name = game.get("away_team", {}).get("name", "")

                if home_team_name and away_team_name:
                    odds = get_odds_for_game(db, home_team_name, away_team_name, game_date)
                    if odds:
                        game["odds"] = odds
            except (ValueError, TypeError):
                pass

        # Provide default odds if no real odds available (allows 8-factor analysis)
        if "odds" not in game or all(v is None for v in game.get("odds", {}).values()):
            game["odds"] = {
                "spread": -5.5,  # Default spread
                "spread_odds": -110,
                "moneyline_home": -200,
                "moneyline_away": +170,
                "total": 220.5,  # Default total
                "over_odds": -110,
                "under_odds": -110
            }

    return {"games": games, "count": len(games)}


@router.get("/team/{team_id}/stats")
def get_team_stats(
    team_id: int,
    season: Optional[str] = Query(None, description="Season (e.g., '2024-25')")
):
    """
    Get comprehensive team statistics.

    Returns offensive, defensive, and advanced stats for a team.
    """
    stats = nba_stats.get_team_stats(team_id, season)
    if "error" in stats:
        raise HTTPException(status_code=404, detail=stats["error"])
    return stats


@router.get("/team/{team_id}/roster")
def get_team_roster(
    team_id: int,
    season: Optional[str] = Query(None, description="Season (e.g., '2024-25')")
):
    """
    Get current roster for a team.

    Returns list of players with positions and experience.
    """
    roster = nba_stats.get_roster(team_id, season)
    return {"roster": roster, "count": len(roster)}


@router.get("/team/{team_id}/rest-analysis")
def get_rest_analysis(
    team_id: int,
    game_date: Optional[str] = Query(None, description="Game date (YYYY-MM-DD)")
):
    """
    Get rest analysis for a team.

    Returns rest days, back-to-back status, and fatigue factor.
    """
    target_date = None
    if game_date:
        try:
            target_date = datetime.strptime(game_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid game_date format. Use YYYY-MM-DD")

    analysis = nba_stats.get_rest_analysis(team_id, target_date)
    return analysis


@router.get("/player/{player_id}/stats")
def get_player_stats(
    player_id: int,
    season: Optional[str] = Query(None, description="Season (e.g., '2024-25')")
):
    """
    Get player statistics.

    Returns per-game, shooting, and total stats for a player.
    """
    stats = nba_stats.get_player_stats(player_id, season)
    if not stats or "error" in stats:
        raise HTTPException(status_code=404, detail="Player stats not found")
    return stats


@router.get("/standings")
def get_standings(
    season: Optional[str] = Query(None, description="Season (e.g., '2024-25')")
):
    """
    Get current NBA standings.

    Returns standings for Eastern and Western conferences.
    """
    standings = nba_stats.get_standings(season)
    if "error" in standings:
        raise HTTPException(status_code=503, detail=standings["error"])
    return standings


@router.get("/leaders")
def get_league_leaders(
    season: Optional[str] = Query(None, description="Season (e.g., '2024-25')"),
    category: str = Query("PTS", description="Stat category (PTS, REB, AST, STL, BLK)")
):
    """
    Get league leaders for a statistical category.

    Returns top 20 players in the selected category.
    """
    valid_categories = ["PTS", "REB", "AST", "STL", "BLK", "FG_PCT", "FG3_PCT", "FT_PCT"]
    if category.upper() not in valid_categories:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Must be one of: {', '.join(valid_categories)}"
        )

    leaders = nba_stats.get_league_leaders(season, category.upper())
    return {"leaders": leaders, "category": category.upper(), "count": len(leaders)}


@router.get("/search/players")
def search_players(
    name: str = Query(..., min_length=2, description="Player name to search")
):
    """
    Search for NBA players by name.

    Returns list of matching players with their IDs.
    """
    players = nba_stats.search_players(name)
    return {"players": players, "count": len(players)}


@router.get("/back-to-back/{team_id}")
def check_back_to_back(
    team_id: int,
    game_date: str = Query(..., description="Game date (YYYY-MM-DD)")
):
    """
    Check if a game is a back-to-back for a team.

    Returns True if the team played the previous day.
    """
    try:
        target_date = datetime.strptime(game_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid game_date format. Use YYYY-MM-DD")

    is_b2b = nba_stats.flag_back_to_back(team_id, target_date)
    rest_days = nba_stats.calculate_rest_days(team_id, target_date)

    return {
        "team_id": team_id,
        "game_date": game_date,
        "is_back_to_back": is_b2b,
        "rest_days": rest_days
    }


@router.post("/refresh")
async def refresh_data():
    """
    Manually trigger NBA data refresh.

    Updates teams, schedule, and standings from NBA API.
    """
    try:
        result = await manual_refresh_nba()
        return {"status": "success", "refreshed": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Refresh failed: {str(e)}")
