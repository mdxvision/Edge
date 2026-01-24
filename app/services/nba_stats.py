"""
NBA Stats API Integration Service

Uses the nba_api library to access NBA.com stats data.
"""

from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

from nba_api.stats.static import teams as nba_teams_static
from nba_api.stats.static import players as nba_players_static
from nba_api.stats.endpoints import (
    leaguegamefinder,
    teamgamelog,
    playergamelog,
    leaguestandings,
    teamdashboardbygeneralsplits,
    playerdashboardbygeneralsplits,
    commonteamroster,
    leaguedashteamstats,
    leaguedashplayerstats,
    scoreboardv2
)

from app.utils.logging import get_logger

logger = get_logger(__name__)

def get_live_nba_scores() -> List[Dict[str, Any]]:
    """
    Fetches active game data including current period and live scores.
    """
    logger.debug("Fetching live NBA scores from NBA API")
    try:
        # ScoreboardV2 is better for high-level live status than static game logs
        sb = scoreboardv2.ScoreboardV2(league_id="00")
        line_score = sb.line_score.get_data_frame()
        game_header = sb.game_header.get_data_frame()
        
        live_games = []
        for _, game in game_header.iterrows():
            status = game.get("GAME_STATUS_TEXT", "")
            # Only process games that are actually live or just finished
            # Qtr = Live, Half = Halftime, Final = Finished
            if "Qtr" in status or "Half" in status or "Final" in status:
                game_id = game.get("GAME_ID")
                
                # Filter line_score for this specific game
                game_scores = line_score[line_score['GAME_ID'] == game_id]
                
                if not game_scores.empty:
                    home_team_id = game.get("HOME_TEAM_ID")
                    away_team_id = game.get("VISITOR_TEAM_ID")
                    
                    home_rows = game_scores[game_scores['TEAM_ID'] == home_team_id]
                    away_rows = game_scores[game_scores['TEAM_ID'] == away_team_id]
                    
                    if not home_rows.empty and not away_rows.empty:
                        home_score = int(home_rows['PTS'].values[0])
                        away_score = int(away_rows['PTS'].values[0])
                        
                        live_games.append({
                            "game_id": game_id,
                            "status": status,
                            "home_score": home_score,
                            "away_score": away_score,
                            "home_team_id": int(home_team_id),
                            "away_team_id": int(away_team_id),
                            "last_update": datetime.now().isoformat()
                        })
        logger.info(f"Fetched {len(live_games)} live NBA games")
        return live_games
    except Exception as e:
        logger.error(f"Live NBA score fetch failed: {e}", exc_info=True)
        return []

# NBA Team city coordinates for travel distance calculation
NBA_TEAM_COORDS = {
    "ATL": (33.7573, -84.3963),    # Atlanta Hawks
    "BOS": (42.3662, -71.0621),    # Boston Celtics
    "BKN": (40.6826, -73.9754),    # Brooklyn Nets
    "CHA": (35.2251, -80.8392),    # Charlotte Hornets
    "CHI": (41.8807, -87.6742),    # Chicago Bulls
    "CLE": (41.4965, -81.6882),    # Cleveland Cavaliers
    "DAL": (32.7905, -96.8103),    # Dallas Mavericks
    "DEN": (39.7487, -105.0077),   # Denver Nuggets
    "DET": (42.3410, -83.0552),    # Detroit Pistons
    "GSW": (37.7680, -122.3877),   # Golden State Warriors
    "HOU": (29.7508, -95.3621),    # Houston Rockets
    "IND": (39.7640, -86.1555),    # Indiana Pacers
    "LAC": (34.0430, -118.2673),   # LA Clippers
    "LAL": (34.0430, -118.2673),   # LA Lakers
    "MEM": (35.1382, -90.0506),    # Memphis Grizzlies
    "MIA": (25.7814, -80.1870),    # Miami Heat
    "MIL": (43.0451, -87.9173),    # Milwaukee Bucks
    "MIN": (44.9795, -93.2760),    # Minnesota Timberwolves
    "NOP": (29.9490, -90.0821),    # New Orleans Pelicans
    "NYK": (40.7505, -73.9934),    # New York Knicks
    "OKC": (35.4634, -97.5151),    # Oklahoma City Thunder
    "ORL": (28.5392, -81.3839),    # Orlando Magic
    "PHI": (39.9012, -75.1720),    # Philadelphia 76ers
    "PHX": (33.4457, -112.0712),   # Phoenix Suns
    "POR": (45.5316, -122.6668),   # Portland Trail Blazers
    "SAC": (38.5802, -121.4997),   # Sacramento Kings
    "SAS": (29.4270, -98.4375),    # San Antonio Spurs
    "TOR": (43.6435, -79.3791),    # Toronto Raptors
    "UTA": (40.7683, -111.9011),   # Utah Jazz
    "WAS": (38.8981, -77.0209)     # Washington Wizards
}


def _calculate_distance(coord1: tuple, coord2: tuple) -> float:
    """Calculate approximate distance in miles between two coordinates."""
    import math
    lat1, lon1 = coord1
    lat2, lon2 = coord2

    # Haversine formula
    R = 3959  # Earth's radius in miles
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c


def get_teams() -> List[Dict[str, Any]]:
    """
    Get all NBA teams with their information.

    Returns:
        List of team dictionaries
    """
    teams = nba_teams_static.get_teams()
    return [
        {
            "nba_id": team["id"],
            "name": team["full_name"],
            "short_name": team["nickname"],
            "abbreviation": team["abbreviation"],
            "city": team["city"],
            "state": team.get("state", ""),
            "year_founded": team.get("year_founded", 0)
        }
        for team in teams
    ]


def get_team_by_abbreviation(abbreviation: str) -> Optional[Dict[str, Any]]:
    """Get team info by abbreviation."""
    teams = nba_teams_static.find_teams_by_abbreviation(abbreviation)
    if teams:
        team = teams[0]
        return {
            "nba_id": team["id"],
            "name": team["full_name"],
            "short_name": team["nickname"],
            "abbreviation": team["abbreviation"],
            "city": team["city"]
        }
    return None


def get_team_stats(team_id: int, season: str = None) -> Dict[str, Any]:
    """
    Get comprehensive team statistics for a season.

    Args:
        team_id: NBA team ID
        season: Season string like "2024-25" (defaults to current)

    Returns:
        Dictionary with offensive, defensive, and advanced stats
    """
    if season is None:
        # Determine current season
        now = datetime.now()
        year = now.year if now.month >= 10 else now.year - 1
        season = f"{year}-{str(year + 1)[-2:]}"

    try:
        # Get team dashboard stats
        dashboard = teamdashboardbygeneralsplits.TeamDashboardByGeneralSplits(
            team_id=team_id,
            season=season,
            season_type_all_star="Regular Season"
        )

        overall = dashboard.overall_team_dashboard.get_data_frame()

        if overall.empty:
            return {"team_id": team_id, "season": season, "error": "No data available"}

        row = overall.iloc[0]

        return {
            "team_id": team_id,
            "season": season,
            "games_played": int(row.get("GP", 0)),
            "wins": int(row.get("W", 0)),
            "losses": int(row.get("L", 0)),
            "win_pct": float(row.get("W_PCT", 0)),
            "offense": {
                "points_per_game": float(row.get("PTS", 0)) / max(int(row.get("GP", 1)), 1),
                "field_goal_pct": float(row.get("FG_PCT", 0)) * 100,
                "three_point_pct": float(row.get("FG3_PCT", 0)) * 100,
                "free_throw_pct": float(row.get("FT_PCT", 0)) * 100,
                "offensive_rebounds": float(row.get("OREB", 0)) / max(int(row.get("GP", 1)), 1),
                "assists_per_game": float(row.get("AST", 0)) / max(int(row.get("GP", 1)), 1),
                "turnovers_per_game": float(row.get("TOV", 0)) / max(int(row.get("GP", 1)), 1)
            },
            "defense": {
                "defensive_rebounds": float(row.get("DREB", 0)) / max(int(row.get("GP", 1)), 1),
                "steals_per_game": float(row.get("STL", 0)) / max(int(row.get("GP", 1)), 1),
                "blocks_per_game": float(row.get("BLK", 0)) / max(int(row.get("GP", 1)), 1)
            },
            "advanced": {
                "plus_minus": float(row.get("PLUS_MINUS", 0)),
                "net_rating": float(row.get("PLUS_MINUS", 0)) / max(int(row.get("GP", 1)), 1)
            }
        }

    except Exception as e:
        logger.error(f"Error fetching team stats for {team_id}: {e}")
        return {"team_id": team_id, "season": season, "error": str(e)}


def get_player_stats(player_id: int, season: str = None) -> Dict[str, Any]:
    """
    Get player statistics for a season.

    Args:
        player_id: NBA player ID
        season: Season string like "2024-25"

    Returns:
        Dictionary with per game and advanced stats
    """
    if season is None:
        now = datetime.now()
        year = now.year if now.month >= 10 else now.year - 1
        season = f"{year}-{str(year + 1)[-2:]}"

    try:
        dashboard = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(
            player_id=player_id,
            season=season,
            season_type_all_star="Regular Season"
        )

        overall = dashboard.overall_player_dashboard.get_data_frame()

        if overall.empty:
            return {"player_id": player_id, "season": season, "error": "No data available"}

        row = overall.iloc[0]
        gp = max(int(row.get("GP", 1)), 1)

        return {
            "player_id": player_id,
            "season": season,
            "games_played": int(row.get("GP", 0)),
            "games_started": int(row.get("GS", 0)) if "GS" in row else 0,
            "per_game": {
                "minutes": float(row.get("MIN", 0)) / gp,
                "points": float(row.get("PTS", 0)) / gp,
                "rebounds": float(row.get("REB", 0)) / gp,
                "assists": float(row.get("AST", 0)) / gp,
                "steals": float(row.get("STL", 0)) / gp,
                "blocks": float(row.get("BLK", 0)) / gp,
                "turnovers": float(row.get("TOV", 0)) / gp
            },
            "shooting": {
                "field_goal_pct": float(row.get("FG_PCT", 0)) * 100,
                "three_point_pct": float(row.get("FG3_PCT", 0)) * 100,
                "free_throw_pct": float(row.get("FT_PCT", 0)) * 100
            },
            "totals": {
                "points": int(row.get("PTS", 0)),
                "rebounds": int(row.get("REB", 0)),
                "assists": int(row.get("AST", 0)),
                "steals": int(row.get("STL", 0)),
                "blocks": int(row.get("BLK", 0))
            }
        }

    except Exception as e:
        logger.error(f"Error fetching player stats for {player_id}: {e}")
        return {"player_id": player_id, "season": season, "error": str(e)}


def get_schedule(team_id: int = None, start_date: date = None, end_date: date = None) -> List[Dict[str, Any]]:
    """
    Get NBA game schedule with rest day calculations.

    Args:
        team_id: Optional team ID to filter
        start_date: Start date (defaults to today)
        end_date: End date (defaults to 7 days from start)

    Returns:
        List of scheduled games with rest analysis
    """
    if start_date is None:
        start_date = date.today()
    if end_date is None:
        end_date = start_date + timedelta(days=7)

    # Build team ID to name mapping
    all_teams = nba_teams_static.get_teams()
    team_id_to_name = {team["id"]: team["full_name"] for team in all_teams}

    try:
        # Get today's scoreboard for immediate games
        games = []
        current_date = start_date

        while current_date <= end_date:
            try:
                sb = scoreboardv2.ScoreboardV2(
                    game_date=current_date.strftime("%Y-%m-%d"),
                    league_id="00"
                )
                game_header = sb.game_header.get_data_frame()

                for _, game in game_header.iterrows():
                    home_team_id = int(game.get("HOME_TEAM_ID", 0))
                    away_team_id = int(game.get("VISITOR_TEAM_ID", 0))

                    if team_id and team_id not in [home_team_id, away_team_id]:
                        continue

                    # Map team IDs to names
                    home_team_name = team_id_to_name.get(home_team_id, f"Team {home_team_id}")
                    away_team_name = team_id_to_name.get(away_team_id, f"Team {away_team_id}")

                    games.append({
                        "game_id": game.get("GAME_ID"),
                        "game_date": current_date.strftime("%Y-%m-%d"),
                        "game_status": game.get("GAME_STATUS_TEXT", ""),
                        "home_team": {
                            "id": home_team_id,
                            "name": home_team_name
                        },
                        "away_team": {
                            "id": away_team_id,
                            "name": away_team_name
                        },
                        "arena": game.get("ARENA_NAME", ""),
                        "national_tv": game.get("NATL_TV_BROADCASTER_ABBREVIATION", "")
                    })

            except Exception as e:
                logger.debug(f"No games found for {current_date}: {e}")

            current_date += timedelta(days=1)

        return games

    except Exception as e:
        logger.error(f"Error fetching schedule: {e}")
        return []


def get_standings(season: str = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get current NBA standings.

    Args:
        season: Season string like "2024-25"

    Returns:
        Dictionary with East and West conference standings
    """
    if season is None:
        now = datetime.now()
        year = now.year if now.month >= 10 else now.year - 1
        season = f"{year}-{str(year + 1)[-2:]}"

    try:
        standings = leaguestandings.LeagueStandings(
            league_id="00",
            season=season,
            season_type="Regular Season"
        )

        standings_df = standings.standings.get_data_frame()

        result = {"Eastern": [], "Western": []}

        for _, row in standings_df.iterrows():
            conference = row.get("Conference", "")
            team_data = {
                "team_id": int(row.get("TeamID", 0)),
                "team_name": row.get("TeamName", ""),
                "team_city": row.get("TeamCity", ""),
                "conference": conference,
                "conference_rank": int(row.get("ConferenceRank", 0)) if row.get("ConferenceRank") else 0,
                "wins": int(row.get("WINS", 0)),
                "losses": int(row.get("LOSSES", 0)),
                "win_pct": float(row.get("WinPCT", 0)),
                "home_record": row.get("HOME", "0-0"),
                "away_record": row.get("ROAD", "0-0"),
                "last_10": row.get("L10", "0-0"),
                "streak": row.get("CurrentStreak", ""),
                "points_pg": float(row.get("PointsPG", 0)) if row.get("PointsPG") else 0,
                "opp_points_pg": float(row.get("OppPointsPG", 0)) if row.get("OppPointsPG") else 0,
                "diff_points_pg": float(row.get("DiffPointsPG", 0)) if row.get("DiffPointsPG") else 0
            }

            if conference == "East":
                result["Eastern"].append(team_data)
            elif conference == "West":
                result["Western"].append(team_data)

        # Sort by conference rank
        result["Eastern"].sort(key=lambda x: x["conference_rank"])
        result["Western"].sort(key=lambda x: x["conference_rank"])

        return result

    except Exception as e:
        logger.error(f"Error fetching standings: {e}")
        return {"Eastern": [], "Western": [], "error": str(e)}


def calculate_rest_days(team_id: int, game_date: date, season: str = None) -> int:
    """
    Calculate days of rest for a team before a game.

    Args:
        team_id: NBA team ID
        game_date: Date of the game to check
        season: Season string

    Returns:
        Number of rest days (0 = back-to-back)
    """
    if season is None:
        year = game_date.year if game_date.month >= 10 else game_date.year - 1
        season = f"{year}-{str(year + 1)[-2:]}"

    try:
        # Get team's game log
        game_log = teamgamelog.TeamGameLog(
            team_id=team_id,
            season=season,
            season_type_all_star="Regular Season"
        )

        games_df = game_log.team_game_log.get_data_frame()

        if games_df.empty:
            return -1

        # Parse dates and find last game before target date
        games_df['GAME_DATE_PARSED'] = games_df['GAME_DATE'].apply(
            lambda x: datetime.strptime(x, "%b %d, %Y").date()
        )

        previous_games = games_df[games_df['GAME_DATE_PARSED'] < game_date]

        if previous_games.empty:
            return -1  # No previous games

        last_game_date = previous_games['GAME_DATE_PARSED'].max()
        rest_days = (game_date - last_game_date).days - 1

        return max(rest_days, 0)

    except Exception as e:
        logger.error(f"Error calculating rest days for team {team_id}: {e}")
        return -1


def flag_back_to_back(team_id: int, game_date: date, season: str = None) -> bool:
    """
    Check if a game is a back-to-back for a team.

    Args:
        team_id: NBA team ID
        game_date: Date to check
        season: Season string

    Returns:
        True if it's a back-to-back game
    """
    rest_days = calculate_rest_days(team_id, game_date, season)
    return rest_days == 0


def get_rest_analysis(team_id: int, game_date: date = None) -> Dict[str, Any]:
    """
    Get comprehensive rest analysis for a team.

    Args:
        team_id: NBA team ID
        game_date: Target game date (defaults to today)

    Returns:
        Rest analysis including B2B detection and travel
    """
    if game_date is None:
        game_date = date.today()

    year = game_date.year if game_date.month >= 10 else game_date.year - 1
    season = f"{year}-{str(year + 1)[-2:]}"

    rest_days = calculate_rest_days(team_id, game_date, season)
    is_b2b = rest_days == 0

    # Get team abbreviation for travel calculation
    teams = get_teams()
    team_abbrev = None
    for team in teams:
        if team["nba_id"] == team_id:
            team_abbrev = team["abbreviation"]
            break

    return {
        "team_id": team_id,
        "game_date": game_date.strftime("%Y-%m-%d"),
        "rest_days": rest_days,
        "is_back_to_back": is_b2b,
        "rest_advantage": "disadvantage" if is_b2b else ("advantage" if rest_days >= 2 else "neutral"),
        "fatigue_factor": 1.0 + (0.03 if is_b2b else 0) - (0.01 * min(rest_days, 3))  # Simple fatigue model
    }


def search_players(name: str) -> List[Dict[str, Any]]:
    """
    Search for NBA players by name.

    Args:
        name: Player name to search

    Returns:
        List of matching players
    """
    players = nba_players_static.find_players_by_full_name(name)
    return [
        {
            "player_id": p["id"],
            "name": p["full_name"],
            "is_active": p["is_active"]
        }
        for p in players
    ]


def get_roster(team_id: int, season: str = None) -> List[Dict[str, Any]]:
    """
    Get current roster for a team.

    Args:
        team_id: NBA team ID
        season: Season string

    Returns:
        List of players on the roster
    """
    if season is None:
        now = datetime.now()
        year = now.year if now.month >= 10 else now.year - 1
        season = f"{year}-{str(year + 1)[-2:]}"

    try:
        roster = commonteamroster.CommonTeamRoster(
            team_id=team_id,
            season=season
        )

        roster_df = roster.common_team_roster.get_data_frame()

        players = []
        for _, row in roster_df.iterrows():
            players.append({
                "player_id": int(row.get("PLAYER_ID", 0)),
                "name": row.get("PLAYER", ""),
                "jersey_number": row.get("NUM", ""),
                "position": row.get("POSITION", ""),
                "height": row.get("HEIGHT", ""),
                "weight": row.get("WEIGHT", ""),
                "age": row.get("AGE", 0),
                "experience": row.get("EXP", "R")
            })

        return players

    except Exception as e:
        logger.error(f"Error fetching roster for team {team_id}: {e}")
        return []


def get_league_leaders(season: str = None, stat_category: str = "PTS") -> List[Dict[str, Any]]:
    """
    Get league leaders for a statistical category.

    Args:
        season: Season string
        stat_category: Stat category (PTS, REB, AST, STL, BLK, etc.)

    Returns:
        List of league leaders
    """
    if season is None:
        now = datetime.now()
        year = now.year if now.month >= 10 else now.year - 1
        season = f"{year}-{str(year + 1)[-2:]}"

    try:
        leaders = leaguedashplayerstats.LeagueDashPlayerStats(
            season=season,
            season_type_all_star="Regular Season",
            per_mode_detailed="PerGame"
        )

        df = leaders.league_dash_player_stats.get_data_frame()

        if df.empty:
            return []

        # Sort by the requested stat category
        if stat_category in df.columns:
            df = df.sort_values(stat_category, ascending=False).head(20)

        result = []
        for _, row in df.iterrows():
            result.append({
                "player_id": int(row.get("PLAYER_ID", 0)),
                "player_name": row.get("PLAYER_NAME", ""),
                "team": row.get("TEAM_ABBREVIATION", ""),
                "games_played": int(row.get("GP", 0)),
                "minutes": float(row.get("MIN", 0)),
                "points": float(row.get("PTS", 0)),
                "rebounds": float(row.get("REB", 0)),
                "assists": float(row.get("AST", 0)),
                "steals": float(row.get("STL", 0)),
                "blocks": float(row.get("BLK", 0)),
                "fg_pct": float(row.get("FG_PCT", 0)) * 100,
                "fg3_pct": float(row.get("FG3_PCT", 0)) * 100
            })

        return result

    except Exception as e:
        logger.error(f"Error fetching league leaders: {e}")
        return []


# Database storage functions
def store_nba_teams(db, teams: List[Dict[str, Any]]):
    """Store NBA teams in the database."""
    from app.db import Team

    for team_data in teams:
        existing = db.query(Team).filter(
            Team.sport == "NBA",
            Team.name == team_data["name"]
        ).first()

        if existing:
            existing.short_name = team_data["abbreviation"]
        else:
            team = Team(
                sport="NBA",
                name=team_data["name"],
                short_name=team_data["abbreviation"],
                rating=1500.0
            )
            db.add(team)

    db.commit()


def store_nba_game(db, game_data: Dict[str, Any]):
    """Store an NBA game in the database."""
    from app.db import Game, Team
    from datetime import datetime

    # Find teams
    home_team = db.query(Team).filter(
        Team.sport == "NBA",
        Team.name == game_data["home_team"]["name"]
    ).first()

    away_team = db.query(Team).filter(
        Team.sport == "NBA",
        Team.name == game_data["away_team"]["name"]
    ).first()

    if not home_team or not away_team:
        return None

    game_date = datetime.strptime(game_data["game_date"], "%Y-%m-%d")

    # Check if game already exists
    existing = db.query(Game).filter(
        Game.sport == "NBA",
        Game.home_team_id == home_team.id,
        Game.away_team_id == away_team.id,
        Game.start_time == game_date
    ).first()

    if existing:
        if not existing.external_id and game_data.get("game_id"):
            existing.external_id = str(game_data.get("game_id"))
            db.commit()
        return existing

    game = Game(
        sport="NBA",
        home_team_id=home_team.id,
        away_team_id=away_team.id,
        start_time=game_date,
        venue=game_data.get("arena", ""),
        league="NBA",
        external_id=str(game_data.get("game_id", ""))
    )
    db.add(game)
    db.commit()
    return game


def refresh_nba_data(db):
    """
    Refresh all NBA data - teams, schedule, and standings.
    Called by the scheduler.
    """
    logger.info("Starting NBA data refresh...")

    # Refresh teams
    teams = get_teams()
    if teams:
        store_nba_teams(db, teams)
        logger.info(f"Stored {len(teams)} NBA teams")

    # Refresh upcoming games
    games = get_schedule()
    games_stored = 0
    for game_data in games:
        if store_nba_game(db, game_data):
            games_stored += 1
    logger.info(f"Stored {games_stored} upcoming NBA games")

    # Get standings
    standings = get_standings()
    east_count = len(standings.get("Eastern", []))
    west_count = len(standings.get("Western", []))
    logger.info(f"Retrieved standings for {east_count} Eastern and {west_count} Western teams")

    return {
        "teams": len(teams),
        "games": games_stored,
        "eastern_standings": east_count,
        "western_standings": west_count
    }
