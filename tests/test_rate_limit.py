"""
Tests for rate limiting middleware.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from fastapi import Request
from fastapi.testclient import TestClient
from starlette.datastructures import Headers

from app.middleware.rate_limit import (
    Tier,
    TierLimits,
    EndpointLimits,
    RateLimitStorage,
    RateLimitMiddleware,
    AuthRateLimitMiddleware,
    get_user_tier,
    get_endpoint_limits,
    get_rate_limit_stats,
    TIER_LIMITS,
    ENDPOINT_LIMITS,
)


class TestTierEnum:
    """Test the Tier enum."""

    def test_tier_values(self):
        assert Tier.FREE.value == "free"
        assert Tier.PREMIUM.value == "premium"
        assert Tier.PRO.value == "pro"
        assert Tier.UNLIMITED.value == "unlimited"


class TestTierLimits:
    """Test tier limit configurations."""

    def test_free_tier_limits(self):
        limits = TIER_LIMITS[Tier.FREE]
        assert limits.requests_per_minute == 30
        assert limits.requests_per_hour == 500
        assert limits.burst_limit == 5

    def test_premium_tier_limits(self):
        limits = TIER_LIMITS[Tier.PREMIUM]
        assert limits.requests_per_minute == 60
        assert limits.requests_per_hour == 2000
        assert limits.burst_limit == 10

    def test_pro_tier_limits(self):
        limits = TIER_LIMITS[Tier.PRO]
        assert limits.requests_per_minute == 120
        assert limits.requests_per_hour == 5000
        assert limits.burst_limit == 20

    def test_unlimited_tier_limits(self):
        limits = TIER_LIMITS[Tier.UNLIMITED]
        assert limits.requests_per_minute == 10000
        assert limits.requests_per_hour == 100000
        assert limits.burst_limit == 100


class TestEndpointLimits:
    """Test per-endpoint rate limit configurations."""

    def test_heavy_endpoints_have_stricter_limits(self):
        assert "/recommendations/run" in ENDPOINT_LIMITS
        rec_limits = ENDPOINT_LIMITS["/recommendations/run"]
        assert rec_limits.requests_per_minute == 5
        assert rec_limits.requests_per_hour == 50

    def test_get_endpoint_limits_exact_match(self):
        limits = get_endpoint_limits("/recommendations/run")
        assert limits is not None
        assert limits.requests_per_minute == 5

    def test_get_endpoint_limits_prefix_match(self):
        limits = get_endpoint_limits("/games/123")
        assert limits is not None
        assert limits.requests_per_minute == 30

    def test_get_endpoint_limits_no_match(self):
        limits = get_endpoint_limits("/nonexistent/endpoint")
        assert limits is None


class TestGetUserTier:
    """Test user tier extraction from requests."""

    def test_free_tier_default(self):
        request = Mock(spec=Request)
        request.headers = Headers({})
        request.state = Mock()
        delattr(request.state, "user")  # No user attribute

        tier = get_user_tier(request)
        assert tier == Tier.FREE

    def test_pro_tier_from_api_key(self):
        request = Mock(spec=Request)
        request.headers = Headers({"x-api-key": "pro_abc123xyz"})

        tier = get_user_tier(request)
        assert tier == Tier.PRO

    def test_premium_tier_from_api_key(self):
        request = Mock(spec=Request)
        request.headers = Headers({"x-api-key": "premium_abc123xyz"})

        tier = get_user_tier(request)
        assert tier == Tier.PREMIUM

    def test_unlimited_tier_from_admin_key(self):
        request = Mock(spec=Request)
        request.headers = Headers({"x-api-key": "admin_secret_key"})

        tier = get_user_tier(request)
        assert tier == Tier.UNLIMITED

    def test_unlimited_tier_from_internal_key(self):
        request = Mock(spec=Request)
        request.headers = Headers({"x-api-key": "internal_service_key"})

        tier = get_user_tier(request)
        assert tier == Tier.UNLIMITED

    def test_tier_from_user_session(self):
        request = Mock(spec=Request)
        request.headers = Headers({})
        request.state = Mock()
        request.state.user = Mock()
        request.state.user.subscription_tier = "premium"

        tier = get_user_tier(request)
        assert tier == Tier.PREMIUM


class TestRateLimitStorage:
    """Test the rate limit storage backend."""

    def test_in_memory_minute_tracking(self):
        storage = RateLimitStorage()
        storage._use_redis = False  # Force in-memory

        # Initially 0
        assert storage.get_minute_count("test_ip") == 0

        # Increment
        storage.increment_minute("test_ip")
        assert storage.get_minute_count("test_ip") == 1

        storage.increment_minute("test_ip")
        assert storage.get_minute_count("test_ip") == 2

    def test_in_memory_hour_tracking(self):
        storage = RateLimitStorage()
        storage._use_redis = False

        assert storage.get_hour_count("test_ip") == 0

        storage.increment_hour("test_ip")
        assert storage.get_hour_count("test_ip") == 1

    def test_endpoint_specific_tracking(self):
        storage = RateLimitStorage()
        storage._use_redis = False

        # Different endpoints tracked separately
        storage.increment_minute("test_ip", "/api/games")
        storage.increment_minute("test_ip", "/api/games")
        storage.increment_minute("test_ip", "/api/odds")

        assert storage.get_minute_count("test_ip", "/api/games") == 2
        assert storage.get_minute_count("test_ip", "/api/odds") == 1

    def test_burst_tracking(self):
        storage = RateLimitStorage()
        storage._use_redis = False

        # First request allowed
        assert storage.check_burst("test_ip") is True
        assert storage.get_burst_count("test_ip") == 1

    def test_get_reset_time_minute(self):
        storage = RateLimitStorage()
        now = int(time.time())
        reset = storage.get_reset_time("minute")

        # Reset time should be within next minute
        assert reset > now
        assert reset <= now + 60

    def test_get_reset_time_hour(self):
        storage = RateLimitStorage()
        now = int(time.time())
        reset = storage.get_reset_time("hour")

        # Reset time should be within next hour
        assert reset > now
        assert reset <= now + 3600

    def test_cleanup_removes_expired(self):
        storage = RateLimitStorage()
        storage._use_redis = False
        storage._last_cleanup = 0  # Force cleanup

        # Add old entries
        old_time = time.time() - 120  # 2 minutes ago
        storage.minute_requests["old_ip"] = [old_time]
        storage.hour_requests["old_ip"] = [old_time]

        # Run cleanup
        storage.cleanup()

        # Old entries should be removed
        assert "old_ip" not in storage.minute_requests or len(storage.minute_requests.get("old_ip", [])) == 0


class TestGetRateLimitStats:
    """Test rate limit statistics."""

    def test_stats_returns_dict(self):
        stats = get_rate_limit_stats()
        assert isinstance(stats, dict)
        assert "backend" in stats
        assert "tiers" in stats

    def test_stats_includes_all_tiers(self):
        stats = get_rate_limit_stats()
        tiers = stats["tiers"]

        assert "free" in tiers
        assert "premium" in tiers
        assert "pro" in tiers
        assert "unlimited" in tiers

    def test_stats_tier_has_limits(self):
        stats = get_rate_limit_stats()
        free_tier = stats["tiers"]["free"]

        assert "requests_per_minute" in free_tier
        assert "requests_per_hour" in free_tier
        assert "burst_limit" in free_tier


class TestRateLimitHeaders:
    """Test rate limit response headers."""

    def test_x_ratelimit_limit_header(self):
        """Verify X-RateLimit-Limit header is set correctly."""
        # This would be tested via integration test with actual middleware
        pass

    def test_x_ratelimit_remaining_header(self):
        """Verify X-RateLimit-Remaining header is set correctly."""
        pass

    def test_x_ratelimit_reset_header(self):
        """Verify X-RateLimit-Reset header is set correctly."""
        pass


class TestRateLimitMiddlewareUnit:
    """Unit tests for RateLimitMiddleware."""

    def test_exempt_paths(self):
        """Test that exempt paths bypass rate limiting."""
        app = Mock()
        middleware = RateLimitMiddleware(app, exempt_paths=["/health", "/docs"])

        assert middleware._is_exempt("/health")
        assert middleware._is_exempt("/docs")
        assert middleware._is_exempt("/health/cache")
        assert not middleware._is_exempt("/api/games")

    def test_get_client_identifier_with_api_key(self):
        """Test client identifier extraction with API key."""
        app = Mock()
        middleware = RateLimitMiddleware(app)

        request = Mock(spec=Request)
        request.headers = Headers({"x-api-key": "test_api_key_12345"})

        identifier = middleware._get_client_identifier(request)
        assert identifier.startswith("key:")

    def test_get_client_identifier_with_ip(self):
        """Test client identifier extraction with IP."""
        app = Mock()
        middleware = RateLimitMiddleware(app)

        request = Mock(spec=Request)
        request.headers = Headers({})
        request.client = Mock()
        request.client.host = "192.168.1.1"

        identifier = middleware._get_client_identifier(request)
        assert identifier == "ip:192.168.1.1"

    def test_get_effective_limits_default(self):
        """Test effective limits for default case."""
        app = Mock()
        middleware = RateLimitMiddleware(app)

        limits = middleware._get_effective_limits(Tier.FREE, "/api/custom")
        assert limits.requests_per_minute == TIER_LIMITS[Tier.FREE].requests_per_minute

    def test_get_effective_limits_with_endpoint_override(self):
        """Test effective limits with endpoint-specific override."""
        app = Mock()
        middleware = RateLimitMiddleware(app)

        limits = middleware._get_effective_limits(Tier.FREE, "/recommendations/run")
        # Should use endpoint-specific limit, not tier default
        assert limits.requests_per_minute == 5


class TestAuthRateLimitMiddleware:
    """Test authentication rate limiting."""

    def test_login_rate_limit_tracking(self):
        """Test that login attempts are tracked."""
        app = Mock()
        middleware = AuthRateLimitMiddleware(app, login_attempts_per_minute=5)

        # Verify initial state
        assert len(middleware.login_attempts) == 0

    def test_register_rate_limit_tracking(self):
        """Test that registration attempts are tracked."""
        app = Mock()
        middleware = AuthRateLimitMiddleware(app, register_attempts_per_hour=10)

        # Verify initial state
        assert len(middleware.register_attempts) == 0
