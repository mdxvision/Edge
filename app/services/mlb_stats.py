"""
MLB Stats API Integration Service

Uses the official MLB Stats API (https://statsapi.mlb.com) - No API key required.
Documentation: https://github.com/toddrob99/MLB-StatsAPI
"""

import httpx
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

MLB_API_BASE = "https://statsapi.mlb.com/api/v1"

# MLB Team ID to abbreviation mapping
MLB_TEAM_ABBREVS = {
    108: "LAA", 109: "ARI", 110: "BAL", 111: "BOS", 112: "CHC",
    113: "CIN", 114: "CLE", 115: "COL", 116: "DET", 117: "HOU",
    118: "KC", 119: "LAD", 120: "WSH", 121: "NYM", 133: "OAK",
    134: "PIT", 135: "SD", 136: "SEA", 137: "SF", 138: "STL",
    139: "TB", 140: "TEX", 141: "TOR", 142: "MIN", 143: "PHI",
    144: "ATL", 145: "CWS", 146: "MIA", 147: "NYY", 158: "MIL"
}

# Ballpark factors (runs, HR, hits) - higher = more offense
BALLPARK_FACTORS = {
    "Coors Field": {"runs": 1.35, "hr": 1.30, "hits": 1.20},
    "Great American Ball Park": {"runs": 1.12, "hr": 1.25, "hits": 1.05},
    "Fenway Park": {"runs": 1.08, "hr": 0.95, "hits": 1.10},
    "Yankee Stadium": {"runs": 1.05, "hr": 1.15, "hits": 1.00},
    "Citizens Bank Park": {"runs": 1.05, "hr": 1.10, "hits": 1.02},
    "Globe Life Field": {"runs": 1.03, "hr": 1.08, "hits": 1.00},
    "Wrigley Field": {"runs": 1.02, "hr": 1.05, "hits": 1.00},
    "Dodger Stadium": {"runs": 0.95, "hr": 0.98, "hits": 0.97},
    "Oracle Park": {"runs": 0.90, "hr": 0.80, "hits": 0.95},
    "Petco Park": {"runs": 0.92, "hr": 0.88, "hits": 0.95},
    "Tropicana Field": {"runs": 0.93, "hr": 0.90, "hits": 0.96},
    "T-Mobile Park": {"runs": 0.95, "hr": 0.92, "hits": 0.97},
    "Oakland Coliseum": {"runs": 0.93, "hr": 0.88, "hits": 0.95},
    "loanDepot park": {"runs": 0.95, "hr": 0.90, "hits": 0.97},
    "Busch Stadium": {"runs": 0.97, "hr": 0.95, "hits": 0.98},
    "Target Field": {"runs": 1.00, "hr": 1.02, "hits": 1.00},
    "Progressive Field": {"runs": 0.98, "hr": 1.00, "hits": 0.99},
    "Comerica Park": {"runs": 0.95, "hr": 0.92, "hits": 0.97},
    "Kauffman Stadium": {"runs": 1.00, "hr": 1.02, "hits": 1.00},
    "Angel Stadium": {"runs": 0.98, "hr": 1.00, "hits": 0.99},
    "Minute Maid Park": {"runs": 1.03, "hr": 1.08, "hits": 1.01},
    "Chase Field": {"runs": 1.05, "hr": 1.08, "hits": 1.02},
    "Rogers Centre": {"runs": 1.02, "hr": 1.05, "hits": 1.00},
    "Nationals Park": {"runs": 0.98, "hr": 1.00, "hits": 0.99},
    "Citi Field": {"runs": 0.95, "hr": 0.92, "hits": 0.97},
    "PNC Park": {"runs": 0.95, "hr": 0.90, "hits": 0.97},
    "Guaranteed Rate Field": {"runs": 1.03, "hr": 1.08, "hits": 1.00},
    "American Family Field": {"runs": 1.02, "hr": 1.05, "hits": 1.00},
    "Truist Park": {"runs": 1.00, "hr": 1.02, "hits": 1.00}
}


async def _make_request(endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
    """Make an async request to the MLB Stats API."""
    url = f"{MLB_API_BASE}/{endpoint}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"MLB API request failed: {e}")
        return None


def _make_request_sync(endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
    """Make a synchronous request to the MLB Stats API."""
    url = f"{MLB_API_BASE}/{endpoint}"
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"MLB API request failed: {e}")
        return None


async def get_teams() -> List[Dict[str, Any]]:
    """
    Get all MLB teams with their IDs and information.

    Returns:
        List of team dictionaries with id, name, abbreviation, league, division
    """
    data = await _make_request("teams", {"sportId": 1})  # sportId 1 = MLB
    if not data or "teams" not in data:
        return []

    teams = []
    for team in data["teams"]:
        if team.get("active", False):
            teams.append({
                "mlb_id": team["id"],
                "name": team["name"],
                "short_name": team.get("teamName", team["name"]),
                "abbreviation": team.get("abbreviation", MLB_TEAM_ABBREVS.get(team["id"], "")),
                "league": team.get("league", {}).get("name", ""),
                "division": team.get("division", {}).get("name", ""),
                "venue": team.get("venue", {}).get("name", ""),
                "first_year": team.get("firstYearOfPlay", "")
            })

    return teams


def get_teams_sync() -> List[Dict[str, Any]]:
    """Synchronous version of get_teams."""
    data = _make_request_sync("teams", {"sportId": 1})
    if not data or "teams" not in data:
        return []

    teams = []
    for team in data["teams"]:
        if team.get("active", False):
            teams.append({
                "mlb_id": team["id"],
                "name": team["name"],
                "short_name": team.get("teamName", team["name"]),
                "abbreviation": team.get("abbreviation", MLB_TEAM_ABBREVS.get(team["id"], "")),
                "league": team.get("league", {}).get("name", ""),
                "division": team.get("division", {}).get("name", ""),
                "venue": team.get("venue", {}).get("name", ""),
                "first_year": team.get("firstYearOfPlay", "")
            })

    return teams


async def get_team_stats(team_id: int, season: int = None) -> Dict[str, Any]:
    """
    Get comprehensive team statistics for a season.

    Args:
        team_id: MLB team ID
        season: Season year (defaults to current year)

    Returns:
        Dictionary with batting, pitching, and fielding stats
    """
    if season is None:
        season = datetime.now().year

    stats = {
        "team_id": team_id,
        "season": season,
        "batting": {},
        "pitching": {},
        "fielding": {}
    }

    # Get batting stats
    batting_data = await _make_request(
        f"teams/{team_id}/stats",
        {"stats": "season", "group": "hitting", "season": season}
    )
    if batting_data and "stats" in batting_data:
        for stat_group in batting_data["stats"]:
            if stat_group.get("splits"):
                split = stat_group["splits"][0].get("stat", {})
                stats["batting"] = {
                    "games_played": split.get("gamesPlayed", 0),
                    "at_bats": split.get("atBats", 0),
                    "runs": split.get("runs", 0),
                    "hits": split.get("hits", 0),
                    "doubles": split.get("doubles", 0),
                    "triples": split.get("triples", 0),
                    "home_runs": split.get("homeRuns", 0),
                    "rbi": split.get("rbi", 0),
                    "stolen_bases": split.get("stolenBases", 0),
                    "walks": split.get("baseOnBalls", 0),
                    "strikeouts": split.get("strikeOuts", 0),
                    "batting_avg": float(split.get("avg", ".000").replace(".", "0.") if split.get("avg") else 0),
                    "obp": float(split.get("obp", ".000").replace(".", "0.") if split.get("obp") else 0),
                    "slg": float(split.get("slg", ".000").replace(".", "0.") if split.get("slg") else 0),
                    "ops": float(split.get("ops", ".000").replace(".", "0.") if split.get("ops") else 0)
                }

    # Get pitching stats
    pitching_data = await _make_request(
        f"teams/{team_id}/stats",
        {"stats": "season", "group": "pitching", "season": season}
    )
    if pitching_data and "stats" in pitching_data:
        for stat_group in pitching_data["stats"]:
            if stat_group.get("splits"):
                split = stat_group["splits"][0].get("stat", {})
                stats["pitching"] = {
                    "games_played": split.get("gamesPlayed", 0),
                    "wins": split.get("wins", 0),
                    "losses": split.get("losses", 0),
                    "era": float(split.get("era", "0.00")) if split.get("era") else 0,
                    "innings_pitched": float(split.get("inningsPitched", "0.0")) if split.get("inningsPitched") else 0,
                    "hits_allowed": split.get("hits", 0),
                    "runs_allowed": split.get("runs", 0),
                    "earned_runs": split.get("earnedRuns", 0),
                    "home_runs_allowed": split.get("homeRuns", 0),
                    "walks": split.get("baseOnBalls", 0),
                    "strikeouts": split.get("strikeOuts", 0),
                    "whip": float(split.get("whip", "0.00")) if split.get("whip") else 0,
                    "avg_against": float(split.get("avg", ".000").replace(".", "0.") if split.get("avg") else 0)
                }

    # Get fielding stats
    fielding_data = await _make_request(
        f"teams/{team_id}/stats",
        {"stats": "season", "group": "fielding", "season": season}
    )
    if fielding_data and "stats" in fielding_data:
        for stat_group in fielding_data["stats"]:
            if stat_group.get("splits"):
                split = stat_group["splits"][0].get("stat", {})
                stats["fielding"] = {
                    "games_played": split.get("gamesPlayed", 0),
                    "total_chances": split.get("chances", 0),
                    "putouts": split.get("putOuts", 0),
                    "assists": split.get("assists", 0),
                    "errors": split.get("errors", 0),
                    "fielding_pct": float(split.get("fielding", ".000").replace(".", "0.") if split.get("fielding") else 0),
                    "double_plays": split.get("doublePlays", 0)
                }

    return stats


async def get_player_stats(player_id: int, season: int = None) -> Dict[str, Any]:
    """
    Get player statistics for a season.

    Args:
        player_id: MLB player ID
        season: Season year (defaults to current year)

    Returns:
        Dictionary with player info and stats
    """
    if season is None:
        season = datetime.now().year

    # Get player info
    player_data = await _make_request(f"people/{player_id}")
    if not player_data or "people" not in player_data:
        return {}

    player_info = player_data["people"][0]
    result = {
        "player_id": player_id,
        "name": player_info.get("fullName", ""),
        "position": player_info.get("primaryPosition", {}).get("abbreviation", ""),
        "team": player_info.get("currentTeam", {}).get("name", ""),
        "team_id": player_info.get("currentTeam", {}).get("id"),
        "bats": player_info.get("batSide", {}).get("code", ""),
        "throws": player_info.get("pitchHand", {}).get("code", ""),
        "age": player_info.get("currentAge"),
        "season": season,
        "batting": {},
        "pitching": {}
    }

    # Get batting stats
    batting_data = await _make_request(
        f"people/{player_id}/stats",
        {"stats": "season", "group": "hitting", "season": season}
    )
    if batting_data and "stats" in batting_data:
        for stat_group in batting_data["stats"]:
            if stat_group.get("splits"):
                split = stat_group["splits"][0].get("stat", {})
                result["batting"] = {
                    "games": split.get("gamesPlayed", 0),
                    "at_bats": split.get("atBats", 0),
                    "runs": split.get("runs", 0),
                    "hits": split.get("hits", 0),
                    "doubles": split.get("doubles", 0),
                    "triples": split.get("triples", 0),
                    "home_runs": split.get("homeRuns", 0),
                    "rbi": split.get("rbi", 0),
                    "stolen_bases": split.get("stolenBases", 0),
                    "walks": split.get("baseOnBalls", 0),
                    "strikeouts": split.get("strikeOuts", 0),
                    "avg": split.get("avg", ".000"),
                    "obp": split.get("obp", ".000"),
                    "slg": split.get("slg", ".000"),
                    "ops": split.get("ops", ".000")
                }

    # Get pitching stats (for pitchers)
    pitching_data = await _make_request(
        f"people/{player_id}/stats",
        {"stats": "season", "group": "pitching", "season": season}
    )
    if pitching_data and "stats" in pitching_data:
        for stat_group in pitching_data["stats"]:
            if stat_group.get("splits"):
                split = stat_group["splits"][0].get("stat", {})
                result["pitching"] = {
                    "games": split.get("gamesPlayed", 0),
                    "games_started": split.get("gamesStarted", 0),
                    "wins": split.get("wins", 0),
                    "losses": split.get("losses", 0),
                    "saves": split.get("saves", 0),
                    "era": split.get("era", "0.00"),
                    "innings_pitched": split.get("inningsPitched", "0.0"),
                    "hits_allowed": split.get("hits", 0),
                    "runs_allowed": split.get("runs", 0),
                    "earned_runs": split.get("earnedRuns", 0),
                    "home_runs_allowed": split.get("homeRuns", 0),
                    "walks": split.get("baseOnBalls", 0),
                    "strikeouts": split.get("strikeOuts", 0),
                    "whip": split.get("whip", "0.00"),
                    "k_per_9": split.get("strikeoutsPer9Inn", "0.00"),
                    "bb_per_9": split.get("walksPer9Inn", "0.00")
                }

    return result


async def get_pitcher_game_logs(player_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get recent game logs for a pitcher.

    Args:
        player_id: MLB player ID
        limit: Number of recent games to return

    Returns:
        List of game log entries
    """
    season = datetime.now().year
    data = await _make_request(
        f"people/{player_id}/stats",
        {"stats": "gameLog", "group": "pitching", "season": season}
    )

    if not data or "stats" not in data:
        return []

    game_logs = []
    for stat_group in data["stats"]:
        if stat_group.get("splits"):
            for split in stat_group["splits"][:limit]:
                stat = split.get("stat", {})
                game_logs.append({
                    "date": split.get("date", ""),
                    "opponent": split.get("opponent", {}).get("name", ""),
                    "is_home": split.get("isHome", False),
                    "result": split.get("stat", {}).get("note", ""),
                    "innings_pitched": stat.get("inningsPitched", "0.0"),
                    "hits_allowed": stat.get("hits", 0),
                    "runs_allowed": stat.get("runs", 0),
                    "earned_runs": stat.get("earnedRuns", 0),
                    "walks": stat.get("baseOnBalls", 0),
                    "strikeouts": stat.get("strikeOuts", 0),
                    "home_runs_allowed": stat.get("homeRuns", 0),
                    "pitches": stat.get("numberOfPitches", 0),
                    "strikes": stat.get("strikes", 0),
                    "game_score": stat.get("gameScore", 0)
                })

    return game_logs


async def get_schedule(start_date: date = None, end_date: date = None, team_id: int = None) -> List[Dict[str, Any]]:
    """
    Get MLB game schedule.

    Args:
        start_date: Start date for schedule (defaults to today)
        end_date: End date for schedule (defaults to 7 days from start)
        team_id: Optional team ID to filter games

    Returns:
        List of scheduled games
    """
    if start_date is None:
        start_date = date.today()
    if end_date is None:
        end_date = start_date + timedelta(days=7)

    params = {
        "sportId": 1,
        "startDate": start_date.strftime("%Y-%m-%d"),
        "endDate": end_date.strftime("%Y-%m-%d"),
        "hydrate": "team,probablePitcher,venue,linescore"
    }
    if team_id:
        params["teamId"] = team_id

    data = await _make_request("schedule", params)
    if not data or "dates" not in data:
        return []

    games = []
    for date_entry in data["dates"]:
        for game in date_entry.get("games", []):
            home_team = game.get("teams", {}).get("home", {})
            away_team = game.get("teams", {}).get("away", {})

            games.append({
                "game_id": game.get("gamePk"),
                "game_date": date_entry.get("date"),
                "game_time": game.get("gameDate"),
                "status": game.get("status", {}).get("detailedState", ""),
                "venue": game.get("venue", {}).get("name", ""),
                "home_team": {
                    "id": home_team.get("team", {}).get("id"),
                    "name": home_team.get("team", {}).get("name", ""),
                    "probable_pitcher": home_team.get("probablePitcher", {}).get("fullName", "TBD"),
                    "probable_pitcher_id": home_team.get("probablePitcher", {}).get("id"),
                    "wins": home_team.get("leagueRecord", {}).get("wins", 0),
                    "losses": home_team.get("leagueRecord", {}).get("losses", 0)
                },
                "away_team": {
                    "id": away_team.get("team", {}).get("id"),
                    "name": away_team.get("team", {}).get("name", ""),
                    "probable_pitcher": away_team.get("probablePitcher", {}).get("fullName", "TBD"),
                    "probable_pitcher_id": away_team.get("probablePitcher", {}).get("id"),
                    "wins": away_team.get("leagueRecord", {}).get("wins", 0),
                    "losses": away_team.get("leagueRecord", {}).get("losses", 0)
                },
                "series_description": game.get("seriesDescription", ""),
                "series_game_number": game.get("seriesGameNumber", 1)
            })

    return games


async def get_game_results(season: int = None, team_id: int = None) -> List[Dict[str, Any]]:
    """
    Get historical game results for a season.

    Args:
        season: Season year (defaults to current year)
        team_id: Optional team ID to filter games

    Returns:
        List of completed game results
    """
    if season is None:
        season = datetime.now().year

    # Get the season date range
    params = {
        "sportId": 1,
        "season": season,
        "gameType": "R",  # Regular season
        "hydrate": "team,linescore,decisions"
    }
    if team_id:
        params["teamId"] = team_id

    # Need to query in chunks due to API limitations
    results = []

    # Regular season typically runs from late March to early October
    season_start = date(season, 3, 20)
    season_end = min(date(season, 10, 10), date.today())

    current_start = season_start
    while current_start < season_end:
        current_end = min(current_start + timedelta(days=30), season_end)

        params["startDate"] = current_start.strftime("%Y-%m-%d")
        params["endDate"] = current_end.strftime("%Y-%m-%d")

        data = await _make_request("schedule", params)
        if data and "dates" in data:
            for date_entry in data["dates"]:
                for game in date_entry.get("games", []):
                    if game.get("status", {}).get("detailedState") == "Final":
                        home = game.get("teams", {}).get("home", {})
                        away = game.get("teams", {}).get("away", {})
                        linescore = game.get("linescore", {})

                        results.append({
                            "game_id": game.get("gamePk"),
                            "game_date": date_entry.get("date"),
                            "season": season,
                            "home_team_id": home.get("team", {}).get("id"),
                            "home_team_name": home.get("team", {}).get("name", ""),
                            "away_team_id": away.get("team", {}).get("id"),
                            "away_team_name": away.get("team", {}).get("name", ""),
                            "home_score": home.get("score", 0),
                            "away_score": away.get("score", 0),
                            "innings": linescore.get("currentInning", 9),
                            "venue": game.get("venue", {}).get("name", ""),
                            "winning_pitcher": game.get("decisions", {}).get("winner", {}).get("fullName", ""),
                            "losing_pitcher": game.get("decisions", {}).get("loser", {}).get("fullName", ""),
                            "save_pitcher": game.get("decisions", {}).get("save", {}).get("fullName", "")
                        })

        current_start = current_end + timedelta(days=1)

    return results


async def get_standings(season: int = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get current MLB standings.

    Args:
        season: Season year (defaults to current year)

    Returns:
        Dictionary with standings by league/division
    """
    if season is None:
        season = datetime.now().year

    # Division IDs: 200=AL West, 201=AL East, 202=AL Central, 203=NL West, 204=NL East, 205=NL Central
    data = await _make_request("standings", {
        "leagueId": "103,104",  # AL and NL
        "season": season,
        "standingsTypes": "regularSeason"
    })

    if not data or "records" not in data:
        return {}

    standings = {}
    for record in data["records"]:
        division = record.get("division", {}).get("name", "Unknown")
        standings[division] = []

        for team_record in record.get("teamRecords", []):
            standings[division].append({
                "team_id": team_record.get("team", {}).get("id"),
                "team_name": team_record.get("team", {}).get("name", ""),
                "wins": team_record.get("wins", 0),
                "losses": team_record.get("losses", 0),
                "pct": team_record.get("winningPercentage", ".000"),
                "games_back": team_record.get("gamesBack", "-"),
                "wild_card_games_back": team_record.get("wildCardGamesBack", "-"),
                "streak": team_record.get("streak", {}).get("streakCode", ""),
                "runs_scored": team_record.get("runsScored", 0),
                "runs_allowed": team_record.get("runsAllowed", 0),
                "run_differential": team_record.get("runDifferential", 0),
                "home_record": f"{team_record.get('records', {}).get('splitRecords', [{}])[0].get('wins', 0)}-{team_record.get('records', {}).get('splitRecords', [{}])[0].get('losses', 0)}",
                "away_record": f"{team_record.get('records', {}).get('splitRecords', [{}])[1].get('wins', 0)}-{team_record.get('records', {}).get('splitRecords', [{}])[1].get('losses', 0)}",
                "last_10": team_record.get("records", {}).get("splitRecords", [{}])[-1].get("wins", 0) if team_record.get("records", {}).get("splitRecords") else 0
            })

    return standings


async def get_ballpark_factors(venue_name: str = None) -> Dict[str, Any]:
    """
    Get ballpark factors for run/HR/hit adjustments.

    Args:
        venue_name: Specific venue name (returns all if None)

    Returns:
        Dictionary of park factors
    """
    if venue_name:
        return BALLPARK_FACTORS.get(venue_name, {"runs": 1.00, "hr": 1.00, "hits": 1.00})
    return BALLPARK_FACTORS


async def get_roster(team_id: int) -> List[Dict[str, Any]]:
    """
    Get current roster for a team.

    Args:
        team_id: MLB team ID

    Returns:
        List of players on the roster
    """
    data = await _make_request(f"teams/{team_id}/roster", {"rosterType": "active"})
    if not data or "roster" not in data:
        return []

    roster = []
    for player in data["roster"]:
        person = player.get("person", {})
        roster.append({
            "player_id": person.get("id"),
            "name": person.get("fullName", ""),
            "jersey_number": player.get("jerseyNumber", ""),
            "position": player.get("position", {}).get("abbreviation", ""),
            "status": player.get("status", {}).get("description", "Active")
        })

    return roster


async def search_players(name: str) -> List[Dict[str, Any]]:
    """
    Search for players by name.

    Args:
        name: Player name to search for

    Returns:
        List of matching players
    """
    data = await _make_request("people/search", {"names": name, "sportId": 1})
    if not data or "people" not in data:
        return []

    players = []
    for person in data["people"]:
        players.append({
            "player_id": person.get("id"),
            "name": person.get("fullName", ""),
            "position": person.get("primaryPosition", {}).get("abbreviation", ""),
            "team": person.get("currentTeam", {}).get("name", ""),
            "team_id": person.get("currentTeam", {}).get("id"),
            "active": person.get("active", False)
        })

    return players


# Database storage functions
def store_mlb_teams(db, teams: List[Dict[str, Any]]):
    """Store MLB teams in the database."""
    from app.db import Team

    for team_data in teams:
        existing = db.query(Team).filter(
            Team.sport == "MLB",
            Team.name == team_data["name"]
        ).first()

        if existing:
            existing.short_name = team_data["abbreviation"]
        else:
            team = Team(
                sport="MLB",
                name=team_data["name"],
                short_name=team_data["abbreviation"],
                rating=1500.0
            )
            db.add(team)

    db.commit()


def store_mlb_game(db, game_data: Dict[str, Any]):
    """Store an MLB game in the database."""
    from app.db import Game, Team
    from datetime import datetime

    # Find teams
    home_team = db.query(Team).filter(
        Team.sport == "MLB",
        Team.name == game_data["home_team"]["name"]
    ).first()

    away_team = db.query(Team).filter(
        Team.sport == "MLB",
        Team.name == game_data["away_team"]["name"]
    ).first()

    if not home_team or not away_team:
        return None

    # Check if game already exists
    game_time = datetime.fromisoformat(game_data["game_time"].replace("Z", "+00:00"))
    existing = db.query(Game).filter(
        Game.sport == "MLB",
        Game.home_team_id == home_team.id,
        Game.away_team_id == away_team.id,
        Game.start_time == game_time
    ).first()

    if existing:
        return existing

    game = Game(
        sport="MLB",
        home_team_id=home_team.id,
        away_team_id=away_team.id,
        start_time=game_time,
        venue=game_data.get("venue", ""),
        league="MLB"
    )
    db.add(game)
    db.commit()
    return game


async def refresh_mlb_data(db):
    """
    Refresh all MLB data - teams, schedule, and standings.
    Called by the scheduler.
    """
    logger.info("Starting MLB data refresh...")

    # Refresh teams
    teams = await get_teams()
    if teams:
        store_mlb_teams(db, teams)
        logger.info(f"Stored {len(teams)} MLB teams")

    # Refresh upcoming games
    games = await get_schedule()
    games_stored = 0
    for game_data in games:
        if store_mlb_game(db, game_data):
            games_stored += 1
    logger.info(f"Stored {games_stored} upcoming MLB games")

    # Get standings
    standings = await get_standings()
    logger.info(f"Retrieved standings for {len(standings)} divisions")

    return {
        "teams": len(teams),
        "games": games_stored,
        "divisions": len(standings)
    }
