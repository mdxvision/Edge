"""
Edge Aggregator Service

The BRAIN that combines all edge factors into unified predictions.
Weighs each factor by reliability and historical predictiveness.
"""

import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.db import (
    Game, UnifiedPrediction, Coach, CoachSituationalRecord,
    Official, LineMovementSummary, GameSituation, GameWeather,
    SocialSentiment, PublicBettingData
)


# Edge factor weights - tuned based on historical predictiveness
EDGE_WEIGHTS = {
    "line_movement": 0.20,      # Most predictive - sharp money
    "coach_dna": 0.18,          # Unique to us - situational coaching
    "situational": 0.17,        # Rest, travel, motivation
    "weather": 0.12,            # Sport-dependent impact
    "officials": 0.10,          # Refs/umps tendency
    "public_fade": 0.10,        # Contrarian signal
    "historical_elo": 0.08,     # Base power ratings
    "social_sentiment": 0.05,   # Soft signal
}

# Confidence thresholds
CONFIDENCE_THRESHOLDS = {
    "VERY_HIGH": 0.75,
    "HIGH": 0.65,
    "MEDIUM": 0.55,
    "LOW": 0.45,
}

# Maximum realistic edge for sports betting
MAX_REALISTIC_EDGE = 10.0  # 10% max edge in percentage points
MAX_REALISTIC_CONFIDENCE = 0.85  # 85% max confidence
MIN_REALISTIC_CONFIDENCE = 0.45  # 45% min confidence

# Recommendation thresholds - more conservative
RECOMMENDATION_MAP = {
    0.70: ("STRONG BET", 2.0),  # 2 units - high confidence
    0.60: ("BET", 1.5),         # 1.5 units
    0.52: ("LEAN", 1.0),        # 1 unit
    0.48: ("MONITOR", 0.5),     # 0.5 units
    0.00: ("AVOID", 0.0),       # No bet
}


async def get_unified_prediction(
    game_id: int,
    db: Session,
    market_type: str = "spread"
) -> Dict[str, Any]:
    """
    Combine ALL edge factors into single prediction.

    This is the core function that aggregates all our edge sources.
    """
    # Get game info
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        return {"error": "Game not found"}

    # Handle both relationship objects and string names
    # game.home_team could be a Team object (relationship) or None
    if game.home_team and hasattr(game.home_team, 'name'):
        home_team = game.home_team.name
    else:
        home_team = "Home"

    if game.away_team and hasattr(game.away_team, 'name'):
        away_team = game.away_team.name
    else:
        away_team = "Away"

    sport = game.sport or "NFL"

    # Initialize factors dictionary
    factors = {}

    # 1. Line Movement Analysis
    factors["line_movement"] = await _get_line_movement_edge(game_id, db)

    # 2. Coach DNA Analysis
    factors["coach_dna"] = await _get_coach_dna_edge(home_team, away_team, sport, db)

    # 3. Situational Analysis
    factors["situational"] = await _get_situational_edge(game_id, home_team, away_team, sport, db)

    # 4. Weather Analysis
    factors["weather"] = await _get_weather_edge(game_id, sport, db)

    # 5. Officials Analysis
    factors["officials"] = await _get_officials_edge(game_id, sport, db)

    # 6. Public Fade Analysis
    factors["public_fade"] = await _get_public_fade_edge(game_id, db)

    # 7. Historical ELO Analysis
    factors["historical_elo"] = await _get_elo_edge(home_team, away_team, sport, db)

    # 8. Social Sentiment Analysis
    factors["social_sentiment"] = await _get_social_sentiment_edge(home_team, away_team, sport, db)

    # Calculate weighted edges
    weighted_factors = _calculate_weighted_factors(factors)

    # Analyze alignment
    analysis = _analyze_factor_alignment(weighted_factors)

    # Generate final prediction
    prediction = _generate_prediction(
        weighted_factors,
        analysis,
        home_team,
        away_team,
        market_type
    )

    # Generate explanation
    explanation = _generate_explanation(
        weighted_factors,
        analysis,
        prediction,
        home_team,
        away_team
    )

    result = {
        "game_id": game_id,
        "game": f"{away_team} @ {home_team}",
        "sport": sport,
        "market": market_type,
        "game_time": game.start_time.isoformat() if game.start_time else None,
        "factors": weighted_factors,
        "analysis": analysis,
        "prediction": prediction,
        "explanation": explanation
    }

    # Store prediction
    await _store_prediction(game_id, result, db)

    return result


async def _get_line_movement_edge(game_id: int, db: Session) -> Dict[str, Any]:
    """Get edge from line movement analysis."""
    summary = db.query(LineMovementSummary).filter(
        LineMovementSummary.game_id == game_id
    ).first()

    if summary and summary.reverse_line_movement:
        # RLM detected - sharp money indicator
        edge = 3.5  # Fixed edge for RLM signal
        direction = "away" if summary.movement_direction == "toward_underdog" else "home"
        signal = "Reverse line movement detected - sharp money signal"

        if summary.steam_move_detected:
            edge = 5.0  # Strong edge for RLM + steam move
            signal = "Steam move + RLM - strong sharp action"
    elif summary and summary.steam_move_detected:
        edge = 3.0
        direction = summary.movement_direction or "neutral"
        signal = "Steam move detected - coordinated sharp action"
    else:
        # No line movement data available
        edge = 0.0
        direction = "neutral"
        signal = "No line movement data available"

    return {
        "edge": round(edge, 2),
        "direction": direction,
        "signal": signal,
        "weight": EDGE_WEIGHTS["line_movement"]
    }


async def _get_coach_dna_edge(
    home_team: str,
    away_team: str,
    sport: str,
    db: Session
) -> Dict[str, Any]:
    """Get edge from coach situational records."""
    # Ensure home_team and away_team are strings
    home_team_name = str(home_team) if home_team else ""
    away_team_name = str(away_team) if away_team else ""

    # Find coaches for these teams
    home_coach = db.query(Coach).filter(
        Coach.current_team == home_team_name,
        Coach.sport == sport
    ).first()

    away_coach = db.query(Coach).filter(
        Coach.current_team == away_team_name,
        Coach.sport == sport
    ).first()

    edge = 0.0
    direction = "neutral"
    signal = "No coach DNA data available"

    if home_coach:
        # Check situational records
        records = db.query(CoachSituationalRecord).filter(
            CoachSituationalRecord.coach_id == home_coach.id
        ).all()

        for record in records:
            if record.total_games >= 10:
                win_pct = record.ats_wins / record.total_games if record.total_games > 0 else 0.5
                if win_pct > 0.55:
                    edge += (win_pct - 0.5) * 10
                    signal = f"{home_coach.name}: {record.situation} record {record.ats_wins}-{record.ats_losses} ATS"
                    direction = "home"

    if away_coach:
        records = db.query(CoachSituationalRecord).filter(
            CoachSituationalRecord.coach_id == away_coach.id
        ).all()

        for record in records:
            if record.total_games >= 10:
                win_pct = record.ats_wins / record.total_games if record.total_games > 0 else 0.5
                if win_pct > 0.55:
                    edge -= (win_pct - 0.5) * 10
                    if direction == "neutral":
                        signal = f"{away_coach.name}: {record.situation} record {record.ats_wins}-{record.ats_losses} ATS"
                        direction = "away"

    # If no coach data, return no edge
    if not home_coach and not away_coach:
        edge = 0.0
        direction = "neutral"
        signal = "No coach DNA data available"

    return {
        "edge": round(abs(edge), 2),
        "direction": direction,
        "signal": signal,
        "weight": EDGE_WEIGHTS["coach_dna"]
    }


async def _get_situational_edge(
    game_id: int,
    home_team: str,
    away_team: str,
    sport: str,
    db: Session
) -> Dict[str, Any]:
    """Get edge from situational factors (rest, travel, motivation)."""
    situation = db.query(GameSituation).filter(
        GameSituation.game_id == game_id
    ).first()

    if situation:
        edge = situation.total_situation_edge or 0

        signals = []
        if situation.rest_edge_home and abs(situation.rest_edge_home) > 0.5:
            signals.append(f"Rest edge: {'home' if situation.rest_edge_home > 0 else 'away'}")
        if situation.travel_edge_home and abs(situation.travel_edge_home) > 0.5:
            signals.append(f"Travel impact: {'home' if situation.travel_edge_home > 0 else 'away'}")
        if situation.is_letdown_spot:
            signals.append(f"Letdown spot for {situation.letdown_team}")
        if situation.is_lookahead_spot:
            signals.append(f"Lookahead spot for {situation.lookahead_team}")

        direction = "home" if edge > 0 else "away" if edge < 0 else "neutral"
        signal = "; ".join(signals) if signals else "No significant situational factors"
    else:
        # No situational data available
        edge = 0.0
        direction = "neutral"
        signal = "No situational data available"

    return {
        "edge": round(abs(edge), 2),
        "direction": direction,
        "signal": signal,
        "weight": EDGE_WEIGHTS["situational"]
    }


async def _get_weather_edge(game_id: int, sport: str, db: Session) -> Dict[str, Any]:
    """Get edge from weather analysis."""
    weather = db.query(GameWeather).filter(
        GameWeather.game_id == game_id
    ).first()

    if weather:
        edge = 0.0
        signals = []

        # Analyze weather factors
        if weather.wind_speed_mph and weather.wind_speed_mph > 15:
            edge -= 1.5  # Under tendency in high wind
            signals.append(f"High winds ({weather.wind_speed_mph} mph) - under lean")

        if weather.temperature_f and weather.temperature_f < 32:
            edge -= 1.0
            signals.append(f"Freezing temps ({weather.temperature_f}°F) - under lean")

        if weather.precipitation_in and weather.precipitation_in > 0.1:
            edge -= 1.2
            signals.append("Precipitation expected - under lean")

        direction = "under" if edge < 0 else "over" if edge > 0 else "neutral"
        signal = "; ".join(signals) if signals else "Dome game - no weather impact"
    else:
        # Default: no weather impact
        edge = 0.0
        direction = "neutral"
        signal = "No weather data or dome game"

    return {
        "edge": round(abs(edge), 2),
        "direction": direction,
        "signal": signal,
        "weight": EDGE_WEIGHTS["weather"]
    }


async def _get_officials_edge(game_id: int, sport: str, db: Session) -> Dict[str, Any]:
    """Get edge from official/referee tendencies."""
    # Look up assigned official from database
    official = db.query(Official).filter(
        Official.sport == sport
    ).first()

    if official and official.over_under_tendency:
        edge = abs(official.over_under_tendency)
        direction = "over" if official.over_under_tendency > 0 else "under"
        signal = f"{official.name} has {direction} tendency (+{edge:.1f} pts avg)"
    else:
        # No official data available
        edge = 0.0
        direction = "neutral"
        signal = "No official data available"

    return {
        "edge": round(edge, 2),
        "direction": direction,
        "signal": signal,
        "weight": EDGE_WEIGHTS["officials"]
    }


async def _get_public_fade_edge(game_id: int, db: Session) -> Dict[str, Any]:
    """Get edge from fading public betting."""
    public_data = db.query(PublicBettingData).filter(
        PublicBettingData.game_id == game_id
    ).first()

    if public_data:
        home_pct = public_data.spread_bet_pct_home or 50

        if home_pct >= 75:
            edge = 5.5  # Strong fade signal
            direction = "away"
            signal = f"Public heavily on home ({home_pct:.0f}%) - fade to away"
        elif home_pct >= 70:
            edge = 3.8
            direction = "away"
            signal = f"Public on home ({home_pct:.0f}%) - lean away"
        elif home_pct <= 25:
            edge = 5.5
            direction = "home"
            signal = f"Public heavily on away ({100-home_pct:.0f}%) - fade to home"
        elif home_pct <= 30:
            edge = 3.8
            direction = "home"
            signal = f"Public on away ({100-home_pct:.0f}%) - lean home"
        else:
            edge = 0.0
            direction = "neutral"
            signal = "Even public action - no fade signal"
    else:
        # No public betting data available
        edge = 0.0
        direction = "neutral"
        signal = "No public betting data available"

    return {
        "edge": round(edge, 2),
        "direction": direction,
        "signal": signal,
        "weight": EDGE_WEIGHTS["public_fade"]
    }


async def _get_elo_edge(home_team: str, away_team: str, sport: str, db: Session) -> Dict[str, Any]:
    """Get edge from historical ELO ratings."""
    from app.db import Team

    home = db.query(Team).filter(Team.name == home_team, Team.sport == sport).first()
    away = db.query(Team).filter(Team.name == away_team, Team.sport == sport).first()

    if home and away and home.rating and away.rating:
        elo_diff = home.rating - away.rating
        # Convert ELO difference to edge
        edge = elo_diff / 100  # Every 100 ELO points = 1% edge
        direction = "home" if edge > 0 else "away" if edge < 0 else "neutral"
        signal = f"ELO: {home_team} {home.rating:.0f} vs {away_team} {away.rating:.0f}"
    else:
        # No ELO data available
        edge = 0.0
        direction = "neutral"
        signal = "No ELO data available"

    return {
        "edge": round(abs(edge), 2),
        "direction": direction,
        "signal": signal,
        "weight": EDGE_WEIGHTS["historical_elo"]
    }


async def _get_social_sentiment_edge(
    home_team: str,
    away_team: str,
    sport: str,
    db: Session
) -> Dict[str, Any]:
    """Get edge from social sentiment analysis."""
    home_sentiment = db.query(SocialSentiment).filter(
        SocialSentiment.team_name == home_team,
        SocialSentiment.sport == sport
    ).order_by(SocialSentiment.timestamp.desc()).first()

    away_sentiment = db.query(SocialSentiment).filter(
        SocialSentiment.team_name == away_team,
        SocialSentiment.sport == sport
    ).order_by(SocialSentiment.timestamp.desc()).first()

    if home_sentiment and away_sentiment:
        # If one team is heavily hyped, fade them
        home_bullish = home_sentiment.bullish_percentage or 50
        away_bullish = away_sentiment.bullish_percentage or 50

        if home_bullish > 75:
            edge = 1.5
            direction = "away"
            signal = f"Heavy social hype on {home_team} - contrarian to {away_team}"
        elif away_bullish > 75:
            edge = 1.5
            direction = "home"
            signal = f"Heavy social hype on {away_team} - contrarian to {home_team}"
        else:
            edge = 0.0
            direction = "neutral"
            signal = "Balanced social sentiment"
    else:
        # No social sentiment data available
        edge = 0.0
        direction = "neutral"
        signal = "No social sentiment data available"

    return {
        "edge": round(edge, 2),
        "direction": direction,
        "signal": signal,
        "weight": EDGE_WEIGHTS["social_sentiment"]
    }


def _calculate_weighted_factors(factors: Dict[str, Dict]) -> Dict[str, Dict]:
    """Calculate weighted contribution of each factor."""
    for key, factor in factors.items():
        edge = factor.get("edge", 0)
        weight = factor.get("weight", 0)
        weighted = edge * weight
        factor["weighted_contribution"] = f"{'+' if weighted >= 0 else ''}{weighted:.2f}%"

    return factors


def _analyze_factor_alignment(factors: Dict[str, Dict]) -> Dict[str, Any]:
    """Analyze how well factors align (confirming vs conflicting)."""
    directions = {}

    for key, factor in factors.items():
        direction = factor.get("direction", "neutral")
        edge = factor.get("edge", 0)

        if direction != "neutral" and edge > 0.5:
            if direction not in directions:
                directions[direction] = 0
            directions[direction] += 1

    # Count confirming and conflicting
    if not directions:
        confirming = 0
        conflicting = 0
        alignment = 0.5
    else:
        max_direction = max(directions.values())
        confirming = max_direction
        conflicting = sum(directions.values()) - max_direction
        alignment = confirming / (confirming + conflicting) if (confirming + conflicting) > 0 else 0.5

    return {
        "confirming_factors": confirming,
        "conflicting_factors": conflicting,
        "alignment_score": round(alignment, 2),
        "dominant_direction": max(directions, key=directions.get) if directions else "neutral"
    }


def _generate_prediction(
    factors: Dict[str, Dict],
    analysis: Dict[str, Any],
    home_team: str,
    away_team: str,
    market_type: str
) -> Dict[str, Any]:
    """Generate final prediction based on weighted factors."""
    # Sum weighted edges by direction
    home_edge = 0.0
    away_edge = 0.0

    for key, factor in factors.items():
        edge = factor.get("edge", 0)
        weight = factor.get("weight", 0)
        direction = factor.get("direction", "neutral")

        weighted = edge * weight

        if direction == "home":
            home_edge += weighted
        elif direction == "away":
            away_edge += weighted

    # Calculate net edge
    net_edge = home_edge - away_edge

    # Determine predicted side
    if abs(net_edge) < 0.5:
        predicted_side = "EVEN - No Strong Edge"
        raw_edge = 0
    elif net_edge > 0:
        predicted_side = f"{home_team}"
        raw_edge = net_edge
    else:
        predicted_side = f"{away_team}"
        raw_edge = abs(net_edge)

    # Cap edge at realistic maximum (10% max)
    raw_edge = min(raw_edge, MAX_REALISTIC_EDGE)

    # Calculate confidence based on alignment and edge strength
    # More conservative calculation for realistic confidence values
    base_confidence = analysis.get("alignment_score", 0.5) * 0.4
    edge_confidence = min(0.25, raw_edge / 15)  # More conservative edge contribution
    confidence = base_confidence + edge_confidence + 0.25  # +0.25 baseline
    confidence = max(MIN_REALISTIC_CONFIDENCE, min(MAX_REALISTIC_CONFIDENCE, confidence))

    # Get confidence label
    if confidence >= CONFIDENCE_THRESHOLDS["VERY_HIGH"]:
        confidence_label = "VERY HIGH"
    elif confidence >= CONFIDENCE_THRESHOLDS["HIGH"]:
        confidence_label = "HIGH"
    elif confidence >= CONFIDENCE_THRESHOLDS["MEDIUM"]:
        confidence_label = "MEDIUM"
    else:
        confidence_label = "LOW"

    # Get recommendation - only recommend bets if there's actual edge
    if raw_edge < 1.5:  # Less than 1.5% edge = no bet
        recommendation = "AVOID"
        unit_size = 0.0
    else:
        recommendation = "AVOID"
        unit_size = 0.0

        for threshold, (rec, units) in RECOMMENDATION_MAP.items():
            if confidence >= threshold:
                recommendation = rec
                unit_size = units
                break

    # Calculate Kelly fraction
    # Kelly = (bp - q) / b where b = odds, p = probability, q = 1-p
    implied_prob = 0.5  # Assume -110 odds
    kelly_fraction = ((raw_edge / 100) * implied_prob) / implied_prob if raw_edge > 0 else 0
    kelly_fraction = max(0, min(0.1, kelly_fraction))  # Cap at 10%

    # Calculate expected value
    expected_value = raw_edge * confidence

    # Star rating (1-5)
    if raw_edge >= 5 and confidence >= 0.75:
        stars = 5
    elif raw_edge >= 4 or (raw_edge >= 3 and confidence >= 0.70):
        stars = 4
    elif raw_edge >= 2.5 or (raw_edge >= 2 and confidence >= 0.65):
        stars = 3
    elif raw_edge >= 1.5:
        stars = 2
    else:
        stars = 1

    return {
        "side": predicted_side,
        "raw_edge": f"+{raw_edge:.1f}%" if raw_edge > 0 else "0%",
        "raw_edge_value": round(raw_edge, 2),
        "confidence": round(confidence, 2),
        "confidence_label": confidence_label,
        "expected_value": f"+{expected_value:.1f}%",
        "kelly_fraction": round(kelly_fraction, 4),
        "recommendation": recommendation,
        "unit_size": f"{unit_size} units",
        "star_rating": stars
    }


def _generate_explanation(
    factors: Dict[str, Dict],
    analysis: Dict[str, Any],
    prediction: Dict[str, Any],
    home_team: str,
    away_team: str
) -> str:
    """Generate natural language explanation of the prediction."""
    side = prediction.get("side", "")
    edge = prediction.get("raw_edge", "0%")
    confidence_label = prediction.get("confidence_label", "LOW")
    recommendation = prediction.get("recommendation", "AVOID")

    # Get top contributing factors
    sorted_factors = sorted(
        [(k, v) for k, v in factors.items() if v.get("edge", 0) > 0.5],
        key=lambda x: x[1].get("edge", 0) * x[1].get("weight", 0),
        reverse=True
    )[:3]

    if not sorted_factors or prediction.get("raw_edge_value", 0) < 1:
        return f"No significant edge detected. Factors are mixed or neutral. {recommendation}."

    # Build explanation
    factor_explanations = []
    for key, factor in sorted_factors:
        signal = factor.get("signal", "")
        if signal:
            factor_explanations.append(signal)

    confirming = analysis.get("confirming_factors", 0)
    conflicting = analysis.get("conflicting_factors", 0)

    explanation = f"{side} shows value with {edge} edge ({confidence_label} confidence). "

    if factor_explanations:
        explanation += "Key factors: " + "; ".join(factor_explanations[:2]) + ". "

    if conflicting > 0:
        explanation += f"Note: {conflicting} conflicting signal(s) reduce confidence. "

    explanation += f"Recommendation: {recommendation}."

    return explanation


async def _store_prediction(
    game_id: int,
    result: Dict[str, Any],
    db: Session
) -> None:
    """Store the unified prediction in the database."""
    factors = result.get("factors", {})
    prediction = result.get("prediction", {})
    analysis = result.get("analysis", {})

    # Check for existing prediction
    existing = db.query(UnifiedPrediction).filter(
        UnifiedPrediction.game_id == game_id,
        UnifiedPrediction.market_type == result.get("market", "spread")
    ).first()

    if existing:
        # Update existing
        existing.line_movement_edge = factors.get("line_movement", {}).get("edge")
        existing.line_movement_direction = factors.get("line_movement", {}).get("direction")
        existing.line_movement_signal = factors.get("line_movement", {}).get("signal")

        existing.coach_dna_edge = factors.get("coach_dna", {}).get("edge")
        existing.coach_dna_direction = factors.get("coach_dna", {}).get("direction")
        existing.coach_dna_signal = factors.get("coach_dna", {}).get("signal")

        existing.situational_edge = factors.get("situational", {}).get("edge")
        existing.situational_direction = factors.get("situational", {}).get("direction")
        existing.situational_signal = factors.get("situational", {}).get("signal")

        existing.weather_edge = factors.get("weather", {}).get("edge")
        existing.weather_direction = factors.get("weather", {}).get("direction")
        existing.weather_signal = factors.get("weather", {}).get("signal")

        existing.officials_edge = factors.get("officials", {}).get("edge")
        existing.officials_direction = factors.get("officials", {}).get("direction")
        existing.officials_signal = factors.get("officials", {}).get("signal")

        existing.public_fade_edge = factors.get("public_fade", {}).get("edge")
        existing.public_fade_direction = factors.get("public_fade", {}).get("direction")
        existing.public_fade_signal = factors.get("public_fade", {}).get("signal")

        existing.confirming_factors = analysis.get("confirming_factors")
        existing.conflicting_factors = analysis.get("conflicting_factors")
        existing.alignment_score = analysis.get("alignment_score")

        existing.predicted_side = prediction.get("side")
        existing.raw_edge = prediction.get("raw_edge_value")
        existing.confidence = prediction.get("confidence")
        existing.confidence_label = prediction.get("confidence_label")
        existing.recommendation = prediction.get("recommendation")
        existing.star_rating = prediction.get("star_rating")
        existing.explanation = result.get("explanation")

        existing.updated_at = datetime.utcnow()
    else:
        # Create new
        game = db.query(Game).filter(Game.id == game_id).first()

        # Extract team names from relationship objects
        home_team_name = ""
        away_team_name = ""
        if game:
            if game.home_team and hasattr(game.home_team, 'name'):
                home_team_name = game.home_team.name
            if game.away_team and hasattr(game.away_team, 'name'):
                away_team_name = game.away_team.name

        new_prediction = UnifiedPrediction(
            game_id=game_id,
            sport=game.sport if game else "NFL",
            home_team=home_team_name,
            away_team=away_team_name,
            game_date=game.start_time if game else datetime.utcnow(),
            market_type=result.get("market", "spread"),

            line_movement_edge=factors.get("line_movement", {}).get("edge"),
            line_movement_direction=factors.get("line_movement", {}).get("direction"),
            line_movement_signal=factors.get("line_movement", {}).get("signal"),

            coach_dna_edge=factors.get("coach_dna", {}).get("edge"),
            coach_dna_direction=factors.get("coach_dna", {}).get("direction"),
            coach_dna_signal=factors.get("coach_dna", {}).get("signal"),

            situational_edge=factors.get("situational", {}).get("edge"),
            situational_direction=factors.get("situational", {}).get("direction"),
            situational_signal=factors.get("situational", {}).get("signal"),

            weather_edge=factors.get("weather", {}).get("edge"),
            weather_direction=factors.get("weather", {}).get("direction"),
            weather_signal=factors.get("weather", {}).get("signal"),

            officials_edge=factors.get("officials", {}).get("edge"),
            officials_direction=factors.get("officials", {}).get("direction"),
            officials_signal=factors.get("officials", {}).get("signal"),

            public_fade_edge=factors.get("public_fade", {}).get("edge"),
            public_fade_direction=factors.get("public_fade", {}).get("direction"),
            public_fade_signal=factors.get("public_fade", {}).get("signal"),

            confirming_factors=analysis.get("confirming_factors"),
            conflicting_factors=analysis.get("conflicting_factors"),
            alignment_score=analysis.get("alignment_score"),

            predicted_side=prediction.get("side"),
            raw_edge=prediction.get("raw_edge_value"),
            confidence=prediction.get("confidence"),
            confidence_label=prediction.get("confidence_label"),
            recommendation=prediction.get("recommendation"),
            star_rating=prediction.get("star_rating"),
            explanation=result.get("explanation")
        )
        db.add(new_prediction)

    db.commit()


async def get_ranked_picks(
    db: Session,
    date: Optional[str] = None,
    sport: Optional[str] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Rank all games by edge strength.

    Only returns games from the next 48 hours to ensure we're showing
    actual upcoming games, not fake/old data.
    """
    from datetime import date as date_type

    # Get games for the next 48 hours only (today and tomorrow)
    now = datetime.utcnow()
    end = now + timedelta(hours=48)

    query = db.query(Game).filter(
        Game.start_time >= now,
        Game.start_time <= end
    )

    if sport:
        query = query.filter(Game.sport == sport)

    games = query.order_by(Game.start_time).limit(50).all()

    # Get predictions for each game
    picks = []
    for game in games:
        prediction = await get_unified_prediction(game.id, db)

        if "error" not in prediction:
            pred_data = prediction.get("prediction", {})

            picks.append({
                "game_id": game.id,
                "game": prediction.get("game"),
                "sport": prediction.get("sport"),
                "game_time": prediction.get("game_time"),
                "side": pred_data.get("side"),
                "edge": pred_data.get("raw_edge"),
                "edge_value": pred_data.get("raw_edge_value", 0),
                "confidence": pred_data.get("confidence"),
                "confidence_label": pred_data.get("confidence_label"),
                "star_rating": pred_data.get("star_rating"),
                "recommendation": pred_data.get("recommendation"),
                "unit_size": pred_data.get("unit_size"),
                "explanation": prediction.get("explanation")
            })

    # Sort by edge strength
    picks.sort(key=lambda x: x.get("edge_value", 0), reverse=True)

    # Add rank
    for i, pick in enumerate(picks):
        pick["rank"] = i + 1

    return picks[:limit]


async def get_top_picks(
    db: Session,
    sport: Optional[str] = None,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Get the best picks of the day.

    Only returns picks with actual positive edge (2%+) and
    recommendations of BET, STRONG BET, or LEAN.

    If no quality picks are found, returns empty list rather than
    showing picks with no edge.
    """
    picks = await get_ranked_picks(db, sport=sport, limit=20)

    # Filter to only picks with actual edge (2%+) and actionable recommendations
    top_picks = [
        p for p in picks
        if p.get("recommendation") in ["BET", "STRONG BET", "LEAN"]
        and p.get("edge_value", 0) >= 1.5  # At least 1.5% edge
    ][:limit]

    return top_picks


def calculate_confidence(
    factors: Dict[str, Dict],
    alignment: float
) -> float:
    """
    Calculate confidence based on:
    1. Number of confirming factors
    2. Strength of individual edges
    3. Sample size of historical data
    4. Signal alignment
    """
    # Base confidence from alignment
    base = alignment * 0.5

    # Add confidence from strong edges
    edge_bonus = 0
    for key, factor in factors.items():
        edge = factor.get("edge", 0)
        if edge > 3:
            edge_bonus += 0.08
        elif edge > 2:
            edge_bonus += 0.05
        elif edge > 1:
            edge_bonus += 0.02

    edge_bonus = min(0.3, edge_bonus)

    # Total confidence
    confidence = base + edge_bonus + 0.2  # +0.2 baseline

    return max(0.30, min(0.95, confidence))
