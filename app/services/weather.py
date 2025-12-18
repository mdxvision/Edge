"""
Weather Service

Fetches weather data from Open-Meteo API (completely free, no API key needed).
Provides current weather, forecasts, and historical data for game venues.
"""

import httpx
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
from functools import lru_cache
import asyncio
import logging

logger = logging.getLogger(__name__)

# Open-Meteo API endpoints
FORECAST_BASE = "https://api.open-meteo.com/v1/forecast"
HISTORICAL_BASE = "https://archive-api.open-meteo.com/v1/archive"

# Weather code mappings
WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

# Cache for weather data (5-minute TTL simulated by storing timestamp)
_weather_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


def _get_cache_key(lat: float, lon: float, date_str: Optional[str] = None) -> str:
    """Generate cache key for weather data."""
    return f"{lat:.4f}_{lon:.4f}_{date_str or 'current'}"


def _is_cache_valid(cache_entry: Dict[str, Any]) -> bool:
    """Check if cache entry is still valid."""
    if not cache_entry:
        return False
    cached_at = cache_entry.get("cached_at", 0)
    return (datetime.now().timestamp() - cached_at) < CACHE_TTL_SECONDS


def _celsius_to_fahrenheit(celsius: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return round((celsius * 9/5) + 32, 1)


def _kmh_to_mph(kmh: float) -> float:
    """Convert km/h to mph."""
    return round(kmh * 0.621371, 1)


def _mm_to_inches(mm: float) -> float:
    """Convert millimeters to inches."""
    return round(mm * 0.0393701, 2)


def _get_weather_description(code: int) -> str:
    """Get human-readable weather description from code."""
    return WEATHER_CODES.get(code, "Unknown")


def _get_wind_direction_name(degrees: float) -> str:
    """Convert wind direction degrees to compass direction."""
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                  "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    index = round(degrees / 22.5) % 16
    return directions[index]


async def get_current_weather(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """
    Get current weather conditions for a location.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        Weather data dict or None if fetch fails
    """
    cache_key = _get_cache_key(lat, lon)

    # Check cache
    if cache_key in _weather_cache and _is_cache_valid(_weather_cache[cache_key]):
        return _weather_cache[cache_key]["data"]

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "rain",
            "weather_code",
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m",
        ],
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
        "timezone": "auto",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(FORECAST_BASE, params=params)
            response.raise_for_status()
            data = response.json()

            current = data.get("current", {})

            weather = {
                "temperature_f": _celsius_to_fahrenheit(current.get("temperature_2m", 0)),
                "temperature_c": round(current.get("temperature_2m", 0), 1),
                "humidity": current.get("relative_humidity_2m", 0),
                "precipitation_in": _mm_to_inches(current.get("precipitation", 0)),
                "rain_in": _mm_to_inches(current.get("rain", 0)),
                "weather_code": current.get("weather_code", 0),
                "conditions": _get_weather_description(current.get("weather_code", 0)),
                "wind_speed_mph": _kmh_to_mph(current.get("wind_speed_10m", 0)),
                "wind_speed_kmh": round(current.get("wind_speed_10m", 0), 1),
                "wind_direction_degrees": current.get("wind_direction_10m", 0),
                "wind_direction": _get_wind_direction_name(current.get("wind_direction_10m", 0)),
                "wind_gusts_mph": _kmh_to_mph(current.get("wind_gusts_10m", 0)),
                "timezone": data.get("timezone", "UTC"),
                "fetched_at": datetime.now().isoformat(),
            }

            # Cache the result
            _weather_cache[cache_key] = {
                "data": weather,
                "cached_at": datetime.now().timestamp()
            }

            return weather

    except Exception as e:
        logger.error(f"Error fetching current weather for ({lat}, {lon}): {e}")
        return None


async def get_forecast(
    lat: float,
    lon: float,
    target_date: date,
    target_hour: int = 12
) -> Optional[Dict[str, Any]]:
    """
    Get weather forecast for a specific date and hour.

    Args:
        lat: Latitude
        lon: Longitude
        target_date: Date to get forecast for
        target_hour: Hour of day (0-23)

    Returns:
        Weather forecast data or None
    """
    cache_key = _get_cache_key(lat, lon, f"{target_date}_{target_hour}")

    if cache_key in _weather_cache and _is_cache_valid(_weather_cache[cache_key]):
        return _weather_cache[cache_key]["data"]

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "rain",
            "snowfall",
            "weather_code",
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m",
        ],
        "start_date": target_date.isoformat(),
        "end_date": target_date.isoformat(),
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
        "timezone": "auto",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(FORECAST_BASE, params=params)
            response.raise_for_status()
            data = response.json()

            hourly = data.get("hourly", {})
            times = hourly.get("time", [])

            # Find the index for the target hour
            target_index = None
            for i, time_str in enumerate(times):
                hour = int(time_str.split("T")[1].split(":")[0])
                if hour == target_hour:
                    target_index = i
                    break

            if target_index is None:
                target_index = min(target_hour, len(times) - 1)

            weather = {
                "forecast_time": times[target_index] if times else None,
                "temperature_f": _celsius_to_fahrenheit(hourly.get("temperature_2m", [0])[target_index]),
                "temperature_c": round(hourly.get("temperature_2m", [0])[target_index], 1),
                "humidity": hourly.get("relative_humidity_2m", [0])[target_index],
                "precipitation_in": _mm_to_inches(hourly.get("precipitation", [0])[target_index]),
                "rain_in": _mm_to_inches(hourly.get("rain", [0])[target_index]),
                "snowfall_in": _mm_to_inches(hourly.get("snowfall", [0])[target_index] * 10),  # cm to mm
                "weather_code": hourly.get("weather_code", [0])[target_index],
                "conditions": _get_weather_description(hourly.get("weather_code", [0])[target_index]),
                "wind_speed_mph": _kmh_to_mph(hourly.get("wind_speed_10m", [0])[target_index]),
                "wind_direction_degrees": hourly.get("wind_direction_10m", [0])[target_index],
                "wind_direction": _get_wind_direction_name(hourly.get("wind_direction_10m", [0])[target_index]),
                "wind_gusts_mph": _kmh_to_mph(hourly.get("wind_gusts_10m", [0])[target_index]),
                "timezone": data.get("timezone", "UTC"),
                "is_forecast": True,
            }

            _weather_cache[cache_key] = {
                "data": weather,
                "cached_at": datetime.now().timestamp()
            }

            return weather

    except Exception as e:
        logger.error(f"Error fetching forecast for ({lat}, {lon}) on {target_date}: {e}")
        return None


async def get_historical_weather(
    lat: float,
    lon: float,
    target_date: date,
    target_hour: int = 12
) -> Optional[Dict[str, Any]]:
    """
    Get historical weather for a past date.

    Args:
        lat: Latitude
        lon: Longitude
        target_date: Past date
        target_hour: Hour of day (0-23)

    Returns:
        Historical weather data or None
    """
    cache_key = _get_cache_key(lat, lon, f"hist_{target_date}_{target_hour}")

    if cache_key in _weather_cache and _is_cache_valid(_weather_cache[cache_key]):
        return _weather_cache[cache_key]["data"]

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "rain",
            "snowfall",
            "weather_code",
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m",
        ],
        "start_date": target_date.isoformat(),
        "end_date": target_date.isoformat(),
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
        "timezone": "auto",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(HISTORICAL_BASE, params=params)
            response.raise_for_status()
            data = response.json()

            hourly = data.get("hourly", {})
            times = hourly.get("time", [])

            target_index = min(target_hour, len(times) - 1) if times else 0

            weather = {
                "recorded_time": times[target_index] if times else None,
                "temperature_f": _celsius_to_fahrenheit(hourly.get("temperature_2m", [0])[target_index]),
                "temperature_c": round(hourly.get("temperature_2m", [0])[target_index], 1),
                "humidity": hourly.get("relative_humidity_2m", [0])[target_index],
                "precipitation_in": _mm_to_inches(hourly.get("precipitation", [0])[target_index]),
                "rain_in": _mm_to_inches(hourly.get("rain", [0])[target_index]),
                "snowfall_in": _mm_to_inches(hourly.get("snowfall", [0])[target_index] * 10),
                "weather_code": hourly.get("weather_code", [0])[target_index],
                "conditions": _get_weather_description(hourly.get("weather_code", [0])[target_index]),
                "wind_speed_mph": _kmh_to_mph(hourly.get("wind_speed_10m", [0])[target_index]),
                "wind_direction_degrees": hourly.get("wind_direction_10m", [0])[target_index],
                "wind_direction": _get_wind_direction_name(hourly.get("wind_direction_10m", [0])[target_index]),
                "wind_gusts_mph": _kmh_to_mph(hourly.get("wind_gusts_10m", [0])[target_index]),
                "timezone": data.get("timezone", "UTC"),
                "is_historical": True,
            }

            _weather_cache[cache_key] = {
                "data": weather,
                "cached_at": datetime.now().timestamp()
            }

            return weather

    except Exception as e:
        logger.error(f"Error fetching historical weather for ({lat}, {lon}) on {target_date}: {e}")
        return None


async def get_game_weather(
    venue_lat: float,
    venue_lon: float,
    game_datetime: datetime
) -> Optional[Dict[str, Any]]:
    """
    Get weather for a specific game based on venue and time.

    Automatically determines whether to fetch current, forecast, or historical data.

    Args:
        venue_lat: Venue latitude
        venue_lon: Venue longitude
        game_datetime: Game date and time

    Returns:
        Weather data with game context
    """
    now = datetime.now()
    game_date = game_datetime.date()
    game_hour = game_datetime.hour

    # Determine which API to use
    if game_date < now.date():
        # Past game - use historical
        weather = await get_historical_weather(venue_lat, venue_lon, game_date, game_hour)
        weather_type = "historical"
    elif game_date == now.date() and abs(game_hour - now.hour) <= 1:
        # Current game - use current weather
        weather = await get_current_weather(venue_lat, venue_lon)
        weather_type = "current"
    else:
        # Future game - use forecast
        weather = await get_forecast(venue_lat, venue_lon, game_date, game_hour)
        weather_type = "forecast"

    if weather:
        weather["weather_type"] = weather_type
        weather["game_datetime"] = game_datetime.isoformat()

    return weather


async def get_multi_hour_forecast(
    lat: float,
    lon: float,
    target_date: date,
    start_hour: int = 0,
    end_hour: int = 23
) -> Optional[List[Dict[str, Any]]]:
    """
    Get hourly forecast for a range of hours on a specific date.
    Useful for games with uncertain start times or long duration.

    Args:
        lat: Latitude
        lon: Longitude
        target_date: Date to get forecast for
        start_hour: Starting hour (0-23)
        end_hour: Ending hour (0-23)

    Returns:
        List of hourly weather forecasts
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "rain",
            "weather_code",
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m",
        ],
        "start_date": target_date.isoformat(),
        "end_date": target_date.isoformat(),
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
        "timezone": "auto",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(FORECAST_BASE, params=params)
            response.raise_for_status()
            data = response.json()

            hourly = data.get("hourly", {})
            times = hourly.get("time", [])

            forecasts = []
            for i, time_str in enumerate(times):
                hour = int(time_str.split("T")[1].split(":")[0])
                if start_hour <= hour <= end_hour:
                    forecasts.append({
                        "time": time_str,
                        "hour": hour,
                        "temperature_f": _celsius_to_fahrenheit(hourly.get("temperature_2m", [0])[i]),
                        "humidity": hourly.get("relative_humidity_2m", [0])[i],
                        "precipitation_in": _mm_to_inches(hourly.get("precipitation", [0])[i]),
                        "conditions": _get_weather_description(hourly.get("weather_code", [0])[i]),
                        "wind_speed_mph": _kmh_to_mph(hourly.get("wind_speed_10m", [0])[i]),
                        "wind_direction": _get_wind_direction_name(hourly.get("wind_direction_10m", [0])[i]),
                    })

            return forecasts

    except Exception as e:
        logger.error(f"Error fetching multi-hour forecast: {e}")
        return None


def clear_weather_cache():
    """Clear the weather cache."""
    global _weather_cache
    _weather_cache = {}
    logger.info("Weather cache cleared")
