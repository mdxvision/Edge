"""
Auto-Settlement Service

Polls for game results and automatically settles picks when games finish.
Uses MySportsFeeds API as primary source, with The Odds API as fallback.
"""

import os
import logging
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from sqlalchemy.orm import Session

from app.db import TrackedPick, SessionLocal
from app.services.edge_tracker import EdgeTracker
from app.services.mysportsfeeds import MySportsFeedsService, get_mysportsfeeds_service

logger = logging.getLogger(__name__)

# API Configuration
ODDS_API_KEY = os.environ.get("THE_ODDS_API_KEY", "")
ODDS_API_BASE = "https://api.the-odds-api.com/v4"

# Sport key mappings for The Odds API
SPORT_KEYS = {
    "NFL": "americanfootball_nfl",
    "NBA": "basketball_nba",
    "MLB": "baseball_mlb",
    "NHL": "icehockey_nhl",
    "NCAAF": "americanfootball_ncaaf",
    "NCAAB": "basketball_ncaab",
    "CBB": "basketball_ncaab"
}


class AutoSettler:
    """Auto-settlement service for tracked picks"""

    def __init__(self, db: Session):
        self.db = db
        self.edge_tracker = EdgeTracker(db)
        self.mysportsfeeds = get_mysportsfeeds_service()

    async def check_and_settle_pending(self) -> Dict:
        """
        Check all pending picks and settle completed games

        Returns:
            Dict with settlement results
        """
        # Get all pending picks
        pending_picks = self.db.query(TrackedPick).filter(
            TrackedPick.status == "pending"
        ).all()

        if not pending_picks:
            return {"message": "No pending picks to settle", "settled": 0}

        settled_count = 0
        errors = []
        settled_picks = []

        # Group picks by sport for efficient API calls
        picks_by_sport = {}
        for pick in pending_picks:
            sport = pick.sport.upper()
            if sport not in picks_by_sport:
                picks_by_sport[sport] = []
            picks_by_sport[sport].append(pick)

        # Process each sport
        for sport, picks in picks_by_sport.items():
            try:
                # Get completed games for this sport
                completed_games = await self._get_completed_games(sport)

                for pick in picks:
                    # Check if game is in completed games
                    game_result = self._find_game_result(
                        pick,
                        completed_games
                    )

                    if game_result:
                        try:
                            result = self._determine_pick_result(pick, game_result)

                            if result:
                                settlement = self.edge_tracker.settle_pick(
                                    pick_id=pick.id,
                                    result=result["result"],
                                    actual_score=result["score_string"],
                                    spread_result=result.get("spread_result"),
                                    total_result=result.get("total_result")
                                )

                                if "error" not in settlement:
                                    settled_count += 1
                                    settled_picks.append({
                                        "pick_id": pick.id,
                                        "pick": pick.pick,
                                        "result": result["result"],
                                        "score": result["score_string"]
                                    })
                        except Exception as e:
                            errors.append(f"Error settling pick {pick.id}: {str(e)}")

            except Exception as e:
                errors.append(f"Error fetching {sport} games: {str(e)}")

        return {
            "message": f"Settled {settled_count} picks",
            "settled": settled_count,
            "pending_remaining": len(pending_picks) - settled_count,
            "settled_picks": settled_picks,
            "errors": errors if errors else None
        }

    async def _get_completed_games(self, sport: str) -> List[Dict]:
        """
        Fetch completed games - tries MySportsFeeds first, then The Odds API

        Args:
            sport: Sport key (NFL, NBA, etc.)

        Returns:
            List of completed game data
        """
        # Try MySportsFeeds first (primary source)
        if self.mysportsfeeds.is_configured():
            try:
                msf_games = await self.mysportsfeeds.get_completed_games(sport, days_back=3)
                if msf_games:
                    logger.info(f"Got {len(msf_games)} completed {sport} games from MySportsFeeds")
                    # Convert to standard format expected by _find_game_result
                    return [self._convert_msf_game(g) for g in msf_games]
            except Exception as e:
                logger.error(f"MySportsFeeds error: {str(e)}")

        # Fallback to The Odds API
        if not ODDS_API_KEY:
            logger.warning("Neither MySportsFeeds nor THE_ODDS_API_KEY configured")
            return []

        sport_key = SPORT_KEYS.get(sport.upper())
        if not sport_key:
            logger.warning(f"Unknown sport: {sport}")
            return []

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{ODDS_API_BASE}/sports/{sport_key}/scores/",
                    params={
                        "apiKey": ODDS_API_KEY,
                        "daysFrom": 3  # Check last 3 days
                    }
                )

                if response.status_code == 200:
                    games = response.json()
                    # Filter to only completed games
                    completed = [g for g in games if g.get("completed", False)]
                    logger.info(f"Got {len(completed)} completed {sport} games from The Odds API")
                    return completed
                else:
                    logger.error(f"Odds API error: {response.status_code}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching scores: {str(e)}")
            return []

    def _convert_msf_game(self, msf_game: Dict) -> Dict:
        """Convert MySportsFeeds game format to The Odds API format for compatibility"""
        return {
            "id": msf_game.get("game_id"),
            "home_team": msf_game.get("home_team"),
            "away_team": msf_game.get("away_team"),
            "completed": msf_game.get("status") == "COMPLETED",
            "scores": [
                {
                    "name": msf_game.get("home_team"),
                    "score": str(msf_game.get("home_score", 0))
                },
                {
                    "name": msf_game.get("away_team"),
                    "score": str(msf_game.get("away_score", 0))
                }
            ]
        }

    def _find_game_result(
        self,
        pick: TrackedPick,
        completed_games: List[Dict]
    ) -> Optional[Dict]:
        """
        Find the game result that matches a pick

        Args:
            pick: The tracked pick
            completed_games: List of completed games from API

        Returns:
            Game result dict if found, None otherwise
        """
        for game in completed_games:
            home_team = game.get("home_team", "").lower()
            away_team = game.get("away_team", "").lower()

            pick_home = pick.home_team.lower()
            pick_away = pick.away_team.lower()

            # Fuzzy match team names (handle abbreviations, city names, etc.)
            home_match = (
                home_team in pick_home or
                pick_home in home_team or
                self._teams_match(home_team, pick_home)
            )
            away_match = (
                away_team in pick_away or
                pick_away in away_team or
                self._teams_match(away_team, pick_away)
            )

            if home_match and away_match:
                # Extract scores
                scores = game.get("scores", [])
                home_score = None
                away_score = None

                for score in scores:
                    if score.get("name", "").lower() == home_team:
                        home_score = int(score.get("score", 0))
                    elif score.get("name", "").lower() == away_team:
                        away_score = int(score.get("score", 0))

                if home_score is not None and away_score is not None:
                    return {
                        "home_team": game.get("home_team"),
                        "away_team": game.get("away_team"),
                        "home_score": home_score,
                        "away_score": away_score,
                        "total": home_score + away_score,
                        "spread": home_score - away_score  # Positive = home won
                    }

        return None

    def _teams_match(self, api_team: str, pick_team: str) -> bool:
        """Check if team names match using common variations"""
        # Common team name mappings
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
            "buccaneers": ["tampa bay", "bucs"],
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
        }

        # Check exact word match
        api_words = set(api_team.split())
        pick_words = set(pick_team.split())

        if api_words & pick_words:
            return True

        # Check aliases
        for main_name, aliases in team_aliases.items():
            if main_name in api_team or main_name in pick_team:
                for alias in aliases:
                    if alias in api_team or alias in pick_team:
                        return True
            for alias in aliases:
                if alias in api_team and (main_name in pick_team or any(a in pick_team for a in aliases)):
                    return True

        return False

    def _determine_pick_result(
        self,
        pick: TrackedPick,
        game_result: Dict
    ) -> Optional[Dict]:
        """
        Determine if a pick won, lost, or pushed

        Args:
            pick: The tracked pick
            game_result: The game result data

        Returns:
            Dict with result details
        """
        home_score = game_result["home_score"]
        away_score = game_result["away_score"]
        total = game_result["total"]
        spread = game_result["spread"]  # Positive = home won by this much

        score_string = f"{game_result['home_team']} {home_score}, {game_result['away_team']} {away_score}"

        pick_type = pick.pick_type.lower()
        line_value = pick.line_value

        if pick_type == "spread":
            # Determine which team was picked
            pick_text = pick.pick.lower()
            pick_team = (pick.pick_team or "").lower()

            # Is this a home team pick?
            is_home_pick = (
                game_result["home_team"].lower() in pick_text or
                game_result["home_team"].lower() in pick_team or
                self._teams_match(game_result["home_team"].lower(), pick_text)
            )

            if line_value is not None:
                if is_home_pick:
                    # Home team pick: home team spread result
                    adjusted_margin = spread + line_value
                else:
                    # Away team pick: away team spread result
                    adjusted_margin = -spread + line_value

                if adjusted_margin > 0:
                    result = "won"
                elif adjusted_margin < 0:
                    result = "lost"
                else:
                    result = "push"

                return {
                    "result": result,
                    "score_string": score_string,
                    "spread_result": spread,
                    "total_result": total
                }

        elif pick_type == "total":
            # Over/under bet
            pick_text = pick.pick.lower()

            if line_value is not None:
                if "over" in pick_text:
                    if total > line_value:
                        result = "won"
                    elif total < line_value:
                        result = "lost"
                    else:
                        result = "push"
                else:  # Under
                    if total < line_value:
                        result = "won"
                    elif total > line_value:
                        result = "lost"
                    else:
                        result = "push"

                return {
                    "result": result,
                    "score_string": score_string,
                    "spread_result": spread,
                    "total_result": total
                }

        elif pick_type == "moneyline":
            # Moneyline bet - straight win
            pick_text = pick.pick.lower()
            pick_team = (pick.pick_team or "").lower()

            is_home_pick = (
                game_result["home_team"].lower() in pick_text or
                game_result["home_team"].lower() in pick_team or
                self._teams_match(game_result["home_team"].lower(), pick_text)
            )

            if is_home_pick:
                if home_score > away_score:
                    result = "won"
                elif home_score < away_score:
                    result = "lost"
                else:
                    result = "push"
            else:
                if away_score > home_score:
                    result = "won"
                elif away_score < home_score:
                    result = "lost"
                else:
                    result = "push"

            return {
                "result": result,
                "score_string": score_string,
                "spread_result": spread,
                "total_result": total
            }

        return None

    async def settle_single_pick(
        self,
        pick_id: str,
        result: str,
        home_score: int,
        away_score: int
    ) -> Dict:
        """
        Manually settle a single pick

        Args:
            pick_id: The pick ID
            result: "won", "lost", or "push"
            home_score: Home team final score
            away_score: Away team final score

        Returns:
            Settlement result dict
        """
        pick = self.db.query(TrackedPick).filter(TrackedPick.id == pick_id).first()
        if not pick:
            return {"error": "Pick not found"}

        score_string = f"{pick.home_team} {home_score}, {pick.away_team} {away_score}"
        spread_result = home_score - away_score
        total_result = home_score + away_score

        return self.edge_tracker.settle_pick(
            pick_id=pick_id,
            result=result,
            actual_score=score_string,
            spread_result=spread_result,
            total_result=total_result
        )


async def run_auto_settlement():
    """
    Standalone function to run auto-settlement
    Called by background job scheduler
    """
    db = SessionLocal()
    try:
        settler = AutoSettler(db)
        result = await settler.check_and_settle_pending()
        logger.info(f"Auto-settlement complete: {result}")
        return result
    except Exception as e:
        logger.error(f"Auto-settlement error: {str(e)}")
        return {"error": str(e)}
    finally:
        db.close()


def get_auto_settler(db: Session) -> AutoSettler:
    """Get an AutoSettler instance"""
    return AutoSettler(db)
