"""
NFL Stats API Integration Service

Uses ESPN's hidden API to access NFL data.
No API key required.
"""

from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import httpx

from app.utils.logging import get_logger

logger = get_logger(__name__)

# ESPN API endpoints for NFL
ESPN_NFL_BASE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
ESPN_NFL_SCOREBOARD = f"{ESPN_NFL_BASE}/scoreboard"
ESPN_NFL_TEAMS = f"{ESPN_NFL_BASE}/teams"
ESPN_NFL_STANDINGS = f"{ESPN_NFL_BASE}/standings"

# NFL Team information with abbreviations
NFL_TEAMS = {
    "ARI": {"name": "Arizona Cardinals", "city": "Arizona"},
    "ATL": {"name": "Atlanta Falcons", "city": "Atlanta"},
    "BAL": {"name": "Baltimore Ravens", "city": "Baltimore"},
    "BUF": {"name": "Buffalo Bills", "city": "Buffalo"},
    "CAR": {"name": "Carolina Panthers", "city": "Carolina"},
    "CHI": {"name": "Chicago Bears", "city": "Chicago"},
    "CIN": {"name": "Cincinnati Bengals", "city": "Cincinnati"},
    "CLE": {"name": "Cleveland Browns", "city": "Cleveland"},
    "DAL": {"name": "Dallas Cowboys", "city": "Dallas"},
    "DEN": {"name": "Denver Broncos", "city": "Denver"},
    "DET": {"name": "Detroit Lions", "city": "Detroit"},
    "GB": {"name": "Green Bay Packers", "city": "Green Bay"},
    "HOU": {"name": "Houston Texans", "city": "Houston"},
    "IND": {"name": "Indianapolis Colts", "city": "Indianapolis"},
    "JAX": {"name": "Jacksonville Jaguars", "city": "Jacksonville"},
    "KC": {"name": "Kansas City Chiefs", "city": "Kansas City"},
    "LV": {"name": "Las Vegas Raiders", "city": "Las Vegas"},
    "LAC": {"name": "Los Angeles Chargers", "city": "Los Angeles"},
    "LAR": {"name": "Los Angeles Rams", "city": "Los Angeles"},
    "MIA": {"name": "Miami Dolphins", "city": "Miami"},
    "MIN": {"name": "Minnesota Vikings", "city": "Minnesota"},
    "NE": {"name": "New England Patriots", "city": "New England"},
    "NO": {"name": "New Orleans Saints", "city": "New Orleans"},
    "NYG": {"name": "New York Giants", "city": "New York"},
    "NYJ": {"name": "New York Jets", "city": "New York"},
    "PHI": {"name": "Philadelphia Eagles", "city": "Philadelphia"},
    "PIT": {"name": "Pittsburgh Steelers", "city": "Pittsburgh"},
    "SF": {"name": "San Francisco 49ers", "city": "San Francisco"},
    "SEA": {"name": "Seattle Seahawks", "city": "Seattle"},
    "TB": {"name": "Tampa Bay Buccaneers", "city": "Tampa Bay"},
    "TEN": {"name": "Tennessee Titans", "city": "Tennessee"},
    "WAS": {"name": "Washington Commanders", "city": "Washington"},
}


async def _fetch_espn(url: str, params: Dict[str, Any] = None) -> Optional[Dict]:
    """Fetch data from ESPN API with error handling."""
    logger.debug(f"ESPN NFL request: {url} params={params}")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            logger.debug(f"ESPN NFL success: {url} status={response.status_code}")
            return response.json()
    except httpx.TimeoutException:
        logger.error(f"ESPN NFL timeout: {url}")
        return None
    except httpx.HTTPStatusError as e:
        logger.error(f"ESPN NFL HTTP error: {url} status={e.response.status_code}")
        return None
    except httpx.HTTPError as e:
        logger.error(f"ESPN NFL API error: {url} error={e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"ESPN NFL unexpected error: {url} error={e}", exc_info=True)
        return None


async def get_teams() -> List[Dict[str, Any]]:
    """
    Get all NFL teams.

    Returns:
        List of teams with ESPN IDs, names, and divisions.
    """
    data = await _fetch_espn(ESPN_NFL_TEAMS)

    if not data or "sports" not in data:
        # Return static team list as fallback
        return [
            {
                "abbreviation": abbr,
                "name": info["name"],
                "city": info["city"]
            }
            for abbr, info in NFL_TEAMS.items()
        ]

    teams = []
    try:
        for team in data["sports"][0]["leagues"][0]["teams"]:
            team_data = team.get("team", {})
            teams.append({
                "espn_id": team_data.get("id"),
                "name": team_data.get("displayName", ""),
                "short_name": team_data.get("shortDisplayName", ""),
                "abbreviation": team_data.get("abbreviation", ""),
                "location": team_data.get("location", ""),
                "logo_url": team_data.get("logos", [{}])[0].get("href") if team_data.get("logos") else None,
                "color": team_data.get("color"),
            })
    except (KeyError, IndexError) as e:
        logger.warning(f"Error parsing teams data: {e}")
        return [
            {
                "abbreviation": abbr,
                "name": info["name"],
                "city": info["city"]
            }
            for abbr, info in NFL_TEAMS.items()
        ]

    return teams


async def get_scoreboard(game_date: date = None) -> List[Dict[str, Any]]:
    """
    Get NFL scoreboard for a specific date.

    Args:
        game_date: Date to get scoreboard for (defaults to today)

    Returns:
        List of games with scores and status
    """
    if game_date is None:
        game_date = date.today()

    params = {"dates": game_date.strftime("%Y%m%d")}
    data = await _fetch_espn(ESPN_NFL_SCOREBOARD, params)

    if not data:
        return []

    games = []
    for event in data.get("events", []):
        try:
            competition = event.get("competitions", [{}])[0]
            competitors = competition.get("competitors", [])

            if len(competitors) < 2:
                continue

            # Find home and away teams
            home_team = None
            away_team = None
            for team in competitors:
                if team.get("homeAway") == "home":
                    home_team = team
                else:
                    away_team = team

            if not home_team or not away_team:
                continue

            # Get odds if available
            odds = None
            odds_data = competition.get("odds", [])
            if odds_data:
                odd = odds_data[0]
                odds = {
                    "spread": odd.get("spread"),
                    "over_under": odd.get("overUnder"),
                    "home_moneyline": odd.get("homeTeamOdds", {}).get("moneyLine"),
                    "away_moneyline": odd.get("awayTeamOdds", {}).get("moneyLine"),
                }

            # Get broadcast info
            broadcast = None
            broadcasts = competition.get("broadcasts", [])
            if broadcasts:
                broadcast = broadcasts[0].get("names", [""])[0] if broadcasts[0].get("names") else None

            games.append({
                "id": event.get("id"),
                "espn_id": event.get("id"),
                "name": event.get("name"),
                "status": event.get("status", {}).get("type", {}).get("description", ""),
                "status_detail": event.get("status", {}).get("type", {}).get("detail", ""),
                "game_date": event.get("date"),
                "venue": competition.get("venue", {}).get("fullName", ""),
                "week": event.get("week", {}).get("number"),
                "home_team": {
                    "id": home_team.get("team", {}).get("id"),
                    "name": home_team.get("team", {}).get("displayName", ""),
                    "abbreviation": home_team.get("team", {}).get("abbreviation", ""),
                    "score": int(home_team.get("score", 0)) if home_team.get("score") else None,
                    "record": home_team.get("records", [{}])[0].get("summary") if home_team.get("records") else None,
                    "logo_url": home_team.get("team", {}).get("logo"),
                },
                "away_team": {
                    "id": away_team.get("team", {}).get("id"),
                    "name": away_team.get("team", {}).get("displayName", ""),
                    "abbreviation": away_team.get("team", {}).get("abbreviation", ""),
                    "score": int(away_team.get("score", 0)) if away_team.get("score") else None,
                    "record": away_team.get("records", [{}])[0].get("summary") if away_team.get("records") else None,
                    "logo_url": away_team.get("team", {}).get("logo"),
                },
                "odds": odds,
                "broadcast": broadcast,
                "quarter": event.get("status", {}).get("period"),
                "time_remaining": event.get("status", {}).get("displayClock"),
                "is_live": event.get("status", {}).get("type", {}).get("state") == "in",
            })
        except (KeyError, IndexError, TypeError) as e:
            logger.warning(f"Error parsing game: {e}")
            continue

    return games


async def get_current_week_games() -> List[Dict[str, Any]]:
    """
    Get games for the current NFL week.

    Returns:
        List of games for the current week
    """
    data = await _fetch_espn(ESPN_NFL_SCOREBOARD)

    if not data:
        return []

    games = []
    for event in data.get("events", []):
        try:
            competition = event.get("competitions", [{}])[0]
            competitors = competition.get("competitors", [])

            if len(competitors) < 2:
                continue

            home_team = None
            away_team = None
            for team in competitors:
                if team.get("homeAway") == "home":
                    home_team = team
                else:
                    away_team = team

            if not home_team or not away_team:
                continue

            odds = None
            odds_data = competition.get("odds", [])
            if odds_data:
                odd = odds_data[0]
                odds = {
                    "spread": odd.get("spread"),
                    "over_under": odd.get("overUnder"),
                }

            broadcast = None
            broadcasts = competition.get("broadcasts", [])
            if broadcasts:
                broadcast = broadcasts[0].get("names", [""])[0] if broadcasts[0].get("names") else None

            games.append({
                "id": event.get("id"),
                "espn_id": event.get("id"),
                "name": event.get("name"),
                "status": event.get("status", {}).get("type", {}).get("description", ""),
                "status_detail": event.get("status", {}).get("type", {}).get("detail", ""),
                "game_date": event.get("date"),
                "venue": competition.get("venue", {}).get("fullName", ""),
                "week": event.get("week", {}).get("number"),
                "home_team": {
                    "id": home_team.get("team", {}).get("id"),
                    "name": home_team.get("team", {}).get("displayName", ""),
                    "abbreviation": home_team.get("team", {}).get("abbreviation", ""),
                    "score": int(home_team.get("score", 0)) if home_team.get("score") else None,
                    "record": home_team.get("records", [{}])[0].get("summary") if home_team.get("records") else None,
                },
                "away_team": {
                    "id": away_team.get("team", {}).get("id"),
                    "name": away_team.get("team", {}).get("displayName", ""),
                    "abbreviation": away_team.get("team", {}).get("abbreviation", ""),
                    "score": int(away_team.get("score", 0)) if away_team.get("score") else None,
                    "record": away_team.get("records", [{}])[0].get("summary") if away_team.get("records") else None,
                },
                "odds": odds,
                "broadcast": broadcast,
                "quarter": event.get("status", {}).get("period"),
                "time_remaining": event.get("status", {}).get("displayClock"),
                "is_live": event.get("status", {}).get("type", {}).get("state") == "in",
            })
        except (KeyError, IndexError, TypeError) as e:
            logger.warning(f"Error parsing game: {e}")
            continue

    return games


async def get_standings() -> Dict[str, Any]:
    """
    Get current NFL standings by conference and division.

    Returns:
        Dictionary with AFC and NFC standings
    """
    data = await _fetch_espn(ESPN_NFL_STANDINGS)

    if not data:
        return {"error": "Unable to fetch standings"}

    standings = {"AFC": {}, "NFC": {}}

    try:
        for child in data.get("children", []):
            conference = child.get("name", "")
            if conference not in ["AFC", "NFC"]:
                continue

            for division in child.get("children", []):
                division_name = division.get("name", "").replace(conference + " ", "")
                standings[conference][division_name] = []

                for team_standing in division.get("standings", {}).get("entries", []):
                    team = team_standing.get("team", {})
                    stats = {}

                    for stat in team_standing.get("stats", []):
                        stats[stat.get("name")] = stat.get("value")

                    standings[conference][division_name].append({
                        "team_id": team.get("id"),
                        "name": team.get("displayName"),
                        "abbreviation": team.get("abbreviation"),
                        "logo": team.get("logos", [{}])[0].get("href") if team.get("logos") else None,
                        "wins": int(stats.get("wins", 0)),
                        "losses": int(stats.get("losses", 0)),
                        "ties": int(stats.get("ties", 0)),
                        "win_pct": float(stats.get("winPercent", 0)),
                        "points_for": int(stats.get("pointsFor", 0)),
                        "points_against": int(stats.get("pointsAgainst", 0)),
                        "point_diff": int(stats.get("pointDifferential", 0)),
                        "division_record": stats.get("divisionRecord"),
                        "conference_record": stats.get("conferenceRecord"),
                    })
    except (KeyError, IndexError) as e:
        logger.warning(f"Error parsing standings: {e}")

    return standings


async def get_team_info(team_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed team information.

    Args:
        team_id: ESPN team ID

    Returns:
        Team info dictionary
    """
    url = f"{ESPN_NFL_TEAMS}/{team_id}"
    data = await _fetch_espn(url)

    if not data or "team" not in data:
        return None

    team = data["team"]

    return {
        "id": team.get("id"),
        "name": team.get("displayName"),
        "short_name": team.get("shortDisplayName"),
        "abbreviation": team.get("abbreviation"),
        "location": team.get("location"),
        "color": team.get("color"),
        "alternate_color": team.get("alternateColor"),
        "logo": team.get("logos", [{}])[0].get("href") if team.get("logos") else None,
        "venue": team.get("franchise", {}).get("venue", {}).get("fullName"),
    }


async def get_team_schedule(team_id: str) -> List[Dict[str, Any]]:
    """
    Get schedule for a specific team.

    Args:
        team_id: ESPN team ID

    Returns:
        List of games
    """
    url = f"{ESPN_NFL_TEAMS}/{team_id}/schedule"
    data = await _fetch_espn(url)

    if not data:
        return []

    games = []
    for event in data.get("events", []):
        try:
            competition = event.get("competitions", [{}])[0]
            competitors = competition.get("competitors", [])

            if len(competitors) < 2:
                continue

            home_team = None
            away_team = None
            for team in competitors:
                if team.get("homeAway") == "home":
                    home_team = team
                else:
                    away_team = team

            # Safely parse scores (may be string, int, dict, or None)
            def safe_score(team_data):
                if not team_data:
                    return None
                score = team_data.get("score")
                if score is None:
                    return None
                if isinstance(score, (int, float)):
                    return int(score)
                if isinstance(score, str) and score.isdigit():
                    return int(score)
                return None

            games.append({
                "id": event.get("id"),
                "name": event.get("name"),
                "status": event.get("status", {}).get("type", {}).get("description", ""),
                "game_date": event.get("date"),
                "week": event.get("week", {}).get("number"),
                "home_team": {
                    "name": home_team.get("team", {}).get("displayName", "") if home_team else "",
                    "score": safe_score(home_team),
                },
                "away_team": {
                    "name": away_team.get("team", {}).get("displayName", "") if away_team else "",
                    "score": safe_score(away_team),
                },
            })
        except (KeyError, IndexError, TypeError) as e:
            logger.warning(f"Error parsing schedule game: {e}")
            continue

    return games


async def refresh_nfl_data(db) -> Dict[str, Any]:
    """
    Refresh NFL data in the database.

    Args:
        db: Database session

    Returns:
        Summary of refreshed data
    """
    from app.db import NFLTeam, NFLGame

    result = {
        "teams": 0,
        "games": 0,
    }

    # Refresh teams
    teams = await get_teams()
    for team_data in teams:
        try:
            espn_id = team_data.get("espn_id")
            if not espn_id:
                continue

            existing = db.query(NFLTeam).filter(NFLTeam.espn_id == espn_id).first()

            if existing:
                existing.name = team_data.get("name", existing.name)
                existing.short_name = team_data.get("short_name", existing.short_name)
                existing.abbreviation = team_data.get("abbreviation", existing.abbreviation)
                existing.logo_url = team_data.get("logo_url", existing.logo_url)
            else:
                new_team = NFLTeam(
                    espn_id=espn_id,
                    name=team_data.get("name", ""),
                    short_name=team_data.get("short_name", ""),
                    abbreviation=team_data.get("abbreviation", ""),
                    location=team_data.get("location", ""),
                    logo_url=team_data.get("logo_url"),
                )
                db.add(new_team)

            result["teams"] += 1
        except Exception as e:
            logger.warning(f"Error storing team: {e}")

    db.commit()

    # Refresh current week games
    games = await get_current_week_games()
    for game_data in games:
        try:
            espn_id = game_data.get("espn_id")
            if not espn_id:
                continue

            existing = db.query(NFLGame).filter(NFLGame.espn_id == espn_id).first()

            game_date = None
            if game_data.get("game_date"):
                try:
                    game_date = datetime.fromisoformat(game_data["game_date"].replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass

            if existing:
                existing.status = game_data.get("status", existing.status)
                existing.home_score = game_data.get("home_team", {}).get("score")
                existing.away_score = game_data.get("away_team", {}).get("score")
            else:
                odds = game_data.get("odds") or {}
                new_game = NFLGame(
                    espn_id=espn_id,
                    status=game_data.get("status", "Scheduled"),
                    game_date=game_date,
                    venue=game_data.get("venue"),
                    week=game_data.get("week"),
                    home_team_name=game_data.get("home_team", {}).get("name", ""),
                    home_score=game_data.get("home_team", {}).get("score"),
                    away_team_name=game_data.get("away_team", {}).get("name", ""),
                    away_score=game_data.get("away_team", {}).get("score"),
                    spread=odds.get("spread"),
                    over_under=odds.get("over_under"),
                    broadcast=game_data.get("broadcast"),
                )
                db.add(new_game)

            result["games"] += 1
        except Exception as e:
            logger.warning(f"Error storing game: {e}")

    db.commit()

    return result


# NFL Team ESPN IDs for rest day lookups
NFL_TEAM_ESPN_IDS = {
    "Arizona Cardinals": "22",
    "Atlanta Falcons": "1",
    "Baltimore Ravens": "33",
    "Buffalo Bills": "2",
    "Carolina Panthers": "29",
    "Chicago Bears": "3",
    "Cincinnati Bengals": "4",
    "Cleveland Browns": "5",
    "Dallas Cowboys": "6",
    "Denver Broncos": "7",
    "Detroit Lions": "8",
    "Green Bay Packers": "9",
    "Houston Texans": "34",
    "Indianapolis Colts": "11",
    "Jacksonville Jaguars": "30",
    "Kansas City Chiefs": "12",
    "Las Vegas Raiders": "13",
    "Los Angeles Chargers": "24",
    "Los Angeles Rams": "14",
    "Miami Dolphins": "15",
    "Minnesota Vikings": "16",
    "New England Patriots": "17",
    "New Orleans Saints": "18",
    "New York Giants": "19",
    "New York Jets": "20",
    "Philadelphia Eagles": "21",
    "Pittsburgh Steelers": "23",
    "San Francisco 49ers": "25",
    "Seattle Seahawks": "26",
    "Tampa Bay Buccaneers": "27",
    "Tennessee Titans": "10",
    "Washington Commanders": "28",
}


async def calculate_rest_days(team_name: str, game_date: date) -> int:
    """
    Calculate days of rest for an NFL team before a game.

    Args:
        team_name: NFL team name (e.g., "Pittsburgh Steelers")
        game_date: Date of the upcoming game

    Returns:
        Number of rest days (-1 if unable to calculate)

    NFL Rest Day Guide:
    - Normal week (Sunday to Sunday): 7 days
    - Thursday Night Football after Sunday: 4 days
    - Monday Night Football to Sunday: 6 days
    - MNF to Thursday: 3 days (rare)
    - Bye week: 13-14 days
    """
    # Find team ESPN ID
    team_id = None
    team_lower = team_name.lower()
    for name, espn_id in NFL_TEAM_ESPN_IDS.items():
        if team_lower in name.lower() or name.lower() in team_lower:
            team_id = espn_id
            break

    if not team_id:
        logger.warning(f"Could not find ESPN ID for NFL team: {team_name}")
        return -1

    try:
        # Get team schedule
        schedule = await get_team_schedule(team_id)

        if not schedule:
            logger.warning(f"No schedule found for {team_name}")
            return -1

        # Parse game dates and find last game before target date
        game_dates = []
        for game in schedule:
            game_date_str = game.get("game_date")
            # Accept any game with a valid date
            if game_date_str:
                try:
                    parsed = datetime.fromisoformat(game_date_str.replace("Z", "+00:00"))
                    game_dates.append(parsed.date())
                except (ValueError, TypeError):
                    continue

        # Find most recent game before target date
        previous_games = [d for d in game_dates if d < game_date]

        if not previous_games:
            return -1  # No previous games (might be week 1)

        last_game_date = max(previous_games)
        rest_days = (game_date - last_game_date).days - 1

        logger.info(f"NFL rest days for {team_name}: {rest_days} (last game: {last_game_date})")

        return max(rest_days, 0)

    except Exception as e:
        logger.error(f"Error calculating NFL rest days for {team_name}: {e}")
        return -1


def get_nfl_team_id(team_name: str) -> Optional[str]:
    """Get ESPN team ID from team name."""
    team_lower = team_name.lower()
    for name, espn_id in NFL_TEAM_ESPN_IDS.items():
        if team_lower in name.lower() or name.lower() in team_lower:
            return espn_id
    return None
