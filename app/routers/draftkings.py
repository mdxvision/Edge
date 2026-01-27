"""
DraftKings Sportsbook Router

API endpoints for DraftKings integration:
- Real-time odds
- Events and markets
- Line movement tracking
- Steam move detection
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from app.db import get_db, User
from app.routers.auth import require_auth
from app.services.draftkings import (
    get_live_odds,
    get_event_odds,
    get_best_odds,
    get_events,
    get_live_events,
    get_event_details,
    get_line_movements,
    detect_steam_moves,
    detect_reverse_line_movement,
    get_markets,
    get_player_props,
    DraftKingsClient,
    SPORT_IDS,
    MARKET_TYPES,
)

router = APIRouter(prefix="/draftkings", tags=["DraftKings"])


# =============================================================================
# Odds Endpoints
# =============================================================================

@router.get("/odds/{sport}")
async def get_sport_odds(
    sport: str,
    market_type: str = Query("MONEYLINE", description="Market type: MONEYLINE, SPREAD, TOTAL"),
    user: User = Depends(require_auth)
):
    """
    Get live odds from DraftKings for a sport.

    Returns current moneyline, spread, or total odds for all events.
    """
    sport = sport.upper()
    if sport not in SPORT_IDS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported sport: {sport}. Supported: {list(SPORT_IDS.keys())}"
        )

    market_type = market_type.upper()
    if market_type not in MARKET_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported market type: {market_type}. Supported: {list(MARKET_TYPES.keys())}"
        )

    odds = await get_live_odds(sport, market_type)

    return {
        "sport": sport,
        "market_type": market_type,
        "count": len(odds),
        "odds": [
            {
                "event_id": o.event_id,
                "market_id": o.market_id,
                "selection": o.selection_name,
                "odds_american": o.odds_american,
                "odds_decimal": round(o.odds_decimal, 3),
                "line": o.line,
                "is_live": o.is_live,
            }
            for o in odds
        ],
        "source": "draftkings",
    }


@router.get("/odds/event/{event_id}")
async def get_single_event_odds(
    event_id: str,
    user: User = Depends(require_auth)
):
    """
    Get all odds for a specific event.

    Returns moneyline, spread, and total odds.
    """
    odds = await get_event_odds(event_id)

    if not odds:
        raise HTTPException(status_code=404, detail="Event not found")

    return odds


@router.get("/odds/best/{sport}")
async def get_best_value_odds(
    sport: str,
    limit: int = Query(10, ge=1, le=50, description="Number of events to return"),
    user: User = Depends(require_auth)
):
    """
    Get events with the best odds value (lowest vig).

    Identifies games where DraftKings has the sharpest lines.
    Useful for finding efficient markets.
    """
    sport = sport.upper()
    if sport not in SPORT_IDS:
        raise HTTPException(status_code=400, detail=f"Unsupported sport: {sport}")

    best = await get_best_odds(sport, min_events=limit)

    return {
        "sport": sport,
        "count": len(best),
        "events": best,
        "note": "Lower vig_pct indicates sharper/more efficient odds",
    }


# =============================================================================
# Events Endpoints
# =============================================================================

@router.get("/events/{sport}")
async def get_sport_events(
    sport: str,
    include_live: bool = Query(True, description="Include live in-progress games"),
    user: User = Depends(require_auth)
):
    """
    Get events/games from DraftKings.

    Returns all scheduled and live games for a sport.
    """
    sport = sport.upper()
    if sport not in SPORT_IDS:
        raise HTTPException(status_code=400, detail=f"Unsupported sport: {sport}")

    events = await get_events(sport, include_live=include_live)

    return {
        "sport": sport,
        "count": len(events),
        "live_count": sum(1 for e in events if e.status == "live"),
        "events": [
            {
                "event_id": e.event_id,
                "league": e.league,
                "home_team": e.home_team,
                "away_team": e.away_team,
                "matchup": f"{e.away_team} @ {e.home_team}",
                "start_time": e.start_time.isoformat(),
                "status": e.status,
                "score": f"{e.away_score}-{e.home_score}" if e.home_score is not None else None,
                "period": e.period,
            }
            for e in events
        ],
    }


@router.get("/events/{sport}/live")
async def get_live_sport_events(
    sport: str,
    user: User = Depends(require_auth)
):
    """
    Get only live in-progress events.

    Useful for live betting opportunities.
    """
    sport = sport.upper()
    if sport not in SPORT_IDS:
        raise HTTPException(status_code=400, detail=f"Unsupported sport: {sport}")

    events = await get_live_events(sport)

    return {
        "sport": sport,
        "live_count": len(events),
        "events": [
            {
                "event_id": e.event_id,
                "matchup": f"{e.away_team} @ {e.home_team}",
                "score": f"{e.away_score}-{e.home_score}",
                "period": e.period,
                "start_time": e.start_time.isoformat(),
            }
            for e in events
        ],
    }


@router.get("/event/{event_id}")
async def get_event(
    event_id: str,
    user: User = Depends(require_auth)
):
    """
    Get detailed information for a specific event.

    Includes event info and available markets.
    """
    event = await get_event_details(event_id)

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return {
        "event_id": event.event_id,
        "sport": event.sport,
        "league": event.league,
        "home_team": event.home_team,
        "away_team": event.away_team,
        "matchup": f"{event.away_team} @ {event.home_team}",
        "start_time": event.start_time.isoformat(),
        "status": event.status,
        "score": {
            "home": event.home_score,
            "away": event.away_score,
        } if event.home_score is not None else None,
        "period": event.period,
        "markets": event.markets,
    }


# =============================================================================
# Line Movement Endpoints
# =============================================================================

@router.get("/lines/{event_id}")
async def get_event_line_movements(
    event_id: str,
    market_type: str = Query("SPREAD", description="Market type: SPREAD, TOTAL, MONEYLINE"),
    user: User = Depends(require_auth)
):
    """
    Get line movement history for an event.

    Shows how lines have moved since opening.
    """
    movements = await get_line_movements(event_id, market_type)

    return {
        "event_id": event_id,
        "market_type": market_type,
        "movements": [
            {
                "market_type": m.market_type,
                "selection": m.selection,
                "opening_line": m.opening_line,
                "current_line": m.current_line,
                "movement": m.movement,
                "movement_pct": round(m.movement_pct, 2),
                "direction": m.direction,
                "opening_odds": m.opening_odds,
                "current_odds": m.current_odds,
                "history": m.timestamps,
            }
            for m in movements
        ],
    }


@router.get("/lines/steam/{sport}")
async def get_steam_moves(
    sport: str,
    user: User = Depends(require_auth)
):
    """
    Detect steam moves (sharp money line movements).

    Returns events where lines have moved significantly in one direction,
    indicating sharp bettor activity.

    **Usage:** Steam moves often signal professional/sharp money.
    """
    sport = sport.upper()
    if sport not in SPORT_IDS:
        raise HTTPException(status_code=400, detail=f"Unsupported sport: {sport}")

    steam = await detect_steam_moves(sport)

    return {
        "sport": sport,
        "steam_moves_detected": len(steam),
        "moves": steam,
        "note": "HIGH = 2+ point movement, MEDIUM = 1-2 point movement",
    }


@router.get("/lines/rlm/{sport}")
async def get_reverse_line_movement(
    sport: str,
    user: User = Depends(require_auth)
):
    """
    Detect reverse line movement (RLM).

    RLM occurs when lines move opposite to public betting percentages,
    indicating sharp money on the opposite side.

    **Usage:** RLM is a strong indicator of where sharps are betting.
    """
    sport = sport.upper()
    if sport not in SPORT_IDS:
        raise HTTPException(status_code=400, detail=f"Unsupported sport: {sport}")

    rlm = await detect_reverse_line_movement(sport)

    return {
        "sport": sport,
        "rlm_alerts": len(rlm),
        "alerts": rlm,
    }


# =============================================================================
# Markets Endpoints
# =============================================================================

@router.get("/markets/{event_id}")
async def get_event_markets(
    event_id: str,
    market_types: Optional[str] = Query(None, description="Comma-separated market types to filter"),
    user: User = Depends(require_auth)
):
    """
    Get all available markets for an event.

    Returns main markets (moneyline, spread, total) and props.
    """
    types = market_types.split(",") if market_types else None
    markets = await get_markets(event_id, types)

    return {
        "event_id": event_id,
        "market_count": len(markets),
        "markets": markets,
    }


@router.get("/props/{event_id}")
async def get_event_player_props(
    event_id: str,
    player: Optional[str] = Query(None, description="Filter by player name"),
    user: User = Depends(require_auth)
):
    """
    Get player prop markets for an event.

    Returns all player props or filtered by specific player.
    """
    props = await get_player_props(event_id, player)

    return {
        "event_id": event_id,
        "player_filter": player,
        "prop_count": len(props),
        "props": props,
    }


# =============================================================================
# Status Endpoints
# =============================================================================

@router.get("/status")
async def get_draftkings_status():
    """
    Get DraftKings API configuration status.

    Shows whether API is configured and available sports.
    """
    client = DraftKingsClient()

    return {
        "configured": client.is_configured,
        "mode": "live" if client.is_configured else "simulation",
        "supported_sports": list(SPORT_IDS.keys()),
        "supported_markets": list(MARKET_TYPES.keys()),
        "note": "Set DRAFTKINGS_API_KEY and DRAFTKINGS_API_SECRET environment variables for live data",
    }


@router.get("/demo")
async def get_demo_data():
    """
    Get demo DraftKings data (no auth required).

    Shows sample odds and events for testing.
    """
    odds = await get_live_odds("NFL", "MONEYLINE")
    events = await get_events("NFL")

    return {
        "demo": True,
        "description": "Sample DraftKings data for NFL",
        "odds_count": len(odds),
        "sample_odds": [
            {
                "event_id": o.event_id,
                "selection": o.selection_name,
                "odds": o.odds_american,
            }
            for o in odds[:6]
        ],
        "events_count": len(events),
        "sample_events": [
            {
                "event_id": e.event_id,
                "matchup": f"{e.away_team} @ {e.home_team}",
                "status": e.status,
            }
            for e in events[:3]
        ],
    }


# =============================================================================
# Comparison Endpoints
# =============================================================================

@router.get("/compare/odds/{event_id}")
async def compare_odds_to_fair_value(
    event_id: str,
    home_fair_prob: float = Query(..., ge=0, le=1, description="Fair probability for home team"),
    user: User = Depends(require_auth)
):
    """
    Compare DraftKings odds to your calculated fair value.

    Input your model's fair probability to see if there's an edge.
    """
    odds = await get_event_odds(event_id)

    if not odds or "moneyline" not in odds:
        raise HTTPException(status_code=404, detail="Event odds not found")

    home_odds = odds["moneyline"].get("home", 0)
    away_odds = odds["moneyline"].get("away", 0)

    # Calculate implied probabilities
    if home_odds < 0:
        dk_home_prob = abs(home_odds) / (abs(home_odds) + 100)
    else:
        dk_home_prob = 100 / (home_odds + 100)

    if away_odds < 0:
        dk_away_prob = abs(away_odds) / (abs(away_odds) + 100)
    else:
        dk_away_prob = 100 / (away_odds + 100)

    away_fair_prob = 1 - home_fair_prob

    # Calculate edges
    home_edge = (home_fair_prob - dk_home_prob) * 100
    away_edge = (away_fair_prob - dk_away_prob) * 100

    # Determine recommendation
    if home_edge >= 3:
        recommendation = f"HOME has +{home_edge:.1f}% edge"
    elif away_edge >= 3:
        recommendation = f"AWAY has +{away_edge:.1f}% edge"
    else:
        recommendation = "No significant edge detected"

    return {
        "event_id": event_id,
        "draftkings_odds": {
            "home": home_odds,
            "away": away_odds,
        },
        "draftkings_implied": {
            "home": round(dk_home_prob, 4),
            "away": round(dk_away_prob, 4),
            "vig": round((dk_home_prob + dk_away_prob - 1) * 100, 2),
        },
        "your_fair_value": {
            "home": round(home_fair_prob, 4),
            "away": round(away_fair_prob, 4),
        },
        "edge": {
            "home": round(home_edge, 2),
            "away": round(away_edge, 2),
        },
        "recommendation": recommendation,
    }
