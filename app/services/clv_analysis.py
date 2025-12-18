"""
Closing Line Value (CLV) Analysis Service.
CLV measures how well you beat the closing line - a key indicator of betting skill.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db import TrackedBet, OddsSnapshot, User


def american_to_implied_prob(american_odds: int) -> float:
    """Convert American odds to implied probability."""
    if american_odds > 0:
        return 100 / (american_odds + 100)
    else:
        return abs(american_odds) / (abs(american_odds) + 100)


def implied_prob_to_american(prob: float) -> int:
    """Convert implied probability to American odds."""
    if prob >= 0.5:
        return int(-100 * prob / (1 - prob))
    else:
        return int(100 * (1 - prob) / prob)


def calculate_clv(bet_odds: int, closing_odds: int) -> float:
    """
    Calculate Closing Line Value.
    Positive CLV means you got better odds than the closing line.
    """
    bet_prob = american_to_implied_prob(bet_odds)
    closing_prob = american_to_implied_prob(closing_odds)

    # CLV = (closing_prob - bet_prob) / bet_prob * 100
    if bet_prob == 0:
        return 0

    return ((closing_prob - bet_prob) / bet_prob) * 100


def get_user_clv_stats(db: Session, user_id: int, days: int = 90) -> Dict[str, Any]:
    """Get CLV statistics for a user."""
    since = datetime.utcnow() - timedelta(days=days)

    # Get settled bets with CLV data
    bets = db.query(TrackedBet).filter(
        TrackedBet.user_id == user_id,
        TrackedBet.status == 'settled',
        TrackedBet.placed_at >= since,
        TrackedBet.clv_percentage.isnot(None)
    ).all()

    if not bets:
        return {
            'total_bets_with_clv': 0,
            'average_clv': 0,
            'positive_clv_rate': 0,
            'total_clv_edge': 0,
            'clv_by_sport': {},
            'clv_trend': []
        }

    total_clv = sum(b.clv_percentage or 0 for b in bets)
    positive_clv_count = sum(1 for b in bets if (b.clv_percentage or 0) > 0)

    # CLV by sport
    clv_by_sport = {}
    for bet in bets:
        if bet.sport not in clv_by_sport:
            clv_by_sport[bet.sport] = {'count': 0, 'total_clv': 0}
        clv_by_sport[bet.sport]['count'] += 1
        clv_by_sport[bet.sport]['total_clv'] += bet.clv_percentage or 0

    for sport in clv_by_sport:
        clv_by_sport[sport]['average_clv'] = (
            clv_by_sport[sport]['total_clv'] / clv_by_sport[sport]['count']
        )

    # CLV trend (weekly averages)
    clv_trend = []
    current_week_start = since
    while current_week_start < datetime.utcnow():
        week_end = current_week_start + timedelta(days=7)
        week_bets = [
            b for b in bets
            if current_week_start <= b.placed_at < week_end
        ]
        if week_bets:
            week_avg = sum(b.clv_percentage or 0 for b in week_bets) / len(week_bets)
            clv_trend.append({
                'week_start': current_week_start.isoformat(),
                'average_clv': round(week_avg, 2),
                'bet_count': len(week_bets)
            })
        current_week_start = week_end

    return {
        'total_bets_with_clv': len(bets),
        'average_clv': round(total_clv / len(bets), 2) if bets else 0,
        'positive_clv_rate': round(positive_clv_count / len(bets) * 100, 1) if bets else 0,
        'total_clv_edge': round(total_clv, 2),
        'clv_by_sport': clv_by_sport,
        'clv_trend': clv_trend
    }


def get_clv_leaderboard(
    db: Session,
    min_bets: int = 20,
    days: int = 30,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Get CLV leaderboard - users ranked by average CLV."""
    since = datetime.utcnow() - timedelta(days=days)

    # Subquery for user CLV stats
    results = db.query(
        TrackedBet.user_id,
        func.count(TrackedBet.id).label('bet_count'),
        func.avg(TrackedBet.clv_percentage).label('avg_clv'),
        func.sum(
            func.case(
                (TrackedBet.clv_percentage > 0, 1),
                else_=0
            )
        ).label('positive_clv_count')
    ).filter(
        TrackedBet.status == 'settled',
        TrackedBet.placed_at >= since,
        TrackedBet.clv_percentage.isnot(None)
    ).group_by(
        TrackedBet.user_id
    ).having(
        func.count(TrackedBet.id) >= min_bets
    ).order_by(
        func.avg(TrackedBet.clv_percentage).desc()
    ).limit(limit).all()

    leaderboard = []
    for i, row in enumerate(results, 1):
        user = db.query(User).filter(User.id == row.user_id).first()
        if user:
            leaderboard.append({
                'rank': i,
                'user_id': row.user_id,
                'display_name': user.display_name or user.username,
                'bet_count': row.bet_count,
                'average_clv': round(float(row.avg_clv), 2),
                'positive_clv_rate': round(row.positive_clv_count / row.bet_count * 100, 1)
            })

    return leaderboard


def analyze_bet_timing(
    db: Session,
    user_id: int,
    days: int = 90
) -> Dict[str, Any]:
    """Analyze bet timing to identify optimal betting patterns."""
    since = datetime.utcnow() - timedelta(days=days)

    bets = db.query(TrackedBet).filter(
        TrackedBet.user_id == user_id,
        TrackedBet.status == 'settled',
        TrackedBet.placed_at >= since,
        TrackedBet.clv_percentage.isnot(None),
        TrackedBet.game_date.isnot(None)
    ).all()

    if not bets:
        return {
            'optimal_timing': 'N/A',
            'timing_analysis': [],
            'recommendation': 'Need more data to analyze timing patterns'
        }

    # Group bets by hours before game
    timing_buckets = {
        'early': {'min_hours': 48, 'max_hours': None, 'bets': []},
        'day_before': {'min_hours': 24, 'max_hours': 48, 'bets': []},
        'same_day': {'min_hours': 4, 'max_hours': 24, 'bets': []},
        'close_to_start': {'min_hours': 0, 'max_hours': 4, 'bets': []}
    }

    for bet in bets:
        if bet.game_date and bet.placed_at:
            hours_before = (bet.game_date - bet.placed_at).total_seconds() / 3600
            for bucket_name, bucket in timing_buckets.items():
                min_h = bucket['min_hours']
                max_h = bucket['max_hours']
                if max_h is None:
                    if hours_before >= min_h:
                        bucket['bets'].append(bet)
                        break
                elif min_h <= hours_before < max_h:
                    bucket['bets'].append(bet)
                    break

    # Calculate stats for each bucket
    timing_analysis = []
    best_bucket = None
    best_clv = float('-inf')

    for bucket_name, bucket in timing_buckets.items():
        if bucket['bets']:
            avg_clv = sum(b.clv_percentage or 0 for b in bucket['bets']) / len(bucket['bets'])
            win_rate = sum(1 for b in bucket['bets'] if b.result == 'won') / len(bucket['bets']) * 100

            timing_analysis.append({
                'timing': bucket_name,
                'bet_count': len(bucket['bets']),
                'average_clv': round(avg_clv, 2),
                'win_rate': round(win_rate, 1)
            })

            if avg_clv > best_clv:
                best_clv = avg_clv
                best_bucket = bucket_name

    timing_labels = {
        'early': '48+ hours before',
        'day_before': '24-48 hours before',
        'same_day': '4-24 hours before',
        'close_to_start': '0-4 hours before'
    }

    recommendation = f"Your best CLV comes from betting {timing_labels.get(best_bucket, 'various times')}"

    return {
        'optimal_timing': best_bucket,
        'timing_analysis': timing_analysis,
        'recommendation': recommendation
    }


def get_sharp_vs_public_analysis(
    db: Session,
    user_id: int,
    days: int = 90
) -> Dict[str, Any]:
    """
    Analyze whether user tends to bet with sharp money or public money.
    Sharp bettors typically have positive CLV.
    """
    since = datetime.utcnow() - timedelta(days=days)

    bets = db.query(TrackedBet).filter(
        TrackedBet.user_id == user_id,
        TrackedBet.status == 'settled',
        TrackedBet.placed_at >= since,
        TrackedBet.clv_percentage.isnot(None)
    ).all()

    if len(bets) < 10:
        return {
            'classification': 'insufficient_data',
            'sharp_tendency': 0,
            'analysis': 'Need at least 10 settled bets with CLV data'
        }

    positive_clv = sum(1 for b in bets if (b.clv_percentage or 0) > 0)
    avg_clv = sum(b.clv_percentage or 0 for b in bets) / len(bets)

    positive_rate = positive_clv / len(bets)

    # Classification
    if avg_clv > 2 and positive_rate > 0.55:
        classification = 'sharp'
        analysis = "Your betting pattern aligns with sharp/professional bettors. You consistently beat the closing line."
    elif avg_clv > 0 and positive_rate > 0.5:
        classification = 'semi_sharp'
        analysis = "You show some sharp tendencies. Focus on sports/bet types where your CLV is highest."
    elif avg_clv > -2:
        classification = 'neutral'
        analysis = "Your CLV is neutral. Consider timing your bets earlier or focusing on less efficient markets."
    else:
        classification = 'recreational'
        analysis = "Your CLV suggests betting against line movement. Consider betting earlier when lines are less efficient."

    return {
        'classification': classification,
        'sharp_tendency': round(positive_rate * 100, 1),
        'average_clv': round(avg_clv, 2),
        'total_bets_analyzed': len(bets),
        'positive_clv_bets': positive_clv,
        'analysis': analysis
    }
