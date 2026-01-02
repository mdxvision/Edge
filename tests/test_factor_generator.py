"""
Factor Generator Tests

Tests for the 8-factor analysis system in app/services/factor_generator.py
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

# Import the factor generator and data
from app.services.factor_generator import (
    FactorGenerator,
    COACH_ATS_DATA,
    NBA_REFEREE_DATA,
    get_factor_generator
)


# ============================================================================
# PHASE 1: COACH DNA TESTS
# ============================================================================

class TestCoachDNA:
    """Tests for coach ATS data lookup and scoring"""

    def setup_method(self):
        """Set up test fixtures"""
        self.fg = FactorGenerator()

    def test_nfl_coach_lookup_returns_real_ats_data(self):
        """Test that NFL coach lookup returns real ATS data from Sharp Football"""
        result = self.fg._calculate_coach_dna(
            pick_team="Pittsburgh Steelers",
            pick_type="moneyline",
            line_value=144
        )

        assert result["score"] > 0
        assert "Mike Tomlin" in result["detail"]
        assert "53.6%" in result["detail"]
        assert "(162-140-6)" in result["detail"]
        assert result["data_source"] == "sharp_football"

    def test_nba_coach_lookup_returns_real_ats_data(self):
        """Test that NBA coach lookup returns team ATS data from Covers"""
        result = self.fg._calculate_coach_dna(
            pick_team="Atlanta Hawks",
            pick_type="moneyline",
            line_value=136
        )

        assert result["score"] > 0
        assert "Quin Snyder" in result["detail"]
        assert "48.5%" in result["detail"]
        assert result["data_source"] == "covers_estimate"

    def test_unknown_team_returns_neutral_score(self):
        """Test that unknown team returns neutral score of 50"""
        result = self.fg._calculate_coach_dna(
            pick_team="Unknown Team XYZ",
            pick_type="moneyline",
            line_value=100
        )

        assert result["score"] == 50
        assert "not found" in result["detail"].lower()
        assert result["data_source"] == "no_data"

    def test_score_calculation_from_ats_percentage(self):
        """Test that ATS % is correctly converted to score"""
        # Lions coach Dan Campbell has 61.1% ATS - should be high score
        result = self.fg._calculate_coach_dna(
            pick_team="Detroit Lions",
            pick_type="moneyline",
            line_value=150
        )

        # 61.1% ATS should give score around 50 + (61.1-50)*3.5 = 88.85, capped at 85
        assert result["score"] >= 80
        assert "Dan Campbell" in result["detail"]

    def test_all_nfl_coaches_have_records(self):
        """Test that all NFL coaches in data have win-loss records"""
        nfl_teams = [
            "49ers", "Bears", "Bengals", "Bills", "Broncos", "Browns",
            "Buccaneers", "Cardinals", "Chargers", "Chiefs", "Colts",
            "Commanders", "Cowboys", "Dolphins", "Eagles", "Falcons",
            "Giants", "Jaguars", "Jets", "Lions", "Packers", "Panthers",
            "Patriots", "Raiders", "Rams", "Ravens", "Saints", "Seahawks",
            "Steelers", "Texans", "Titans", "Vikings"
        ]

        for team in nfl_teams:
            assert team in COACH_ATS_DATA, f"{team} missing from COACH_ATS_DATA"
            assert "record" in COACH_ATS_DATA[team], f"{team} missing record"


# ============================================================================
# PHASE 2: REFEREE TESTS
# ============================================================================

class TestReferee:
    """Tests for referee tendency lookup and scoring"""

    def setup_method(self):
        """Set up test fixtures"""
        self.fg = FactorGenerator()
        self.game_time = datetime.now() + timedelta(hours=2)  # Game in 2 hours

    def test_known_nba_referee_returns_tendency_data(self):
        """Test that known NBA referee returns tendency data"""
        result = self.fg._calculate_referee_factor(
            sport="NBA",
            game_time=self.game_time,
            referee_name="Scott Foster",
            pick_is_home=True,
            pick_type="total"
        )

        assert result["score"] > 50  # Scott Foster is OVER ref
        assert "Scott Foster" in result["detail"]
        assert result["data_source"] == "covers_referee_stats"

    def test_unknown_referee_returns_neutral_score(self):
        """Test that unknown referee returns neutral score"""
        result = self.fg._calculate_referee_factor(
            sport="NBA",
            game_time=self.game_time,
            referee_name="Unknown Referee",
            pick_is_home=True,
            pick_type="moneyline"
        )

        assert result["score"] == 50
        assert result["data_source"] == "no_data"

    def test_home_team_advantage_with_home_friendly_ref(self):
        """Test home team gets advantage with home-friendly referee"""
        result = self.fg._calculate_referee_factor(
            sport="NBA",
            game_time=self.game_time,
            referee_name="Curtis Blair",  # 84.2% home ATS
            pick_is_home=True,
            pick_type="moneyline"
        )

        assert result["score"] > 60  # Should be advantageous
        assert "HOME" in result["detail"]

    def test_away_team_disadvantage_with_home_friendly_ref(self):
        """Test away team gets disadvantage with home-friendly referee"""
        result = self.fg._calculate_referee_factor(
            sport="NBA",
            game_time=self.game_time,
            referee_name="Curtis Blair",  # 84.2% home ATS
            pick_is_home=False,
            pick_type="moneyline"
        )

        assert result["score"] < 50  # Should be disadvantageous
        assert "AWAY DISADVANTAGE" in result["detail"]

    def test_officials_not_yet_assigned(self):
        """Test that games >24 hours away show officials not assigned"""
        future_game = datetime.now() + timedelta(hours=30)

        result = self.fg._calculate_referee_factor(
            sport="NBA",
            game_time=future_game,
            referee_name=None,
            pick_is_home=True,
            pick_type="moneyline"
        )

        assert result["score"] == 50
        assert "not yet assigned" in result["detail"].lower()
        assert result["data_source"] == "pending"


# ============================================================================
# PHASE 4: PUBLIC BETTING TESTS
# ============================================================================

class TestPublicBetting:
    """Tests for public betting percentage calculations"""

    def setup_method(self):
        """Set up test fixtures"""
        self.fg = FactorGenerator()

    def test_contrarian_value_low_public(self):
        """Test that ≤35% public gives high contrarian score"""
        result = self.fg._calculate_public_betting(
            pick_team="Hawks",
            line_value=136,
            public_pct=30
        )

        assert result["score"] >= 70
        assert "CONTRARIAN" in result["detail"]
        assert result["data_source"] == "action_network"

    def test_slight_contrarian(self):
        """Test that 36-45% public gives slight contrarian score"""
        result = self.fg._calculate_public_betting(
            pick_team="Hawks",
            line_value=136,
            public_pct=40
        )

        assert result["score"] == 60
        assert "contrarian" in result["detail"].lower()

    def test_balanced_action(self):
        """Test that 46-54% public gives neutral score"""
        result = self.fg._calculate_public_betting(
            pick_team="Hawks",
            line_value=136,
            public_pct=50
        )

        assert result["score"] == 50
        assert "balanced" in result["detail"].lower()

    def test_public_side(self):
        """Test that 55-69% public gives lower score"""
        result = self.fg._calculate_public_betting(
            pick_team="Hawks",
            line_value=-150,
            public_pct=65
        )

        assert result["score"] < 50
        assert "public side" in result["detail"].lower() or "public on" in result["detail"].lower()

    def test_heavy_chalk_warning(self):
        """Test that ≥70% public gives warning and low score"""
        result = self.fg._calculate_public_betting(
            pick_team="Chiefs",
            line_value=-200,
            public_pct=75
        )

        assert result["score"] <= 35
        assert "WARNING" in result["detail"] or "HEAVY" in result["detail"]

    def test_estimate_when_no_data_underdog(self):
        """Test estimate for underdog when no public % provided"""
        result = self.fg._calculate_public_betting(
            pick_team="Hawks",
            line_value=136,  # Underdog
            public_pct=None
        )

        assert result["score"] >= 60  # Underdogs typically contrarian
        assert "Estimated" in result["detail"] or "underdog" in result["detail"].lower()
        assert result["data_source"] == "line_estimate"


# ============================================================================
# PHASE 5: WEATHER TESTS
# ============================================================================

class TestWeather:
    """Tests for weather impact calculations"""

    def setup_method(self):
        """Set up test fixtures"""
        self.fg = FactorGenerator()

    @pytest.mark.asyncio
    async def test_indoor_sport_returns_neutral(self):
        """Test that indoor sports return neutral weather score"""
        result = await self.fg._calculate_weather_factor(
            sport="NBA",
            home_team="Hawks",
            game_time=datetime.now(),
            weather_data=None
        )

        assert result["score"] == 50
        assert "indoor" in result["detail"].lower()

    @pytest.mark.asyncio
    async def test_outdoor_sport_no_weather_data(self):
        """Test outdoor sport with no weather data"""
        result = await self.fg._calculate_weather_factor(
            sport="NFL",
            home_team="Chiefs",
            game_time=datetime.now(),
            weather_data=None
        )

        assert result["score"] == 50  # Neutral when no data


# ============================================================================
# PHASE 6: TRAVEL TESTS
# ============================================================================

class TestTravel:
    """Tests for travel distance calculations"""

    def setup_method(self):
        """Set up test fixtures"""
        self.fg = FactorGenerator()

    def test_home_team_returns_advantage(self):
        """Test that home team gets travel advantage"""
        result = self.fg._calculate_travel_factor(
            pick_team="Atlanta Hawks",
            home_team="Atlanta Hawks",
            away_team="Los Angeles Lakers"
        )

        assert result["score"] >= 60
        assert "home" in result["detail"].lower()

    def test_away_team_long_travel(self):
        """Test away team with long travel gets penalty"""
        result = self.fg._calculate_travel_factor(
            pick_team="Los Angeles Lakers",
            home_team="Boston Celtics",
            away_team="Los Angeles Lakers"
        )

        # LA to Boston is ~2600 miles - should be disadvantage
        assert result["score"] <= 50


# ============================================================================
# PHASE 7: LINE MOVEMENT TESTS
# ============================================================================

class TestLineMovement:
    """Tests for line movement calculations"""

    def setup_method(self):
        """Set up test fixtures"""
        self.fg = FactorGenerator()

    def test_returns_neutral_when_no_data(self):
        """Test that line movement returns neutral when no data"""
        result = self.fg._calculate_line_movement(
            pick_type="moneyline",
            line_value=136,
            opening_line=None,
            current_line=None
        )

        assert result["score"] == 50
        assert result["data_source"] == "awaiting_data"

    def test_awaiting_data_indicator(self):
        """Test that awaiting_data source is indicated"""
        result = self.fg._calculate_line_movement(
            pick_type="spread",
            line_value=-3.5,
            opening_line=None,
            current_line=None
        )

        assert "awaiting_data" in result.get("data_source", "")
        assert "pending" in result["detail"].lower() or "awaiting" in result["detail"].lower()


# ============================================================================
# PHASE 8: SITUATIONAL TESTS
# ============================================================================

class TestSituational:
    """Tests for situational trend calculations"""

    def setup_method(self):
        """Set up test fixtures"""
        self.fg = FactorGenerator()
        self.game_time = datetime.now()

    def test_big_underdog_situation(self):
        """Test big underdog gets situational consideration"""
        result = self.fg._calculate_situational_factor(
            sport="NBA",
            pick_team="Hawks",
            pick_type="moneyline",
            line_value=200,  # Big underdog
            game_time=self.game_time
        )

        assert result["score"] > 0
        assert "underdog" in result["detail"].lower()

    def test_favorite_situation(self):
        """Test favorite gets situational consideration"""
        result = self.fg._calculate_situational_factor(
            sport="NBA",
            pick_team="Celtics",
            pick_type="moneyline",
            line_value=-200,  # Big favorite
            game_time=self.game_time
        )

        assert result["score"] > 0
        assert "favorite" in result["detail"].lower()

    def test_weekend_game_detection(self):
        """Test weekend game is detected"""
        # Find a Saturday
        saturday = datetime.now()
        while saturday.weekday() != 5:  # 5 = Saturday
            saturday += timedelta(days=1)

        result = self.fg._calculate_situational_factor(
            sport="NFL",
            pick_team="Steelers",
            pick_type="moneyline",
            line_value=144,
            game_time=saturday
        )

        assert result["score"] > 0
        # Weekend games may have different patterns


# ============================================================================
# PHASE 9: INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for full factor generation"""

    def setup_method(self):
        """Set up test fixtures"""
        self.fg = FactorGenerator()

    @pytest.mark.asyncio
    async def test_full_factor_generation_nba(self):
        """Test full factor generation for NBA game"""
        factors = await self.fg.generate_factors(
            sport="NBA",
            home_team="Atlanta Hawks",
            away_team="Minnesota Timberwolves",
            pick_team="Atlanta Hawks",
            pick_type="moneyline",
            line_value=136,
            game_time=datetime.now() + timedelta(hours=2)
        )

        # Should have all 8 factors
        expected_factors = [
            "coach_dna", "referee", "weather", "line_movement",
            "rest", "travel", "situational", "public_betting"
        ]

        for factor in expected_factors:
            assert factor in factors, f"Missing factor: {factor}"
            assert "score" in factors[factor], f"Missing score in {factor}"
            assert "detail" in factors[factor], f"Missing detail in {factor}"

    @pytest.mark.asyncio
    async def test_full_factor_generation_nfl(self):
        """Test full factor generation for NFL game"""
        factors = await self.fg.generate_factors(
            sport="NFL",
            home_team="Pittsburgh Steelers",
            away_team="Baltimore Ravens",
            pick_team="Pittsburgh Steelers",
            pick_type="moneyline",
            line_value=144,
            game_time=datetime.now() + timedelta(days=4)
        )

        # Should have all 8 factors
        assert len(factors) == 8

        # Coach DNA should have real Tomlin data
        assert "Tomlin" in factors["coach_dna"]["detail"]

    @pytest.mark.asyncio
    async def test_all_factors_have_valid_scores(self):
        """Test all factors return valid scores between 0-100"""
        factors = await self.fg.generate_factors(
            sport="NBA",
            home_team="Boston Celtics",
            away_team="Los Angeles Lakers",
            pick_team="Boston Celtics",
            pick_type="moneyline",
            line_value=-150,
            game_time=datetime.now() + timedelta(hours=3)
        )

        for name, factor in factors.items():
            score = factor["score"]
            assert 0 <= score <= 100, f"{name} has invalid score: {score}"

    @pytest.mark.asyncio
    async def test_average_score_calculation(self):
        """Test that average score can be calculated from factors"""
        factors = await self.fg.generate_factors(
            sport="NBA",
            home_team="Atlanta Hawks",
            away_team="Minnesota Timberwolves",
            pick_team="Atlanta Hawks",
            pick_type="moneyline",
            line_value=136,
            game_time=datetime.now() + timedelta(hours=2)
        )

        scores = [f["score"] for f in factors.values()]
        avg = sum(scores) / len(scores)

        assert 0 <= avg <= 100
        assert len(scores) == 8

    @pytest.mark.asyncio
    async def test_with_public_betting_pct_parameter(self):
        """Test factor generation with public betting percentage"""
        factors = await self.fg.generate_factors(
            sport="NBA",
            home_team="Atlanta Hawks",
            away_team="Minnesota Timberwolves",
            pick_team="Atlanta Hawks",
            pick_type="moneyline",
            line_value=136,
            game_time=datetime.now() + timedelta(hours=2),
            public_betting_pct=40  # 40% on Hawks
        )

        # Public betting should show Action Network source
        pb = factors["public_betting"]
        assert pb["data_source"] == "action_network"
        assert pb["score"] == 60  # 40% is slight contrarian
        assert "40%" in pb["detail"]


# ============================================================================
# DATA VALIDATION TESTS
# ============================================================================

class TestDataValidation:
    """Tests to validate static data integrity"""

    def test_coach_data_has_required_fields(self):
        """Test all coach entries have required fields"""
        required_fields = ["coach", "ats_pct", "situation_detail"]

        for team, data in COACH_ATS_DATA.items():
            for field in required_fields:
                assert field in data, f"{team} missing {field}"

            # ATS % should be between 30-75
            assert 30 <= data["ats_pct"] <= 75, f"{team} has invalid ATS %: {data['ats_pct']}"

    def test_referee_data_has_required_fields(self):
        """Test all referee entries have required fields"""
        for ref, data in NBA_REFEREE_DATA.items():
            assert "tendency" in data, f"{ref} missing tendency"

            # Should have either ou_pct or home_ats_pct
            has_ou = "ou_pct" in data
            has_home = "home_ats_pct" in data
            assert has_ou or has_home, f"{ref} missing percentage data"

    def test_all_30_nba_teams_have_coach_data(self):
        """Test all 30 NBA teams have coach data"""
        nba_teams = [
            "Hawks", "Celtics", "Nets", "Hornets", "Bulls",
            "Cavaliers", "Mavericks", "Nuggets", "Pistons", "Warriors",
            "Rockets", "Pacers", "Clippers", "Lakers", "Grizzlies",
            "Heat", "Bucks", "Timberwolves", "Pelicans", "Knicks",
            "Thunder", "Magic", "76ers", "Suns", "Trail Blazers",
            "Kings", "Spurs", "Raptors", "Jazz", "Wizards"
        ]

        for team in nba_teams:
            assert team in COACH_ATS_DATA, f"NBA team {team} missing from COACH_ATS_DATA"
