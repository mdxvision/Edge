from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.db import TrackedBet, User, LeaderboardEntry, BetRecommendation
from app.services.currency import convert_currency


def place_bet(
    db: Session,
    user_id: int,
    sport: str,
    bet_type: str,
    selection: str,
    odds: int,
    stake: float,
    currency: str = "USD",
    sportsbook: Optional[str] = None,
    notes: Optional[str] = None,
    game_id: Optional[int] = None,
    game_date: Optional[datetime] = None,
    recommendation_id: Optional[int] = None
) -> TrackedBet:
    if odds > 0:
        potential_profit = stake * (odds / 100)
    else:
        potential_profit = stake * (100 / abs(odds))
    
    bet = TrackedBet(
        user_id=user_id,
        recommendation_id=recommendation_id,
        sport=sport,
        bet_type=bet_type,
        selection=selection,
        odds=odds,
        stake=stake,
        currency=currency,
        potential_profit=potential_profit,
        sportsbook=sportsbook,
        notes=notes,
        game_id=game_id,
        game_date=game_date
    )
    
    db.add(bet)
    db.commit()
    db.refresh(bet)
    
    return bet


def settle_bet(
    db: Session,
    bet: TrackedBet,
    result: str,
    actual_profit_loss: Optional[float] = None
) -> TrackedBet:
    bet.status = "settled"
    bet.result = result
    bet.settled_at = datetime.utcnow()
    
    if actual_profit_loss is not None:
        bet.profit_loss = actual_profit_loss
    elif result == "won":
        bet.profit_loss = bet.potential_profit
    elif result == "lost":
        bet.profit_loss = -bet.stake
    elif result == "push":
        bet.profit_loss = 0.0
    elif result == "void":
        bet.profit_loss = 0.0
    else:
        bet.profit_loss = 0.0
    
    db.commit()
    db.refresh(bet)
    
    update_leaderboard_for_user(db, bet.user_id)
    
    return bet


def get_user_bets(
    db: Session,
    user_id: int,
    status: Optional[str] = None,
    sport: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[TrackedBet]:
    query = db.query(TrackedBet).filter(TrackedBet.user_id == user_id)
    
    if status:
        query = query.filter(TrackedBet.status == status)
    
    if sport:
        query = query.filter(TrackedBet.sport == sport)
    
    return query.order_by(desc(TrackedBet.placed_at)).offset(offset).limit(limit).all()


def get_bet_by_id(db: Session, bet_id: int, user_id: int) -> Optional[TrackedBet]:
    return db.query(TrackedBet).filter(
        TrackedBet.id == bet_id,
        TrackedBet.user_id == user_id
    ).first()


def delete_bet(db: Session, bet: TrackedBet) -> bool:
    if bet.status == "settled":
        return False
    
    db.delete(bet)
    db.commit()
    return True


def get_user_stats(
    db: Session,
    user_id: int,
    currency: str = "USD"
) -> Dict[str, Any]:
    bets = db.query(TrackedBet).filter(
        TrackedBet.user_id == user_id,
        TrackedBet.status == "settled"
    ).all()
    
    if not bets:
        return {
            "total_bets": 0,
            "winning_bets": 0,
            "losing_bets": 0,
            "push_bets": 0,
            "win_rate": 0.0,
            "total_staked": 0.0,
            "total_profit": 0.0,
            "roi": 0.0,
            "average_odds": 0,
            "best_win": 0.0,
            "worst_loss": 0.0,
            "current_streak": 0,
            "best_streak": 0,
            "currency": currency
        }
    
    total_bets = len(bets)
    winning_bets = sum(1 for b in bets if b.result == "won")
    losing_bets = sum(1 for b in bets if b.result == "lost")
    push_bets = sum(1 for b in bets if b.result in ["push", "void"])
    
    total_staked = sum(convert_currency(b.stake, b.currency, currency) for b in bets)
    total_profit = sum(convert_currency(b.profit_loss or 0, b.currency, currency) for b in bets)
    
    win_rate = (winning_bets / total_bets * 100) if total_bets > 0 else 0.0
    roi = (total_profit / total_staked * 100) if total_staked > 0 else 0.0
    
    avg_odds = sum(b.odds for b in bets) / total_bets if total_bets > 0 else 0
    
    profits = [convert_currency(b.profit_loss or 0, b.currency, currency) for b in bets]
    best_win = max(profits) if profits else 0.0
    worst_loss = min(profits) if profits else 0.0
    
    sorted_bets = sorted(bets, key=lambda x: x.settled_at or x.placed_at)
    current_streak = 0
    best_streak = 0
    temp_streak = 0
    
    for bet in sorted_bets:
        if bet.result == "won":
            temp_streak += 1
            best_streak = max(best_streak, temp_streak)
        else:
            temp_streak = 0
    
    for bet in reversed(sorted_bets):
        if bet.result == "won":
            current_streak += 1
        else:
            break
    
    return {
        "total_bets": total_bets,
        "winning_bets": winning_bets,
        "losing_bets": losing_bets,
        "push_bets": push_bets,
        "win_rate": round(win_rate, 2),
        "total_staked": round(total_staked, 2),
        "total_profit": round(total_profit, 2),
        "roi": round(roi, 2),
        "average_odds": int(avg_odds),
        "best_win": round(best_win, 2),
        "worst_loss": round(worst_loss, 2),
        "current_streak": current_streak,
        "best_streak": best_streak,
        "currency": currency
    }


def get_profit_by_period(
    db: Session,
    user_id: int,
    days: int = 30,
    currency: str = "USD"
) -> List[Dict[str, Any]]:
    since = datetime.utcnow() - timedelta(days=days)
    
    bets = db.query(TrackedBet).filter(
        TrackedBet.user_id == user_id,
        TrackedBet.status == "settled",
        TrackedBet.settled_at >= since
    ).order_by(TrackedBet.settled_at).all()
    
    daily_profits = {}
    cumulative = 0.0
    
    for bet in bets:
        date_key = bet.settled_at.strftime("%Y-%m-%d")
        profit = convert_currency(bet.profit_loss or 0, bet.currency, currency)
        
        if date_key not in daily_profits:
            daily_profits[date_key] = {"date": date_key, "daily_profit": 0.0, "cumulative": 0.0}
        
        daily_profits[date_key]["daily_profit"] += profit
        cumulative += profit
        daily_profits[date_key]["cumulative"] = cumulative
    
    return list(daily_profits.values())


def get_profit_by_sport(
    db: Session,
    user_id: int,
    currency: str = "USD"
) -> Dict[str, Dict[str, Any]]:
    bets = db.query(TrackedBet).filter(
        TrackedBet.user_id == user_id,
        TrackedBet.status == "settled"
    ).all()
    
    by_sport = {}
    
    for bet in bets:
        if bet.sport not in by_sport:
            by_sport[bet.sport] = {
                "total_bets": 0,
                "winning_bets": 0,
                "profit": 0.0,
                "staked": 0.0
            }
        
        by_sport[bet.sport]["total_bets"] += 1
        if bet.result == "won":
            by_sport[bet.sport]["winning_bets"] += 1
        
        by_sport[bet.sport]["profit"] += convert_currency(bet.profit_loss or 0, bet.currency, currency)
        by_sport[bet.sport]["staked"] += convert_currency(bet.stake, bet.currency, currency)
    
    for sport, data in by_sport.items():
        data["win_rate"] = round(data["winning_bets"] / data["total_bets"] * 100, 2) if data["total_bets"] > 0 else 0
        data["roi"] = round(data["profit"] / data["staked"] * 100, 2) if data["staked"] > 0 else 0
        data["profit"] = round(data["profit"], 2)
        data["staked"] = round(data["staked"], 2)
    
    return by_sport


def update_leaderboard_for_user(db: Session, user_id: int) -> None:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return
    
    stats = get_user_stats(db, user_id)
    
    entry = db.query(LeaderboardEntry).filter(LeaderboardEntry.user_id == user_id).first()
    
    if not entry:
        entry = LeaderboardEntry(
            user_id=user_id,
            display_name=user.display_name or user.username
        )
        db.add(entry)
    
    entry.total_bets = stats["total_bets"]
    entry.winning_bets = stats["winning_bets"]
    entry.total_profit = stats["total_profit"]
    entry.roi_percentage = stats["roi"]
    entry.current_streak = stats["current_streak"]
    entry.best_streak = max(entry.best_streak, stats["best_streak"])
    
    week_ago = datetime.utcnow() - timedelta(days=7)
    month_ago = datetime.utcnow() - timedelta(days=30)
    
    weekly_bets = db.query(TrackedBet).filter(
        TrackedBet.user_id == user_id,
        TrackedBet.status == "settled",
        TrackedBet.settled_at >= week_ago
    ).all()
    entry.weekly_profit = sum(b.profit_loss or 0 for b in weekly_bets)
    
    monthly_bets = db.query(TrackedBet).filter(
        TrackedBet.user_id == user_id,
        TrackedBet.status == "settled",
        TrackedBet.settled_at >= month_ago
    ).all()
    entry.monthly_profit = sum(b.profit_loss or 0 for b in monthly_bets)
    
    db.commit()


def get_leaderboard(
    db: Session,
    sort_by: str = "total_profit",
    limit: int = 50
) -> List[LeaderboardEntry]:
    if sort_by == "roi":
        order = desc(LeaderboardEntry.roi_percentage)
    elif sort_by == "weekly":
        order = desc(LeaderboardEntry.weekly_profit)
    elif sort_by == "monthly":
        order = desc(LeaderboardEntry.monthly_profit)
    elif sort_by == "streak":
        order = desc(LeaderboardEntry.current_streak)
    else:
        order = desc(LeaderboardEntry.total_profit)
    
    entries = db.query(LeaderboardEntry).filter(
        LeaderboardEntry.is_public == True,
        LeaderboardEntry.total_bets >= 10
    ).order_by(order).limit(limit).all()
    
    for i, entry in enumerate(entries, 1):
        entry.previous_rank = entry.rank
        entry.rank = i
    
    db.commit()
    
    return entries
