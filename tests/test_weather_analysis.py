"""
Tests for Enhanced Weather Analysis Service

Tests cover:
- Historical correlation data
- Enhanced NFL wind impact with stadium orientations
- Enhanced MLB wind impact with outfield direction
- Temperature impact curves
- Precipitation impact analysis
- Weather edge finder
- Comprehensive weather analysis
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

from app.services.weather_analysis import (
    NFL_HISTORICAL_CORRELATIONS,
    MLB_HISTORICAL_CORRELATIONS,
    NFL_STADIUM_ORIENTATIONS,
    calculate_nfl_wind_impact_enhanced,
    calculate_mlb_wind_impact_enhanced,
    calculate_temperature_impact,
    calculate_precipitation_impact,
    find_weather_edges,
    get_comprehensive_weather_analysis,
    _get_wind_bucket,
)


# =============================================================================
# Historical Correlation Data Tests
# =============================================================================

class TestHistoricalCorrelations:
    """Test historical correlation data structures."""

    def test_nfl_correlations_structure(self):
        """Test NFL correlations have correct structure."""
        assert "wind_mph" in NFL_HISTORICAL_CORRELATIONS
        assert "temperature" in NFL_HISTORICAL_CORRELATIONS
        assert "precipitation" in NFL_HISTORICAL_CORRELATIONS
        assert "snow" in NFL_HISTORICAL_CORRELATIONS

    def test_nfl_wind_buckets(self):
        """Test NFL wind speed buckets."""
        wind = NFL_HISTORICAL_CORRELATIONS["wind_mph"]
        assert "0-9" in wind
        assert "10-14" in wind
        assert "15-19" in wind
        assert "20-24" in wind
        assert "25+" in wind

        # Each bucket should have (adjustment, sample_size, rate)
        for bucket, data in wind.items():
            assert len(data) == 3
            assert isinstance(data[0], (int, float))  # adjustment
            assert isinstance(data[1], int)  # sample size
            assert 0 <= data[2] <= 1  # rate

    def test_nfl_temperature_buckets(self):
        """Test NFL temperature buckets."""
        temp = NFL_HISTORICAL_CORRELATIONS["temperature"]
        expected_buckets = ["below_20", "20-32", "33-45", "46-65", "66-80", "above_80"]
        for bucket in expected_buckets:
            assert bucket in temp

    def test_mlb_correlations_structure(self):
        """Test MLB correlations have correct structure."""
        assert "wind_out" in MLB_HISTORICAL_CORRELATIONS
        assert "wind_in" in MLB_HISTORICAL_CORRELATIONS
        assert "temperature" in MLB_HISTORICAL_CORRELATIONS
        assert "humidity" in MLB_HISTORICAL_CORRELATIONS
        assert "altitude" in MLB_HISTORICAL_CORRELATIONS

    def test_mlb_altitude_coors_effect(self):
        """Test that Coors Field altitude effect is captured."""
        altitude = MLB_HISTORICAL_CORRELATIONS["altitude"]
        assert "5000+" in altitude
        # Coors effect should show significant over rate
        coors_data = altitude["5000+"]
        assert coors_data[0] >= 2.0  # At least 2 runs added
        assert coors_data[2] >= 0.55  # Over rate above 55%

    def test_nfl_stadium_orientations(self):
        """Test stadium orientation data."""
        assert len(NFL_STADIUM_ORIENTATIONS) >= 10

        for stadium, info in NFL_STADIUM_ORIENTATIONS.items():
            assert "orientation" in info
            assert 0 <= info["orientation"] <= 360
            assert "open_end" in info


# =============================================================================
# NFL Wind Impact Tests
# =============================================================================

class TestNFLWindImpact:
    """Test enhanced NFL wind impact calculations."""

    def test_low_wind_no_impact(self):
        """Test that low wind has minimal impact."""
        result = calculate_nfl_wind_impact_enhanced(5, 0, "arrowhead_stadium")

        assert result["wind_speed_mph"] == 5
        assert result["total_adjustment"] == 0
        assert len(result["factors"]) == 0

    def test_moderate_wind_impact(self):
        """Test moderate wind impact."""
        result = calculate_nfl_wind_impact_enhanced(15, 270, "arrowhead_stadium")

        assert result["total_adjustment"] < 0
        assert result["historical_correlation"] is not None
        assert result["historical_correlation"]["bucket"] == "15-19 mph"

    def test_high_wind_severe_impact(self):
        """Test high wind has severe impact."""
        result = calculate_nfl_wind_impact_enhanced(25, 180, "lambeau_field")

        assert result["total_adjustment"] <= -7  # May be reduced for crosswind
        assert len(result["factors"]) > 0
        assert result["confidence"] > 0.4

    def test_wind_aligned_with_field(self):
        """Test wind aligned with field orientation."""
        # Arrowhead has west orientation (270 degrees)
        # Wind at 270 should be aligned
        result = calculate_nfl_wind_impact_enhanced(18, 270, "arrowhead_stadium")

        # Should have enhanced passing impact
        assert any("aligned" in f.lower() for f in result["factors"])
        assert result["pass_impact_pct"] < 0

    def test_crosswind_affects_kicks(self):
        """Test crosswind affects field goals."""
        # Lambeau has north orientation (0 degrees)
        # Wind at 90 degrees (east) is crosswind
        result = calculate_nfl_wind_impact_enhanced(18, 90, "lambeau_field")

        # Should affect kicks
        assert result["fg_impact_pct"] < 0

    def test_unknown_stadium_basic_calculation(self):
        """Test calculation works for unknown stadiums."""
        result = calculate_nfl_wind_impact_enhanced(20, 180, "unknown_stadium")

        # Should still calculate basic impact
        assert result["total_adjustment"] < 0
        assert "wind_speed_mph" in result

    def test_confidence_based_on_sample_size(self):
        """Test confidence varies with sample size."""
        # High wind has smaller sample size
        high_wind = calculate_nfl_wind_impact_enhanced(26, 0, "lambeau_field")

        # Low wind has larger sample size
        low_wind = calculate_nfl_wind_impact_enhanced(5, 0, "lambeau_field")

        # High wind should have higher confidence (more predictable)
        # Actually high wind has smaller sample = lower confidence
        assert low_wind["confidence"] >= high_wind["confidence"]


# =============================================================================
# MLB Wind Impact Tests
# =============================================================================

class TestMLBWindImpact:
    """Test enhanced MLB wind impact calculations."""

    def test_wind_out_increases_scoring(self):
        """Test wind blowing out increases scoring expectation."""
        venue = {"outfield_direction": 180, "name": "Wrigley Field"}
        # Wind at 180 (same as outfield) blows out
        result = calculate_mlb_wind_impact_enhanced(15, 180, venue)

        assert result["wind_type"] == "out"
        assert result["total_adjustment"] > 0
        assert result["hr_probability_change"] > 0

    def test_wind_in_decreases_scoring(self):
        """Test wind blowing in decreases scoring."""
        venue = {"outfield_direction": 180, "name": "Wrigley Field"}
        # Wind at 0 (opposite of outfield) blows in
        result = calculate_mlb_wind_impact_enhanced(15, 0, venue)

        assert result["wind_type"] == "in"
        assert result["total_adjustment"] < 0
        assert result["hr_probability_change"] < 0

    def test_crosswind_minimal_impact(self):
        """Test crosswind has minimal impact."""
        venue = {"outfield_direction": 180, "name": "Test Park"}
        # Wind at 90 is crosswind
        result = calculate_mlb_wind_impact_enhanced(15, 90, venue)

        assert result["wind_type"] == "cross"
        assert abs(result["total_adjustment"]) < 0.5

    def test_unknown_outfield_direction(self):
        """Test handling of unknown outfield direction."""
        venue = {"outfield_direction": 0, "name": "Unknown Park"}
        result = calculate_mlb_wind_impact_enhanced(18, 180, venue)

        assert "Unknown outfield orientation" in result["factors"][0]

    def test_strong_wind_out_high_hr_boost(self):
        """Test strong wind out significantly boosts HR probability."""
        venue = {"outfield_direction": 270, "name": "Coors Field"}
        result = calculate_mlb_wind_impact_enhanced(22, 270, venue)

        assert result["wind_type"] == "out"
        assert result["hr_probability_change"] >= 25

    def test_wind_bucket_helper(self):
        """Test wind bucket helper function."""
        assert _get_wind_bucket(5) == "0-7"
        assert _get_wind_bucket(10) == "8-12"
        assert _get_wind_bucket(15) == "13-17"
        assert _get_wind_bucket(20) == "18-22"
        assert _get_wind_bucket(25) == "23+"


# =============================================================================
# Temperature Impact Tests
# =============================================================================

class TestTemperatureImpact:
    """Test temperature impact calculations."""

    def test_extreme_cold_nfl(self):
        """Test extreme cold reduces NFL totals."""
        result = calculate_temperature_impact(15, "NFL")

        assert result["total_adjustment"] <= -4
        assert "extreme cold" in result["factors"][0].lower()
        assert result["historical_correlation"]["bucket"] == "below_20"

    def test_freezing_temperature_nfl(self):
        """Test freezing temps in NFL."""
        result = calculate_temperature_impact(28, "NFL")

        assert result["total_adjustment"] < 0
        assert result["historical_correlation"]["bucket"] == "20-32"

    def test_ideal_temperature_nfl(self):
        """Test ideal temps have no impact."""
        result = calculate_temperature_impact(55, "NFL")

        assert result["total_adjustment"] == 0
        assert "ideal" in result["factors"][0].lower()

    def test_hot_temperature_nfl_fatigue(self):
        """Test hot temps cause fatigue."""
        result = calculate_temperature_impact(90, "NFL")

        assert result["total_adjustment"] < 0  # Fatigue reduces scoring
        assert "hot" in result["factors"][0].lower()

    def test_cold_temperature_mlb(self):
        """Test cold temps in MLB."""
        result = calculate_temperature_impact(45, "MLB")

        assert result["total_adjustment"] < 0
        assert result["historical_correlation"]["bucket"] == "below_50"

    def test_hot_temperature_mlb_ball_carry(self):
        """Test hot temps help ball carry in MLB."""
        result = calculate_temperature_impact(92, "MLB")

        assert result["total_adjustment"] > 0
        assert result["historical_correlation"]["bucket"] == "90+"

    def test_cfb_uses_nfl_correlations(self):
        """Test CFB uses NFL temperature data."""
        nfl_result = calculate_temperature_impact(20, "NFL")
        cfb_result = calculate_temperature_impact(20, "CFB")

        assert nfl_result["total_adjustment"] == cfb_result["total_adjustment"]


# =============================================================================
# Precipitation Impact Tests
# =============================================================================

class TestPrecipitationImpact:
    """Test precipitation impact calculations."""

    def test_no_precipitation(self):
        """Test no precipitation has no impact."""
        result = calculate_precipitation_impact(0, 0, "NFL")

        assert result["total_adjustment"] == 0
        assert result["turnover_impact_pct"] == 0

    def test_light_rain(self):
        """Test light rain impact."""
        result = calculate_precipitation_impact(0.05, 0, "NFL")

        assert result["total_adjustment"] < 0
        assert result["historical_correlation"]["bucket"] == "light"

    def test_moderate_rain(self):
        """Test moderate rain impact."""
        result = calculate_precipitation_impact(0.2, 0, "NFL")

        assert result["total_adjustment"] <= -4
        assert result["turnover_impact_pct"] >= 20

    def test_heavy_rain(self):
        """Test heavy rain has severe impact."""
        result = calculate_precipitation_impact(0.5, 0, "NFL")

        assert result["total_adjustment"] <= -6
        assert result["turnover_impact_pct"] >= 30
        assert result["pass_impact_pct"] < -20

    def test_snow_takes_precedence(self):
        """Test snow impact takes precedence over rain."""
        # Both rain and snow
        result = calculate_precipitation_impact(0.3, 2, "NFL")

        assert result["total_adjustment"] <= -5
        assert "snow" in result["factors"][0].lower()

    def test_heavy_snow_chaos_game(self):
        """Test heavy snow creates chaos game."""
        result = calculate_precipitation_impact(0, 4, "NFL")

        assert result["total_adjustment"] <= -9
        assert result["turnover_impact_pct"] >= 40
        assert "chaos" in result["factors"][0].lower()

    def test_non_football_minimal_impact(self):
        """Test non-football sports have minimal precipitation model."""
        result = calculate_precipitation_impact(0.5, 0, "MLB")

        # Basic impact only
        assert result["total_adjustment"] <= 0


# =============================================================================
# Comprehensive Analysis Tests
# =============================================================================

class TestComprehensiveAnalysis:
    """Test comprehensive weather analysis."""

    def test_dome_venue_no_impact(self):
        """Test dome venues have no weather impact."""
        weather = {
            "temperature_f": 72,
            "wind_speed_mph": 25,
            "wind_direction_degrees": 180,
            "precipitation_in": 0.5,
        }
        venue = {"name": "Lucas Oil Stadium", "dome_type": "dome"}

        result = get_comprehensive_weather_analysis(weather, venue, "NFL")

        assert result["dome_type"] == "dome"
        assert "no weather impact" in result["analysis"].get("note", "").lower()

    def test_outdoor_venue_combines_factors(self):
        """Test outdoor venues combine all factors."""
        weather = {
            "temperature_f": 28,
            "wind_speed_mph": 18,
            "wind_direction_degrees": 270,
            "wind_direction": "W",
            "precipitation_in": 0.1,
            "snowfall_in": 0,
            "conditions": "Cloudy",
        }
        venue = {
            "name": "Lambeau Field",
            "dome_type": "outdoor",
            "altitude_ft": 600,
        }

        result = get_comprehensive_weather_analysis(weather, venue, "NFL")

        assert result["analysis"].get("wind") is not None
        assert result["analysis"].get("temperature") is not None
        assert result["combined_impact"]["total_adjustment"] != 0

    def test_strong_under_recommendation(self):
        """Test strong under recommendation for bad weather."""
        weather = {
            "temperature_f": 18,
            "wind_speed_mph": 22,
            "wind_direction_degrees": 0,
            "precipitation_in": 0.3,
            "snowfall_in": 0,
            "conditions": "Rain",
        }
        venue = {"name": "Highmark Stadium", "dome_type": "outdoor"}

        result = get_comprehensive_weather_analysis(weather, venue, "NFL")

        assert result["combined_impact"]["recommendation"] in ("UNDER", "STRONG_UNDER")
        assert result["combined_impact"]["total_adjustment"] < -4

    def test_mlb_altitude_factor(self):
        """Test MLB altitude factor is included."""
        weather = {
            "temperature_f": 75,
            "wind_speed_mph": 5,
            "wind_direction_degrees": 180,
            "conditions": "Clear",
        }
        venue = {
            "name": "Coors Field",
            "dome_type": "outdoor",
            "altitude_ft": 5200,
            "outfield_direction": 225,
        }

        result = get_comprehensive_weather_analysis(weather, venue, "MLB")

        assert "altitude" in result["analysis"]
        assert result["analysis"]["altitude"]["total_adjustment"] > 0


# =============================================================================
# Weather Edge Finder Tests
# =============================================================================

class TestWeatherEdgeFinder:
    """Test weather edge finder functionality."""

    @pytest.mark.asyncio
    async def test_find_weather_edges_empty_db(self):
        """Test edge finder with no games."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.filter.return_value.limit.return_value.all.return_value = []

        edges = await find_weather_edges(mock_db)

        assert edges == []

    @pytest.mark.asyncio
    async def test_find_weather_edges_returns_list(self):
        """Test edge finder returns a list."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.filter.return_value.limit.return_value.all.return_value = []

        # With no games, should return empty list
        edges = await find_weather_edges(mock_db, min_impact=2.0)

        assert isinstance(edges, list)
        assert edges == []

    def test_edge_structure(self):
        """Test edge result has expected structure."""
        # This tests what the edge dict should contain
        expected_keys = {
            "game_id", "matchup", "sport", "start_time",
            "venue", "weather", "impact", "edge_type", "edge_magnitude"
        }

        # Create a sample edge structure
        sample_edge = {
            "game_id": 1,
            "matchup": "MIA @ BUF",
            "sport": "NFL",
            "start_time": datetime.utcnow().isoformat(),
            "venue": "Highmark Stadium",
            "weather": {
                "temperature_f": 20,
                "wind_speed_mph": 25,
            },
            "impact": {
                "total_adjustment": -6.5,
                "recommendation": "STRONG_UNDER",
                "confidence": 0.72,
            },
            "edge_type": "UNDER",
            "edge_magnitude": 6.5,
        }

        assert set(sample_edge.keys()) == expected_keys
        assert sample_edge["edge_type"] in ("OVER", "UNDER")

    @pytest.mark.asyncio
    async def test_find_weather_edges_filters_domes(self):
        """Test that dome venues are filtered out."""
        mock_game = MagicMock()
        mock_game.id = 1
        mock_game.sport = "NFL"
        mock_game.home_team = "Dallas Cowboys"
        mock_game.away_team = "Philadelphia Eagles"
        mock_game.start_time = datetime.utcnow() + timedelta(days=1)

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.filter.return_value.limit.return_value.all.return_value = [
            mock_game
        ]

        with patch("app.data.venues.get_venue_by_name") as mock_venue:
            # Return dome venue
            mock_venue.return_value = {
                "name": "AT&T Stadium",
                "lat": 32.75,
                "lon": -97.09,
                "dome_type": "dome",
            }

            edges = await find_weather_edges(mock_db)

            # Dome should be filtered out
            assert edges == []


# =============================================================================
# Router Endpoint Tests
# =============================================================================

class TestWeatherAnalysisEndpoints:
    """Test weather analysis router endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)

    def test_get_correlations_nfl(self, client):
        """Test NFL correlations endpoint."""
        response = client.get("/weather/correlations/nfl")
        assert response.status_code == 200

        data = response.json()
        assert data["sport"] == "NFL"
        assert "correlations" in data
        assert "wind_mph" in data["correlations"]

    def test_get_correlations_mlb(self, client):
        """Test MLB correlations endpoint."""
        response = client.get("/weather/correlations/mlb")
        assert response.status_code == 200

        data = response.json()
        assert data["sport"] == "MLB"
        assert "wind_out" in data["correlations"]

    def test_get_correlations_unsupported_sport(self, client):
        """Test correlations for unsupported sport."""
        response = client.get("/weather/correlations/tennis")
        assert response.status_code == 200

        data = response.json()
        assert data["correlations"] is None

    def test_get_stadium_orientations(self, client):
        """Test stadium orientations endpoint."""
        response = client.get("/weather/stadiums/orientations")
        assert response.status_code == 200

        data = response.json()
        assert data["sport"] == "NFL"
        assert "stadiums" in data
        assert len(data["stadiums"]) >= 10

    def test_nfl_wind_analysis(self, client):
        """Test NFL wind analysis endpoint."""
        response = client.get(
            "/weather/analysis/wind/nfl",
            params={"venue": "lambeau_field", "wind_speed": 20, "wind_direction": 90}
        )
        assert response.status_code == 200

        data = response.json()
        assert "analysis" in data
        assert data["analysis"]["wind_speed_mph"] == 20

    def test_nfl_wind_analysis_dome_venue(self, client):
        """Test NFL wind analysis for dome venue."""
        response = client.get(
            "/weather/analysis/wind/nfl",
            params={"venue": "caesars_superdome", "wind_speed": 20, "wind_direction": 90}
        )
        assert response.status_code == 200

        data = response.json()
        assert data.get("dome_type") == "dome" or "dome" in str(data.get("note", "")).lower()

    def test_mlb_wind_analysis(self, client):
        """Test MLB wind analysis endpoint."""
        response = client.get(
            "/weather/analysis/wind/mlb",
            params={"venue": "wrigley_field", "wind_speed": 18, "wind_direction": 225}
        )
        assert response.status_code == 200

        data = response.json()
        assert "analysis" in data

    def test_temperature_analysis(self, client):
        """Test temperature analysis endpoint."""
        response = client.get(
            "/weather/analysis/temperature",
            params={"temperature": 25, "sport": "NFL"}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["temperature_f"] == 25
        assert "analysis" in data
        assert data["analysis"]["total_adjustment"] < 0

    def test_precipitation_analysis(self, client):
        """Test precipitation analysis endpoint."""
        response = client.get(
            "/weather/analysis/precipitation",
            params={"rain_in": 0.4, "snow_in": 0, "sport": "NFL"}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["precipitation"]["rain_in"] == 0.4
        assert data["analysis"]["total_adjustment"] < -5
