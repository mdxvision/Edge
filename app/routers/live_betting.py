"""
Live Betting Router

API endpoints for real-time in-game predictions:
- Live win probability
- Momentum detection
- Live edge alerts
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from app.db import get_db, User
from app.routers.auth import require_auth
from app.services.live_betting import (
    LiveGameState,
    GameStatus,
    calculate_win_probability,
    analyze_momentum,
    calculate_live_edges,
    generate_live_alerts,
    analyze_live_game,
    simulate_live_game,
)

router = APIRouter(prefix="/live", tags=["Live Betting"])


# =============================================================================
# Request/Response Models
# =============================================================================

class LiveGameInput(BaseModel):
    """Input model for live game analysis."""
    game_id: str = Field(..., description="Unique game identifier")
    sport: str = Field(..., description="Sport code (NFL, NBA, MLB, NHL, SOCCER)")
    home_team: str = Field(..., description="Home team name")
    away_team: str = Field(..., description="Away team name")
    home_score: int = Field(..., ge=0, description="Home team score")
    away_score: int = Field(..., ge=0, description="Away team score")
    period: str = Field(..., description="Current period (Q1, Q2, 1st Half, etc.)")
    time_remaining: str = Field(..., description="Time remaining (e.g., '5:30')")

    # Optional odds for edge calculation
    home_ml_odds: Optional[int] = Field(None, description="Home moneyline odds")
    away_ml_odds: Optional[int] = Field(None, description="Away moneyline odds")
    live_spread: Optional[float] = Field(None, description="Current live spread")
    live_total: Optional[float] = Field(None, description="Current live total")

    # Optional scoring history
    scoring_plays: Optional[List[dict]] = Field(
        None,
        description="List of scoring plays [{team: 'home'|'away', points: int}]"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "game_id": "nfl_2024_wk10_kc_buf",
                "sport": "NFL",
                "home_team": "Buffalo Bills",
                "away_team": "Kansas City Chiefs",
                "home_score": 21,
                "away_score": 17,
                "period": "Q3",
                "time_remaining": "8:45",
                "home_ml_odds": -150,
                "away_ml_odds": 130,
                "live_spread": -2.5,
                "live_total": 48.5
            }
        }


class ProbabilityResponse(BaseModel):
    """Win probability response."""
    home_win_prob: float
    away_win_prob: float
    tie_prob: float = 0.0
    confidence: float
    model_used: str
    factors: List[str]


class MomentumResponse(BaseModel):
    """Momentum analysis response."""
    level: str
    score: float
    trend: str
    recent_scoring: dict
    key_events: List[str]


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/analyze")
async def analyze_game(
    game_input: LiveGameInput,
    user: User = Depends(require_auth)
):
    """
    Perform complete live game analysis.

    Returns:
    - Win probability for both teams
    - Momentum analysis
    - Live betting edges (if odds provided)
    - Alerts for significant opportunities

    **Usage:** Call this endpoint with live game data to get real-time predictions.
    """
    # Convert input to LiveGameState
    state = LiveGameState(
        game_id=game_input.game_id,
        sport=game_input.sport.upper(),
        home_team=game_input.home_team,
        away_team=game_input.away_team,
        home_score=game_input.home_score,
        away_score=game_input.away_score,
        period=game_input.period,
        time_remaining=game_input.time_remaining,
        status=GameStatus.IN_PROGRESS,
        scoring_plays=game_input.scoring_plays or [],
    )

    # Build odds dict if provided
    current_odds = {}
    if game_input.home_ml_odds:
        current_odds["home_ml"] = game_input.home_ml_odds
    if game_input.away_ml_odds:
        current_odds["away_ml"] = game_input.away_ml_odds
    if game_input.live_spread is not None:
        current_odds["live_spread"] = game_input.live_spread
    if game_input.live_total is not None:
        current_odds["live_total"] = game_input.live_total

    # Perform analysis
    result = analyze_live_game(state, current_odds if current_odds else None)

    return result


@router.post("/probability")
async def get_win_probability(
    game_input: LiveGameInput,
    user: User = Depends(require_auth)
):
    """
    Calculate win probability for a live game.

    Uses sport-specific models:
    - NFL: Time-score model with home field adjustment
    - NBA: Possession-based model accounting for high variance
    - MLB: Run expectancy model with batting order consideration
    - NHL: Goal expectancy with OT probability
    - Soccer: Poisson model with draw probability

    Returns probability for each outcome with confidence level.
    """
    state = LiveGameState(
        game_id=game_input.game_id,
        sport=game_input.sport.upper(),
        home_team=game_input.home_team,
        away_team=game_input.away_team,
        home_score=game_input.home_score,
        away_score=game_input.away_score,
        period=game_input.period,
        time_remaining=game_input.time_remaining,
        status=GameStatus.IN_PROGRESS,
    )

    probability = calculate_win_probability(state)

    return {
        "game_id": game_input.game_id,
        "matchup": f"{game_input.away_team} @ {game_input.home_team}",
        "score": f"{game_input.away_score}-{game_input.home_score}",
        "period": game_input.period,
        "probability": {
            "home_win": probability.home_win_prob,
            "away_win": probability.away_win_prob,
            "tie": probability.tie_prob,
        },
        "confidence": probability.confidence,
        "model": probability.model_used,
        "factors": probability.factors,
    }


@router.post("/momentum")
async def get_momentum_analysis(
    game_input: LiveGameInput,
    user: User = Depends(require_auth)
):
    """
    Analyze game momentum based on recent scoring.

    Requires scoring_plays in the input for accurate analysis.

    Returns:
    - Momentum level (strong_home, moderate_home, neutral, moderate_away, strong_away)
    - Momentum score (-100 to 100)
    - Trend (increasing_home, stable, increasing_away)
    - Key events affecting momentum

    **Usage:** Identify momentum shifts that may not be reflected in odds yet.
    """
    if not game_input.scoring_plays:
        return {
            "game_id": game_input.game_id,
            "momentum": {
                "level": "neutral",
                "score": 0,
                "trend": "stable",
            },
            "note": "Provide scoring_plays for detailed momentum analysis",
        }

    state = LiveGameState(
        game_id=game_input.game_id,
        sport=game_input.sport.upper(),
        home_team=game_input.home_team,
        away_team=game_input.away_team,
        home_score=game_input.home_score,
        away_score=game_input.away_score,
        period=game_input.period,
        time_remaining=game_input.time_remaining,
        status=GameStatus.IN_PROGRESS,
        scoring_plays=game_input.scoring_plays,
    )

    momentum = analyze_momentum(state)

    return {
        "game_id": game_input.game_id,
        "matchup": f"{game_input.away_team} @ {game_input.home_team}",
        "momentum": {
            "level": momentum.level.value,
            "score": momentum.score,
            "trend": momentum.trend,
            "recent_scoring": momentum.recent_scoring,
        },
        "key_events": momentum.key_events,
    }


@router.post("/edges")
async def find_live_edges(
    game_input: LiveGameInput,
    user: User = Depends(require_auth)
):
    """
    Find live betting edges by comparing model probabilities to current odds.

    Requires odds (home_ml_odds, away_ml_odds) in the input.

    Returns edges where our model probability exceeds implied probability by 3%+.

    **Usage:** Identify value bets in real-time as odds shift.
    """
    if not game_input.home_ml_odds and not game_input.away_ml_odds:
        raise HTTPException(
            status_code=400,
            detail="Provide home_ml_odds and/or away_ml_odds for edge calculation"
        )

    state = LiveGameState(
        game_id=game_input.game_id,
        sport=game_input.sport.upper(),
        home_team=game_input.home_team,
        away_team=game_input.away_team,
        home_score=game_input.home_score,
        away_score=game_input.away_score,
        period=game_input.period,
        time_remaining=game_input.time_remaining,
        status=GameStatus.IN_PROGRESS,
    )

    probability = calculate_win_probability(state)

    current_odds = {
        "home_ml": game_input.home_ml_odds or 0,
        "away_ml": game_input.away_ml_odds or 0,
    }
    if game_input.live_spread is not None:
        current_odds["live_spread"] = game_input.live_spread
    if game_input.live_total is not None:
        current_odds["live_total"] = game_input.live_total

    edges = calculate_live_edges(state, probability, current_odds)

    return {
        "game_id": game_input.game_id,
        "matchup": f"{game_input.away_team} @ {game_input.home_team}",
        "model_probability": {
            "home_win": probability.home_win_prob,
            "away_win": probability.away_win_prob,
        },
        "edges": [
            {
                "type": e.edge_type,
                "side": e.side,
                "current_line": e.current_line,
                "fair_value": e.fair_value,
                "edge_pct": e.edge_pct,
                "confidence": e.confidence,
                "recommendation": e.recommendation,
            }
            for e in edges
        ],
        "edges_found": len(edges),
    }


@router.get("/simulate/{sport}")
async def get_simulated_game(
    sport: str,
    game_id: Optional[str] = Query(None, description="Custom game ID"),
    user: User = Depends(require_auth)
):
    """
    Get a simulated live game for testing.

    Generates realistic game state with scores, period, and scoring plays.

    **Usage:** Test the live betting model without real game data.
    """
    sport = sport.upper()
    if sport not in ["NFL", "NBA", "MLB", "NHL", "SOCCER"]:
        raise HTTPException(status_code=400, detail=f"Unsupported sport: {sport}")

    gid = game_id or f"sim_{sport.lower()}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    state = simulate_live_game(sport, gid)

    # Also run analysis on simulated game
    current_odds = {
        "home_ml": state.home_ml_odds,
        "away_ml": state.away_ml_odds,
    }
    if state.total_line:
        current_odds["live_total"] = state.total_line + (state.home_score + state.away_score) * 0.5

    result = analyze_live_game(state, current_odds)

    return {
        "simulated": True,
        **result
    }


@router.get("/demo")
async def get_demo_analysis():
    """
    Get a demo live game analysis (no auth required).

    Shows sample output from the live betting model.
    """
    # Create a demo NFL game
    state = LiveGameState(
        game_id="demo_nfl_game",
        sport="NFL",
        home_team="Buffalo Bills",
        away_team="Kansas City Chiefs",
        home_score=24,
        away_score=21,
        period="Q4",
        time_remaining="4:35",
        status=GameStatus.IN_PROGRESS,
        scoring_plays=[
            {"team": "away", "points": 7, "time": "12:00"},
            {"team": "home", "points": 3, "time": "8:30"},
            {"team": "home", "points": 7, "time": "5:15"},
            {"team": "away", "points": 7, "time": "2:00"},
            {"team": "home", "points": 7, "time": "14:00"},
            {"team": "away", "points": 7, "time": "10:30"},
            {"team": "home", "points": 7, "time": "6:45"},
        ],
        home_spread=-2.5,
        total_line=52.5,
        home_ml_odds=-140,
        away_ml_odds=120,
    )

    current_odds = {
        "home_ml": -140,
        "away_ml": 120,
        "live_spread": -1.5,
        "live_total": 51.5,
    }

    result = analyze_live_game(state, current_odds)

    return {
        "demo": True,
        "description": "Sample NFL game in 4th quarter with home team leading by 3",
        **result
    }


# =============================================================================
# Bulk Analysis Endpoints
# =============================================================================

@router.post("/analyze/bulk")
async def analyze_multiple_games(
    games: List[LiveGameInput],
    user: User = Depends(require_auth)
):
    """
    Analyze multiple live games at once.

    Returns analysis for each game sorted by edge magnitude.

    **Usage:** Monitor multiple games simultaneously for opportunities.
    """
    if len(games) > 20:
        raise HTTPException(
            status_code=400,
            detail="Maximum 20 games per request"
        )

    results = []

    for game_input in games:
        state = LiveGameState(
            game_id=game_input.game_id,
            sport=game_input.sport.upper(),
            home_team=game_input.home_team,
            away_team=game_input.away_team,
            home_score=game_input.home_score,
            away_score=game_input.away_score,
            period=game_input.period,
            time_remaining=game_input.time_remaining,
            status=GameStatus.IN_PROGRESS,
            scoring_plays=game_input.scoring_plays or [],
        )

        current_odds = {}
        if game_input.home_ml_odds:
            current_odds["home_ml"] = game_input.home_ml_odds
        if game_input.away_ml_odds:
            current_odds["away_ml"] = game_input.away_ml_odds
        if game_input.live_spread is not None:
            current_odds["live_spread"] = game_input.live_spread
        if game_input.live_total is not None:
            current_odds["live_total"] = game_input.live_total

        result = analyze_live_game(state, current_odds if current_odds else None)
        results.append(result)

    # Sort by max edge found
    results.sort(
        key=lambda x: max([e.get("edge_pct", 0) for e in x.get("edges", [])] or [0]),
        reverse=True
    )

    return {
        "games_analyzed": len(results),
        "results": results,
        "games_with_edges": sum(1 for r in results if r.get("edges")),
    }


@router.get("/alerts/active")
async def get_active_alerts(
    sport: Optional[str] = Query(None, description="Filter by sport"),
    min_edge: float = Query(3.0, ge=0, le=20, description="Minimum edge percentage"),
    user: User = Depends(require_auth)
):
    """
    Get all active live betting alerts.

    Returns alerts from recently analyzed games that haven't expired.

    **Usage:** Monitor for actionable live betting opportunities.
    """
    # In production, this would pull from a cache/database of active alerts
    # For now, return a simulated response
    return {
        "sport_filter": sport,
        "min_edge": min_edge,
        "active_alerts": [],
        "note": "Alerts are generated when games are analyzed via /live/analyze",
    }


# =============================================================================
# Model Information
# =============================================================================

@router.get("/models")
async def get_model_info():
    """
    Get information about the live betting models.

    Returns details about the probability models used for each sport.
    """
    return {
        "models": {
            "NFL": {
                "name": "nfl_time_score",
                "description": "Logistic model using score differential and time remaining",
                "factors": [
                    "Score differential",
                    "Time remaining",
                    "Home field advantage (~2.5 points)",
                    "Quarter adjustments"
                ],
                "confidence_range": "0.5 - 0.9 based on game progress"
            },
            "NBA": {
                "name": "nba_possession",
                "description": "Possession-based model accounting for high variance",
                "factors": [
                    "Score differential",
                    "Possessions remaining",
                    "Home court advantage (~3 points)",
                    "Garbage time detection"
                ],
                "confidence_range": "0.5 - 0.85 based on game progress"
            },
            "MLB": {
                "name": "mlb_run_expectancy",
                "description": "Run expectancy model with inning considerations",
                "factors": [
                    "Run differential",
                    "Innings remaining",
                    "Home team bats last advantage",
                    "Half-inning position"
                ],
                "confidence_range": "0.5 - 0.9 based on game progress"
            },
            "NHL": {
                "name": "nhl_goal_expectancy",
                "description": "Goal expectancy model with OT probability",
                "factors": [
                    "Goal differential",
                    "Time remaining",
                    "Home ice advantage",
                    "Overtime probability"
                ],
                "confidence_range": "0.5 - 0.9 based on game progress"
            },
            "SOCCER": {
                "name": "soccer_poisson",
                "description": "Poisson-based model with draw probability",
                "factors": [
                    "Goal differential",
                    "Minutes remaining",
                    "Draw probability",
                    "Home field advantage"
                ],
                "confidence_range": "0.45 - 0.8 based on game progress"
            }
        },
        "edge_detection": {
            "minimum_edge": "3% for consideration",
            "high_edge": "5%+ for strong recommendation",
            "expiration": "5 minutes (odds change quickly)"
        },
        "momentum_detection": {
            "scoring_plays_required": "Minimum 2 for analysis",
            "lookback": "Last 5-8 scoring plays",
            "levels": ["strong_home", "moderate_home", "neutral", "moderate_away", "strong_away"]
        }
    }
