"""
Weather API Router

Endpoints for weather data and weather impact analysis for games.
Provides real betting edge by calculating how weather affects outcomes.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import Optional, List

from app.db import get_db
from app.services.weather import (
    get_current_weather,
    get_forecast,
    get_historical_weather,
    get_game_weather,
    get_multi_hour_forecast,
)
from app.services.weather_impact import (
    calculate_mlb_impact,
    calculate_nfl_impact,
    calculate_soccer_impact,
    calculate_cfb_impact,
    get_weather_impact,
    analyze_game_weather,
    get_impact_summary,
)
from app.data.venues import (
    get_all_venues,
    get_venue_by_name,
    get_venue_by_team,
    get_venue_by_team_abbr,
    get_outdoor_venues,
    get_venue_coordinates,
    MLB_VENUES,
    NFL_VENUES,
    NBA_VENUES,
    CFB_VENUES,
    SOCCER_VENUES,
)

router = APIRouter(prefix="/weather", tags=["Weather"])


@router.get("/current/{venue_id}")
async def get_venue_current_weather(venue_id: str):
    """
    Get current weather at a venue.

    Args:
        venue_id: Venue key (e.g., 'wrigley_field', 'yankee_stadium')
    """
    # Find venue in all venue dictionaries
    venue = None
    for venues in [MLB_VENUES, NFL_VENUES, CFB_VENUES, SOCCER_VENUES]:
        if venue_id in venues:
            venue = venues[venue_id]
            break

    if not venue:
        # Try by name search
        venue = get_venue_by_name(venue_id)

    if not venue:
        raise HTTPException(status_code=404, detail=f"Venue '{venue_id}' not found")

    weather = await get_current_weather(venue["lat"], venue["lon"])

    if not weather:
        raise HTTPException(status_code=503, detail="Unable to fetch weather data")

    return {
        "venue": {
            "id": venue_id,
            "name": venue["name"],
            "city": venue.get("city"),
            "dome_type": venue.get("dome_type"),
        },
        "weather": weather,
    }


@router.get("/forecast/{venue_id}/{target_date}")
async def get_venue_forecast(
    venue_id: str,
    target_date: str,
    hour: int = Query(19, ge=0, le=23, description="Hour of day (0-23)")
):
    """
    Get weather forecast for a venue on a specific date.

    Args:
        venue_id: Venue key
        target_date: Date in YYYY-MM-DD format
        hour: Hour of day for forecast (default 7 PM for evening games)
    """
    venue = None
    for venues in [MLB_VENUES, NFL_VENUES, CFB_VENUES, SOCCER_VENUES]:
        if venue_id in venues:
            venue = venues[venue_id]
            break

    if not venue:
        venue = get_venue_by_name(venue_id)

    if not venue:
        raise HTTPException(status_code=404, detail=f"Venue '{venue_id}' not found")

    try:
        forecast_date = datetime.strptime(target_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    weather = await get_forecast(venue["lat"], venue["lon"], forecast_date, hour)

    if not weather:
        raise HTTPException(status_code=503, detail="Unable to fetch forecast data")

    return {
        "venue": {
            "id": venue_id,
            "name": venue["name"],
            "city": venue.get("city"),
        },
        "date": target_date,
        "hour": hour,
        "forecast": weather,
    }


@router.get("/impact/mlb")
async def get_mlb_weather_impact(
    venue: str = Query(..., description="Venue name or team abbreviation"),
    game_date: Optional[str] = Query(None, description="Game date (YYYY-MM-DD), defaults to today"),
    game_hour: int = Query(19, ge=0, le=23, description="Game start hour")
):
    """
    Get MLB weather impact analysis.

    Returns weather conditions and their effect on scoring (runs), HR probability, etc.
    This is the edge - use this to inform over/under bets.

    Args:
        venue: Venue name or team abbreviation (e.g., 'wrigley_field' or 'CHC')
        game_date: Date of game
        game_hour: Start time hour
    """
    # Find venue
    venue_data = None
    for key, v in MLB_VENUES.items():
        if key.lower() == venue.lower() or v.get("team_abbr", "").lower() == venue.lower():
            venue_data = v
            break

    if not venue_data:
        venue_data = get_venue_by_name(venue, "mlb")

    if not venue_data:
        raise HTTPException(status_code=404, detail=f"MLB venue '{venue}' not found")

    # Get date
    if game_date:
        try:
            target_date = datetime.strptime(game_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        target_date = date.today()

    # Get weather
    game_datetime = datetime.combine(target_date, datetime.min.time().replace(hour=game_hour))
    weather = await get_game_weather(venue_data["lat"], venue_data["lon"], game_datetime)

    if not weather:
        raise HTTPException(status_code=503, detail="Unable to fetch weather data")

    # Calculate impact
    impact = calculate_mlb_impact(weather, venue_data)

    return {
        "sport": "MLB",
        "venue": venue_data["name"],
        "team": venue_data.get("team"),
        "game_time": game_datetime.isoformat(),
        "dome_type": venue_data.get("dome_type"),
        "altitude_ft": venue_data.get("altitude_ft"),
        "weather": {
            "temperature_f": weather.get("temperature_f"),
            "humidity": weather.get("humidity"),
            "wind_speed_mph": weather.get("wind_speed_mph"),
            "wind_direction": weather.get("wind_direction"),
            "conditions": weather.get("conditions"),
            "weather_type": weather.get("weather_type"),
        },
        "impact": {
            "total_adjustment": impact["total_adjustment"],
            "hr_factor": impact["hr_factor"],
            "scoring_factor": impact["scoring_factor"],
            "recommendation": impact["recommendation"],
            "confidence": impact["confidence"],
            "factors": impact["factors"],
        },
        "summary": get_impact_summary(impact),
    }


@router.get("/impact/nfl")
async def get_nfl_weather_impact(
    venue: str = Query(..., description="Venue name or team abbreviation"),
    game_date: Optional[str] = Query(None, description="Game date (YYYY-MM-DD)"),
    game_hour: int = Query(13, ge=0, le=23, description="Game start hour (default 1 PM)")
):
    """
    Get NFL weather impact analysis.

    Returns weather conditions and their effect on passing, rushing, turnovers.
    Critical for over/under and player prop bets.

    Args:
        venue: Venue name or team abbreviation
        game_date: Date of game
        game_hour: Start time hour
    """
    venue_data = None
    for key, v in NFL_VENUES.items():
        if key.lower() == venue.lower():
            venue_data = v
            break
        team_abbr = v.get("team_abbr", "")
        if venue.upper() in team_abbr.split("/"):
            venue_data = v
            break

    if not venue_data:
        venue_data = get_venue_by_name(venue, "nfl")

    if not venue_data:
        raise HTTPException(status_code=404, detail=f"NFL venue '{venue}' not found")

    if game_date:
        try:
            target_date = datetime.strptime(game_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        target_date = date.today()

    game_datetime = datetime.combine(target_date, datetime.min.time().replace(hour=game_hour))
    weather = await get_game_weather(venue_data["lat"], venue_data["lon"], game_datetime)

    if not weather:
        raise HTTPException(status_code=503, detail="Unable to fetch weather data")

    impact = calculate_nfl_impact(weather, venue_data)

    return {
        "sport": "NFL",
        "venue": venue_data["name"],
        "team": venue_data.get("team"),
        "game_time": game_datetime.isoformat(),
        "dome_type": venue_data.get("dome_type"),
        "weather": {
            "temperature_f": weather.get("temperature_f"),
            "humidity": weather.get("humidity"),
            "wind_speed_mph": weather.get("wind_speed_mph"),
            "wind_direction": weather.get("wind_direction"),
            "conditions": weather.get("conditions"),
            "precipitation_in": weather.get("precipitation_in"),
            "snowfall_in": weather.get("snowfall_in"),
            "weather_type": weather.get("weather_type"),
        },
        "impact": {
            "total_adjustment": impact["total_adjustment"],
            "pass_yards_factor": impact["pass_yards_factor"],
            "rush_yards_factor": impact["rush_yards_factor"],
            "turnover_factor": impact["turnover_factor"],
            "recommendation": impact["recommendation"],
            "confidence": impact["confidence"],
            "factors": impact["factors"],
        },
        "summary": get_impact_summary(impact),
    }


@router.get("/impact/soccer")
async def get_soccer_weather_impact(
    venue: str = Query(..., description="Venue name"),
    game_date: Optional[str] = Query(None, description="Match date (YYYY-MM-DD)"),
    game_hour: int = Query(15, ge=0, le=23, description="Kickoff hour (default 3 PM)")
):
    """
    Get Soccer weather impact analysis.

    Rain and wind affect pitch conditions and ball movement.

    Args:
        venue: Venue name
        game_date: Date of match
        game_hour: Kickoff hour
    """
    venue_data = None
    for key, v in SOCCER_VENUES.items():
        if key.lower() == venue.lower() or venue.lower() in v["name"].lower():
            venue_data = v
            break

    if not venue_data:
        venue_data = get_venue_by_name(venue, "soccer")

    if not venue_data:
        raise HTTPException(status_code=404, detail=f"Soccer venue '{venue}' not found")

    if game_date:
        try:
            target_date = datetime.strptime(game_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        target_date = date.today()

    game_datetime = datetime.combine(target_date, datetime.min.time().replace(hour=game_hour))
    weather = await get_game_weather(venue_data["lat"], venue_data["lon"], game_datetime)

    if not weather:
        raise HTTPException(status_code=503, detail="Unable to fetch weather data")

    impact = calculate_soccer_impact(weather, venue_data)

    return {
        "sport": "Soccer",
        "venue": venue_data["name"],
        "team": venue_data.get("team"),
        "kickoff": game_datetime.isoformat(),
        "dome_type": venue_data.get("dome_type"),
        "weather": {
            "temperature_f": weather.get("temperature_f"),
            "humidity": weather.get("humidity"),
            "wind_speed_mph": weather.get("wind_speed_mph"),
            "wind_direction": weather.get("wind_direction"),
            "conditions": weather.get("conditions"),
            "precipitation_in": weather.get("precipitation_in"),
            "weather_type": weather.get("weather_type"),
        },
        "impact": {
            "total_adjustment": impact["total_adjustment"],
            "goals_factor": impact["goals_factor"],
            "recommendation": impact["recommendation"],
            "confidence": impact["confidence"],
            "factors": impact["factors"],
        },
        "summary": get_impact_summary(impact),
    }


@router.get("/impact/cfb")
async def get_cfb_weather_impact(
    venue: str = Query(..., description="Venue name or team"),
    game_date: Optional[str] = Query(None, description="Game date (YYYY-MM-DD)"),
    game_hour: int = Query(15, ge=0, le=23, description="Kickoff hour")
):
    """
    Get College Football weather impact analysis.

    Similar to NFL but college teams may be more affected by conditions.
    """
    venue_data = None
    for key, v in CFB_VENUES.items():
        if key.lower() == venue.lower() or venue.lower() in v["name"].lower():
            venue_data = v
            break

    if not venue_data:
        venue_data = get_venue_by_name(venue, "cfb")

    if not venue_data:
        # Default to outdoor venue
        venue_data = {
            "name": venue,
            "dome_type": "outdoor",
            "altitude_ft": 500,
            "lat": 40.0,  # Default coords
            "lon": -83.0,
        }

    if game_date:
        try:
            target_date = datetime.strptime(game_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        target_date = date.today()

    game_datetime = datetime.combine(target_date, datetime.min.time().replace(hour=game_hour))
    weather = await get_game_weather(venue_data["lat"], venue_data["lon"], game_datetime)

    if not weather:
        raise HTTPException(status_code=503, detail="Unable to fetch weather data")

    impact = calculate_cfb_impact(weather, venue_data)

    return {
        "sport": "CFB",
        "venue": venue_data["name"],
        "team": venue_data.get("team"),
        "kickoff": game_datetime.isoformat(),
        "dome_type": venue_data.get("dome_type"),
        "weather": {
            "temperature_f": weather.get("temperature_f"),
            "humidity": weather.get("humidity"),
            "wind_speed_mph": weather.get("wind_speed_mph"),
            "wind_direction": weather.get("wind_direction"),
            "conditions": weather.get("conditions"),
            "precipitation_in": weather.get("precipitation_in"),
            "snowfall_in": weather.get("snowfall_in"),
            "weather_type": weather.get("weather_type"),
        },
        "impact": {
            "total_adjustment": impact["total_adjustment"],
            "pass_yards_factor": impact["pass_yards_factor"],
            "rush_yards_factor": impact["rush_yards_factor"],
            "turnover_factor": impact["turnover_factor"],
            "recommendation": impact["recommendation"],
            "confidence": impact["confidence"],
            "factors": impact["factors"],
        },
        "summary": get_impact_summary(impact),
    }


@router.get("/venues")
async def list_venues(
    sport: Optional[str] = Query(None, description="Filter by sport (mlb, nfl, nba, cfb, soccer)"),
    outdoor_only: bool = Query(False, description="Only show outdoor venues")
):
    """
    List all venues with coordinates.

    Args:
        sport: Optional sport filter
        outdoor_only: If true, only return outdoor venues (where weather matters)
    """
    if outdoor_only:
        venues = get_outdoor_venues(sport)
    else:
        venues = get_all_venues(sport)

    return {
        "count": len(venues),
        "venues": venues,
    }


@router.get("/venues/{venue_id}")
async def get_venue_details(venue_id: str):
    """
    Get details for a specific venue.

    Args:
        venue_id: Venue key
    """
    for venues in [MLB_VENUES, NFL_VENUES, NBA_VENUES, CFB_VENUES, SOCCER_VENUES]:
        if venue_id in venues:
            return {
                "id": venue_id,
                **venues[venue_id]
            }

    # Try search by name
    venue = get_venue_by_name(venue_id)
    if venue:
        return venue

    raise HTTPException(status_code=404, detail=f"Venue '{venue_id}' not found")


@router.get("/team/{team}")
async def get_team_weather(
    team: str,
    sport: str = Query(..., description="Sport (mlb, nfl, nba, cfb, soccer)")
):
    """
    Get current weather at a team's home venue.

    Args:
        team: Team name or abbreviation
        sport: Sport code
    """
    venue = get_venue_by_team(team, sport)

    if not venue:
        venue = get_venue_by_team_abbr(team, sport)

    if not venue:
        raise HTTPException(status_code=404, detail=f"Team '{team}' not found for {sport}")

    weather = await get_current_weather(venue["lat"], venue["lon"])

    if not weather:
        raise HTTPException(status_code=503, detail="Unable to fetch weather data")

    return {
        "team": team,
        "venue": venue["name"],
        "dome_type": venue.get("dome_type"),
        "weather": weather,
    }


@router.get("/bulk/today")
async def get_todays_weather_impacts(
    sport: str = Query(..., description="Sport (mlb, nfl, cfb, soccer)")
):
    """
    Get weather impact analysis for all outdoor venues for today.
    Useful for scanning for weather edges across all games.

    Args:
        sport: Sport to analyze
    """
    sport_lower = sport.lower()
    if sport_lower == "mlb":
        venues = MLB_VENUES
        impact_func = calculate_mlb_impact
        game_hour = 19
    elif sport_lower == "nfl":
        venues = NFL_VENUES
        impact_func = calculate_nfl_impact
        game_hour = 13
    elif sport_lower == "cfb":
        venues = CFB_VENUES
        impact_func = calculate_cfb_impact
        game_hour = 15
    elif sport_lower == "soccer":
        venues = SOCCER_VENUES
        impact_func = calculate_soccer_impact
        game_hour = 15
    else:
        raise HTTPException(status_code=400, detail=f"Sport '{sport}' not supported")

    today = date.today()
    game_datetime = datetime.combine(today, datetime.min.time().replace(hour=game_hour))

    results = []
    significant_impacts = []

    for venue_id, venue_data in venues.items():
        # Skip domes
        if venue_data.get("dome_type") == "dome":
            continue

        try:
            weather = await get_current_weather(venue_data["lat"], venue_data["lon"])
            if weather:
                impact = impact_func(weather, venue_data)

                result = {
                    "venue_id": venue_id,
                    "venue_name": venue_data["name"],
                    "team": venue_data.get("team"),
                    "weather_summary": f"{weather.get('temperature_f', 0):.0f}°F, {weather.get('conditions', 'Unknown')}",
                    "wind": f"{weather.get('wind_speed_mph', 0):.0f} mph {weather.get('wind_direction', '')}",
                    "total_adjustment": impact["total_adjustment"],
                    "recommendation": impact["recommendation"],
                    "confidence": impact["confidence"],
                }
                results.append(result)

                # Track significant impacts
                if abs(impact["total_adjustment"]) >= 1.0:
                    significant_impacts.append(result)
        except Exception as e:
            continue  # Skip venues with errors

    # Sort by impact magnitude
    results.sort(key=lambda x: abs(x["total_adjustment"]), reverse=True)
    significant_impacts.sort(key=lambda x: abs(x["total_adjustment"]), reverse=True)

    return {
        "sport": sport.upper(),
        "date": today.isoformat(),
        "total_venues": len(results),
        "significant_impacts": len(significant_impacts),
        "edges": significant_impacts,  # Top weather edges
        "all_venues": results,
    }
