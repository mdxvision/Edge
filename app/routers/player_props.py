"""
Player Props router for prop predictions and value finding.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime

from app.db import get_db
from app.services.player_props import (
    PropType,
    PropPrediction,
    get_prop_prediction,
    find_value_player_props,
    PlayerPropModel,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/player-props", tags=["player-props"])


# Request/Response Models

class PropPredictionRequest(BaseModel):
    player_id: int
    player_name: str
    prop_type: str = Field(..., description="Type of prop (points, rebounds, assists, etc.)")
    line: float = Field(..., description="The prop line to evaluate")
    sport: str = Field(default="NBA", pattern="^(NBA|NFL|MLB|NHL)$")
    opponent_team_id: Optional[int] = None
    is_home: bool = True
    injury_status: Optional[str] = None
    teammates_out: Optional[List[str]] = None


class PropPredictionResponse(BaseModel):
    player_id: int
    player_name: str
    prop_type: str
    line: float
    projected_value: float
    over_probability: float
    under_probability: float
    edge_over: float
    edge_under: float
    confidence: float
    recommendation: str
    factors: Dict[str, float]


class ValuePropResponse(BaseModel):
    player_id: int
    player_name: str
    prop_type: str
    line: float
    projected_value: float
    over_probability: float
    edge: float
    direction: str
    confidence: float
    sport: str


class BulkPredictionRequest(BaseModel):
    props: List[PropPredictionRequest]


# Endpoints

@router.post("/predict", response_model=PropPredictionResponse)
async def predict_player_prop(
    request: PropPredictionRequest,
    db: Session = Depends(get_db)
):
    """
    Get prediction for a specific player prop.

    Returns projected value, over/under probabilities, and edge.
    """
    try:
        prediction = get_prop_prediction(
            db=db,
            player_id=request.player_id,
            player_name=request.player_name,
            prop_type=request.prop_type,
            line=request.line,
            sport=request.sport,
            opponent_team_id=request.opponent_team_id,
            is_home=request.is_home,
            injury_status=request.injury_status,
            teammates_out=request.teammates_out
        )

        under_prob = 1 - prediction.over_probability
        edge_under = -prediction.edge_over  # Inverse of over edge

        # Determine recommendation
        if prediction.edge_over >= 3:
            recommendation = "STRONG OVER"
        elif prediction.edge_over >= 1:
            recommendation = "LEAN OVER"
        elif edge_under >= 3:
            recommendation = "STRONG UNDER"
        elif edge_under >= 1:
            recommendation = "LEAN UNDER"
        else:
            recommendation = "NO EDGE"

        return PropPredictionResponse(
            player_id=prediction.player_id,
            player_name=prediction.player_name,
            prop_type=prediction.prop_type,
            line=prediction.line,
            projected_value=prediction.projected_value,
            over_probability=round(prediction.over_probability, 4),
            under_probability=round(under_prob, 4),
            edge_over=round(prediction.edge_over, 2),
            edge_under=round(edge_under, 2),
            confidence=round(prediction.confidence, 2),
            recommendation=recommendation,
            factors=prediction.factors
        )
    except Exception as e:
        logger.error(f"Error predicting prop: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict/bulk", response_model=List[PropPredictionResponse])
async def predict_bulk_props(
    request: BulkPredictionRequest,
    db: Session = Depends(get_db)
):
    """
    Get predictions for multiple player props at once.

    Useful for analyzing a slate of props.
    """
    results = []

    for prop in request.props:
        try:
            prediction = get_prop_prediction(
                db=db,
                player_id=prop.player_id,
                player_name=prop.player_name,
                prop_type=prop.prop_type,
                line=prop.line,
                sport=prop.sport,
                opponent_team_id=prop.opponent_team_id,
                is_home=prop.is_home,
                injury_status=prop.injury_status,
                teammates_out=prop.teammates_out
            )

            under_prob = 1 - prediction.over_probability
            edge_under = -prediction.edge_over

            if prediction.edge_over >= 3:
                recommendation = "STRONG OVER"
            elif prediction.edge_over >= 1:
                recommendation = "LEAN OVER"
            elif edge_under >= 3:
                recommendation = "STRONG UNDER"
            elif edge_under >= 1:
                recommendation = "LEAN UNDER"
            else:
                recommendation = "NO EDGE"

            results.append(PropPredictionResponse(
                player_id=prediction.player_id,
                player_name=prediction.player_name,
                prop_type=prediction.prop_type,
                line=prediction.line,
                projected_value=prediction.projected_value,
                over_probability=round(prediction.over_probability, 4),
                under_probability=round(under_prob, 4),
                edge_over=round(prediction.edge_over, 2),
                edge_under=round(edge_under, 2),
                confidence=round(prediction.confidence, 2),
                recommendation=recommendation,
                factors=prediction.factors
            ))
        except Exception as e:
            logger.warning(f"Error predicting prop for {prop.player_name}: {e}")
            continue

    return results


@router.get("/value", response_model=List[ValuePropResponse])
async def find_value_props(
    sport: str = Query("NBA", pattern="^(NBA|NFL|MLB|NHL)$"),
    min_edge: float = Query(3.0, ge=0, le=20, description="Minimum edge percentage"),
    limit: int = Query(20, ge=1, le=100),
    prop_type: Optional[str] = Query(None, description="Filter by prop type"),
    db: Session = Depends(get_db)
):
    """
    Find player props with positive expected value.

    Scans available props and returns those meeting the edge threshold.
    """
    try:
        value_props = find_value_player_props(
            db=db,
            sport=sport,
            min_edge=min_edge,
            limit=limit
        )

        results = []
        for pred in value_props:
            # Filter by prop_type if specified
            if prop_type and pred.prop_type != prop_type:
                continue

            direction = "OVER" if pred.edge_over > 0 else "UNDER"
            edge = abs(pred.edge_over)

            results.append(ValuePropResponse(
                player_id=pred.player_id,
                player_name=pred.player_name,
                prop_type=pred.prop_type,
                line=pred.line,
                projected_value=round(pred.projected_value, 2),
                over_probability=round(pred.over_probability, 4),
                edge=round(edge, 2),
                direction=direction,
                confidence=round(pred.confidence, 2),
                sport=sport
            ))

        # Sort by edge descending
        results.sort(key=lambda x: x.edge, reverse=True)

        return results[:limit]
    except Exception as e:
        logger.error(f"Error finding value props: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prop-types")
async def list_prop_types(
    sport: Optional[str] = Query(None, pattern="^(NBA|NFL|MLB|NHL)$")
):
    """
    List available prop types, optionally filtered by sport.
    """
    prop_types = {
        "NBA": ["points", "rebounds", "assists", "steals", "blocks", "threes", "pts_rebs_asts", "pts_rebs", "pts_asts", "rebs_asts"],
        "NFL": ["passing_yards", "passing_tds", "rushing_yards", "rushing_tds", "receiving_yards", "receiving_tds", "receptions", "completions", "interceptions"],
        "MLB": ["hits", "runs", "rbis", "total_bases", "home_runs", "strikeouts_pitcher", "earned_runs", "hits_allowed", "walks_allowed"],
        "NHL": ["goals", "assists_nhl", "points_nhl", "shots", "saves", "goals_against"]
    }

    if sport:
        return {"sport": sport, "prop_types": prop_types.get(sport, [])}

    return prop_types


@router.get("/player/{player_id}/history")
async def get_player_prop_history(
    player_id: int,
    prop_type: str,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Get recent prop performance history for a player.

    Shows actual results vs lines for the specified prop type.
    """
    # This would query historical data from tracked_picks or a props table
    # For now, return placeholder structure
    return {
        "player_id": player_id,
        "prop_type": prop_type,
        "history": [],
        "average": 0,
        "hit_rate_vs_line": 0,
        "message": "Historical data tracking coming soon"
    }


@router.get("/correlations")
async def get_prop_correlations(
    sport: str = Query("NBA", pattern="^(NBA|NFL|MLB|NHL)$"),
    prop_type_1: str = Query(..., description="First prop type"),
    prop_type_2: str = Query(..., description="Second prop type"),
    db: Session = Depends(get_db)
):
    """
    Get correlation between two prop types.

    Useful for same-game parlay analysis.
    """
    # Known correlations for SGP analysis
    correlations = {
        "NBA": {
            ("points", "assists"): 0.35,
            ("points", "rebounds"): 0.15,
            ("rebounds", "assists"): 0.10,
            ("points", "threes"): 0.65,
            ("assists", "rebounds"): 0.05,
        },
        "NFL": {
            ("passing_yards", "passing_tds"): 0.55,
            ("rushing_yards", "rushing_tds"): 0.45,
            ("receiving_yards", "receptions"): 0.70,
            ("completions", "passing_yards"): 0.80,
        },
        "MLB": {
            ("hits", "runs"): 0.40,
            ("hits", "total_bases"): 0.75,
            ("strikeouts_pitcher", "earned_runs"): -0.25,
        }
    }

    sport_corrs = correlations.get(sport, {})

    # Check both orderings
    key1 = (prop_type_1, prop_type_2)
    key2 = (prop_type_2, prop_type_1)

    correlation = sport_corrs.get(key1) or sport_corrs.get(key2) or 0

    return {
        "sport": sport,
        "prop_type_1": prop_type_1,
        "prop_type_2": prop_type_2,
        "correlation": correlation,
        "interpretation": _interpret_correlation(correlation)
    }


def _interpret_correlation(corr: float) -> str:
    """Interpret correlation value."""
    if corr >= 0.7:
        return "Strong positive - props tend to hit together"
    elif corr >= 0.4:
        return "Moderate positive - some tendency to hit together"
    elif corr >= 0.1:
        return "Weak positive - slight tendency to hit together"
    elif corr >= -0.1:
        return "No significant correlation"
    elif corr >= -0.4:
        return "Weak negative - slight tendency to move opposite"
    elif corr >= -0.7:
        return "Moderate negative - props often move opposite"
    else:
        return "Strong negative - props tend to move opposite"
