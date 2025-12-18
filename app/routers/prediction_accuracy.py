"""
Prediction Accuracy Tracking API Endpoints
"""

from datetime import datetime
from typing import Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import prediction_accuracy as accuracy_service


router = APIRouter(prefix="/prediction-accuracy", tags=["Prediction Accuracy"])


class PredictionCreate(BaseModel):
    """Schema for creating a new prediction"""
    sport: str = Field(..., description="Sport (nfl, nba, mlb, etc.)")
    prediction_type: str = Field(..., description="Type: spread, moneyline, total")
    prediction: str = Field(..., description="The prediction (e.g., 'Chiefs -3.5')")
    game_id: Optional[str] = Field(None, description="External game ID")
    game_description: Optional[str] = Field(None, description="Game description")
    game_date: Optional[datetime] = Field(None, description="Game date/time")
    predicted_edge: Optional[float] = Field(None, ge=0, le=100, description="Predicted edge %")
    confidence_score: Optional[float] = Field(None, ge=0, le=100, description="Confidence score")
    factors_used: Optional[Dict[str, float]] = Field(None, description="Factors and their contributions")


class PredictionResultUpdate(BaseModel):
    """Schema for updating a prediction with its result"""
    actual_result: str = Field(..., description="The actual result")
    was_correct: bool = Field(..., description="Whether prediction was correct")
    closing_line: Optional[float] = Field(None, description="Closing line for CLV calculation")


@router.post("/record")
async def record_prediction(
    prediction: PredictionCreate,
    db: Session = Depends(get_db)
):
    """
    Record a new prediction for tracking.

    Include the factors used and their edge contributions for factor analysis.
    """
    try:
        record = accuracy_service.record_prediction(
            db=db,
            sport=prediction.sport,
            prediction_type=prediction.prediction_type,
            prediction=prediction.prediction,
            game_id=prediction.game_id,
            game_description=prediction.game_description,
            game_date=prediction.game_date,
            predicted_edge=prediction.predicted_edge,
            confidence_score=prediction.confidence_score,
            factors_used=prediction.factors_used
        )
        return {
            "id": record.id,
            "sport": record.sport,
            "prediction": record.prediction,
            "created_at": record.created_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/result/{prediction_id}")
async def update_prediction_result(
    prediction_id: int,
    result: PredictionResultUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a prediction with its actual result.

    This grades the prediction and updates factor performance metrics.
    """
    try:
        record = accuracy_service.update_prediction_result(
            db=db,
            prediction_id=prediction_id,
            actual_result=result.actual_result,
            was_correct=result.was_correct,
            closing_line=result.closing_line
        )
        return {
            "id": record.id,
            "prediction": record.prediction,
            "was_correct": record.was_correct,
            "actual_result": record.actual_result,
            "edge_realized": record.edge_realized,
            "clv_captured": record.clv_captured
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_accuracy_summary(
    sport: Optional[str] = Query(None, description="Filter by sport"),
    prediction_type: Optional[str] = Query(None, description="Filter by type: spread, moneyline, total"),
    days: int = Query(30, ge=1, le=365, description="Look-back period in days"),
    db: Session = Depends(get_db)
):
    """
    Get overall prediction accuracy summary.

    Returns accuracy percentages, ROI estimates, and breakdowns by type.
    """
    try:
        summary = accuracy_service.get_accuracy_summary(db, sport, prediction_type, days)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/factors")
async def get_factor_performance(
    sport: Optional[str] = Query(None, description="Filter by sport"),
    min_uses: int = Query(10, ge=1, description="Minimum uses to include"),
    db: Session = Depends(get_db)
):
    """
    Get performance metrics for each prediction factor.

    Shows which factors are most predictive and recommended weight adjustments.
    """
    try:
        factors = accuracy_service.get_factor_performance(db, sport, min_uses)
        return {
            "sport": sport or "all",
            "min_uses": min_uses,
            "factors": factors,
            "count": len(factors)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent")
async def get_recent_predictions(
    sport: Optional[str] = Query(None, description="Filter by sport"),
    limit: int = Query(50, ge=1, le=200, description="Number of predictions to return"),
    graded_only: bool = Query(False, description="Only show graded predictions"),
    db: Session = Depends(get_db)
):
    """
    Get recent predictions.

    Set graded_only=true to see only predictions with results.
    """
    try:
        predictions = accuracy_service.get_recent_predictions(db, sport, limit, graded_only)
        return {
            "sport": sport or "all",
            "graded_only": graded_only,
            "predictions": predictions,
            "count": len(predictions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/high-confidence")
async def get_high_confidence_performance(
    sport: Optional[str] = Query(None, description="Filter by sport"),
    threshold: float = Query(70.0, ge=50, le=100, description="Confidence threshold"),
    days: int = Query(30, ge=1, le=365, description="Look-back period"),
    db: Session = Depends(get_db)
):
    """
    Get performance of high-confidence predictions.

    Analyzes whether higher confidence predictions perform better.
    """
    try:
        performance = accuracy_service.get_high_confidence_performance(
            db, sport, threshold, days
        )
        return performance
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/streaks")
async def get_streak_analysis(
    sport: Optional[str] = Query(None, description="Filter by sport"),
    limit: int = Query(100, ge=10, le=500, description="Number of predictions to analyze"),
    db: Session = Depends(get_db)
):
    """
    Analyze prediction streaks.

    Returns current streak, longest winning/losing streaks.
    """
    try:
        analysis = accuracy_service.get_streak_analysis(db, sport, limit)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{sport}/seed")
async def seed_prediction_data(
    sport: str,
    db: Session = Depends(get_db)
):
    """
    Seed sample prediction data for demonstration.
    """
    try:
        result = accuracy_service.seed_prediction_data(db, sport)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
