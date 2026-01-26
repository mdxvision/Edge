"""
Rate limiting middleware with Redis support and API key tiers.

Features:
- Per-endpoint rate limits
- API key tier support (Free/Premium/Pro)
- Redis-backed with in-memory fallback
- Standard rate limit headers (X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset)
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import time
import os
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging
import json

logger = logging.getLogger(__name__)

MAX_TRACKED_IPS = 10000

# Allow disabling rate limiting via environment variable (for testing)
RATE_LIMIT_DISABLED = os.environ.get("DISABLE_RATE_LIMIT", "").lower() in ("true", "1", "yes")


class Tier(Enum):
    """API key subscription tiers."""
    FREE = "free"
    PREMIUM = "premium"
    PRO = "pro"
    UNLIMITED = "unlimited"  # For internal/admin use


@dataclass
class TierLimits:
    """Rate limits for a specific tier."""
    requests_per_minute: int
    requests_per_hour: int
    burst_limit: int


# Default tier limits
TIER_LIMITS: Dict[Tier, TierLimits] = {
    Tier.FREE: TierLimits(requests_per_minute=30, requests_per_hour=500, burst_limit=5),
    Tier.PREMIUM: TierLimits(requests_per_minute=60, requests_per_hour=2000, burst_limit=10),
    Tier.PRO: TierLimits(requests_per_minute=120, requests_per_hour=5000, burst_limit=20),
    Tier.UNLIMITED: TierLimits(requests_per_minute=10000, requests_per_hour=100000, burst_limit=100),
}


@dataclass
class EndpointLimits:
    """Per-endpoint rate limit configuration."""
    requests_per_minute: Optional[int] = None
    requests_per_hour: Optional[int] = None
    burst_limit: Optional[int] = None


# Per-endpoint rate limit overrides (path patterns)
ENDPOINT_LIMITS: Dict[str, EndpointLimits] = {
    # Heavy computation endpoints - stricter limits
    "/recommendations/run": EndpointLimits(requests_per_minute=5, requests_per_hour=50),
    "/analytics/arbitrage": EndpointLimits(requests_per_minute=10, requests_per_hour=100),
    "/player-props/predict": EndpointLimits(requests_per_minute=10, requests_per_hour=100),
    "/analytics/edge-tracker": EndpointLimits(requests_per_minute=10, requests_per_hour=100),

    # Data-heavy endpoints - moderate limits
    "/games": EndpointLimits(requests_per_minute=30, requests_per_hour=300),
    "/odds": EndpointLimits(requests_per_minute=30, requests_per_hour=300),

    # Read-only endpoints - relaxed limits
    "/health": EndpointLimits(requests_per_minute=120, requests_per_hour=1000),
    "/docs": EndpointLimits(requests_per_minute=60, requests_per_hour=500),
}


class RateLimitStorage:
    """
    Abstract storage interface for rate limiting.
    Supports Redis and in-memory backends.
    """

    def __init__(self):
        self._redis_client = None
        self._use_redis = False
        self._init_storage()

        # In-memory fallback storage
        self.minute_requests: Dict[str, List[float]] = {}
        self.hour_requests: Dict[str, List[float]] = {}
        self.burst_tracker: Dict[str, Tuple[float, int]] = {}
        self._last_cleanup = time.time()

    def _init_storage(self):
        """Initialize Redis connection if available."""
        redis_url = os.environ.get("REDIS_URL")
        if redis_url:
            try:
                import redis
                self._redis_client = redis.from_url(redis_url, decode_responses=True)
                self._redis_client.ping()
                self._use_redis = True
                logger.info("Rate limiter using Redis backend")
            except Exception as e:
                logger.warning(f"Redis connection failed for rate limiter ({e}), using in-memory")
                self._use_redis = False
        else:
            logger.info("Rate limiter using in-memory backend")

    def _redis_key(self, key_type: str, identifier: str, endpoint: str = "") -> str:
        """Generate Redis key for rate limiting."""
        if endpoint:
            return f"ratelimit:{key_type}:{identifier}:{endpoint}"
        return f"ratelimit:{key_type}:{identifier}"

    def get_minute_count(self, identifier: str, endpoint: str = "") -> int:
        """Get request count for the last minute."""
        if self._use_redis:
            try:
                key = self._redis_key("minute", identifier, endpoint)
                count = self._redis_client.get(key)
                return int(count) if count else 0
            except Exception as e:
                logger.error(f"Redis error in get_minute_count: {e}")
                # Fall through to in-memory

        cache_key = f"{identifier}:{endpoint}" if endpoint else identifier
        now = time.time()
        minute_ago = now - 60
        if cache_key in self.minute_requests:
            return len([t for t in self.minute_requests[cache_key] if t > minute_ago])
        return 0

    def get_hour_count(self, identifier: str, endpoint: str = "") -> int:
        """Get request count for the last hour."""
        if self._use_redis:
            try:
                key = self._redis_key("hour", identifier, endpoint)
                count = self._redis_client.get(key)
                return int(count) if count else 0
            except Exception as e:
                logger.error(f"Redis error in get_hour_count: {e}")

        cache_key = f"{identifier}:{endpoint}" if endpoint else identifier
        now = time.time()
        hour_ago = now - 3600
        if cache_key in self.hour_requests:
            return len([t for t in self.hour_requests[cache_key] if t > hour_ago])
        return 0

    def increment_minute(self, identifier: str, endpoint: str = "") -> int:
        """Increment minute counter, returns new count."""
        if self._use_redis:
            try:
                key = self._redis_key("minute", identifier, endpoint)
                pipe = self._redis_client.pipeline()
                pipe.incr(key)
                pipe.expire(key, 60)
                results = pipe.execute()
                return results[0]
            except Exception as e:
                logger.error(f"Redis error in increment_minute: {e}")

        cache_key = f"{identifier}:{endpoint}" if endpoint else identifier
        now = time.time()
        if cache_key not in self.minute_requests:
            self.minute_requests[cache_key] = []
        self.minute_requests[cache_key].append(now)
        return len(self.minute_requests[cache_key])

    def increment_hour(self, identifier: str, endpoint: str = "") -> int:
        """Increment hour counter, returns new count."""
        if self._use_redis:
            try:
                key = self._redis_key("hour", identifier, endpoint)
                pipe = self._redis_client.pipeline()
                pipe.incr(key)
                pipe.expire(key, 3600)
                results = pipe.execute()
                return results[0]
            except Exception as e:
                logger.error(f"Redis error in increment_hour: {e}")

        cache_key = f"{identifier}:{endpoint}" if endpoint else identifier
        now = time.time()
        if cache_key not in self.hour_requests:
            self.hour_requests[cache_key] = []
        self.hour_requests[cache_key].append(now)
        return len(self.hour_requests[cache_key])

    def check_burst(self, identifier: str) -> bool:
        """Check and update burst limit. Returns True if allowed."""
        now = time.time()

        if self._use_redis:
            try:
                key = self._redis_key("burst", identifier)
                pipe = self._redis_client.pipeline()
                pipe.get(key)
                pipe.incr(key)
                pipe.expire(key, 1)
                results = pipe.execute()
                count = int(results[0]) if results[0] else 0
                return True  # Actual check happens in middleware
            except Exception as e:
                logger.error(f"Redis error in check_burst: {e}")

        if identifier in self.burst_tracker:
            last_time, count = self.burst_tracker[identifier]
            if now - last_time < 1:
                self.burst_tracker[identifier] = (last_time, count + 1)
                return count < 100  # Max burst
            else:
                self.burst_tracker[identifier] = (now, 1)
        else:
            self.burst_tracker[identifier] = (now, 1)
        return True

    def get_burst_count(self, identifier: str) -> int:
        """Get current burst count."""
        if self._use_redis:
            try:
                key = self._redis_key("burst", identifier)
                count = self._redis_client.get(key)
                return int(count) if count else 0
            except Exception as e:
                logger.error(f"Redis error in get_burst_count: {e}")

        if identifier in self.burst_tracker:
            _, count = self.burst_tracker[identifier]
            return count
        return 0

    def get_reset_time(self, window: str = "minute") -> int:
        """Get Unix timestamp when rate limit resets."""
        now = int(time.time())
        if window == "minute":
            return now + 60 - (now % 60)
        elif window == "hour":
            return now + 3600 - (now % 3600)
        return now + 60

    def cleanup(self):
        """Cleanup expired entries (for in-memory storage only)."""
        if self._use_redis:
            return  # Redis handles expiration automatically

        now = time.time()
        if now - self._last_cleanup < 60:
            return

        self._last_cleanup = now
        minute_ago = now - 60
        hour_ago = now - 3600

        # Cleanup minute requests
        for key in list(self.minute_requests.keys()):
            self.minute_requests[key] = [t for t in self.minute_requests[key] if t > minute_ago]
            if not self.minute_requests[key]:
                del self.minute_requests[key]

        # Cleanup hour requests
        for key in list(self.hour_requests.keys()):
            self.hour_requests[key] = [t for t in self.hour_requests[key] if t > hour_ago]
            if not self.hour_requests[key]:
                del self.hour_requests[key]

        # Cleanup burst tracker
        for key in list(self.burst_tracker.keys()):
            last_time, _ = self.burst_tracker[key]
            if now - last_time > 10:
                del self.burst_tracker[key]

        # Limit memory usage
        if len(self.minute_requests) > MAX_TRACKED_IPS:
            oldest_keys = sorted(
                self.minute_requests.keys(),
                key=lambda k: min(self.minute_requests[k]) if self.minute_requests[k] else 0
            )
            for key in oldest_keys[:len(self.minute_requests) - MAX_TRACKED_IPS]:
                del self.minute_requests[key]


# Global storage instance
_storage = RateLimitStorage()


def get_user_tier(request: Request) -> Tier:
    """
    Extract user tier from request.
    Checks API key header, then authenticated user session.
    """
    # Check X-API-Key header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        # In production, look up the API key in database
        # For now, use prefix-based tier detection
        if api_key.startswith("pro_"):
            return Tier.PRO
        elif api_key.startswith("premium_"):
            return Tier.PREMIUM
        elif api_key.startswith("admin_") or api_key.startswith("internal_"):
            return Tier.UNLIMITED

    # Check authenticated user's subscription tier
    # This would typically come from JWT token or session
    user = getattr(request.state, "user", None)
    if user:
        tier_str = getattr(user, "subscription_tier", "free")
        try:
            return Tier(tier_str.lower())
        except ValueError:
            pass

    return Tier.FREE


def get_endpoint_limits(path: str) -> Optional[EndpointLimits]:
    """Get rate limits for a specific endpoint path."""
    # Check exact match first
    if path in ENDPOINT_LIMITS:
        return ENDPOINT_LIMITS[path]

    # Check prefix matches
    for pattern, limits in ENDPOINT_LIMITS.items():
        if path.startswith(pattern):
            return limits

    return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with tier support and per-endpoint limits.

    Features:
    - Per-IP rate limiting
    - API key tier support (Free/Premium/Pro)
    - Per-endpoint limit overrides
    - Redis-backed with in-memory fallback
    - Standard rate limit headers
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_limit: int = 10,
        exempt_paths: list = None
    ):
        super().__init__(app)
        # Default limits (used as base for FREE tier)
        self.default_limits = TierLimits(
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour,
            burst_limit=burst_limit
        )
        self.exempt_paths = exempt_paths or ["/health", "/docs", "/openapi.json", "/"]

    def _get_client_identifier(self, request: Request) -> str:
        """Get client identifier (API key or IP address)."""
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"key:{api_key[:16]}"  # Use prefix of API key

        if request.client and request.client.host:
            return f"ip:{request.client.host}"

        return "ip:unknown"

    def _is_exempt(self, path: str) -> bool:
        """Check if path is exempt from rate limiting."""
        return any(path.startswith(exempt) for exempt in self.exempt_paths)

    def _get_effective_limits(self, tier: Tier, path: str) -> TierLimits:
        """Get effective rate limits for a request."""
        tier_limits = TIER_LIMITS.get(tier, TIER_LIMITS[Tier.FREE])
        endpoint_limits = get_endpoint_limits(path)

        if endpoint_limits:
            return TierLimits(
                requests_per_minute=endpoint_limits.requests_per_minute or tier_limits.requests_per_minute,
                requests_per_hour=endpoint_limits.requests_per_hour or tier_limits.requests_per_hour,
                burst_limit=endpoint_limits.burst_limit or tier_limits.burst_limit
            )

        return tier_limits

    async def dispatch(self, request: Request, call_next):
        if RATE_LIMIT_DISABLED:
            return await call_next(request)

        path = request.url.path

        if self._is_exempt(path):
            return await call_next(request)

        # Cleanup old entries periodically
        _storage.cleanup()

        # Get client identifier and tier
        identifier = self._get_client_identifier(request)
        tier = get_user_tier(request)
        limits = self._get_effective_limits(tier, path)

        # For per-endpoint limits, use path-specific tracking
        endpoint_key = path.split("?")[0]  # Remove query params

        # Check burst limit
        burst_count = _storage.get_burst_count(identifier)
        if burst_count >= limits.burst_limit:
            logger.warning(f"Burst limit exceeded for {identifier}")
            return self._rate_limit_response(
                "Too many requests. Please slow down.",
                retry_after=1,
                limit=limits.burst_limit,
                remaining=0,
                reset=_storage.get_reset_time("minute")
            )
        _storage.check_burst(identifier)

        # Check minute limit
        minute_count = _storage.get_minute_count(identifier, endpoint_key)
        if minute_count >= limits.requests_per_minute:
            logger.warning(f"Minute rate limit exceeded for {identifier}: {minute_count} requests")
            return self._rate_limit_response(
                "Rate limit exceeded. Too many requests per minute.",
                retry_after=60,
                limit=limits.requests_per_minute,
                remaining=0,
                reset=_storage.get_reset_time("minute")
            )

        # Check hour limit
        hour_count = _storage.get_hour_count(identifier, endpoint_key)
        if hour_count >= limits.requests_per_hour:
            logger.warning(f"Hourly rate limit exceeded for {identifier}: {hour_count} requests")
            return self._rate_limit_response(
                "Rate limit exceeded. Too many requests per hour.",
                retry_after=3600,
                limit=limits.requests_per_hour,
                remaining=0,
                reset=_storage.get_reset_time("hour")
            )

        # Record the request
        _storage.increment_minute(identifier, endpoint_key)
        _storage.increment_hour(identifier, endpoint_key)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        new_minute_count = _storage.get_minute_count(identifier, endpoint_key)
        response.headers["X-RateLimit-Limit"] = str(limits.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limits.requests_per_minute - new_minute_count))
        response.headers["X-RateLimit-Reset"] = str(_storage.get_reset_time("minute"))
        response.headers["X-RateLimit-Tier"] = tier.value

        return response

    def _rate_limit_response(
        self,
        detail: str,
        retry_after: int,
        limit: int,
        remaining: int,
        reset: int
    ) -> JSONResponse:
        """Create a rate limit exceeded response."""
        return JSONResponse(
            status_code=429,
            content={
                "detail": detail,
                "retry_after": retry_after
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(reset)
            }
        )


class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Specialized rate limiting for authentication endpoints.

    Stricter limits to prevent brute force attacks.
    """

    def __init__(
        self,
        app,
        login_attempts_per_minute: int = 5,
        register_attempts_per_hour: int = 10
    ):
        super().__init__(app)
        self.login_attempts_per_minute = login_attempts_per_minute
        self.register_attempts_per_hour = register_attempts_per_hour

        # Use separate in-memory storage for auth (always local for security)
        self.login_attempts: Dict[str, List[float]] = {}
        self.register_attempts: Dict[str, List[float]] = {}
        self._last_cleanup = time.time()

    def _get_client_ip(self, request: Request) -> str:
        if request.client and request.client.host:
            return request.client.host
        return "unknown"

    def _cleanup_all(self):
        now = time.time()

        if now - self._last_cleanup < 60:
            return

        self._last_cleanup = now
        minute_ago = now - 60
        hour_ago = now - 3600

        for ip in list(self.login_attempts.keys()):
            self.login_attempts[ip] = [t for t in self.login_attempts[ip] if t > minute_ago]
            if not self.login_attempts[ip]:
                del self.login_attempts[ip]

        for ip in list(self.register_attempts.keys()):
            self.register_attempts[ip] = [t for t in self.register_attempts[ip] if t > hour_ago]
            if not self.register_attempts[ip]:
                del self.register_attempts[ip]

    async def dispatch(self, request: Request, call_next):
        if RATE_LIMIT_DISABLED:
            return await call_next(request)

        path = request.url.path
        method = request.method

        if method != "POST":
            return await call_next(request)

        self._cleanup_all()

        client_ip = self._get_client_ip(request)
        now = time.time()
        reset_time = _storage.get_reset_time("minute")

        if path == "/auth/login":
            minute_ago = now - 60
            if client_ip in self.login_attempts:
                self.login_attempts[client_ip] = [
                    t for t in self.login_attempts[client_ip] if t > minute_ago
                ]

            current_count = len(self.login_attempts.get(client_ip, []))
            if current_count >= self.login_attempts_per_minute:
                logger.warning(f"Login rate limit exceeded for {client_ip}")
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Too many login attempts. Please try again later.",
                        "retry_after": 60
                    },
                    headers={
                        "Retry-After": "60",
                        "X-RateLimit-Limit": str(self.login_attempts_per_minute),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_time)
                    }
                )

            if client_ip not in self.login_attempts:
                self.login_attempts[client_ip] = []
            self.login_attempts[client_ip].append(now)

        elif path == "/auth/register":
            hour_ago = now - 3600
            if client_ip in self.register_attempts:
                self.register_attempts[client_ip] = [
                    t for t in self.register_attempts[client_ip] if t > hour_ago
                ]

            current_count = len(self.register_attempts.get(client_ip, []))
            if current_count >= self.register_attempts_per_hour:
                logger.warning(f"Registration rate limit exceeded for {client_ip}")
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Too many registration attempts. Please try again later.",
                        "retry_after": 3600
                    },
                    headers={
                        "Retry-After": "3600",
                        "X-RateLimit-Limit": str(self.register_attempts_per_hour),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(_storage.get_reset_time("hour"))
                    }
                )

            if client_ip not in self.register_attempts:
                self.register_attempts[client_ip] = []
            self.register_attempts[client_ip].append(now)

        return await call_next(request)


def get_rate_limit_stats() -> Dict[str, Any]:
    """Get current rate limiting statistics."""
    return {
        "backend": "redis" if _storage._use_redis else "memory",
        "tracked_identifiers": len(_storage.minute_requests) if not _storage._use_redis else "N/A",
        "rate_limit_disabled": RATE_LIMIT_DISABLED,
        "tiers": {tier.value: {
            "requests_per_minute": limits.requests_per_minute,
            "requests_per_hour": limits.requests_per_hour,
            "burst_limit": limits.burst_limit
        } for tier, limits in TIER_LIMITS.items()}
    }
