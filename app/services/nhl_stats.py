"""
NHL Stats API Integration Service

Uses ESPN's hidden API endpoints - No API key required.
Base URL: https://site.api.espn.com/apis/site/v2/sports/hockey/nhl
"""

import httpx
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import logging

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


async def refresh_nhl_data(db) -> Dict[str, Any]:
    """Refresh NHL data in database."""
    results = {
        "teams": 0,
        "games": 0,
    }

    # Refresh teams
    teams = await get_teams()
    results["teams"] = len(teams)

    # Refresh today's games
    games = await get_scoreboard()
    results["games"] = len(games)

    return results
