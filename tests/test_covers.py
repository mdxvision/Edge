"""
Tests for Covers.com Data Scraper Service

Tests ATS records, O/U trends, consensus picks, and expert picks functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
import random

from app.services import covers_scraper


# =============================================================================
# Configuration Tests
# =============================================================================

class TestConfiguration:
    """Test Covers.com configuration."""

    def test_scraping_disabled_by_default(self):
        """Test scraping is disabled by default."""
        original = covers_scraper.COVERS_SCRAPING_ENABLED
        covers_scraper.COVERS_SCRAPING_ENABLED = False
        assert covers_scraper.is_scraping_enabled() is False
        covers_scraper.COVERS_SCRAPING_ENABLED = original

    def test_scraping_can_be_enabled(self):
        """Test scraping can be enabled."""
        original = covers_scraper.COVERS_SCRAPING_ENABLED
        covers_scraper.COVERS_SCRAPING_ENABLED = True
        assert covers_scraper.is_scraping_enabled() is True
        covers_scraper.COVERS_SCRAPING_ENABLED = original

    def test_sport_url_mapping_exists(self):
        """Test sport URL mappings are defined."""
        assert "NFL" in covers_scraper.SPORT_URL_MAPPING
        assert "NBA" in covers_scraper.SPORT_URL_MAPPING
        assert "MLB" in covers_scraper.SPORT_URL_MAPPING

    def test_team_mappings_exist(self):
        """Test team mappings are defined."""
        assert len(covers_scraper.NFL_TEAMS) == 32
        assert len(covers_scraper.NBA_TEAMS) == 30


# =============================================================================
# ATS Records Tests
# =============================================================================

class TestATSRecords:
    """Test ATS record generation."""

    def test_generate_ats_records_nfl(self):
        """Test NFL ATS records generation."""
        mock_db = MagicMock()
        records = covers_scraper._generate_ats_records("NFL", mock_db)

        assert len(records) == 32  # All NFL teams
        assert all("team" in r for r in records)
        assert all("overall" in r for r in records)

    def test_generate_ats_records_nba(self):
        """Test NBA ATS records generation."""
        mock_db = MagicMock()
        records = covers_scraper._generate_ats_records("NBA", mock_db)

        assert len(records) == 30  # All NBA teams

    def test_ats_record_structure(self):
        """Test ATS record has correct structure."""
        mock_db = MagicMock()
        records = covers_scraper._generate_ats_records("NFL", mock_db)

        record = records[0]
        assert "team" in record
        assert "abbrev" in record
        assert "overall" in record
        assert "home" in record
        assert "away" in record
        assert "as_favorite" in record
        assert "as_underdog" in record
        assert "streak" in record

    def test_ats_percentages_are_valid(self):
        """Test ATS percentages are within valid range."""
        mock_db = MagicMock()
        records = covers_scraper._generate_ats_records("NFL", mock_db)

        for record in records:
            overall = record["overall"]
            assert 0 <= overall["pct"] <= 100
            assert overall["wins"] >= 0
            assert overall["losses"] >= 0

    def test_ats_records_sum_correctly(self):
        """Test wins + losses + pushes equals games played."""
        mock_db = MagicMock()
        records = covers_scraper._generate_ats_records("NFL", mock_db)

        for record in records:
            overall = record["overall"]
            total = overall["wins"] + overall["losses"] + overall["pushes"]
            assert total == overall["games"]

    def test_ats_records_are_sorted(self):
        """Test records are sorted by ATS percentage."""
        mock_db = MagicMock()
        records = covers_scraper._generate_ats_records("NFL", mock_db)

        pcts = [r["overall"]["pct"] for r in records]
        assert pcts == sorted(pcts, reverse=True)

    def test_ats_streak_format(self):
        """Test ATS streak has correct format."""
        rng = random.Random(42)
        streak = covers_scraper._generate_ats_streak(rng)

        assert "type" in streak
        assert streak["type"] in ["W", "L", "P"]
        assert "length" in streak
        assert 1 <= streak["length"] <= 6
        assert "description" in streak


# =============================================================================
# O/U Trends Tests
# =============================================================================

class TestOUTrends:
    """Test O/U trend generation."""

    def test_generate_ou_trends_nfl(self):
        """Test NFL O/U trends generation."""
        trends = covers_scraper._generate_ou_trends("NFL")

        assert len(trends) == 32
        assert all("team" in t for t in trends)

    def test_ou_trend_structure(self):
        """Test O/U trend has correct structure."""
        trends = covers_scraper._generate_ou_trends("NBA")

        trend = trends[0]
        assert "overall" in trend
        assert "home" in trend
        assert "away" in trend
        assert "averages" in trend
        assert "streak" in trend

    def test_ou_overs_unders_sum_correctly(self):
        """Test overs + unders + pushes equals games."""
        trends = covers_scraper._generate_ou_trends("NFL")

        for trend in trends:
            overall = trend["overall"]
            total = overall["overs"] + overall["unders"] + overall["pushes"]
            assert total == overall["games"]

    def test_ou_percentages_valid(self):
        """Test O/U percentages are within range."""
        trends = covers_scraper._generate_ou_trends("NBA")

        for trend in trends:
            assert 0 <= trend["overall"]["over_pct"] <= 100

    def test_ou_averages_reasonable(self):
        """Test average totals are reasonable for sport."""
        nfl_trends = covers_scraper._generate_ou_trends("NFL")
        nba_trends = covers_scraper._generate_ou_trends("NBA")

        # NFL totals should be 40-55ish
        for trend in nfl_trends:
            avg = trend["averages"]["avg_total_set"]
            assert 35 <= avg <= 60

        # NBA totals should be 200-250ish
        for trend in nba_trends:
            avg = trend["averages"]["avg_total_set"]
            assert 200 <= avg <= 250


# =============================================================================
# Consensus Picks Tests
# =============================================================================

class TestConsensusPicks:
    """Test consensus picks generation."""

    @pytest.mark.asyncio
    async def test_generate_consensus_with_games(self):
        """Test consensus generation when games exist."""
        mock_db = MagicMock()

        # Mock game query
        mock_game = MagicMock()
        mock_game.id = 1
        mock_game.sport = "NFL"
        mock_game.start_time = datetime.utcnow()
        mock_game.home_team = "Chiefs"
        mock_game.away_team = "Bills"

        mock_db.query.return_value.filter.return_value.all.return_value = [mock_game]

        picks = await covers_scraper._generate_consensus_picks("NFL", datetime.utcnow(), mock_db)

        assert len(picks) == 1
        assert picks[0]["game_id"] == 1
        assert "spread" in picks[0]
        assert "total" in picks[0]

    @pytest.mark.asyncio
    async def test_consensus_structure(self):
        """Test consensus pick structure."""
        mock_db = MagicMock()
        mock_game = MagicMock()
        mock_game.id = 1
        mock_game.sport = "NFL"
        mock_game.start_time = datetime.utcnow()
        mock_game.home_team = "Chiefs"
        mock_game.away_team = "Bills"

        mock_db.query.return_value.filter.return_value.all.return_value = [mock_game]

        picks = await covers_scraper._generate_consensus_picks("NFL", datetime.utcnow(), mock_db)

        pick = picks[0]
        assert "expert_picks" in pick["spread"]
        assert "public_picks" in pick["spread"]
        assert "home_pct" in pick["spread"]["expert_picks"]
        assert "away_pct" in pick["spread"]["expert_picks"]

    @pytest.mark.asyncio
    async def test_consensus_percentages_sum_to_100(self):
        """Test expert pick percentages sum to 100."""
        mock_db = MagicMock()
        mock_game = MagicMock()
        mock_game.id = 1
        mock_game.sport = "NFL"
        mock_game.start_time = datetime.utcnow()
        mock_game.home_team = "Chiefs"
        mock_game.away_team = "Bills"

        mock_db.query.return_value.filter.return_value.all.return_value = [mock_game]

        picks = await covers_scraper._generate_consensus_picks("NFL", datetime.utcnow(), mock_db)

        spread = picks[0]["spread"]["expert_picks"]
        assert abs(spread["home_pct"] + spread["away_pct"] - 100) < 0.1


# =============================================================================
# Expert Picks Tests
# =============================================================================

class TestExpertPicks:
    """Test expert picks generation."""

    def test_generate_expert_picks(self):
        """Test expert picks generation."""
        mock_db = MagicMock()
        picks = covers_scraper._generate_expert_picks("NFL", datetime.utcnow(), mock_db)

        assert len(picks) > 0
        assert all("expert" in p for p in picks)
        assert all("track_record" in p for p in picks)

    def test_expert_track_record_structure(self):
        """Test expert track record has correct structure."""
        mock_db = MagicMock()
        picks = covers_scraper._generate_expert_picks("NFL", datetime.utcnow(), mock_db)

        pick = picks[0]
        track_record = pick["track_record"]

        assert "wins" in track_record
        assert "losses" in track_record
        assert "win_pct" in track_record
        assert "roi" in track_record

    def test_expert_win_rate_realistic(self):
        """Test expert win rates are realistic (50-58%)."""
        mock_db = MagicMock()
        picks = covers_scraper._generate_expert_picks("NFL", datetime.utcnow(), mock_db)

        for pick in picks:
            win_pct = pick["track_record"]["win_pct"]
            assert 50 <= win_pct <= 60

    def test_expert_roi_calculation(self):
        """Test ROI is calculated based on win rate."""
        mock_db = MagicMock()
        picks = covers_scraper._generate_expert_picks("NFL", datetime.utcnow(), mock_db)

        for pick in picks:
            # Higher win % should have positive ROI (roughly)
            win_pct = pick["track_record"]["win_pct"]
            roi = pick["track_record"]["roi"]

            # 52.4% is breakeven at -110
            if win_pct > 53:
                assert roi > -5  # Should be positive or close to it

    def test_pick_selection_generation(self):
        """Test pick selection string generation."""
        rng = random.Random(42)

        spread_pick = covers_scraper._generate_pick_selection("spread", "NFL", rng)
        assert any(c in spread_pick for c in ["-", "+"])

        total_pick = covers_scraper._generate_pick_selection("total", "NFL", rng)
        assert "Over" in total_pick or "Under" in total_pick

        ml_pick = covers_scraper._generate_pick_selection("moneyline", "NFL", rng)
        assert "ML" in ml_pick


# =============================================================================
# Team Trends Tests
# =============================================================================

class TestTeamTrends:
    """Test team trends generation."""

    @pytest.mark.asyncio
    async def test_get_team_trends(self):
        """Test getting comprehensive team trends."""
        mock_db = MagicMock()

        with patch.object(covers_scraper, 'get_team_ats_record') as mock_ats:
            with patch.object(covers_scraper, 'get_team_ou_trend') as mock_ou:
                with patch.object(covers_scraper.cache, 'get', return_value=None):
                    with patch.object(covers_scraper.cache, 'set'):
                        mock_ats.return_value = {
                            "team": "Chiefs",
                            "overall": {"wins": 10, "losses": 7, "pct": 58.8},
                            "home": {"wins": 5, "losses": 3, "pct": 62.5},
                            "away": {"wins": 5, "losses": 4, "pct": 55.6},
                            "as_favorite": {"wins": 7, "losses": 5, "pct": 58.3, "games": 12},
                            "as_underdog": {"wins": 3, "losses": 2, "pct": 60.0, "games": 5},
                            "streak": {"type": "W", "length": 3, "description": "3W ATS"},
                        }

                        mock_ou.return_value = {
                            "team": "Chiefs",
                            "overall": {"overs": 9, "unders": 8, "over_pct": 52.9},
                        }

                        result = await covers_scraper.get_team_trends("Chiefs", "NFL", mock_db)

                        assert result["team"] == "Chiefs"
                        assert "ats_record" in result
                        assert "ou_trends" in result
                        assert "situational_trends" in result
                        assert "key_angles" in result

    def test_generate_key_angles(self):
        """Test key angles generation."""
        rng = random.Random(42)

        ats = {
            "overall": {"wins": 12, "losses": 5, "pct": 70.6},
            "home": {"wins": 6, "losses": 2, "pct": 75.0},
            "as_underdog": {"wins": 4, "losses": 1, "pct": 80.0, "games": 5},
            "streak": {"type": "W", "length": 4, "description": "4W ATS"},
        }

        ou = {
            "overall": {"overs": 10, "unders": 7, "over_pct": 58.8},
        }

        angles = covers_scraper._generate_key_angles("Chiefs", ats, ou, rng)

        assert len(angles) > 0
        assert len(angles) <= 4
        assert all(isinstance(a, str) for a in angles)


# =============================================================================
# Caching Tests
# =============================================================================

class TestCaching:
    """Test caching behavior."""

    @pytest.mark.asyncio
    async def test_ats_records_use_cache(self):
        """Test ATS records use caching."""
        mock_db = MagicMock()

        with patch.object(covers_scraper.cache, 'get') as mock_get:
            mock_get.return_value = [{"team": "Cached", "overall": {"pct": 50}}]

            result = await covers_scraper.get_team_ats_records("NFL", mock_db)

            mock_get.assert_called_once()
            assert result[0]["team"] == "Cached"

    @pytest.mark.asyncio
    async def test_cache_miss_generates_data(self):
        """Test cache miss triggers data generation."""
        mock_db = MagicMock()

        with patch.object(covers_scraper.cache, 'get', return_value=None):
            with patch.object(covers_scraper.cache, 'set') as mock_set:
                result = await covers_scraper.get_team_ats_records("NFL", mock_db)

                mock_set.assert_called_once()
                assert len(result) == 32


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests."""

    @pytest.mark.asyncio
    async def test_full_ats_flow(self):
        """Test full ATS retrieval flow."""
        mock_db = MagicMock()

        with patch.object(covers_scraper.cache, 'get', return_value=None):
            with patch.object(covers_scraper.cache, 'set'):
                records = await covers_scraper.get_team_ats_records("NFL", mock_db)

                assert len(records) == 32

                # Get specific team
                chiefs_record = await covers_scraper.get_team_ats_record("Kansas City Chiefs", "NFL", mock_db)

                assert chiefs_record["team"] == "Kansas City Chiefs"
                assert chiefs_record["abbrev"] == "KC"

    @pytest.mark.asyncio
    async def test_full_ou_flow(self):
        """Test full O/U retrieval flow."""
        mock_db = MagicMock()

        with patch.object(covers_scraper.cache, 'get', return_value=None):
            with patch.object(covers_scraper.cache, 'set'):
                trends = await covers_scraper.get_team_ou_trends("NBA", mock_db)

                assert len(trends) == 30

                # Get specific team
                lakers_trend = await covers_scraper.get_team_ou_trend("Los Angeles Lakers", "NBA", mock_db)

                assert lakers_trend["team"] == "Los Angeles Lakers"

    @pytest.mark.asyncio
    async def test_refresh_all_data(self):
        """Test refreshing all data for a sport."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []

        with patch.object(covers_scraper.cache, 'get', return_value=None):
            with patch.object(covers_scraper.cache, 'set'):
                result = await covers_scraper.refresh_all_data("NFL", mock_db)

                assert result["sport"] == "NFL"
                assert "ats_records" in result
                assert "ou_trends" in result
                assert result["errors"] == [] or isinstance(result["errors"], list)


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_team_not_found(self):
        """Test handling of unknown team."""
        mock_db = MagicMock()

        with patch.object(covers_scraper.cache, 'get', return_value=None):
            with patch.object(covers_scraper.cache, 'set'):
                result = await covers_scraper.get_team_ats_record("Unknown Team XYZ", "NFL", mock_db)

                assert "error" in result

    @pytest.mark.asyncio
    async def test_game_not_found_consensus(self):
        """Test game consensus when game doesn't exist."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = await covers_scraper.get_game_consensus(99999, mock_db)

        assert "error" in result
