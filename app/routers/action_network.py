"""
Action Network Integration Router

API endpoints for public betting percentages, sharp money indicators,
line movement alerts, and consensus picks from Action Network data.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.db import get_db, User
from app.routers.auth import require_auth
from app.services import action_network

router = APIRouter(prefix="/action-network", tags=["Action Network"])


# =============================================================================
# Public Betting Percentages
# =============================================================================

@router.get("/public-betting/{game_id}")
async def get_public_betting(
    game_id: int,
    force_refresh: bool = Query(False, description="Force refresh from source"),
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Get public betting percentages for a game.

    Returns:
    - Spread: bet %, money %, public side, sharp side
    - Moneyline: bet %, money %
    - Total: bet %, money %, public side, sharp side
    - Ticket count estimate
    - Sharp vs public divergence indicator
    - Fade signals

    **Data Source:** Action Network aggregated data
    """
    result = await action_network.fetch_public_betting(
        game_id=game_id,
        sport="NFL",  # Will be overridden by game lookup
        db=db,
        force_refresh=force_refresh
    )

    if not result or "error" in result:
        raise HTTPException(
            status_code=404,
            detail=result.get("error", "Game not found")
        )

    return result


@router.get("/public-betting")
async def get_public_betting_bulk(
    sport: str = Query(..., description="Sport code (NFL, NBA, MLB, etc.)"),
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Get public betting percentages for all games of a sport on a date.

    Returns aggregated public betting data for games.
    """
    from app.db import Game
    from datetime import timedelta

    # Parse date
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        target_date = datetime.utcnow()

    start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    games = db.query(Game).filter(
        Game.sport == sport,
        Game.start_time >= start_of_day,
        Game.start_time < end_of_day
    ).all()

    results = []
    for game in games:
        try:
            data = await action_network.fetch_public_betting(
                game_id=game.id,
                sport=sport,
                db=db
            )
            if data and "error" not in data:
                # Add game info
                home_team = game.home_team if isinstance(game.home_team, str) else (
                    game.home_team.name if hasattr(game.home_team, 'name') else "Home"
                )
                away_team = game.away_team if isinstance(game.away_team, str) else (
                    game.away_team.name if hasattr(game.away_team, 'name') else "Away"
                )

                data["matchup"] = f"{away_team} @ {home_team}"
                data["start_time"] = game.start_time.isoformat() if game.start_time else None
                results.append(data)
        except Exception:
            pass

    return {
        "sport": sport,
        "date": target_date.date().isoformat(),
        "games": results,
        "count": len(results)
    }


# =============================================================================
# Sharp Money Indicators
# =============================================================================

@router.get("/sharp-money/{game_id}")
async def get_sharp_money(
    game_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Get sharp money indicators for a game.

    Analyzes:
    - Bet % vs Money % divergence (indicates big bettors)
    - Reverse Line Movement (RLM) - line moves opposite to public
    - Steam moves - sudden sharp action across books

    Returns a sharp confidence score (0-100) and recommendations.

    **Key Indicators:**
    - Score 70+: Strong sharp action - consider following
    - Score 50-69: Moderate indicators - monitor
    - Score <50: No significant sharp action
    """
    result = await action_network.get_sharp_money_indicators(game_id, db)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/sharp-money")
async def get_sharp_money_bulk(
    sport: Optional[str] = Query(None, description="Filter by sport"),
    min_score: float = Query(50, ge=0, le=100, description="Minimum sharp score"),
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Get games with significant sharp money action.

    Returns all upcoming games that meet the minimum sharp score threshold.
    Default threshold is 50 (moderate+ sharp action).
    """
    from app.db import Game
    from datetime import timedelta

    query = db.query(Game).filter(
        Game.start_time >= datetime.utcnow(),
        Game.start_time <= datetime.utcnow() + timedelta(days=3)
    )

    if sport:
        query = query.filter(Game.sport == sport)

    games = query.limit(50).all()

    results = []
    for game in games:
        try:
            data = await action_network.get_sharp_money_indicators(game.id, db)
            if data.get("sharp_confidence_score", 0) >= min_score:
                results.append(data)
        except Exception:
            pass

    # Sort by sharp score
    results.sort(key=lambda x: x.get("sharp_confidence_score", 0), reverse=True)

    return {
        "min_score": min_score,
        "sport_filter": sport,
        "games": results,
        "count": len(results)
    }


# =============================================================================
# Line Movement Alerts
# =============================================================================

@router.get("/alerts")
async def get_line_alerts(
    sport: Optional[str] = Query(None, description="Filter by sport"),
    hours: int = Query(6, ge=1, le=48, description="Hours to look back"),
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Get recent line movement alerts.

    Alert types:
    - STEAM_MOVE: Sharp money hitting multiple books quickly
    - LARGE_MOVE: Significant line movement (1.5+ points)
    - LINE_MOVE: Notable movement (1+ points)

    Useful for identifying:
    - Sharp action coming in
    - Injury/news affecting lines
    - Value opportunities before lines adjust
    """
    alerts = await action_network.get_line_movement_alerts(
        db=db,
        sport=sport,
        hours=hours
    )

    return {
        "hours": hours,
        "sport_filter": sport,
        "alerts": alerts,
        "count": len(alerts)
    }


@router.get("/alerts/steam")
async def get_steam_moves(
    sport: Optional[str] = Query(None, description="Filter by sport"),
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Get steam move alerts only.

    Steam moves are sudden, sharp line movements across multiple books,
    typically indicating professional betting action.
    """
    all_alerts = await action_network.get_line_movement_alerts(
        db=db,
        sport=sport,
        hours=12
    )

    steam_only = [a for a in all_alerts if a.get("alert_type") == "STEAM_MOVE"]

    return {
        "sport_filter": sport,
        "alerts": steam_only,
        "count": len(steam_only)
    }


# =============================================================================
# Consensus Picks
# =============================================================================

@router.get("/consensus")
async def get_consensus_picks(
    sport: Optional[str] = Query(None, description="Filter by sport"),
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    min_rating: float = Query(50, ge=0, le=100, description="Minimum consensus rating"),
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Get consensus picks based on sharp money and public betting analysis.

    Consensus is determined by:
    1. Sharp money indicators (bet % vs money % divergence)
    2. Reverse Line Movement confirmation
    3. Public betting alignment/opposition

    **Rating System:**
    - 75+: Strong consensus - high confidence pick
    - 60-74: Moderate consensus - good lean
    - 50-59: Weak consensus - slight edge

    Best value is often when sharp money opposes heavy public action.
    """
    # Parse date
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        target_date = datetime.utcnow()

    picks = await action_network.get_consensus_picks(
        db=db,
        sport=sport,
        date=target_date
    )

    # Filter by minimum rating
    filtered = [p for p in picks if p.get("overall_rating", 0) >= min_rating]

    return {
        "date": target_date.date().isoformat(),
        "sport_filter": sport,
        "min_rating": min_rating,
        "picks": filtered,
        "count": len(filtered)
    }


@router.get("/consensus/{game_id}")
async def get_game_consensus(
    game_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Get detailed consensus analysis for a specific game.

    Returns both spread and total consensus picks with:
    - Pick direction (home/away, over/under)
    - Strength score
    - Sharp alignment
    - Public alignment
    - RLM confirmation
    - Reasoning explanation
    """
    from app.db import Game

    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Get sharp indicators
    sharp_data = await action_network.get_sharp_money_indicators(game_id, db)

    # Get public betting
    public_data = await action_network.fetch_public_betting(
        game_id, game.sport or "NFL", db
    )

    # Build consensus
    spread_consensus = action_network._build_spread_consensus(sharp_data, public_data)
    total_consensus = action_network._build_total_consensus(sharp_data, public_data)

    home_team = game.home_team if isinstance(game.home_team, str) else (
        game.home_team.name if hasattr(game.home_team, 'name') else "Home"
    )
    away_team = game.away_team if isinstance(game.away_team, str) else (
        game.away_team.name if hasattr(game.away_team, 'name') else "Away"
    )

    return {
        "game_id": game_id,
        "matchup": f"{away_team} @ {home_team}",
        "sport": game.sport,
        "start_time": game.start_time.isoformat() if game.start_time else None,
        "spread_consensus": spread_consensus,
        "total_consensus": total_consensus,
        "sharp_analysis": sharp_data.get("sharp_indicators"),
        "public_betting": public_data,
        "overall_rating": action_network._calculate_consensus_rating(
            spread_consensus, total_consensus
        ),
    }


# =============================================================================
# Fade Public Plays
# =============================================================================

@router.get("/fade-public")
async def get_fade_public_plays(
    sport: Optional[str] = Query(None, description="Filter by sport"),
    min_public_pct: float = Query(70, ge=50, le=90, description="Minimum public percentage to fade"),
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Get fade-the-public plays.

    Returns games where:
    - Public is heavily on one side (default 70%+)
    - Sharp money is on the opposite side
    - Line movement supports the fade

    Historical edge from fading 70%+ public: ~54% win rate
    Historical edge from fading 80%+ public: ~57% win rate

    Best used as part of a multi-factor approach, not standalone.
    """
    from app.db import Game
    from datetime import timedelta

    query = db.query(Game).filter(
        Game.start_time >= datetime.utcnow(),
        Game.start_time <= datetime.utcnow() + timedelta(days=3)
    )

    if sport:
        query = query.filter(Game.sport == sport)

    games = query.all()

    fade_plays = []
    for game in games:
        try:
            public_data = await action_network.fetch_public_betting(
                game.id, game.sport or "NFL", db
            )

            spread_data = public_data.get("spread", {})
            total_data = public_data.get("total", {})

            # Check for fade opportunities
            spread_fade = None
            total_fade = None

            max_spread_pct = max(
                spread_data.get("home_bet_pct", 50),
                spread_data.get("away_bet_pct", 50)
            )

            if max_spread_pct >= min_public_pct:
                public_side = spread_data.get("public_side")
                sharp_side = spread_data.get("sharp_side")

                # Best fades: sharp opposite public
                if sharp_side and sharp_side != public_side:
                    historical_edge = _calculate_historical_edge(max_spread_pct)
                    spread_fade = {
                        "public_side": public_side,
                        "public_pct": max_spread_pct,
                        "fade_side": sharp_side,
                        "sharp_confirmed": True,
                        "historical_edge": historical_edge,
                    }

            max_total_pct = max(
                total_data.get("over_bet_pct", 50),
                total_data.get("under_bet_pct", 50)
            )

            if max_total_pct >= min_public_pct:
                public_side = total_data.get("public_side")
                sharp_side = total_data.get("sharp_side")

                if sharp_side and sharp_side != public_side:
                    historical_edge = _calculate_historical_edge(max_total_pct)
                    total_fade = {
                        "public_side": public_side,
                        "public_pct": max_total_pct,
                        "fade_side": sharp_side,
                        "sharp_confirmed": True,
                        "historical_edge": historical_edge,
                    }

            if spread_fade or total_fade:
                home_team = game.home_team if isinstance(game.home_team, str) else (
                    game.home_team.name if hasattr(game.home_team, 'name') else "Home"
                )
                away_team = game.away_team if isinstance(game.away_team, str) else (
                    game.away_team.name if hasattr(game.away_team, 'name') else "Away"
                )

                fade_plays.append({
                    "game_id": game.id,
                    "matchup": f"{away_team} @ {home_team}",
                    "sport": game.sport,
                    "start_time": game.start_time.isoformat() if game.start_time else None,
                    "spread_fade": spread_fade,
                    "total_fade": total_fade,
                })

        except Exception:
            pass

    # Sort by highest public percentage
    fade_plays.sort(
        key=lambda x: max(
            (x.get("spread_fade") or {}).get("public_pct", 0),
            (x.get("total_fade") or {}).get("public_pct", 0)
        ),
        reverse=True
    )

    return {
        "min_public_pct": min_public_pct,
        "sport_filter": sport,
        "plays": fade_plays,
        "count": len(fade_plays)
    }


def _calculate_historical_edge(public_pct: float) -> str:
    """Calculate historical edge from fading given public percentage."""
    if public_pct >= 80:
        return "+7.0%"  # ~57% win rate
    elif public_pct >= 75:
        return "+5.2%"  # ~55.5% win rate
    elif public_pct >= 70:
        return "+3.8%"  # ~54% win rate
    else:
        return "+2.0%"


# =============================================================================
# Configuration Status
# =============================================================================

@router.get("/status")
def get_action_network_status():
    """
    Check Action Network integration status.

    Returns whether the API is configured and data freshness info.
    """
    return {
        "configured": action_network.is_action_network_configured(),
        "source": "Action Network" if action_network.is_action_network_configured() else "Simulated",
        "features": {
            "public_betting": True,
            "sharp_money": True,
            "line_alerts": True,
            "consensus_picks": True,
        },
        "data_refresh_interval": "15 minutes",
        "note": "Without API key, realistic simulated data is provided"
    }


# =============================================================================
# Admin - Refresh Data
# =============================================================================

@router.post("/refresh/{sport}")
async def refresh_public_betting(
    sport: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Refresh public betting data for a sport.

    Admin endpoint to force refresh data for all games of a sport.
    """
    # Simple access check (could be more robust)
    if user.subscription_tier != "pro":
        raise HTTPException(status_code=403, detail="Pro subscription required")

    result = await action_network.refresh_public_betting_for_sport(db, sport)

    return result
