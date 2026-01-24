"""
Player Prop Prediction Model

Provides predictions for player performance props including:
- Points, rebounds, assists (NBA)
- Passing/rushing/receiving yards (NFL)
- Hits, strikeouts, home runs (MLB)
- Goals, assists, saves (NHL)

Uses matchup analysis, usage rates, and injury impact modeling.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db import (
    Player, PlayerStats, Game, Team, InjuryReport,
    HistoricalGameResult, SessionLocal
)
from app.utils.logging import get_logger

logger = get_logger(__name__)


class PropType(str, Enum):
    """Types of player props."""
    # NBA
    POINTS = "points"
    REBOUNDS = "rebounds"
    ASSISTS = "assists"
    THREES = "threes"
    PRA = "points_rebounds_assists"
    STEALS_BLOCKS = "steals_blocks"

    # NFL
    PASSING_YARDS = "passing_yards"
    RUSHING_YARDS = "rushing_yards"
    RECEIVING_YARDS = "receiving_yards"
    TOUCHDOWNS = "touchdowns"
    COMPLETIONS = "completions"
    RECEPTIONS = "receptions"

    # MLB
    HITS = "hits"
    STRIKEOUTS = "strikeouts"
    HOME_RUNS = "home_runs"
    RBIS = "rbis"
    BASES = "total_bases"

    # NHL
    GOALS = "goals"
    ASSISTS_NHL = "assists_nhl"
    SHOTS = "shots"
    SAVES = "saves"


@dataclass
class PropPrediction:
    """A player prop prediction."""
    player_id: int
    player_name: str
    team: str
    opponent: str
    prop_type: str
    line: float
    projected_value: float
    over_probability: float
    under_probability: float
    edge_over: float
    edge_under: float
    confidence: float
    factors: Dict[str, Any]


# Sport-specific stat mappings
PROP_STAT_MAPPING = {
    "NBA": {
        PropType.POINTS: "points_per_game",
        PropType.REBOUNDS: "rebounds_per_game",
        PropType.ASSISTS: "assists_per_game",
    },
    "NFL": {
        PropType.PASSING_YARDS: "passing_yards",
        PropType.RUSHING_YARDS: "rushing_yards",
        PropType.TOUCHDOWNS: "touchdowns",
    },
    "MLB": {
        PropType.STRIKEOUTS: "era",  # Proxy
        PropType.HOME_RUNS: "home_runs",
        PropType.RBIS: "rbi",
    },
    "NHL": {
        PropType.GOALS: "goals",
        PropType.ASSISTS_NHL: "assists_hockey",
        PropType.SAVES: "save_percentage",
    },
}


# Default variance by prop type (standard deviation as % of mean)
PROP_VARIANCE = {
    PropType.POINTS: 0.30,
    PropType.REBOUNDS: 0.35,
    PropType.ASSISTS: 0.40,
    PropType.PASSING_YARDS: 0.25,
    PropType.RUSHING_YARDS: 0.45,
    PropType.RECEIVING_YARDS: 0.50,
    PropType.TOUCHDOWNS: 0.60,
    PropType.GOALS: 0.70,
    PropType.ASSISTS_NHL: 0.65,
}


class MatchupAnalyzer:
    """Analyzes player-opponent matchups."""

    # Defensive ratings by position (1.0 = average, <1.0 = good D, >1.0 = bad D)
    # These would ideally come from a database, using defaults here
    DEFAULT_DEF_RATING = 1.0

    def __init__(self, db: Session):
        self.db = db

    def get_opponent_defense_factor(
        self,
        opponent_team: Team,
        prop_type: PropType,
        sport: str
    ) -> float:
        """
        Get defensive factor for opponent.

        Returns multiplier: <1.0 means tough matchup, >1.0 means favorable.
        """
        # In production, this would query historical data
        # For now, use team rating as proxy
        if opponent_team and opponent_team.rating:
            # Higher rated teams = better defense = lower factor
            rating_diff = (opponent_team.rating - 1500) / 500
            return 1.0 - (rating_diff * 0.1)

        return self.DEFAULT_DEF_RATING

    def get_pace_factor(
        self,
        player_team: Team,
        opponent_team: Team,
        sport: str
    ) -> float:
        """
        Get pace factor for the matchup.

        Higher pace = more opportunities = higher projections.
        """
        # Default neutral pace
        pace = 1.0

        if sport == "NBA":
            # NBA pace affects counting stats significantly
            # Would use actual pace data in production
            pace = 1.0
        elif sport == "NFL":
            # NFL game script matters
            pace = 1.0

        return pace


class UsageRatePredictor:
    """Predicts player usage rates based on various factors."""

    def __init__(self, db: Session):
        self.db = db

    def predict_usage(
        self,
        player: Player,
        stats: Optional[PlayerStats],
        injuries: List[InjuryReport]
    ) -> float:
        """
        Predict usage rate adjustment.

        Returns multiplier for expected usage.
        """
        usage_factor = 1.0

        # Check for teammate injuries that might increase usage
        if injuries:
            for injury in injuries:
                if injury.is_active and injury.status in ["out", "doubtful"]:
                    # Key player out = increased usage for others
                    if injury.impact_rating and injury.impact_rating > 7:
                        usage_factor += 0.05

        # Minutes factor (if player is playing more/less than usual)
        if stats and stats.minutes_per_game:
            # This would compare to recent games
            pass

        return min(1.3, max(0.7, usage_factor))


class InjuryImpactModeler:
    """Models the impact of injuries on player performance."""

    INJURY_IMPACTS = {
        "out": 0.0,
        "doubtful": 0.15,
        "questionable": 0.7,
        "probable": 0.95,
        "active": 1.0,
    }

    BODY_PART_FACTORS = {
        # Lower impact
        "finger": 0.95,
        "toe": 0.95,
        "wrist": 0.90,

        # Medium impact
        "ankle": 0.80,
        "knee": 0.75,
        "hamstring": 0.75,
        "groin": 0.80,

        # Higher impact
        "back": 0.70,
        "shoulder": 0.75,
        "concussion": 0.60,
    }

    def get_injury_factor(self, injury: Optional[InjuryReport]) -> Tuple[float, str]:
        """
        Get performance factor based on injury.

        Returns (factor, reason).
        """
        if not injury or not injury.is_active:
            return 1.0, "healthy"

        status_factor = self.INJURY_IMPACTS.get(injury.status.lower(), 1.0)

        if status_factor == 0.0:
            return 0.0, f"out - {injury.injury_type}"

        # Adjust for body part
        body_factor = 1.0
        if injury.body_part:
            body_lower = injury.body_part.lower()
            for part, factor in self.BODY_PART_FACTORS.items():
                if part in body_lower:
                    body_factor = factor
                    break

        final_factor = status_factor * body_factor
        reason = f"{injury.status} - {injury.injury_type}"

        return final_factor, reason


class PlayerPropModel:
    """Main player prop prediction model."""

    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
        self.matchup_analyzer = MatchupAnalyzer(self.db)
        self.usage_predictor = UsageRatePredictor(self.db)
        self.injury_modeler = InjuryImpactModeler()

    def get_player_baseline(
        self,
        player: Player,
        stats: Optional[PlayerStats],
        prop_type: PropType
    ) -> Optional[float]:
        """Get baseline projection from historical stats."""
        if not stats:
            return None

        sport = player.sport
        stat_mapping = PROP_STAT_MAPPING.get(sport, {})
        stat_field = stat_mapping.get(prop_type)

        if stat_field and hasattr(stats, stat_field):
            return getattr(stats, stat_field)

        return None

    def calculate_projection(
        self,
        player: Player,
        opponent_team: Optional[Team],
        prop_type: PropType,
        stats: Optional[PlayerStats] = None,
        injury: Optional[InjuryReport] = None,
        teammate_injuries: List[InjuryReport] = None,
        is_home: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate projected value for a player prop.
        """
        factors = {}

        # Get baseline
        baseline = self.get_player_baseline(player, stats, prop_type)
        if baseline is None:
            return {"error": "No baseline stats available"}

        factors["baseline"] = baseline
        projection = baseline

        # Home/away adjustment
        home_factor = 1.03 if is_home else 0.97
        projection *= home_factor
        factors["home_away"] = home_factor

        # Matchup adjustment
        if opponent_team:
            matchup_factor = self.matchup_analyzer.get_opponent_defense_factor(
                opponent_team, prop_type, player.sport
            )
            projection *= matchup_factor
            factors["matchup"] = matchup_factor

        # Usage adjustment
        usage_factor = self.usage_predictor.predict_usage(
            player, stats, teammate_injuries or []
        )
        projection *= usage_factor
        factors["usage"] = usage_factor

        # Injury adjustment
        injury_factor, injury_reason = self.injury_modeler.get_injury_factor(injury)
        if injury_factor == 0:
            return {"error": f"Player is {injury_reason}"}

        projection *= injury_factor
        factors["injury"] = {"factor": injury_factor, "reason": injury_reason}

        # Calculate variance
        variance_pct = PROP_VARIANCE.get(prop_type, 0.35)
        std_dev = projection * variance_pct

        factors["projected_value"] = round(projection, 1)
        factors["std_dev"] = round(std_dev, 2)

        return factors

    def predict_prop(
        self,
        player_id: int,
        prop_type: PropType,
        line: float,
        opponent_team_id: Optional[int] = None,
        is_home: bool = True
    ) -> Optional[PropPrediction]:
        """
        Generate a prediction for a specific player prop.
        """
        # Get player
        player = self.db.query(Player).filter(Player.id == player_id).first()
        if not player:
            logger.warning(f"Player {player_id} not found")
            return None

        # Get current season stats
        current_year = datetime.utcnow().year
        season = f"{current_year}-{current_year + 1}" if datetime.utcnow().month > 6 else f"{current_year - 1}-{current_year}"

        stats = self.db.query(PlayerStats).filter(
            PlayerStats.player_id == player_id,
            PlayerStats.season == season
        ).first()

        # Get player's injury status
        injury = self.db.query(InjuryReport).filter(
            InjuryReport.player_id == player_id,
            InjuryReport.is_active == True
        ).first()

        # Get opponent team
        opponent_team = None
        if opponent_team_id:
            opponent_team = self.db.query(Team).filter(Team.id == opponent_team_id).first()

        # Get teammate injuries (same team, active)
        teammate_injuries = []
        if player.team_id:
            teammate_injuries = self.db.query(InjuryReport).join(Player).filter(
                Player.team_id == player.team_id,
                Player.id != player_id,
                InjuryReport.is_active == True
            ).all()

        # Calculate projection
        projection_data = self.calculate_projection(
            player=player,
            opponent_team=opponent_team,
            prop_type=prop_type,
            stats=stats,
            injury=injury,
            teammate_injuries=teammate_injuries,
            is_home=is_home
        )

        if "error" in projection_data:
            logger.warning(f"Projection error for player {player_id}: {projection_data['error']}")
            return None

        projected_value = projection_data["projected_value"]
        std_dev = projection_data["std_dev"]

        # Calculate probabilities using normal distribution approximation
        from math import erf, sqrt

        def normal_cdf(x, mean, std):
            """Cumulative distribution function for normal distribution."""
            if std == 0:
                return 1.0 if x >= mean else 0.0
            return 0.5 * (1 + erf((x - mean) / (std * sqrt(2))))

        under_prob = normal_cdf(line, projected_value, std_dev)
        over_prob = 1 - under_prob

        # Assume -110 juice on both sides (implied prob 52.4%)
        implied_prob = 0.524

        edge_over = (over_prob - implied_prob) * 100
        edge_under = (under_prob - implied_prob) * 100

        # Confidence based on sample size and projection stability
        confidence = 0.5  # Base confidence
        if stats and stats.games_played:
            # More games = higher confidence
            confidence += min(0.3, stats.games_played / 50)
        if injury:
            confidence -= 0.15  # Less confident with injury

        confidence = max(0.2, min(0.9, confidence))

        # Get team names
        team_name = player.team.name if player.team else "Unknown"
        opponent_name = opponent_team.name if opponent_team else "Unknown"

        return PropPrediction(
            player_id=player.id,
            player_name=player.name,
            team=team_name,
            opponent=opponent_name,
            prop_type=prop_type.value,
            line=line,
            projected_value=projected_value,
            over_probability=round(over_prob, 3),
            under_probability=round(under_prob, 3),
            edge_over=round(edge_over, 1),
            edge_under=round(edge_under, 1),
            confidence=round(confidence, 2),
            factors=projection_data
        )

    def find_value_props(
        self,
        sport: str,
        min_edge: float = 5.0,
        limit: int = 20
    ) -> List[PropPrediction]:
        """
        Find player props with positive expected value.
        """
        value_props = []

        # Get players with stats
        current_year = datetime.utcnow().year
        season = f"{current_year}-{current_year + 1}" if datetime.utcnow().month > 6 else f"{current_year - 1}-{current_year}"

        players_with_stats = self.db.query(Player, PlayerStats).join(
            PlayerStats, Player.id == PlayerStats.player_id
        ).filter(
            Player.sport == sport,
            Player.is_active == True,
            PlayerStats.season == season
        ).limit(100).all()

        prop_types = list(PROP_STAT_MAPPING.get(sport, {}).keys())

        for player, stats in players_with_stats:
            for prop_type in prop_types:
                baseline = self.get_player_baseline(player, stats, prop_type)
                if baseline is None or baseline <= 0:
                    continue

                # Simulate different lines around baseline
                for line_offset in [-1, -0.5, 0, 0.5, 1]:
                    line = baseline + line_offset
                    if line <= 0:
                        continue

                    prediction = self.predict_prop(
                        player_id=player.id,
                        prop_type=prop_type,
                        line=line
                    )

                    if prediction:
                        # Check if either side has value
                        if prediction.edge_over >= min_edge or prediction.edge_under >= min_edge:
                            value_props.append(prediction)

        # Sort by max edge
        value_props.sort(
            key=lambda p: max(p.edge_over, p.edge_under),
            reverse=True
        )

        return value_props[:limit]


def get_prop_prediction(
    db: Session,
    player_id: int,
    prop_type: str,
    line: float,
    opponent_team_id: Optional[int] = None,
    is_home: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Get a prediction for a player prop.

    Convenience function for API usage.
    """
    try:
        prop_type_enum = PropType(prop_type)
    except ValueError:
        return {"error": f"Invalid prop type: {prop_type}"}

    model = PlayerPropModel(db)
    prediction = model.predict_prop(
        player_id=player_id,
        prop_type=prop_type_enum,
        line=line,
        opponent_team_id=opponent_team_id,
        is_home=is_home
    )

    if prediction:
        return {
            "player_id": prediction.player_id,
            "player_name": prediction.player_name,
            "team": prediction.team,
            "opponent": prediction.opponent,
            "prop_type": prediction.prop_type,
            "line": prediction.line,
            "projected_value": prediction.projected_value,
            "over_probability": prediction.over_probability,
            "under_probability": prediction.under_probability,
            "edge_over": prediction.edge_over,
            "edge_under": prediction.edge_under,
            "confidence": prediction.confidence,
            "recommendation": "over" if prediction.edge_over > prediction.edge_under else "under",
            "factors": prediction.factors
        }

    return None


def find_value_player_props(
    db: Session,
    sport: str,
    min_edge: float = 5.0,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Find player props with positive expected value.

    Convenience function for API usage.
    """
    model = PlayerPropModel(db)
    predictions = model.find_value_props(sport, min_edge, limit)

    return [
        {
            "player_id": p.player_id,
            "player_name": p.player_name,
            "team": p.team,
            "opponent": p.opponent,
            "prop_type": p.prop_type,
            "line": p.line,
            "projected_value": p.projected_value,
            "over_probability": p.over_probability,
            "under_probability": p.under_probability,
            "edge_over": p.edge_over,
            "edge_under": p.edge_under,
            "confidence": p.confidence,
            "recommendation": "over" if p.edge_over > p.edge_under else "under",
        }
        for p in predictions
    ]
