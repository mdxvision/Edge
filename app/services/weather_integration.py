"""
Weather Integration for Edge Tracker

Enhances predictions with real weather conditions and impact analysis.
Wraps the existing weather service with sports-specific impact calculations.
"""

import os
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Use WeatherAPI if key is available, otherwise Open-Meteo
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY", "")
WEATHER_API_BASE = "http://api.weatherapi.com/v1"

# Venue coordinates for major sports venues
VENUE_COORDINATES = {
    # NFL Stadiums
    "arrowhead stadium": (39.0489, -94.4839),
    "sofi stadium": (33.9535, -118.3390),
    "allegiant stadium": (36.0909, -115.1833),
    "at&t stadium": (32.7473, -97.0945),
    "lambeau field": (44.5013, -88.0622),
    "lincoln financial field": (39.9008, -75.1675),
    "gillette stadium": (42.0909, -71.2643),
    "soldier field": (41.8623, -87.6167),
    "ford field": (42.3400, -83.0456),
    "us bank stadium": (44.9736, -93.2575),
    "lumen field": (47.5952, -122.3316),
    "raymond james stadium": (27.9759, -82.5033),
    "metlife stadium": (40.8128, -74.0742),
    "hard rock stadium": (25.9580, -80.2389),
    "caesars superdome": (29.9511, -90.0812),
    "mercedes-benz stadium": (33.7553, -84.4006),
    "bank of america stadium": (35.2258, -80.8528),
    "highmark stadium": (42.7738, -78.7870),
    "m&t bank stadium": (39.2780, -76.6227),
    "acrisure stadium": (40.4468, -80.0158),
    "firstenergy stadium": (41.5061, -81.6995),
    "paycor stadium": (39.0955, -84.5161),
    "nissan stadium": (36.1665, -86.7713),
    "lucas oil stadium": (39.7601, -86.1639),
    "nrg stadium": (29.6847, -95.4107),
    "tiaa bank field": (30.3239, -81.6373),
    "empower field": (39.7439, -105.0201),
    "state farm stadium": (33.5276, -112.2626),
    "levi's stadium": (37.4033, -121.9694),
    "fedexfield": (38.9076, -76.8645),

    # NBA Arenas
    "madison square garden": (40.7505, -73.9934),
    "crypto.com arena": (34.0430, -118.2673),
    "united center": (41.8807, -87.6742),
    "td garden": (42.3662, -71.0621),
    "chase center": (37.7680, -122.3877),
    "barclays center": (40.6826, -73.9754),
    "wells fargo center": (39.9012, -75.1720),
    "american airlines center": (32.7905, -96.8103),
    "target center": (44.9795, -93.2761),
    "fiserv forum": (43.0451, -87.9173),
    "ball arena": (39.7487, -105.0077),
    "rocket mortgage fieldhouse": (41.4965, -81.6882),
    "footprint center": (33.4457, -112.0712),
    "kaseya center": (25.7814, -80.1870),
    "t-mobile arena": (36.1029, -115.1785),

    # MLB Stadiums
    "yankee stadium": (40.8296, -73.9262),
    "dodger stadium": (34.0739, -118.2400),
    "fenway park": (42.3467, -71.0972),
    "wrigley field": (41.9484, -87.6553),
    "oracle park": (37.7786, -122.3893),
    "citi field": (40.7571, -73.8458),
    "citizens bank park": (39.9061, -75.1665),
    "tropicana field": (27.7682, -82.6534),  # Dome
    "globe life field": (32.7473, -97.0832),  # Retractable
    "minute maid park": (29.7573, -95.3555),  # Retractable
    "t-mobile park": (47.5914, -122.3325),  # Retractable
}

# Dome/indoor venues (weather doesn't matter)
INDOOR_VENUES = {
    "caesars superdome",
    "lucas oil stadium",
    "mercedes-benz stadium",
    "us bank stadium",
    "at&t stadium",
    "sofi stadium",
    "allegiant stadium",
    "ford field",
    "tropicana field",
    "globe life field",
    "minute maid park",
    "t-mobile park",
    "crypto.com arena",
    "madison square garden",
    "barclays center",
    "td garden",
    "united center",
    "wells fargo center",
    "chase center",
    "fiserv forum",
    "target center",
    "ball arena",
    "rocket mortgage fieldhouse",
    "footprint center",
    "kaseya center",
    "american airlines center",
    "t-mobile arena",
}


class WeatherService:
    """Weather service with sports-specific impact analysis"""

    def __init__(self):
        self.api_key = WEATHER_API_KEY

    async def get_game_weather(
        self,
        venue: str,
        game_time: datetime
    ) -> Dict[str, Any]:
        """
        Get weather for game time and location

        Args:
            venue: Venue name or city
            game_time: Game start time

        Returns:
            Weather data with impact analysis
        """
        venue_lower = venue.lower()

        # Check if indoor venue
        for indoor in INDOOR_VENUES:
            if indoor in venue_lower:
                return {
                    "is_dome": True,
                    "temp_f": 72,
                    "wind_mph": 0,
                    "wind_direction": "N/A",
                    "precip_chance": 0,
                    "condition": "Indoor (Climate Controlled)",
                    "impact_score": 0,
                    "recommendation": "Indoor venue - weather not a factor"
                }

        # Get coordinates
        coords = self._get_venue_coords(venue)
        if not coords:
            # Try to geocode the venue/city
            coords = await self._geocode_venue(venue)

        if not coords:
            return {
                "error": "Could not locate venue",
                "impact_score": 50,
                "recommendation": "Unable to fetch weather data"
            }

        # Fetch weather data
        weather = await self._fetch_weather(coords[0], coords[1], game_time)

        if weather:
            weather["is_dome"] = False
            return weather

        return {
            "error": "Weather data unavailable",
            "impact_score": 50,
            "recommendation": "Check weather closer to game time"
        }

    def calculate_weather_impact(
        self,
        weather: Dict[str, Any],
        sport: str
    ) -> Dict[str, Any]:
        """
        Sport-specific weather impact analysis

        Args:
            weather: Weather data dict
            sport: Sport type (NFL, MLB, etc.)

        Returns:
            Impact analysis with score and recommendations
        """
        if weather.get("is_dome") or weather.get("error"):
            return {
                "impact_score": 0,
                "factors": [],
                "recommendation": weather.get("recommendation", "Indoor venue")
            }

        impact_score = 0
        factors = []
        recommendations = []

        temp = weather.get("temp_f", 70)
        wind = weather.get("wind_mph", 0)
        precip = weather.get("precip_chance", 0)
        condition = weather.get("condition", "").lower()

        sport_upper = sport.upper()

        if sport_upper == "NFL":
            # Wind impact on passing game
            if wind >= 20:
                impact_score += 30
                factors.append(f"High wind ({wind} mph) - significant passing impact")
                recommendations.append("Favor run-heavy teams and unders")
            elif wind >= 15:
                impact_score += 20
                factors.append(f"Moderate wind ({wind} mph) - some passing impact")
                recommendations.append("Consider under on high totals")
            elif wind >= 10:
                impact_score += 10
                factors.append(f"Light wind ({wind} mph) - minimal impact")

            # Cold weather
            if temp <= 32:
                impact_score += 25
                factors.append(f"Freezing temps ({temp}F) - dome teams struggle")
                recommendations.append("Fade dome teams, favor cold-weather teams")
            elif temp <= 40:
                impact_score += 15
                factors.append(f"Cold temps ({temp}F) - may affect visitors")

            # Precipitation
            if "rain" in condition or "snow" in condition:
                impact_score += 20
                factors.append(f"Precipitation ({condition}) - ball handling affected")
                recommendations.append("Favor rushing attacks, under on total")

        elif sport_upper == "MLB":
            # Wind direction and HR rates
            if wind >= 15:
                impact_score += 25
                factors.append(f"Strong wind ({wind} mph) - affects ball flight")

                wind_dir = weather.get("wind_direction", "").upper()
                if wind_dir in ["N", "NE", "NW"]:
                    recommendations.append("Wind blowing in - favor unders/pitchers")
                elif wind_dir in ["S", "SE", "SW"]:
                    recommendations.append("Wind blowing out - favor overs/hitters")

            # Temperature affects ball carry
            if temp >= 85:
                impact_score += 15
                factors.append(f"Hot temps ({temp}F) - ball carries well")
                recommendations.append("Slightly favor overs")
            elif temp <= 50:
                impact_score += 15
                factors.append(f"Cold temps ({temp}F) - ball doesn't carry")
                recommendations.append("Slightly favor unders")

            # Rain delays
            if precip >= 50:
                impact_score += 20
                factors.append(f"High rain chance ({precip}%) - possible delay")
                recommendations.append("Monitor for bullpen impact")

        elif sport_upper in ["NBA", "CBB", "NCAAB"]:
            # Indoor sport, but travel weather can matter
            if temp <= 20 or "snow" in condition:
                impact_score += 10
                factors.append("Severe weather may affect travel/energy")

        elif sport_upper == "SOCCER":
            # Rain affects ball movement
            if "rain" in condition:
                impact_score += 20
                factors.append(f"Rain ({condition}) - slick surface")
                recommendations.append("May favor defensive play, unders")

            if wind >= 15:
                impact_score += 15
                factors.append(f"Wind ({wind} mph) - affects long balls")

        return {
            "impact_score": min(impact_score, 100),
            "factors": factors,
            "recommendations": recommendations,
            "recommendation": "; ".join(recommendations) if recommendations else "No significant weather impact"
        }

    def _get_venue_coords(self, venue: str) -> Optional[tuple]:
        """Get coordinates for known venue"""
        venue_lower = venue.lower()
        for venue_name, coords in VENUE_COORDINATES.items():
            if venue_name in venue_lower or venue_lower in venue_name:
                return coords
        return None

    async def _geocode_venue(self, venue: str) -> Optional[tuple]:
        """Geocode a venue/city name"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Use Open-Meteo's geocoding
                response = await client.get(
                    "https://geocoding-api.open-meteo.com/v1/search",
                    params={"name": venue, "count": 1}
                )

                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    if results:
                        return (results[0]["latitude"], results[0]["longitude"])
        except Exception as e:
            logger.error(f"Geocoding error: {str(e)}")

        return None

    async def _fetch_weather(
        self,
        lat: float,
        lon: float,
        game_time: datetime
    ) -> Optional[Dict]:
        """Fetch weather data from API"""
        # Try WeatherAPI first if key available
        if self.api_key:
            weather = await self._fetch_from_weatherapi(lat, lon, game_time)
            if weather:
                return weather

        # Fallback to Open-Meteo (free, no key needed)
        return await self._fetch_from_openmeteo(lat, lon, game_time)

    async def _fetch_from_weatherapi(
        self,
        lat: float,
        lon: float,
        game_time: datetime
    ) -> Optional[Dict]:
        """Fetch from WeatherAPI.com"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Use forecast endpoint
                response = await client.get(
                    f"{WEATHER_API_BASE}/forecast.json",
                    params={
                        "key": self.api_key,
                        "q": f"{lat},{lon}",
                        "dt": game_time.strftime("%Y-%m-%d"),
                        "hour": game_time.hour
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    forecast = data.get("forecast", {}).get("forecastday", [{}])[0]
                    hours = forecast.get("hour", [])

                    # Find the hour closest to game time
                    target_hour = game_time.hour
                    hour_data = None
                    for h in hours:
                        hour_time = datetime.fromisoformat(h["time"])
                        if hour_time.hour == target_hour:
                            hour_data = h
                            break

                    if hour_data:
                        return {
                            "temp_f": hour_data.get("temp_f", 70),
                            "wind_mph": hour_data.get("wind_mph", 0),
                            "wind_direction": hour_data.get("wind_dir", "N"),
                            "precip_chance": hour_data.get("chance_of_rain", 0),
                            "humidity": hour_data.get("humidity", 50),
                            "condition": hour_data.get("condition", {}).get("text", "Unknown"),
                            "source": "WeatherAPI"
                        }

        except Exception as e:
            logger.error(f"WeatherAPI error: {str(e)}")

        return None

    async def _fetch_from_openmeteo(
        self,
        lat: float,
        lon: float,
        game_time: datetime
    ) -> Optional[Dict]:
        """Fetch from Open-Meteo (free)"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "hourly": "temperature_2m,wind_speed_10m,wind_direction_10m,precipitation_probability,weather_code",
                        "temperature_unit": "fahrenheit",
                        "wind_speed_unit": "mph",
                        "timezone": "auto"
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    hourly = data.get("hourly", {})
                    times = hourly.get("time", [])

                    # Find the hour closest to game time
                    target_str = game_time.strftime("%Y-%m-%dT%H:00")
                    idx = None
                    for i, t in enumerate(times):
                        if t == target_str:
                            idx = i
                            break

                    if idx is not None:
                        # Map weather code to condition
                        weather_code = hourly.get("weather_code", [])[idx] if hourly.get("weather_code") else 0
                        condition = self._weather_code_to_condition(weather_code)

                        # Map wind direction degrees to cardinal
                        wind_deg = hourly.get("wind_direction_10m", [])[idx] if hourly.get("wind_direction_10m") else 0
                        wind_dir = self._degrees_to_cardinal(wind_deg)

                        return {
                            "temp_f": hourly.get("temperature_2m", [])[idx] if hourly.get("temperature_2m") else 70,
                            "wind_mph": hourly.get("wind_speed_10m", [])[idx] if hourly.get("wind_speed_10m") else 0,
                            "wind_direction": wind_dir,
                            "precip_chance": hourly.get("precipitation_probability", [])[idx] if hourly.get("precipitation_probability") else 0,
                            "condition": condition,
                            "source": "Open-Meteo"
                        }

        except Exception as e:
            logger.error(f"Open-Meteo error: {str(e)}")

        return None

    def _weather_code_to_condition(self, code: int) -> str:
        """Convert Open-Meteo weather code to condition string"""
        codes = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Fog",
            51: "Light drizzle",
            53: "Drizzle",
            55: "Dense drizzle",
            61: "Light rain",
            63: "Rain",
            65: "Heavy rain",
            71: "Light snow",
            73: "Snow",
            75: "Heavy snow",
            80: "Rain showers",
            81: "Rain showers",
            82: "Heavy showers",
            85: "Snow showers",
            86: "Heavy snow",
            95: "Thunderstorm",
            96: "Thunderstorm with hail",
            99: "Severe thunderstorm"
        }
        return codes.get(code, "Unknown")

    def _degrees_to_cardinal(self, degrees: float) -> str:
        """Convert wind direction degrees to cardinal direction"""
        directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                      "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        idx = round(degrees / 22.5) % 16
        return directions[idx]


def get_weather_service() -> WeatherService:
    """Get a WeatherService instance"""
    return WeatherService()
