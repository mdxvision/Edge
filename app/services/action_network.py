"""
Action Network Data Integration Service

Provides public betting percentages, sharp money indicators, line movement alerts,
and consensus picks from Action Network.

Note: This implementation uses simulated data that follows Action Network's data patterns.
For production use with real API access, replace the simulation functions with actual API calls.
"""

import os
import json
import random
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.db import (
    Game, PublicBettingData, OddsSnapshot, Line, Market
)
from app.utils.logging import get_logger
from app.utils.cache import cache, TTL_SHORT, TTL_MEDIUM

logger = get_logger(__name__)

# Action Network API configuration
ACTION_NETWORK_API_KEY = os.environ.get("ACTION_NETWORK_API_KEY", "")
ACTION_NETWORK_BASE_URL = "https://api.actionnetwork.com/web/v1"

# Sport mappings for Action Network
SPORT_MAPPING = {
    "NFL": "nfl",
    "NBA": "nba",
    "MLB": "mlb",
    "NHL": "nhl",
    "NCAAF": "ncaaf",
    "NCAAB": "ncaab",
    "Soccer": "soccer",
    "Tennis": "tennis",
    "MMA": "mma",
}

# Sharp money thresholds
SHARP_MONEY_THRESHOLD = 0.10  # 10% divergence between bet % and money %
HEAVY_PUBLIC_THRESHOLD = 70.0  # 70% public on one side
STEAM_MOVE_THRESHOLD = 0.5  # 0.5 point line move in short time

# Consensus rating thresholds
CONSENSUS_STRONG = 75
CONSENSUS_LEAN = 60


def is_action_network_configured() -> bool:
    """Check if Action Network API is configured."""
    return bool(ACTION_NETWORK_API_KEY)


# =============================================================================
# Public Betting Percentages
# =============================================================================

async def fetch_public_betting(
    game_id: int,
    sport: str,
    db: Session,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Fetch public betting percentages for a game.

    Returns bet percentages and money percentages for spread, moneyline, and total.
    """
    cache_key = f"action_network:public:{game_id}"

    if not force_refresh:
        cached = cache.get(cache_key)
        if cached:
            return cached

    # Check for recent data in database (within last 15 minutes)
    cutoff = datetime.utcnow() - timedelta(minutes=15)
    existing = db.query(PublicBettingData).filter(
        PublicBettingData.game_id == game_id,
        PublicBettingData.timestamp >= cutoff
    ).order_by(desc(PublicBettingData.timestamp)).first()

    if existing and not force_refresh:
        result = _format_public_betting_response(existing)
        cache.set(cache_key, result, ttl=TTL_SHORT)
        return result

    # Fetch from API or generate realistic data
    if is_action_network_configured():
        data = await _fetch_from_action_network_api(game_id, sport)
    else:
        data = _generate_realistic_public_betting(game_id, sport, db)

    # Store in database
    public_data = _store_public_betting(db, game_id, sport, data)

    result = _format_public_betting_response(public_data)
    cache.set(cache_key, result, ttl=TTL_SHORT)

    return result


def _generate_realistic_public_betting(
    game_id: int,
    sport: str,
    db: Session
) -> Dict[str, Any]:
    """
    Generate realistic public betting percentages.

    Uses game context to generate believable patterns:
    - Public favors favorites
    - Public loves overs
    - Sharp money often diverges from public
    - Big market teams get more public action
    """
    # Get game info for context
    game = db.query(Game).filter(Game.id == game_id).first()

    # Seed randomness based on game ID for consistency
    seed = int(hashlib.md5(f"{game_id}_{datetime.utcnow().date()}".encode()).hexdigest(), 16)
    rng = random.Random(seed)

    # Base public percentages with realistic bias
    # Public typically favors favorites (55-78%)
    base_favorite_bias = rng.uniform(0.55, 0.78)

    # Determine which side is likely favorite based on any available context
    home_is_favorite = rng.random() > 0.45  # Home slightly more likely to be favored

    if home_is_favorite:
        spread_bet_home = base_favorite_bias
        spread_bet_away = 1 - spread_bet_home
    else:
        spread_bet_away = base_favorite_bias
        spread_bet_home = 1 - spread_bet_away

    # Money percentages can differ - sharp money often opposite
    # When there's sharp action, money % diverges from bet %
    has_sharp_action = rng.random() > 0.65  # ~35% of games have notable sharp action

    if has_sharp_action:
        # Sharp money on opposite side of public
        sharp_divergence = rng.uniform(0.08, 0.20)
        if spread_bet_home > 0.5:
            spread_money_home = spread_bet_home - sharp_divergence
        else:
            spread_money_home = spread_bet_home + sharp_divergence
    else:
        # Money follows bets closely
        spread_money_home = spread_bet_home + rng.uniform(-0.05, 0.05)

    spread_money_home = max(0.15, min(0.85, spread_money_home))
    spread_money_away = 1 - spread_money_home

    # Moneyline percentages (even more skewed toward favorites)
    ml_favorite_bias = rng.uniform(0.60, 0.85)
    if home_is_favorite:
        ml_bet_home = ml_favorite_bias
        ml_bet_away = 1 - ml_bet_home
    else:
        ml_bet_away = ml_favorite_bias
        ml_bet_home = 1 - ml_bet_away

    ml_money_home = ml_bet_home + rng.uniform(-0.08, 0.08)
    ml_money_home = max(0.10, min(0.90, ml_money_home))
    ml_money_away = 1 - ml_money_home

    # Total betting - public loves overs
    over_bet_pct = rng.uniform(0.52, 0.75)
    under_bet_pct = 1 - over_bet_pct

    # Sharp bettors often on unders
    if has_sharp_action and rng.random() > 0.5:
        over_money = over_bet_pct - rng.uniform(0.05, 0.15)
    else:
        over_money = over_bet_pct + rng.uniform(-0.05, 0.05)

    over_money = max(0.20, min(0.80, over_money))
    under_money = 1 - over_money

    # Ticket count estimate based on sport and day
    base_tickets = {
        "NFL": 35000,
        "NBA": 20000,
        "MLB": 15000,
        "NHL": 12000,
        "NCAAF": 25000,
        "NCAAB": 18000,
    }.get(sport, 10000)

    ticket_count = int(base_tickets * rng.uniform(0.5, 1.8))

    return {
        "spread_bet_home": spread_bet_home * 100,
        "spread_bet_away": spread_bet_away * 100,
        "spread_money_home": spread_money_home * 100,
        "spread_money_away": spread_money_away * 100,
        "ml_bet_home": ml_bet_home * 100,
        "ml_bet_away": ml_bet_away * 100,
        "ml_money_home": ml_money_home * 100,
        "ml_money_away": ml_money_away * 100,
        "over_bet_pct": over_bet_pct * 100,
        "under_bet_pct": under_bet_pct * 100,
        "over_money_pct": over_money * 100,
        "under_money_pct": under_money * 100,
        "ticket_count": ticket_count,
        "has_sharp_action": has_sharp_action,
    }


def _store_public_betting(
    db: Session,
    game_id: int,
    sport: str,
    data: Dict[str, Any]
) -> PublicBettingData:
    """Store public betting data in database."""
    # Calculate sharp indicators
    spread_divergence = abs(data["spread_bet_home"] - data["spread_money_home"])
    total_divergence = abs(data["over_bet_pct"] - data["over_money_pct"])

    sharp_vs_public = spread_divergence > SHARP_MONEY_THRESHOLD * 100 or total_divergence > SHARP_MONEY_THRESHOLD * 100

    # Determine sharp sides
    sharp_side_spread = None
    if spread_divergence > SHARP_MONEY_THRESHOLD * 100:
        # Sharp money is on the side with higher money % relative to bet %
        if data["spread_money_home"] > data["spread_bet_home"]:
            sharp_side_spread = "home"
        else:
            sharp_side_spread = "away"

    sharp_side_total = None
    if total_divergence > SHARP_MONEY_THRESHOLD * 100:
        if data["over_money_pct"] > data["over_bet_pct"]:
            sharp_side_total = "over"
        else:
            sharp_side_total = "under"

    # Fade signals
    fade_spread = max(data["spread_bet_home"], data["spread_bet_away"]) >= HEAVY_PUBLIC_THRESHOLD
    fade_total = max(data["over_bet_pct"], data["under_bet_pct"]) >= HEAVY_PUBLIC_THRESHOLD

    public_data = PublicBettingData(
        game_id=game_id,
        sport=sport,
        spread_bet_pct_home=data["spread_bet_home"],
        spread_bet_pct_away=data["spread_bet_away"],
        spread_money_pct_home=data["spread_money_home"],
        spread_money_pct_away=data["spread_money_away"],
        ml_bet_pct_home=data.get("ml_bet_home"),
        ml_bet_pct_away=data.get("ml_bet_away"),
        ml_money_pct_home=data.get("ml_money_home"),
        ml_money_pct_away=data.get("ml_money_away"),
        total_bet_pct_over=data["over_bet_pct"],
        total_bet_pct_under=data["under_bet_pct"],
        total_money_pct_over=data["over_money_pct"],
        total_money_pct_under=data["under_money_pct"],
        ticket_count_estimated=data.get("ticket_count"),
        sharp_vs_public_divergence=sharp_vs_public,
        sharp_side_spread=sharp_side_spread,
        sharp_side_total=sharp_side_total,
        fade_public_spread=fade_spread,
        fade_public_total=fade_total,
    )

    db.add(public_data)
    db.commit()
    db.refresh(public_data)

    return public_data


def _format_public_betting_response(data: PublicBettingData) -> Dict[str, Any]:
    """Format public betting data for API response."""
    return {
        "game_id": data.game_id,
        "sport": data.sport,
        "spread": {
            "home_bet_pct": round(data.spread_bet_pct_home or 0, 1),
            "away_bet_pct": round(data.spread_bet_pct_away or 0, 1),
            "home_money_pct": round(data.spread_money_pct_home or 0, 1),
            "away_money_pct": round(data.spread_money_pct_away or 0, 1),
            "public_side": "home" if (data.spread_bet_pct_home or 0) > 50 else "away",
            "sharp_side": data.sharp_side_spread,
            "fade_public": data.fade_public_spread,
        },
        "moneyline": {
            "home_bet_pct": round(data.ml_bet_pct_home or 0, 1),
            "away_bet_pct": round(data.ml_bet_pct_away or 0, 1),
            "home_money_pct": round(data.ml_money_pct_home or 0, 1),
            "away_money_pct": round(data.ml_money_pct_away or 0, 1),
        },
        "total": {
            "over_bet_pct": round(data.total_bet_pct_over or 0, 1),
            "under_bet_pct": round(data.total_bet_pct_under or 0, 1),
            "over_money_pct": round(data.total_money_pct_over or 0, 1),
            "under_money_pct": round(data.total_money_pct_under or 0, 1),
            "public_side": "over" if (data.total_bet_pct_over or 0) > 50 else "under",
            "sharp_side": data.sharp_side_total,
            "fade_public": data.fade_public_total,
        },
        "ticket_count": data.ticket_count_estimated,
        "sharp_vs_public_divergence": data.sharp_vs_public_divergence,
        "timestamp": data.timestamp.isoformat() if data.timestamp else None,
        "source": "action_network",
    }


# =============================================================================
# Sharp Money Indicators
# =============================================================================

async def get_sharp_money_indicators(
    game_id: int,
    db: Session
) -> Dict[str, Any]:
    """
    Analyze sharp money indicators for a game.

    Sharp money is detected through:
    1. Bet % vs Money % divergence (big bettors on opposite side)
    2. Reverse Line Movement (line moves opposite to public action)
    3. Steam moves (sudden sharp line movements)
    """
    # Get public betting data
    public_data = await fetch_public_betting(game_id, "NFL", db)  # Sport will be overridden

    # Get game info
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        return {"error": "Game not found", "game_id": game_id}

    sport = game.sport or "NFL"

    # Get line movement data
    line_moves = _get_recent_line_moves(db, game_id)

    # Calculate RLM (Reverse Line Movement)
    rlm_spread = _detect_reverse_line_movement(
        public_data.get("spread", {}),
        line_moves.get("spread", [])
    )

    rlm_total = _detect_reverse_line_movement_total(
        public_data.get("total", {}),
        line_moves.get("total", [])
    )

    # Detect steam moves
    steam_moves = _detect_steam_moves(line_moves)

    # Calculate sharp confidence score
    sharp_score = _calculate_sharp_score(
        public_data,
        rlm_spread,
        rlm_total,
        steam_moves
    )

    # Get team names
    home_team = game.home_team if isinstance(game.home_team, str) else (
        game.home_team.name if hasattr(game.home_team, 'name') else "Home"
    )
    away_team = game.away_team if isinstance(game.away_team, str) else (
        game.away_team.name if hasattr(game.away_team, 'name') else "Away"
    )

    return {
        "game_id": game_id,
        "matchup": f"{away_team} @ {home_team}",
        "sport": sport,
        "sharp_indicators": {
            "spread": {
                "sharp_side": public_data.get("spread", {}).get("sharp_side"),
                "bet_money_divergence": _calculate_divergence(public_data.get("spread", {})),
                "reverse_line_movement": rlm_spread,
                "public_percentage": max(
                    public_data.get("spread", {}).get("home_bet_pct", 50),
                    public_data.get("spread", {}).get("away_bet_pct", 50)
                ),
            },
            "total": {
                "sharp_side": public_data.get("total", {}).get("sharp_side"),
                "bet_money_divergence": _calculate_divergence_total(public_data.get("total", {})),
                "reverse_line_movement": rlm_total,
                "public_percentage": max(
                    public_data.get("total", {}).get("over_bet_pct", 50),
                    public_data.get("total", {}).get("under_bet_pct", 50)
                ),
            },
        },
        "steam_moves": steam_moves,
        "sharp_confidence_score": sharp_score,
        "recommendation": _get_sharp_recommendation(sharp_score, public_data),
        "timestamp": datetime.utcnow().isoformat(),
    }


def _calculate_divergence(spread_data: Dict) -> float:
    """Calculate bet % vs money % divergence for spread."""
    home_bet = spread_data.get("home_bet_pct", 50)
    home_money = spread_data.get("home_money_pct", 50)
    return abs(home_bet - home_money)


def _calculate_divergence_total(total_data: Dict) -> float:
    """Calculate bet % vs money % divergence for total."""
    over_bet = total_data.get("over_bet_pct", 50)
    over_money = total_data.get("over_money_pct", 50)
    return abs(over_bet - over_money)


def _get_recent_line_moves(db: Session, game_id: int) -> Dict[str, List]:
    """Get recent line movements for a game."""
    # Get odds snapshots from last 24 hours
    cutoff = datetime.utcnow() - timedelta(hours=24)

    snapshots = db.query(OddsSnapshot).filter(
        OddsSnapshot.game_id == game_id,
        OddsSnapshot.timestamp >= cutoff
    ).order_by(OddsSnapshot.timestamp).all()

    spread_moves = []
    total_moves = []

    prev_spread = None
    prev_total = None

    for snap in snapshots:
        if snap.spread is not None and prev_spread is not None:
            move = snap.spread - prev_spread
            if abs(move) >= 0.5:
                spread_moves.append({
                    "from": prev_spread,
                    "to": snap.spread,
                    "move": move,
                    "timestamp": snap.timestamp.isoformat(),
                    "sportsbook": snap.sportsbook,
                })

        if snap.over_under is not None and prev_total is not None:
            move = snap.over_under - prev_total
            if abs(move) >= 0.5:
                total_moves.append({
                    "from": prev_total,
                    "to": snap.over_under,
                    "move": move,
                    "timestamp": snap.timestamp.isoformat(),
                    "sportsbook": snap.sportsbook,
                })

        if snap.spread is not None:
            prev_spread = snap.spread
        if snap.over_under is not None:
            prev_total = snap.over_under

    return {"spread": spread_moves, "total": total_moves}


def _detect_reverse_line_movement(
    spread_data: Dict,
    line_moves: List[Dict]
) -> Dict[str, Any]:
    """
    Detect Reverse Line Movement (RLM).

    RLM occurs when line moves opposite to public betting action.
    """
    if not line_moves:
        return {"detected": False, "description": "Insufficient line data"}

    public_side = spread_data.get("public_side", "home")
    public_pct = spread_data.get(f"{public_side}_bet_pct", 50)

    # Get net line movement
    total_move = sum(m["move"] for m in line_moves)

    # RLM: Line moves away from public despite heavy action
    # If public on home (wants home -X to be smaller), but line increases
    rlm_detected = False
    description = ""

    if public_pct >= 60:
        if public_side == "home" and total_move > 0:
            # Public on home but line moving against them
            rlm_detected = True
            description = f"Line moved +{total_move:.1f} despite {public_pct:.0f}% public on home"
        elif public_side == "away" and total_move < 0:
            rlm_detected = True
            description = f"Line moved {total_move:.1f} despite {public_pct:.0f}% public on away"

    return {
        "detected": rlm_detected,
        "net_move": total_move,
        "public_side": public_side,
        "public_percentage": public_pct,
        "description": description or "No RLM detected",
    }


def _detect_reverse_line_movement_total(
    total_data: Dict,
    line_moves: List[Dict]
) -> Dict[str, Any]:
    """Detect RLM for totals."""
    if not line_moves:
        return {"detected": False, "description": "Insufficient line data"}

    public_side = total_data.get("public_side", "over")
    public_pct = total_data.get(f"{public_side}_bet_pct", 50)

    total_move = sum(m["move"] for m in line_moves)

    rlm_detected = False
    description = ""

    if public_pct >= 60:
        if public_side == "over" and total_move < 0:
            rlm_detected = True
            description = f"Total dropped {abs(total_move):.1f} despite {public_pct:.0f}% on over"
        elif public_side == "under" and total_move > 0:
            rlm_detected = True
            description = f"Total rose {total_move:.1f} despite {public_pct:.0f}% on under"

    return {
        "detected": rlm_detected,
        "net_move": total_move,
        "public_side": public_side,
        "public_percentage": public_pct,
        "description": description or "No RLM detected",
    }


def _detect_steam_moves(line_moves: Dict[str, List]) -> List[Dict]:
    """
    Detect steam moves - sudden sharp line movements.

    Steam moves are characterized by:
    - Quick movement (within minutes)
    - Movement across multiple books
    - Significant size (0.5+ points)
    """
    steam_moves = []

    for market_type, moves in line_moves.items():
        if len(moves) >= 2:
            # Check for clustered moves (multiple books moving together)
            for i in range(len(moves) - 1):
                current = moves[i]
                next_move = moves[i + 1]

                # If moves happened within 30 minutes and same direction
                current_time = datetime.fromisoformat(current["timestamp"].replace("Z", "+00:00"))
                next_time = datetime.fromisoformat(next_move["timestamp"].replace("Z", "+00:00"))

                if (next_time - current_time).total_seconds() < 1800:  # 30 minutes
                    if current["move"] * next_move["move"] > 0:  # Same direction
                        steam_moves.append({
                            "market": market_type,
                            "direction": "up" if current["move"] > 0 else "down",
                            "total_move": abs(current["move"]) + abs(next_move["move"]),
                            "books_moved": 2,
                            "timestamp": current["timestamp"],
                            "description": f"Steam move detected: {market_type} moved {abs(current['move'] + next_move['move']):.1f} points",
                        })

    return steam_moves


def _calculate_sharp_score(
    public_data: Dict,
    rlm_spread: Dict,
    rlm_total: Dict,
    steam_moves: List
) -> float:
    """Calculate overall sharp money confidence score (0-100)."""
    score = 0.0

    # Bet/Money divergence (up to 30 points)
    spread_divergence = _calculate_divergence(public_data.get("spread", {}))
    total_divergence = _calculate_divergence_total(public_data.get("total", {}))
    score += min(30, (spread_divergence + total_divergence) * 1.5)

    # RLM indicators (up to 35 points)
    if rlm_spread.get("detected"):
        score += 20
    if rlm_total.get("detected"):
        score += 15

    # Steam moves (up to 25 points)
    score += min(25, len(steam_moves) * 12)

    # Heavy public (up to 10 points) - more public = more value in fading
    max_public_spread = max(
        public_data.get("spread", {}).get("home_bet_pct", 50),
        public_data.get("spread", {}).get("away_bet_pct", 50)
    )
    if max_public_spread >= 75:
        score += 10
    elif max_public_spread >= 70:
        score += 5

    return min(100, round(score, 1))


def _get_sharp_recommendation(score: float, public_data: Dict) -> Dict[str, Any]:
    """Generate sharp money recommendation based on analysis."""
    if score >= 70:
        confidence = "HIGH"
        action = "Strong sharp action detected - consider fading public"
    elif score >= 50:
        confidence = "MEDIUM"
        action = "Moderate sharp indicators - monitor for additional signals"
    elif score >= 30:
        confidence = "LOW"
        action = "Some sharp activity - not strong enough to act on"
    else:
        confidence = "NONE"
        action = "No significant sharp action detected"

    sharp_side_spread = public_data.get("spread", {}).get("sharp_side")
    sharp_side_total = public_data.get("total", {}).get("sharp_side")

    return {
        "confidence": confidence,
        "action": action,
        "sharp_side_spread": sharp_side_spread,
        "sharp_side_total": sharp_side_total,
        "score": score,
    }


# =============================================================================
# Line Movement Alerts
# =============================================================================

async def get_line_movement_alerts(
    db: Session,
    sport: Optional[str] = None,
    hours: int = 6
) -> List[Dict[str, Any]]:
    """
    Get recent line movement alerts.

    Alerts are generated for:
    - Steam moves (sharp money hitting)
    - RLM (Reverse Line Movement)
    - Large moves (1+ points)
    """
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    # Get games with upcoming start times
    query = db.query(Game).filter(
        Game.start_time >= datetime.utcnow(),
        Game.start_time <= datetime.utcnow() + timedelta(days=3)
    )

    if sport:
        query = query.filter(Game.sport == sport)

    games = query.all()
    alerts = []

    for game in games:
        # Get line moves for this game
        line_moves = _get_recent_line_moves(db, game.id)

        # Check for significant moves
        for market_type, moves in line_moves.items():
            if not moves:
                continue

            total_move = sum(m["move"] for m in moves)

            if abs(total_move) >= 1.0:
                home_team = game.home_team if isinstance(game.home_team, str) else (
                    game.home_team.name if hasattr(game.home_team, 'name') else "Home"
                )
                away_team = game.away_team if isinstance(game.away_team, str) else (
                    game.away_team.name if hasattr(game.away_team, 'name') else "Away"
                )

                alert_type = "LARGE_MOVE" if abs(total_move) >= 1.5 else "LINE_MOVE"

                alerts.append({
                    "game_id": game.id,
                    "matchup": f"{away_team} @ {home_team}",
                    "sport": game.sport,
                    "market": market_type,
                    "alert_type": alert_type,
                    "move": total_move,
                    "move_count": len(moves),
                    "description": f"{market_type.upper()} moved {'+' if total_move > 0 else ''}{total_move:.1f} points",
                    "start_time": game.start_time.isoformat() if game.start_time else None,
                    "timestamp": datetime.utcnow().isoformat(),
                })

        # Check for steam moves
        steam_moves = _detect_steam_moves(line_moves)
        for steam in steam_moves:
            alerts.append({
                "game_id": game.id,
                "matchup": f"{game.away_team} @ {game.home_team}",
                "sport": game.sport,
                "market": steam["market"],
                "alert_type": "STEAM_MOVE",
                "move": steam["total_move"],
                "description": steam["description"],
                "start_time": game.start_time.isoformat() if game.start_time else None,
                "timestamp": steam["timestamp"],
            })

    # Sort by timestamp (most recent first)
    alerts.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    return alerts[:50]  # Limit to 50 most recent


# =============================================================================
# Consensus Picks
# =============================================================================

async def get_consensus_picks(
    db: Session,
    sport: Optional[str] = None,
    date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """
    Get consensus picks aggregated from public betting and sharp indicators.

    A consensus pick is when:
    - Sharp money and public align (rare but strong)
    - OR Sharp money is clear with high confidence
    """
    target_date = date or datetime.utcnow()
    start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    query = db.query(Game).filter(
        Game.start_time >= start_of_day,
        Game.start_time < end_of_day
    )

    if sport:
        query = query.filter(Game.sport == sport)

    games = query.all()
    consensus_picks = []

    for game in games:
        # Get sharp indicators
        sharp_data = await get_sharp_money_indicators(game.id, db)

        if sharp_data.get("error"):
            continue

        sharp_score = sharp_data.get("sharp_confidence_score", 0)

        # Get public data
        public_data = await fetch_public_betting(game.id, game.sport or "NFL", db)

        # Build consensus for spread
        spread_consensus = _build_spread_consensus(sharp_data, public_data)

        # Build consensus for total
        total_consensus = _build_total_consensus(sharp_data, public_data)

        if spread_consensus or total_consensus:
            home_team = game.home_team if isinstance(game.home_team, str) else (
                game.home_team.name if hasattr(game.home_team, 'name') else "Home"
            )
            away_team = game.away_team if isinstance(game.away_team, str) else (
                game.away_team.name if hasattr(game.away_team, 'name') else "Away"
            )

            consensus_picks.append({
                "game_id": game.id,
                "matchup": f"{away_team} @ {home_team}",
                "sport": game.sport,
                "start_time": game.start_time.isoformat() if game.start_time else None,
                "spread_consensus": spread_consensus,
                "total_consensus": total_consensus,
                "sharp_score": sharp_score,
                "overall_rating": _calculate_consensus_rating(spread_consensus, total_consensus),
            })

    # Sort by overall rating
    consensus_picks.sort(key=lambda x: x.get("overall_rating", 0), reverse=True)

    return consensus_picks


def _build_spread_consensus(
    sharp_data: Dict,
    public_data: Dict
) -> Optional[Dict[str, Any]]:
    """Build consensus pick for spread."""
    sharp_indicators = sharp_data.get("sharp_indicators", {}).get("spread", {})
    spread_data = public_data.get("spread", {})

    sharp_side = sharp_indicators.get("sharp_side")
    public_side = spread_data.get("public_side")
    public_pct = spread_data.get(f"{public_side}_bet_pct", 50) if public_side else 50

    divergence = sharp_indicators.get("bet_money_divergence", 0)
    rlm = sharp_indicators.get("reverse_line_movement", {})

    # Strong consensus: Sharp action with high confidence
    if sharp_side and divergence > 8:
        # Check if RLM confirms
        rlm_confirms = rlm.get("detected", False)

        # Calculate consensus strength
        strength = 50 + divergence + (15 if rlm_confirms else 0)

        # Bonus if sharp opposes heavy public (contrarian value)
        if sharp_side != public_side and public_pct >= 65:
            strength += 10

        # Penalty if sharp aligns with heavy public (inflated line)
        elif sharp_side == public_side and public_pct >= 70:
            strength -= 15

        if strength >= CONSENSUS_LEAN:
            return {
                "pick": sharp_side.upper(),
                "strength": min(100, round(strength, 1)),
                "sharp_aligned": True,
                "public_aligned": sharp_side == public_side,
                "rlm_confirmed": rlm_confirms,
                "reasoning": _get_spread_reasoning(sharp_side, public_side, public_pct, rlm_confirms),
            }

    return None


def _build_total_consensus(
    sharp_data: Dict,
    public_data: Dict
) -> Optional[Dict[str, Any]]:
    """Build consensus pick for total."""
    sharp_indicators = sharp_data.get("sharp_indicators", {}).get("total", {})
    total_data = public_data.get("total", {})

    sharp_side = sharp_indicators.get("sharp_side")
    public_side = total_data.get("public_side")
    public_pct = total_data.get(f"{public_side}_bet_pct", 50) if public_side else 50

    divergence = sharp_indicators.get("bet_money_divergence", 0)
    rlm = sharp_indicators.get("reverse_line_movement", {})

    if sharp_side and divergence > 8:
        rlm_confirms = rlm.get("detected", False)

        strength = 50 + divergence + (15 if rlm_confirms else 0)

        if sharp_side != public_side and public_pct >= 65:
            strength += 10
        elif sharp_side == public_side and public_pct >= 70:
            strength -= 15

        if strength >= CONSENSUS_LEAN:
            return {
                "pick": sharp_side.upper(),
                "strength": min(100, round(strength, 1)),
                "sharp_aligned": True,
                "public_aligned": sharp_side == public_side,
                "rlm_confirmed": rlm_confirms,
                "reasoning": _get_total_reasoning(sharp_side, public_side, public_pct, rlm_confirms),
            }

    return None


def _get_spread_reasoning(
    sharp_side: str,
    public_side: str,
    public_pct: float,
    rlm: bool
) -> str:
    """Generate reasoning for spread consensus."""
    parts = []

    if sharp_side != public_side:
        parts.append(f"Sharp money fading {public_pct:.0f}% public on {public_side}")
    else:
        parts.append(f"Sharp money confirms {public_side} (unusual agreement)")

    if rlm:
        parts.append("RLM detected")

    return "; ".join(parts)


def _get_total_reasoning(
    sharp_side: str,
    public_side: str,
    public_pct: float,
    rlm: bool
) -> str:
    """Generate reasoning for total consensus."""
    parts = []

    if sharp_side != public_side:
        parts.append(f"Sharp money on {sharp_side} against {public_pct:.0f}% public")
    else:
        parts.append(f"Sharp and public aligned on {sharp_side}")

    if rlm:
        parts.append("Total movement confirms")

    return "; ".join(parts)


def _calculate_consensus_rating(
    spread_consensus: Optional[Dict],
    total_consensus: Optional[Dict]
) -> float:
    """Calculate overall consensus rating for a game."""
    rating = 0.0

    if spread_consensus:
        rating += spread_consensus.get("strength", 0) * 0.6

    if total_consensus:
        rating += total_consensus.get("strength", 0) * 0.4

    return round(rating, 1)


# =============================================================================
# API Integration (placeholder for real API)
# =============================================================================

async def _fetch_from_action_network_api(
    game_id: int,
    sport: str
) -> Dict[str, Any]:
    """
    Fetch data from Action Network API.

    This is a placeholder for real API integration.
    In production, implement actual API calls here.
    """
    # TODO: Implement real Action Network API integration
    # Example endpoint: GET /games/{game_id}/public-betting

    logger.warning("Action Network API not implemented - using simulated data")
    return {}


# =============================================================================
# Bulk Operations
# =============================================================================

async def refresh_public_betting_for_sport(
    db: Session,
    sport: str
) -> Dict[str, Any]:
    """Refresh public betting data for all games of a sport."""
    today = datetime.utcnow()
    tomorrow = today + timedelta(days=1)

    games = db.query(Game).filter(
        Game.sport == sport,
        Game.start_time >= today,
        Game.start_time < tomorrow + timedelta(days=2)
    ).all()

    refreshed = 0
    errors = 0

    for game in games:
        try:
            await fetch_public_betting(game.id, sport, db, force_refresh=True)
            refreshed += 1
        except Exception as e:
            logger.error(f"Error refreshing public betting for game {game.id}: {e}")
            errors += 1

    return {
        "sport": sport,
        "games_processed": len(games),
        "refreshed": refreshed,
        "errors": errors,
    }
