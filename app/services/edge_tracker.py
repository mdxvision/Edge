"""
Edge Validation Tracker - Proves EdgeBet's predictive edge

Features:
- Log every pick with all 8 factors scored
- Track confidence level and recommended bet size
- Auto-settle when games complete
- Calculate actual vs expected win rate
- Analyze which factors correlate with wins
- Statistical significance testing
"""

import json
import uuid
import math
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.db import TrackedPick, BankrollSnapshot

# Starting virtual bankroll (100 units)
STARTING_BANKROLL = 100.0

# Factor names for analysis
FACTOR_NAMES = [
    "coach_dna",
    "referee",
    "weather",
    "line_movement",
    "rest",
    "travel",
    "situational",
    "public_betting"
]


class EdgeTracker:
    """Core tracking functionality for edge validation"""

    def __init__(self, db: Session):
        self.db = db

    def log_pick(
        self,
        game_id: str,
        sport: str,
        home_team: str,
        away_team: str,
        game_time: datetime,
        pick_type: str,
        pick: str,
        odds: int,
        confidence: float,
        factors: Dict[str, Dict[str, Any]],
        pick_team: Optional[str] = None,
        line_value: Optional[float] = None,
        weather_data: Optional[Dict] = None,
        units_wagered: Optional[float] = None
    ) -> Dict:
        """
        Log a pick with full factor breakdown

        Args:
            game_id: Unique game identifier
            sport: Sport type (NFL, NBA, MLB, etc.)
            home_team: Home team name
            away_team: Away team name
            game_time: Game start time
            pick_type: spread, moneyline, or total
            pick: The actual pick ("Chiefs -3", "Over 45.5", "Lakers ML")
            odds: American odds (-110, +150, etc.)
            confidence: 0-100 confidence score
            factors: Dict of all 8 factors with scores and details
            pick_team: Team picked (for spread/ML)
            line_value: Line value (-3, 45.5, etc.)
            weather_data: Weather conditions if available

        Returns:
            Dict with pick details and ID
        """
        pick_id = f"pick_{uuid.uuid4().hex[:12]}"

        # Calculate recommended units based on confidence
        recommended_units = self._calculate_units(confidence, odds)

        # Get current bankroll
        current_bankroll = self._get_current_bankroll()

        # Use user-provided units_wagered if available, otherwise use recommended
        actual_units = units_wagered if units_wagered is not None else recommended_units

        tracked_pick = TrackedPick(
            id=pick_id,
            game_id=game_id,
            sport=sport.upper(),
            home_team=home_team,
            away_team=away_team,
            game_time=game_time,
            pick_type=pick_type.lower(),
            pick=pick,
            pick_team=pick_team,
            line_value=line_value,
            odds=odds,
            confidence=confidence,
            recommended_units=recommended_units,
            factors=json.dumps(factors) if factors else None,
            weather_data=json.dumps(weather_data) if weather_data else None,
            units_wagered=actual_units,
            status="pending"
        )

        self.db.add(tracked_pick)
        self.db.commit()

        return {
            "pick_id": pick_id,
            "game_id": game_id,
            "sport": sport,
            "pick": pick,
            "odds": odds,
            "confidence": confidence,
            "recommended_units": recommended_units,
            "current_bankroll": current_bankroll,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }

    def settle_pick(
        self,
        pick_id: str,
        result: str,
        actual_score: str,
        spread_result: Optional[float] = None,
        total_result: Optional[float] = None
    ) -> Dict:
        """
        Settle a pick when game finishes

        Args:
            pick_id: The pick ID to settle
            result: "won", "lost", or "push"
            actual_score: Final score string ("Chiefs 27, Raiders 20")
            spread_result: Actual spread result (negative = home won)
            total_result: Actual total points

        Returns:
            Dict with settlement details
        """
        pick = self.db.query(TrackedPick).filter(TrackedPick.id == pick_id).first()
        if not pick:
            return {"error": "Pick not found"}

        if pick.status != "pending":
            return {"error": "Pick already settled"}

        # Calculate units result
        units_result = self._calculate_result(result, pick.units_wagered, pick.odds)

        # Get current bankroll before this pick
        current_bankroll = self._get_current_bankroll()
        new_bankroll = current_bankroll + units_result

        # Update pick
        pick.status = result.lower()
        pick.result_score = actual_score
        pick.spread_result = spread_result
        pick.total_result = total_result
        pick.units_result = units_result
        pick.bankroll_after = new_bankroll
        pick.settled_at = datetime.utcnow()

        self.db.commit()

        # Create bankroll snapshot
        self._create_snapshot()

        return {
            "pick_id": pick_id,
            "result": result,
            "units_wagered": pick.units_wagered,
            "units_result": units_result,
            "previous_bankroll": current_bankroll,
            "new_bankroll": new_bankroll,
            "actual_score": actual_score
        }

    def get_factor_analysis(self) -> Dict:
        """
        Analyze which factors correlate with wins

        Returns:
            Dict with correlation data for each factor
        """
        picks = self.db.query(TrackedPick).filter(
            TrackedPick.status.in_(["won", "lost"])
        ).all()

        if len(picks) < 10:
            return {
                "error": "Need at least 10 settled picks for factor analysis",
                "current_picks": len(picks)
            }

        factor_stats = {}

        for factor_name in FACTOR_NAMES:
            high_picks = []
            low_picks = []

            for pick in picks:
                if not pick.factors:
                    continue

                try:
                    factors = json.loads(pick.factors)
                    factor_data = factors.get(factor_name, {})
                    score = factor_data.get("score", 50)

                    is_win = 1 if pick.status == "won" else 0

                    if score >= 70:
                        high_picks.append(is_win)
                    elif score <= 50:
                        low_picks.append(is_win)
                except:
                    continue

            # Calculate stats for this factor
            high_wins = sum(high_picks)
            high_total = len(high_picks)
            low_wins = sum(low_picks)
            low_total = len(low_picks)

            win_rate_high = (high_wins / high_total * 100) if high_total > 0 else 0
            win_rate_low = (low_wins / low_total * 100) if low_total > 0 else 0

            # Calculate correlation
            correlation = self._calculate_factor_correlation(picks, factor_name)

            # Determine predictive value
            if high_total >= 10 and low_total >= 10:
                diff = win_rate_high - win_rate_low
                if diff > 10 and correlation > 0.2:
                    predictive_value = "HIGH"
                elif diff > 5 and correlation > 0.1:
                    predictive_value = "MEDIUM"
                elif diff > 0:
                    predictive_value = "LOW"
                else:
                    predictive_value = "NONE"
            else:
                predictive_value = "INSUFFICIENT_DATA"

            factor_stats[factor_name] = {
                "total_picks": high_total + low_total,
                "wins_when_high": high_wins,
                "total_when_high": high_total,
                "win_rate_high": round(win_rate_high, 1),
                "wins_when_low": low_wins,
                "total_when_low": low_total,
                "win_rate_low": round(win_rate_low, 1),
                "correlation": round(correlation, 3),
                "predictive_value": predictive_value
            }

        return {
            "total_analyzed": len(picks),
            "factors": factor_stats
        }

    def get_edge_stats(self) -> Dict:
        """
        Calculate overall edge statistics

        Returns:
            Dict with comprehensive edge stats
        """
        picks = self.db.query(TrackedPick).filter(
            TrackedPick.status != "pending"
        ).all()

        total_picks = len(picks)
        wins = sum(1 for p in picks if p.status == "won")
        losses = sum(1 for p in picks if p.status == "lost")
        pushes = sum(1 for p in picks if p.status == "push")

        # Calculate win rate (excluding pushes)
        decided_picks = wins + losses
        win_rate = (wins / decided_picks * 100) if decided_picks > 0 else 0

        # Calculate expected win rate from odds
        expected_rate = self._calculate_expected_win_rate(picks)

        # Calculate edge
        edge = win_rate - expected_rate

        # Calculate ROI
        total_wagered = sum(p.units_wagered for p in picks if p.units_wagered)
        total_won = sum(p.units_result for p in picks if p.units_result and p.units_result > 0)
        total_lost = abs(sum(p.units_result for p in picks if p.units_result and p.units_result < 0))
        units_won = total_won - total_lost

        roi = (units_won / total_wagered * 100) if total_wagered > 0 else 0

        # Statistical significance
        p_value = self._calculate_p_value(wins, decided_picks, expected_rate / 100)
        confidence_interval = self._wilson_confidence_interval(wins, decided_picks)

        # Sample size needed for 95% confidence
        sample_needed = self._calculate_required_sample_size(win_rate / 100 if win_rate > 0 else 0.55)

        # Current statistical confidence
        current_confidence = min(95, (decided_picks / sample_needed) * 95) if sample_needed > 0 else 0

        return {
            "total_picks": total_picks,
            "wins": wins,
            "losses": losses,
            "pushes": pushes,
            "win_rate": round(win_rate, 1),
            "expected_rate": round(expected_rate, 1),
            "edge": round(edge, 1),
            "roi": round(roi, 1),
            "units_won": round(units_won, 2),
            "total_wagered": round(total_wagered, 2),
            "p_value": round(p_value, 4),
            "confidence_interval": [round(ci, 1) for ci in confidence_interval],
            "is_significant": p_value < 0.05,
            "sample_size_needed": sample_needed,
            "current_sample": decided_picks,
            "current_confidence": round(current_confidence, 0)
        }

    def get_bankroll_history(self) -> List[Dict]:
        """Get bankroll history over time"""
        snapshots = self.db.query(BankrollSnapshot).order_by(
            BankrollSnapshot.timestamp
        ).all()

        if not snapshots:
            return [{
                "timestamp": datetime.utcnow().isoformat(),
                "balance": STARTING_BANKROLL,
                "total_picks": 0,
                "roi": 0
            }]

        return [
            {
                "timestamp": s.timestamp.isoformat(),
                "balance": round(s.balance, 2),
                "total_picks": s.total_picks,
                "wins": s.total_wins,
                "losses": s.total_losses,
                "roi": round(s.roi, 1),
                "win_rate": round(s.win_rate, 1)
            }
            for s in snapshots
        ]

    def get_streak_analysis(self) -> Dict:
        """Analyze win/loss streaks and drawdowns"""
        picks = self.db.query(TrackedPick).filter(
            TrackedPick.status.in_(["won", "lost"])
        ).order_by(TrackedPick.settled_at).all()

        if not picks:
            return {
                "current_streak": 0,
                "current_streak_type": None,
                "longest_win_streak": 0,
                "longest_loss_streak": 0,
                "max_drawdown": 0,
                "max_drawdown_picks": 0
            }

        # Calculate streaks
        current_streak = 0
        current_type = None
        longest_win = 0
        longest_loss = 0
        temp_win = 0
        temp_loss = 0

        for pick in picks:
            if pick.status == "won":
                temp_win += 1
                temp_loss = 0
                if temp_win > longest_win:
                    longest_win = temp_win
            else:
                temp_loss += 1
                temp_win = 0
                if temp_loss > longest_loss:
                    longest_loss = temp_loss

        # Current streak
        if picks:
            last_result = picks[-1].status
            current_type = "win" if last_result == "won" else "loss"
            for i in range(len(picks) - 1, -1, -1):
                if picks[i].status == last_result:
                    current_streak += 1
                else:
                    break

        # Calculate max drawdown
        peak_bankroll = STARTING_BANKROLL
        max_drawdown = 0
        max_drawdown_picks = 0
        current_drawdown_picks = 0

        running_bankroll = STARTING_BANKROLL
        for pick in picks:
            if pick.units_result:
                running_bankroll += pick.units_result

            if running_bankroll > peak_bankroll:
                peak_bankroll = running_bankroll
                current_drawdown_picks = 0
            else:
                current_drawdown_picks += 1
                drawdown = ((peak_bankroll - running_bankroll) / peak_bankroll) * 100
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
                    max_drawdown_picks = current_drawdown_picks

        return {
            "current_streak": current_streak,
            "current_streak_type": current_type,
            "longest_win_streak": longest_win,
            "longest_loss_streak": longest_loss,
            "max_drawdown": round(max_drawdown, 1),
            "max_drawdown_picks": max_drawdown_picks
        }

    def get_picks(
        self,
        sport: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Get picks with filters"""
        query = self.db.query(TrackedPick)

        if sport:
            query = query.filter(TrackedPick.sport == sport.upper())
        if status:
            query = query.filter(TrackedPick.status == status.lower())
        if start_date:
            query = query.filter(TrackedPick.created_at >= start_date)
        if end_date:
            query = query.filter(TrackedPick.created_at <= end_date)

        picks = query.order_by(desc(TrackedPick.created_at)).limit(limit).all()

        return [self._pick_to_dict(p) for p in picks]

    def get_pick(self, pick_id: str) -> Optional[Dict]:
        """Get single pick details"""
        pick = self.db.query(TrackedPick).filter(TrackedPick.id == pick_id).first()
        if not pick:
            return None
        return self._pick_to_dict(pick)

    def get_stats_by_sport(self) -> Dict:
        """Get edge stats broken down by sport"""
        sports = self.db.query(TrackedPick.sport).distinct().all()
        sports = [s[0] for s in sports]

        stats_by_sport = {}
        for sport in sports:
            picks = self.db.query(TrackedPick).filter(
                TrackedPick.sport == sport,
                TrackedPick.status != "pending"
            ).all()

            wins = sum(1 for p in picks if p.status == "won")
            losses = sum(1 for p in picks if p.status == "lost")
            decided = wins + losses

            if decided > 0:
                win_rate = wins / decided * 100
                units_result = sum(p.units_result or 0 for p in picks)
                total_wagered = sum(p.units_wagered or 0 for p in picks)
                roi = (units_result / total_wagered * 100) if total_wagered > 0 else 0

                stats_by_sport[sport] = {
                    "total_picks": len(picks),
                    "wins": wins,
                    "losses": losses,
                    "win_rate": round(win_rate, 1),
                    "units_won": round(units_result, 2),
                    "roi": round(roi, 1)
                }

        return stats_by_sport

    def get_stats_by_confidence_tier(self) -> Dict:
        """Get stats by confidence tier to validate if higher confidence = better results"""
        tiers = [
            ("low", 0, 60),
            ("medium", 60, 75),
            ("high", 75, 90),
            ("very_high", 90, 101)
        ]

        tier_stats = {}
        for tier_name, min_conf, max_conf in tiers:
            picks = self.db.query(TrackedPick).filter(
                TrackedPick.confidence >= min_conf,
                TrackedPick.confidence < max_conf,
                TrackedPick.status != "pending"
            ).all()

            wins = sum(1 for p in picks if p.status == "won")
            losses = sum(1 for p in picks if p.status == "lost")
            decided = wins + losses

            if decided > 0:
                win_rate = wins / decided * 100
                units_result = sum(p.units_result or 0 for p in picks)

                tier_stats[tier_name] = {
                    "confidence_range": f"{min_conf}-{max_conf - 1}",
                    "total_picks": len(picks),
                    "wins": wins,
                    "losses": losses,
                    "win_rate": round(win_rate, 1),
                    "units_won": round(units_result, 2)
                }

        return tier_stats

    def export_data(self) -> List[Dict]:
        """Export all picks for external analysis"""
        picks = self.db.query(TrackedPick).order_by(TrackedPick.created_at).all()
        return [self._pick_to_dict(p, include_factors=True) for p in picks]

    # Private helper methods

    def _calculate_units(self, confidence: float, odds: int) -> float:
        """Calculate recommended units based on confidence and odds"""
        # Base units from confidence
        if confidence >= 90:
            base_units = 3.0
        elif confidence >= 80:
            base_units = 2.0
        elif confidence >= 70:
            base_units = 1.5
        elif confidence >= 60:
            base_units = 1.0
        else:
            base_units = 0.5

        # Adjust for odds value
        implied_prob = self._american_to_implied_prob(odds)
        if implied_prob < 0.4:  # Underdog
            base_units *= 0.75  # Be more conservative on underdogs
        elif implied_prob > 0.6:  # Heavy favorite
            base_units *= 1.1  # Slightly more on favorites

        return round(min(max(base_units, 0.5), 5.0), 1)

    def _calculate_result(self, result: str, units: float, odds: int) -> float:
        """Calculate units won/lost based on result and odds"""
        if result.lower() == "push":
            return 0.0
        elif result.lower() == "won":
            if odds > 0:
                return units * (odds / 100)
            else:
                return units * (100 / abs(odds))
        else:  # lost
            return -units

    def _get_current_bankroll(self) -> float:
        """Get current bankroll balance"""
        last_pick = self.db.query(TrackedPick).filter(
            TrackedPick.bankroll_after.isnot(None)
        ).order_by(desc(TrackedPick.settled_at)).first()

        if last_pick and last_pick.bankroll_after:
            return last_pick.bankroll_after
        return STARTING_BANKROLL

    def _create_snapshot(self):
        """Create a bankroll snapshot"""
        stats = self.get_edge_stats()
        current_bankroll = self._get_current_bankroll()

        snapshot = BankrollSnapshot(
            balance=current_bankroll,
            total_picks=stats["total_picks"],
            total_wins=stats["wins"],
            total_losses=stats["losses"],
            total_pushes=stats["pushes"],
            total_wagered=stats["total_wagered"],
            total_won=stats["units_won"] + stats["total_wagered"] if stats["units_won"] > 0 else 0,
            total_lost=abs(stats["units_won"]) if stats["units_won"] < 0 else 0,
            roi=stats["roi"],
            win_rate=stats["win_rate"]
        )

        self.db.add(snapshot)
        self.db.commit()

    def _calculate_expected_win_rate(self, picks: List[TrackedPick]) -> float:
        """Calculate expected win rate based on odds"""
        if not picks:
            return 52.4  # Default expected rate at -110

        total_implied = 0
        count = 0

        for pick in picks:
            if pick.odds:
                implied = self._american_to_implied_prob(pick.odds)
                total_implied += implied
                count += 1

        if count > 0:
            return (total_implied / count) * 100
        return 52.4

    def _american_to_implied_prob(self, odds: int) -> float:
        """Convert American odds to implied probability"""
        if odds > 0:
            return 100 / (odds + 100)
        else:
            return abs(odds) / (abs(odds) + 100)

    def _calculate_p_value(self, wins: int, total: int, expected_prob: float) -> float:
        """Calculate p-value using binomial test"""
        if total == 0:
            return 1.0

        # Use normal approximation for binomial test
        observed_prob = wins / total
        se = math.sqrt(expected_prob * (1 - expected_prob) / total)

        if se == 0:
            return 1.0

        z = (observed_prob - expected_prob) / se

        # Two-tailed p-value using normal CDF approximation
        p_value = 2 * (1 - self._normal_cdf(abs(z)))
        return max(0.0001, min(p_value, 1.0))

    def _normal_cdf(self, x: float) -> float:
        """Approximate normal CDF"""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    def _wilson_confidence_interval(self, wins: int, total: int, z: float = 1.96) -> tuple:
        """Calculate Wilson score confidence interval"""
        if total == 0:
            return (0, 100)

        p = wins / total
        n = total

        denominator = 1 + z * z / n
        centre = p + z * z / (2 * n)
        adjustment = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)

        lower = (centre - adjustment) / denominator
        upper = (centre + adjustment) / denominator

        return (max(0, lower * 100), min(100, upper * 100))

    def _calculate_required_sample_size(self, p: float, margin: float = 0.05, z: float = 1.96) -> int:
        """Calculate required sample size for 95% confidence"""
        if p <= 0 or p >= 1:
            p = 0.55  # Default assumption

        n = (z * z * p * (1 - p)) / (margin * margin)
        return int(math.ceil(n))

    def _calculate_factor_correlation(self, picks: List[TrackedPick], factor_name: str) -> float:
        """Calculate Pearson correlation between factor score and result"""
        scores = []
        results = []

        for pick in picks:
            if not pick.factors:
                continue

            try:
                factors = json.loads(pick.factors)
                factor_data = factors.get(factor_name, {})
                score = factor_data.get("score")

                if score is not None:
                    scores.append(score)
                    results.append(1 if pick.status == "won" else 0)
            except:
                continue

        if len(scores) < 5:
            return 0.0

        # Calculate Pearson correlation
        n = len(scores)
        sum_x = sum(scores)
        sum_y = sum(results)
        sum_xy = sum(x * y for x, y in zip(scores, results))
        sum_x2 = sum(x * x for x in scores)
        sum_y2 = sum(y * y for y in results)

        numerator = n * sum_xy - sum_x * sum_y
        denominator = math.sqrt((n * sum_x2 - sum_x ** 2) * (n * sum_y2 - sum_y ** 2))

        if denominator == 0:
            return 0.0

        return numerator / denominator

    def _pick_to_dict(self, pick: TrackedPick, include_factors: bool = True) -> Dict:
        """Convert pick model to dict - always includes factors for expanded view"""
        result = {
            "id": pick.id,
            "game_id": pick.game_id,
            "sport": pick.sport,
            "home_team": pick.home_team,
            "away_team": pick.away_team,
            "game_time": pick.game_time.isoformat() if pick.game_time else None,
            "pick_type": pick.pick_type,
            "pick": pick.pick,
            "pick_team": pick.pick_team,
            "line_value": pick.line_value,
            "odds": pick.odds,
            "confidence": pick.confidence,
            "recommended_units": pick.recommended_units,
            "units_wagered": pick.units_wagered,
            "status": pick.status,
            "result_score": pick.result_score,
            "spread_result": pick.spread_result,
            "total_result": pick.total_result,
            "units_result": pick.units_result,
            "bankroll_after": pick.bankroll_after,
            "created_at": pick.created_at.isoformat() if pick.created_at else None,
            "settled_at": pick.settled_at.isoformat() if pick.settled_at else None
        }

        # Always include factors and weather_data for expanded view
        if include_factors:
            result["factors"] = json.loads(pick.factors) if pick.factors else None
            result["weather_data"] = json.loads(pick.weather_data) if pick.weather_data else None

        return result


# Singleton-style helper functions
def get_edge_tracker(db: Session) -> EdgeTracker:
    """Get an EdgeTracker instance"""
    return EdgeTracker(db)
