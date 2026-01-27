"""
Sportradar API Integration Service

Comprehensive sports data provider for:
- Real-time game data
- Player statistics
- Injury reports
- Historical data for backtesting

Supports: NFL, NBA, MLB, NHL, Soccer
"""

import os
import hashlib
import httpx
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum

from app.utils.logging import get_logger
from app.utils.cache import cache, TTL_SHORT, TTL_MEDIUM, TTL_LONG

logger = get_logger(__name__)


# =============================================================================
# Configuration
# =============================================================================

SPORTRADAR_API_KEY = os.environ.get("SPORTRADAR_API_KEY", "")
SPORTRADAR_BASE_URL = "https://api.sportradar.us"

# API endpoints by sport
SPORT_CONFIGS = {
    "NFL": {
        "base": "/nfl/official/trial/v7/en",
        "schedule": "/games/{year}/{season}/schedule.json",
        "game": "/games/{game_id}/boxscore.json",
        "standings": "/seasons/{year}/{season}/standings/season.json",
        "injuries": "/league/injuries.json",
        "player": "/players/{player_id}/profile.json",
        "team_roster": "/teams/{team_id}/full_roster.json",
        "weekly_schedule": "/games/{year}/{season}/{week}/schedule.json",
    },
    "NBA": {
        "base": "/nba/trial/v8/en",
        "schedule": "/games/{year}/{season}/schedule.json",
        "game": "/games/{game_id}/boxscore.json",
        "standings": "/seasons/{year}/{season}/standings.json",
        "injuries": "/league/injuries.json",
        "player": "/players/{player_id}/profile.json",
        "team_roster": "/teams/{team_id}/profile.json",
        "daily_schedule": "/games/{year}/{month}/{day}/schedule.json",
    },
    "MLB": {
        "base": "/mlb/trial/v7/en",
        "schedule": "/games/{year}/{season}/schedule.json",
        "game": "/games/{game_id}/boxscore.json",
        "standings": "/seasons/{year}/{season}/standings.json",
        "injuries": "/league/injuries.json",
        "player": "/players/{player_id}/profile.json",
        "team_roster": "/teams/{team_id}/profile.json",
        "daily_schedule": "/games/{year}/{month}/{day}/schedule.json",
    },
    "NHL": {
        "base": "/nhl/trial/v7/en",
        "schedule": "/games/{year}/{season}/schedule.json",
        "game": "/games/{game_id}/boxscore.json",
        "standings": "/seasons/{year}/{season}/standings.json",
        "injuries": "/league/injuries.json",
        "player": "/players/{player_id}/profile.json",
        "team_roster": "/teams/{team_id}/profile.json",
        "daily_schedule": "/games/{year}/{month}/{day}/schedule.json",
    },
    "SOCCER": {
        "base": "/soccer/trial/v4/en",
        "schedule": "/competitions/{competition_id}/seasons/{season_id}/schedules.json",
        "match": "/sport_events/{match_id}/timeline.json",
        "standings": "/competitions/{competition_id}/seasons/{season_id}/standings.json",
        "player": "/players/{player_id}/profile.json",
        "team": "/teams/{team_id}/profile.json",
    },
}

# Season types
class SeasonType(str, Enum):
    PRESEASON = "PRE"
    REGULAR = "REG"
    POSTSEASON = "PST"


# =============================================================================
# API Client
# =============================================================================

def is_api_enabled() -> bool:
    """Check if Sportradar API is enabled."""
    return bool(SPORTRADAR_API_KEY)


async def _make_request(url: str, params: Optional[Dict] = None) -> Optional[Dict]:
    """Make authenticated request to Sportradar API."""
    if not SPORTRADAR_API_KEY:
        logger.debug("Sportradar API key not configured, using simulation")
        return None

    if params is None:
        params = {}
    params["api_key"] = SPORTRADAR_API_KEY

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                logger.error("Sportradar API access denied - check API key")
            elif response.status_code == 429:
                logger.warning("Sportradar rate limit exceeded")
            else:
                logger.error(f"Sportradar API error: {response.status_code}")

            return None
    except Exception as e:
        logger.error(f"Sportradar API request failed: {e}")
        return None


def _build_url(sport: str, endpoint_key: str, **kwargs) -> str:
    """Build Sportradar API URL."""
    config = SPORT_CONFIGS.get(sport.upper())
    if not config:
        raise ValueError(f"Unsupported sport: {sport}")

    base = config["base"]
    endpoint = config.get(endpoint_key, "")

    if not endpoint:
        raise ValueError(f"Unknown endpoint: {endpoint_key}")

    # Format endpoint with provided kwargs
    endpoint = endpoint.format(**kwargs)

    return f"{SPORTRADAR_BASE_URL}{base}{endpoint}"


# =============================================================================
# Real-time Game Data
# =============================================================================

async def get_live_games(sport: str) -> List[Dict[str, Any]]:
    """
    Get currently live games for a sport.

    Args:
        sport: Sport code (NFL, NBA, MLB, NHL, SOCCER)

    Returns:
        List of live game data
    """
    cache_key = f"sportradar:live:{sport.upper()}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    # Try API first
    if is_api_enabled():
        try:
            today = date.today()
            if sport.upper() in ("NBA", "MLB", "NHL"):
                url = _build_url(
                    sport, "daily_schedule",
                    year=today.year,
                    month=str(today.month).zfill(2),
                    day=str(today.day).zfill(2)
                )
            elif sport.upper() == "NFL":
                # NFL uses weekly schedule
                url = _build_url(
                    sport, "weekly_schedule",
                    year=today.year,
                    season="REG",
                    week=_get_nfl_week()
                )
            else:
                url = _build_url(sport, "schedule", year=today.year, season="REG")

            data = await _make_request(url)
            if data and "games" in data:
                live_games = [
                    _parse_game(g, sport)
                    for g in data["games"]
                    if g.get("status") in ("inprogress", "halftime", "live")
                ]
                cache.set(cache_key, live_games, ttl=TTL_SHORT)
                return live_games
        except Exception as e:
            logger.error(f"Error fetching live games: {e}")

    # Simulation mode
    games = _simulate_live_games(sport)
    cache.set(cache_key, games, ttl=TTL_SHORT)
    return games


async def get_game_boxscore(sport: str, game_id: str) -> Dict[str, Any]:
    """
    Get detailed boxscore for a specific game.

    Args:
        sport: Sport code
        game_id: Sportradar game ID

    Returns:
        Game boxscore with stats
    """
    cache_key = f"sportradar:boxscore:{sport}:{game_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    if is_api_enabled():
        try:
            url = _build_url(sport, "game", game_id=game_id)
            data = await _make_request(url)
            if data:
                result = _parse_boxscore(data, sport)
                cache.set(cache_key, result, ttl=TTL_SHORT)
                return result
        except Exception as e:
            logger.error(f"Error fetching boxscore: {e}")

    # Simulation
    result = _simulate_boxscore(sport, game_id)
    cache.set(cache_key, result, ttl=TTL_SHORT)
    return result


async def get_daily_schedule(
    sport: str,
    target_date: Optional[date] = None
) -> List[Dict[str, Any]]:
    """
    Get schedule for a specific date.

    Args:
        sport: Sport code
        target_date: Date to get schedule for (defaults to today)

    Returns:
        List of scheduled games
    """
    if target_date is None:
        target_date = date.today()

    cache_key = f"sportradar:schedule:{sport}:{target_date.isoformat()}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    if is_api_enabled():
        try:
            if sport.upper() in ("NBA", "MLB", "NHL"):
                url = _build_url(
                    sport, "daily_schedule",
                    year=target_date.year,
                    month=str(target_date.month).zfill(2),
                    day=str(target_date.day).zfill(2)
                )
            else:
                url = _build_url(sport, "schedule", year=target_date.year, season="REG")

            data = await _make_request(url)
            if data and "games" in data:
                games = [_parse_game(g, sport) for g in data["games"]]
                cache.set(cache_key, games, ttl=TTL_MEDIUM)
                return games
        except Exception as e:
            logger.error(f"Error fetching schedule: {e}")

    # Simulation
    games = _simulate_schedule(sport, target_date)
    cache.set(cache_key, games, ttl=TTL_MEDIUM)
    return games


# =============================================================================
# Player Statistics
# =============================================================================

async def get_player_profile(sport: str, player_id: str) -> Dict[str, Any]:
    """
    Get player profile and statistics.

    Args:
        sport: Sport code
        player_id: Sportradar player ID

    Returns:
        Player profile with stats
    """
    cache_key = f"sportradar:player:{sport}:{player_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    if is_api_enabled():
        try:
            url = _build_url(sport, "player", player_id=player_id)
            data = await _make_request(url)
            if data:
                result = _parse_player_profile(data, sport)
                cache.set(cache_key, result, ttl=TTL_LONG)
                return result
        except Exception as e:
            logger.error(f"Error fetching player profile: {e}")

    # Simulation
    result = _simulate_player_profile(sport, player_id)
    cache.set(cache_key, result, ttl=TTL_LONG)
    return result


async def get_team_roster(sport: str, team_id: str) -> Dict[str, Any]:
    """
    Get full team roster with player info.

    Args:
        sport: Sport code
        team_id: Sportradar team ID

    Returns:
        Team roster
    """
    cache_key = f"sportradar:roster:{sport}:{team_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    if is_api_enabled():
        try:
            url = _build_url(sport, "team_roster", team_id=team_id)
            data = await _make_request(url)
            if data:
                result = _parse_team_roster(data, sport)
                cache.set(cache_key, result, ttl=TTL_LONG)
                return result
        except Exception as e:
            logger.error(f"Error fetching team roster: {e}")

    # Simulation
    result = _simulate_team_roster(sport, team_id)
    cache.set(cache_key, result, ttl=TTL_LONG)
    return result


async def search_players(
    sport: str,
    query: str,
    position: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search for players by name.

    Args:
        sport: Sport code
        query: Search query
        position: Optional position filter

    Returns:
        List of matching players
    """
    # Simulation - return mock search results
    return _simulate_player_search(sport, query, position)


# =============================================================================
# Injury Reports
# =============================================================================

async def get_injuries(sport: str) -> List[Dict[str, Any]]:
    """
    Get current injury report for a sport.

    Args:
        sport: Sport code

    Returns:
        List of injured players
    """
    cache_key = f"sportradar:injuries:{sport}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    if is_api_enabled():
        try:
            url = _build_url(sport, "injuries")
            data = await _make_request(url)
            if data and "teams" in data:
                injuries = []
                for team in data["teams"]:
                    team_name = team.get("name", "Unknown")
                    for player in team.get("players", []):
                        injuries.append(_parse_injury(player, team_name, sport))
                cache.set(cache_key, injuries, ttl=TTL_MEDIUM)
                return injuries
        except Exception as e:
            logger.error(f"Error fetching injuries: {e}")

    # Simulation
    injuries = _simulate_injuries(sport)
    cache.set(cache_key, injuries, ttl=TTL_MEDIUM)
    return injuries


async def get_team_injuries(sport: str, team_id: str) -> List[Dict[str, Any]]:
    """
    Get injuries for a specific team.

    Args:
        sport: Sport code
        team_id: Team ID or abbreviation

    Returns:
        List of team's injured players
    """
    all_injuries = await get_injuries(sport)
    return [
        inj for inj in all_injuries
        if inj.get("team_id") == team_id or team_id.upper() in inj.get("team", "").upper()
    ]


# =============================================================================
# Historical Data
# =============================================================================

async def get_historical_games(
    sport: str,
    start_date: date,
    end_date: Optional[date] = None,
    team_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get historical game data for backtesting.

    Args:
        sport: Sport code
        start_date: Start date
        end_date: End date (defaults to start_date)
        team_id: Optional team filter

    Returns:
        List of historical games with results
    """
    if end_date is None:
        end_date = start_date

    cache_key = f"sportradar:historical:{sport}:{start_date}:{end_date}:{team_id or 'all'}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    games = []

    # Iterate through dates
    current = start_date
    while current <= end_date:
        day_games = await get_daily_schedule(sport, current)
        games.extend(day_games)
        current += timedelta(days=1)

    # Filter by team if specified
    if team_id:
        games = [
            g for g in games
            if team_id.upper() in g.get("home_team", {}).get("id", "").upper()
            or team_id.upper() in g.get("away_team", {}).get("id", "").upper()
            or team_id.upper() in g.get("home_team", {}).get("abbreviation", "").upper()
            or team_id.upper() in g.get("away_team", {}).get("abbreviation", "").upper()
        ]

    cache.set(cache_key, games, ttl=TTL_LONG)
    return games


async def get_standings(
    sport: str,
    season_year: Optional[int] = None,
    season_type: str = "REG"
) -> Dict[str, Any]:
    """
    Get league standings.

    Args:
        sport: Sport code
        season_year: Season year (defaults to current)
        season_type: Season type (PRE, REG, PST)

    Returns:
        Standings data
    """
    if season_year is None:
        season_year = date.today().year

    cache_key = f"sportradar:standings:{sport}:{season_year}:{season_type}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    if is_api_enabled():
        try:
            url = _build_url(
                sport, "standings",
                year=season_year,
                season=season_type
            )
            data = await _make_request(url)
            if data:
                result = _parse_standings(data, sport)
                cache.set(cache_key, result, ttl=TTL_MEDIUM)
                return result
        except Exception as e:
            logger.error(f"Error fetching standings: {e}")

    # Simulation
    result = _simulate_standings(sport, season_year)
    cache.set(cache_key, result, ttl=TTL_MEDIUM)
    return result


# =============================================================================
# Parsing Functions
# =============================================================================

def _parse_game(game_data: Dict, sport: str) -> Dict[str, Any]:
    """Parse raw game data into standard format."""
    return {
        "id": game_data.get("id"),
        "status": game_data.get("status"),
        "scheduled": game_data.get("scheduled"),
        "home_team": {
            "id": game_data.get("home", {}).get("id"),
            "name": game_data.get("home", {}).get("name"),
            "abbreviation": game_data.get("home", {}).get("alias"),
            "score": game_data.get("home", {}).get("points", 0),
        },
        "away_team": {
            "id": game_data.get("away", {}).get("id"),
            "name": game_data.get("away", {}).get("name"),
            "abbreviation": game_data.get("away", {}).get("alias"),
            "score": game_data.get("away", {}).get("points", 0),
        },
        "venue": game_data.get("venue", {}).get("name"),
        "broadcast": game_data.get("broadcast", {}).get("network"),
        "sport": sport.upper(),
    }


def _parse_boxscore(data: Dict, sport: str) -> Dict[str, Any]:
    """Parse boxscore data."""
    return {
        "game_id": data.get("id"),
        "status": data.get("status"),
        "home": {
            "team": data.get("home", {}).get("name"),
            "score": data.get("home", {}).get("points", 0),
            "statistics": data.get("home", {}).get("statistics", {}),
        },
        "away": {
            "team": data.get("away", {}).get("name"),
            "score": data.get("away", {}).get("points", 0),
            "statistics": data.get("away", {}).get("statistics", {}),
        },
        "sport": sport.upper(),
    }


def _parse_player_profile(data: Dict, sport: str) -> Dict[str, Any]:
    """Parse player profile data."""
    return {
        "id": data.get("id"),
        "name": data.get("full_name") or f"{data.get('first_name', '')} {data.get('last_name', '')}",
        "position": data.get("position"),
        "team": data.get("team", {}).get("name"),
        "team_id": data.get("team", {}).get("id"),
        "jersey_number": data.get("jersey_number"),
        "height": data.get("height"),
        "weight": data.get("weight"),
        "birth_date": data.get("birth_date"),
        "experience": data.get("experience"),
        "college": data.get("college"),
        "draft": data.get("draft"),
        "seasons": data.get("seasons", []),
        "sport": sport.upper(),
    }


def _parse_team_roster(data: Dict, sport: str) -> Dict[str, Any]:
    """Parse team roster data."""
    return {
        "team_id": data.get("id"),
        "team_name": data.get("name"),
        "abbreviation": data.get("alias"),
        "players": [
            {
                "id": p.get("id"),
                "name": p.get("full_name") or f"{p.get('first_name', '')} {p.get('last_name', '')}",
                "position": p.get("position"),
                "jersey_number": p.get("jersey_number"),
                "status": p.get("status"),
            }
            for p in data.get("players", [])
        ],
        "coaches": data.get("coaches", []),
        "sport": sport.upper(),
    }


def _parse_injury(player_data: Dict, team_name: str, sport: str) -> Dict[str, Any]:
    """Parse injury data."""
    return {
        "player_id": player_data.get("id"),
        "player_name": player_data.get("full_name") or f"{player_data.get('first_name', '')} {player_data.get('last_name', '')}",
        "team": team_name,
        "position": player_data.get("position"),
        "status": player_data.get("injury", {}).get("status", "Unknown"),
        "injury_type": player_data.get("injury", {}).get("desc", "Undisclosed"),
        "practice_status": player_data.get("injury", {}).get("practice_status"),
        "updated": player_data.get("injury", {}).get("update_date"),
        "sport": sport.upper(),
    }


def _parse_standings(data: Dict, sport: str) -> Dict[str, Any]:
    """Parse standings data."""
    return {
        "sport": sport.upper(),
        "season": data.get("season", {}).get("year"),
        "conferences": data.get("conferences", []),
        "divisions": data.get("divisions", []),
    }


# =============================================================================
# Simulation Functions (for when API is not available)
# =============================================================================

def _get_nfl_week() -> int:
    """Calculate current NFL week."""
    # NFL season typically starts first Thursday of September
    today = date.today()
    # Simplified - assume Week 1 starts early September
    season_start = date(today.year, 9, 5)
    if today < season_start:
        return 1
    weeks = (today - season_start).days // 7 + 1
    return min(weeks, 18)  # Max 18 weeks


def _simulate_live_games(sport: str) -> List[Dict[str, Any]]:
    """Generate simulated live games."""
    import random

    teams = _get_sport_teams(sport)
    if len(teams) < 4:
        return []

    games = []
    num_games = random.randint(1, 3)

    for i in range(num_games):
        home_idx = random.randint(0, len(teams) - 1)
        away_idx = (home_idx + random.randint(1, len(teams) - 1)) % len(teams)

        home = teams[home_idx]
        away = teams[away_idx]

        if sport.upper() in ("NFL", "CFB"):
            home_score = random.randint(7, 35)
            away_score = random.randint(7, 35)
            period = random.choice(["Q1", "Q2", "Q3", "Q4", "Halftime"])
        elif sport.upper() in ("NBA", "CBB"):
            home_score = random.randint(45, 110)
            away_score = random.randint(45, 110)
            period = random.choice(["Q1", "Q2", "Q3", "Q4", "Halftime"])
        elif sport.upper() == "MLB":
            home_score = random.randint(0, 8)
            away_score = random.randint(0, 8)
            period = f"{'Top' if random.random() > 0.5 else 'Bot'} {random.randint(1, 9)}"
        elif sport.upper() == "NHL":
            home_score = random.randint(0, 5)
            away_score = random.randint(0, 5)
            period = random.choice(["1st", "2nd", "3rd", "OT"])
        else:
            home_score = random.randint(0, 4)
            away_score = random.randint(0, 4)
            period = f"{random.randint(1, 90)}'"

        games.append({
            "id": f"sr:game:{sport.lower()}:{i+1}",
            "status": "inprogress",
            "scheduled": datetime.now().isoformat(),
            "period": period,
            "home_team": {
                "id": home["id"],
                "name": home["name"],
                "abbreviation": home["abbr"],
                "score": home_score,
            },
            "away_team": {
                "id": away["id"],
                "name": away["name"],
                "abbreviation": away["abbr"],
                "score": away_score,
            },
            "sport": sport.upper(),
        })

    return games


def _simulate_schedule(sport: str, target_date: date) -> List[Dict[str, Any]]:
    """Generate simulated schedule."""
    import random

    teams = _get_sport_teams(sport)
    games = []

    # Generate 3-8 games
    num_games = random.randint(3, min(8, len(teams) // 2))
    used_teams = set()

    for i in range(num_games):
        available = [t for t in teams if t["id"] not in used_teams]
        if len(available) < 2:
            break

        home = random.choice(available)
        used_teams.add(home["id"])
        available = [t for t in available if t["id"] != home["id"]]
        away = random.choice(available)
        used_teams.add(away["id"])

        # Random game time
        hours = [13, 16, 19, 20] if sport.upper() in ("NFL", "CFB") else [19, 20, 22]
        game_time = datetime.combine(target_date, datetime.min.time().replace(hour=random.choice(hours)))

        # Determine if game is completed (past date)
        status = "closed" if target_date < date.today() else "scheduled"

        games.append({
            "id": f"sr:game:{sport.lower()}:{target_date.isoformat()}:{i+1}",
            "status": status,
            "scheduled": game_time.isoformat(),
            "home_team": {
                "id": home["id"],
                "name": home["name"],
                "abbreviation": home["abbr"],
                "score": random.randint(70, 130) if status == "closed" and sport == "NBA" else (
                    random.randint(14, 42) if status == "closed" and sport == "NFL" else 0
                ),
            },
            "away_team": {
                "id": away["id"],
                "name": away["name"],
                "abbreviation": away["abbr"],
                "score": random.randint(70, 130) if status == "closed" and sport == "NBA" else (
                    random.randint(14, 42) if status == "closed" and sport == "NFL" else 0
                ),
            },
            "sport": sport.upper(),
        })

    return games


def _simulate_boxscore(sport: str, game_id: str) -> Dict[str, Any]:
    """Generate simulated boxscore."""
    import random

    teams = _get_sport_teams(sport)
    home = random.choice(teams)
    away = random.choice([t for t in teams if t["id"] != home["id"]])

    return {
        "game_id": game_id,
        "status": "closed",
        "home": {
            "team": home["name"],
            "score": random.randint(80, 120) if sport == "NBA" else random.randint(17, 35),
            "statistics": _generate_team_stats(sport),
        },
        "away": {
            "team": away["name"],
            "score": random.randint(80, 120) if sport == "NBA" else random.randint(17, 35),
            "statistics": _generate_team_stats(sport),
        },
        "sport": sport.upper(),
    }


def _simulate_player_profile(sport: str, player_id: str) -> Dict[str, Any]:
    """Generate simulated player profile."""
    import random

    positions = {
        "NFL": ["QB", "RB", "WR", "TE", "OL", "DL", "LB", "CB", "S", "K"],
        "NBA": ["PG", "SG", "SF", "PF", "C"],
        "MLB": ["P", "C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH"],
        "NHL": ["C", "LW", "RW", "D", "G"],
    }

    first_names = ["James", "Michael", "Patrick", "Josh", "Justin", "Travis", "Tyreek", "Aaron"]
    last_names = ["Johnson", "Williams", "Brown", "Jones", "Davis", "Miller", "Wilson", "Taylor"]

    pos = random.choice(positions.get(sport.upper(), ["Unknown"]))
    name = f"{random.choice(first_names)} {random.choice(last_names)}"

    return {
        "id": player_id,
        "name": name,
        "position": pos,
        "team": random.choice(_get_sport_teams(sport))["name"],
        "jersey_number": str(random.randint(1, 99)),
        "height": f"{random.randint(5, 7)}'{random.randint(0, 11)}\"",
        "weight": random.randint(180, 320),
        "birth_date": f"{random.randint(1990, 2002)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
        "experience": random.randint(1, 15),
        "college": random.choice(["Alabama", "Ohio State", "Georgia", "Michigan", "Texas", "LSU"]),
        "sport": sport.upper(),
    }


def _simulate_team_roster(sport: str, team_id: str) -> Dict[str, Any]:
    """Generate simulated team roster."""
    import random

    team = None
    for t in _get_sport_teams(sport):
        if t["id"] == team_id or t["abbr"].upper() == team_id.upper():
            team = t
            break

    if not team:
        team = {"id": team_id, "name": "Unknown Team", "abbr": team_id[:3].upper()}

    positions = {
        "NFL": ["QB", "RB", "RB", "WR", "WR", "WR", "TE", "OL", "OL", "OL", "OL", "OL",
                "DL", "DL", "DL", "DL", "LB", "LB", "LB", "CB", "CB", "S", "S", "K", "P"],
        "NBA": ["PG", "SG", "SF", "PF", "C", "PG", "SG", "SF", "PF", "C", "G", "F", "C"],
        "MLB": ["P", "P", "P", "P", "P", "C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH", "UT"],
        "NHL": ["C", "C", "C", "LW", "LW", "LW", "RW", "RW", "RW", "D", "D", "D", "D", "D", "D", "G", "G"],
    }

    first_names = ["James", "Michael", "Patrick", "Josh", "Justin", "Travis", "Tyreek", "Aaron",
                   "Lamar", "Jalen", "Chris", "David", "Robert", "Anthony", "Marcus"]
    last_names = ["Johnson", "Williams", "Brown", "Jones", "Davis", "Miller", "Wilson", "Taylor",
                  "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin", "Thompson"]

    players = []
    for i, pos in enumerate(positions.get(sport.upper(), ["Unknown"] * 15)):
        players.append({
            "id": f"sr:player:{team['abbr'].lower()}:{i+1}",
            "name": f"{random.choice(first_names)} {random.choice(last_names)}",
            "position": pos,
            "jersey_number": str(random.randint(1, 99)),
            "status": random.choices(["Active", "Active", "Active", "Injured"], [0.85, 0.05, 0.05, 0.05])[0],
        })

    return {
        "team_id": team["id"],
        "team_name": team["name"],
        "abbreviation": team["abbr"],
        "players": players,
        "sport": sport.upper(),
    }


def _simulate_injuries(sport: str) -> List[Dict[str, Any]]:
    """Generate simulated injury report."""
    import random

    teams = _get_sport_teams(sport)
    injuries = []

    injury_types = {
        "NFL": ["Hamstring", "Knee", "Ankle", "Shoulder", "Concussion", "Back", "Quad", "Calf"],
        "NBA": ["Knee", "Ankle", "Back", "Hamstring", "Quad", "Shoulder", "Wrist"],
        "MLB": ["Shoulder", "Elbow", "Hamstring", "Oblique", "Back", "Knee", "Wrist"],
        "NHL": ["Lower Body", "Upper Body", "Undisclosed", "Concussion"],
    }

    statuses = ["Out", "Doubtful", "Questionable", "Probable", "Day-to-Day"]
    first_names = ["James", "Michael", "Patrick", "Josh", "Justin", "Travis", "Tyreek", "Aaron"]
    last_names = ["Johnson", "Williams", "Brown", "Jones", "Davis", "Miller", "Wilson", "Taylor"]

    # 2-5 injuries per team average
    for team in teams:
        num_injuries = random.randint(0, 6)
        for i in range(num_injuries):
            injuries.append({
                "player_id": f"sr:player:{team['abbr'].lower()}:inj:{i+1}",
                "player_name": f"{random.choice(first_names)} {random.choice(last_names)}",
                "team": team["name"],
                "team_id": team["id"],
                "position": random.choice(["QB", "RB", "WR", "TE", "OL", "DL", "LB", "CB", "S"] if sport == "NFL" else ["G", "F", "C"]),
                "status": random.choice(statuses),
                "injury_type": random.choice(injury_types.get(sport.upper(), ["Undisclosed"])),
                "practice_status": random.choice(["DNP", "Limited", "Full", None]),
                "updated": (date.today() - timedelta(days=random.randint(0, 3))).isoformat(),
                "sport": sport.upper(),
            })

    return injuries


def _simulate_standings(sport: str, season_year: int) -> Dict[str, Any]:
    """Generate simulated standings."""
    import random

    teams = _get_sport_teams(sport)
    random.shuffle(teams)

    standings = []
    for i, team in enumerate(teams):
        if sport.upper() in ("NFL", "CFB"):
            wins = random.randint(0, 17 if sport == "NFL" else 12)
            losses = 17 - wins if sport == "NFL" else 12 - wins
            ties = random.randint(0, 1) if random.random() < 0.1 else 0
        elif sport.upper() == "NBA":
            wins = random.randint(15, 67)
            losses = 82 - wins
            ties = 0
        elif sport.upper() == "MLB":
            wins = random.randint(50, 110)
            losses = 162 - wins
            ties = 0
        else:
            wins = random.randint(20, 60)
            losses = 82 - wins
            ties = random.randint(0, 5)

        standings.append({
            "rank": i + 1,
            "team_id": team["id"],
            "team_name": team["name"],
            "abbreviation": team["abbr"],
            "wins": wins,
            "losses": losses,
            "ties": ties,
            "win_pct": round(wins / (wins + losses + ties), 3) if (wins + losses + ties) > 0 else 0,
            "games_back": round(i * 0.5, 1) if i > 0 else 0,
        })

    # Sort by win percentage
    standings.sort(key=lambda x: x["win_pct"], reverse=True)
    for i, s in enumerate(standings):
        s["rank"] = i + 1
        s["games_back"] = round((standings[0]["wins"] - s["wins"] + s["losses"] - standings[0]["losses"]) / 2, 1)

    return {
        "sport": sport.upper(),
        "season": season_year,
        "standings": standings,
    }


def _simulate_player_search(sport: str, query: str, position: Optional[str]) -> List[Dict[str, Any]]:
    """Simulate player search results."""
    import random

    results = []
    num_results = random.randint(1, 5)

    for i in range(num_results):
        player = _simulate_player_profile(sport, f"sr:player:search:{i+1}")
        # Make name somewhat match query
        if query:
            player["name"] = f"{query.title()} {player['name'].split()[-1]}"
        if position:
            player["position"] = position
        results.append(player)

    return results


def _generate_team_stats(sport: str) -> Dict[str, Any]:
    """Generate team statistics."""
    import random

    if sport.upper() == "NFL":
        return {
            "total_yards": random.randint(250, 500),
            "passing_yards": random.randint(150, 350),
            "rushing_yards": random.randint(80, 200),
            "turnovers": random.randint(0, 4),
            "first_downs": random.randint(15, 30),
            "third_down_pct": round(random.uniform(0.3, 0.6), 2),
            "time_of_possession": f"{random.randint(25, 35)}:{random.randint(0, 59):02d}",
        }
    elif sport.upper() == "NBA":
        return {
            "field_goal_pct": round(random.uniform(0.40, 0.55), 3),
            "three_point_pct": round(random.uniform(0.30, 0.45), 3),
            "free_throw_pct": round(random.uniform(0.70, 0.90), 3),
            "rebounds": random.randint(35, 55),
            "assists": random.randint(18, 32),
            "steals": random.randint(5, 15),
            "blocks": random.randint(3, 10),
            "turnovers": random.randint(8, 20),
        }
    elif sport.upper() == "MLB":
        return {
            "hits": random.randint(5, 15),
            "runs": random.randint(2, 10),
            "errors": random.randint(0, 3),
            "strikeouts": random.randint(5, 15),
            "walks": random.randint(2, 8),
            "home_runs": random.randint(0, 4),
        }
    else:
        return {}


def _get_sport_teams(sport: str) -> List[Dict[str, Any]]:
    """Get list of teams for a sport."""
    teams = {
        "NFL": [
            {"id": "sr:team:nfl:1", "name": "Kansas City Chiefs", "abbr": "KC"},
            {"id": "sr:team:nfl:2", "name": "Buffalo Bills", "abbr": "BUF"},
            {"id": "sr:team:nfl:3", "name": "Philadelphia Eagles", "abbr": "PHI"},
            {"id": "sr:team:nfl:4", "name": "San Francisco 49ers", "abbr": "SF"},
            {"id": "sr:team:nfl:5", "name": "Dallas Cowboys", "abbr": "DAL"},
            {"id": "sr:team:nfl:6", "name": "Miami Dolphins", "abbr": "MIA"},
            {"id": "sr:team:nfl:7", "name": "Baltimore Ravens", "abbr": "BAL"},
            {"id": "sr:team:nfl:8", "name": "Detroit Lions", "abbr": "DET"},
            {"id": "sr:team:nfl:9", "name": "Green Bay Packers", "abbr": "GB"},
            {"id": "sr:team:nfl:10", "name": "Cincinnati Bengals", "abbr": "CIN"},
            {"id": "sr:team:nfl:11", "name": "Cleveland Browns", "abbr": "CLE"},
            {"id": "sr:team:nfl:12", "name": "Pittsburgh Steelers", "abbr": "PIT"},
            {"id": "sr:team:nfl:13", "name": "New York Jets", "abbr": "NYJ"},
            {"id": "sr:team:nfl:14", "name": "New England Patriots", "abbr": "NE"},
            {"id": "sr:team:nfl:15", "name": "Los Angeles Rams", "abbr": "LAR"},
            {"id": "sr:team:nfl:16", "name": "Las Vegas Raiders", "abbr": "LV"},
        ],
        "NBA": [
            {"id": "sr:team:nba:1", "name": "Boston Celtics", "abbr": "BOS"},
            {"id": "sr:team:nba:2", "name": "Denver Nuggets", "abbr": "DEN"},
            {"id": "sr:team:nba:3", "name": "Milwaukee Bucks", "abbr": "MIL"},
            {"id": "sr:team:nba:4", "name": "Philadelphia 76ers", "abbr": "PHI"},
            {"id": "sr:team:nba:5", "name": "Phoenix Suns", "abbr": "PHX"},
            {"id": "sr:team:nba:6", "name": "Golden State Warriors", "abbr": "GSW"},
            {"id": "sr:team:nba:7", "name": "Los Angeles Lakers", "abbr": "LAL"},
            {"id": "sr:team:nba:8", "name": "Miami Heat", "abbr": "MIA"},
            {"id": "sr:team:nba:9", "name": "New York Knicks", "abbr": "NYK"},
            {"id": "sr:team:nba:10", "name": "Dallas Mavericks", "abbr": "DAL"},
            {"id": "sr:team:nba:11", "name": "Cleveland Cavaliers", "abbr": "CLE"},
            {"id": "sr:team:nba:12", "name": "Sacramento Kings", "abbr": "SAC"},
        ],
        "MLB": [
            {"id": "sr:team:mlb:1", "name": "New York Yankees", "abbr": "NYY"},
            {"id": "sr:team:mlb:2", "name": "Los Angeles Dodgers", "abbr": "LAD"},
            {"id": "sr:team:mlb:3", "name": "Atlanta Braves", "abbr": "ATL"},
            {"id": "sr:team:mlb:4", "name": "Houston Astros", "abbr": "HOU"},
            {"id": "sr:team:mlb:5", "name": "Philadelphia Phillies", "abbr": "PHI"},
            {"id": "sr:team:mlb:6", "name": "San Diego Padres", "abbr": "SD"},
            {"id": "sr:team:mlb:7", "name": "Chicago Cubs", "abbr": "CHC"},
            {"id": "sr:team:mlb:8", "name": "Boston Red Sox", "abbr": "BOS"},
            {"id": "sr:team:mlb:9", "name": "Texas Rangers", "abbr": "TEX"},
            {"id": "sr:team:mlb:10", "name": "Arizona Diamondbacks", "abbr": "ARI"},
        ],
        "NHL": [
            {"id": "sr:team:nhl:1", "name": "Boston Bruins", "abbr": "BOS"},
            {"id": "sr:team:nhl:2", "name": "Carolina Hurricanes", "abbr": "CAR"},
            {"id": "sr:team:nhl:3", "name": "New Jersey Devils", "abbr": "NJD"},
            {"id": "sr:team:nhl:4", "name": "Toronto Maple Leafs", "abbr": "TOR"},
            {"id": "sr:team:nhl:5", "name": "Vegas Golden Knights", "abbr": "VGK"},
            {"id": "sr:team:nhl:6", "name": "Edmonton Oilers", "abbr": "EDM"},
            {"id": "sr:team:nhl:7", "name": "Colorado Avalanche", "abbr": "COL"},
            {"id": "sr:team:nhl:8", "name": "Dallas Stars", "abbr": "DAL"},
        ],
        "SOCCER": [
            {"id": "sr:team:soccer:1", "name": "Manchester City", "abbr": "MCI"},
            {"id": "sr:team:soccer:2", "name": "Arsenal", "abbr": "ARS"},
            {"id": "sr:team:soccer:3", "name": "Liverpool", "abbr": "LIV"},
            {"id": "sr:team:soccer:4", "name": "Manchester United", "abbr": "MUN"},
            {"id": "sr:team:soccer:5", "name": "Chelsea", "abbr": "CHE"},
            {"id": "sr:team:soccer:6", "name": "Tottenham", "abbr": "TOT"},
            {"id": "sr:team:soccer:7", "name": "Real Madrid", "abbr": "RMA"},
            {"id": "sr:team:soccer:8", "name": "Barcelona", "abbr": "BAR"},
        ],
    }

    return teams.get(sport.upper(), [])


# =============================================================================
# Status & Configuration
# =============================================================================

def get_api_status() -> Dict[str, Any]:
    """Get Sportradar API status and configuration."""
    return {
        "api_enabled": is_api_enabled(),
        "data_source": "Sportradar API" if is_api_enabled() else "Simulated",
        "supported_sports": list(SPORT_CONFIGS.keys()),
        "features": {
            "live_games": True,
            "boxscores": True,
            "player_stats": True,
            "injuries": True,
            "historical_data": True,
            "standings": True,
        },
        "cache_settings": {
            "live_data": f"{TTL_SHORT}s",
            "schedules": f"{TTL_MEDIUM}s",
            "player_profiles": f"{TTL_LONG}s",
        },
        "note": "Set SPORTRADAR_API_KEY environment variable to enable live data",
    }
