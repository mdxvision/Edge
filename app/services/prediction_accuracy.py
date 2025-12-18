"""
Prediction Accuracy Tracking Service
Tracks and analyzes the accuracy of EdgeBet predictions
"""

import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import and_, or_, desc, func
from sqlalchemy.orm import Session

from app.db import PredictionRecord, FactorPerformance


# Supported prediction factors
PREDICTION_FACTORS = [
    "power_rating",
    "coach_dna",
    "officials",
    "weather_impact",
    "line_movement",
    "h2h_history",
    "situational_trends",
    "rest_days",
    "travel_distance",
    "divisional",
    "public_fade",
    "sharp_money",
    "revenge_spot",
    "letdown_spot"
]


def record_prediction(
    db: Session,
    sport: str,
    prediction_type: str,
    prediction: str,
    game_id: Optional[str] = None,
    game_description: Optional[str] = None,
    game_date: Optional[datetime] = None,
    predicted_edge: Optional[float] = None,
    confidence_score: Optional[float] = None,
    factors_used: Optional[Dict[str, float]] = None
) -> PredictionRecord:
    """Record a new prediction"""

    record = PredictionRecord(
        sport=sport.lower(),
        game_id=game_id,
        game_description=game_description,
        game_date=game_date or datetime.utcnow(),
        prediction_type=prediction_type,
        prediction=prediction,
        predicted_edge=predicted_edge,
        confidence_score=confidence_score,
        factors_used=json.dumps(factors_used) if factors_used else None,
        created_at=datetime.utcnow()
    )

    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_prediction_result(
    db: Session,
    prediction_id: int,
    actual_result: str,
    was_correct: bool,
    closing_line: Optional[float] = None
) -> PredictionRecord:
    """Update a prediction with its actual result"""

    record = db.query(PredictionRecord).filter(
        PredictionRecord.id == prediction_id
    ).first()

    if not record:
        raise ValueError(f"Prediction {prediction_id} not found")

    record.actual_result = actual_result
    record.was_correct = was_correct
    record.closing_line = closing_line

    # Calculate edge realized (simplified)
    if record.predicted_edge is not None:
        if was_correct:
            record.edge_realized = record.predicted_edge
        else:
            record.edge_realized = -record.predicted_edge

    # Calculate CLV if closing line available
    if closing_line is not None and record.predicted_edge is not None:
        record.clv_captured = closing_line - record.predicted_edge

    db.commit()
    db.refresh(record)

    # Update factor performance
    if record.factors_used:
        factors = json.loads(record.factors_used)
        for factor_name, edge_contribution in factors.items():
            _update_factor_performance(
                db, factor_name, record.sport, was_correct, edge_contribution
            )

    return record


def _update_factor_performance(
    db: Session,
    factor_name: str,
    sport: str,
    was_correct: bool,
    edge_contribution: float
):
    """Update the performance tracking for a factor"""

    # Get or create factor performance record
    factor = db.query(FactorPerformance).filter(
        FactorPerformance.factor_name == factor_name,
        FactorPerformance.sport == sport.lower()
    ).first()

    if not factor:
        factor = FactorPerformance(
            factor_name=factor_name,
            sport=sport.lower(),
            times_used=0,
            correct_predictions=0,
            incorrect_predictions=0,
            avg_edge_when_present=0,
            avg_edge_when_correct=0,
            avg_edge_when_incorrect=0,
            current_weight=1.0
        )
        db.add(factor)

    factor.times_used += 1

    if was_correct:
        factor.correct_predictions += 1
    else:
        factor.incorrect_predictions += 1

    # Update hit rate
    total = factor.correct_predictions + factor.incorrect_predictions
    factor.hit_rate = round(factor.correct_predictions / total * 100, 1) if total > 0 else 0

    # Update edge averages (simplified running average)
    if factor.avg_edge_when_present is None:
        factor.avg_edge_when_present = edge_contribution
    else:
        factor.avg_edge_when_present = (
            factor.avg_edge_when_present * (factor.times_used - 1) + edge_contribution
        ) / factor.times_used

    if was_correct:
        if factor.avg_edge_when_correct is None:
            factor.avg_edge_when_correct = edge_contribution
        else:
            factor.avg_edge_when_correct = (
                factor.avg_edge_when_correct * (factor.correct_predictions - 1) + edge_contribution
            ) / factor.correct_predictions
    else:
        if factor.avg_edge_when_incorrect is None:
            factor.avg_edge_when_incorrect = edge_contribution
        else:
            prev_count = factor.incorrect_predictions - 1
            factor.avg_edge_when_incorrect = (
                factor.avg_edge_when_incorrect * prev_count + edge_contribution
            ) / factor.incorrect_predictions if factor.incorrect_predictions > 0 else edge_contribution

    # Calculate recommended weight based on performance
    if factor.hit_rate and factor.hit_rate > 55:
        # Increase weight if hitting above 55%
        factor.recommended_weight = round(1.0 + (factor.hit_rate - 52.38) / 50, 2)
    elif factor.hit_rate and factor.hit_rate < 45:
        # Decrease weight if hitting below 45%
        factor.recommended_weight = round(max(0.1, 1.0 - (45 - factor.hit_rate) / 50), 2)
    else:
        factor.recommended_weight = 1.0

    factor.last_updated = datetime.utcnow()
    db.commit()


def get_accuracy_summary(
    db: Session,
    sport: Optional[str] = None,
    prediction_type: Optional[str] = None,
    days: int = 30
) -> Dict[str, Any]:
    """Get overall prediction accuracy summary"""

    cutoff = datetime.utcnow() - timedelta(days=days)

    query = db.query(PredictionRecord).filter(
        PredictionRecord.created_at >= cutoff,
        PredictionRecord.was_correct.isnot(None)  # Only graded predictions
    )

    if sport:
        query = query.filter(PredictionRecord.sport == sport.lower())

    if prediction_type:
        query = query.filter(PredictionRecord.prediction_type == prediction_type)

    records = query.all()

    if not records:
        return {
            "total_predictions": 0,
            "message": "No graded predictions in this period"
        }

    correct = sum(1 for r in records if r.was_correct)
    total = len(records)

    avg_edge = sum(r.predicted_edge or 0 for r in records) / total
    avg_confidence = sum(r.confidence_score or 0 for r in records) / total

    # Group by prediction type
    by_type = {}
    for r in records:
        if r.prediction_type not in by_type:
            by_type[r.prediction_type] = {"correct": 0, "total": 0}
        by_type[r.prediction_type]["total"] += 1
        if r.was_correct:
            by_type[r.prediction_type]["correct"] += 1

    for ptype, stats in by_type.items():
        stats["accuracy"] = round(stats["correct"] / stats["total"] * 100, 1)

    return {
        "period_days": days,
        "sport": sport or "all",
        "prediction_type": prediction_type or "all",
        "total_predictions": total,
        "correct_predictions": correct,
        "accuracy_pct": round(correct / total * 100, 1),
        "avg_predicted_edge": round(avg_edge, 2),
        "avg_confidence": round(avg_confidence, 1),
        "roi_estimate": round((correct / total - 0.4762) * 100, 2),  # vs break-even
        "by_type": by_type
    }


def get_factor_performance(
    db: Session,
    sport: Optional[str] = None,
    min_uses: int = 10
) -> List[Dict[str, Any]]:
    """Get performance metrics for each prediction factor"""

    query = db.query(FactorPerformance)

    if sport:
        query = query.filter(FactorPerformance.sport == sport.lower())

    query = query.filter(FactorPerformance.times_used >= min_uses)

    factors = query.order_by(desc(FactorPerformance.hit_rate)).all()

    return [{
        "factor": f.factor_name,
        "sport": f.sport or "all",
        "times_used": f.times_used,
        "correct": f.correct_predictions,
        "incorrect": f.incorrect_predictions,
        "hit_rate": f.hit_rate or 0,
        "avg_edge_present": round(f.avg_edge_when_present or 0, 2),
        "avg_edge_correct": round(f.avg_edge_when_correct or 0, 2),
        "avg_edge_incorrect": round(f.avg_edge_when_incorrect or 0, 2),
        "current_weight": f.current_weight,
        "recommended_weight": f.recommended_weight,
        "last_updated": f.last_updated.isoformat() if f.last_updated else None
    } for f in factors]


def get_recent_predictions(
    db: Session,
    sport: Optional[str] = None,
    limit: int = 50,
    graded_only: bool = False
) -> List[Dict[str, Any]]:
    """Get recent predictions"""

    query = db.query(PredictionRecord)

    if sport:
        query = query.filter(PredictionRecord.sport == sport.lower())

    if graded_only:
        query = query.filter(PredictionRecord.was_correct.isnot(None))

    records = query.order_by(desc(PredictionRecord.created_at)).limit(limit).all()

    return [{
        "id": r.id,
        "sport": r.sport,
        "game_id": r.game_id,
        "game_description": r.game_description,
        "game_date": r.game_date.isoformat() if r.game_date else None,
        "prediction_type": r.prediction_type,
        "prediction": r.prediction,
        "predicted_edge": r.predicted_edge,
        "confidence_score": r.confidence_score,
        "factors_used": json.loads(r.factors_used) if r.factors_used else None,
        "actual_result": r.actual_result,
        "was_correct": r.was_correct,
        "edge_realized": r.edge_realized,
        "clv_captured": r.clv_captured,
        "created_at": r.created_at.isoformat()
    } for r in records]


def get_high_confidence_performance(
    db: Session,
    sport: Optional[str] = None,
    confidence_threshold: float = 70.0,
    days: int = 30
) -> Dict[str, Any]:
    """Get performance of high-confidence predictions"""

    cutoff = datetime.utcnow() - timedelta(days=days)

    query = db.query(PredictionRecord).filter(
        PredictionRecord.created_at >= cutoff,
        PredictionRecord.was_correct.isnot(None),
        PredictionRecord.confidence_score >= confidence_threshold
    )

    if sport:
        query = query.filter(PredictionRecord.sport == sport.lower())

    records = query.all()

    if not records:
        return {
            "threshold": confidence_threshold,
            "total": 0,
            "message": "No high-confidence predictions graded"
        }

    correct = sum(1 for r in records if r.was_correct)
    total = len(records)

    return {
        "confidence_threshold": confidence_threshold,
        "period_days": days,
        "total_predictions": total,
        "correct": correct,
        "accuracy": round(correct / total * 100, 1),
        "avg_confidence": round(sum(r.confidence_score for r in records) / total, 1),
        "vs_baseline": round(correct / total * 100 - 52.38, 1)  # vs break-even
    }


def get_streak_analysis(
    db: Session,
    sport: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """Analyze prediction streaks"""

    query = db.query(PredictionRecord).filter(
        PredictionRecord.was_correct.isnot(None)
    )

    if sport:
        query = query.filter(PredictionRecord.sport == sport.lower())

    records = query.order_by(desc(PredictionRecord.created_at)).limit(limit).all()

    if not records:
        return {"message": "No graded predictions"}

    # Calculate current streak
    current_streak = 0
    streak_type = None
    for r in records:
        if streak_type is None:
            streak_type = "win" if r.was_correct else "loss"
            current_streak = 1
        elif (streak_type == "win" and r.was_correct) or (streak_type == "loss" and not r.was_correct):
            current_streak += 1
        else:
            break

    # Calculate longest streaks
    longest_win = 0
    longest_loss = 0
    current_win = 0
    current_loss = 0

    for r in reversed(records):
        if r.was_correct:
            current_win += 1
            current_loss = 0
            longest_win = max(longest_win, current_win)
        else:
            current_loss += 1
            current_win = 0
            longest_loss = max(longest_loss, current_loss)

    return {
        "analyzed_predictions": len(records),
        "current_streak": {
            "type": streak_type,
            "count": current_streak
        },
        "longest_winning_streak": longest_win,
        "longest_losing_streak": longest_loss
    }


def seed_prediction_data(db: Session, sport: str) -> Dict[str, Any]:
    """Seed sample prediction data for demonstration"""

    # Sample predictions with results
    sample_predictions = {
        "nfl": [
            {"type": "spread", "pred": "Chiefs -3.5", "edge": 3.2, "conf": 72, "correct": True,
             "factors": {"power_rating": 2.5, "coach_dna": 1.5, "h2h_history": 0.8}},
            {"type": "spread", "pred": "49ers -7", "edge": 2.8, "conf": 68, "correct": True,
             "factors": {"power_rating": 3.0, "situational_trends": 1.2, "weather_impact": 0.5}},
            {"type": "total", "pred": "Under 48.5", "edge": 4.1, "conf": 75, "correct": True,
             "factors": {"weather_impact": 2.5, "officials": 1.0, "h2h_history": 1.5}},
            {"type": "spread", "pred": "Eagles -2.5", "edge": 1.8, "conf": 58, "correct": False,
             "factors": {"power_rating": 1.5, "divisional": 0.8, "rest_days": -0.5}},
            {"type": "spread", "pred": "Ravens -6", "edge": 3.5, "conf": 70, "correct": True,
             "factors": {"power_rating": 2.8, "coach_dna": 1.2, "sharp_money": 1.0}},
            {"type": "moneyline", "pred": "Bills ML", "edge": 2.2, "conf": 65, "correct": True,
             "factors": {"power_rating": 2.0, "situational_trends": 0.8, "h2h_history": 0.5}},
            {"type": "total", "pred": "Over 52.5", "edge": 1.5, "conf": 55, "correct": False,
             "factors": {"weather_impact": -1.0, "h2h_history": 1.2, "line_movement": 1.0}},
            {"type": "spread", "pred": "Cowboys +3", "edge": 2.5, "conf": 62, "correct": True,
             "factors": {"public_fade": 2.0, "situational_trends": 1.0, "divisional": 0.5}},
        ],
        "nba": [
            {"type": "spread", "pred": "Celtics -5.5", "edge": 2.9, "conf": 70, "correct": True,
             "factors": {"power_rating": 2.5, "rest_days": 1.0, "h2h_history": 0.5}},
            {"type": "total", "pred": "Over 225.5", "edge": 2.2, "conf": 64, "correct": True,
             "factors": {"h2h_history": 1.5, "situational_trends": 1.0, "officials": 0.5}},
            {"type": "spread", "pred": "Lakers +2", "edge": 1.8, "conf": 58, "correct": False,
             "factors": {"public_fade": 1.5, "rest_days": -0.5, "travel_distance": -0.8}},
            {"type": "spread", "pred": "Warriors -3", "edge": 2.5, "conf": 66, "correct": True,
             "factors": {"power_rating": 2.0, "coach_dna": 1.0, "situational_trends": 0.5}},
        ],
        "mlb": [
            {"type": "spread", "pred": "Dodgers -1.5", "edge": 3.2, "conf": 68, "correct": True,
             "factors": {"power_rating": 2.5, "weather_impact": 0.8, "h2h_history": 0.5}},
            {"type": "total", "pred": "Under 8.5", "edge": 2.8, "conf": 65, "correct": True,
             "factors": {"weather_impact": 1.5, "power_rating": 1.0, "officials": 0.5}},
            {"type": "spread", "pred": "Yankees -1.5", "edge": 1.5, "conf": 55, "correct": False,
             "factors": {"power_rating": 1.2, "h2h_history": 0.8, "situational_trends": -0.5}},
        ]
    }

    if sport.lower() not in sample_predictions:
        return {"error": f"No sample data for sport: {sport}"}

    predictions_added = 0
    for pred in sample_predictions[sport.lower()]:
        record = record_prediction(
            db=db,
            sport=sport,
            prediction_type=pred["type"],
            prediction=pred["pred"],
            game_date=datetime.utcnow() - timedelta(days=predictions_added),
            predicted_edge=pred["edge"],
            confidence_score=pred["conf"],
            factors_used=pred["factors"]
        )

        # Update with result
        update_prediction_result(
            db=db,
            prediction_id=record.id,
            actual_result=f"{'Correct' if pred['correct'] else 'Incorrect'} - {pred['pred']}",
            was_correct=pred["correct"]
        )

        predictions_added += 1

    return {
        "success": True,
        "sport": sport,
        "predictions_added": predictions_added
    }
