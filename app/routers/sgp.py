"""
Same Game Parlay (SGP) Builder Router

AI-assisted SGP construction with correlation analysis.
"""

from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field

from app.db import get_db
from app.services.sgp import (
    analyze_sgp_correlations,
    calculate_sgp_odds,
    calculate_sgp_ev,
    get_sgp_risk_score,
    suggest_sgp_legs,
    build_custom_sgp,
    classify_leg,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/sgp", tags=["Same Game Parlay"])


class SGPLeg(BaseModel):
    """A single leg in an SGP."""
    selection: str = Field(..., description="Selection name (e.g., 'Lakers -5.5')")
    market_type: str = Field(..., description="Market type (h2h, spreads, totals, player_prop)")
    odds: int = Field(..., description="American odds (e.g., -110)")
    probability: Optional[float] = Field(None, description="Estimated win probability (0-1)")
    point: Optional[float] = Field(None, description="Line value (e.g., -5.5 for spread)")
    player_name: Optional[str] = Field(None, description="Player name for props")
    prop_type: Optional[str] = Field(None, description="Prop type (passing_yards, points, etc.)")
    is_favorite: Optional[bool] = Field(None, description="Is this the favorite side")


class SGPRequest(BaseModel):
    """Request to build/analyze an SGP."""
    legs: List[SGPLeg] = Field(..., min_length=2, max_length=10, description="SGP legs (2-10)")
    stake: Optional[float] = Field(None, ge=0, description="Stake amount")
    bankroll: Optional[float] = Field(None, ge=0, description="Total bankroll for Kelly sizing")
    sportsbook_odds: Optional[int] = Field(None, description="Actual sportsbook SGP odds (for EV calc)")


class CorrelationRequest(BaseModel):
    """Request to analyze correlations."""
    legs: List[SGPLeg] = Field(..., min_length=2, description="Legs to analyze")


@router.post("/build")
def build_sgp(request: SGPRequest):
    """
    Build and analyze a custom Same Game Parlay.

    Provides comprehensive analysis including:
    - Leg correlation detection
    - Expected value calculation
    - Risk scoring
    - Stake recommendations

    **Example Request:**
    ```json
    {
        "legs": [
            {"selection": "Lakers -5.5", "market_type": "spreads", "odds": -110},
            {"selection": "Over 220.5", "market_type": "totals", "odds": -110}
        ],
        "stake": 100,
        "bankroll": 5000
    }
    ```
    """
    legs_data = [leg.model_dump() for leg in request.legs]

    result = build_custom_sgp(
        legs=legs_data,
        stake=request.stake,
        bankroll=request.bankroll
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    # If sportsbook odds provided, recalculate EV
    if request.sportsbook_odds:
        result["expected_value"] = calculate_sgp_ev(legs_data, request.sportsbook_odds)

    return result


@router.post("/analyze-correlations")
def analyze_correlations(request: CorrelationRequest):
    """
    Analyze correlations between SGP legs.

    Identifies:
    - Positively correlated legs (tend to win together)
    - Negatively correlated legs (tend to oppose)
    - Conflicting legs (cannot both win)

    Use this to understand how your legs interact before placing an SGP.
    """
    legs_data = [leg.model_dump() for leg in request.legs]
    analysis = analyze_sgp_correlations(legs_data)

    return {
        "leg_count": len(request.legs),
        "analysis": analysis,
        "summary": get_correlation_summary(analysis)
    }


def get_correlation_summary(analysis: dict) -> str:
    """Generate human-readable correlation summary."""
    if analysis["has_conflicts"]:
        return "WARNING: Your SGP contains conflicting legs that cannot both win!"

    pos = analysis["positive_correlations"]
    neg = analysis["negative_correlations"]

    if pos > neg:
        return f"Good SGP structure: {pos} positive correlations increase combined probability"
    elif neg > pos:
        return f"Risky SGP: {neg} negative correlations decrease combined probability"
    else:
        return "Neutral SGP: legs are relatively independent"


@router.post("/calculate-odds")
def calculate_odds(request: CorrelationRequest):
    """
    Calculate SGP odds with correlation adjustment.

    Returns:
    - Raw odds (treating legs as independent)
    - Correlation-adjusted odds (our true estimate)
    - Estimated sportsbook odds (what books typically offer)
    """
    legs_data = [leg.model_dump() for leg in request.legs]
    return calculate_sgp_odds(legs_data)


@router.post("/calculate-ev")
def calculate_expected_value(
    request: CorrelationRequest,
    sportsbook_odds: Optional[int] = Query(None, description="Actual sportsbook SGP odds")
):
    """
    Calculate expected value of an SGP.

    If you provide the actual sportsbook odds, we calculate EV against those.
    Otherwise, we estimate what the book would offer.

    Positive EV = good bet, Negative EV = avoid.
    """
    legs_data = [leg.model_dump() for leg in request.legs]
    return calculate_sgp_ev(legs_data, sportsbook_odds)


@router.post("/risk-score")
def get_risk_score(request: CorrelationRequest):
    """
    Get risk score for an SGP (0-100).

    Risk factors:
    - Number of legs (more legs = higher risk)
    - Conflicting correlations
    - Long shot legs
    - Low combined probability

    Returns risk level and recommended max stake percentage.
    """
    legs_data = [leg.model_dump() for leg in request.legs]
    return get_sgp_risk_score(legs_data)


@router.get("/suggest/{game_id}")
def suggest_sgp(
    game_id: int,
    strategy: str = Query(
        "balanced",
        description="SGP strategy",
        enum=["balanced", "conservative", "aggressive", "correlated"]
    ),
    db: Session = Depends(get_db)
):
    """
    Get AI-suggested SGP for a game.

    **Strategies:**
    - `balanced`: Mix of favorites and reasonable odds (2-3 legs)
    - `conservative`: Safer legs, higher win probability (2 legs)
    - `aggressive`: More legs, bigger payout potential (4-5 legs)
    - `correlated`: Legs that tend to win together

    Returns suggested legs with full analysis.
    """
    result = suggest_sgp_legs(db, game_id, strategy)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/strategies")
def list_strategies():
    """
    List available SGP building strategies.
    """
    return {
        "strategies": [
            {
                "name": "balanced",
                "description": "Mix of favorites and reasonable odds",
                "typical_legs": "2-3",
                "risk_level": "medium",
                "best_for": "Regular SGP bettors"
            },
            {
                "name": "conservative",
                "description": "Safer legs with higher win probability",
                "typical_legs": "2",
                "risk_level": "low",
                "best_for": "Risk-averse bettors"
            },
            {
                "name": "aggressive",
                "description": "More legs for bigger payout potential",
                "typical_legs": "4-5",
                "risk_level": "high",
                "best_for": "High-risk, high-reward seekers"
            },
            {
                "name": "correlated",
                "description": "Legs that statistically tend to win together",
                "typical_legs": "2-3",
                "risk_level": "medium",
                "best_for": "Sharp bettors understanding correlations"
            }
        ]
    }


@router.get("/correlation-guide")
def correlation_guide():
    """
    Guide to common SGP leg correlations.

    Understanding correlations helps build smarter SGPs.
    """
    return {
        "positive_correlations": [
            {
                "combo": "Favorite ML + Game Over",
                "factor": 1.15,
                "reason": "When favorites win, they often score more points"
            },
            {
                "combo": "QB Passing Yards Over + Team Total Over",
                "factor": 1.25,
                "reason": "High passing yards usually means high team scoring"
            },
            {
                "combo": "Team Spread Cover + Team Total Over",
                "factor": 1.20,
                "reason": "Covering spreads often requires scoring"
            },
            {
                "combo": "Player Points Over + Team Total Over",
                "factor": 1.25,
                "reason": "Star player scoring = team scoring"
            }
        ],
        "negative_correlations": [
            {
                "combo": "Underdog ML + Game Under",
                "factor": 0.85,
                "reason": "Underdogs often need lower-scoring games to win"
            },
            {
                "combo": "QB Interceptions Over + Team ML",
                "factor": 0.75,
                "reason": "Interceptions hurt win probability"
            },
            {
                "combo": "Favorite ML + Game Under",
                "factor": 0.85,
                "reason": "Favorites often win by scoring more"
            }
        ],
        "conflicts": [
            {
                "combo": "Team A ML + Team B ML",
                "factor": 0.0,
                "reason": "Only one team can win"
            },
            {
                "combo": "Over + Under (same total)",
                "factor": 0.0,
                "reason": "Mutually exclusive outcomes"
            }
        ],
        "tip": "Build SGPs with positively correlated legs for better true odds vs what sportsbooks offer"
    }


@router.post("/classify-leg")
def classify_single_leg(leg: SGPLeg):
    """
    Classify a single leg for correlation lookup.

    Useful for understanding how a leg will be categorized
    in correlation analysis.
    """
    leg_data = leg.model_dump()
    classification = classify_leg(leg_data)

    return {
        "leg": leg_data,
        "classification": classification,
        "description": get_classification_description(classification)
    }


def get_classification_description(classification: str) -> str:
    """Get description of leg classification."""
    descriptions = {
        "moneyline_favorite": "Moneyline bet on the favorite",
        "moneyline_underdog": "Moneyline bet on the underdog",
        "spread_favorite": "Spread bet on the favorite (giving points)",
        "spread_underdog": "Spread bet on the underdog (getting points)",
        "over": "Game total over",
        "under": "Game total under",
        "team_total_over": "Team total over",
        "team_total_under": "Team total under",
        "qb_passing_yards_over": "QB passing yards over",
        "qb_passing_yards_under": "QB passing yards under",
        "qb_passing_tds_over": "QB passing TDs over",
        "qb_passing_tds_under": "QB passing TDs under",
        "rb_rushing_yards_over": "RB rushing yards over",
        "rb_rushing_yards_under": "RB rushing yards under",
        "wr_receiving_yards_over": "WR receiving yards over",
        "wr_receiving_yards_under": "WR receiving yards under",
        "player_points_over": "Player points over",
        "player_points_under": "Player points under",
        "player_rebounds_over": "Player rebounds over",
        "player_rebounds_under": "Player rebounds under",
        "player_assists_over": "Player assists over",
        "player_assists_under": "Player assists under",
        "unknown": "Unclassified leg type"
    }
    return descriptions.get(classification, "Unknown classification")
