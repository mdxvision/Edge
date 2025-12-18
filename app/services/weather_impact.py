"""
Weather Impact Calculation Service

THE SECRET SAUCE: Calculate how weather conditions affect game outcomes
and betting lines for different sports.

This is where EdgeBet provides real edge - not just weather data,
but models that predict how weather affects game outcomes.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import logging

from app.data.venues import (
    MLB_VENUES, NFL_VENUES, SOCCER_VENUES, CFB_VENUES,
    OUTDOOR, DOME, RETRACTABLE,
    get_venue_by_name, get_venue_by_team_abbr, is_dome_venue
)

logger = logging.getLogger(__name__)


# =============================================================================
# WIND DIRECTION CALCULATIONS
# =============================================================================

def is_wind_blowing_out(wind_direction_degrees: float, venue: Dict[str, Any]) -> bool:
    """
    Calculate if wind is blowing toward outfield (helps HRs in baseball).
    Each ballpark has different orientation.

    Args:
        wind_direction_degrees: Wind direction in degrees (0=N, 90=E, 180=S, 270=W)
        venue: Venue dict with outfield_direction

    Returns:
        True if wind is blowing out toward outfield
    """
    outfield_direction = venue.get("outfield_direction", 0)
    if outfield_direction == 0:
        return False  # Unknown orientation

    # Wind is "out" if within 45 degrees of outfield direction
    diff = abs(wind_direction_degrees - outfield_direction)
    if diff > 180:
        diff = 360 - diff

    return diff < 45


def is_wind_blowing_in(wind_direction_degrees: float, venue: Dict[str, Any]) -> bool:
    """
    Calculate if wind is blowing toward home plate (hurts HRs in baseball).

    Args:
        wind_direction_degrees: Wind direction in degrees
        venue: Venue dict with outfield_direction

    Returns:
        True if wind is blowing in from outfield
    """
    outfield_direction = venue.get("outfield_direction", 0)
    if outfield_direction == 0:
        return False

    # Inward wind is opposite of outfield direction
    inward_direction = (outfield_direction + 180) % 360

    diff = abs(wind_direction_degrees - inward_direction)
    if diff > 180:
        diff = 360 - diff

    return diff < 45


def is_wind_crosswind(wind_direction_degrees: float, venue: Dict[str, Any]) -> bool:
    """Check if wind is blowing across the field (perpendicular to outfield)."""
    outfield_direction = venue.get("outfield_direction", 0)
    if outfield_direction == 0:
        return True  # Assume crosswind if unknown

    # Crosswind is 90 degrees off from outfield direction
    diff = abs(wind_direction_degrees - outfield_direction)
    if diff > 180:
        diff = 360 - diff

    return 45 <= diff <= 135


# =============================================================================
# MLB WEATHER IMPACT
# =============================================================================

def calculate_mlb_impact(
    weather: Dict[str, Any],
    venue: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate weather impact for MLB games.

    This is the SECRET SAUCE for baseball betting.
    Factors in wind direction, temperature, humidity, altitude.

    Args:
        weather: Weather data dict with temperature_f, wind_speed_mph, etc.
        venue: Venue dict with altitude_ft, outfield_direction, dome_type

    Returns:
        Impact analysis with adjustments and recommendations
    """
    impact = {
        "total_adjustment": 0.0,  # +/- runs from base total
        "hr_factor": 1.0,  # Multiplier for HR probability
        "scoring_factor": 1.0,  # Overall scoring multiplier
        "factors": [],
        "recommendation": "NEUTRAL",
        "confidence": 0.5,
        "sport": "MLB",
    }

    # Check if dome - no weather impact
    if venue.get("dome_type") == DOME:
        impact["factors"].append("Dome game - no weather impact")
        return impact

    # Retractable roof - assume closed in bad weather
    if venue.get("dome_type") == RETRACTABLE:
        # Check for rain/cold that would trigger closed roof
        if weather.get("rain_in", 0) > 0 or weather.get("temperature_f", 70) < 50:
            impact["factors"].append("Retractable roof likely closed - reduced weather impact")
            # Still apply some effects but reduced
            pass

    wind_speed = weather.get("wind_speed_mph", 0)
    wind_dir = weather.get("wind_direction_degrees", 0)
    temp = weather.get("temperature_f", 70)
    humidity = weather.get("humidity", 50)
    altitude = venue.get("altitude_ft", 0)

    # ==========================================================================
    # WIND IMPACT (HUGE for baseball)
    # ==========================================================================

    # Wind blowing out (increases HRs significantly)
    if is_wind_blowing_out(wind_dir, venue):
        if wind_speed > 20:
            impact["total_adjustment"] += 2.0
            impact["hr_factor"] += 0.35
            impact["scoring_factor"] += 0.15
            impact["factors"].append(
                f"Strong wind blowing out at {wind_speed:.0f} mph: +2.0 runs, +35% HR probability"
            )
        elif wind_speed > 15:
            impact["total_adjustment"] += 1.5
            impact["hr_factor"] += 0.25
            impact["factors"].append(
                f"Wind blowing out at {wind_speed:.0f} mph: +1.5 runs, +25% HR probability"
            )
        elif wind_speed > 10:
            impact["total_adjustment"] += 0.75
            impact["hr_factor"] += 0.15
            impact["factors"].append(
                f"Light wind blowing out at {wind_speed:.0f} mph: +0.75 runs"
            )

    # Wind blowing in (decreases HRs)
    elif is_wind_blowing_in(wind_dir, venue):
        if wind_speed > 20:
            impact["total_adjustment"] -= 2.0
            impact["hr_factor"] -= 0.30
            impact["scoring_factor"] -= 0.10
            impact["factors"].append(
                f"Strong wind blowing in at {wind_speed:.0f} mph: -2.0 runs, -30% HR probability"
            )
        elif wind_speed > 15:
            impact["total_adjustment"] -= 1.5
            impact["hr_factor"] -= 0.20
            impact["factors"].append(
                f"Wind blowing in at {wind_speed:.0f} mph: -1.5 runs, -20% HR probability"
            )
        elif wind_speed > 10:
            impact["total_adjustment"] -= 0.75
            impact["hr_factor"] -= 0.10
            impact["factors"].append(
                f"Light wind blowing in at {wind_speed:.0f} mph: -0.75 runs"
            )

    # Crosswind (affects fly balls unpredictably)
    elif is_wind_crosswind(wind_dir, venue) and wind_speed > 15:
        impact["factors"].append(
            f"Crosswind at {wind_speed:.0f} mph: fly balls harder to track, slightly increases scoring"
        )
        impact["total_adjustment"] += 0.25

    # ==========================================================================
    # TEMPERATURE IMPACT
    # ==========================================================================

    if temp > 90:
        impact["total_adjustment"] += 0.75
        impact["hr_factor"] += 0.10
        impact["factors"].append(
            f"Very hot weather ({temp:.0f}°F): ball carries better, +0.75 runs"
        )
    elif temp > 85:
        impact["total_adjustment"] += 0.5
        impact["factors"].append(
            f"Hot weather ({temp:.0f}°F): ball carries +0.5 runs"
        )
    elif temp < 45:
        impact["total_adjustment"] -= 1.0
        impact["hr_factor"] -= 0.15
        impact["factors"].append(
            f"Cold weather ({temp:.0f}°F): dead ball, pitcher advantage, -1.0 runs"
        )
    elif temp < 55:
        impact["total_adjustment"] -= 0.5
        impact["hr_factor"] -= 0.08
        impact["factors"].append(
            f"Cool weather ({temp:.0f}°F): slightly dead ball, -0.5 runs"
        )

    # ==========================================================================
    # HUMIDITY IMPACT
    # ==========================================================================

    if humidity > 85:
        impact["total_adjustment"] -= 0.25
        impact["factors"].append(
            f"Very high humidity ({humidity}%): heavier air, pitcher grip affected"
        )
    elif humidity < 30:
        impact["total_adjustment"] += 0.25
        impact["hr_factor"] += 0.05
        impact["factors"].append(
            f"Low humidity ({humidity}%): ball carries slightly better"
        )

    # ==========================================================================
    # ALTITUDE IMPACT (Coors Field special case)
    # ==========================================================================

    if altitude > 5000:
        # Coors Field at 5200 ft
        impact["total_adjustment"] += 2.0
        impact["hr_factor"] += 0.40
        impact["factors"].append(
            f"High altitude ({altitude} ft): thin air significantly increases scoring +2.0 runs"
        )
    elif altitude > 3000:
        impact["total_adjustment"] += 0.75
        impact["hr_factor"] += 0.15
        impact["factors"].append(
            f"Elevated altitude ({altitude} ft): ball carries better +0.75 runs"
        )
    elif altitude > 1000:
        impact["total_adjustment"] += 0.25
        impact["factors"].append(
            f"Moderate altitude ({altitude} ft): slight ball carry advantage"
        )

    # ==========================================================================
    # RAIN IMPACT
    # ==========================================================================

    if weather.get("rain_in", 0) > 0.1:
        impact["total_adjustment"] -= 0.5
        impact["factors"].append(
            "Active rain: slippery conditions, game pace affected"
        )

    # ==========================================================================
    # CALCULATE RECOMMENDATION
    # ==========================================================================

    if impact["total_adjustment"] >= 1.5:
        impact["recommendation"] = "OVER"
        impact["confidence"] = min(0.85, 0.6 + abs(impact["total_adjustment"]) * 0.1)
    elif impact["total_adjustment"] <= -1.5:
        impact["recommendation"] = "UNDER"
        impact["confidence"] = min(0.85, 0.6 + abs(impact["total_adjustment"]) * 0.1)
    elif impact["total_adjustment"] >= 0.75:
        impact["recommendation"] = "LEAN_OVER"
        impact["confidence"] = 0.55 + abs(impact["total_adjustment"]) * 0.05
    elif impact["total_adjustment"] <= -0.75:
        impact["recommendation"] = "LEAN_UNDER"
        impact["confidence"] = 0.55 + abs(impact["total_adjustment"]) * 0.05
    else:
        impact["recommendation"] = "NEUTRAL"
        impact["confidence"] = 0.5

    # Round values
    impact["total_adjustment"] = round(impact["total_adjustment"], 2)
    impact["hr_factor"] = round(impact["hr_factor"], 2)
    impact["scoring_factor"] = round(impact["scoring_factor"], 2)
    impact["confidence"] = round(impact["confidence"], 2)

    return impact


# =============================================================================
# NFL WEATHER IMPACT
# =============================================================================

def calculate_nfl_impact(
    weather: Dict[str, Any],
    venue: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate weather impact for NFL games.

    Wind and precipitation dramatically affect passing games.
    Cold weather benefits cold-weather teams.

    Args:
        weather: Weather data dict
        venue: Venue dict

    Returns:
        Impact analysis
    """
    impact = {
        "total_adjustment": 0.0,  # +/- points from base total
        "pass_yards_factor": 1.0,  # Multiplier for passing yards
        "rush_yards_factor": 1.0,  # Multiplier for rushing yards
        "turnover_factor": 1.0,  # Multiplier for turnover probability
        "scoring_factor": 1.0,
        "factors": [],
        "recommendation": "NEUTRAL",
        "confidence": 0.5,
        "sport": "NFL",
    }

    # Check if dome - no weather impact
    if venue.get("dome_type") == DOME:
        impact["factors"].append("Dome game - no weather impact")
        return impact

    # Retractable roof - likely closed in bad weather
    if venue.get("dome_type") == RETRACTABLE:
        if (weather.get("rain_in", 0) > 0.1 or
            weather.get("temperature_f", 70) < 40 or
            weather.get("wind_speed_mph", 0) > 20):
            impact["factors"].append("Retractable roof likely closed - minimal weather impact")
            return impact

    wind_speed = weather.get("wind_speed_mph", 0)
    temp = weather.get("temperature_f", 70)
    rain = weather.get("rain_in", 0)
    snow = weather.get("snowfall_in", 0)

    # ==========================================================================
    # WIND IMPACT (Critical for passing)
    # ==========================================================================

    if wind_speed > 25:
        impact["total_adjustment"] -= 6
        impact["pass_yards_factor"] -= 0.35
        impact["rush_yards_factor"] += 0.15
        impact["factors"].append(
            f"Severe wind ({wind_speed:.0f} mph): passing game devastated, -6 points expected"
        )
    elif wind_speed > 20:
        impact["total_adjustment"] -= 4
        impact["pass_yards_factor"] -= 0.25
        impact["rush_yards_factor"] += 0.10
        impact["factors"].append(
            f"High wind ({wind_speed:.0f} mph): passing severely impacted, -4 points"
        )
    elif wind_speed > 15:
        impact["total_adjustment"] -= 2
        impact["pass_yards_factor"] -= 0.15
        impact["factors"].append(
            f"Windy ({wind_speed:.0f} mph): deep passing affected, -2 points"
        )
    elif wind_speed > 10:
        impact["total_adjustment"] -= 0.5
        impact["pass_yards_factor"] -= 0.05
        impact["factors"].append(
            f"Breezy ({wind_speed:.0f} mph): slight impact on long passes"
        )

    # ==========================================================================
    # PRECIPITATION IMPACT
    # ==========================================================================

    if rain > 0.3:
        impact["total_adjustment"] -= 5
        impact["turnover_factor"] += 0.35
        impact["pass_yards_factor"] -= 0.20
        impact["factors"].append(
            "Heavy rain: fumbles highly likely, passing limited, -5 points"
        )
    elif rain > 0.1:
        impact["total_adjustment"] -= 3
        impact["turnover_factor"] += 0.20
        impact["factors"].append(
            "Rain: increased fumble risk, wet ball affects passing, -3 points"
        )
    elif rain > 0:
        impact["total_adjustment"] -= 1
        impact["turnover_factor"] += 0.10
        impact["factors"].append(
            "Light rain: slight fumble risk, -1 point"
        )

    # ==========================================================================
    # SNOW IMPACT (Major factor)
    # ==========================================================================

    if snow > 3:
        impact["total_adjustment"] -= 8
        impact["turnover_factor"] += 0.40
        impact["pass_yards_factor"] -= 0.40
        impact["rush_yards_factor"] -= 0.15
        impact["factors"].append(
            "Heavy snow: scoring significantly reduced, high chaos factor, -8 points"
        )
    elif snow > 1:
        impact["total_adjustment"] -= 5
        impact["turnover_factor"] += 0.25
        impact["pass_yards_factor"] -= 0.25
        impact["factors"].append(
            "Snow: footing issues, passing limited, -5 points"
        )
    elif snow > 0:
        impact["total_adjustment"] -= 2
        impact["factors"].append(
            "Light snow: minor impact on play, -2 points"
        )

    # ==========================================================================
    # TEMPERATURE IMPACT
    # ==========================================================================

    if temp < 20:
        impact["total_adjustment"] -= 3
        impact["turnover_factor"] += 0.15
        impact["factors"].append(
            f"Extreme cold ({temp:.0f}°F): ball harder to grip, dome teams disadvantaged"
        )
    elif temp < 32:
        impact["total_adjustment"] -= 1.5
        impact["factors"].append(
            f"Freezing conditions ({temp:.0f}°F): cold-weather advantage"
        )
    elif temp > 90:
        impact["total_adjustment"] -= 1
        impact["factors"].append(
            f"Extreme heat ({temp:.0f}°F): fatigue factor, pace may slow"
        )

    # ==========================================================================
    # ALTITUDE IMPACT (Denver)
    # ==========================================================================

    altitude = venue.get("altitude_ft", 0)
    if altitude > 5000:
        impact["total_adjustment"] += 2
        impact["factors"].append(
            f"High altitude ({altitude} ft): visiting team fatigue, kicking affected"
        )

    # ==========================================================================
    # CALCULATE RECOMMENDATION
    # ==========================================================================

    if impact["total_adjustment"] >= 3:
        impact["recommendation"] = "OVER"
        impact["confidence"] = min(0.80, 0.55 + abs(impact["total_adjustment"]) * 0.04)
    elif impact["total_adjustment"] <= -4:
        impact["recommendation"] = "UNDER"
        impact["confidence"] = min(0.85, 0.6 + abs(impact["total_adjustment"]) * 0.03)
    elif impact["total_adjustment"] <= -2:
        impact["recommendation"] = "LEAN_UNDER"
        impact["confidence"] = 0.55 + abs(impact["total_adjustment"]) * 0.03
    else:
        impact["recommendation"] = "NEUTRAL"
        impact["confidence"] = 0.5

    # Round values
    impact["total_adjustment"] = round(impact["total_adjustment"], 2)
    impact["pass_yards_factor"] = round(impact["pass_yards_factor"], 2)
    impact["rush_yards_factor"] = round(impact["rush_yards_factor"], 2)
    impact["turnover_factor"] = round(impact["turnover_factor"], 2)
    impact["confidence"] = round(impact["confidence"], 2)

    return impact


# =============================================================================
# SOCCER WEATHER IMPACT
# =============================================================================

def calculate_soccer_impact(
    weather: Dict[str, Any],
    venue: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate weather impact for Soccer matches.

    Rain creates slippery conditions and faster ball movement.
    Wind affects long passes and crosses.

    Args:
        weather: Weather data dict
        venue: Venue dict

    Returns:
        Impact analysis
    """
    impact = {
        "total_adjustment": 0.0,  # +/- goals from base total
        "goals_factor": 1.0,
        "scoring_factor": 1.0,
        "factors": [],
        "recommendation": "NEUTRAL",
        "confidence": 0.5,
        "sport": "SOCCER",
    }

    # Check if retractable/dome (some modern stadiums)
    if venue.get("dome_type") == DOME:
        impact["factors"].append("Indoor venue - no weather impact")
        return impact

    wind_speed = weather.get("wind_speed_mph", 0)
    temp = weather.get("temperature_f", 60)
    rain = weather.get("rain_in", 0)

    # ==========================================================================
    # RAIN IMPACT (Unique for soccer - can increase chaos/goals)
    # ==========================================================================

    if rain > 0.4:
        impact["total_adjustment"] += 0.5
        impact["goals_factor"] += 0.15
        impact["factors"].append(
            "Heavy rain: slippery pitch, ball skids, defensive errors more likely, +0.5 goals"
        )
    elif rain > 0.2:
        impact["total_adjustment"] += 0.25
        impact["goals_factor"] += 0.08
        impact["factors"].append(
            "Wet pitch: ball moves faster, increased chance of goals from errors"
        )
    elif rain > 0:
        impact["factors"].append(
            "Light rain: minor pitch impact"
        )

    # ==========================================================================
    # WIND IMPACT
    # ==========================================================================

    if wind_speed > 25:
        impact["total_adjustment"] -= 0.5
        impact["factors"].append(
            f"Strong wind ({wind_speed:.0f} mph): long balls affected, set pieces unpredictable"
        )
    elif wind_speed > 18:
        impact["total_adjustment"] -= 0.25
        impact["factors"].append(
            f"Windy ({wind_speed:.0f} mph): crosses and long passes affected"
        )
    elif wind_speed > 12:
        impact["factors"].append(
            f"Breezy ({wind_speed:.0f} mph): slight impact on aerial balls"
        )

    # ==========================================================================
    # TEMPERATURE IMPACT
    # ==========================================================================

    if temp < 35:
        impact["total_adjustment"] -= 0.25
        impact["factors"].append(
            f"Very cold ({temp:.0f}°F): pitch may be hard, players less mobile"
        )
    elif temp > 85:
        impact["total_adjustment"] -= 0.25
        impact["factors"].append(
            f"Hot conditions ({temp:.0f}°F): player fatigue, drink breaks may slow game"
        )

    # ==========================================================================
    # CALCULATE RECOMMENDATION
    # ==========================================================================

    if impact["total_adjustment"] >= 0.4:
        impact["recommendation"] = "OVER"
        impact["confidence"] = min(0.70, 0.55 + abs(impact["total_adjustment"]) * 0.2)
    elif impact["total_adjustment"] <= -0.4:
        impact["recommendation"] = "UNDER"
        impact["confidence"] = min(0.70, 0.55 + abs(impact["total_adjustment"]) * 0.2)
    else:
        impact["recommendation"] = "NEUTRAL"
        impact["confidence"] = 0.5

    impact["total_adjustment"] = round(impact["total_adjustment"], 2)
    impact["goals_factor"] = round(impact["goals_factor"], 2)
    impact["confidence"] = round(impact["confidence"], 2)

    return impact


# =============================================================================
# COLLEGE FOOTBALL IMPACT
# =============================================================================

def calculate_cfb_impact(
    weather: Dict[str, Any],
    venue: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate weather impact for College Football games.
    Similar to NFL but with less consistent team quality.
    """
    # Use NFL impact as base
    impact = calculate_nfl_impact(weather, venue)
    impact["sport"] = "CFB"

    # College teams may be more affected by weather
    # Increase impact factors slightly
    impact["total_adjustment"] *= 1.1
    impact["total_adjustment"] = round(impact["total_adjustment"], 2)

    return impact


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_weather_impact(
    sport: str,
    weather: Dict[str, Any],
    venue: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Get weather impact for any supported sport.

    Args:
        sport: Sport code (MLB, NFL, CFB, SOCCER)
        weather: Weather data
        venue: Venue data

    Returns:
        Impact analysis dict
    """
    sport_upper = sport.upper()

    if sport_upper == "MLB":
        return calculate_mlb_impact(weather, venue)
    elif sport_upper == "NFL":
        return calculate_nfl_impact(weather, venue)
    elif sport_upper in ("CFB", "NCAAF", "NCAA_FOOTBALL"):
        return calculate_cfb_impact(weather, venue)
    elif sport_upper in ("SOCCER", "FOOTBALL"):
        return calculate_soccer_impact(weather, venue)
    else:
        return {
            "total_adjustment": 0,
            "scoring_factor": 1.0,
            "factors": [f"Weather impact not calculated for {sport}"],
            "recommendation": "NEUTRAL",
            "confidence": 0.5,
            "sport": sport_upper,
        }


def analyze_game_weather(
    sport: str,
    weather: Dict[str, Any],
    venue_name: str
) -> Dict[str, Any]:
    """
    Full analysis of weather impact for a game.

    Args:
        sport: Sport code
        weather: Weather data dict
        venue_name: Name of venue

    Returns:
        Complete weather impact analysis
    """
    # Find venue
    venue = get_venue_by_name(venue_name, sport)
    if not venue:
        venue = {
            "name": venue_name,
            "dome_type": OUTDOOR,
            "altitude_ft": 0,
        }

    impact = get_weather_impact(sport, weather, venue)

    return {
        "venue": venue.get("name", venue_name),
        "dome_type": venue.get("dome_type", OUTDOOR),
        "weather": {
            "temperature_f": weather.get("temperature_f"),
            "humidity": weather.get("humidity"),
            "wind_speed_mph": weather.get("wind_speed_mph"),
            "wind_direction": weather.get("wind_direction"),
            "conditions": weather.get("conditions"),
            "precipitation_in": weather.get("precipitation_in"),
        },
        "impact": impact,
    }


def get_impact_summary(impact: Dict[str, Any]) -> str:
    """
    Get a brief text summary of the weather impact.

    Args:
        impact: Impact analysis dict

    Returns:
        Summary string
    """
    adj = impact.get("total_adjustment", 0)
    rec = impact.get("recommendation", "NEUTRAL")

    if abs(adj) < 0.5:
        return "Minimal weather impact"

    direction = "higher" if adj > 0 else "lower"
    sport = impact.get("sport", "")

    if sport == "MLB":
        unit = "runs"
    elif sport in ("NFL", "CFB"):
        unit = "points"
    else:
        unit = "goals"

    return f"Weather suggests {abs(adj):.1f} {unit} {direction} than expected. {rec}."
