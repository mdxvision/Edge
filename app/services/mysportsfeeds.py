"""
MySportsFeeds API Integration Service

Fetches real game scores for auto-settlement of picks.
API Documentation: https://www.mysportsfeeds.com/data-feeds/
"""

import os
import base64
import logging
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

# API Configuration
MYSPORTSFEEDS_API_KEY = os.environ.get("MYSPORTSFEEDS_API_KEY", "")
MYSPORTSFEEDS_BASE_URL = "https://api.mysportsfeeds.com/v2.1/pull"

# Sport key mappings
SPORT_KEYS = {
    "NFL": "nfl",
    "NBA": "nba",
    "MLB": "mlb",
    "NHL": "nhl",
    "NCAAF": "ncaafb",
    "NCAAB": "ncaab",
    "CBB": "ncaab"
}

# Season mappings (MySportsFeeds uses season format)
def get_current_season(sport: str) -> str:
    """Get current season identifier for sport"""
    now = datetime.utcnow()
    year = now.year
    month = now.month

    sport_upper = sport.upper()

    if sport_upper == "NFL":
        # NFL season spans Sep-Feb
        if month >= 9:
            return f"{year}-regular"
        elif month <= 2:
            return f"{year - 1}-regular"
        else:
            return f"{year - 1}-regular"  # Offseason

    elif sport_upper == "NBA":
        # NBA season spans Oct-Jun
        if month >= 10:
            return f"{year}-{year + 1}-regular"
        elif month <= 6:
            return f"{year - 1}-{year}-regular"
        else:
            return f"{year - 1}-{year}-regular"  # Offseason

    elif sport_upper == "MLB":
        # MLB season spans Mar-Oct
        return f"{year}-regular"

    elif sport_upper == "NHL":
        # NHL season spans Oct-Jun
        if month >= 10:
            return f"{year}-{year + 1}-regular"
        elif month <= 6:
            return f"{year - 1}-{year}-regular"
        else:
            return f"{year - 1}-{year}-regular"

    elif sport_upper in ["NCAAF"]:
        if month >= 8:
            return f"{year}-regular"
        else:
            return f"{year - 1}-regular"

    elif sport_upper in ["NCAAB", "CBB"]:
        if month >= 11:
            return f"{year}-{year + 1}-regular"
        elif month <= 4:
            return f"{year - 1}-{year}-regular"
        else:
            return f"{year - 1}-{year}-regular"

    return "current"


class MySportsFeedsService:
    """Service for fetching game data from MySportsFeeds API"""

    def __init__(self):
        self.api_key = MYSPORTSFEEDS_API_KEY
        self.base_url = MYSPORTSFEEDS_BASE_URL

    def _get_auth_header(self) -> Dict[str, str]:
        """Get Basic Auth header for API"""
        if not self.api_key:
            return {}

        # MySportsFeeds uses API key as username and "MYSPORTSFEEDS" as password
        credentials = f"{self.api_key}:MYSPORTSFEEDS"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {"Authorization": f"Basic {encoded}"}

    def is_configured(self) -> bool:
        """Check if API key is configured"""
        return bool(self.api_key)

    async def test_connection(self) -> Dict[str, Any]:
        """Test API connection"""
        if not self.api_key:
            return {
                "success": False,
                "error": "MYSPORTSFEEDS_API_KEY not configured"
            }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Test with a simple endpoint
                response = await client.get(
                    f"{self.base_url}/nfl/current/games.json",
                    headers=self._get_auth_header(),
                    params={"limit": 1}
                )

                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": "MySportsFeeds API connection successful",
                        "status_code": response.status_code
                    }
                elif response.status_code == 401:
                    return {
                        "success": False,
                        "error": "Invalid API key",
                        "status_code": response.status_code
                    }
                else:
                    return {
                        "success": False,
                        "error": f"API returned status {response.status_code}",
                        "status_code": response.status_code
                    }

        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "Connection timeout"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def get_games(
        self,
        sport: str,
        date: Optional[datetime] = None,
        days_back: int = 3
    ) -> List[Dict]:
        """
        Get games for a sport

        Args:
            sport: Sport key (NFL, NBA, MLB, etc.)
            date: Specific date (or None for recent)
            days_back: Days to look back for completed games

        Returns:
            List of game data
        """
        if not self.api_key:
            logger.warning("MySportsFeeds API key not configured")
            return []

        sport_key = SPORT_KEYS.get(sport.upper())
        if not sport_key:
            logger.warning(f"Unknown sport: {sport}")
            return []

        season = get_current_season(sport)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Build date range
                if date:
                    date_str = date.strftime("%Y%m%d")
                    params = {"date": date_str}
                else:
                    # Get games from last N days
                    end_date = datetime.utcnow()
                    start_date = end_date - timedelta(days=days_back)
                    params = {
                        "date": f"from-{start_date.strftime('%Y%m%d')}-to-{end_date.strftime('%Y%m%d')}"
                    }

                response = await client.get(
                    f"{self.base_url}/{sport_key}/{season}/games.json",
                    headers=self._get_auth_header(),
                    params=params
                )

                if response.status_code == 200:
                    data = response.json()
                    games = data.get("games", [])
                    return [self._parse_game(g, sport) for g in games]
                elif response.status_code == 204:
                    # No content - no games found
                    return []
                else:
                    logger.error(f"MySportsFeeds API error: {response.status_code}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching games: {str(e)}")
            return []

    async def get_completed_games(self, sport: str, days_back: int = 3) -> List[Dict]:
        """
        Get completed games for a sport

        Args:
            sport: Sport key
            days_back: Days to look back

        Returns:
            List of completed game data with scores
        """
        games = await self.get_games(sport, days_back=days_back)

        # Filter to completed games
        completed = []
        for game in games:
            if game.get("status") == "COMPLETED" and game.get("home_score") is not None:
                completed.append(game)

        return completed

    async def get_game_by_teams(
        self,
        sport: str,
        home_team: str,
        away_team: str,
        game_date: Optional[datetime] = None,
        days_range: int = 3
    ) -> Optional[Dict]:
        """
        Find a specific game by teams

        Args:
            sport: Sport key
            home_team: Home team name
            away_team: Away team name
            game_date: Expected game date
            days_range: Days to search around date

        Returns:
            Game data if found
        """
        games = await self.get_games(sport, date=game_date, days_back=days_range)

        home_lower = home_team.lower()
        away_lower = away_team.lower()

        for game in games:
            game_home = game.get("home_team", "").lower()
            game_away = game.get("away_team", "").lower()

            # Fuzzy matching
            home_match = (
                home_lower in game_home or
                game_home in home_lower or
                self._teams_match(home_lower, game_home)
            )
            away_match = (
                away_lower in game_away or
                game_away in away_lower or
                self._teams_match(away_lower, game_away)
            )

            if home_match and away_match:
                return game

        return None

    def _parse_game(self, game_data: Dict, sport: str) -> Dict:
        """Parse raw game data into standard format"""
        schedule = game_data.get("schedule", {})
        score = game_data.get("score", {})

        # Get team names
        home_team_data = schedule.get("homeTeam", {})
        away_team_data = schedule.get("awayTeam", {})

        home_team = home_team_data.get("name", home_team_data.get("abbreviation", "Unknown"))
        away_team = away_team_data.get("name", away_team_data.get("abbreviation", "Unknown"))

        # Get scores
        home_score = score.get("homeScoreTotal")
        away_score = score.get("awayScoreTotal")

        # Determine status
        played_status = schedule.get("playedStatus", "UNPLAYED")
        if played_status == "COMPLETED":
            status = "COMPLETED"
        elif played_status == "LIVE":
            status = "IN_PROGRESS"
        else:
            status = "SCHEDULED"

        # Parse game time
        start_time = schedule.get("startTime")
        game_time = None
        if start_time:
            try:
                game_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            except:
                pass

        result = {
            "game_id": str(schedule.get("id", "")),
            "sport": sport.upper(),
            "home_team": home_team,
            "away_team": away_team,
            "home_score": home_score,
            "away_score": away_score,
            "status": status,
            "game_time": game_time.isoformat() if game_time else None,
            "venue": schedule.get("venue", {}).get("name", "")
        }

        # Add calculated fields for completed games
        if status == "COMPLETED" and home_score is not None and away_score is not None:
            result["total"] = home_score + away_score
            result["spread"] = home_score - away_score  # Positive = home won

        return result

    def _teams_match(self, team1: str, team2: str) -> bool:
        """Check if team names match using common variations"""
        # Common team name aliases
        team_aliases = {
            "chiefs": ["kansas city", "kc"],
            "49ers": ["san francisco", "sf", "niners"],
            "lakers": ["los angeles lakers", "la lakers"],
            "celtics": ["boston"],
            "knicks": ["new york knicks", "ny knicks"],
            "cowboys": ["dallas"],
            "eagles": ["philadelphia", "philly"],
            "bills": ["buffalo"],
            "ravens": ["baltimore"],
            "packers": ["green bay", "gb"],
            "buccaneers": ["tampa bay", "bucs", "tampa"],
            "patriots": ["new england", "ne"],
            "bears": ["chicago"],
            "lions": ["detroit"],
            "vikings": ["minnesota"],
            "seahawks": ["seattle"],
            "rams": ["los angeles rams", "la rams"],
            "chargers": ["los angeles chargers", "la chargers"],
            "broncos": ["denver"],
            "raiders": ["las vegas", "lv"],
            "cardinals": ["arizona"],
            "giants": ["new york giants", "ny giants"],
            "jets": ["new york jets", "ny jets"],
            "dolphins": ["miami"],
            "saints": ["new orleans"],
            "falcons": ["atlanta"],
            "panthers": ["carolina"],
            "steelers": ["pittsburgh"],
            "browns": ["cleveland"],
            "bengals": ["cincinnati"],
            "titans": ["tennessee"],
            "colts": ["indianapolis", "indy"],
            "texans": ["houston"],
            "jaguars": ["jacksonville", "jags"],
            "commanders": ["washington"],
            "warriors": ["golden state", "gsw"],
            "clippers": ["la clippers"],
            "heat": ["miami heat"],
            "nets": ["brooklyn"],
            "rockets": ["houston rockets"],
            "spurs": ["san antonio"],
            "mavericks": ["dallas mavs", "mavs"],
            "suns": ["phoenix"],
            "bucks": ["milwaukee"],
            "sixers": ["philadelphia 76ers", "76ers"],
            "raptors": ["toronto"],
            "jazz": ["utah"],
            "nuggets": ["denver nuggets"],
            "pelicans": ["new orleans pelicans"],
            "timberwolves": ["minnesota timberwolves", "twolves"],
            "thunder": ["oklahoma city", "okc"],
            "grizzlies": ["memphis"],
            "hawks": ["atlanta hawks"],
            "hornets": ["charlotte"],
            "magic": ["orlando"],
            "pistons": ["detroit pistons"],
            "pacers": ["indiana"],
            "cavaliers": ["cleveland cavaliers", "cavs"],
            "bulls": ["chicago bulls"],
            "blazers": ["portland", "trail blazers"],
            "kings": ["sacramento"],
        }

        # Check word overlap
        words1 = set(team1.split())
        words2 = set(team2.split())
        if words1 & words2:
            return True

        # Check aliases
        for main_name, aliases in team_aliases.items():
            all_names = [main_name] + aliases
            team1_match = any(name in team1 for name in all_names)
            team2_match = any(name in team2 for name in all_names)
            if team1_match and team2_match:
                return True

        return False


def get_mysportsfeeds_service() -> MySportsFeedsService:
    """Get a MySportsFeedsService instance"""
    return MySportsFeedsService()
