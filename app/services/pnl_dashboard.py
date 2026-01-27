"""
P&L Dashboard Service

Comprehensive profit/loss tracking and analytics for bet tracking.
Provides ROI by sport/market, streak analysis, unit tracking, and CSV export.
"""

import csv
import io
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_

from app.db import TrackedBet, User
from app.services.currency import convert_currency
from app.utils.logging import get_logger

logger = get_logger(__name__)


class TimeFrame(str, Enum):
    """Time frames for P&L analysis."""
    TODAY = "today"
    YESTERDAY = "yesterday"
    THIS_WEEK = "this_week"
    LAST_WEEK = "last_week"
    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"
    LAST_30_DAYS = "last_30_days"
    LAST_90_DAYS = "last_90_days"
    THIS_YEAR = "this_year"
    ALL_TIME = "all_time"


@dataclass
class StreakInfo:
    """Information about a betting streak."""
    streak_type: str  # "win" or "lose"
    length: int
    start_date: datetime
    end_date: datetime
    profit_loss: float
    bets: List[int]  # bet IDs


def get_timeframe_dates(timeframe: TimeFrame) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Get start and end dates for a timeframe."""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if timeframe == TimeFrame.TODAY:
        return today_start, now

    elif timeframe == TimeFrame.YESTERDAY:
        yesterday = today_start - timedelta(days=1)
        return yesterday, today_start

    elif timeframe == TimeFrame.THIS_WEEK:
        # Start of current week (Monday)
        start = today_start - timedelta(days=now.weekday())
        return start, now

    elif timeframe == TimeFrame.LAST_WEEK:
        this_week_start = today_start - timedelta(days=now.weekday())
        last_week_start = this_week_start - timedelta(days=7)
        return last_week_start, this_week_start

    elif timeframe == TimeFrame.THIS_MONTH:
        start = today_start.replace(day=1)
        return start, now

    elif timeframe == TimeFrame.LAST_MONTH:
        this_month_start = today_start.replace(day=1)
        last_month_end = this_month_start - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        return last_month_start, this_month_start

    elif timeframe == TimeFrame.LAST_30_DAYS:
        return now - timedelta(days=30), now

    elif timeframe == TimeFrame.LAST_90_DAYS:
        return now - timedelta(days=90), now

    elif timeframe == TimeFrame.THIS_YEAR:
        start = today_start.replace(month=1, day=1)
        return start, now

    else:  # ALL_TIME
        return None, None


def get_pnl_summary(
    db: Session,
    user_id: int,
    timeframe: TimeFrame = TimeFrame.ALL_TIME,
    currency: str = "USD"
) -> Dict[str, Any]:
    """
    Get comprehensive P&L summary for a user.

    Returns overview stats, daily breakdown, and comparison to previous period.
    """
    start_date, end_date = get_timeframe_dates(timeframe)

    query = db.query(TrackedBet).filter(
        TrackedBet.user_id == user_id,
        TrackedBet.status == "settled"
    )

    if start_date:
        query = query.filter(TrackedBet.settled_at >= start_date)
    if end_date:
        query = query.filter(TrackedBet.settled_at <= end_date)

    bets = query.order_by(TrackedBet.settled_at).all()

    if not bets:
        return {
            "timeframe": timeframe.value,
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            },
            "summary": _empty_summary(currency),
            "daily_breakdown": [],
            "comparison": None
        }

    # Calculate summary stats
    summary = _calculate_summary(bets, currency)

    # Daily breakdown
    daily = _get_daily_breakdown(bets, currency)

    # Previous period comparison
    comparison = _get_period_comparison(db, user_id, timeframe, summary, currency)

    return {
        "timeframe": timeframe.value,
        "period": {
            "start": start_date.isoformat() if start_date else bets[0].settled_at.isoformat(),
            "end": end_date.isoformat() if end_date else bets[-1].settled_at.isoformat()
        },
        "summary": summary,
        "daily_breakdown": daily,
        "comparison": comparison
    }


def _empty_summary(currency: str) -> Dict[str, Any]:
    """Return empty summary structure."""
    return {
        "total_bets": 0,
        "wins": 0,
        "losses": 0,
        "pushes": 0,
        "win_rate": 0.0,
        "total_staked": 0.0,
        "total_profit": 0.0,
        "roi": 0.0,
        "average_stake": 0.0,
        "average_odds": 0,
        "average_profit_per_bet": 0.0,
        "biggest_win": 0.0,
        "biggest_loss": 0.0,
        "currency": currency
    }


def _calculate_summary(bets: List[TrackedBet], currency: str) -> Dict[str, Any]:
    """Calculate summary statistics from bets."""
    total = len(bets)
    wins = sum(1 for b in bets if b.result == "won")
    losses = sum(1 for b in bets if b.result == "lost")
    pushes = sum(1 for b in bets if b.result in ["push", "void"])

    total_staked = sum(convert_currency(b.stake, b.currency, currency) for b in bets)
    total_profit = sum(convert_currency(b.profit_loss or 0, b.currency, currency) for b in bets)

    profits = [convert_currency(b.profit_loss or 0, b.currency, currency) for b in bets]
    wins_only = [p for p in profits if p > 0]
    losses_only = [p for p in profits if p < 0]

    return {
        "total_bets": total,
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "win_rate": round(wins / total * 100, 2) if total > 0 else 0.0,
        "total_staked": round(total_staked, 2),
        "total_profit": round(total_profit, 2),
        "roi": round(total_profit / total_staked * 100, 2) if total_staked > 0 else 0.0,
        "average_stake": round(total_staked / total, 2) if total > 0 else 0.0,
        "average_odds": int(sum(b.odds for b in bets) / total) if total > 0 else 0,
        "average_profit_per_bet": round(total_profit / total, 2) if total > 0 else 0.0,
        "biggest_win": round(max(wins_only), 2) if wins_only else 0.0,
        "biggest_loss": round(min(losses_only), 2) if losses_only else 0.0,
        "currency": currency
    }


def _get_daily_breakdown(bets: List[TrackedBet], currency: str) -> List[Dict[str, Any]]:
    """Get daily P&L breakdown."""
    daily = {}
    cumulative = 0.0

    for bet in bets:
        date_key = bet.settled_at.strftime("%Y-%m-%d")
        profit = convert_currency(bet.profit_loss or 0, bet.currency, currency)

        if date_key not in daily:
            daily[date_key] = {
                "date": date_key,
                "bets": 0,
                "wins": 0,
                "losses": 0,
                "staked": 0.0,
                "profit": 0.0,
                "cumulative": 0.0
            }

        daily[date_key]["bets"] += 1
        if bet.result == "won":
            daily[date_key]["wins"] += 1
        elif bet.result == "lost":
            daily[date_key]["losses"] += 1

        daily[date_key]["staked"] += convert_currency(bet.stake, bet.currency, currency)
        daily[date_key]["profit"] += profit
        cumulative += profit
        daily[date_key]["cumulative"] = round(cumulative, 2)

    # Round values
    for d in daily.values():
        d["staked"] = round(d["staked"], 2)
        d["profit"] = round(d["profit"], 2)

    return list(daily.values())


def _get_period_comparison(
    db: Session,
    user_id: int,
    timeframe: TimeFrame,
    current_summary: Dict[str, Any],
    currency: str
) -> Optional[Dict[str, Any]]:
    """Compare current period to previous period."""
    if timeframe == TimeFrame.ALL_TIME:
        return None

    start_date, end_date = get_timeframe_dates(timeframe)
    if not start_date or not end_date:
        return None

    period_length = (end_date - start_date).days
    prev_start = start_date - timedelta(days=period_length)
    prev_end = start_date

    prev_bets = db.query(TrackedBet).filter(
        TrackedBet.user_id == user_id,
        TrackedBet.status == "settled",
        TrackedBet.settled_at >= prev_start,
        TrackedBet.settled_at < prev_end
    ).all()

    if not prev_bets:
        return None

    prev_summary = _calculate_summary(prev_bets, currency)

    return {
        "previous_period": {
            "start": prev_start.isoformat(),
            "end": prev_end.isoformat()
        },
        "profit_change": round(current_summary["total_profit"] - prev_summary["total_profit"], 2),
        "profit_change_pct": _calc_pct_change(prev_summary["total_profit"], current_summary["total_profit"]),
        "roi_change": round(current_summary["roi"] - prev_summary["roi"], 2),
        "bet_count_change": current_summary["total_bets"] - prev_summary["total_bets"],
        "win_rate_change": round(current_summary["win_rate"] - prev_summary["win_rate"], 2)
    }


def _calc_pct_change(old: float, new: float) -> float:
    """Calculate percentage change."""
    if old == 0:
        return 100.0 if new > 0 else (-100.0 if new < 0 else 0.0)
    return round((new - old) / abs(old) * 100, 2)


def get_roi_by_market_type(
    db: Session,
    user_id: int,
    timeframe: TimeFrame = TimeFrame.ALL_TIME,
    currency: str = "USD"
) -> Dict[str, Dict[str, Any]]:
    """
    Get ROI breakdown by market/bet type.

    Returns stats for each bet type (spread, moneyline, totals, props, etc.)
    """
    start_date, end_date = get_timeframe_dates(timeframe)

    query = db.query(TrackedBet).filter(
        TrackedBet.user_id == user_id,
        TrackedBet.status == "settled"
    )

    if start_date:
        query = query.filter(TrackedBet.settled_at >= start_date)
    if end_date:
        query = query.filter(TrackedBet.settled_at <= end_date)

    bets = query.all()

    by_type = {}

    for bet in bets:
        bet_type = bet.bet_type or "unknown"

        if bet_type not in by_type:
            by_type[bet_type] = {
                "total_bets": 0,
                "wins": 0,
                "losses": 0,
                "pushes": 0,
                "staked": 0.0,
                "profit": 0.0
            }

        by_type[bet_type]["total_bets"] += 1

        if bet.result == "won":
            by_type[bet_type]["wins"] += 1
        elif bet.result == "lost":
            by_type[bet_type]["losses"] += 1
        else:
            by_type[bet_type]["pushes"] += 1

        by_type[bet_type]["staked"] += convert_currency(bet.stake, bet.currency, currency)
        by_type[bet_type]["profit"] += convert_currency(bet.profit_loss or 0, bet.currency, currency)

    # Calculate derived metrics
    for bet_type, data in by_type.items():
        total = data["total_bets"]
        data["win_rate"] = round(data["wins"] / total * 100, 2) if total > 0 else 0.0
        data["roi"] = round(data["profit"] / data["staked"] * 100, 2) if data["staked"] > 0 else 0.0
        data["average_stake"] = round(data["staked"] / total, 2) if total > 0 else 0.0
        data["staked"] = round(data["staked"], 2)
        data["profit"] = round(data["profit"], 2)

    return by_type


def get_roi_by_sport(
    db: Session,
    user_id: int,
    timeframe: TimeFrame = TimeFrame.ALL_TIME,
    currency: str = "USD"
) -> Dict[str, Dict[str, Any]]:
    """
    Get ROI breakdown by sport.
    """
    start_date, end_date = get_timeframe_dates(timeframe)

    query = db.query(TrackedBet).filter(
        TrackedBet.user_id == user_id,
        TrackedBet.status == "settled"
    )

    if start_date:
        query = query.filter(TrackedBet.settled_at >= start_date)
    if end_date:
        query = query.filter(TrackedBet.settled_at <= end_date)

    bets = query.all()

    by_sport = {}

    for bet in bets:
        sport = bet.sport or "unknown"

        if sport not in by_sport:
            by_sport[sport] = {
                "total_bets": 0,
                "wins": 0,
                "losses": 0,
                "pushes": 0,
                "staked": 0.0,
                "profit": 0.0
            }

        by_sport[sport]["total_bets"] += 1

        if bet.result == "won":
            by_sport[sport]["wins"] += 1
        elif bet.result == "lost":
            by_sport[sport]["losses"] += 1
        else:
            by_sport[sport]["pushes"] += 1

        by_sport[sport]["staked"] += convert_currency(bet.stake, bet.currency, currency)
        by_sport[sport]["profit"] += convert_currency(bet.profit_loss or 0, bet.currency, currency)

    # Calculate derived metrics
    for sport, data in by_sport.items():
        total = data["total_bets"]
        data["win_rate"] = round(data["wins"] / total * 100, 2) if total > 0 else 0.0
        data["roi"] = round(data["profit"] / data["staked"] * 100, 2) if data["staked"] > 0 else 0.0
        data["average_stake"] = round(data["staked"] / total, 2) if total > 0 else 0.0
        data["staked"] = round(data["staked"], 2)
        data["profit"] = round(data["profit"], 2)

    return by_sport


def get_roi_by_sportsbook(
    db: Session,
    user_id: int,
    timeframe: TimeFrame = TimeFrame.ALL_TIME,
    currency: str = "USD"
) -> Dict[str, Dict[str, Any]]:
    """
    Get ROI breakdown by sportsbook.
    """
    start_date, end_date = get_timeframe_dates(timeframe)

    query = db.query(TrackedBet).filter(
        TrackedBet.user_id == user_id,
        TrackedBet.status == "settled"
    )

    if start_date:
        query = query.filter(TrackedBet.settled_at >= start_date)
    if end_date:
        query = query.filter(TrackedBet.settled_at <= end_date)

    bets = query.all()

    by_book = {}

    for bet in bets:
        book = bet.sportsbook or "unspecified"

        if book not in by_book:
            by_book[book] = {
                "total_bets": 0,
                "wins": 0,
                "losses": 0,
                "staked": 0.0,
                "profit": 0.0
            }

        by_book[book]["total_bets"] += 1

        if bet.result == "won":
            by_book[book]["wins"] += 1
        elif bet.result == "lost":
            by_book[book]["losses"] += 1

        by_book[book]["staked"] += convert_currency(bet.stake, bet.currency, currency)
        by_book[book]["profit"] += convert_currency(bet.profit_loss or 0, bet.currency, currency)

    # Calculate derived metrics
    for book, data in by_book.items():
        total = data["total_bets"]
        data["win_rate"] = round(data["wins"] / total * 100, 2) if total > 0 else 0.0
        data["roi"] = round(data["profit"] / data["staked"] * 100, 2) if data["staked"] > 0 else 0.0
        data["staked"] = round(data["staked"], 2)
        data["profit"] = round(data["profit"], 2)

    return by_book


def get_streak_analysis(
    db: Session,
    user_id: int,
    currency: str = "USD"
) -> Dict[str, Any]:
    """
    Comprehensive streak analysis.

    Tracks winning streaks, losing streaks, and identifies hot/cold periods.
    """
    bets = db.query(TrackedBet).filter(
        TrackedBet.user_id == user_id,
        TrackedBet.status == "settled"
    ).order_by(TrackedBet.settled_at).all()

    if not bets:
        return {
            "current_streak": {"type": None, "length": 0, "profit": 0.0},
            "best_win_streak": None,
            "worst_lose_streak": None,
            "all_win_streaks": [],
            "all_lose_streaks": [],
            "hot_periods": [],
            "cold_periods": []
        }

    # Find all streaks
    win_streaks = []
    lose_streaks = []

    current_type = None
    current_length = 0
    current_profit = 0.0
    current_start = None
    current_bets = []

    for bet in bets:
        profit = convert_currency(bet.profit_loss or 0, bet.currency, currency)

        if bet.result == "won":
            bet_type = "win"
        elif bet.result == "lost":
            bet_type = "lose"
        else:
            continue  # Skip pushes for streak calculation

        if bet_type == current_type:
            current_length += 1
            current_profit += profit
            current_bets.append(bet.id)
        else:
            # Save previous streak if it exists
            if current_type and current_length >= 2:
                streak = StreakInfo(
                    streak_type=current_type,
                    length=current_length,
                    start_date=current_start,
                    end_date=bet.settled_at,
                    profit_loss=current_profit,
                    bets=current_bets
                )
                if current_type == "win":
                    win_streaks.append(streak)
                else:
                    lose_streaks.append(streak)

            # Start new streak
            current_type = bet_type
            current_length = 1
            current_profit = profit
            current_start = bet.settled_at
            current_bets = [bet.id]

    # Don't forget the last streak
    if current_type and current_length >= 2:
        streak = StreakInfo(
            streak_type=current_type,
            length=current_length,
            start_date=current_start,
            end_date=bets[-1].settled_at,
            profit_loss=current_profit,
            bets=current_bets
        )
        if current_type == "win":
            win_streaks.append(streak)
        else:
            lose_streaks.append(streak)

    # Find best and worst streaks
    best_win = max(win_streaks, key=lambda s: s.length) if win_streaks else None
    worst_lose = max(lose_streaks, key=lambda s: s.length) if lose_streaks else None

    # Identify hot/cold periods (rolling 10-bet windows with exceptional performance)
    hot_periods = []
    cold_periods = []
    window_size = 10

    if len(bets) >= window_size:
        for i in range(len(bets) - window_size + 1):
            window = bets[i:i + window_size]
            wins = sum(1 for b in window if b.result == "won")
            losses = sum(1 for b in window if b.result == "lost")
            profit = sum(convert_currency(b.profit_loss or 0, b.currency, currency) for b in window)

            win_rate = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0

            if win_rate >= 70:  # Hot period
                hot_periods.append({
                    "start_date": window[0].settled_at.isoformat(),
                    "end_date": window[-1].settled_at.isoformat(),
                    "bets": window_size,
                    "wins": wins,
                    "win_rate": round(win_rate, 2),
                    "profit": round(profit, 2)
                })
            elif win_rate <= 30:  # Cold period
                cold_periods.append({
                    "start_date": window[0].settled_at.isoformat(),
                    "end_date": window[-1].settled_at.isoformat(),
                    "bets": window_size,
                    "wins": wins,
                    "win_rate": round(win_rate, 2),
                    "profit": round(profit, 2)
                })

    # Deduplicate overlapping periods
    hot_periods = _dedupe_periods(hot_periods)
    cold_periods = _dedupe_periods(cold_periods)

    return {
        "current_streak": {
            "type": current_type,
            "length": current_length,
            "profit": round(current_profit, 2)
        },
        "best_win_streak": _streak_to_dict(best_win) if best_win else None,
        "worst_lose_streak": _streak_to_dict(worst_lose) if worst_lose else None,
        "all_win_streaks": [_streak_to_dict(s) for s in sorted(win_streaks, key=lambda x: -x.length)[:5]],
        "all_lose_streaks": [_streak_to_dict(s) for s in sorted(lose_streaks, key=lambda x: -x.length)[:5]],
        "hot_periods": hot_periods[:5],
        "cold_periods": cold_periods[:5]
    }


def _streak_to_dict(streak: StreakInfo) -> Dict[str, Any]:
    """Convert StreakInfo to dict."""
    return {
        "type": streak.streak_type,
        "length": streak.length,
        "start_date": streak.start_date.isoformat(),
        "end_date": streak.end_date.isoformat(),
        "profit": round(streak.profit_loss, 2)
    }


def _dedupe_periods(periods: List[Dict]) -> List[Dict]:
    """Remove overlapping periods, keeping the best ones."""
    if not periods:
        return []

    # Sort by profit (descending for hot, ascending for cold)
    sorted_periods = sorted(periods, key=lambda x: -abs(x["profit"]))
    result = []

    for period in sorted_periods:
        # Check if this period overlaps with any already selected
        overlaps = False
        for selected in result:
            if period["start_date"] <= selected["end_date"] and period["end_date"] >= selected["start_date"]:
                overlaps = True
                break

        if not overlaps:
            result.append(period)

    return result


def get_unit_tracking(
    db: Session,
    user_id: int,
    base_unit: float = 100.0,
    timeframe: TimeFrame = TimeFrame.ALL_TIME,
    currency: str = "USD"
) -> Dict[str, Any]:
    """
    Track betting in units rather than dollars.

    Useful for standardizing bet tracking across different bankroll sizes.
    """
    start_date, end_date = get_timeframe_dates(timeframe)

    query = db.query(TrackedBet).filter(
        TrackedBet.user_id == user_id,
        TrackedBet.status == "settled"
    )

    if start_date:
        query = query.filter(TrackedBet.settled_at >= start_date)
    if end_date:
        query = query.filter(TrackedBet.settled_at <= end_date)

    bets = query.order_by(TrackedBet.settled_at).all()

    if not bets:
        return {
            "base_unit": base_unit,
            "currency": currency,
            "total_units_wagered": 0.0,
            "total_units_won": 0.0,
            "total_units_lost": 0.0,
            "net_units": 0.0,
            "roi_units": 0.0,
            "average_bet_size_units": 0.0,
            "unit_history": []
        }

    total_wagered = 0.0
    total_won = 0.0
    total_lost = 0.0
    unit_history = []
    cumulative_units = 0.0

    for bet in bets:
        stake = convert_currency(bet.stake, bet.currency, currency)
        profit = convert_currency(bet.profit_loss or 0, bet.currency, currency)

        units_wagered = stake / base_unit
        units_result = profit / base_unit

        total_wagered += units_wagered

        if profit > 0:
            total_won += units_result
        else:
            total_lost += abs(units_result)

        cumulative_units += units_result

        unit_history.append({
            "date": bet.settled_at.strftime("%Y-%m-%d"),
            "bet_id": bet.id,
            "units_wagered": round(units_wagered, 2),
            "units_result": round(units_result, 2),
            "cumulative_units": round(cumulative_units, 2)
        })

    net_units = total_won - total_lost

    return {
        "base_unit": base_unit,
        "currency": currency,
        "total_units_wagered": round(total_wagered, 2),
        "total_units_won": round(total_won, 2),
        "total_units_lost": round(total_lost, 2),
        "net_units": round(net_units, 2),
        "roi_units": round(net_units / total_wagered * 100, 2) if total_wagered > 0 else 0.0,
        "average_bet_size_units": round(total_wagered / len(bets), 2) if bets else 0.0,
        "unit_history": unit_history[-50:]  # Last 50 bets
    }


def export_bets_csv(
    db: Session,
    user_id: int,
    timeframe: TimeFrame = TimeFrame.ALL_TIME,
    include_pending: bool = False
) -> str:
    """
    Export bets to CSV format.

    Returns CSV string that can be downloaded.
    """
    start_date, end_date = get_timeframe_dates(timeframe)

    query = db.query(TrackedBet).filter(TrackedBet.user_id == user_id)

    if not include_pending:
        query = query.filter(TrackedBet.status == "settled")

    if start_date:
        query = query.filter(TrackedBet.settled_at >= start_date)
    if end_date:
        query = query.filter(TrackedBet.settled_at <= end_date)

    bets = query.order_by(TrackedBet.placed_at).all()

    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow([
        "ID",
        "Date Placed",
        "Date Settled",
        "Sport",
        "Bet Type",
        "Selection",
        "Odds",
        "Stake",
        "Currency",
        "Potential Profit",
        "Status",
        "Result",
        "Profit/Loss",
        "Sportsbook",
        "Notes"
    ])

    # Data rows
    for bet in bets:
        writer.writerow([
            bet.id,
            bet.placed_at.strftime("%Y-%m-%d %H:%M:%S") if bet.placed_at else "",
            bet.settled_at.strftime("%Y-%m-%d %H:%M:%S") if bet.settled_at else "",
            bet.sport,
            bet.bet_type,
            bet.selection,
            bet.odds,
            bet.stake,
            bet.currency,
            bet.potential_profit,
            bet.status,
            bet.result or "",
            bet.profit_loss if bet.profit_loss is not None else "",
            bet.sportsbook or "",
            bet.notes or ""
        ])

    return output.getvalue()


def get_performance_by_odds_range(
    db: Session,
    user_id: int,
    timeframe: TimeFrame = TimeFrame.ALL_TIME,
    currency: str = "USD"
) -> List[Dict[str, Any]]:
    """
    Analyze performance by odds range.

    Helps identify which odds ranges are most profitable.
    """
    start_date, end_date = get_timeframe_dates(timeframe)

    query = db.query(TrackedBet).filter(
        TrackedBet.user_id == user_id,
        TrackedBet.status == "settled"
    )

    if start_date:
        query = query.filter(TrackedBet.settled_at >= start_date)
    if end_date:
        query = query.filter(TrackedBet.settled_at <= end_date)

    bets = query.all()

    # Define odds ranges
    ranges = [
        ("Heavy Favorites", -500, -200),
        ("Moderate Favorites", -199, -120),
        ("Small Favorites", -119, -100),
        ("Pick 'em", -99, 100),
        ("Small Underdogs", 101, 150),
        ("Moderate Underdogs", 151, 250),
        ("Large Underdogs", 251, 500),
        ("Longshots", 501, 10000)
    ]

    results = []

    for name, min_odds, max_odds in ranges:
        range_bets = [b for b in bets if min_odds <= b.odds <= max_odds]

        if not range_bets:
            continue

        total = len(range_bets)
        wins = sum(1 for b in range_bets if b.result == "won")
        staked = sum(convert_currency(b.stake, b.currency, currency) for b in range_bets)
        profit = sum(convert_currency(b.profit_loss or 0, b.currency, currency) for b in range_bets)

        results.append({
            "odds_range": name,
            "min_odds": min_odds,
            "max_odds": max_odds,
            "total_bets": total,
            "wins": wins,
            "win_rate": round(wins / total * 100, 2) if total > 0 else 0.0,
            "staked": round(staked, 2),
            "profit": round(profit, 2),
            "roi": round(profit / staked * 100, 2) if staked > 0 else 0.0
        })

    return results


def get_dashboard_summary(
    db: Session,
    user_id: int,
    currency: str = "USD"
) -> Dict[str, Any]:
    """
    Get complete P&L dashboard data in a single call.

    Combines all analytics into one comprehensive response.
    """
    return {
        "all_time": get_pnl_summary(db, user_id, TimeFrame.ALL_TIME, currency),
        "this_month": get_pnl_summary(db, user_id, TimeFrame.THIS_MONTH, currency),
        "last_30_days": get_pnl_summary(db, user_id, TimeFrame.LAST_30_DAYS, currency),
        "by_sport": get_roi_by_sport(db, user_id, TimeFrame.ALL_TIME, currency),
        "by_market_type": get_roi_by_market_type(db, user_id, TimeFrame.ALL_TIME, currency),
        "by_sportsbook": get_roi_by_sportsbook(db, user_id, TimeFrame.ALL_TIME, currency),
        "by_odds_range": get_performance_by_odds_range(db, user_id, TimeFrame.ALL_TIME, currency),
        "streaks": get_streak_analysis(db, user_id, currency),
        "units": get_unit_tracking(db, user_id, 100.0, TimeFrame.ALL_TIME, currency)
    }
