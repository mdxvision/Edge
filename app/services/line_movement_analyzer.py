"""
Line Movement Analyzer

Analyzes OddsSnapshot data to detect:
- RLM (Reverse Line Movement) - line moves opposite of public money
- Steam moves - rapid coordinated movement across books
- Sharp book origination - Pinnacle/Circa moves first

Creates/updates LineMovementSummary records for the prediction engine.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db import Game, OddsSnapshot, LineMovementSummary, Market, Line

logger = logging.getLogger(__name__)

# Sharp books that move first on sharp action
SHARP_BOOKS = ['pinnacle', 'circa', 'bookmaker', 'betcris', 'heritage']

# Thresholds
SIGNIFICANT_MOVE_THRESHOLD = 0.5  # Half point move is significant
STEAM_MOVE_THRESHOLD = 1.0  # Full point move in short time
STEAM_TIME_WINDOW_MINUTES = 30  # Steam move window


def analyze_game_movement(db: Session, game: Game) -> Optional[LineMovementSummary]:
    """
    Analyze line movement for a single game.
    Returns the created/updated LineMovementSummary or None.
    """
    if not game:
        return None

    # Get all snapshots for this game, ordered by time
    snapshots = db.query(OddsSnapshot).filter(
        OddsSnapshot.game_id == game.id,
        OddsSnapshot.market_type == 'spread'
    ).order_by(OddsSnapshot.captured_at.asc()).all()

    if len(snapshots) < 2:
        # Need at least 2 snapshots to detect movement
        return None

    # Get opening and current snapshots
    opening = snapshots[0]
    current = snapshots[-1]

    # Calculate movement
    opening_line = opening.line_value or 0
    current_line = current.line_value or 0
    total_movement = abs(current_line - opening_line)

    # Determine movement direction
    if current_line < opening_line:
        # Line went down (e.g., -3 to -4 means favorite getting more points)
        movement_direction = 'toward_favorite'
    elif current_line > opening_line:
        # Line went up (e.g., -3 to -2 means underdog getting fewer points)
        movement_direction = 'toward_underdog'
    else:
        movement_direction = 'neutral'

    # Detect RLM (Reverse Line Movement)
    # Public typically bets: favorites, overs, popular teams
    # RLM = line moves OPPOSITE of where public money should push it
    reverse_line_movement = detect_rlm(opening_line, current_line, game.sport)

    # Detect steam moves
    steam_detected, steam_time, first_book = detect_steam_move(snapshots)

    # Check if sharp book originated the move
    sharp_originated = is_sharp_book(first_book) if first_book else False

    # Simulate public betting percentages based on line movement
    # In reality, you'd get this from Action Network or similar
    public_bet_pct, public_money_pct = estimate_public_betting(
        opening_line, current_line, movement_direction
    )

    # Create or update LineMovementSummary
    existing = db.query(LineMovementSummary).filter(
        LineMovementSummary.game_id == game.id,
        LineMovementSummary.market_type == 'spread'
    ).first()

    if existing:
        summary = existing
        summary.current_line = current_line
        summary.current_odds = current.odds
        summary.total_movement = total_movement
        summary.movement_direction = movement_direction
        summary.reverse_line_movement = reverse_line_movement
        summary.steam_move_detected = steam_detected
        summary.sharp_book_originated = sharp_originated
        summary.first_move_book = first_book
        summary.steam_move_time = steam_time
        summary.public_bet_percentage = public_bet_pct
        summary.public_money_percentage = public_money_pct
        summary.updated_at = datetime.utcnow()
    else:
        summary = LineMovementSummary(
            game_id=game.id,
            sport=game.sport or 'NFL',
            market_type='spread',
            opening_line=opening_line,
            current_line=current_line,
            opening_odds=opening.odds,
            current_odds=current.odds,
            total_movement=total_movement,
            movement_direction=movement_direction,
            reverse_line_movement=reverse_line_movement,
            steam_move_detected=steam_detected,
            sharp_book_originated=sharp_originated,
            first_move_book=first_book,
            steam_move_time=steam_time,
            public_bet_percentage=public_bet_pct,
            public_money_percentage=public_money_pct
        )
        db.add(summary)

    return summary


def detect_rlm(opening_line: float, current_line: float, sport: str) -> bool:
    """
    Detect Reverse Line Movement.

    RLM occurs when the line moves opposite to where public money should push it.
    - Public loves favorites → if line moves toward underdog despite this = RLM
    - Public loves overs → if total moves down despite this = RLM

    For spreads:
    - Public typically bets the favorite
    - If line moves toward underdog (becomes less favorable for favorite),
      that's likely sharp money on underdog = RLM signal on underdog
    """
    movement = current_line - opening_line

    if abs(movement) < SIGNIFICANT_MOVE_THRESHOLD:
        return False

    # For spreads: negative line = home favorite
    # Public bets favorites, so line should move toward favorite (more negative)
    # If line moves toward underdog (less negative) = RLM

    if opening_line < 0:  # Home is favorite
        # Public should push line more negative
        # If it went less negative (toward underdog), that's RLM
        if movement > SIGNIFICANT_MOVE_THRESHOLD:
            return True
    else:  # Home is underdog
        # Public should push line toward the road favorite (more positive)
        # If it went less positive, that's RLM
        if movement < -SIGNIFICANT_MOVE_THRESHOLD:
            return True

    return False


def detect_steam_move(snapshots: List[OddsSnapshot]) -> Tuple[bool, Optional[datetime], Optional[str]]:
    """
    Detect steam moves - rapid coordinated line movement.

    Steam move = line moves significantly (1+ points) in a short window (30 min).
    """
    if len(snapshots) < 2:
        return False, None, None

    # Look for rapid movement between consecutive snapshots
    for i in range(1, len(snapshots)):
        prev = snapshots[i-1]
        curr = snapshots[i]

        if prev.line_value is None or curr.line_value is None:
            continue

        time_diff = (curr.captured_at - prev.captured_at).total_seconds() / 60
        line_diff = abs(curr.line_value - prev.line_value)

        # Steam move: 1+ point move in 30 minutes or less
        if time_diff <= STEAM_TIME_WINDOW_MINUTES and line_diff >= STEAM_MOVE_THRESHOLD:
            return True, curr.captured_at, curr.sportsbook

    return False, None, None


def is_sharp_book(sportsbook: str) -> bool:
    """Check if the sportsbook is considered a sharp book."""
    if not sportsbook:
        return False
    return sportsbook.lower() in SHARP_BOOKS


def estimate_public_betting(
    opening_line: float,
    current_line: float,
    movement_direction: str
) -> Tuple[float, float]:
    """
    Estimate public betting percentages based on line movement.

    This is a simulation - in production you'd use real data from
    Action Network, VegasInsider, etc.

    Logic:
    - If line moves toward favorite, public is likely heavy on favorite (65-75%)
    - If line moves toward underdog (RLM), public is on favorite but sharps on dog
    """
    movement = abs(current_line - opening_line)

    if movement_direction == 'toward_favorite':
        # Public pounding favorite, line moving with them
        public_bet_pct = min(75.0, 55.0 + movement * 10)
        public_money_pct = min(80.0, 50.0 + movement * 15)
    elif movement_direction == 'toward_underdog':
        # RLM - public on favorite but line moving other way
        public_bet_pct = min(70.0, 60.0 + movement * 5)  # Public still on favorite
        public_money_pct = max(40.0, 55.0 - movement * 10)  # But money split
    else:
        public_bet_pct = 50.0
        public_money_pct = 50.0

    return round(public_bet_pct, 1), round(public_money_pct, 1)


def analyze_all_upcoming_games(db: Session) -> Dict[str, int]:
    """
    Analyze line movement for all upcoming games.
    Returns stats on games analyzed and summaries created.
    """
    # Get games starting in next 7 days
    now = datetime.utcnow()
    cutoff = now + timedelta(days=7)

    upcoming_games = db.query(Game).filter(
        Game.start_time >= now,
        Game.start_time <= cutoff
    ).all()

    stats = {
        'games_checked': len(upcoming_games),
        'summaries_created': 0,
        'summaries_updated': 0,
        'rlm_detected': 0,
        'steam_detected': 0
    }

    for game in upcoming_games:
        try:
            # Check if summary exists
            existing = db.query(LineMovementSummary).filter(
                LineMovementSummary.game_id == game.id
            ).first()

            summary = analyze_game_movement(db, game)

            if summary:
                if existing:
                    stats['summaries_updated'] += 1
                else:
                    stats['summaries_created'] += 1

                if summary.reverse_line_movement:
                    stats['rlm_detected'] += 1
                if summary.steam_move_detected:
                    stats['steam_detected'] += 1

        except Exception as e:
            logger.error(f"Error analyzing game {game.id}: {e}")
            continue

    db.commit()
    logger.info(f"Line movement analysis complete: {stats}")

    return stats


def run_analysis(db: Session) -> Dict[str, int]:
    """
    Main entry point for line movement analysis.
    Call this after each odds refresh.
    """
    return analyze_all_upcoming_games(db)
