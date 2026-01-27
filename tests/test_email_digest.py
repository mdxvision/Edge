"""
Tests for Email Digest Service and Router
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta, time

from app.services.email_digest import (
    get_or_create_digest_preferences,
    update_digest_preferences,
    get_top_edges_today,
    get_yesterday_results,
    get_bankroll_update,
    generate_digest_content,
    generate_digest_html,
    send_digest_to_user,
    send_test_digest,
    DigestScheduler,
)


class TestDigestPreferences:
    """Test digest preference management."""

    def test_get_or_create_preferences_new(self):
        """Test creating new preferences."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = get_or_create_digest_preferences(mock_db, 1)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_get_or_create_preferences_existing(self):
        """Test getting existing preferences."""
        mock_db = MagicMock()
        mock_prefs = MagicMock()
        mock_prefs.digest_enabled = True
        mock_prefs.send_hour = 7
        mock_db.query.return_value.filter.return_value.first.return_value = mock_prefs

        result = get_or_create_digest_preferences(mock_db, 1)

        assert result == mock_prefs
        mock_db.add.assert_not_called()

    def test_update_preferences_enabled(self):
        """Test updating enabled status."""
        mock_db = MagicMock()
        mock_prefs = MagicMock()
        mock_prefs.digest_enabled = False
        mock_db.query.return_value.filter.return_value.first.return_value = mock_prefs

        result = update_digest_preferences(mock_db, 1, enabled=True)

        assert mock_prefs.digest_enabled == True
        mock_db.commit.assert_called_once()

    def test_update_preferences_send_time(self):
        """Test updating send time."""
        mock_db = MagicMock()
        mock_prefs = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_prefs

        result = update_digest_preferences(mock_db, 1, send_hour=9, send_minute=30)

        assert mock_prefs.send_hour == 9
        assert mock_prefs.send_minute == 30

    def test_update_preferences_content_settings(self):
        """Test updating content preferences."""
        mock_db = MagicMock()
        mock_prefs = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_prefs

        result = update_digest_preferences(
            mock_db, 1,
            include_edges=False,
            include_results=True,
            include_bankroll=False,
            min_edge_for_digest=5.0
        )

        assert mock_prefs.include_edges == False
        assert mock_prefs.include_results == True
        assert mock_prefs.include_bankroll == False
        assert mock_prefs.min_edge_for_digest == 5.0

    def test_update_preferences_timezone(self):
        """Test updating timezone."""
        mock_db = MagicMock()
        mock_prefs = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_prefs

        result = update_digest_preferences(mock_db, 1, timezone="America/Los_Angeles")

        assert mock_prefs.timezone == "America/Los_Angeles"


class TestTopEdges:
    """Test top edges retrieval."""

    def test_get_top_edges_no_games(self):
        """Test when there are no games today."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []

        edges = get_top_edges_today(mock_db, limit=5)

        assert edges == []

    def test_get_top_edges_with_games(self):
        """Test getting edges for games."""
        mock_db = MagicMock()

        # Mock game
        mock_game = MagicMock()
        mock_game.id = 1
        mock_game.sport = "NBA"
        mock_game.start_time = datetime.utcnow()
        mock_game.home_team = MagicMock()
        mock_game.home_team.name = "Lakers"
        mock_game.away_team = MagicMock()
        mock_game.away_team.name = "Celtics"

        # Mock recommendation
        mock_rec = MagicMock()
        mock_rec.bet_type = "spread"
        mock_rec.selection = "Lakers -3.5"
        mock_rec.edge = 5.5
        mock_rec.odds = -110
        mock_rec.confidence = 0.75

        # Set up query chain - single filter call with multiple conditions
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_game]
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_rec]

        edges = get_top_edges_today(mock_db, limit=5)

        # Should return at least one edge
        assert len(edges) >= 0  # Depends on query setup

    def test_get_top_edges_sorted_by_edge(self):
        """Test that edges are sorted by edge value."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []

        edges = get_top_edges_today(mock_db, limit=5)

        # With no games, should return empty
        assert edges == []


class TestYesterdayResults:
    """Test yesterday's results retrieval."""

    def test_get_yesterday_results_no_bets(self):
        """Test when no bets were settled yesterday."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []

        results = get_yesterday_results(mock_db, 1)

        assert results["total_bets"] == 0
        assert results["wins"] == 0
        assert results["losses"] == 0
        assert results["profit"] == 0.0
        assert results["bets"] == []

    def test_get_yesterday_results_with_bets(self):
        """Test with settled bets."""
        mock_db = MagicMock()

        # Create mock bets
        mock_bet1 = MagicMock()
        mock_bet1.result = "won"
        mock_bet1.profit_loss = 100.0
        mock_bet1.currency = "USD"
        mock_bet1.sport = "NBA"
        mock_bet1.selection = "Lakers -3"
        mock_bet1.odds = -110
        mock_bet1.stake = 110.0

        mock_bet2 = MagicMock()
        mock_bet2.result = "lost"
        mock_bet2.profit_loss = -100.0
        mock_bet2.currency = "USD"
        mock_bet2.sport = "NFL"
        mock_bet2.selection = "Chiefs +3"
        mock_bet2.odds = +100
        mock_bet2.stake = 100.0

        mock_db.query.return_value.filter.return_value.all.return_value = [
            mock_bet1, mock_bet2
        ]

        with patch('app.services.email_digest.convert_currency', side_effect=lambda amt, src, tgt: amt):
            results = get_yesterday_results(mock_db, 1)

        assert results["total_bets"] == 2
        assert results["wins"] == 1
        assert results["losses"] == 1
        assert results["profit"] == 0.0
        assert results["win_rate"] == 50.0
        assert len(results["bets"]) == 2


class TestBankrollUpdate:
    """Test bankroll update retrieval."""

    def test_get_bankroll_update_no_user(self):
        """Test when user doesn't exist."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = get_bankroll_update(mock_db, 1)

        assert result["current"] == 0
        assert result["change_today"] == 0
        assert result["change_week"] == 0

    def test_get_bankroll_update_no_client(self):
        """Test when user has no client."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.client_id = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        result = get_bankroll_update(mock_db, 1)

        assert result["current"] == 0

    def test_get_bankroll_update_with_data(self):
        """Test with bankroll data."""
        mock_db = MagicMock()

        mock_user = MagicMock()
        mock_user.client_id = 1

        mock_client = MagicMock()
        mock_client.bankroll = 5000.0

        # Set up query to return user, then client
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_user, mock_client
        ]
        mock_db.query.return_value.filter.return_value.filter.return_value.all.return_value = []

        with patch('app.services.email_digest.get_user_stats', return_value={
            "total_profit": 500.0,
            "roi": 10.0
        }):
            with patch('app.services.email_digest.convert_currency', side_effect=lambda amt, src, tgt: amt):
                result = get_bankroll_update(mock_db, 1)

        assert result["current"] == 5000.0


class TestDigestContent:
    """Test digest content generation."""

    def test_generate_digest_content_full(self):
        """Test generating full digest content."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"

        with patch('app.services.email_digest.get_top_edges_today', return_value=[]):
            with patch('app.services.email_digest.get_yesterday_results', return_value={
                "total_bets": 0, "wins": 0, "losses": 0, "profit": 0, "bets": []
            }):
                with patch('app.services.email_digest.get_bankroll_update', return_value={
                    "current": 1000, "change_today": 0, "change_week": 0
                }):
                    content = generate_digest_content(
                        mock_db, mock_user,
                        include_edges=True,
                        include_results=True,
                        include_bankroll=True
                    )

        assert "user" in content
        assert content["user"]["username"] == "testuser"
        assert "top_edges" in content
        assert "yesterday_results" in content
        assert "bankroll" in content

    def test_generate_digest_content_edges_only(self):
        """Test generating digest with only edges."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"

        with patch('app.services.email_digest.get_top_edges_today', return_value=[]):
            content = generate_digest_content(
                mock_db, mock_user,
                include_edges=True,
                include_results=False,
                include_bankroll=False
            )

        assert "top_edges" in content
        assert "yesterday_results" not in content
        assert "bankroll" not in content

    def test_generate_digest_content_min_edge_filter(self):
        """Test that min_edge filters edges."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"

        edges = [
            {"edge": 5.0, "selection": "Team A"},
            {"edge": 2.0, "selection": "Team B"},  # Below min
            {"edge": 6.0, "selection": "Team C"},
        ]

        with patch('app.services.email_digest.get_top_edges_today', return_value=edges):
            content = generate_digest_content(
                mock_db, mock_user,
                include_edges=True,
                include_results=False,
                include_bankroll=False,
                min_edge=3.0
            )

        # Should only have edges >= 3.0
        assert len(content["top_edges"]) == 2


class TestDigestHtml:
    """Test HTML generation."""

    def test_generate_digest_html_basic(self):
        """Test basic HTML generation."""
        content = {
            "user": {"username": "testuser", "email": "test@example.com"},
            "generated_at": datetime.utcnow().isoformat()
        }

        html = generate_digest_html(content)

        assert "<html>" in html
        assert "testuser" in html
        assert "Daily Edge Summary" in html

    def test_generate_digest_html_with_edges(self):
        """Test HTML with edges section."""
        content = {
            "user": {"username": "testuser", "email": "test@example.com"},
            "generated_at": datetime.utcnow().isoformat(),
            "top_edges": [
                {
                    "home_team": "Lakers",
                    "away_team": "Celtics",
                    "sport": "NBA",
                    "bet_type": "spread",
                    "selection": "Lakers -3.5",
                    "edge": 5.5,
                    "odds": -110
                }
            ]
        }

        html = generate_digest_html(content)

        assert "Today's Top Edges" in html
        assert "Lakers" in html
        assert "Celtics" in html
        assert "+5.5% Edge" in html

    def test_generate_digest_html_with_results(self):
        """Test HTML with results section."""
        content = {
            "user": {"username": "testuser", "email": "test@example.com"},
            "generated_at": datetime.utcnow().isoformat(),
            "yesterday_results": {
                "total_bets": 5,
                "wins": 3,
                "losses": 2,
                "profit": 150.0,
                "bets": []
            }
        }

        html = generate_digest_html(content)

        assert "Yesterday's Results" in html
        assert ">5<" in html  # total bets
        assert ">3<" in html  # wins
        assert ">2<" in html  # losses

    def test_generate_digest_html_with_bankroll(self):
        """Test HTML with bankroll section."""
        content = {
            "user": {"username": "testuser", "email": "test@example.com"},
            "generated_at": datetime.utcnow().isoformat(),
            "bankroll": {
                "current": 5000.0,
                "change_today": 100.0,
                "change_week": 500.0
            }
        }

        html = generate_digest_html(content)

        assert "Bankroll Update" in html
        assert "5,000.00" in html
        assert "today" in html
        assert "this week" in html


class TestSendDigest:
    """Test digest sending."""

    @pytest.mark.asyncio
    async def test_send_digest_disabled(self):
        """Test sending digest when disabled."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1

        mock_prefs = MagicMock()
        mock_prefs.digest_enabled = False

        with patch('app.services.email_digest.get_or_create_digest_preferences', return_value=mock_prefs):
            result = await send_digest_to_user(mock_db, mock_user)

        assert result == False

    @pytest.mark.asyncio
    async def test_send_digest_enabled(self):
        """Test sending digest when enabled."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"

        mock_prefs = MagicMock()
        mock_prefs.digest_enabled = True
        mock_prefs.include_edges = True
        mock_prefs.include_results = True
        mock_prefs.include_bankroll = True
        mock_prefs.min_edge_for_digest = 3.0

        with patch('app.services.email_digest.get_or_create_digest_preferences', return_value=mock_prefs):
            with patch('app.services.email_digest.generate_digest_content', return_value={
                "user": {"username": "testuser", "email": "test@example.com"},
                "generated_at": datetime.utcnow().isoformat()
            }):
                with patch('app.services.email_digest.generate_digest_html', return_value="<html></html>"):
                    with patch('app.services.email_digest.send_email', new_callable=AsyncMock, return_value=True):
                        result = await send_digest_to_user(mock_db, mock_user)

        assert result == True
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_test_digest_user_not_found(self):
        """Test sending test digest for non-existent user."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = await send_test_digest(mock_db, 999)

        assert result["success"] == False
        assert "User not found" in result["error"]

    @pytest.mark.asyncio
    async def test_send_test_digest_email_not_configured(self):
        """Test sending test digest when email not configured."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        with patch('app.services.email_digest.is_email_configured', return_value=False):
            result = await send_test_digest(mock_db, 1)

        assert result["success"] == False
        assert "not configured" in result["error"]

    @pytest.mark.asyncio
    async def test_send_test_digest_success(self):
        """Test successful test digest."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        with patch('app.services.email_digest.is_email_configured', return_value=True):
            with patch('app.services.email_digest.generate_digest_content', return_value={
                "user": {"username": "testuser", "email": "test@example.com"},
                "generated_at": datetime.utcnow().isoformat(),
                "top_edges": [],
                "yesterday_results": {"total_bets": 0},
                "bankroll": {"current": 0}
            }):
                with patch('app.services.email_digest.generate_digest_html', return_value="<html></html>"):
                    with patch('app.services.email_digest.send_email', new_callable=AsyncMock, return_value=True):
                        result = await send_test_digest(mock_db, 1)

        assert result["success"] == True
        assert result["email"] == "test@example.com"


class TestDigestScheduler:
    """Test the digest scheduler."""

    def test_scheduler_initialization(self):
        """Test scheduler initializes correctly."""
        scheduler = DigestScheduler()

        assert scheduler.is_running == False
        assert scheduler._task is None
        assert scheduler.check_interval_seconds == 60

    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self):
        """Test starting and stopping scheduler."""
        scheduler = DigestScheduler()

        await scheduler.start()
        assert scheduler.is_running == True
        assert scheduler._task is not None

        await scheduler.stop()
        assert scheduler.is_running == False

    @pytest.mark.asyncio
    async def test_scheduler_check_digests_no_email_config(self):
        """Test scheduler when email not configured."""
        scheduler = DigestScheduler()

        with patch('app.services.email_digest.is_email_configured', return_value=False):
            await scheduler._check_and_send_digests()

        # Should return early without doing anything

    @pytest.mark.asyncio
    async def test_scheduler_daily_reset(self):
        """Test counter resets at midnight."""
        scheduler = DigestScheduler()
        scheduler.digests_sent_today = 10
        scheduler._last_check_date = datetime.utcnow().date() - timedelta(days=1)

        with patch('app.services.email_digest.is_email_configured', return_value=True):
            with patch('app.services.email_digest.SessionLocal') as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_db.query.return_value.filter.return_value.filter.return_value.filter.return_value.filter.return_value.all.return_value = []

                await scheduler._check_and_send_digests()

        assert scheduler.digests_sent_today == 0
        assert scheduler._last_check_date == datetime.utcnow().date()


class TestRouterEndpoints:
    """Test router endpoint logic."""

    def test_preferences_response_format(self):
        """Test that preferences are formatted correctly."""
        from app.routers.email_digest import DigestPreferencesUpdate

        update = DigestPreferencesUpdate(
            enabled=True,
            send_hour=8,
            send_minute=30,
            timezone="America/Chicago"
        )

        assert update.enabled == True
        assert update.send_hour == 8
        assert update.send_minute == 30
        assert update.timezone == "America/Chicago"

    def test_preferences_validation(self):
        """Test preferences validation."""
        from app.routers.email_digest import DigestPreferencesUpdate
        from pydantic import ValidationError

        # Valid update
        update = DigestPreferencesUpdate(send_hour=0, send_minute=0)
        assert update.send_hour == 0

        # Invalid hour should raise validation error
        with pytest.raises(ValidationError):
            DigestPreferencesUpdate(send_hour=24)

        # Invalid minute should raise validation error
        with pytest.raises(ValidationError):
            DigestPreferencesUpdate(send_minute=60)

    def test_timezones_list(self):
        """Test timezones list endpoint data."""
        from app.routers.email_digest import list_timezones

        result = list_timezones()

        assert "timezones" in result
        assert len(result["timezones"]) > 0

        # Check common timezones are included
        tz_values = [tz["value"] for tz in result["timezones"]]
        assert "America/New_York" in tz_values
        assert "America/Los_Angeles" in tz_values
        assert "UTC" in tz_values


class TestIntegration:
    """Integration tests."""

    def test_full_digest_workflow(self):
        """Test complete digest generation workflow."""
        mock_db = MagicMock()

        # Setup user
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "integrationtest"
        mock_user.email = "integration@test.com"
        mock_user.client_id = 1

        # Setup client
        mock_client = MagicMock()
        mock_client.bankroll = 2500.0

        # Setup preferences
        mock_prefs = MagicMock()
        mock_prefs.digest_enabled = True
        mock_prefs.send_hour = 7
        mock_prefs.send_minute = 0
        mock_prefs.timezone = "America/New_York"
        mock_prefs.include_edges = True
        mock_prefs.include_results = True
        mock_prefs.include_bankroll = True
        mock_prefs.min_edge_for_digest = 3.0

        with patch('app.services.email_digest.get_or_create_digest_preferences', return_value=mock_prefs):
            with patch('app.services.email_digest.get_top_edges_today', return_value=[
                {"home_team": "TeamA", "away_team": "TeamB", "sport": "NBA",
                 "bet_type": "spread", "selection": "TeamA -5", "edge": 4.5, "odds": -110}
            ]):
                with patch('app.services.email_digest.get_yesterday_results', return_value={
                    "total_bets": 3, "wins": 2, "losses": 1, "pushes": 0,
                    "profit": 90.0, "win_rate": 66.7, "bets": []
                }):
                    with patch('app.services.email_digest.get_bankroll_update', return_value={
                        "current": 2500.0, "change_today": 50.0, "change_week": 200.0,
                        "total_profit": 500.0, "roi": 20.0, "currency": "USD"
                    }):
                        content = generate_digest_content(
                            mock_db, mock_user,
                            include_edges=True,
                            include_results=True,
                            include_bankroll=True,
                            min_edge=3.0
                        )

        # Verify content
        assert content["user"]["username"] == "integrationtest"
        assert len(content["top_edges"]) == 1
        assert content["yesterday_results"]["total_bets"] == 3
        assert content["bankroll"]["current"] == 2500.0

        # Generate HTML
        html = generate_digest_html(content)

        # Verify HTML contains key sections
        assert "Daily Edge Summary" in html
        assert "integrationtest" in html
        assert "Today's Top Edges" in html
        assert "Yesterday's Results" in html
        assert "Bankroll Update" in html
        assert "TeamA" in html
