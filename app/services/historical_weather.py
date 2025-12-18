"""
Historical Weather Service

Fetches and stores historical weather data for past games.
Used for ML model training and backtesting weather impact predictions.
"""

from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
import logging
import asyncio

from app.db import GameWeather, WeatherImpactFactor, HistoricalGameResult, Venue
from app.services.weather import get_historical_weather, get_game_weather
from app.services.weather_impact import get_weather_impact, get_impact_summary
from app.data.venues import (
    get_venue_by_name,
    get_venue_coordinates,
    MLB_VENUES,
    NFL_VENUES,
    CFB_VENUES,
    SOCCER_VENUES,
)

logger = logging.getLogger(__name__)


async def fetch_historical_game_weather(
    db: Session,
    game_date: datetime,
    venue_name: str,
    sport: str,
    game_id: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """
    Fetch and store historical weather for a past game.

    Args:
        db: Database session
        game_date: Date and time of the game
        venue_name: Name of the venue
        sport: Sport code
        game_id: Optional game ID to link

    Returns:
        Weather data dict or None
    """
    # Find venue coordinates
    venue = get_venue_by_name(venue_name, sport)
    if not venue:
        coords = get_venue_coordinates(venue_name, sport)
        if coords:
            venue = {"lat": coords[0], "lon": coords[1], "name": venue_name}
        else:
            logger.warning(f"Could not find coordinates for venue: {venue_name}")
            return None

    # Fetch historical weather
    weather = await get_historical_weather(
        venue["lat"],
        venue["lon"],
        game_date.date(),
        game_date.hour
    )

    if not weather:
        logger.warning(f"Could not fetch weather for {venue_name} on {game_date}")
        return None

    # Store in database
    try:
        game_weather = GameWeather(
            game_id=game_id,
            sport=sport.upper(),
            game_date=game_date,
            temperature_f=weather.get("temperature_f"),
            humidity=weather.get("humidity"),
            precipitation_in=weather.get("precipitation_in"),
            rain_in=weather.get("rain_in"),
            snowfall_in=weather.get("snowfall_in"),
            weather_code=weather.get("weather_code"),
            conditions=weather.get("conditions"),
            wind_speed_mph=weather.get("wind_speed_mph"),
            wind_direction_degrees=weather.get("wind_direction_degrees"),
            wind_direction=weather.get("wind_direction"),
            wind_gusts_mph=weather.get("wind_gusts_mph"),
            weather_type="historical",
        )
        db.add(game_weather)
        db.commit()
        db.refresh(game_weather)

        # Calculate and store impact
        impact = get_weather_impact(sport, weather, venue)
        impact_factor = WeatherImpactFactor(
            game_weather_id=game_weather.id,
            game_id=game_id,
            sport=sport.upper(),
            total_adjustment=impact["total_adjustment"],
            scoring_factor=impact.get("scoring_factor", 1.0),
            hr_factor=impact.get("hr_factor"),
            pass_yards_factor=impact.get("pass_yards_factor"),
            rush_yards_factor=impact.get("rush_yards_factor"),
            turnover_factor=impact.get("turnover_factor"),
            goals_factor=impact.get("goals_factor"),
            recommendation=impact["recommendation"],
            confidence=impact["confidence"],
            factors=str(impact["factors"]),
        )
        db.add(impact_factor)
        db.commit()

        return {
            "weather": weather,
            "impact": impact,
            "stored": True,
        }

    except Exception as e:
        logger.error(f"Error storing weather data: {e}")
        db.rollback()
        return {
            "weather": weather,
            "impact": get_weather_impact(sport, weather, venue),
            "stored": False,
            "error": str(e),
        }


async def backfill_historical_weather(
    db: Session,
    sport: str,
    start_date: date,
    end_date: date,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Backfill weather data for historical games.

    Fetches weather for games in the date range that don't have weather data.

    Args:
        db: Database session
        sport: Sport code
        start_date: Start of date range
        end_date: End of date range
        limit: Maximum games to process

    Returns:
        Summary of backfill operation
    """
    # Get historical games without weather data
    games = db.query(HistoricalGameResult).filter(
        HistoricalGameResult.sport == sport.upper(),
        HistoricalGameResult.game_date >= datetime.combine(start_date, datetime.min.time()),
        HistoricalGameResult.game_date <= datetime.combine(end_date, datetime.max.time()),
        HistoricalGameResult.venue.isnot(None),
    ).limit(limit).all()

    logger.info(f"Found {len(games)} games to backfill weather for {sport}")

    results = {
        "total_games": len(games),
        "success": 0,
        "failed": 0,
        "skipped": 0,
    }

    for game in games:
        # Check if weather already exists
        existing = db.query(GameWeather).filter(
            GameWeather.game_id == game.id
        ).first()

        if existing:
            results["skipped"] += 1
            continue

        try:
            weather_result = await fetch_historical_game_weather(
                db=db,
                game_date=game.game_date,
                venue_name=game.venue,
                sport=sport,
                game_id=game.id
            )

            if weather_result and weather_result.get("stored"):
                results["success"] += 1
            else:
                results["failed"] += 1

            # Rate limit - don't hammer the API
            await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"Error backfilling weather for game {game.id}: {e}")
            results["failed"] += 1

    return results


async def analyze_weather_prediction_accuracy(
    db: Session,
    sport: str,
    min_games: int = 50
) -> Dict[str, Any]:
    """
    Analyze how accurate our weather impact predictions have been.

    Compares predicted total adjustments vs actual game scoring.

    Args:
        db: Database session
        sport: Sport code
        min_games: Minimum games required for analysis

    Returns:
        Accuracy analysis results
    """
    # Get games with both weather impact and results
    from sqlalchemy import and_

    results = db.query(
        WeatherImpactFactor,
        HistoricalGameResult
    ).join(
        HistoricalGameResult,
        WeatherImpactFactor.game_id == HistoricalGameResult.id
    ).filter(
        WeatherImpactFactor.sport == sport.upper(),
        HistoricalGameResult.total_points.isnot(None)
    ).all()

    if len(results) < min_games:
        return {
            "status": "insufficient_data",
            "games_found": len(results),
            "min_required": min_games,
        }

    # Analyze predictions
    over_predictions = []
    under_predictions = []
    neutral_predictions = []

    for impact, game in results:
        if impact.recommendation == "OVER" or impact.recommendation == "LEAN_OVER":
            over_predictions.append({
                "predicted_adjustment": impact.total_adjustment,
                "actual_total": game.total_points,
                "closing_total": game.closing_total,
            })
        elif impact.recommendation == "UNDER" or impact.recommendation == "LEAN_UNDER":
            under_predictions.append({
                "predicted_adjustment": impact.total_adjustment,
                "actual_total": game.total_points,
                "closing_total": game.closing_total,
            })
        else:
            neutral_predictions.append({
                "actual_total": game.total_points,
                "closing_total": game.closing_total,
            })

    # Calculate accuracy
    def calc_accuracy(predictions: List[Dict], direction: str) -> Dict[str, Any]:
        if not predictions:
            return {"count": 0}

        correct = 0
        for p in predictions:
            if p["closing_total"] is None:
                continue
            if direction == "over" and p["actual_total"] > p["closing_total"]:
                correct += 1
            elif direction == "under" and p["actual_total"] < p["closing_total"]:
                correct += 1

        valid = len([p for p in predictions if p["closing_total"] is not None])
        return {
            "count": len(predictions),
            "valid_count": valid,
            "correct": correct,
            "accuracy": correct / valid if valid > 0 else 0,
        }

    return {
        "sport": sport,
        "total_games_analyzed": len(results),
        "over_predictions": calc_accuracy(over_predictions, "over"),
        "under_predictions": calc_accuracy(under_predictions, "under"),
        "neutral_count": len(neutral_predictions),
        "analysis_date": datetime.now().isoformat(),
    }


def get_weather_edge_history(
    db: Session,
    sport: str,
    min_confidence: float = 0.6,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get historical weather edges and their outcomes.

    Args:
        db: Database session
        sport: Sport code
        min_confidence: Minimum confidence threshold
        limit: Maximum results

    Returns:
        List of weather edge results
    """
    from sqlalchemy import and_

    results = db.query(
        WeatherImpactFactor,
        HistoricalGameResult
    ).join(
        HistoricalGameResult,
        WeatherImpactFactor.game_id == HistoricalGameResult.id
    ).filter(
        and_(
            WeatherImpactFactor.sport == sport.upper(),
            WeatherImpactFactor.confidence >= min_confidence,
            HistoricalGameResult.total_points.isnot(None),
            HistoricalGameResult.closing_total.isnot(None)
        )
    ).order_by(
        HistoricalGameResult.game_date.desc()
    ).limit(limit).all()

    edges = []
    for impact, game in results:
        was_correct = False
        if impact.recommendation in ("OVER", "LEAN_OVER"):
            was_correct = game.total_points > game.closing_total
        elif impact.recommendation in ("UNDER", "LEAN_UNDER"):
            was_correct = game.total_points < game.closing_total

        edges.append({
            "game_date": game.game_date.isoformat(),
            "venue": game.venue,
            "total_adjustment": impact.total_adjustment,
            "recommendation": impact.recommendation,
            "confidence": impact.confidence,
            "closing_total": game.closing_total,
            "actual_total": game.total_points,
            "was_correct": was_correct,
        })

    return edges


def calculate_weather_edge_roi(
    db: Session,
    sport: str,
    min_confidence: float = 0.6
) -> Dict[str, Any]:
    """
    Calculate hypothetical ROI from following weather edge recommendations.

    Assumes flat betting on totals where weather suggests an edge.

    Args:
        db: Database session
        sport: Sport code
        min_confidence: Minimum confidence threshold

    Returns:
        ROI analysis
    """
    edges = get_weather_edge_history(db, sport, min_confidence, limit=500)

    if not edges:
        return {"status": "no_data"}

    total_bets = len(edges)
    wins = sum(1 for e in edges if e["was_correct"])
    losses = total_bets - wins

    # Assuming -110 odds (standard totals)
    win_payout = 0.9091  # $100 to win $90.91
    loss_payout = -1.0

    profit = (wins * win_payout) + (losses * loss_payout)
    roi = (profit / total_bets) * 100 if total_bets > 0 else 0

    return {
        "sport": sport,
        "total_bets": total_bets,
        "wins": wins,
        "losses": losses,
        "win_rate": wins / total_bets if total_bets > 0 else 0,
        "profit_units": round(profit, 2),
        "roi_percentage": round(roi, 2),
        "assumed_odds": -110,
    }
