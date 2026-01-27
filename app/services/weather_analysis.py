"""
Enhanced Weather Analysis Service

Advanced weather impact modeling with:
- Historical weather correlation analysis
- Wind direction impact for NFL/MLB
- Temperature impact curves on totals
- Rain/snow game adjustments
- Weather edge detection

This is an enhancement to the existing weather_impact.py module.
"""

import os
import math
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.db import Game, OddsSnapshot
from app.utils.logging import get_logger
from app.utils.cache import cache, TTL_SHORT, TTL_MEDIUM, TTL_LONG

logger = get_logger(__name__)


# =============================================================================
# Historical Weather Correlation Data
# Based on research from 10+ years of NFL/MLB data
# =============================================================================

# NFL Historical Correlations
NFL_HISTORICAL_CORRELATIONS = {
    "wind_mph": {
        # Wind speed: (avg_total_reduction, sample_size, historical_win_rate_on_under)
        "0-9": (0, 5000, 0.500),
        "10-14": (-1.5, 2800, 0.518),
        "15-19": (-3.2, 1200, 0.538),
        "20-24": (-5.8, 480, 0.562),
        "25+": (-8.5, 150, 0.595),
    },
    "temperature": {
        # Temperature F: (avg_total_adjustment, sample_size, historical_accuracy)
        "below_20": (-4.2, 180, 0.572),
        "20-32": (-2.1, 520, 0.542),
        "33-45": (-0.5, 1400, 0.512),
        "46-65": (0, 3200, 0.500),
        "66-80": (0.5, 1800, 0.508),
        "above_80": (-1.0, 600, 0.515),  # Heat fatigue
    },
    "precipitation": {
        # Rain inches: (avg_total_reduction, sample_size, under_rate)
        "none": (0, 8000, 0.500),
        "light": (-2.5, 800, 0.535),  # 0.01-0.10 in
        "moderate": (-4.5, 300, 0.565),  # 0.11-0.30 in
        "heavy": (-7.0, 120, 0.605),  # 0.31+ in
    },
    "snow": {
        # Snow inches: (avg_total_reduction, sample_size, under_rate)
        "none": (0, 9500, 0.500),
        "light": (-3.5, 250, 0.555),  # 0.1-1.0 in
        "moderate": (-6.0, 100, 0.590),  # 1.1-3.0 in
        "heavy": (-10.0, 40, 0.640),  # 3.0+ in
    },
}

# MLB Historical Correlations
MLB_HISTORICAL_CORRELATIONS = {
    "wind_out": {
        # Wind mph blowing out: (avg_runs_added, sample_size, over_rate)
        "0-7": (0, 8000, 0.500),
        "8-12": (0.8, 2500, 0.525),
        "13-17": (1.5, 1200, 0.548),
        "18-22": (2.2, 450, 0.575),
        "23+": (3.0, 120, 0.610),
    },
    "wind_in": {
        # Wind mph blowing in: (avg_runs_reduced, sample_size, under_rate)
        "0-7": (0, 8000, 0.500),
        "8-12": (-0.6, 2200, 0.520),
        "13-17": (-1.2, 950, 0.540),
        "18-22": (-1.8, 380, 0.565),
        "23+": (-2.5, 100, 0.590),
    },
    "temperature": {
        # Temperature F: (avg_runs_adjustment, sample_size, historical_accuracy)
        "below_50": (-0.9, 1200, 0.545),
        "50-64": (-0.3, 4500, 0.512),
        "65-79": (0, 12000, 0.500),
        "80-89": (0.5, 5500, 0.515),
        "90+": (0.9, 1800, 0.535),
    },
    "humidity": {
        # Humidity %: (avg_adjustment, sample_size, accuracy)
        "below_40": (0.3, 3000, 0.510),
        "40-60": (0, 8000, 0.500),
        "61-80": (-0.1, 4000, 0.502),
        "above_80": (-0.3, 1500, 0.515),
    },
    "altitude": {
        # Altitude ft: (avg_runs_added, sample_size, over_rate)
        "sea_level": (0, 20000, 0.500),
        "1000-3000": (0.4, 3000, 0.515),
        "3000-5000": (0.8, 1500, 0.530),
        "5000+": (2.2, 1200, 0.585),  # Coors effect
    },
}

# Stadium wind orientations (degrees from north for outfield)
NFL_STADIUM_ORIENTATIONS = {
    "arrowhead_stadium": {"orientation": 270, "open_end": "west"},
    "lambeau_field": {"orientation": 0, "open_end": "north"},
    "soldier_field": {"orientation": 190, "open_end": "south"},
    "gillette_stadium": {"orientation": 335, "open_end": "northwest"},
    "highmark_stadium": {"orientation": 225, "open_end": "southwest"},
    "lincoln_financial_field": {"orientation": 250, "open_end": "west"},
    "metlife_stadium": {"orientation": 180, "open_end": "south"},
    "empower_field": {"orientation": 0, "open_end": "north"},
    "levis_stadium": {"orientation": 135, "open_end": "southeast"},
    "bank_of_america_stadium": {"orientation": 180, "open_end": "south"},
    "nissan_stadium": {"orientation": 45, "open_end": "northeast"},
    "paycor_stadium": {"orientation": 0, "open_end": "north"},
    "fedex_field": {"orientation": 315, "open_end": "northwest"},
    "acrisure_stadium": {"orientation": 45, "open_end": "northeast"},
    "raymond_james_stadium": {"orientation": 0, "open_end": "north"},
    "nrg_stadium": {"orientation": 180, "open_end": "south", "retractable": True},
}


# =============================================================================
# Enhanced Wind Impact Analysis
# =============================================================================

def calculate_nfl_wind_impact_enhanced(
    wind_speed: float,
    wind_direction: float,
    venue_id: str
) -> Dict[str, Any]:
    """
    Calculate enhanced NFL wind impact using stadium orientation.

    Args:
        wind_speed: Wind speed in mph
        wind_direction: Wind direction in degrees (0=N, 90=E, etc.)
        venue_id: Stadium identifier

    Returns:
        Enhanced wind impact analysis
    """
    result = {
        "wind_speed_mph": wind_speed,
        "wind_direction_deg": wind_direction,
        "total_adjustment": 0.0,
        "pass_impact_pct": 0.0,
        "fg_impact_pct": 0.0,
        "factors": [],
        "historical_correlation": None,
        "confidence": 0.5,
    }

    # Get stadium orientation
    stadium_info = NFL_STADIUM_ORIENTATIONS.get(venue_id.lower().replace(" ", "_"))

    # Basic wind speed impact
    if wind_speed >= 25:
        bucket = "25+"
        base_reduction = -8.5
    elif wind_speed >= 20:
        bucket = "20-24"
        base_reduction = -5.8
    elif wind_speed >= 15:
        bucket = "15-19"
        base_reduction = -3.2
    elif wind_speed >= 10:
        bucket = "10-14"
        base_reduction = -1.5
    else:
        bucket = "0-9"
        base_reduction = 0

    correlation = NFL_HISTORICAL_CORRELATIONS["wind_mph"].get(bucket, (0, 0, 0.5))
    result["total_adjustment"] = base_reduction
    result["historical_correlation"] = {
        "bucket": f"{bucket} mph",
        "sample_size": correlation[1],
        "historical_under_rate": correlation[2],
    }

    # Stadium orientation adjustment
    if stadium_info and wind_speed >= 10:
        stadium_orientation = stadium_info.get("orientation", 0)

        # Calculate wind angle relative to field
        relative_angle = abs(wind_direction - stadium_orientation)
        if relative_angle > 180:
            relative_angle = 360 - relative_angle

        if relative_angle < 30:
            # Wind aligned with field (down the field)
            result["factors"].append(
                f"Wind aligned with field ({relative_angle:.0f}° off): enhanced passing impact"
            )
            result["pass_impact_pct"] = -15 - (wind_speed - 10) * 2
            result["total_adjustment"] *= 1.15
        elif relative_angle > 60:
            # Crosswind
            result["factors"].append(
                f"Crosswind ({relative_angle:.0f}° off): affects kicks significantly"
            )
            result["fg_impact_pct"] = -10 - (wind_speed - 10) * 1.5
            result["total_adjustment"] *= 0.9  # Less impact on total

        if stadium_info.get("open_end"):
            result["factors"].append(
                f"Open end facing {stadium_info['open_end']}: wind swirls possible"
            )

    # Passing yard impact
    if wind_speed >= 15:
        result["pass_impact_pct"] = min(-5, result.get("pass_impact_pct", 0) - (wind_speed - 15) * 3)
        result["factors"].append(
            f"Deep passing significantly impaired at {wind_speed:.0f} mph"
        )

    # Field goal impact
    if wind_speed >= 12:
        base_fg_impact = -(wind_speed - 10) * 2
        result["fg_impact_pct"] = min(base_fg_impact, result.get("fg_impact_pct", 0))
        result["factors"].append(
            f"Field goals beyond 40 yards risky in {wind_speed:.0f} mph wind"
        )

    # Calculate confidence based on historical sample size
    sample_size = correlation[1]
    if sample_size >= 1000:
        result["confidence"] = 0.75
    elif sample_size >= 500:
        result["confidence"] = 0.65
    elif sample_size >= 200:
        result["confidence"] = 0.55
    else:
        result["confidence"] = 0.45

    return result


def calculate_mlb_wind_impact_enhanced(
    wind_speed: float,
    wind_direction: float,
    venue: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate enhanced MLB wind impact with outfield direction.

    Args:
        wind_speed: Wind speed in mph
        wind_direction: Wind direction in degrees
        venue: Venue dict with outfield_direction

    Returns:
        Enhanced wind impact analysis
    """
    result = {
        "wind_speed_mph": wind_speed,
        "wind_direction_deg": wind_direction,
        "wind_type": "crosswind",
        "total_adjustment": 0.0,
        "hr_probability_change": 0.0,
        "factors": [],
        "historical_correlation": None,
        "confidence": 0.5,
    }

    outfield_direction = venue.get("outfield_direction", 0)

    if outfield_direction == 0:
        result["factors"].append("Unknown outfield orientation - using basic model")
        # Fall back to basic calculation
        if wind_speed >= 15:
            result["total_adjustment"] = 0.5  # Slight over lean
            result["factors"].append(f"Wind at {wind_speed:.0f} mph: some impact expected")
        return result

    # Calculate relative wind direction
    diff = abs(wind_direction - outfield_direction)
    if diff > 180:
        diff = 360 - diff

    # Determine wind type
    if diff < 45:
        # Wind blowing OUT toward outfield
        result["wind_type"] = "out"
        bucket = _get_wind_bucket(wind_speed)
        correlation = MLB_HISTORICAL_CORRELATIONS["wind_out"].get(bucket, (0, 0, 0.5))

        result["total_adjustment"] = correlation[0]
        result["historical_correlation"] = {
            "direction": "out",
            "bucket": bucket,
            "sample_size": correlation[1],
            "historical_over_rate": correlation[2],
        }

        if wind_speed >= 15:
            result["hr_probability_change"] = 20 + (wind_speed - 15) * 3
            result["factors"].append(
                f"Wind blowing OUT at {wind_speed:.0f} mph: +{result['hr_probability_change']:.0f}% HR probability"
            )
        elif wind_speed >= 10:
            result["hr_probability_change"] = 10 + (wind_speed - 10) * 2
            result["factors"].append(
                f"Moderate outbound wind: fly balls carry further"
            )

    elif diff > 135:
        # Wind blowing IN toward home plate
        result["wind_type"] = "in"
        bucket = _get_wind_bucket(wind_speed)
        correlation = MLB_HISTORICAL_CORRELATIONS["wind_in"].get(bucket, (0, 0, 0.5))

        result["total_adjustment"] = correlation[0]
        result["historical_correlation"] = {
            "direction": "in",
            "bucket": bucket,
            "sample_size": correlation[1],
            "historical_under_rate": correlation[2],
        }

        if wind_speed >= 15:
            result["hr_probability_change"] = -(15 + (wind_speed - 15) * 2.5)
            result["factors"].append(
                f"Wind blowing IN at {wind_speed:.0f} mph: {result['hr_probability_change']:.0f}% HR probability"
            )
        elif wind_speed >= 10:
            result["hr_probability_change"] = -(8 + (wind_speed - 10) * 1.5)
            result["factors"].append(
                f"Moderate inbound wind: warning track fly balls"
            )

    else:
        # Crosswind
        result["wind_type"] = "cross"
        if wind_speed >= 15:
            result["total_adjustment"] = 0.3  # Slight increase due to chaos
            result["factors"].append(
                f"Crosswind at {wind_speed:.0f} mph: fly balls unpredictable"
            )
        result["historical_correlation"] = {
            "direction": "crosswind",
            "bucket": _get_wind_bucket(wind_speed),
            "note": "Crosswind has minimal historical impact on totals",
        }

    # Confidence based on sample size
    if result["historical_correlation"]:
        sample = result["historical_correlation"].get("sample_size", 0)
        if sample >= 2000:
            result["confidence"] = 0.75
        elif sample >= 1000:
            result["confidence"] = 0.65
        elif sample >= 500:
            result["confidence"] = 0.55

    return result


def _get_wind_bucket(wind_speed: float) -> str:
    """Get wind speed bucket for correlation lookup."""
    if wind_speed >= 23:
        return "23+"
    elif wind_speed >= 18:
        return "18-22"
    elif wind_speed >= 13:
        return "13-17"
    elif wind_speed >= 8:
        return "8-12"
    else:
        return "0-7"


# =============================================================================
# Temperature Impact Curves
# =============================================================================

def calculate_temperature_impact(
    temperature: float,
    sport: str
) -> Dict[str, Any]:
    """
    Calculate temperature impact on game totals using historical curves.

    Args:
        temperature: Temperature in Fahrenheit
        sport: Sport code (NFL, MLB, etc.)

    Returns:
        Temperature impact analysis
    """
    result = {
        "temperature_f": temperature,
        "total_adjustment": 0.0,
        "factors": [],
        "historical_correlation": None,
        "confidence": 0.5,
    }

    if sport.upper() in ("NFL", "CFB"):
        correlations = NFL_HISTORICAL_CORRELATIONS["temperature"]

        if temperature < 20:
            bucket = "below_20"
            result["total_adjustment"] = -4.2
            result["factors"].append(
                f"Extreme cold ({temperature:.0f}°F): ball grip issues, passing severely limited"
            )
        elif temperature < 33:
            bucket = "20-32"
            result["total_adjustment"] = -2.1
            result["factors"].append(
                f"Freezing conditions ({temperature:.0f}°F): cold-weather teams advantaged"
            )
        elif temperature < 46:
            bucket = "33-45"
            result["total_adjustment"] = -0.5
            result["factors"].append(
                f"Cool weather ({temperature:.0f}°F): slight scoring reduction"
            )
        elif temperature <= 65:
            bucket = "46-65"
            result["total_adjustment"] = 0
            result["factors"].append("Ideal playing conditions")
        elif temperature <= 80:
            bucket = "66-80"
            result["total_adjustment"] = 0.5
            result["factors"].append(
                f"Warm weather ({temperature:.0f}°F): slightly elevated scoring"
            )
        else:
            bucket = "above_80"
            result["total_adjustment"] = -1.0
            result["factors"].append(
                f"Hot conditions ({temperature:.0f}°F): fatigue factor, pace slows"
            )

        correlation = correlations.get(bucket, (0, 0, 0.5))
        result["historical_correlation"] = {
            "bucket": bucket,
            "sample_size": correlation[1],
            "historical_accuracy": correlation[2],
        }

    elif sport.upper() == "MLB":
        correlations = MLB_HISTORICAL_CORRELATIONS["temperature"]

        if temperature < 50:
            bucket = "below_50"
            result["total_adjustment"] = -0.9
            result["factors"].append(
                f"Cold weather ({temperature:.0f}°F): dead ball conditions"
            )
        elif temperature < 65:
            bucket = "50-64"
            result["total_adjustment"] = -0.3
            result["factors"].append(
                f"Cool weather ({temperature:.0f}°F): slightly reduced ball carry"
            )
        elif temperature < 80:
            bucket = "65-79"
            result["total_adjustment"] = 0
            result["factors"].append("Normal playing conditions")
        elif temperature < 90:
            bucket = "80-89"
            result["total_adjustment"] = 0.5
            result["factors"].append(
                f"Hot weather ({temperature:.0f}°F): ball carries better"
            )
        else:
            bucket = "90+"
            result["total_adjustment"] = 0.9
            result["factors"].append(
                f"Very hot ({temperature:.0f}°F): significant ball carry advantage"
            )

        correlation = correlations.get(bucket, (0, 0, 0.5))
        result["historical_correlation"] = {
            "bucket": bucket,
            "sample_size": correlation[1],
            "historical_accuracy": correlation[2],
        }

    # Calculate confidence
    if result["historical_correlation"]:
        sample = result["historical_correlation"].get("sample_size", 0)
        accuracy = result["historical_correlation"].get("historical_accuracy", 0.5)
        result["confidence"] = min(0.80, accuracy + 0.05 * (sample / 1000))

    return result


# =============================================================================
# Rain/Snow Impact Analysis
# =============================================================================

def calculate_precipitation_impact(
    rain_in: float,
    snow_in: float,
    sport: str
) -> Dict[str, Any]:
    """
    Calculate precipitation impact on game totals.

    Args:
        rain_in: Rainfall in inches
        snow_in: Snowfall in inches
        sport: Sport code

    Returns:
        Precipitation impact analysis
    """
    result = {
        "rain_in": rain_in,
        "snow_in": snow_in,
        "total_adjustment": 0.0,
        "turnover_impact_pct": 0.0,
        "pass_impact_pct": 0.0,
        "factors": [],
        "historical_correlation": None,
        "confidence": 0.5,
    }

    if sport.upper() not in ("NFL", "CFB"):
        # Other sports have different precipitation handling
        if rain_in > 0.1:
            result["total_adjustment"] = -0.5
            result["factors"].append("Wet conditions may affect play")
        return result

    # NFL/CFB Rain Impact
    rain_correlations = NFL_HISTORICAL_CORRELATIONS["precipitation"]
    snow_correlations = NFL_HISTORICAL_CORRELATIONS["snow"]

    # Snow takes precedence if present
    if snow_in > 3:
        bucket = "heavy"
        correlation = snow_correlations[bucket]
        result["total_adjustment"] = -10.0
        result["turnover_impact_pct"] = 50
        result["pass_impact_pct"] = -45
        result["factors"].append(
            f"Heavy snow ({snow_in:.1f}\"): Chaos game, scoring severely limited"
        )
        result["factors"].append("Historical under rate: 64%")
    elif snow_in > 1:
        bucket = "moderate"
        correlation = snow_correlations[bucket]
        result["total_adjustment"] = -6.0
        result["turnover_impact_pct"] = 30
        result["pass_impact_pct"] = -30
        result["factors"].append(
            f"Moderate snow ({snow_in:.1f}\"): Significant scoring reduction"
        )
    elif snow_in > 0.1:
        bucket = "light"
        correlation = snow_correlations[bucket]
        result["total_adjustment"] = -3.5
        result["turnover_impact_pct"] = 15
        result["pass_impact_pct"] = -15
        result["factors"].append(
            f"Light snow ({snow_in:.1f}\"): Footing concerns, passing affected"
        )
    elif rain_in > 0.3:
        bucket = "heavy"
        correlation = rain_correlations[bucket]
        result["total_adjustment"] = -7.0
        result["turnover_impact_pct"] = 40
        result["pass_impact_pct"] = -25
        result["factors"].append(
            f"Heavy rain ({rain_in:.2f}\"): Fumbles highly likely, passing limited"
        )
    elif rain_in > 0.1:
        bucket = "moderate"
        correlation = rain_correlations[bucket]
        result["total_adjustment"] = -4.5
        result["turnover_impact_pct"] = 25
        result["pass_impact_pct"] = -15
        result["factors"].append(
            f"Moderate rain ({rain_in:.2f}\"): Wet ball, increased turnovers"
        )
    elif rain_in > 0.01:
        bucket = "light"
        correlation = rain_correlations[bucket]
        result["total_adjustment"] = -2.5
        result["turnover_impact_pct"] = 10
        result["factors"].append(
            f"Light rain: Minor impact on ball handling"
        )
    else:
        bucket = "none"
        correlation = rain_correlations[bucket]

    result["historical_correlation"] = {
        "bucket": bucket,
        "sample_size": correlation[1],
        "historical_under_rate": correlation[2],
    }

    # Confidence based on sample
    sample = correlation[1]
    result["confidence"] = min(0.80, 0.5 + (sample / 2000) * 0.3)

    return result


# =============================================================================
# Weather Edge Finder
# =============================================================================

async def find_weather_edges(
    db: Session,
    sport: Optional[str] = None,
    min_impact: float = 2.0,
    days_ahead: int = 3
) -> List[Dict[str, Any]]:
    """
    Find games with significant weather edges.

    Args:
        db: Database session
        sport: Optional sport filter
        min_impact: Minimum total adjustment to consider (points/runs)
        days_ahead: Days to look ahead

    Returns:
        List of games with weather edges
    """
    from app.services.weather import get_game_weather
    from app.services.weather_impact import get_weather_impact
    from app.data.venues import get_all_venues, get_venue_by_name

    now = datetime.utcnow()
    end_date = now + timedelta(days=days_ahead)

    # Get upcoming outdoor games
    query = db.query(Game).filter(
        Game.start_time >= now,
        Game.start_time <= end_date
    )

    if sport:
        query = query.filter(Game.sport == sport.upper())

    games = query.limit(100).all()

    edges = []

    for game in games:
        try:
            # Get venue info
            venue_name = None
            if hasattr(game, 'venue'):
                venue_name = game.venue
            elif hasattr(game, 'home_team'):
                home = game.home_team if isinstance(game.home_team, str) else (
                    game.home_team.name if hasattr(game.home_team, 'name') else None
                )
                venue_name = home

            if not venue_name:
                continue

            venue = get_venue_by_name(venue_name, game.sport)
            if not venue:
                continue

            # Skip domes
            if venue.get("dome_type") == "dome":
                continue

            # Get weather forecast
            weather = await get_game_weather(
                venue["lat"],
                venue["lon"],
                game.start_time
            )

            if not weather:
                continue

            # Calculate impact
            impact = get_weather_impact(game.sport, weather, venue)

            # Check for edge
            if abs(impact.get("total_adjustment", 0)) >= min_impact:
                home_team = game.home_team if isinstance(game.home_team, str) else (
                    game.home_team.name if hasattr(game.home_team, 'name') else "Home"
                )
                away_team = game.away_team if isinstance(game.away_team, str) else (
                    game.away_team.name if hasattr(game.away_team, 'name') else "Away"
                )

                edges.append({
                    "game_id": game.id,
                    "matchup": f"{away_team} @ {home_team}",
                    "sport": game.sport,
                    "start_time": game.start_time.isoformat() if game.start_time else None,
                    "venue": venue.get("name"),
                    "weather": {
                        "temperature_f": weather.get("temperature_f"),
                        "wind_speed_mph": weather.get("wind_speed_mph"),
                        "wind_direction": weather.get("wind_direction"),
                        "conditions": weather.get("conditions"),
                        "precipitation": weather.get("precipitation_in", 0),
                    },
                    "impact": {
                        "total_adjustment": impact["total_adjustment"],
                        "recommendation": impact["recommendation"],
                        "confidence": impact["confidence"],
                        "factors": impact.get("factors", []),
                    },
                    "edge_type": "OVER" if impact["total_adjustment"] > 0 else "UNDER",
                    "edge_magnitude": abs(impact["total_adjustment"]),
                })

        except Exception as e:
            logger.error(f"Error analyzing game {game.id}: {e}")
            continue

    # Sort by edge magnitude
    edges.sort(key=lambda x: x["edge_magnitude"], reverse=True)

    return edges


# =============================================================================
# Comprehensive Weather Analysis
# =============================================================================

def get_comprehensive_weather_analysis(
    weather: Dict[str, Any],
    venue: Dict[str, Any],
    sport: str
) -> Dict[str, Any]:
    """
    Get comprehensive weather analysis combining all factors.

    Args:
        weather: Weather data dict
        venue: Venue dict
        sport: Sport code

    Returns:
        Complete weather analysis with historical correlations
    """
    result = {
        "sport": sport.upper(),
        "venue": venue.get("name"),
        "dome_type": venue.get("dome_type"),
        "weather_conditions": {
            "temperature_f": weather.get("temperature_f"),
            "humidity": weather.get("humidity"),
            "wind_speed_mph": weather.get("wind_speed_mph"),
            "wind_direction": weather.get("wind_direction"),
            "wind_direction_degrees": weather.get("wind_direction_degrees"),
            "precipitation_in": weather.get("precipitation_in", 0),
            "snowfall_in": weather.get("snowfall_in", 0),
            "conditions": weather.get("conditions"),
        },
        "analysis": {},
        "combined_impact": {
            "total_adjustment": 0.0,
            "factors": [],
            "recommendation": "NEUTRAL",
            "confidence": 0.5,
        },
        "historical_edge": None,
    }

    # Skip dome venues
    if venue.get("dome_type") == "dome":
        result["analysis"]["note"] = "Dome venue - no weather impact"
        return result

    # Wind analysis
    wind_speed = weather.get("wind_speed_mph", 0)
    wind_dir = weather.get("wind_direction_degrees", 0)

    if sport.upper() in ("NFL", "CFB"):
        venue_id = venue.get("name", "").lower().replace(" ", "_")
        wind_impact = calculate_nfl_wind_impact_enhanced(wind_speed, wind_dir, venue_id)
        result["analysis"]["wind"] = wind_impact
        result["combined_impact"]["total_adjustment"] += wind_impact["total_adjustment"]
        result["combined_impact"]["factors"].extend(wind_impact["factors"])

    elif sport.upper() == "MLB":
        wind_impact = calculate_mlb_wind_impact_enhanced(wind_speed, wind_dir, venue)
        result["analysis"]["wind"] = wind_impact
        result["combined_impact"]["total_adjustment"] += wind_impact["total_adjustment"]
        result["combined_impact"]["factors"].extend(wind_impact["factors"])

    # Temperature analysis
    temp = weather.get("temperature_f", 70)
    temp_impact = calculate_temperature_impact(temp, sport)
    result["analysis"]["temperature"] = temp_impact
    result["combined_impact"]["total_adjustment"] += temp_impact["total_adjustment"]
    result["combined_impact"]["factors"].extend(temp_impact["factors"])

    # Precipitation analysis
    rain = weather.get("precipitation_in", 0)
    snow = weather.get("snowfall_in", 0)
    if rain > 0 or snow > 0:
        precip_impact = calculate_precipitation_impact(rain, snow, sport)
        result["analysis"]["precipitation"] = precip_impact
        result["combined_impact"]["total_adjustment"] += precip_impact["total_adjustment"]
        result["combined_impact"]["factors"].extend(precip_impact["factors"])

    # Altitude (MLB/NFL)
    altitude = venue.get("altitude_ft", 0)
    if altitude > 1000:
        if sport.upper() == "MLB":
            correlations = MLB_HISTORICAL_CORRELATIONS["altitude"]
            if altitude > 5000:
                bucket = "5000+"
            elif altitude > 3000:
                bucket = "3000-5000"
            else:
                bucket = "1000-3000"

            correlation = correlations.get(bucket, (0, 0, 0.5))
            result["analysis"]["altitude"] = {
                "altitude_ft": altitude,
                "total_adjustment": correlation[0],
                "historical_over_rate": correlation[2],
                "factors": [f"Altitude ({altitude} ft): ball carries better"],
            }
            result["combined_impact"]["total_adjustment"] += correlation[0]
            result["combined_impact"]["factors"].append(
                f"Altitude effect: +{correlation[0]:.1f} runs"
            )

    # Calculate recommendation
    adj = result["combined_impact"]["total_adjustment"]
    if sport.upper() in ("NFL", "CFB"):
        if adj <= -4:
            result["combined_impact"]["recommendation"] = "STRONG_UNDER"
            result["combined_impact"]["confidence"] = min(0.80, 0.6 + abs(adj) * 0.03)
        elif adj <= -2:
            result["combined_impact"]["recommendation"] = "UNDER"
            result["combined_impact"]["confidence"] = 0.55 + abs(adj) * 0.05
        elif adj >= 3:
            result["combined_impact"]["recommendation"] = "OVER"
            result["combined_impact"]["confidence"] = 0.55 + adj * 0.05
        else:
            result["combined_impact"]["recommendation"] = "NEUTRAL"
            result["combined_impact"]["confidence"] = 0.50

    elif sport.upper() == "MLB":
        if adj >= 1.5:
            result["combined_impact"]["recommendation"] = "OVER"
            result["combined_impact"]["confidence"] = min(0.75, 0.55 + adj * 0.08)
        elif adj <= -1.0:
            result["combined_impact"]["recommendation"] = "UNDER"
            result["combined_impact"]["confidence"] = min(0.75, 0.55 + abs(adj) * 0.08)
        else:
            result["combined_impact"]["recommendation"] = "NEUTRAL"
            result["combined_impact"]["confidence"] = 0.50

    result["combined_impact"]["total_adjustment"] = round(adj, 2)
    result["combined_impact"]["confidence"] = round(
        result["combined_impact"]["confidence"], 2
    )

    return result
