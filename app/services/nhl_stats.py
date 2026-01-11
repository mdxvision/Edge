"""
NHL Stats API Integration Service

Uses ESPN's hidden API endpoints - No API key required.
Base URL: https://site.api.espn.com/apis/site/v2/sports/hockey/nhl
"""

import httpx
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import logging
from app.db import Game, Team
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

ESPN_NHL_BASE = "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl"

# Cache for reducing API calls
_cache: Dict[str, tuple] = {}
CACHE_TTL = 300  # 5 minutes


def _get_cached(key: str) -> Optional[Any]:
    """Get cached value if not expired."""
    if key in _cache:
        data, timestamp = _cache[key]
        if datetime.now().timestamp() - timestamp < CACHE_TTL:
            return data
    return None


def _set_cached(key: str, data: Any):
    """Set cached value with current timestamp."""
    _cache[key] = (data, datetime.now().timestamp())


async def _make_request(url: str, params: Optional[Dict] = None) -> Optional[Dict]:
    """Make an async request to the ESPN API."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"ESPN NHL API request failed: {e}")
        return None


async def get_teams() -> List[Dict[str, Any]]:
    """
    Get all NHL teams.

    Returns:
        List of team dictionaries with id, name, abbreviation, division
    """
    cache_key = "nhl_teams"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    url = f"{ESPN_NHL_BASE}/teams"
    data = await _make_request(url)

    if not data or "sports" not in data:
        return []

    teams = []
    for sport in data.get("sports", []):
        for league in sport.get("leagues", []):
            for team in league.get("teams", []):
                team_info = team.get("team", {})
                teams.append({
                    "espn_id": team_info.get("id"),
                    "name": team_info.get("displayName", ""),
                    "short_name": team_info.get("shortDisplayName", ""),
                    "abbreviation": team_info.get("abbreviation", ""),
                    "location": team_info.get("location", ""),
                    "color": team_info.get("color", ""),
                    "logo": team_info.get("logos", [{}])[0].get("href", "") if team_info.get("logos") else "",
                })

    _set_cached(cache_key, teams)
    return teams


async def get_scoreboard(target_date: date = None) -> List[Dict[str, Any]]:
    """
    Get NHL games for a specific date.

    Args:
        target_date: Date to get games for (defaults to today)

    Returns:
        List of game dictionaries
    """
    if target_date is None:
        target_date = date.today()

    cache_key = f"nhl_scoreboard_{target_date.isoformat()}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    url = f"{ESPN_NHL_BASE}/scoreboard"
    data = await _make_request(url, {"dates": target_date.strftime("%Y%m%d")})

    if not data or "events" not in data:
        return []

    games = []
    for event in data.get("events", []):
        competition = event.get("competitions", [{}])[0]
        competitors = competition.get("competitors", [])

        home_team = None
        away_team = None
        for comp in competitors:
            if comp.get("homeAway") == "home":
                home_team = comp
            else:
                away_team = comp

        if not home_team or not away_team:
            continue

        # Get odds if available
        odds = None
        odds_data = competition.get("odds", [])
        if odds_data:
            odds_info = odds_data[0]
            odds = {
                "spread": odds_info.get("spread"),
                "over_under": odds_info.get("overUnder"),
                "moneyline_home": odds_info.get("homeTeamOdds", {}).get("moneyLine"),
                "moneyline_away": odds_info.get("awayTeamOdds", {}).get("moneyLine"),
            }

        games.append({
            "game_id": event.get("id"),
            "date": event.get("date"),
            "name": event.get("name", ""),
            "short_name": event.get("shortName", ""),
            "status": event.get("status", {}).get("type", {}).get("name", ""),
            "status_detail": event.get("status", {}).get("type", {}).get("detail", ""),
            "period": event.get("status", {}).get("period", 0),
            "clock": event.get("status", {}).get("displayClock", "0:00"),
            "venue": competition.get("venue", {}).get("fullName", ""),
            "broadcast": competition.get("broadcasts", [{}])[0].get("names", [""])[0] if competition.get("broadcasts") else "",
            "home_team": {
                "id": home_team.get("team", {}).get("id"),
                "name": home_team.get("team", {}).get("displayName", ""),
                "abbreviation": home_team.get("team", {}).get("abbreviation", ""),
                "logo": home_team.get("team", {}).get("logo", ""),
                "score": int(home_team.get("score", 0)) if home_team.get("score") else 0,
                "record": home_team.get("records", [{}])[0].get("summary", "") if home_team.get("records") else "",
            },
            "away_team": {
                "id": away_team.get("team", {}).get("id"),
                "name": away_team.get("team", {}).get("displayName", ""),
                "abbreviation": away_team.get("team", {}).get("abbreviation", ""),
                "logo": away_team.get("team", {}).get("logo", ""),
                "score": int(away_team.get("score", 0)) if away_team.get("score") else 0,
                "record": away_team.get("records", [{}])[0].get("summary", "") if away_team.get("records") else "",
            },
            "odds": odds,
        })

    _set_cached(cache_key, games)
    return games


async def get_standings() -> Dict[str, Any]:
    """
    Get current NHL standings.

    Returns:
        Dictionary with standings by conference and division
    """
    cache_key = "nhl_standings"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    url = f"{ESPN_NHL_BASE}/standings"
    data = await _make_request(url)

    if not data or "children" not in data:
        return {"error": "No standings data available"}

    standings = []
    for conf in data.get("children", []):
        conf_data = {
            "name": conf.get("name", ""),
            "abbreviation": conf.get("abbreviation", ""),
            "divisions": []
        }
        for div in conf.get("children", []):
            div_standings = []
            for entry in div.get("standings", {}).get("entries", []):
                team = entry.get("team", {})
                stats = {s.get("name"): s.get("value") for s in entry.get("stats", [])}
                div_standings.append({
                    "team": team.get("displayName", ""),
                    "team_id": team.get("id"),
                    "wins": stats.get("wins", 0),
                    "losses": stats.get("losses", 0),
                    "ot_losses": stats.get("otLosses", 0),
                    "points": stats.get("points", 0),
                    "games_played": stats.get("gamesPlayed", 0),
                })
            conf_data["divisions"].append({
                "name": div.get("name", ""),
                "standings": div_standings
            })
        standings.append(conf_data)

    result = {"conferences": standings}
    _set_cached(cache_key, result)
    return result


async def get_team_info(team_id: str) -> Optional[Dict[str, Any]]:
    """Get detailed team information."""
    url = f"{ESPN_NHL_BASE}/teams/{team_id}"
    data = await _make_request(url)

    if not data or "team" not in data:
        return None

    team = data.get("team", {})
    return {
        "id": team.get("id"),
        "name": team.get("displayName", ""),
        "abbreviation": team.get("abbreviation", ""),
        "location": team.get("location", ""),
        "color": team.get("color", ""),
        "logo": team.get("logos", [{}])[0].get("href", "") if team.get("logos") else "",
        "venue": team.get("franchise", {}).get("venue", {}).get("fullName", ""),
        "record": team.get("record", {}).get("items", [{}])[0].get("summary", "") if team.get("record") else "",
    }


async def get_team_schedule(team_id: str) -> List[Dict[str, Any]]:
    """Get team schedule."""
    url = f"{ESPN_NHL_BASE}/teams/{team_id}/schedule"
    data = await _make_request(url)

    if not data or "events" not in data:
        return []

    schedule = []
    for event in data.get("events", []):
        competition = event.get("competitions", [{}])[0]
        competitors = competition.get("competitors", [])

        opponent = None
        is_home = True
        for comp in competitors:
            if comp.get("team", {}).get("id") != team_id:
                opponent = comp
                is_home = comp.get("homeAway") == "away"

        if opponent:
            schedule.append({
                "game_id": event.get("id"),
                "date": event.get("date"),
                "opponent": opponent.get("team", {}).get("displayName", ""),
                "opponent_id": opponent.get("team", {}).get("id"),
                "is_home": is_home,
                "result": event.get("competitions", [{}])[0].get("status", {}).get("type", {}).get("completed", False),
            })

    return schedule


async def refresh_nhl_data(db: Session) -> Dict[str, Any]:
    """Refresh NHL data in database."""
    results = {
        "teams": 0,
        "games": 0,
    }

    # Refresh teams
    teams = await get_teams()
    for team_data in teams:
        store_nhl_team(db, team_data)
        results["teams"] += 1

    # Refresh today's games
    games = await get_scoreboard()
    for game_data in games:
        store_nhl_game(db, game_data)
        results["games"] += 1

    db.commit()
    return results

def store_nhl_team(db: Session, team_data: Dict[str, Any]):
    """Store or update NHL team."""
    team = db.query(Team).filter(
        Team.sport == "NHL",
        Team.name == team_data["name"]
    ).first()

    if not team:
        team = Team(
            sport="NHL",
            name=team_data["name"],
            short_name=team_data.get("short_name", "") or team_data["name"][:10],
            logo_url=team_data.get("logo")
        )
        db.add(team)
    else:
        # Update existing fields if needed
        if team_data.get("logo"):
            team.logo_url = team_data.get("logo")
    
    db.flush()
    return team

def store_nhl_game(db: Session, game_data: Dict[str, Any]):
    """Store or update NHL game."""
    home_name = game_data["home_team"]["name"]
    away_name = game_data["away_team"]["name"]
    
    home_team = db.query(Team).filter(Team.sport == "NHL", Team.name == home_name).first()
    away_team = db.query(Team).filter(Team.sport == "NHL", Team.name == away_name).first()

    if not home_team or not away_team:
        logger.warning(f"Could not find teams for NHL game: {home_name} vs {away_name}")
        return None

    # Parse proper datetime
    # game_data["date"] is likely ISO string, ensure format
    try:
        start_time = datetime.fromisoformat(game_data["date"].replace("Z", "+00:00"))
    except:
        start_time = datetime.now() # Fallback

    external_id = str(game_data.get("game_id", ""))
    
    # Try to find existing game
    game = db.query(Game).filter(
        Game.sport == "NHL",
        Game.home_team_id == home_team.id,
        Game.away_team_id == away_team.id,
        Game.start_time == start_time
    ).first()
    
    # Also try external_id match if available
    if not game and external_id:
        game = db.query(Game).filter(
            Game.sport == "NHL",
            Game.external_id == external_id
        ).first()

    current_score = f"{game_data['home_team']['score']}-{game_data['away_team']['score']}"
    status = game_data.get("status", "scheduled")
    
    # Remap status names to standardized ones if needed, or stick to raw
    # raw: STATUS_SCHEDULED, STATUS_IN_PROGRESS, STATUS_FINAL

    if not game:
        game = Game(
            sport="NHL",
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            start_time=start_time,
            venue=game_data.get("venue", ""),
            league="NHL",
            external_id=external_id,
            status=status,
            current_score=current_score
        )
        db.add(game)
    else:
        game.status = status
        game.current_score = current_score
        if external_id and not game.external_id:
            game.external_id = external_id
    
    db.flush()
    return game


async def calculate_rest_days(team_id: str, game_date: date) -> int:
    """
    Calculate days of rest for a team before a game.
    
    Args:
        team_id: ESPN Team ID
        game_date: Date of the game to check
        
    Returns:
        Number of rest days (-1 if unknown)
    """
    try:
        schedule = await get_team_schedule(team_id)
        if not schedule:
            return -1
            
        # Filter for completed games before target date
        previous_games = []
        for game in schedule:
            # Parse game date (ISO string to date object)
            try:
                g_date_str = game["date"].split("T")[0]
                g_date = datetime.strptime(g_date_str, "%Y-%m-%d").date()
                
                if g_date < game_date and game["result"]: # result=True means completed
                    previous_games.append(g_date)
            except (ValueError, KeyError):
                continue
                
        if not previous_games:
            return -1
            
        # Get Max date
        last_game_date = max(previous_games)
        rest_days = (game_date - last_game_date).days - 1
        return max(rest_days, 0)
        
    except Exception as e:
        logger.error(f"Error calculating NHL rest days: {e}")
        return -1
