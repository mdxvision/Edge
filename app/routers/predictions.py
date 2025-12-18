"""
Unified Predictions API Router

Provides endpoints for unified ML predictions that combine all edge factors.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from app.db import get_db, Game, UnifiedPrediction
from app.services import edge_aggregator

router = APIRouter(prefix="/predictions", tags=["predictions"])


class CustomAnalysisRequest(BaseModel):
    home_team: str
    away_team: str
    sport: str = "NFL"
    market_type: str = "spread"
    line_value: Optional[float] = None
    # Optional overrides
    public_pct_home: Optional[float] = None
    is_revenge_game: Optional[bool] = None
    home_days_rest: Optional[int] = None
    away_days_rest: Optional[int] = None


@router.get("/game/{game_id}")
async def get_game_prediction(
    game_id: int,
    market_type: str = Query("spread"),
    db: Session = Depends(get_db)
):
    """
    Get full unified prediction for a game.

    Combines all edge factors:
    - Line movement (sharp money)
    - Coach DNA (situational records)
    - Situational factors (rest, travel, motivation)
    - Weather impact
    - Official tendencies
    - Public fade signals
    - Historical ELO
    - Social sentiment

    Returns weighted edge, confidence, and recommendation.
    """
    prediction = await edge_aggregator.get_unified_prediction(game_id, db, market_type)

    if "error" in prediction:
        raise HTTPException(status_code=404, detail=prediction["error"])

    return prediction


@router.get("/today")
async def get_todays_predictions(
    sport: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Get all predictions for today, ranked by edge strength.
    """
    picks = await edge_aggregator.get_ranked_picks(db, sport=sport, limit=limit)

    return {
        "date": datetime.utcnow().date().isoformat(),
        "sport_filter": sport,
        "predictions": picks,
        "count": len(picks)
    }


@router.get("/top-picks")
async def get_top_picks(
    sport: Optional[str] = Query(None),
    limit: int = Query(5, ge=1, le=10),
    db: Session = Depends(get_db)
):
    """
    Get the best picks of the day.

    Returns only BET or STRONG BET recommendations sorted by edge.
    """
    picks = await edge_aggregator.get_top_picks(db, sport=sport, limit=limit)

    # Calculate total expected edge
    total_edge = sum(p.get("edge_value", 0) for p in picks)
    avg_confidence = sum(p.get("confidence", 0) for p in picks) / len(picks) if picks else 0

    return {
        "date": datetime.utcnow().date().isoformat(),
        "sport_filter": sport,
        "top_picks": picks,
        "count": len(picks),
        "summary": {
            "total_expected_edge": f"+{total_edge:.1f}%",
            "average_confidence": f"{avg_confidence * 100:.0f}%",
            "picks_available": len(picks)
        }
    }


@router.get("/sport/{sport}")
async def get_predictions_by_sport(
    sport: str,
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Get predictions filtered by sport.
    """
    picks = await edge_aggregator.get_ranked_picks(db, sport=sport, limit=limit)

    return {
        "sport": sport,
        "date": datetime.utcnow().date().isoformat(),
        "predictions": picks,
        "count": len(picks)
    }


@router.get("/explain/{game_id}")
async def get_prediction_explanation(
    game_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed explanation of a prediction.

    Returns full breakdown of each factor's contribution.
    """
    prediction = await edge_aggregator.get_unified_prediction(game_id, db)

    if "error" in prediction:
        raise HTTPException(status_code=404, detail=prediction["error"])

    # Format detailed explanation
    factors = prediction.get("factors", {})
    pred = prediction.get("prediction", {})

    factor_breakdown = []
    for key, factor in factors.items():
        factor_breakdown.append({
            "factor": key.replace("_", " ").title(),
            "edge": factor.get("edge", 0),
            "direction": factor.get("direction", "neutral"),
            "signal": factor.get("signal", ""),
            "weight": f"{factor.get('weight', 0) * 100:.0f}%",
            "contribution": factor.get("weighted_contribution", "0%")
        })

    # Sort by weight
    factor_breakdown.sort(key=lambda x: float(x["weight"].replace("%", "")), reverse=True)

    return {
        "game_id": game_id,
        "game": prediction.get("game"),
        "sport": prediction.get("sport"),
        "predicted_side": pred.get("side"),
        "total_edge": pred.get("raw_edge"),
        "confidence": pred.get("confidence"),
        "confidence_label": pred.get("confidence_label"),
        "recommendation": pred.get("recommendation"),
        "star_rating": pred.get("star_rating"),
        "factor_breakdown": factor_breakdown,
        "analysis": prediction.get("analysis"),
        "explanation": prediction.get("explanation"),
        "methodology": {
            "description": "Prediction combines 8 unique edge factors using weighted averaging",
            "weights": {
                "line_movement": "20% - Sharp money indicators",
                "coach_dna": "18% - Situational coaching records",
                "situational": "17% - Rest, travel, motivation",
                "weather": "12% - Weather impact on scoring",
                "officials": "10% - Referee/umpire tendencies",
                "public_fade": "10% - Contrarian signals",
                "historical_elo": "8% - Power ratings",
                "social_sentiment": "5% - Social media sentiment"
            }
        }
    }


@router.post("/custom")
async def custom_analysis(
    request: CustomAnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    Run custom analysis with user-provided context.

    Useful for analyzing hypothetical scenarios or games not in our database.
    """
    # Try to find existing game
    game = db.query(Game).filter(
        Game.home_team == request.home_team,
        Game.away_team == request.away_team,
        Game.sport == request.sport
    ).first()

    if game:
        # Use existing game
        prediction = await edge_aggregator.get_unified_prediction(
            game.id, db, request.market_type
        )
    else:
        # Create temporary analysis without storing
        prediction = {
            "game": f"{request.away_team} @ {request.home_team}",
            "sport": request.sport,
            "market": request.market_type,
            "note": "Custom analysis - game not in database",
            "factors": {},
            "analysis": {
                "confirming_factors": 0,
                "conflicting_factors": 0,
                "alignment_score": 0.5
            },
            "prediction": {
                "side": "Unable to generate - insufficient data",
                "raw_edge": "0%",
                "confidence": 0.0,
                "confidence_label": "N/A",
                "recommendation": "INSUFFICIENT DATA"
            },
            "explanation": "Cannot generate prediction without game data. Add game to database first."
        }

    return prediction


@router.get("/history")
async def get_prediction_history(
    sport: Optional[str] = Query(None),
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """
    Get historical predictions for backtesting.
    """
    from datetime import timedelta

    cutoff = datetime.utcnow() - timedelta(days=days)

    query = db.query(UnifiedPrediction).filter(
        UnifiedPrediction.created_at >= cutoff
    )

    if sport:
        query = query.filter(UnifiedPrediction.sport == sport)

    predictions = query.order_by(UnifiedPrediction.created_at.desc()).limit(100).all()

    return {
        "days": days,
        "sport_filter": sport,
        "predictions": [
            {
                "id": p.id,
                "game_id": p.game_id,
                "sport": p.sport,
                "home_team": p.home_team,
                "away_team": p.away_team,
                "game_date": p.game_date.isoformat() if p.game_date else None,
                "predicted_side": p.predicted_side,
                "edge": p.raw_edge,
                "confidence": p.confidence,
                "recommendation": p.recommendation,
                "star_rating": p.star_rating,
                "created_at": p.created_at.isoformat() if p.created_at else None
            }
            for p in predictions
        ],
        "count": len(predictions)
    }


@router.get("/stats")
async def get_prediction_stats(
    sport: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get statistics about predictions.
    """
    query = db.query(UnifiedPrediction)

    if sport:
        query = query.filter(UnifiedPrediction.sport == sport)

    predictions = query.all()

    if not predictions:
        return {
            "total_predictions": 0,
            "message": "No predictions available"
        }

    # Calculate stats
    total = len(predictions)
    strong_bets = len([p for p in predictions if p.recommendation == "STRONG BET"])
    bets = len([p for p in predictions if p.recommendation == "BET"])
    leans = len([p for p in predictions if p.recommendation == "LEAN"])

    avg_edge = sum(p.raw_edge or 0 for p in predictions) / total if total > 0 else 0
    avg_confidence = sum(p.confidence or 0 for p in predictions) / total if total > 0 else 0

    five_star = len([p for p in predictions if p.star_rating == 5])
    four_star = len([p for p in predictions if p.star_rating == 4])

    return {
        "sport_filter": sport,
        "total_predictions": total,
        "recommendations": {
            "strong_bet": strong_bets,
            "bet": bets,
            "lean": leans,
            "monitor_or_avoid": total - strong_bets - bets - leans
        },
        "star_ratings": {
            "5_star": five_star,
            "4_star": four_star,
            "3_star_or_below": total - five_star - four_star
        },
        "averages": {
            "edge": f"+{avg_edge:.2f}%",
            "confidence": f"{avg_confidence * 100:.1f}%"
        }
    }
