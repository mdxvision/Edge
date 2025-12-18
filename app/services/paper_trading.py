"""
Paper Trading Service

Virtual bankroll tracking for validating betting strategies without real money.
"""

from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from datetime import datetime, timedelta
import logging
import json

from app.db import PaperTrade, PaperBankroll, PaperBankrollHistory

logger = logging.getLogger(__name__)

DEFAULT_STARTING_BALANCE = 10000.0
UNIT_SIZE = 100.0  # 1% of starting bankroll


def calculate_payout(stake: float, odds: int) -> float:
    """Calculate potential payout from American odds."""
    if odds > 0:
        return stake + (stake * odds / 100)
    else:
        return stake + (stake * 100 / abs(odds))


def get_or_create_bankroll(db: Session, user_id: Optional[int] = None) -> PaperBankroll:
    """Get or create a paper bankroll for the user."""
    bankroll = db.query(PaperBankroll).filter(
        PaperBankroll.user_id == user_id
    ).first()

    if not bankroll:
        bankroll = PaperBankroll(
            user_id=user_id,
            starting_balance=DEFAULT_STARTING_BALANCE,
            current_balance=DEFAULT_STARTING_BALANCE,
            high_water_mark=DEFAULT_STARTING_BALANCE,
            low_water_mark=DEFAULT_STARTING_BALANCE,
        )
        db.add(bankroll)
        db.commit()
        db.refresh(bankroll)

        # Create initial history entry
        history = PaperBankrollHistory(
            user_id=user_id,
            bankroll_id=bankroll.id,
            date=datetime.utcnow(),
            balance=DEFAULT_STARTING_BALANCE,
        )
        db.add(history)
        db.commit()

    return bankroll


def get_bankroll_status(db: Session, user_id: Optional[int] = None) -> Dict[str, Any]:
    """Get current bankroll status and stats."""
    bankroll = get_or_create_bankroll(db, user_id)

    return {
        "bankroll_id": bankroll.id,
        "starting_balance": bankroll.starting_balance,
        "current_balance": round(bankroll.current_balance, 2),
        "high_water_mark": round(bankroll.high_water_mark, 2),
        "low_water_mark": round(bankroll.low_water_mark, 2),
        "total_profit_loss": round(bankroll.total_profit_loss, 2),
        "total_wagered": round(bankroll.total_wagered, 2),
        "roi_percentage": round(bankroll.roi_percentage, 2) if bankroll.roi_percentage else 0,
        "win_percentage": round(bankroll.win_percentage, 2) if bankroll.win_percentage else 0,
        "units_won": round(bankroll.units_won, 2),
        "stats": {
            "total_bets": bankroll.total_bets,
            "pending_bets": bankroll.pending_bets,
            "winning_bets": bankroll.winning_bets,
            "losing_bets": bankroll.losing_bets,
            "pushes": bankroll.pushes,
        },
        "streaks": {
            "current": bankroll.current_streak,
            "longest_win": bankroll.longest_win_streak,
            "longest_lose": bankroll.longest_lose_streak,
        },
        "created_at": bankroll.created_at.isoformat() if bankroll.created_at else None,
        "last_updated": bankroll.last_updated.isoformat() if bankroll.last_updated else None,
    }


def place_bet(
    db: Session,
    sport: str,
    bet_type: str,
    selection: str,
    odds: int,
    stake: float,
    game_id: Optional[str] = None,
    game_description: Optional[str] = None,
    line_value: Optional[float] = None,
    game_date: Optional[datetime] = None,
    edge_at_placement: Optional[float] = None,
    notes: Optional[str] = None,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Place a new paper trade.

    Args:
        sport: Sport code (NFL, NBA, etc.)
        bet_type: Type of bet (spread, moneyline, total)
        selection: What you're betting on (team name, over/under)
        odds: American odds (-110, +150, etc.)
        stake: Amount to wager
        game_id: Optional external game ID
        game_description: Optional game description
        line_value: Optional spread/total number
        game_date: When the game is
        edge_at_placement: EdgeBet's calculated edge
        notes: Any notes
        user_id: User ID if authenticated

    Returns:
        Dict with trade details
    """
    bankroll = get_or_create_bankroll(db, user_id)

    # Validate stake
    if stake <= 0:
        return {"error": "Stake must be positive"}
    if stake > bankroll.current_balance:
        return {"error": f"Insufficient balance. Available: ${bankroll.current_balance:.2f}"}

    # Calculate potential payout
    potential_payout = calculate_payout(stake, odds)

    # Create the trade
    trade = PaperTrade(
        user_id=user_id,
        sport=sport.upper(),
        game_id=game_id,
        game_description=game_description,
        bet_type=bet_type.lower(),
        selection=selection,
        line_value=line_value,
        odds=odds,
        stake=stake,
        potential_payout=potential_payout,
        game_date=game_date,
        edge_at_placement=edge_at_placement,
        notes=notes,
        status="pending",
    )
    db.add(trade)

    # Update bankroll
    bankroll.current_balance -= stake
    bankroll.total_wagered += stake
    bankroll.total_bets += 1
    bankroll.pending_bets += 1

    # Update low water mark
    if bankroll.current_balance < bankroll.low_water_mark:
        bankroll.low_water_mark = bankroll.current_balance

    db.commit()
    db.refresh(trade)

    return {
        "success": True,
        "trade_id": trade.id,
        "sport": trade.sport,
        "bet_type": trade.bet_type,
        "selection": trade.selection,
        "line_value": trade.line_value,
        "odds": trade.odds,
        "stake": trade.stake,
        "potential_payout": round(trade.potential_payout, 2),
        "game_description": trade.game_description,
        "status": trade.status,
        "placed_at": trade.placed_at.isoformat(),
        "current_balance": round(bankroll.current_balance, 2),
    }


def settle_bet(
    db: Session,
    trade_id: int,
    result: str,  # "won", "lost", "push"
    result_score: Optional[str] = None,
    closing_line_value: Optional[float] = None,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Settle a pending paper trade.

    Args:
        trade_id: ID of the trade to settle
        result: Outcome - "won", "lost", or "push"
        result_score: Final score (e.g., "Chiefs 24 - Bills 21")
        closing_line_value: What the line closed at
        user_id: User ID for verification

    Returns:
        Dict with settlement details
    """
    trade = db.query(PaperTrade).filter(PaperTrade.id == trade_id).first()

    if not trade:
        return {"error": "Trade not found"}
    if trade.status != "pending":
        return {"error": f"Trade already settled with status: {trade.status}"}
    if user_id and trade.user_id != user_id:
        return {"error": "Not authorized to settle this trade"}

    bankroll = get_or_create_bankroll(db, trade.user_id)

    # Calculate profit/loss
    if result == "won":
        profit_loss = trade.potential_payout - trade.stake
        bankroll.current_balance += trade.potential_payout
        bankroll.total_won += profit_loss
        bankroll.winning_bets += 1
        bankroll.current_streak = max(1, bankroll.current_streak + 1) if bankroll.current_streak >= 0 else 1
        bankroll.longest_win_streak = max(bankroll.longest_win_streak, bankroll.current_streak)
    elif result == "lost":
        profit_loss = -trade.stake
        bankroll.total_lost += trade.stake
        bankroll.losing_bets += 1
        bankroll.current_streak = min(-1, bankroll.current_streak - 1) if bankroll.current_streak <= 0 else -1
        bankroll.longest_lose_streak = max(bankroll.longest_lose_streak, abs(bankroll.current_streak))
    else:  # push
        profit_loss = 0
        bankroll.current_balance += trade.stake  # Return stake
        bankroll.pushes += 1
        bankroll.current_streak = 0

    # Update trade
    trade.status = result
    trade.result_score = result_score
    trade.profit_loss = profit_loss
    trade.closing_line_value = closing_line_value
    trade.settled_at = datetime.utcnow()

    # Update bankroll stats
    bankroll.pending_bets -= 1
    bankroll.total_profit_loss = bankroll.total_won - bankroll.total_lost

    # Update ROI
    if bankroll.total_wagered > 0:
        bankroll.roi_percentage = (bankroll.total_profit_loss / bankroll.total_wagered) * 100

    # Update win percentage
    settled = bankroll.winning_bets + bankroll.losing_bets
    if settled > 0:
        bankroll.win_percentage = (bankroll.winning_bets / settled) * 100

    # Update units won (based on 1% = 1 unit)
    bankroll.units_won = bankroll.total_profit_loss / UNIT_SIZE

    # Update high water mark
    if bankroll.current_balance > bankroll.high_water_mark:
        bankroll.high_water_mark = bankroll.current_balance

    db.commit()

    return {
        "success": True,
        "trade_id": trade.id,
        "result": result,
        "profit_loss": round(profit_loss, 2),
        "result_score": result_score,
        "new_balance": round(bankroll.current_balance, 2),
        "total_profit_loss": round(bankroll.total_profit_loss, 2),
        "roi_percentage": round(bankroll.roi_percentage or 0, 2),
    }


def get_open_bets(
    db: Session,
    user_id: Optional[int] = None,
    sport: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get all pending paper trades."""
    query = db.query(PaperTrade).filter(
        PaperTrade.status == "pending"
    )

    if user_id:
        query = query.filter(PaperTrade.user_id == user_id)
    if sport:
        query = query.filter(PaperTrade.sport == sport.upper())

    trades = query.order_by(desc(PaperTrade.placed_at)).all()

    return [
        {
            "id": t.id,
            "sport": t.sport,
            "bet_type": t.bet_type,
            "selection": t.selection,
            "line_value": t.line_value,
            "odds": t.odds,
            "stake": t.stake,
            "potential_payout": round(t.potential_payout, 2),
            "game_description": t.game_description,
            "game_date": t.game_date.isoformat() if t.game_date else None,
            "edge_at_placement": t.edge_at_placement,
            "placed_at": t.placed_at.isoformat(),
            "status": t.status,
        }
        for t in trades
    ]


def get_bet_history(
    db: Session,
    user_id: Optional[int] = None,
    sport: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Get settled paper trades history."""
    query = db.query(PaperTrade)

    if user_id:
        query = query.filter(PaperTrade.user_id == user_id)
    if sport:
        query = query.filter(PaperTrade.sport == sport.upper())
    if status:
        query = query.filter(PaperTrade.status == status)
    else:
        query = query.filter(PaperTrade.status.in_(["won", "lost", "push"]))

    trades = query.order_by(desc(PaperTrade.settled_at)).limit(limit).all()

    return [
        {
            "id": t.id,
            "sport": t.sport,
            "bet_type": t.bet_type,
            "selection": t.selection,
            "line_value": t.line_value,
            "odds": t.odds,
            "stake": t.stake,
            "potential_payout": round(t.potential_payout, 2),
            "profit_loss": round(t.profit_loss, 2) if t.profit_loss else 0,
            "game_description": t.game_description,
            "result_score": t.result_score,
            "status": t.status,
            "edge_at_placement": t.edge_at_placement,
            "closing_line_value": t.closing_line_value,
            "placed_at": t.placed_at.isoformat(),
            "settled_at": t.settled_at.isoformat() if t.settled_at else None,
        }
        for t in trades
    ]


def get_trade_by_id(db: Session, trade_id: int) -> Optional[Dict[str, Any]]:
    """Get a single trade by ID."""
    trade = db.query(PaperTrade).filter(PaperTrade.id == trade_id).first()
    if not trade:
        return None

    return {
        "id": trade.id,
        "sport": trade.sport,
        "bet_type": trade.bet_type,
        "selection": trade.selection,
        "line_value": trade.line_value,
        "odds": trade.odds,
        "stake": trade.stake,
        "potential_payout": round(trade.potential_payout, 2),
        "profit_loss": round(trade.profit_loss, 2) if trade.profit_loss else None,
        "game_id": trade.game_id,
        "game_description": trade.game_description,
        "game_date": trade.game_date.isoformat() if trade.game_date else None,
        "result_score": trade.result_score,
        "status": trade.status,
        "edge_at_placement": trade.edge_at_placement,
        "closing_line_value": trade.closing_line_value,
        "notes": trade.notes,
        "placed_at": trade.placed_at.isoformat(),
        "settled_at": trade.settled_at.isoformat() if trade.settled_at else None,
    }


def cancel_bet(db: Session, trade_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
    """Cancel a pending bet and return the stake."""
    trade = db.query(PaperTrade).filter(PaperTrade.id == trade_id).first()

    if not trade:
        return {"error": "Trade not found"}
    if trade.status != "pending":
        return {"error": "Can only cancel pending trades"}
    if user_id and trade.user_id != user_id:
        return {"error": "Not authorized"}

    bankroll = get_or_create_bankroll(db, trade.user_id)

    # Return stake
    bankroll.current_balance += trade.stake
    bankroll.total_wagered -= trade.stake
    bankroll.total_bets -= 1
    bankroll.pending_bets -= 1

    trade.status = "cancelled"
    trade.settled_at = datetime.utcnow()

    db.commit()

    return {
        "success": True,
        "trade_id": trade.id,
        "stake_returned": trade.stake,
        "new_balance": round(bankroll.current_balance, 2),
    }


def reset_bankroll(db: Session, user_id: Optional[int] = None) -> Dict[str, Any]:
    """Reset bankroll to starting balance. Deletes all trades."""
    bankroll = db.query(PaperBankroll).filter(
        PaperBankroll.user_id == user_id
    ).first()

    if bankroll:
        # Delete all trades
        db.query(PaperTrade).filter(
            PaperTrade.user_id == user_id
        ).delete()

        # Delete history
        db.query(PaperBankrollHistory).filter(
            PaperBankrollHistory.bankroll_id == bankroll.id
        ).delete()

        # Reset bankroll
        bankroll.current_balance = DEFAULT_STARTING_BALANCE
        bankroll.high_water_mark = DEFAULT_STARTING_BALANCE
        bankroll.low_water_mark = DEFAULT_STARTING_BALANCE
        bankroll.total_bets = 0
        bankroll.pending_bets = 0
        bankroll.winning_bets = 0
        bankroll.losing_bets = 0
        bankroll.pushes = 0
        bankroll.total_wagered = 0
        bankroll.total_won = 0
        bankroll.total_lost = 0
        bankroll.total_profit_loss = 0
        bankroll.win_percentage = None
        bankroll.roi_percentage = None
        bankroll.units_won = 0
        bankroll.current_streak = 0
        bankroll.longest_win_streak = 0
        bankroll.longest_lose_streak = 0
        bankroll.last_updated = datetime.utcnow()

        # Create new history entry
        history = PaperBankrollHistory(
            user_id=user_id,
            bankroll_id=bankroll.id,
            date=datetime.utcnow(),
            balance=DEFAULT_STARTING_BALANCE,
        )
        db.add(history)

        db.commit()

    return {
        "success": True,
        "message": "Bankroll reset to $10,000",
        "new_balance": DEFAULT_STARTING_BALANCE,
    }


def get_bankroll_chart_data(
    db: Session,
    user_id: Optional[int] = None,
    days: int = 30,
) -> List[Dict[str, Any]]:
    """Get bankroll history for charting."""
    bankroll = get_or_create_bankroll(db, user_id)

    cutoff = datetime.utcnow() - timedelta(days=days)

    history = db.query(PaperBankrollHistory).filter(
        PaperBankrollHistory.bankroll_id == bankroll.id,
        PaperBankrollHistory.date >= cutoff,
    ).order_by(PaperBankrollHistory.date).all()

    return [
        {
            "date": h.date.isoformat(),
            "balance": round(h.balance, 2),
            "daily_profit_loss": round(h.daily_profit_loss, 2),
            "bets_placed": h.bets_placed,
            "bets_settled": h.bets_settled,
        }
        for h in history
    ]


def get_performance_by_sport(
    db: Session,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Get performance breakdown by sport."""
    trades = db.query(PaperTrade).filter(
        PaperTrade.status.in_(["won", "lost", "push"])
    )

    if user_id:
        trades = trades.filter(PaperTrade.user_id == user_id)

    trades = trades.all()

    by_sport = {}
    for t in trades:
        if t.sport not in by_sport:
            by_sport[t.sport] = {
                "bets": 0,
                "wins": 0,
                "losses": 0,
                "pushes": 0,
                "wagered": 0,
                "profit_loss": 0,
            }

        by_sport[t.sport]["bets"] += 1
        by_sport[t.sport]["wagered"] += t.stake

        if t.status == "won":
            by_sport[t.sport]["wins"] += 1
            by_sport[t.sport]["profit_loss"] += t.profit_loss or 0
        elif t.status == "lost":
            by_sport[t.sport]["losses"] += 1
            by_sport[t.sport]["profit_loss"] += t.profit_loss or 0
        else:
            by_sport[t.sport]["pushes"] += 1

    # Calculate percentages
    result = {}
    for sport, stats in by_sport.items():
        settled = stats["wins"] + stats["losses"]
        result[sport] = {
            **stats,
            "win_percentage": round((stats["wins"] / settled) * 100, 1) if settled > 0 else 0,
            "roi": round((stats["profit_loss"] / stats["wagered"]) * 100, 1) if stats["wagered"] > 0 else 0,
            "profit_loss": round(stats["profit_loss"], 2),
            "wagered": round(stats["wagered"], 2),
        }

    return result


def get_performance_by_bet_type(
    db: Session,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Get performance breakdown by bet type."""
    trades = db.query(PaperTrade).filter(
        PaperTrade.status.in_(["won", "lost", "push"])
    )

    if user_id:
        trades = trades.filter(PaperTrade.user_id == user_id)

    trades = trades.all()

    by_type = {}
    for t in trades:
        bet_type = t.bet_type
        if bet_type not in by_type:
            by_type[bet_type] = {
                "bets": 0,
                "wins": 0,
                "losses": 0,
                "pushes": 0,
                "wagered": 0,
                "profit_loss": 0,
            }

        by_type[bet_type]["bets"] += 1
        by_type[bet_type]["wagered"] += t.stake

        if t.status == "won":
            by_type[bet_type]["wins"] += 1
            by_type[bet_type]["profit_loss"] += t.profit_loss or 0
        elif t.status == "lost":
            by_type[bet_type]["losses"] += 1
            by_type[bet_type]["profit_loss"] += t.profit_loss or 0
        else:
            by_type[bet_type]["pushes"] += 1

    # Calculate percentages
    result = {}
    for bet_type, stats in by_type.items():
        settled = stats["wins"] + stats["losses"]
        result[bet_type] = {
            **stats,
            "win_percentage": round((stats["wins"] / settled) * 100, 1) if settled > 0 else 0,
            "roi": round((stats["profit_loss"] / stats["wagered"]) * 100, 1) if stats["wagered"] > 0 else 0,
            "profit_loss": round(stats["profit_loss"], 2),
            "wagered": round(stats["wagered"], 2),
        }

    return result
