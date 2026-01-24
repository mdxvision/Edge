"""
CLV (Closing Line Value) Tracker Service

Captures closing lines, calculates CLV for tracked bets,
and provides model calibration metrics.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.db import (
    Game, Market, Line, OddsSnapshot, TrackedBet,
    TrackedPick, BetRecommendation, HistoricalGameResult
)
from app.utils.logging import get_logger

logger = get_logger(__name__)


def american_to_implied_prob(american_odds: int) -> float:
    """Convert American odds to implied probability."""
    if american_odds > 0:
        return 100 / (american_odds + 100)
    else:
        return abs(american_odds) / (abs(american_odds) + 100)


def calculate_clv(bet_odds: int, closing_odds: int) -> float:
    """
    Calculate Closing Line Value as a percentage.

    Positive CLV = you got better odds than closing
    Example: bet at +150, closed at +130 = positive CLV
    """
    bet_prob = american_to_implied_prob(bet_odds)
    closing_prob = american_to_implied_prob(closing_odds)

    if bet_prob == 0:
        return 0.0

    # CLV formula: (closing_prob - bet_prob) / bet_prob * 100
    return ((closing_prob - bet_prob) / bet_prob) * 100


def get_closing_line(
    db: Session,
    game_id: int,
    market_type: str,
    selection: str,
    sportsbook: Optional[str] = None
) -> Optional[int]:
    """
    Get the closing line for a specific market.

    The closing line is the last recorded odds before the game started.
    """
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        return None

    # Get the last odds snapshot before game start
    query = db.query(OddsSnapshot).filter(
        OddsSnapshot.game_id == game_id,
        OddsSnapshot.market_type == market_type,
        OddsSnapshot.captured_at < game.start_time
    )

    if sportsbook:
        query = query.filter(OddsSnapshot.sportsbook == sportsbook)

    snapshot = query.order_by(OddsSnapshot.captured_at.desc()).first()

    if snapshot:
        return snapshot.odds

    # Fallback: get from current lines
    market = db.query(Market).filter(
        Market.game_id == game_id,
        Market.market_type == market_type,
        Market.selection == selection
    ).first()

    if market and market.lines:
        if sportsbook:
            for line in market.lines:
                if line.sportsbook == sportsbook:
                    return line.american_odds
        return market.lines[0].american_odds

    return None


def capture_closing_lines(db: Session, hours_before: float = 0.5) -> Dict[str, Any]:
    """
    Capture closing lines for games about to start.

    Should be run periodically (e.g., every 15-30 minutes) to capture
    lines close to game time.

    Args:
        db: Database session
        hours_before: Capture lines for games starting within this many hours

    Returns:
        Summary of captured lines
    """
    now = datetime.utcnow()
    cutoff = now + timedelta(hours=hours_before)

    # Find games starting soon that don't have closing lines captured yet
    games = db.query(Game).filter(
        Game.start_time > now,
        Game.start_time <= cutoff,
        Game.status == "scheduled"
    ).all()

    captured = 0
    games_processed = 0

    for game in games:
        games_processed += 1

        for market in game.markets:
            for line in market.lines:
                # Check if we already have a recent snapshot
                recent = db.query(OddsSnapshot).filter(
                    OddsSnapshot.game_id == game.id,
                    OddsSnapshot.market_type == market.market_type,
                    OddsSnapshot.sportsbook == line.sportsbook,
                    OddsSnapshot.captured_at > now - timedelta(minutes=30)
                ).first()

                if not recent:
                    snapshot = OddsSnapshot(
                        game_id=game.id,
                        market_type=market.market_type,
                        sportsbook=line.sportsbook,
                        odds=line.american_odds,
                        line_value=line.line_value,
                        captured_at=now
                    )
                    db.add(snapshot)
                    captured += 1

    db.commit()

    logger.info(f"Captured {captured} closing lines for {games_processed} games")
    return {
        "games_processed": games_processed,
        "lines_captured": captured,
        "timestamp": now.isoformat()
    }


def update_bet_clv(
    db: Session,
    bet: TrackedBet,
    closing_odds: Optional[int] = None
) -> Optional[float]:
    """
    Update CLV for a tracked bet.

    Args:
        db: Database session
        bet: The tracked bet to update
        closing_odds: Optional closing odds (will lookup if not provided)

    Returns:
        Calculated CLV percentage or None
    """
    if not bet.odds:
        return None

    # Get closing odds if not provided
    if closing_odds is None:
        # Try to find from recommendation/game data
        if bet.recommendation_id:
            rec = db.query(BetRecommendation).filter(
                BetRecommendation.id == bet.recommendation_id
            ).first()
            if rec and rec.line_id:
                line = db.query(Line).filter(Line.id == rec.line_id).first()
                if line:
                    market = line.market
                    closing_odds = get_closing_line(
                        db,
                        market.game_id,
                        market.market_type,
                        market.selection,
                        line.sportsbook
                    )

    if closing_odds is None:
        return None

    clv = calculate_clv(bet.odds, closing_odds)

    bet.closing_odds = closing_odds
    bet.clv_percentage = round(clv, 2)
    db.commit()

    return clv


def batch_update_clv(db: Session) -> Dict[str, Any]:
    """
    Batch update CLV for all eligible bets.

    Processes settled bets that don't have CLV calculated yet.
    """
    # Find settled bets without CLV
    bets = db.query(TrackedBet).filter(
        TrackedBet.status == "settled",
        TrackedBet.clv_percentage.is_(None),
        TrackedBet.odds.isnot(None)
    ).limit(100).all()

    updated = 0
    failed = 0

    for bet in bets:
        try:
            clv = update_bet_clv(db, bet)
            if clv is not None:
                updated += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Error updating CLV for bet {bet.id}: {e}")
            failed += 1

    logger.info(f"Batch CLV update: {updated} updated, {failed} failed")
    return {
        "updated": updated,
        "failed": failed,
        "processed": len(bets)
    }


# Model Calibration Metrics

def get_calibration_metrics(
    db: Session,
    sport: Optional[str] = None,
    days: int = 90
) -> Dict[str, Any]:
    """
    Calculate model calibration metrics.

    Measures how well predicted probabilities match actual outcomes.
    A well-calibrated model predicts 60% when events happen 60% of the time.
    """
    since = datetime.utcnow() - timedelta(days=days)

    # Get recommendations with outcomes
    query = db.query(BetRecommendation).join(TrackedBet).filter(
        TrackedBet.status == "settled",
        TrackedBet.result.in_(["won", "lost"]),
        BetRecommendation.created_at >= since
    )

    if sport:
        query = query.filter(BetRecommendation.sport == sport)

    recommendations = query.all()

    if len(recommendations) < 20:
        return {
            "calibration_score": None,
            "message": "Insufficient data (need 20+ settled bets)",
            "sample_size": len(recommendations)
        }

    # Calibration buckets (10% intervals)
    buckets = {i: {"predictions": 0, "wins": 0} for i in range(10)}

    for rec in recommendations:
        # Get outcome
        tracked = db.query(TrackedBet).filter(
            TrackedBet.recommendation_id == rec.id
        ).first()

        if not tracked or tracked.result not in ["won", "lost"]:
            continue

        won = tracked.result == "won"
        prob = rec.model_probability

        # Bucket by probability (0-10%, 10-20%, etc.)
        bucket_idx = min(9, int(prob * 10))
        buckets[bucket_idx]["predictions"] += 1
        if won:
            buckets[bucket_idx]["wins"] += 1

    # Calculate calibration error (Brier score component)
    calibration_data = []
    total_error = 0
    total_predictions = 0

    for bucket_idx, data in buckets.items():
        if data["predictions"] > 0:
            expected_prob = (bucket_idx + 0.5) / 10  # Midpoint of bucket
            actual_rate = data["wins"] / data["predictions"]
            error = abs(expected_prob - actual_rate)
            total_error += error * data["predictions"]
            total_predictions += data["predictions"]

            calibration_data.append({
                "probability_range": f"{bucket_idx*10}-{(bucket_idx+1)*10}%",
                "predictions": data["predictions"],
                "wins": data["wins"],
                "expected_win_rate": round(expected_prob * 100, 1),
                "actual_win_rate": round(actual_rate * 100, 1),
                "calibration_error": round(error * 100, 1)
            })

    avg_calibration_error = (total_error / total_predictions * 100) if total_predictions > 0 else 0

    # Brier score
    brier_score = 0
    for rec in recommendations:
        tracked = db.query(TrackedBet).filter(
            TrackedBet.recommendation_id == rec.id
        ).first()
        if tracked and tracked.result in ["won", "lost"]:
            outcome = 1 if tracked.result == "won" else 0
            brier_score += (rec.model_probability - outcome) ** 2

    brier_score = brier_score / len(recommendations) if recommendations else 0

    return {
        "calibration_score": round(100 - avg_calibration_error, 1),  # Higher is better
        "brier_score": round(brier_score, 4),
        "sample_size": len(recommendations),
        "calibration_by_bucket": calibration_data,
        "interpretation": get_calibration_interpretation(avg_calibration_error, brier_score)
    }


def get_calibration_interpretation(calibration_error: float, brier_score: float) -> str:
    """Interpret calibration metrics."""
    if calibration_error < 5:
        cal_text = "Excellent calibration - predictions closely match outcomes"
    elif calibration_error < 10:
        cal_text = "Good calibration - predictions are reasonably accurate"
    elif calibration_error < 15:
        cal_text = "Fair calibration - some adjustment needed"
    else:
        cal_text = "Poor calibration - model predictions need significant adjustment"

    if brier_score < 0.2:
        brier_text = "Strong predictive accuracy"
    elif brier_score < 0.25:
        brier_text = "Good predictive accuracy"
    else:
        brier_text = "Predictive accuracy needs improvement"

    return f"{cal_text}. {brier_text}."


def get_edge_accuracy(
    db: Session,
    sport: Optional[str] = None,
    days: int = 90
) -> Dict[str, Any]:
    """
    Analyze accuracy of edge predictions.

    Compares predicted edge to actual outcomes.
    """
    since = datetime.utcnow() - timedelta(days=days)

    query = db.query(BetRecommendation).join(TrackedBet).filter(
        TrackedBet.status == "settled",
        TrackedBet.result.in_(["won", "lost"]),
        BetRecommendation.created_at >= since,
        BetRecommendation.edge > 0
    )

    if sport:
        query = query.filter(BetRecommendation.sport == sport)

    recommendations = query.all()

    if len(recommendations) < 10:
        return {
            "message": "Insufficient data",
            "sample_size": len(recommendations)
        }

    # Group by edge ranges
    edge_buckets = {
        "1-3%": {"min": 0.01, "max": 0.03, "bets": [], "wins": 0},
        "3-5%": {"min": 0.03, "max": 0.05, "bets": [], "wins": 0},
        "5-8%": {"min": 0.05, "max": 0.08, "bets": [], "wins": 0},
        "8%+": {"min": 0.08, "max": 1.0, "bets": [], "wins": 0},
    }

    total_profit = 0
    total_staked = 0

    for rec in recommendations:
        tracked = db.query(TrackedBet).filter(
            TrackedBet.recommendation_id == rec.id
        ).first()

        if not tracked:
            continue

        won = tracked.result == "won"

        for bucket_name, bucket in edge_buckets.items():
            if bucket["min"] <= rec.edge < bucket["max"]:
                bucket["bets"].append(rec)
                if won:
                    bucket["wins"] += 1
                break

        if tracked.profit_loss:
            total_profit += tracked.profit_loss
            total_staked += tracked.stake

    # Calculate stats per edge bucket
    edge_analysis = []
    for bucket_name, bucket in edge_buckets.items():
        if bucket["bets"]:
            win_rate = bucket["wins"] / len(bucket["bets"]) * 100
            avg_edge = sum(b.edge for b in bucket["bets"]) / len(bucket["bets"]) * 100
            edge_analysis.append({
                "edge_range": bucket_name,
                "bet_count": len(bucket["bets"]),
                "wins": bucket["wins"],
                "win_rate": round(win_rate, 1),
                "avg_edge": round(avg_edge, 1)
            })

    roi = (total_profit / total_staked * 100) if total_staked > 0 else 0

    return {
        "sample_size": len(recommendations),
        "overall_roi": round(roi, 2),
        "total_profit": round(total_profit, 2),
        "edge_analysis": edge_analysis
    }


def get_clv_roi_correlation(
    db: Session,
    user_id: Optional[int] = None,
    days: int = 90
) -> Dict[str, Any]:
    """
    Analyze correlation between CLV and ROI.

    Strong positive correlation indicates skill-based betting.
    """
    since = datetime.utcnow() - timedelta(days=days)

    query = db.query(TrackedBet).filter(
        TrackedBet.status == "settled",
        TrackedBet.result.in_(["won", "lost"]),
        TrackedBet.placed_at >= since,
        TrackedBet.clv_percentage.isnot(None),
        TrackedBet.profit_loss.isnot(None)
    )

    if user_id:
        query = query.filter(TrackedBet.user_id == user_id)

    bets = query.all()

    if len(bets) < 20:
        return {
            "correlation": None,
            "message": "Insufficient data (need 20+ bets with CLV)",
            "sample_size": len(bets)
        }

    # Split into positive and negative CLV groups
    positive_clv = [b for b in bets if b.clv_percentage > 0]
    negative_clv = [b for b in bets if b.clv_percentage <= 0]

    def calc_roi(bet_list):
        if not bet_list:
            return 0
        total_stake = sum(b.stake for b in bet_list)
        total_profit = sum(b.profit_loss for b in bet_list)
        return (total_profit / total_stake * 100) if total_stake > 0 else 0

    pos_roi = calc_roi(positive_clv)
    neg_roi = calc_roi(negative_clv)

    # Simple correlation coefficient
    if len(bets) >= 2:
        clv_values = [b.clv_percentage for b in bets]
        roi_values = [b.profit_loss / b.stake * 100 if b.stake else 0 for b in bets]

        mean_clv = sum(clv_values) / len(clv_values)
        mean_roi = sum(roi_values) / len(roi_values)

        numerator = sum((c - mean_clv) * (r - mean_roi) for c, r in zip(clv_values, roi_values))
        denom_clv = sum((c - mean_clv) ** 2 for c in clv_values) ** 0.5
        denom_roi = sum((r - mean_roi) ** 2 for r in roi_values) ** 0.5

        correlation = numerator / (denom_clv * denom_roi) if (denom_clv * denom_roi) > 0 else 0
    else:
        correlation = 0

    return {
        "correlation": round(correlation, 3),
        "sample_size": len(bets),
        "positive_clv_bets": len(positive_clv),
        "positive_clv_roi": round(pos_roi, 2),
        "negative_clv_bets": len(negative_clv),
        "negative_clv_roi": round(neg_roi, 2),
        "interpretation": get_correlation_interpretation(correlation, pos_roi, neg_roi)
    }


def get_correlation_interpretation(correlation: float, pos_roi: float, neg_roi: float) -> str:
    """Interpret CLV-ROI correlation."""
    if correlation > 0.3 and pos_roi > neg_roi:
        return "Strong positive correlation - CLV is a good predictor of profitability"
    elif correlation > 0.1:
        return "Moderate positive correlation - some predictive value in CLV"
    elif correlation > -0.1:
        return "Weak correlation - CLV not strongly predictive of ROI"
    else:
        return "Negative correlation - investigate betting patterns"
