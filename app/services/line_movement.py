"""
Line Movement Engine

Tracks line changes and detects sharp money indicators.
Key features:
- Reverse Line Movement (RLM) detection
- Steam move detection
- Sharp book tracking (Pinnacle/Circa move first)
- Closing Line Value (CLV) prediction
"""

from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from datetime import datetime, timedelta
import logging

from app.db import LineMovement, LineMovementSummary, Game, OddsSnapshot

logger = logging.getLogger(__name__)

# Sharp books that move first (others follow)
SHARP_BOOKS = ["pinnacle", "circa", "betcris", "bookmaker"]

# Books to track
ALL_BOOKS = [
    "draftkings", "fanduel", "betmgm", "caesars", "pointsbet",
    "pinnacle", "circa", "bovada", "betonline"
]


def record_line_snapshot(
    db: Session,
    game_id: int,
    sport: str,
    sportsbook: str,
    market_type: str,
    line_value: float,
    odds: int
) -> LineMovement:
    """
    Record a line snapshot and calculate movement from previous.

    Args:
        db: Database session
        game_id: Game ID
        sport: Sport code
        sportsbook: Sportsbook name
        market_type: spread, total, or moneyline
        line_value: Current line value
        odds: American odds

    Returns:
        Created LineMovement record
    """
    # Get previous snapshot for this game/book/market
    previous = db.query(LineMovement).filter(
        LineMovement.game_id == game_id,
        LineMovement.sportsbook == sportsbook,
        LineMovement.market_type == market_type
    ).order_by(desc(LineMovement.recorded_at)).first()

    previous_line = previous.current_line if previous else None
    previous_odds = previous.current_odds if previous else None

    # Calculate movement
    movement_pct = None
    direction = None

    if previous_line is not None and previous_line != line_value:
        movement = line_value - previous_line

        if market_type == "spread":
            # Spread moving more negative = toward favorite
            direction = "toward_favorite" if movement < 0 else "toward_underdog"
        elif market_type == "total":
            direction = "toward_over" if movement > 0 else "toward_under"

        # Calculate percentage movement
        if previous_line != 0:
            movement_pct = (movement / abs(previous_line)) * 100

    # Create new movement record
    line_movement = LineMovement(
        game_id=game_id,
        market_type=market_type,
        sportsbook=sportsbook,
        previous_odds=previous_odds,
        current_odds=odds,
        previous_line=previous_line,
        current_line=line_value,
        movement_percentage=movement_pct,
        direction=direction,
        recorded_at=datetime.utcnow()
    )

    db.add(line_movement)
    db.commit()

    # Update summary if significant movement
    _update_movement_summary(db, game_id, sport, market_type)

    return line_movement


def get_line_history(
    db: Session,
    game_id: int,
    market_type: Optional[str] = None,
    sportsbook: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get full line movement history for a game.

    Args:
        db: Database session
        game_id: Game ID
        market_type: Optional filter by market
        sportsbook: Optional filter by book

    Returns:
        List of line movements ordered by time
    """
    query = db.query(LineMovement).filter(LineMovement.game_id == game_id)

    if market_type:
        query = query.filter(LineMovement.market_type == market_type)
    if sportsbook:
        query = query.filter(LineMovement.sportsbook == sportsbook)

    movements = query.order_by(LineMovement.recorded_at).all()

    return [
        {
            "id": m.id,
            "sportsbook": m.sportsbook,
            "market_type": m.market_type,
            "line_value": m.current_line,
            "odds": m.current_odds,
            "previous_line": m.previous_line,
            "movement": m.current_line - m.previous_line if m.previous_line else None,
            "direction": m.direction,
            "recorded_at": m.recorded_at.isoformat() if m.recorded_at else None
        }
        for m in movements
    ]


def calculate_total_movement(
    db: Session,
    game_id: int,
    market_type: str = "spread"
) -> Dict[str, Any]:
    """
    Calculate total line movement from opening to current.

    Args:
        db: Database session
        game_id: Game ID
        market_type: Market type to analyze

    Returns:
        Movement analysis with opening, current, and total movement
    """
    # Get opening line (first recorded)
    opening = db.query(LineMovement).filter(
        LineMovement.game_id == game_id,
        LineMovement.market_type == market_type
    ).order_by(LineMovement.recorded_at).first()

    # Get current line (most recent)
    current = db.query(LineMovement).filter(
        LineMovement.game_id == game_id,
        LineMovement.market_type == market_type
    ).order_by(desc(LineMovement.recorded_at)).first()

    if not opening or not current:
        return {
            "game_id": game_id,
            "market_type": market_type,
            "opening_line": None,
            "current_line": None,
            "total_movement": None,
            "direction": None,
            "message": "Insufficient data"
        }

    total_movement = current.current_line - opening.current_line if opening.current_line else 0

    # Determine direction
    if market_type == "spread":
        if total_movement < -0.5:
            direction = "toward_favorite"
        elif total_movement > 0.5:
            direction = "toward_underdog"
        else:
            direction = "stable"
    elif market_type == "total":
        if total_movement > 0.5:
            direction = "toward_over"
        elif total_movement < -0.5:
            direction = "toward_under"
        else:
            direction = "stable"
    else:
        direction = "unknown"

    return {
        "game_id": game_id,
        "market_type": market_type,
        "opening_line": opening.current_line,
        "current_line": current.current_line,
        "total_movement": round(total_movement, 1),
        "direction": direction,
        "first_recorded": opening.recorded_at.isoformat() if opening.recorded_at else None,
        "last_updated": current.recorded_at.isoformat() if current.recorded_at else None
    }


def detect_reverse_line_movement(
    db: Session,
    game_id: int,
    public_bet_percentage: Optional[float] = None,
    market_type: str = "spread"
) -> Dict[str, Any]:
    """
    Detect reverse line movement (sharp money indicator).

    RLM occurs when the line moves OPPOSITE to public betting percentage.
    E.g., 75% of bets on Team A, but line moves toward Team B = sharp money on B.

    Args:
        db: Database session
        game_id: Game ID
        public_bet_percentage: Percentage of bets on favorite/over (0-100)
        market_type: Market type to analyze

    Returns:
        RLM analysis with confidence and recommendation
    """
    movement = calculate_total_movement(db, game_id, market_type)

    if not movement.get("total_movement"):
        return {
            "game_id": game_id,
            "rlm_detected": False,
            "message": "Insufficient movement data"
        }

    total_move = movement["total_movement"]
    direction = movement["direction"]

    # If we don't have public betting data, we can still flag significant movement
    if public_bet_percentage is None:
        # Assume 50% if unknown
        public_bet_percentage = 50

    rlm_detected = False
    confidence = 0.0
    implication = ""

    if market_type == "spread":
        # If public is heavily on favorite (>65%) but line moves toward underdog
        if public_bet_percentage > 65 and direction == "toward_underdog":
            rlm_detected = True
            confidence = min((public_bet_percentage - 50) / 50 + abs(total_move) / 3, 1.0)
            implication = "Sharp money on underdog"

        # If public is heavily on underdog but line moves toward favorite
        elif public_bet_percentage < 35 and direction == "toward_favorite":
            rlm_detected = True
            confidence = min((50 - public_bet_percentage) / 50 + abs(total_move) / 3, 1.0)
            implication = "Sharp money on favorite"

    elif market_type == "total":
        # If public is heavily on over but line moves down
        if public_bet_percentage > 65 and direction == "toward_under":
            rlm_detected = True
            confidence = min((public_bet_percentage - 50) / 50 + abs(total_move) / 3, 1.0)
            implication = "Sharp money on under"

        elif public_bet_percentage < 35 and direction == "toward_over":
            rlm_detected = True
            confidence = min((50 - public_bet_percentage) / 50 + abs(total_move) / 3, 1.0)
            implication = "Sharp money on over"

    return {
        "game_id": game_id,
        "market_type": market_type,
        "rlm_detected": rlm_detected,
        "confidence": round(confidence, 2),
        "public_bet_percentage": public_bet_percentage,
        "line_direction": direction,
        "total_movement": total_move,
        "implication": implication if rlm_detected else "No clear RLM signal"
    }


def detect_steam_move(
    db: Session,
    game_id: int,
    market_type: str = "spread",
    threshold_minutes: int = 10,
    threshold_movement: float = 1.0
) -> Dict[str, Any]:
    """
    Detect steam moves (rapid coordinated line movement).

    A steam move is when a line moves significantly (1+ points) in a short time
    across multiple books, indicating coordinated sharp action.

    Args:
        db: Database session
        game_id: Game ID
        market_type: Market type to analyze
        threshold_minutes: Time window to detect steam
        threshold_movement: Minimum movement to qualify

    Returns:
        Steam move analysis
    """
    # Get all movements in last hour
    cutoff = datetime.utcnow() - timedelta(hours=1)

    movements = db.query(LineMovement).filter(
        LineMovement.game_id == game_id,
        LineMovement.market_type == market_type,
        LineMovement.recorded_at >= cutoff
    ).order_by(LineMovement.recorded_at).all()

    if len(movements) < 3:
        return {
            "game_id": game_id,
            "steam_detected": False,
            "message": "Insufficient recent data"
        }

    # Look for rapid movement patterns
    steam_detected = False
    steam_time = None
    steam_direction = None
    books_moved = set()

    for i in range(len(movements) - 2):
        window_start = movements[i].recorded_at
        window_movements = []

        # Collect movements within threshold_minutes
        for m in movements[i:]:
            if m.recorded_at and window_start:
                if (m.recorded_at - window_start).total_seconds() <= threshold_minutes * 60:
                    window_movements.append(m)
                else:
                    break

        # Check if multiple books moved significantly
        if len(window_movements) >= 3:
            unique_books = set(m.sportsbook for m in window_movements)
            total_change = 0
            direction_votes = {"positive": 0, "negative": 0}

            for m in window_movements:
                if m.previous_line is not None and m.current_line is not None:
                    change = m.current_line - m.previous_line
                    total_change += change
                    if change > 0:
                        direction_votes["positive"] += 1
                    elif change < 0:
                        direction_votes["negative"] += 1

            # Steam move if 3+ books moved same direction significantly
            avg_movement = total_change / len(window_movements) if window_movements else 0
            if len(unique_books) >= 3 and abs(avg_movement) >= threshold_movement:
                steam_detected = True
                steam_time = window_start
                steam_direction = "up" if avg_movement > 0 else "down"
                books_moved = unique_books
                break

    # Determine recommendation
    recommendation = None
    if steam_detected:
        if market_type == "spread":
            recommendation = "Follow the steam - sharp money identified"
        elif market_type == "total":
            if steam_direction == "up":
                recommendation = "Steam on OVER"
            else:
                recommendation = "Steam on UNDER"

    return {
        "game_id": game_id,
        "market_type": market_type,
        "steam_detected": steam_detected,
        "steam_time": steam_time.isoformat() if steam_time else None,
        "steam_direction": steam_direction,
        "books_moved": list(books_moved) if books_moved else [],
        "recommendation": recommendation
    }


def get_sharp_book_movement(
    db: Session,
    game_id: int,
    market_type: str = "spread"
) -> Dict[str, Any]:
    """
    Track sharp book movements (Pinnacle, Circa move first).

    Sharp books take large limits and have sharp bettors.
    When they move first, others typically follow.

    Args:
        db: Database session
        game_id: Game ID
        market_type: Market type to analyze

    Returns:
        Sharp book analysis
    """
    # Get movements by book
    movements = db.query(LineMovement).filter(
        LineMovement.game_id == game_id,
        LineMovement.market_type == market_type
    ).order_by(LineMovement.recorded_at).all()

    if not movements:
        return {
            "game_id": game_id,
            "sharp_originated": False,
            "message": "No movement data"
        }

    # Find first significant movement
    first_mover = None
    first_direction = None

    for m in movements:
        if m.previous_line is not None and m.current_line is not None:
            change = m.current_line - m.previous_line
            if abs(change) >= 0.5:  # Significant movement
                first_mover = m.sportsbook.lower() if m.sportsbook else None
                first_direction = "positive" if change > 0 else "negative"
                break

    sharp_originated = first_mover in SHARP_BOOKS if first_mover else False

    # Get current sharp book lines vs market
    sharp_lines = []
    market_lines = []

    for m in movements:
        if m.current_line is not None:
            book = m.sportsbook.lower() if m.sportsbook else ""
            if book in SHARP_BOOKS:
                sharp_lines.append(m.current_line)
            else:
                market_lines.append(m.current_line)

    sharp_avg = sum(sharp_lines) / len(sharp_lines) if sharp_lines else None
    market_avg = sum(market_lines) / len(market_lines) if market_lines else None

    # Calculate divergence
    divergence = None
    if sharp_avg is not None and market_avg is not None:
        divergence = round(sharp_avg - market_avg, 2)

    return {
        "game_id": game_id,
        "market_type": market_type,
        "sharp_originated": sharp_originated,
        "first_mover": first_mover,
        "sharp_average": round(sharp_avg, 2) if sharp_avg else None,
        "market_average": round(market_avg, 2) if market_avg else None,
        "divergence": divergence,
        "recommendation": _get_sharp_recommendation(sharp_originated, divergence)
    }


def _get_sharp_recommendation(sharp_originated: bool, divergence: Optional[float]) -> str:
    """Generate recommendation based on sharp book analysis."""
    if sharp_originated:
        if divergence and abs(divergence) >= 0.5:
            return f"Sharp books at different number ({divergence:+.1f}) - consider waiting for market to adjust"
        return "Sharp money moved first - consider following the steam"
    return "Movement originated from public books - less reliable signal"


def calculate_clv_potential(
    db: Session,
    game_id: int,
    bet_line: float,
    market_type: str = "spread"
) -> Dict[str, Any]:
    """
    Estimate closing line value potential.

    CLV is the difference between your bet line and the closing line.
    Positive CLV indicates a good bet, even if it loses.

    Args:
        db: Database session
        game_id: Game ID
        bet_line: The line at which you would bet
        market_type: Market type

    Returns:
        CLV prediction with confidence
    """
    movement = calculate_total_movement(db, game_id, market_type)
    sharp = get_sharp_book_movement(db, game_id, market_type)
    rlm = detect_reverse_line_movement(db, game_id, market_type=market_type)

    if not movement.get("current_line"):
        return {
            "game_id": game_id,
            "clv_prediction": None,
            "message": "Insufficient data"
        }

    current_line = movement["current_line"]

    # Predict closing line based on sharp indicators
    projected_movement = 0.0

    # Sharp book divergence suggests market will move toward sharp line
    if sharp.get("divergence"):
        projected_movement += sharp["divergence"] * 0.5

    # RLM suggests continued movement in sharp direction
    if rlm.get("rlm_detected") and rlm.get("confidence", 0) > 0.5:
        if rlm.get("line_direction") in ["toward_favorite", "toward_under"]:
            projected_movement -= 0.5
        else:
            projected_movement += 0.5

    # Project closing line
    projected_closing = current_line + projected_movement

    # Calculate potential CLV
    clv = bet_line - projected_closing if market_type == "spread" else projected_closing - bet_line

    # Positive CLV is good for spread bets (you got more points)
    # For totals, depends on which side you're on

    return {
        "game_id": game_id,
        "market_type": market_type,
        "bet_line": bet_line,
        "current_line": current_line,
        "projected_closing": round(projected_closing, 1),
        "expected_clv": round(clv, 2),
        "clv_interpretation": _interpret_clv(clv, market_type),
        "confidence": round(min(0.3 + (abs(clv) * 0.1), 0.8), 2)
    }


def _interpret_clv(clv: float, market_type: str) -> str:
    """Interpret CLV value."""
    if abs(clv) < 0.3:
        return "Neutral - line unlikely to move significantly"
    elif clv > 0:
        if market_type == "spread":
            return f"Positive CLV (+{clv:.1f}) - good value getting extra points"
        else:
            return f"Positive CLV (+{clv:.1f}) - line expected to move your direction"
    else:
        return f"Negative CLV ({clv:.1f}) - consider waiting for better line"


def _update_movement_summary(
    db: Session,
    game_id: int,
    sport: str,
    market_type: str
):
    """Update or create movement summary for a game."""
    # Check for existing summary
    summary = db.query(LineMovementSummary).filter(
        LineMovementSummary.game_id == game_id,
        LineMovementSummary.market_type == market_type
    ).first()

    # Calculate current stats
    movement_data = calculate_total_movement(db, game_id, market_type)
    steam = detect_steam_move(db, game_id, market_type)
    rlm = detect_reverse_line_movement(db, game_id, market_type=market_type)
    sharp = get_sharp_book_movement(db, game_id, market_type)

    if summary:
        # Update existing
        summary.current_line = movement_data.get("current_line")
        summary.total_movement = movement_data.get("total_movement")
        summary.movement_direction = movement_data.get("direction")
        summary.steam_move_detected = steam.get("steam_detected", False)
        summary.reverse_line_movement = rlm.get("rlm_detected", False)
        summary.sharp_book_originated = sharp.get("sharp_originated", False)
        summary.first_move_book = sharp.get("first_mover")
        summary.updated_at = datetime.utcnow()
    else:
        # Create new
        summary = LineMovementSummary(
            game_id=game_id,
            sport=sport,
            market_type=market_type,
            opening_line=movement_data.get("opening_line"),
            current_line=movement_data.get("current_line"),
            total_movement=movement_data.get("total_movement"),
            movement_direction=movement_data.get("direction"),
            steam_move_detected=steam.get("steam_detected", False),
            reverse_line_movement=rlm.get("rlm_detected", False),
            sharp_book_originated=sharp.get("sharp_originated", False),
            first_move_book=sharp.get("first_mover")
        )
        db.add(summary)

    db.commit()


def get_games_with_alerts(
    db: Session,
    sport: Optional[str] = None,
    alert_type: Optional[str] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Get games with significant line movement alerts.

    Args:
        db: Database session
        sport: Optional sport filter
        alert_type: Filter by alert type (steam, rlm, sharp)
        limit: Max results

    Returns:
        List of games with alerts
    """
    query = db.query(LineMovementSummary)

    if sport:
        query = query.filter(LineMovementSummary.sport == sport)

    if alert_type == "steam":
        query = query.filter(LineMovementSummary.steam_move_detected == True)
    elif alert_type == "rlm":
        query = query.filter(LineMovementSummary.reverse_line_movement == True)
    elif alert_type == "sharp":
        query = query.filter(LineMovementSummary.sharp_book_originated == True)
    else:
        # Any significant alert
        query = query.filter(
            (LineMovementSummary.steam_move_detected == True) |
            (LineMovementSummary.reverse_line_movement == True) |
            (LineMovementSummary.sharp_book_originated == True)
        )

    summaries = query.order_by(desc(LineMovementSummary.updated_at)).limit(limit).all()

    return [
        {
            "game_id": s.game_id,
            "sport": s.sport,
            "market_type": s.market_type,
            "opening_line": s.opening_line,
            "current_line": s.current_line,
            "total_movement": s.total_movement,
            "direction": s.movement_direction,
            "alerts": {
                "steam_move": s.steam_move_detected,
                "rlm": s.reverse_line_movement,
                "sharp_originated": s.sharp_book_originated
            },
            "first_mover": s.first_move_book,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None
        }
        for s in summaries
    ]


def get_movement_analysis(
    db: Session,
    game_id: int,
    market_type: str = "spread",
    public_bet_pct: Optional[float] = None
) -> Dict[str, Any]:
    """
    Get comprehensive movement analysis for a game.

    Returns all indicators: movement, RLM, steam, sharp book analysis.
    """
    movement = calculate_total_movement(db, game_id, market_type)
    rlm = detect_reverse_line_movement(db, game_id, public_bet_pct, market_type)
    steam = detect_steam_move(db, game_id, market_type)
    sharp = get_sharp_book_movement(db, game_id, market_type)

    # Build alerts list
    alerts = []

    if rlm.get("rlm_detected"):
        alerts.append({
            "type": "REVERSE_LINE_MOVEMENT",
            "message": f"{public_bet_pct or 50:.0f}% of bets on one side, line moved opposite",
            "implication": rlm.get("implication"),
            "confidence": rlm.get("confidence", 0)
        })

    if steam.get("steam_detected"):
        alerts.append({
            "type": "STEAM_MOVE",
            "message": f"Rapid coordinated movement detected at {steam.get('steam_time', 'unknown time')}",
            "implication": steam.get("recommendation"),
            "confidence": 0.85
        })

    if sharp.get("sharp_originated"):
        alerts.append({
            "type": "SHARP_BOOK_LEAD",
            "message": f"{sharp.get('first_mover', 'Sharp book').title()} moved first",
            "implication": "Follow sharp books",
            "confidence": 0.75
        })

    # Generate recommendation
    recommendation = _generate_recommendation(movement, alerts)

    return {
        "game_id": game_id,
        "market": market_type,
        "opening_line": movement.get("opening_line"),
        "current_line": movement.get("current_line"),
        "movement": f"{movement.get('total_movement', 0):+.1f}" if movement.get("total_movement") else "0",
        "direction": movement.get("direction"),
        "alerts": alerts,
        "alert_count": len(alerts),
        "recommendation": recommendation
    }


def _generate_recommendation(movement: Dict, alerts: List) -> str:
    """Generate betting recommendation based on analysis."""
    if not alerts:
        return "No significant indicators - bet at your discretion"

    # Strong signals
    rlm_alert = next((a for a in alerts if a["type"] == "REVERSE_LINE_MOVEMENT"), None)
    steam_alert = next((a for a in alerts if a["type"] == "STEAM_MOVE"), None)
    sharp_alert = next((a for a in alerts if a["type"] == "SHARP_BOOK_LEAD"), None)

    if rlm_alert and steam_alert:
        return "STRONG SIGNAL: RLM + Steam move - consider following sharp money"

    if rlm_alert and rlm_alert.get("confidence", 0) > 0.7:
        return f"SHARP MONEY SIGNAL: {rlm_alert.get('implication', 'Follow the money')}"

    if steam_alert:
        return f"STEAM ALERT: {steam_alert.get('implication', 'Follow the steam')}"

    if sharp_alert:
        return "Sharp books moved first - monitor for additional movement"

    return "Minor signals detected - proceed with caution"
