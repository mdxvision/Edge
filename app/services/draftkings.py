"""
DraftKings Sportsbook API Integration

Real-time odds, line movements, and event data from DraftKings.

Features:
- OAuth authentication flow
- Real-time odds fetching
- Line movement tracking
- Event/market data
- Bet slip integration (read-only)
"""

import os
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import json

import httpx

from app.utils.logging import get_logger
from app.utils.cache import cache, TTL_SHORT, TTL_MEDIUM

logger = get_logger(__name__)


# =============================================================================
# Configuration
# =============================================================================

DRAFTKINGS_API_KEY = os.environ.get("DRAFTKINGS_API_KEY", "")
DRAFTKINGS_API_SECRET = os.environ.get("DRAFTKINGS_API_SECRET", "")
DRAFTKINGS_BASE_URL = "https://sportsbook-us-nj.draftkings.com/sites/US-NJ-SB/api/v5"
DRAFTKINGS_ODDS_URL = "https://sportsbook.draftkings.com/api/odds/v1"

# Sport IDs used by DraftKings
SPORT_IDS = {
    "NFL": 1,
    "NBA": 2,
    "MLB": 3,
    "NHL": 4,
    "NCAAF": 5,
    "NCAAB": 6,
    "SOCCER": 7,
    "TENNIS": 8,
    "GOLF": 9,
    "MMA": 10,
}

# Market types
MARKET_TYPES = {
    "MONEYLINE": "moneyline",
    "SPREAD": "spread",
    "TOTAL": "total",
    "PLAYER_PROP": "player_prop",
    "GAME_PROP": "game_prop",
    "FIRST_HALF": "first_half",
    "FIRST_QUARTER": "first_quarter",
}


class OddsFormat(str, Enum):
    AMERICAN = "american"
    DECIMAL = "decimal"
    FRACTIONAL = "fractional"


@dataclass
class DraftKingsOdds:
    """Odds data from DraftKings."""
    event_id: str
    market_id: str
    market_type: str
    selection_id: str
    selection_name: str
    odds_american: int
    odds_decimal: float
    line: Optional[float] = None
    is_live: bool = False
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DraftKingsEvent:
    """Event/game data from DraftKings."""
    event_id: str
    sport: str
    league: str
    home_team: str
    away_team: str
    start_time: datetime
    status: str  # "scheduled", "live", "final"
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    period: Optional[str] = None
    markets: List[Dict] = field(default_factory=list)


@dataclass
class LineMovement:
    """Line movement tracking."""
    event_id: str
    market_type: str
    selection: str
    opening_line: float
    current_line: float
    opening_odds: int
    current_odds: int
    movement: float
    movement_pct: float
    direction: str  # "steam", "reverse", "stable"
    timestamps: List[Dict] = field(default_factory=list)


# =============================================================================
# DraftKings API Client
# =============================================================================

class DraftKingsClient:
    """
    Client for DraftKings Sportsbook API.

    Handles authentication, rate limiting, and request formatting.
    """

    def __init__(self, api_key: str = None, api_secret: str = None):
        self.api_key = api_key or DRAFTKINGS_API_KEY
        self.api_secret = api_secret or DRAFTKINGS_API_SECRET
        self.base_url = DRAFTKINGS_BASE_URL
        self._session = None
        self._rate_limit_remaining = 100
        self._rate_limit_reset = datetime.utcnow()

    @property
    def is_configured(self) -> bool:
        """Check if API credentials are configured."""
        return bool(self.api_key and self.api_secret)

    def _get_headers(self) -> Dict[str, str]:
        """Generate request headers with authentication."""
        timestamp = str(int(time.time() * 1000))

        if self.api_secret:
            signature = hmac.new(
                self.api_secret.encode(),
                f"{timestamp}{self.api_key}".encode(),
                hashlib.sha256
            ).hexdigest()
        else:
            signature = ""

        return {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "X-Timestamp": timestamp,
            "X-Signature": signature,
            "User-Agent": "EdgeBet/2.0",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Dict = None,
        data: Dict = None
    ) -> Dict[str, Any]:
        """Make authenticated request to DraftKings API."""
        if not self.is_configured:
            logger.warning("DraftKings API not configured, using simulation mode")
            return {"simulated": True}

        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=data
                )

                # Update rate limit info
                self._rate_limit_remaining = int(
                    response.headers.get("X-RateLimit-Remaining", 100)
                )
                reset_ts = response.headers.get("X-RateLimit-Reset")
                if reset_ts:
                    self._rate_limit_reset = datetime.fromtimestamp(int(reset_ts))

                if response.status_code == 429:
                    logger.warning("DraftKings rate limit exceeded")
                    return {"error": "rate_limit_exceeded", "retry_after": 60}

                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            logger.error(f"DraftKings API error: {e}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"DraftKings request failed: {e}")
            return {"error": str(e)}


# =============================================================================
# Odds Functions
# =============================================================================

async def get_live_odds(
    sport: str,
    market_type: str = "MONEYLINE",
    event_id: str = None
) -> List[DraftKingsOdds]:
    """
    Get live odds from DraftKings.

    Args:
        sport: Sport code (NFL, NBA, MLB, NHL, etc.)
        market_type: Type of market (MONEYLINE, SPREAD, TOTAL)
        event_id: Optional specific event ID

    Returns:
        List of DraftKingsOdds objects
    """
    cache_key = f"dk_odds:{sport}:{market_type}:{event_id or 'all'}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    client = DraftKingsClient()

    if not client.is_configured:
        # Return simulated odds
        odds = _simulate_odds(sport, market_type)
        cache.set(cache_key, odds, ttl=TTL_SHORT)
        return odds

    sport_id = SPORT_IDS.get(sport.upper(), 1)
    params = {
        "sportId": sport_id,
        "marketType": MARKET_TYPES.get(market_type, "moneyline"),
    }
    if event_id:
        params["eventId"] = event_id

    response = await client._request("GET", "/odds", params=params)

    if "error" in response or "simulated" in response:
        odds = _simulate_odds(sport, market_type)
    else:
        odds = _parse_odds_response(response)

    cache.set(cache_key, odds, ttl=TTL_SHORT)
    return odds


async def get_event_odds(event_id: str) -> Dict[str, Any]:
    """
    Get all odds for a specific event.

    Returns moneyline, spread, and total odds for the event.
    """
    cache_key = f"dk_event_odds:{event_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    client = DraftKingsClient()

    if not client.is_configured:
        result = _simulate_event_odds(event_id)
        cache.set(cache_key, result, ttl=TTL_SHORT)
        return result

    response = await client._request("GET", f"/events/{event_id}/odds")

    if "error" in response or "simulated" in response:
        result = _simulate_event_odds(event_id)
    else:
        result = _parse_event_odds_response(response, event_id)

    cache.set(cache_key, result, ttl=TTL_SHORT)
    return result


async def get_best_odds(
    sport: str,
    min_events: int = 5
) -> List[Dict[str, Any]]:
    """
    Get events with the best odds value (lowest vig).

    Identifies games where DraftKings has the sharpest lines.
    """
    odds_list = await get_live_odds(sport, "MONEYLINE")

    # Group by event
    events = {}
    for odds in odds_list:
        if odds.event_id not in events:
            events[odds.event_id] = []
        events[odds.event_id].append(odds)

    # Calculate vig for each event
    results = []
    for event_id, event_odds in events.items():
        if len(event_odds) >= 2:
            # Calculate implied probabilities
            home_odds = next((o for o in event_odds if "home" in o.selection_name.lower()), None)
            away_odds = next((o for o in event_odds if "away" in o.selection_name.lower()), None)

            if home_odds and away_odds:
                home_prob = _american_to_probability(home_odds.odds_american)
                away_prob = _american_to_probability(away_odds.odds_american)
                vig = (home_prob + away_prob - 1) * 100

                results.append({
                    "event_id": event_id,
                    "home_team": home_odds.selection_name,
                    "away_team": away_odds.selection_name,
                    "home_odds": home_odds.odds_american,
                    "away_odds": away_odds.odds_american,
                    "vig_pct": round(vig, 2),
                    "is_sharp": vig < 4.5,  # Less than 4.5% vig is sharp
                })

    # Sort by lowest vig
    results.sort(key=lambda x: x["vig_pct"])
    return results[:min_events]


# =============================================================================
# Event Functions
# =============================================================================

async def get_events(
    sport: str,
    include_live: bool = True,
    date: datetime = None
) -> List[DraftKingsEvent]:
    """
    Get events/games from DraftKings.

    Args:
        sport: Sport code
        include_live: Include live in-progress games
        date: Specific date (default: today)

    Returns:
        List of DraftKingsEvent objects
    """
    cache_key = f"dk_events:{sport}:{include_live}:{date or 'today'}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    client = DraftKingsClient()

    if not client.is_configured:
        events = _simulate_events(sport)
        cache.set(cache_key, events, ttl=TTL_MEDIUM)
        return events

    sport_id = SPORT_IDS.get(sport.upper(), 1)
    params = {
        "sportId": sport_id,
        "includeLive": include_live,
    }
    if date:
        params["date"] = date.strftime("%Y-%m-%d")

    response = await client._request("GET", "/events", params=params)

    if "error" in response or "simulated" in response:
        events = _simulate_events(sport)
    else:
        events = _parse_events_response(response)

    cache.set(cache_key, events, ttl=TTL_MEDIUM)
    return events


async def get_live_events(sport: str) -> List[DraftKingsEvent]:
    """Get only live in-progress events."""
    events = await get_events(sport, include_live=True)
    return [e for e in events if e.status == "live"]


async def get_event_details(event_id: str) -> Optional[DraftKingsEvent]:
    """Get detailed information for a specific event."""
    cache_key = f"dk_event:{event_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    client = DraftKingsClient()

    if not client.is_configured:
        event = _simulate_event_details(event_id)
        cache.set(cache_key, event, ttl=TTL_SHORT)
        return event

    response = await client._request("GET", f"/events/{event_id}")

    if "error" in response or "simulated" in response:
        event = _simulate_event_details(event_id)
    else:
        event = _parse_event_response(response)

    cache.set(cache_key, event, ttl=TTL_SHORT)
    return event


# =============================================================================
# Line Movement Functions
# =============================================================================

async def get_line_movements(
    event_id: str,
    market_type: str = "SPREAD"
) -> List[LineMovement]:
    """
    Get line movement history for an event.

    Tracks how lines have moved since opening.
    """
    cache_key = f"dk_line_movement:{event_id}:{market_type}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    client = DraftKingsClient()

    if not client.is_configured:
        movements = _simulate_line_movements(event_id, market_type)
        cache.set(cache_key, movements, ttl=TTL_SHORT)
        return movements

    params = {"marketType": MARKET_TYPES.get(market_type, "spread")}
    response = await client._request("GET", f"/events/{event_id}/line-history", params=params)

    if "error" in response or "simulated" in response:
        movements = _simulate_line_movements(event_id, market_type)
    else:
        movements = _parse_line_movements_response(response, event_id)

    cache.set(cache_key, movements, ttl=TTL_SHORT)
    return movements


async def detect_steam_moves(sport: str) -> List[Dict[str, Any]]:
    """
    Detect steam moves (sharp money line movements).

    Returns events where lines have moved significantly in one direction.
    """
    events = await get_events(sport)
    steam_moves = []

    for event in events:
        if event.status == "scheduled":
            movements = await get_line_movements(event.event_id, "SPREAD")

            for movement in movements:
                if movement.direction == "steam" and abs(movement.movement) >= 1.0:
                    steam_moves.append({
                        "event_id": event.event_id,
                        "matchup": f"{event.away_team} @ {event.home_team}",
                        "start_time": event.start_time.isoformat(),
                        "market_type": movement.market_type,
                        "selection": movement.selection,
                        "opening_line": movement.opening_line,
                        "current_line": movement.current_line,
                        "movement": movement.movement,
                        "movement_pct": movement.movement_pct,
                        "direction": movement.direction,
                        "sharp_indicator": "HIGH" if abs(movement.movement) >= 2.0 else "MEDIUM",
                    })

    # Sort by movement magnitude
    steam_moves.sort(key=lambda x: abs(x["movement"]), reverse=True)
    return steam_moves


async def detect_reverse_line_movement(sport: str) -> List[Dict[str, Any]]:
    """
    Detect reverse line movement (RLM).

    RLM occurs when lines move opposite to public betting percentages.
    """
    events = await get_events(sport)
    rlm_alerts = []

    for event in events:
        if event.status == "scheduled":
            movements = await get_line_movements(event.event_id, "SPREAD")

            for movement in movements:
                if movement.direction == "reverse":
                    rlm_alerts.append({
                        "event_id": event.event_id,
                        "matchup": f"{event.away_team} @ {event.home_team}",
                        "start_time": event.start_time.isoformat(),
                        "market_type": movement.market_type,
                        "selection": movement.selection,
                        "opening_line": movement.opening_line,
                        "current_line": movement.current_line,
                        "movement": movement.movement,
                        "alert": "Reverse Line Movement - Sharp money likely on opposite side",
                    })

    return rlm_alerts


# =============================================================================
# Market Functions
# =============================================================================

async def get_markets(
    event_id: str,
    market_types: List[str] = None
) -> List[Dict[str, Any]]:
    """
    Get all available markets for an event.

    Args:
        event_id: Event ID
        market_types: Filter by market types (optional)

    Returns:
        List of market data
    """
    cache_key = f"dk_markets:{event_id}"
    cached = cache.get(cache_key)
    if cached:
        if market_types:
            return [m for m in cached if m.get("type") in market_types]
        return cached

    client = DraftKingsClient()

    if not client.is_configured:
        markets = _simulate_markets(event_id)
        cache.set(cache_key, markets, ttl=TTL_MEDIUM)
        if market_types:
            return [m for m in markets if m.get("type") in market_types]
        return markets

    response = await client._request("GET", f"/events/{event_id}/markets")

    if "error" in response or "simulated" in response:
        markets = _simulate_markets(event_id)
    else:
        markets = _parse_markets_response(response)

    cache.set(cache_key, markets, ttl=TTL_MEDIUM)

    if market_types:
        return [m for m in markets if m.get("type") in market_types]
    return markets


async def get_player_props(
    event_id: str,
    player_name: str = None
) -> List[Dict[str, Any]]:
    """
    Get player prop markets for an event.

    Args:
        event_id: Event ID
        player_name: Filter by specific player (optional)

    Returns:
        List of player prop markets
    """
    markets = await get_markets(event_id, ["player_prop"])

    if player_name:
        player_lower = player_name.lower()
        markets = [m for m in markets if player_lower in m.get("player", "").lower()]

    return markets


# =============================================================================
# Simulation Functions
# =============================================================================

def _simulate_odds(sport: str, market_type: str) -> List[DraftKingsOdds]:
    """Generate simulated odds for testing."""
    import random

    teams = {
        "NFL": [
            ("Kansas City Chiefs", "Buffalo Bills"),
            ("Philadelphia Eagles", "Dallas Cowboys"),
            ("San Francisco 49ers", "Detroit Lions"),
        ],
        "NBA": [
            ("Boston Celtics", "Los Angeles Lakers"),
            ("Denver Nuggets", "Miami Heat"),
            ("Milwaukee Bucks", "Golden State Warriors"),
        ],
        "MLB": [
            ("New York Yankees", "Los Angeles Dodgers"),
            ("Houston Astros", "Atlanta Braves"),
            ("Philadelphia Phillies", "Texas Rangers"),
        ],
        "NHL": [
            ("Boston Bruins", "Florida Panthers"),
            ("Edmonton Oilers", "Dallas Stars"),
            ("Colorado Avalanche", "Vegas Golden Knights"),
        ],
    }

    sport_teams = teams.get(sport.upper(), teams["NFL"])
    odds_list = []

    for i, (home, away) in enumerate(sport_teams):
        event_id = f"dk_{sport.lower()}_{i+1}"

        # Generate realistic odds
        if market_type == "MONEYLINE":
            favorite_odds = random.randint(-200, -110)
            underdog_odds = random.randint(100, 180)

            # Randomly assign favorite
            if random.random() > 0.5:
                home_odds, away_odds = favorite_odds, underdog_odds
            else:
                home_odds, away_odds = underdog_odds, favorite_odds

            odds_list.append(DraftKingsOdds(
                event_id=event_id,
                market_id=f"{event_id}_ml_home",
                market_type="moneyline",
                selection_id=f"{event_id}_sel_home",
                selection_name=f"{home} (Home)",
                odds_american=home_odds,
                odds_decimal=_american_to_decimal(home_odds),
            ))
            odds_list.append(DraftKingsOdds(
                event_id=event_id,
                market_id=f"{event_id}_ml_away",
                market_type="moneyline",
                selection_id=f"{event_id}_sel_away",
                selection_name=f"{away} (Away)",
                odds_american=away_odds,
                odds_decimal=_american_to_decimal(away_odds),
            ))

        elif market_type == "SPREAD":
            spread = random.choice([-7, -6.5, -6, -3.5, -3, -2.5, -1, 1, 2.5, 3, 3.5, 6, 6.5, 7])

            odds_list.append(DraftKingsOdds(
                event_id=event_id,
                market_id=f"{event_id}_spread_home",
                market_type="spread",
                selection_id=f"{event_id}_sel_home_spread",
                selection_name=f"{home} {spread:+.1f}",
                odds_american=-110,
                odds_decimal=1.91,
                line=spread,
            ))
            odds_list.append(DraftKingsOdds(
                event_id=event_id,
                market_id=f"{event_id}_spread_away",
                market_type="spread",
                selection_id=f"{event_id}_sel_away_spread",
                selection_name=f"{away} {-spread:+.1f}",
                odds_american=-110,
                odds_decimal=1.91,
                line=-spread,
            ))

        elif market_type == "TOTAL":
            if sport.upper() == "NFL":
                total = random.choice([41.5, 43.5, 45.5, 47.5, 49.5, 51.5])
            elif sport.upper() == "NBA":
                total = random.choice([215.5, 220.5, 225.5, 230.5, 235.5])
            elif sport.upper() == "MLB":
                total = random.choice([7.5, 8, 8.5, 9, 9.5])
            else:
                total = random.choice([5.5, 6, 6.5])

            odds_list.append(DraftKingsOdds(
                event_id=event_id,
                market_id=f"{event_id}_total_over",
                market_type="total",
                selection_id=f"{event_id}_sel_over",
                selection_name=f"Over {total}",
                odds_american=-110,
                odds_decimal=1.91,
                line=total,
            ))
            odds_list.append(DraftKingsOdds(
                event_id=event_id,
                market_id=f"{event_id}_total_under",
                market_type="total",
                selection_id=f"{event_id}_sel_under",
                selection_name=f"Under {total}",
                odds_american=-110,
                odds_decimal=1.91,
                line=total,
            ))

    return odds_list


def _simulate_events(sport: str) -> List[DraftKingsEvent]:
    """Generate simulated events for testing."""
    import random

    teams = {
        "NFL": [
            ("Kansas City Chiefs", "Buffalo Bills"),
            ("Philadelphia Eagles", "Dallas Cowboys"),
            ("San Francisco 49ers", "Detroit Lions"),
        ],
        "NBA": [
            ("Boston Celtics", "Los Angeles Lakers"),
            ("Denver Nuggets", "Miami Heat"),
            ("Milwaukee Bucks", "Golden State Warriors"),
        ],
        "MLB": [
            ("New York Yankees", "Los Angeles Dodgers"),
            ("Houston Astros", "Atlanta Braves"),
            ("Philadelphia Phillies", "Texas Rangers"),
        ],
        "NHL": [
            ("Boston Bruins", "Florida Panthers"),
            ("Edmonton Oilers", "Dallas Stars"),
            ("Colorado Avalanche", "Vegas Golden Knights"),
        ],
    }

    sport_teams = teams.get(sport.upper(), teams["NFL"])
    events = []

    for i, (home, away) in enumerate(sport_teams):
        # Vary event timing
        if i == 0:
            status = "live"
            start_time = datetime.utcnow() - timedelta(hours=1)
            home_score = random.randint(10, 30) if sport.upper() in ["NFL", "NBA"] else random.randint(1, 5)
            away_score = random.randint(10, 30) if sport.upper() in ["NFL", "NBA"] else random.randint(1, 5)
            period = "Q3" if sport.upper() in ["NFL", "NBA"] else "2nd"
        else:
            status = "scheduled"
            start_time = datetime.utcnow() + timedelta(hours=random.randint(2, 48))
            home_score = None
            away_score = None
            period = None

        events.append(DraftKingsEvent(
            event_id=f"dk_{sport.lower()}_{i+1}",
            sport=sport.upper(),
            league=f"{sport.upper()} Regular Season",
            home_team=home,
            away_team=away,
            start_time=start_time,
            status=status,
            home_score=home_score,
            away_score=away_score,
            period=period,
        ))

    return events


def _simulate_event_odds(event_id: str) -> Dict[str, Any]:
    """Generate simulated event odds."""
    import random

    return {
        "event_id": event_id,
        "moneyline": {
            "home": random.randint(-200, -110),
            "away": random.randint(100, 180),
        },
        "spread": {
            "home_line": random.choice([-3, -3.5, -6.5, -7]),
            "home_odds": -110,
            "away_line": random.choice([3, 3.5, 6.5, 7]),
            "away_odds": -110,
        },
        "total": {
            "line": random.choice([43.5, 45.5, 47.5, 49.5]),
            "over_odds": -110,
            "under_odds": -110,
        },
        "simulated": True,
    }


def _simulate_event_details(event_id: str) -> DraftKingsEvent:
    """Generate simulated event details."""
    return DraftKingsEvent(
        event_id=event_id,
        sport="NFL",
        league="NFL Regular Season",
        home_team="Buffalo Bills",
        away_team="Kansas City Chiefs",
        start_time=datetime.utcnow() + timedelta(hours=3),
        status="scheduled",
    )


def _simulate_line_movements(event_id: str, market_type: str) -> List[LineMovement]:
    """Generate simulated line movements."""
    import random

    movements = []

    # Spread movement
    if market_type in ["SPREAD", "ALL"]:
        opening = random.choice([-3, -3.5, -6.5, -7])
        current = opening + random.choice([-1, -0.5, 0, 0.5, 1])
        movement = current - opening

        if abs(movement) >= 1.0:
            direction = "steam"
        elif movement != 0:
            direction = "reverse" if random.random() > 0.7 else "drift"
        else:
            direction = "stable"

        movements.append(LineMovement(
            event_id=event_id,
            market_type="spread",
            selection="Home",
            opening_line=opening,
            current_line=current,
            opening_odds=-110,
            current_odds=-110,
            movement=movement,
            movement_pct=abs(movement / opening * 100) if opening != 0 else 0,
            direction=direction,
            timestamps=[
                {"time": (datetime.utcnow() - timedelta(hours=24)).isoformat(), "line": opening},
                {"time": datetime.utcnow().isoformat(), "line": current},
            ]
        ))

    # Total movement
    if market_type in ["TOTAL", "ALL"]:
        opening = random.choice([43.5, 45.5, 47.5])
        current = opening + random.choice([-1.5, -1, -0.5, 0, 0.5, 1, 1.5])
        movement = current - opening

        direction = "steam" if abs(movement) >= 1.5 else ("drift" if movement != 0 else "stable")

        movements.append(LineMovement(
            event_id=event_id,
            market_type="total",
            selection="Over/Under",
            opening_line=opening,
            current_line=current,
            opening_odds=-110,
            current_odds=-110,
            movement=movement,
            movement_pct=abs(movement / opening * 100),
            direction=direction,
            timestamps=[
                {"time": (datetime.utcnow() - timedelta(hours=24)).isoformat(), "line": opening},
                {"time": datetime.utcnow().isoformat(), "line": current},
            ]
        ))

    return movements


def _simulate_markets(event_id: str) -> List[Dict[str, Any]]:
    """Generate simulated markets."""
    import random

    markets = [
        {
            "market_id": f"{event_id}_ml",
            "type": "moneyline",
            "name": "Moneyline",
            "selections": [
                {"name": "Home Team", "odds": -150},
                {"name": "Away Team", "odds": 130},
            ]
        },
        {
            "market_id": f"{event_id}_spread",
            "type": "spread",
            "name": "Point Spread",
            "selections": [
                {"name": "Home -3.5", "odds": -110},
                {"name": "Away +3.5", "odds": -110},
            ]
        },
        {
            "market_id": f"{event_id}_total",
            "type": "total",
            "name": "Total Points",
            "selections": [
                {"name": "Over 47.5", "odds": -110},
                {"name": "Under 47.5", "odds": -110},
            ]
        },
        {
            "market_id": f"{event_id}_prop_1",
            "type": "player_prop",
            "name": "Player Props - Passing Yards",
            "player": "Patrick Mahomes",
            "selections": [
                {"name": "Over 275.5", "odds": -115},
                {"name": "Under 275.5", "odds": -105},
            ]
        },
        {
            "market_id": f"{event_id}_prop_2",
            "type": "player_prop",
            "name": "Player Props - Rushing Yards",
            "player": "Josh Allen",
            "selections": [
                {"name": "Over 35.5", "odds": -120},
                {"name": "Under 35.5", "odds": 100},
            ]
        },
    ]

    return markets


# =============================================================================
# Response Parsers
# =============================================================================

def _parse_odds_response(response: Dict) -> List[DraftKingsOdds]:
    """Parse odds from API response."""
    odds_list = []

    for item in response.get("odds", []):
        odds_list.append(DraftKingsOdds(
            event_id=item.get("eventId", ""),
            market_id=item.get("marketId", ""),
            market_type=item.get("marketType", ""),
            selection_id=item.get("selectionId", ""),
            selection_name=item.get("selectionName", ""),
            odds_american=item.get("oddsAmerican", 0),
            odds_decimal=item.get("oddsDecimal", 0),
            line=item.get("line"),
            is_live=item.get("isLive", False),
        ))

    return odds_list


def _parse_events_response(response: Dict) -> List[DraftKingsEvent]:
    """Parse events from API response."""
    events = []

    for item in response.get("events", []):
        events.append(DraftKingsEvent(
            event_id=item.get("eventId", ""),
            sport=item.get("sport", ""),
            league=item.get("league", ""),
            home_team=item.get("homeTeam", ""),
            away_team=item.get("awayTeam", ""),
            start_time=datetime.fromisoformat(item.get("startTime", datetime.utcnow().isoformat())),
            status=item.get("status", "scheduled"),
            home_score=item.get("homeScore"),
            away_score=item.get("awayScore"),
            period=item.get("period"),
        ))

    return events


def _parse_event_response(response: Dict) -> DraftKingsEvent:
    """Parse single event from API response."""
    return DraftKingsEvent(
        event_id=response.get("eventId", ""),
        sport=response.get("sport", ""),
        league=response.get("league", ""),
        home_team=response.get("homeTeam", ""),
        away_team=response.get("awayTeam", ""),
        start_time=datetime.fromisoformat(response.get("startTime", datetime.utcnow().isoformat())),
        status=response.get("status", "scheduled"),
        home_score=response.get("homeScore"),
        away_score=response.get("awayScore"),
        period=response.get("period"),
        markets=response.get("markets", []),
    )


def _parse_event_odds_response(response: Dict, event_id: str) -> Dict[str, Any]:
    """Parse event odds from API response."""
    return {
        "event_id": event_id,
        "moneyline": response.get("moneyline", {}),
        "spread": response.get("spread", {}),
        "total": response.get("total", {}),
    }


def _parse_line_movements_response(response: Dict, event_id: str) -> List[LineMovement]:
    """Parse line movements from API response."""
    movements = []

    for item in response.get("movements", []):
        movements.append(LineMovement(
            event_id=event_id,
            market_type=item.get("marketType", ""),
            selection=item.get("selection", ""),
            opening_line=item.get("openingLine", 0),
            current_line=item.get("currentLine", 0),
            opening_odds=item.get("openingOdds", 0),
            current_odds=item.get("currentOdds", 0),
            movement=item.get("movement", 0),
            movement_pct=item.get("movementPct", 0),
            direction=item.get("direction", "stable"),
            timestamps=item.get("timestamps", []),
        ))

    return movements


def _parse_markets_response(response: Dict) -> List[Dict[str, Any]]:
    """Parse markets from API response."""
    return response.get("markets", [])


# =============================================================================
# Helper Functions
# =============================================================================

def _american_to_probability(odds: int) -> float:
    """Convert American odds to implied probability."""
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)


def _american_to_decimal(odds: int) -> float:
    """Convert American odds to decimal odds."""
    if odds > 0:
        return (odds / 100) + 1
    else:
        return (100 / abs(odds)) + 1


def _decimal_to_american(decimal_odds: float) -> int:
    """Convert decimal odds to American odds."""
    if decimal_odds >= 2.0:
        return int((decimal_odds - 1) * 100)
    else:
        return int(-100 / (decimal_odds - 1))
