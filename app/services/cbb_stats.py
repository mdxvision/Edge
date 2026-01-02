"""
College Basketball (NCAA) Stats API Integration Service

Uses ESPN's hidden API endpoints - No API key required.
Base URL: https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball
"""

import httpx
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

ESPN_CBB_BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball"
ESPN_CBB_CORE = "https://sports.core.api.espn.com/v2/sports/basketball/leagues/mens-college-basketball"

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
        logger.error(f"ESPN CBB API request failed: {e}")
        return None


def _make_request_sync(url: str, params: Optional[Dict] = None) -> Optional[Dict]:
    """Make a synchronous request to the ESPN API."""
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"ESPN CBB API request failed: {e}")
        return None


async def get_teams(limit: int = 400) -> List[Dict[str, Any]]:
    """
    Get all D1 college basketball teams.

    Returns:
        List of team dictionaries with id, name, abbreviation, conference
    """
    cache_key = f"cbb_teams_{limit}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    url = f"{ESPN_CBB_BASE}/teams"
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


def get_teams_sync(limit: int = 400) -> List[Dict[str, Any]]:
    """Synchronous version of get_teams."""
    cache_key = f"cbb_teams_{limit}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    url = f"{ESPN_CBB_BASE}/teams"
    data = _make_request_sync(url, {"limit": limit})

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


async def get_rankings() -> Dict[str, Any]:
    """
    Get current AP Top 25 and other rankings.

    Returns:
        Dictionary with rankings by type (AP, NET, Coaches Poll)
    """
    cache_key = "cbb_rankings"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    url = f"{ESPN_CBB_BASE}/rankings"
    data = await _make_request(url)

    if not data or "rankings" not in data:
        return {"ap_top_25": [], "coaches_poll": []}

    result = {
        "ap_top_25": [],
        "coaches_poll": [],
        "net_rankings": []
    }

    for ranking in data.get("rankings", []):
        ranking_type = ranking.get("name", "").lower()
        ranks = []

        for rank_entry in ranking.get("ranks", []):
            team_info = rank_entry.get("team", {})
            ranks.append({
                "rank": rank_entry.get("current"),
                "previous_rank": rank_entry.get("previous"),
                "trend": rank_entry.get("trend"),
                "team_id": team_info.get("id"),
                "team_name": team_info.get("name", ""),
                "team_abbreviation": team_info.get("abbreviation", ""),
                "team_logo": team_info.get("logos", [{}])[0].get("href", "") if team_info.get("logos") else "",
                "record": rank_entry.get("recordSummary", ""),
                "points": rank_entry.get("points"),
                "first_place_votes": rank_entry.get("firstPlaceVotes")
            })

        if "ap" in ranking_type:
            result["ap_top_25"] = ranks
        elif "coaches" in ranking_type:
            result["coaches_poll"] = ranks
        elif "net" in ranking_type:
            result["net_rankings"] = ranks

    _set_cached(cache_key, result)
    return result


async def get_team_info(team_id: str) -> Dict[str, Any]:
    """
    Get detailed team information.

    Args:
        team_id: ESPN team ID

    Returns:
        Dictionary with team details
    """
    url = f"{ESPN_CBB_BASE}/teams/{team_id}"
    data = await _make_request(url)

    if not data or "team" not in data:
        return {}

    team = data["team"]
    return {
        "espn_id": team.get("id"),
        "name": team.get("displayName", ""),
        "short_name": team.get("shortDisplayName", ""),
        "abbreviation": team.get("abbreviation", ""),
        "location": team.get("location", ""),
        "color": team.get("color", ""),
        "alternate_color": team.get("alternateColor", ""),
        "logo": team.get("logos", [{}])[0].get("href", "") if team.get("logos") else "",
        "venue": team.get("venue", {}).get("fullName", ""),
        "venue_capacity": team.get("venue", {}).get("capacity"),
        "conference": team.get("groups", {}).get("parent", {}).get("name", ""),
        "record": team.get("record", {}).get("items", [{}])[0].get("summary", "") if team.get("record", {}).get("items") else "",
        "standing": team.get("standingSummary", ""),
        "next_event": team.get("nextEvent", [{}])[0] if team.get("nextEvent") else None
    }


async def get_team_stats(team_id: str) -> Dict[str, Any]:
    """
    Get team statistics.

    Args:
        team_id: ESPN team ID

    Returns:
        Dictionary with team statistics
    """
    url = f"{ESPN_CBB_BASE}/teams/{team_id}/statistics"
    data = await _make_request(url)

    if not data:
        return {}

    stats = {
        "team_id": team_id,
        "offensive": {},
        "defensive": {}
    }

    # Parse categories
    for category in data.get("splits", {}).get("categories", []):
        cat_name = category.get("name", "").lower()

        for stat in category.get("stats", []):
            stat_name = stat.get("name", "")
            stat_value = stat.get("value", 0)
            stat_display = stat.get("displayValue", "")

            if "offensive" in cat_name or stat_name in ["points", "fieldGoals", "threePointers", "freeThrows", "assists", "turnovers"]:
                stats["offensive"][stat_name] = {
                    "value": stat_value,
                    "display": stat_display,
                    "rank": stat.get("rank")
                }
            else:
                stats["defensive"][stat_name] = {
                    "value": stat_value,
                    "display": stat_display,
                    "rank": stat.get("rank")
                }

    return stats


async def get_team_schedule(team_id: str) -> List[Dict[str, Any]]:
    """
    Get team schedule.

    Args:
        team_id: ESPN team ID

    Returns:
        List of scheduled/completed games
    """
    url = f"{ESPN_CBB_BASE}/teams/{team_id}/schedule"
    data = await _make_request(url)

    if not data or "events" not in data:
        return []

    schedule = []
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

        schedule.append({
            "game_id": event.get("id"),
            "date": event.get("date"),
            "name": event.get("name", ""),
            "short_name": event.get("shortName", ""),
            "status": competition.get("status", {}).get("type", {}).get("name", ""),
            "status_detail": competition.get("status", {}).get("type", {}).get("detail", ""),
            "venue": competition.get("venue", {}).get("fullName", ""),
            "broadcast": competition.get("broadcasts", [{}])[0].get("names", [""])[0] if competition.get("broadcasts") else "",
            "home_team": {
                "id": home_team.get("team", {}).get("id") if home_team else None,
                "name": home_team.get("team", {}).get("displayName", "") if home_team else "",
                "abbreviation": home_team.get("team", {}).get("abbreviation", "") if home_team else "",
                "score": home_team.get("score", "") if home_team else "",
                "winner": home_team.get("winner", False) if home_team else False
            } if home_team else None,
            "away_team": {
                "id": away_team.get("team", {}).get("id") if away_team else None,
                "name": away_team.get("team", {}).get("displayName", "") if away_team else "",
                "abbreviation": away_team.get("team", {}).get("abbreviation", "") if away_team else "",
                "score": away_team.get("score", "") if away_team else "",
                "winner": away_team.get("winner", False) if away_team else False
            } if away_team else None,
            "conference_game": competition.get("conferenceCompetition", False),
            "neutral_site": competition.get("neutralSite", False)
        })

    return schedule


async def get_scoreboard(game_date: date = None) -> List[Dict[str, Any]]:
    """
    Get games/scoreboard for a specific date.

    Args:
        game_date: Date to get games for (defaults to today)

    Returns:
        List of games on that date
    """
    if game_date is None:
        game_date = date.today()

    cache_key = f"cbb_scoreboard_{game_date.isoformat()}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    url = f"{ESPN_CBB_BASE}/scoreboard"
    params = {"dates": game_date.strftime("%Y%m%d"), "limit": 100}
    data = await _make_request(url, params)

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

        odds_data = competition.get("odds", [{}])[0] if competition.get("odds") else {}

        games.append({
            "game_id": event.get("id"),
            "date": event.get("date"),
            "name": event.get("name", ""),
            "short_name": event.get("shortName", ""),
            "status": competition.get("status", {}).get("type", {}).get("name", ""),
            "status_detail": competition.get("status", {}).get("type", {}).get("detail", ""),
            "period": competition.get("status", {}).get("period", 0),
            "clock": competition.get("status", {}).get("displayClock", ""),
            "venue": competition.get("venue", {}).get("fullName", ""),
            "broadcast": competition.get("broadcasts", [{}])[0].get("names", [""])[0] if competition.get("broadcasts") else "",
            "home_team": {
                "id": home_team.get("team", {}).get("id") if home_team else None,
                "name": home_team.get("team", {}).get("displayName", "") if home_team else "",
                "abbreviation": home_team.get("team", {}).get("abbreviation", "") if home_team else "",
                "logo": home_team.get("team", {}).get("logo", "") if home_team else "",
                "score": int(home_team.get("score", 0)) if home_team and home_team.get("score") else 0,
                "rank": home_team.get("curatedRank", {}).get("current") if home_team else None,
                "record": home_team.get("records", [{}])[0].get("summary", "") if home_team and home_team.get("records") else ""
            } if home_team else None,
            "away_team": {
                "id": away_team.get("team", {}).get("id") if away_team else None,
                "name": away_team.get("team", {}).get("displayName", "") if away_team else "",
                "abbreviation": away_team.get("team", {}).get("abbreviation", "") if away_team else "",
                "logo": away_team.get("team", {}).get("logo", "") if away_team else "",
                "score": int(away_team.get("score", 0)) if away_team and away_team.get("score") else 0,
                "rank": away_team.get("curatedRank", {}).get("current") if away_team else None,
                "record": away_team.get("records", [{}])[0].get("summary", "") if away_team and away_team.get("records") else ""
            } if away_team else None,
            "odds": {
                "spread": odds_data.get("spread"),
                "over_under": odds_data.get("overUnder"),
                "details": odds_data.get("details", "")
            } if odds_data else None,
            "conference_game": competition.get("conferenceCompetition", False),
            "neutral_site": competition.get("neutralSite", False)
        })

    _set_cached(cache_key, games)
    return games


async def get_game(game_id: str) -> Dict[str, Any]:
    """
    Get detailed game information.

    Args:
        game_id: ESPN game ID

    Returns:
        Dictionary with game details
    """
    url = f"{ESPN_CBB_BASE}/summary"
    data = await _make_request(url, {"event": game_id})

    if not data:
        return {}

    header = data.get("header", {})
    competition = header.get("competitions", [{}])[0]
    boxscore = data.get("boxscore", {})

    competitors = competition.get("competitors", [])
    home_team = None
    away_team = None
    for comp in competitors:
        if comp.get("homeAway") == "home":
            home_team = comp
        else:
            away_team = comp

    return {
        "game_id": game_id,
        "date": header.get("gameDate"),
        "venue": competition.get("venue", {}).get("fullName", ""),
        "attendance": boxscore.get("attendance"),
        "status": competition.get("status", {}).get("type", {}).get("name", ""),
        "home_team": {
            "id": home_team.get("team", {}).get("id") if home_team else None,
            "name": home_team.get("team", {}).get("displayName", "") if home_team else "",
            "score": home_team.get("score", "") if home_team else "",
            "winner": home_team.get("winner", False) if home_team else False,
            "line_scores": home_team.get("linescores", []) if home_team else []
        } if home_team else None,
        "away_team": {
            "id": away_team.get("team", {}).get("id") if away_team else None,
            "name": away_team.get("team", {}).get("displayName", "") if away_team else "",
            "score": away_team.get("score", "") if away_team else "",
            "winner": away_team.get("winner", False) if away_team else False,
            "line_scores": away_team.get("linescores", []) if away_team else []
        } if away_team else None,
        "leaders": data.get("leaders", []),
        "plays": len(data.get("plays", [])),
        "headlines": data.get("news", {}).get("header", "")
    }


async def get_conferences() -> List[Dict[str, Any]]:
    """
    Get all conferences.

    Returns:
        List of conference dictionaries
    """
    cache_key = "cbb_conferences"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    url = f"{ESPN_CBB_BASE}/groups"
    data = await _make_request(url)

    if not data or "groups" not in data:
        return []

    conferences = []
    for group in data.get("groups", []):
        conferences.append({
            "id": group.get("id"),
            "name": group.get("name", ""),
            "short_name": group.get("shortName", ""),
            "abbreviation": group.get("abbreviation", ""),
            "logo": group.get("logos", [{}])[0].get("href", "") if group.get("logos") else ""
        })

    _set_cached(cache_key, conferences)
    return conferences


async def get_conference_standings(conference_id: str) -> List[Dict[str, Any]]:
    """
    Get standings for a conference.

    Args:
        conference_id: ESPN conference ID

    Returns:
        List of teams in standings order
    """
    url = f"{ESPN_CBB_BASE}/standings"
    data = await _make_request(url, {"group": conference_id})

    if not data or "standings" not in data:
        return []

    standings = []
    for entry in data.get("standings", {}).get("entries", []):
        team = entry.get("team", {})
        stats = {}
        for stat in entry.get("stats", []):
            stats[stat.get("name", "")] = stat.get("displayValue", stat.get("value", ""))

        standings.append({
            "team_id": team.get("id"),
            "team_name": team.get("displayName", ""),
            "team_abbreviation": team.get("abbreviation", ""),
            "team_logo": team.get("logos", [{}])[0].get("href", "") if team.get("logos") else "",
            "conference_wins": stats.get("conferenceWins", stats.get("wins", "0")),
            "conference_losses": stats.get("conferenceLosses", stats.get("losses", "0")),
            "overall_wins": stats.get("wins", "0"),
            "overall_losses": stats.get("losses", "0"),
            "win_percentage": stats.get("winPercent", stats.get("gamesBehind", "0")),
            "games_behind": stats.get("gamesBehind", "-"),
            "streak": stats.get("streak", ""),
            "home_record": stats.get("homeRecord", ""),
            "away_record": stats.get("awayRecord", "")
        })

    return standings


# Database storage functions
def store_cbb_teams(db, teams: List[Dict[str, Any]]):
    """Store CBB teams in the database."""
    from app.db import CBBTeam

    for team_data in teams:
        existing = db.query(CBBTeam).filter(
            CBBTeam.espn_id == team_data["espn_id"]
        ).first()

        if existing:
            existing.name = team_data["name"]
            existing.abbreviation = team_data["abbreviation"]
            existing.location = team_data["location"]
            existing.logo_url = team_data.get("logo", "")
        else:
            team = CBBTeam(
                espn_id=team_data["espn_id"],
                name=team_data["name"],
                short_name=team_data["short_name"],
                abbreviation=team_data["abbreviation"],
                location=team_data["location"],
                conference_id=team_data.get("conference"),
                logo_url=team_data.get("logo", ""),
                color=team_data.get("color", "")
            )
            db.add(team)

    db.commit()


def store_cbb_game(db, game_data: Dict[str, Any]):
    """Store a CBB game in the database."""
    from app.db import CBBGame, CBBTeam
    from datetime import datetime

    if not game_data.get("home_team") or not game_data.get("away_team"):
        return None

    # Find teams
    home_team = db.query(CBBTeam).filter(
        CBBTeam.espn_id == str(game_data["home_team"]["id"])
    ).first()

    away_team = db.query(CBBTeam).filter(
        CBBTeam.espn_id == str(game_data["away_team"]["id"])
    ).first()

    # Check if game already exists
    existing = db.query(CBBGame).filter(
        CBBGame.espn_id == game_data["game_id"]
    ).first()

    if existing:
        # Update scores if game is in progress or complete
        if game_data.get("home_team", {}).get("score"):
            existing.home_score = game_data["home_team"]["score"]
        if game_data.get("away_team", {}).get("score"):
            existing.away_score = game_data["away_team"]["score"]
        existing.status = game_data.get("status", "")
        db.commit()
        return existing

    game_time = datetime.fromisoformat(game_data["date"].replace("Z", "+00:00")) if game_data.get("date") else datetime.now()

    game = CBBGame(
        espn_id=game_data["game_id"],
        home_team_id=home_team.id if home_team else None,
        away_team_id=away_team.id if away_team else None,
        game_date=game_time,
        venue=game_data.get("venue", ""),
        status=game_data.get("status", "scheduled"),
        home_score=game_data.get("home_team", {}).get("score"),
        away_score=game_data.get("away_team", {}).get("score"),
        spread=game_data.get("odds", {}).get("spread") if game_data.get("odds") else None,
        over_under=game_data.get("odds", {}).get("over_under") if game_data.get("odds") else None,
        is_conference_game=game_data.get("conference_game", False),
        is_neutral_site=game_data.get("neutral_site", False),
        broadcast=game_data.get("broadcast", ""),
        home_team_name=game_data.get("home_team", {}).get("name", ""),
        away_team_name=game_data.get("away_team", {}).get("name", ""),
        home_team_rank=game_data.get("home_team", {}).get("rank"),
        away_team_rank=game_data.get("away_team", {}).get("rank")
    )
    db.add(game)
    db.commit()
    return game


async def refresh_cbb_data(db):
    """
    Refresh all CBB data - teams, rankings, and games.
    Called by the scheduler.
    """
    logger.info("Starting CBB data refresh...")

    # Refresh teams
    teams = await get_teams()
    if teams:
        store_cbb_teams(db, teams)
        logger.info(f"Stored {len(teams)} CBB teams")

    # Refresh today's games
    games = await get_scoreboard()
    games_stored = 0
    for game_data in games:
        if store_cbb_game(db, game_data):
            games_stored += 1
    logger.info(f"Stored {games_stored} CBB games for today")

    # Get rankings
    rankings = await get_rankings()
    logger.info(f"Retrieved rankings: AP Top 25 has {len(rankings.get('ap_top_25', []))} teams")

    return {
        "teams": len(teams),
        "games": games_stored,
        "rankings": len(rankings.get("ap_top_25", []))
    }
