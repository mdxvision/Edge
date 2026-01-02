"""
College Football (NCAA) Stats API Integration Service

Uses ESPN's hidden API endpoints - No API key required.
Base URL: https://site.api.espn.com/apis/site/v2/sports/football/college-football
"""

import httpx
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

ESPN_CFB_BASE = "https://site.api.espn.com/apis/site/v2/sports/football/college-football"
ESPN_CFB_CORE = "https://sports.core.api.espn.com/v2/sports/football/leagues/college-football"

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
        logger.error(f"ESPN CFB API request failed: {e}")
        return None


async def get_teams(limit: int = 150) -> List[Dict[str, Any]]:
    """
    Get FBS college football teams.

    Returns:
        List of team dictionaries with id, name, abbreviation, conference
    """
    cache_key = f"cfb_teams_{limit}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    url = f"{ESPN_CFB_BASE}/teams"
    data = await _make_request(url, {"limit": limit})

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
                    "conference": team_info.get("conferenceId", ""),
                })

    _set_cached(cache_key, teams)
    return teams


async def get_scoreboard(target_date: date = None) -> List[Dict[str, Any]]:
    """
    Get college football games for a specific date.

    Args:
        target_date: Date to get games for (defaults to today)

    Returns:
        List of game dictionaries
    """
    if target_date is None:
        target_date = date.today()

    cache_key = f"cfb_scoreboard_{target_date.isoformat()}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    url = f"{ESPN_CFB_BASE}/scoreboard"
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
                "spread_odds": odds_info.get("spreadOdds"),
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
                "rank": home_team.get("curatedRank", {}).get("current", 99),
                "record": home_team.get("records", [{}])[0].get("summary", "") if home_team.get("records") else "",
            },
            "away_team": {
                "id": away_team.get("team", {}).get("id"),
                "name": away_team.get("team", {}).get("displayName", ""),
                "abbreviation": away_team.get("team", {}).get("abbreviation", ""),
                "logo": away_team.get("team", {}).get("logo", ""),
                "score": int(away_team.get("score", 0)) if away_team.get("score") else 0,
                "rank": away_team.get("curatedRank", {}).get("current", 99),
                "record": away_team.get("records", [{}])[0].get("summary", "") if away_team.get("records") else "",
            },
            "odds": odds,
            "conference_game": competition.get("conferenceCompetition", False),
            "neutral_site": competition.get("neutralSite", False),
        })

    _set_cached(cache_key, games)
    return games


async def get_rankings() -> Dict[str, Any]:
    """
    Get current college football rankings.

    Returns:
        Dictionary with CFP, AP, and Coaches Poll rankings
    """
    cache_key = "cfb_rankings"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    url = f"{ESPN_CFB_BASE}/rankings"
    data = await _make_request(url)

    if not data or "rankings" not in data:
        return {"rankings": []}

    rankings = []
    for ranking in data.get("rankings", []):
        rankings.append({
            "name": ranking.get("name", ""),
            "short_name": ranking.get("shortName", ""),
            "type": ranking.get("type", ""),
            "ranks": [
                {
                    "rank": team.get("current"),
                    "team": team.get("team", {}).get("displayName", ""),
                    "team_id": team.get("team", {}).get("id"),
                    "record": team.get("recordSummary", ""),
                    "previous": team.get("previous"),
                }
                for team in ranking.get("ranks", [])[:25]
            ]
        })

    result = {"rankings": rankings}
    _set_cached(cache_key, result)
    return result


async def get_team_info(team_id: str) -> Optional[Dict[str, Any]]:
    """Get detailed team information."""
    url = f"{ESPN_CFB_BASE}/teams/{team_id}"
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
    url = f"{ESPN_CFB_BASE}/teams/{team_id}/schedule"
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


async def get_conferences() -> List[Dict[str, Any]]:
    """Get all FBS conferences."""
    url = f"{ESPN_CFB_BASE}/groups"
    data = await _make_request(url)

    if not data or "groups" not in data:
        return []

    return [
        {
            "id": conf.get("id"),
            "name": conf.get("name", ""),
            "short_name": conf.get("abbreviation", ""),
        }
        for conf in data.get("groups", [])
    ]


async def refresh_cfb_data(db) -> Dict[str, Any]:
    """Refresh CFB data in database."""
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
