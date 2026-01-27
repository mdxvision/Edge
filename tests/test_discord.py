"""
Tests for Discord Bot Integration Service and Router
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
import json

from app.services.discord_bot import (
    is_discord_configured,
    is_webhook_configured,
    generate_link_code,
    create_link_code,
    verify_link_code,
    complete_link,
    cleanup_expired_link_codes,
    get_discord_user,
    get_discord_user_by_discord_id,
    unlink_discord,
    create_webhook,
    get_user_webhooks,
    get_webhook,
    delete_webhook,
    build_recommendation_embed,
    build_result_embed,
    build_alert_embed,
    build_daily_digest_embed,
    send_webhook_message,
    handle_interaction,
    handle_link_command,
    handle_status_command,
    handle_edges_command,
    handle_help_command,
    EMBED_COLORS,
)


class TestConfiguration:
    """Test Discord configuration checks."""

    def test_is_discord_configured_without_token(self):
        """Test when Discord is not configured."""
        with patch('app.services.discord_bot.DISCORD_BOT_TOKEN', None):
            with patch('app.services.discord_bot.DISCORD_CLIENT_ID', None):
                assert is_discord_configured() == False

    def test_is_discord_configured_with_token(self):
        """Test when Discord is configured."""
        with patch('app.services.discord_bot.DISCORD_BOT_TOKEN', 'test_token'):
            assert is_discord_configured() == True

    def test_is_discord_configured_with_client_id(self):
        """Test when Discord is configured with client ID."""
        with patch('app.services.discord_bot.DISCORD_BOT_TOKEN', None):
            with patch('app.services.discord_bot.DISCORD_CLIENT_ID', 'test_client'):
                assert is_discord_configured() == True

    def test_is_webhook_configured(self):
        """Webhooks don't require bot configuration."""
        assert is_webhook_configured() == True


class TestLinkCodeManagement:
    """Test link code creation and verification."""

    def test_generate_link_code_format(self):
        """Test link code is hex string of correct length."""
        code = generate_link_code()
        assert len(code) == 32
        assert all(c in '0123456789abcdef' for c in code)

    def test_generate_link_code_unique(self):
        """Test generated codes are unique."""
        codes = [generate_link_code() for _ in range(100)]
        assert len(codes) == len(set(codes))

    def test_create_link_code(self):
        """Test creating a link code in database."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.delete.return_value = 0

        code = create_link_code(mock_db, 1)

        assert len(code) == 32
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_verify_link_code_valid(self):
        """Test verifying a valid link code."""
        mock_db = MagicMock()
        mock_link_code = MagicMock()
        mock_link_code.user_id = 42
        mock_db.query.return_value.filter.return_value.first.return_value = mock_link_code

        result = verify_link_code(mock_db, "valid_code")

        assert result == 42

    def test_verify_link_code_invalid(self):
        """Test verifying an invalid link code."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = verify_link_code(mock_db, "invalid_code")

        assert result is None

    def test_cleanup_expired_codes(self):
        """Test cleaning up expired link codes."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.delete.return_value = 5

        count = cleanup_expired_link_codes(mock_db)

        assert count == 5
        mock_db.commit.assert_called_once()


class TestCompleteLinking:
    """Test completing the Discord link process."""

    def test_complete_link_invalid_code(self):
        """Test linking with invalid code fails."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = complete_link(mock_db, "invalid_code", "discord_123")

        assert result == False

    def test_complete_link_new_user(self):
        """Test linking new Discord user."""
        mock_db = MagicMock()

        # Valid link code
        mock_link_code = MagicMock()
        mock_link_code.user_id = 1

        # No existing Discord user
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_link_code,  # Link code query
            None  # Discord user query
        ]

        result = complete_link(
            mock_db, "valid_code", "discord_123",
            discord_username="TestUser",
            discord_discriminator="1234"
        )

        assert result == True
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()

    def test_complete_link_existing_user_same_account(self):
        """Test linking when Discord already linked to same account."""
        mock_db = MagicMock()

        mock_link_code = MagicMock()
        mock_link_code.user_id = 1

        mock_existing = MagicMock()
        mock_existing.user_id = 1

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_link_code,
            mock_existing
        ]

        result = complete_link(mock_db, "valid_code", "discord_123")

        assert result == True

    def test_complete_link_existing_user_different_account(self):
        """Test linking when Discord linked to different account."""
        mock_db = MagicMock()

        mock_link_code = MagicMock()
        mock_link_code.user_id = 1

        mock_existing = MagicMock()
        mock_existing.user_id = 999  # Different user

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_link_code,
            mock_existing
        ]

        result = complete_link(mock_db, "valid_code", "discord_123")

        assert result == False


class TestDiscordUserManagement:
    """Test Discord user CRUD operations."""

    def test_get_discord_user_exists(self):
        """Test getting existing Discord user."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        result = get_discord_user(mock_db, 1)

        assert result == mock_user

    def test_get_discord_user_not_exists(self):
        """Test getting non-existent Discord user."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = get_discord_user(mock_db, 1)

        assert result is None

    def test_get_discord_user_by_discord_id(self):
        """Test getting Discord user by Discord ID."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        result = get_discord_user_by_discord_id(mock_db, "discord_123")

        assert result == mock_user

    def test_unlink_discord_success(self):
        """Test unlinking Discord account."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.delete.return_value = 1

        result = unlink_discord(mock_db, 1)

        assert result == True
        mock_db.commit.assert_called_once()

    def test_unlink_discord_not_linked(self):
        """Test unlinking when not linked."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.delete.return_value = 0

        result = unlink_discord(mock_db, 1)

        assert result == False


class TestWebhookManagement:
    """Test webhook CRUD operations."""

    def test_create_webhook(self):
        """Test creating a webhook."""
        mock_db = MagicMock()
        mock_webhook = MagicMock()
        mock_webhook.id = 1

        # Mock refresh to set values
        def mock_refresh(obj):
            obj.id = 1
        mock_db.refresh = mock_refresh

        webhook = create_webhook(
            db=mock_db,
            user_id=1,
            name="Test Webhook",
            webhook_url="https://discord.com/api/webhooks/123/abc"
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_get_user_webhooks(self):
        """Test getting all webhooks for user."""
        mock_db = MagicMock()
        mock_webhooks = [MagicMock(), MagicMock()]
        mock_db.query.return_value.filter.return_value.all.return_value = mock_webhooks

        result = get_user_webhooks(mock_db, 1)

        assert result == mock_webhooks

    def test_get_webhook(self):
        """Test getting specific webhook."""
        mock_db = MagicMock()
        mock_webhook = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_webhook

        result = get_webhook(mock_db, 1, 1)

        assert result == mock_webhook

    def test_delete_webhook_success(self):
        """Test deleting webhook."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.delete.return_value = 1

        result = delete_webhook(mock_db, 1, 1)

        assert result == True

    def test_delete_webhook_not_found(self):
        """Test deleting non-existent webhook."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.delete.return_value = 0

        result = delete_webhook(mock_db, 1, 1)

        assert result == False


class TestEmbedBuilders:
    """Test Discord embed building functions."""

    def test_build_recommendation_embed_strong_edge(self):
        """Test recommendation embed with strong edge."""
        recommendation = {
            "sport": "NBA",
            "selection": "Lakers -3.5",
            "edge": 8.0,
            "odds": -110,
            "stake": 100.0,
            "explanation": "Strong edge based on line movement"
        }

        embed = build_recommendation_embed(recommendation)

        assert "STRONG EDGE" in embed["title"]
        assert embed["color"] == EMBED_COLORS["success"]
        assert any(f["name"] == "Edge" and "8.0" in f["value"] for f in embed["fields"])

    def test_build_recommendation_embed_good_edge(self):
        """Test recommendation embed with good edge."""
        recommendation = {
            "sport": "NFL",
            "selection": "Chiefs +3",
            "edge": 5.5,
            "odds": +150,
            "stake": 50.0
        }

        embed = build_recommendation_embed(recommendation)

        assert "GOOD EDGE" in embed["title"]
        assert any(f["value"] == "+150" for f in embed["fields"])

    def test_build_result_embed_won(self):
        """Test result embed for won bet."""
        bet = {
            "sport": "NBA",
            "selection": "Lakers -3.5",
            "result": "won",
            "profit_loss": 90.91
        }

        embed = build_result_embed(bet)

        assert "WIN" in embed["title"]
        assert embed["color"] == EMBED_COLORS["success"]
        assert any("+$90.91" in f["value"] for f in embed["fields"])

    def test_build_result_embed_lost(self):
        """Test result embed for lost bet."""
        bet = {
            "sport": "NFL",
            "selection": "Chiefs +3",
            "result": "lost",
            "profit_loss": -100.0
        }

        embed = build_result_embed(bet)

        assert "LOSS" in embed["title"]
        assert embed["color"] == EMBED_COLORS["danger"]

    def test_build_result_embed_push(self):
        """Test result embed for push."""
        bet = {
            "sport": "MLB",
            "selection": "Yankees -1.5",
            "result": "push",
            "profit_loss": 0
        }

        embed = build_result_embed(bet)

        assert "PUSH" in embed["title"]
        assert embed["color"] == EMBED_COLORS["warning"]

    def test_build_alert_embed(self):
        """Test alert embed."""
        embed = build_alert_embed("Line Movement", "Lakers line moved from -3 to -5", "warning")

        assert "Line Movement" in embed["title"]
        assert embed["color"] == EMBED_COLORS["warning"]
        assert "Lakers line moved" in embed["description"]

    def test_build_daily_digest_embed(self):
        """Test daily digest embed."""
        edges = [
            {"home_team": "Lakers", "away_team": "Celtics", "sport": "NBA",
             "selection": "Lakers -3", "edge": 5.0, "odds": -110}
        ]
        yesterday = {"total_bets": 5, "wins": 3, "losses": 2, "profit": 150.0}
        bankroll = {"current": 5000.0, "change_today": 100.0, "change_week": 500.0}

        embeds = build_daily_digest_embed(edges, yesterday, bankroll)

        assert len(embeds) == 4  # Header, edges, results, bankroll
        assert "Daily Edge Summary" in embeds[0]["title"]
        assert "Top Edges" in embeds[1]["title"]
        assert "Results" in embeds[2]["title"]
        assert "Bankroll" in embeds[3]["title"]


class TestSendWebhookMessage:
    """Test webhook message sending."""

    @pytest.mark.asyncio
    async def test_send_webhook_message_no_url(self):
        """Test sending to empty URL fails gracefully."""
        result = await send_webhook_message("", content="Test")
        assert result == False

    @pytest.mark.asyncio
    async def test_send_webhook_message_success(self):
        """Test successful webhook message."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 204
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await send_webhook_message(
                "https://discord.com/api/webhooks/123/abc",
                content="Test message"
            )

            assert result == True

    @pytest.mark.asyncio
    async def test_send_webhook_message_with_embeds(self):
        """Test sending webhook with embeds."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await send_webhook_message(
                "https://discord.com/api/webhooks/123/abc",
                embeds=[{"title": "Test"}]
            )

            assert result == True

    @pytest.mark.asyncio
    async def test_send_webhook_message_failure(self):
        """Test failed webhook message."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.text = "Not Found"
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await send_webhook_message(
                "https://discord.com/api/webhooks/123/abc",
                content="Test"
            )

            assert result == False


class TestSlashCommands:
    """Test slash command handling."""

    def test_handle_interaction_ping(self):
        """Test handling ping interaction."""
        mock_db = MagicMock()
        interaction = {"type": 1}

        result = handle_interaction(mock_db, interaction)

        assert result == {"type": 1}

    def test_handle_help_command(self):
        """Test /help command."""
        result = handle_help_command()

        assert result["type"] == 4
        assert "embeds" in result["data"]
        assert "Commands" in result["data"]["embeds"][0]["title"]

    def test_handle_status_command_not_linked(self):
        """Test /status when not linked."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = handle_status_command(mock_db, "discord_123")

        assert result["type"] == 4
        assert "not linked" in result["data"]["content"]

    def test_handle_status_command_linked(self):
        """Test /status when linked."""
        mock_db = MagicMock()

        mock_discord_user = MagicMock()
        mock_discord_user.user_id = 1
        mock_discord_user.notify_recommendations = True
        mock_discord_user.notify_results = True
        mock_discord_user.notify_alerts = False

        mock_user = MagicMock()
        mock_user.username = "testuser"

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_discord_user,
            mock_user
        ]

        result = handle_status_command(mock_db, "discord_123")

        assert result["type"] == 4
        assert "embeds" in result["data"]
        assert "Account Status" in result["data"]["embeds"][0]["title"]

    def test_handle_link_command_no_code(self):
        """Test /link without code."""
        mock_db = MagicMock()
        interaction = {"data": {"options": []}}

        result = handle_link_command(mock_db, interaction, "discord_123")

        assert "provide your link code" in result["data"]["content"]

    def test_handle_link_command_success(self):
        """Test /link with valid code."""
        mock_db = MagicMock()

        # Valid link code
        mock_link_code = MagicMock()
        mock_link_code.user_id = 1

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_link_code,  # Link code
            None  # No existing Discord user
        ]

        interaction = {
            "data": {"options": [{"name": "code", "value": "valid_code"}]},
            "member": {"user": {"username": "TestUser", "discriminator": "1234", "avatar": "abc"}},
            "guild_id": "guild_123"
        }

        result = handle_link_command(mock_db, interaction, "discord_123")

        assert "embeds" in result["data"]
        assert "Linked" in result["data"]["embeds"][0]["title"]

    def test_handle_link_command_invalid_code(self):
        """Test /link with invalid code."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        interaction = {
            "data": {"options": [{"name": "code", "value": "invalid"}]},
            "member": {"user": {"username": "TestUser"}}
        }

        result = handle_link_command(mock_db, interaction, "discord_123")

        assert "Invalid or expired" in result["data"]["content"]

    def test_handle_edges_command_no_edges(self):
        """Test /edges with no edges available."""
        mock_db = MagicMock()

        with patch('app.services.email_digest.get_top_edges_today', return_value=[]):
            result = handle_edges_command(mock_db)

        assert "No edges found" in result["data"]["content"]

    def test_handle_edges_command_with_edges(self):
        """Test /edges with edges available."""
        mock_db = MagicMock()

        edges = [
            {"home_team": "Lakers", "away_team": "Celtics", "sport": "NBA",
             "selection": "Lakers -3", "edge": 5.0, "odds": -110}
        ]

        with patch('app.services.email_digest.get_top_edges_today', return_value=edges):
            result = handle_edges_command(mock_db)

        assert "embeds" in result["data"]
        assert "Top Edges" in result["data"]["embeds"][0]["title"]


class TestRouterModels:
    """Test Pydantic models for router."""

    def test_webhook_create_request_validation(self):
        """Test webhook creation request validation."""
        from app.routers.discord import WebhookCreateRequest
        from pydantic import ValidationError

        # Valid request
        req = WebhookCreateRequest(
            name="Test",
            webhook_url="https://discord.com/api/webhooks/123/abc"
        )
        assert req.name == "Test"
        assert req.min_edge == 3.0

        # Invalid - empty name
        with pytest.raises(ValidationError):
            WebhookCreateRequest(name="", webhook_url="https://test.com")

    def test_webhook_update_request_partial(self):
        """Test partial webhook update."""
        from app.routers.discord import WebhookUpdateRequest

        req = WebhookUpdateRequest(name="Updated", min_edge=5.0)
        assert req.name == "Updated"
        assert req.min_edge == 5.0
        assert req.notify_recommendations is None


class TestIntegration:
    """Integration tests."""

    def test_full_linking_workflow(self):
        """Test complete linking workflow."""
        mock_db = MagicMock()

        # Step 1: Create link code
        mock_db.query.return_value.filter.return_value.delete.return_value = 0
        code = create_link_code(mock_db, 1)
        assert len(code) == 32

        # Step 2: Complete link
        mock_link_code = MagicMock()
        mock_link_code.user_id = 1

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_link_code,
            None
        ]

        result = complete_link(
            mock_db, code, "discord_123",
            discord_username="TestUser"
        )
        assert result == True

    def test_webhook_workflow(self):
        """Test complete webhook workflow."""
        mock_db = MagicMock()

        # Create webhook
        webhook = create_webhook(
            mock_db, 1, "Alerts Channel",
            "https://discord.com/api/webhooks/123/abc",
            min_edge=5.0,
            sports=["NBA", "NFL"]
        )

        mock_db.add.assert_called_once()

        # Get user webhooks
        mock_db.query.return_value.filter.return_value.all.return_value = [webhook]
        webhooks = get_user_webhooks(mock_db, 1)
        assert len(webhooks) == 1
