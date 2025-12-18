"""
Soccer Stats API Integration Service

Uses Football-Data.org API
Base URL: https://api.football-data.org/v4
Free tier: 10 requests/minute, covers major leagues
"""

import httpx
import os
import asyncio
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

FOOTBALL_DATA_BASE = "https://api.football-data.org/v4"
API_KEY = os.getenv("FOOTBALL_DATA_API_KEY", "")

# Free tier supported competitions
SUPPORTED_COMPETITIONS = {
    "PL": "Premier League",
    "PD": "La Liga",
    "BL1": "Bundesliga",
    "SA": "Serie A",
    "FL1": "Ligue 1",
    "ELC": "Championship",
    "CL": "Champions League"
}

# Cache for reducing API calls (important for rate limiting)
_cache: Dict[str, tuple] = {}
CACHE_TTL = 600  # 10 minutes (longer due to rate limits)

# Rate limiting
_last_request_time = 0
MIN_REQUEST_INTERVAL = 6  # 10 requests per minute = 1 request per 6 seconds


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


async def _rate_limit():
    """Ensure we don't exceed rate limits."""
    global _last_request_time
    current_time = datetime.now().timestamp()
    time_since_last = current_time - _last_request_time

    if time_since_last < MIN_REQUEST_INTERVAL:
        await asyncio.sleep(MIN_REQUEST_INTERVAL - time_since_last)

    _last_request_time = datetime.now().timestamp()


async def _make_request(endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
    """Make an async request to the Football-Data.org API."""
    if not API_KEY:
        logger.warning("FOOTBALL_DATA_API_KEY not set - Soccer API calls will fail")
        return None

    await _rate_limit()

    url = f"{FOOTBALL_DATA_BASE}/{endpoint}"
    headers = {"X-Auth-Token": API_KEY}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            logger.warning("Rate limit exceeded for Football-Data.org API")
        else:
            logger.error(f"Football-Data.org API request failed: {e}")
        return None
    except httpx.HTTPError as e:
        logger.error(f"Football-Data.org API request failed: {e}")
        return None


def _make_request_sync(endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
    """Make a synchronous request to the Football-Data.org API."""
    if not API_KEY:
        logger.warning("FOOTBALL_DATA_API_KEY not set - Soccer API calls will fail")
        return None

    url = f"{FOOTBALL_DATA_BASE}/{endpoint}"
    headers = {"X-Auth-Token": API_KEY}

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            logger.warning("Rate limit exceeded for Football-Data.org API")
        else:
            logger.error(f"Football-Data.org API request failed: {e}")
        return None
    except httpx.HTTPError as e:
        logger.error(f"Football-Data.org API request failed: {e}")
        return None


async def get_competitions() -> List[Dict[str, Any]]:
    """
    Get list of available competitions (leagues).

    Returns:
        List of competition dictionaries
    """
    cache_key = "soccer_competitions"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    data = await _make_request("competitions")

    if not data or "competitions" not in data:
        # Return supported competitions as fallback
        return [
            {"code": code, "name": name, "available": False}
            for code, name in SUPPORTED_COMPETITIONS.items()
        ]

    competitions = []
    for comp in data.get("competitions", []):
        comp_code = comp.get("code", "")
        competitions.append({
            "id": comp.get("id"),
            "code": comp_code,
            "name": comp.get("name", ""),
            "country": comp.get("area", {}).get("name", ""),
            "country_flag": comp.get("area", {}).get("flag", ""),
            "emblem": comp.get("emblem", ""),
            "type": comp.get("type", ""),
            "current_season": comp.get("currentSeason", {}),
            "available": comp_code in SUPPORTED_COMPETITIONS
        })

    # Filter to only supported competitions for free tier
    competitions = [c for c in competitions if c["available"]]

    _set_cached(cache_key, competitions)
    return competitions


async def get_standings(competition_code: str) -> Dict[str, Any]:
    """
    Get league table/standings for a competition.

    Args:
        competition_code: Competition code (e.g., 'PL' for Premier League)

    Returns:
        Dictionary with standings data
    """
    if competition_code not in SUPPORTED_COMPETITIONS:
        return {"error": f"Competition {competition_code} not available in free tier"}

    cache_key = f"soccer_standings_{competition_code}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    data = await _make_request(f"competitions/{competition_code}/standings")

    if not data:
        return {}

    result = {
        "competition": {
            "id": data.get("competition", {}).get("id"),
            "name": data.get("competition", {}).get("name", ""),
            "code": competition_code,
            "emblem": data.get("competition", {}).get("emblem", "")
        },
        "season": data.get("season", {}),
        "standings": []
    }

    for standing in data.get("standings", []):
        if standing.get("type") == "TOTAL":
            table = []
            for entry in standing.get("table", []):
                team = entry.get("team", {})
                table.append({
                    "position": entry.get("position"),
                    "team_id": team.get("id"),
                    "team_name": team.get("name", ""),
                    "team_short_name": team.get("shortName", ""),
                    "team_crest": team.get("crest", ""),
                    "played": entry.get("playedGames", 0),
                    "won": entry.get("won", 0),
                    "drawn": entry.get("draw", 0),
                    "lost": entry.get("lost", 0),
                    "goals_for": entry.get("goalsFor", 0),
                    "goals_against": entry.get("goalsAgainst", 0),
                    "goal_difference": entry.get("goalDifference", 0),
                    "points": entry.get("points", 0),
                    "form": entry.get("form", "")
                })
            result["standings"] = table
            break

    _set_cached(cache_key, result)
    return result


async def get_matches(
    competition_code: str,
    matchday: Optional[int] = None,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None
) -> List[Dict[str, Any]]:
    """
    Get matches for a competition.

    Args:
        competition_code: Competition code (e.g., 'PL')
        matchday: Specific matchday number
        status: Match status filter (SCHEDULED, LIVE, IN_PLAY, PAUSED, FINISHED, etc.)
        date_from: Start date filter
        date_to: End date filter

    Returns:
        List of match dictionaries
    """
    if competition_code not in SUPPORTED_COMPETITIONS:
        return []

    params = {}
    if matchday:
        params["matchday"] = matchday
    if status:
        params["status"] = status
    if date_from:
        params["dateFrom"] = date_from.isoformat()
    if date_to:
        params["dateTo"] = date_to.isoformat()

    cache_key = f"soccer_matches_{competition_code}_{matchday}_{status}_{date_from}_{date_to}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    data = await _make_request(f"competitions/{competition_code}/matches", params)

    if not data or "matches" not in data:
        return []

    matches = []
    for match in data.get("matches", []):
        home_team = match.get("homeTeam", {})
        away_team = match.get("awayTeam", {})
        score = match.get("score", {})

        matches.append({
            "id": match.get("id"),
            "competition": competition_code,
            "matchday": match.get("matchday"),
            "stage": match.get("stage", ""),
            "group": match.get("group"),
            "utc_date": match.get("utcDate"),
            "status": match.get("status", ""),
            "venue": match.get("venue", ""),
            "home_team": {
                "id": home_team.get("id"),
                "name": home_team.get("name", ""),
                "short_name": home_team.get("shortName", ""),
                "crest": home_team.get("crest", "")
            },
            "away_team": {
                "id": away_team.get("id"),
                "name": away_team.get("name", ""),
                "short_name": away_team.get("shortName", ""),
                "crest": away_team.get("crest", "")
            },
            "score": {
                "winner": score.get("winner"),
                "duration": score.get("duration", "REGULAR"),
                "full_time": score.get("fullTime", {}),
                "half_time": score.get("halfTime", {})
            },
            "referees": [ref.get("name", "") for ref in match.get("referees", [])]
        })

    _set_cached(cache_key, matches)
    return matches


async def get_match(match_id: int) -> Dict[str, Any]:
    """
    Get detailed match information.

    Args:
        match_id: Football-Data.org match ID

    Returns:
        Dictionary with match details
    """
    data = await _make_request(f"matches/{match_id}")

    if not data:
        return {}

    home_team = data.get("homeTeam", {})
    away_team = data.get("awayTeam", {})
    score = data.get("score", {})

    return {
        "id": data.get("id"),
        "competition": {
            "id": data.get("competition", {}).get("id"),
            "name": data.get("competition", {}).get("name", ""),
            "code": data.get("competition", {}).get("code", ""),
            "emblem": data.get("competition", {}).get("emblem", "")
        },
        "season": data.get("season", {}),
        "utc_date": data.get("utcDate"),
        "status": data.get("status", ""),
        "matchday": data.get("matchday"),
        "stage": data.get("stage", ""),
        "venue": data.get("venue", ""),
        "home_team": {
            "id": home_team.get("id"),
            "name": home_team.get("name", ""),
            "short_name": home_team.get("shortName", ""),
            "crest": home_team.get("crest", ""),
            "coach": home_team.get("coach", {}).get("name", ""),
            "formation": home_team.get("formation", "")
        },
        "away_team": {
            "id": away_team.get("id"),
            "name": away_team.get("name", ""),
            "short_name": away_team.get("shortName", ""),
            "crest": away_team.get("crest", ""),
            "coach": away_team.get("coach", {}).get("name", ""),
            "formation": away_team.get("formation", "")
        },
        "score": {
            "winner": score.get("winner"),
            "duration": score.get("duration", "REGULAR"),
            "full_time": score.get("fullTime", {}),
            "half_time": score.get("halfTime", {})
        },
        "goals": data.get("goals", []),
        "bookings": data.get("bookings", []),
        "substitutions": data.get("substitutions", []),
        "referees": data.get("referees", [])
    }


async def get_team(team_id: int) -> Dict[str, Any]:
    """
    Get team information.

    Args:
        team_id: Football-Data.org team ID

    Returns:
        Dictionary with team details
    """
    cache_key = f"soccer_team_{team_id}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    data = await _make_request(f"teams/{team_id}")

    if not data:
        return {}

    result = {
        "id": data.get("id"),
        "name": data.get("name", ""),
        "short_name": data.get("shortName", ""),
        "tla": data.get("tla", ""),
        "crest": data.get("crest", ""),
        "address": data.get("address", ""),
        "website": data.get("website", ""),
        "founded": data.get("founded"),
        "club_colors": data.get("clubColors", ""),
        "venue": data.get("venue", ""),
        "area": data.get("area", {}),
        "running_competitions": [
            {
                "id": comp.get("id"),
                "name": comp.get("name", ""),
                "code": comp.get("code", "")
            }
            for comp in data.get("runningCompetitions", [])
        ],
        "coach": data.get("coach", {}),
        "squad": [
            {
                "id": player.get("id"),
                "name": player.get("name", ""),
                "position": player.get("position", ""),
                "nationality": player.get("nationality", "")
            }
            for player in data.get("squad", [])
        ]
    }

    _set_cached(cache_key, result)
    return result


async def get_team_matches(
    team_id: int,
    status: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get matches for a specific team.

    Args:
        team_id: Football-Data.org team ID
        status: Match status filter
        limit: Maximum matches to return

    Returns:
        List of match dictionaries
    """
    params = {"limit": limit}
    if status:
        params["status"] = status

    data = await _make_request(f"teams/{team_id}/matches", params)

    if not data or "matches" not in data:
        return []

    matches = []
    for match in data.get("matches", []):
        home_team = match.get("homeTeam", {})
        away_team = match.get("awayTeam", {})
        score = match.get("score", {})

        matches.append({
            "id": match.get("id"),
            "competition": {
                "id": match.get("competition", {}).get("id"),
                "name": match.get("competition", {}).get("name", ""),
                "code": match.get("competition", {}).get("code", "")
            },
            "utc_date": match.get("utcDate"),
            "status": match.get("status", ""),
            "home_team": {
                "id": home_team.get("id"),
                "name": home_team.get("name", ""),
                "crest": home_team.get("crest", "")
            },
            "away_team": {
                "id": away_team.get("id"),
                "name": away_team.get("name", ""),
                "crest": away_team.get("crest", "")
            },
            "score": {
                "winner": score.get("winner"),
                "full_time": score.get("fullTime", {})
            }
        })

    return matches


async def get_scorers(competition_code: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get top scorers for a competition.

    Args:
        competition_code: Competition code (e.g., 'PL')
        limit: Number of scorers to return

    Returns:
        List of scorer dictionaries
    """
    if competition_code not in SUPPORTED_COMPETITIONS:
        return []

    cache_key = f"soccer_scorers_{competition_code}_{limit}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    data = await _make_request(f"competitions/{competition_code}/scorers", {"limit": limit})

    if not data or "scorers" not in data:
        return []

    scorers = []
    for scorer in data.get("scorers", []):
        player = scorer.get("player", {})
        team = scorer.get("team", {})

        scorers.append({
            "player_id": player.get("id"),
            "player_name": player.get("name", ""),
            "nationality": player.get("nationality", ""),
            "position": player.get("position", ""),
            "team_id": team.get("id"),
            "team_name": team.get("name", ""),
            "team_crest": team.get("crest", ""),
            "goals": scorer.get("goals", 0),
            "assists": scorer.get("assists"),
            "penalties": scorer.get("penalties"),
            "played_matches": scorer.get("playedMatches", 0)
        })

    _set_cached(cache_key, scorers)
    return scorers


async def get_todays_matches() -> List[Dict[str, Any]]:
    """
    Get all matches across supported competitions for today.

    Returns:
        List of match dictionaries
    """
    cache_key = f"soccer_today_{date.today().isoformat()}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    today = date.today()
    all_matches = []

    for comp_code in SUPPORTED_COMPETITIONS.keys():
        matches = await get_matches(
            comp_code,
            date_from=today,
            date_to=today
        )
        all_matches.extend(matches)

    # Sort by date
    all_matches.sort(key=lambda x: x.get("utc_date", ""))

    _set_cached(cache_key, all_matches)
    return all_matches


# Database storage functions
def store_soccer_teams(db, teams: List[Dict[str, Any]], competition_code: str):
    """Store soccer teams in the database."""
    from app.db import SoccerTeam, SoccerCompetition

    # Find competition
    competition = db.query(SoccerCompetition).filter(
        SoccerCompetition.code == competition_code
    ).first()

    for team_data in teams:
        existing = db.query(SoccerTeam).filter(
            SoccerTeam.football_data_id == team_data["team_id"]
        ).first()

        if existing:
            existing.name = team_data["team_name"]
            existing.short_name = team_data.get("team_short_name", "")
            existing.crest_url = team_data.get("team_crest", "")
        else:
            team = SoccerTeam(
                football_data_id=team_data["team_id"],
                name=team_data["team_name"],
                short_name=team_data.get("team_short_name", ""),
                crest_url=team_data.get("team_crest", ""),
                competition_id=competition.id if competition else None
            )
            db.add(team)

    db.commit()


def store_soccer_match(db, match_data: Dict[str, Any]):
    """Store a soccer match in the database."""
    from app.db import SoccerMatch, SoccerTeam, SoccerCompetition
    from datetime import datetime

    # Find teams
    home_team = db.query(SoccerTeam).filter(
        SoccerTeam.football_data_id == match_data["home_team"]["id"]
    ).first()

    away_team = db.query(SoccerTeam).filter(
        SoccerTeam.football_data_id == match_data["away_team"]["id"]
    ).first()

    # Check if match already exists
    existing = db.query(SoccerMatch).filter(
        SoccerMatch.football_data_id == match_data["id"]
    ).first()

    if existing:
        # Update score if available
        if match_data.get("score", {}).get("full_time"):
            existing.home_score = match_data["score"]["full_time"].get("home")
            existing.away_score = match_data["score"]["full_time"].get("away")
        existing.status = match_data.get("status", "")
        db.commit()
        return existing

    match_time = datetime.fromisoformat(match_data["utc_date"].replace("Z", "+00:00")) if match_data.get("utc_date") else datetime.now()

    match = SoccerMatch(
        football_data_id=match_data["id"],
        competition_code=match_data.get("competition", ""),
        matchday=match_data.get("matchday"),
        home_team_id=home_team.id if home_team else None,
        away_team_id=away_team.id if away_team else None,
        match_date=match_time,
        status=match_data.get("status", "SCHEDULED"),
        venue=match_data.get("venue", ""),
        home_score=match_data.get("score", {}).get("full_time", {}).get("home"),
        away_score=match_data.get("score", {}).get("full_time", {}).get("away"),
        home_team_name=match_data.get("home_team", {}).get("name", ""),
        away_team_name=match_data.get("away_team", {}).get("name", "")
    )
    db.add(match)
    db.commit()
    return match


async def refresh_soccer_data(db):
    """
    Refresh all soccer data - competitions, standings, and matches.
    Called by the scheduler.
    """
    logger.info("Starting Soccer data refresh...")

    if not API_KEY:
        logger.warning("FOOTBALL_DATA_API_KEY not set - skipping soccer data refresh")
        return {"error": "API key not configured", "teams": 0, "matches": 0}

    # Store competitions
    from app.db import SoccerCompetition
    for code, name in SUPPORTED_COMPETITIONS.items():
        existing = db.query(SoccerCompetition).filter(
            SoccerCompetition.code == code
        ).first()
        if not existing:
            comp = SoccerCompetition(code=code, name=name)
            db.add(comp)
    db.commit()

    total_teams = 0
    total_matches = 0

    # Refresh standings for each competition (which gives us teams)
    for comp_code in SUPPORTED_COMPETITIONS.keys():
        try:
            standings = await get_standings(comp_code)
            if standings.get("standings"):
                store_soccer_teams(db, standings["standings"], comp_code)
                total_teams += len(standings["standings"])
                logger.info(f"Stored {len(standings['standings'])} teams for {comp_code}")

            # Get today's and tomorrow's matches
            matches = await get_matches(
                comp_code,
                date_from=date.today(),
                date_to=date.today() + timedelta(days=7)
            )
            for match_data in matches:
                store_soccer_match(db, match_data)
                total_matches += 1

        except Exception as e:
            logger.error(f"Error refreshing {comp_code}: {e}")
            continue

    logger.info(f"Soccer refresh complete: {total_teams} teams, {total_matches} matches")

    return {
        "teams": total_teams,
        "matches": total_matches,
        "competitions": len(SUPPORTED_COMPETITIONS)
    }
