"""
Redis-backed caching with in-memory fallback.

Usage:
    from app.utils.cache import cache, cached, invalidate_cache

    # Direct cache access
    cache.set("key", value, ttl=300)
    value = cache.get("key")
    cache.delete("key")

    # Decorator for caching function results
    @cached("prefix", ttl=300)
    def expensive_function(arg1, arg2):
        ...

    # Decorator for cache invalidation
    @invalidate_cache("prefix")
    def update_function():
        ...
"""

import os
import json
import hashlib
from functools import wraps
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional, Union
from abc import ABC, abstractmethod

from app.utils.logging import get_logger

logger = get_logger(__name__)

# Cache TTL constants (in seconds)
TTL_SHORT = 60          # 1 minute
TTL_MEDIUM = 300        # 5 minutes
TTL_LONG = 900          # 15 minutes
TTL_HOUR = 3600         # 1 hour
TTL_DAY = 86400         # 24 hours

# Cache key prefixes
PREFIX_ODDS = "odds"
PREFIX_GAMES = "games"
PREFIX_TEAMS = "teams"
PREFIX_STATS = "stats"
PREFIX_SESSION = "session"


class CacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int) -> bool:
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        pass

    @abstractmethod
    def clear_prefix(self, prefix: str) -> int:
        pass

    @abstractmethod
    def clear_all(self) -> int:
        pass

    @abstractmethod
    def stats(self) -> Dict[str, Any]:
        pass


class InMemoryCache(CacheBackend):
    """Simple in-memory cache for development/fallback."""

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            entry = self._cache[key]
            if datetime.utcnow() < entry["expires_at"]:
                self._hits += 1
                return entry["value"]
            else:
                del self._cache[key]

        self._misses += 1
        return None

    def set(self, key: str, value: Any, ttl: int) -> bool:
        self._cache[key] = {
            "value": value,
            "expires_at": datetime.utcnow() + timedelta(seconds=ttl),
        }
        return True

    def delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear_prefix(self, prefix: str) -> int:
        keys = [k for k in self._cache.keys() if k.startswith(f"{prefix}:")]
        for key in keys:
            del self._cache[key]
        return len(keys)

    def clear_all(self) -> int:
        count = len(self._cache)
        self._cache.clear()
        return count

    def stats(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        return {
            "backend": "memory",
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total, 3) if total > 0 else 0,
            "size": len(self._cache),
        }


class RedisCache(CacheBackend):
    """Redis-backed cache for production."""

    def __init__(self, redis_url: str):
        import redis
        self._client = redis.from_url(redis_url, decode_responses=True)
        self._hits = 0
        self._misses = 0
        self._prefix = "edge:"  # Namespace all keys

    def _key(self, key: str) -> str:
        return f"{self._prefix}{key}"

    def get(self, key: str) -> Optional[Any]:
        try:
            data = self._client.get(self._key(key))
            if data:
                self._hits += 1
                return json.loads(data)
            self._misses += 1
            return None
        except Exception as e:
            logger.error(f"Redis GET error: {e}")
            self._misses += 1
            return None

    def set(self, key: str, value: Any, ttl: int) -> bool:
        try:
            data = json.dumps(value, default=str)
            self._client.setex(self._key(key), ttl, data)
            return True
        except Exception as e:
            logger.error(f"Redis SET error: {e}")
            return False

    def delete(self, key: str) -> bool:
        try:
            return self._client.delete(self._key(key)) > 0
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}")
            return False

    def clear_prefix(self, prefix: str) -> int:
        try:
            pattern = f"{self._prefix}{prefix}:*"
            keys = self._client.keys(pattern)
            if keys:
                return self._client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis CLEAR error: {e}")
            return 0

    def clear_all(self) -> int:
        try:
            pattern = f"{self._prefix}*"
            keys = self._client.keys(pattern)
            if keys:
                return self._client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis CLEAR ALL error: {e}")
            return 0

    def stats(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        try:
            info = self._client.info("stats")
            db_size = self._client.dbsize()
        except Exception:
            info = {}
            db_size = 0

        return {
            "backend": "redis",
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total, 3) if total > 0 else 0,
            "db_size": db_size,
            "redis_hits": info.get("keyspace_hits", 0),
            "redis_misses": info.get("keyspace_misses", 0),
        }

    def ping(self) -> bool:
        try:
            return self._client.ping()
        except Exception:
            return False


class Cache:
    """
    Unified cache interface with Redis and in-memory fallback.
    """

    def __init__(self):
        self._backend: CacheBackend
        self._default_ttl = TTL_MEDIUM

        redis_url = os.environ.get("REDIS_URL")

        if redis_url:
            try:
                self._backend = RedisCache(redis_url)
                if self._backend.ping():
                    logger.info(f"Redis cache connected: {redis_url.split('@')[-1] if '@' in redis_url else redis_url}")
                else:
                    raise ConnectionError("Redis ping failed")
            except Exception as e:
                logger.warning(f"Redis connection failed ({e}), using in-memory cache")
                self._backend = InMemoryCache()
        else:
            logger.info("No REDIS_URL configured, using in-memory cache")
            self._backend = InMemoryCache()

    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a cache key from prefix and arguments."""
        key_data = json.dumps({"a": args, "k": kwargs}, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_data.encode()).hexdigest()[:12]
        return f"{prefix}:{key_hash}"

    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        return self._backend.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in cache with TTL."""
        return self._backend.set(key, value, ttl or self._default_ttl)

    def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        return self._backend.delete(key)

    def invalidate(self, prefix: str) -> int:
        """Invalidate all keys with a given prefix."""
        count = self._backend.clear_prefix(prefix)
        if count > 0:
            logger.debug(f"Invalidated {count} cache entries with prefix '{prefix}'")
        return count

    def clear(self) -> int:
        """Clear all cache entries."""
        return self._backend.clear_all()

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self._backend.stats()

    def is_redis(self) -> bool:
        """Check if using Redis backend."""
        return isinstance(self._backend, RedisCache)


# Global cache instance
cache = Cache()


def cached(prefix: str, ttl: Optional[int] = None):
    """
    Decorator to cache function results.

    Usage:
        @cached("odds", ttl=300)
        async def get_odds(sport: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Skip 'self' or 'db' arguments for key generation
            cache_args = args[1:] if args else args
            cache_key = cache._make_key(prefix, *cache_args, **kwargs)

            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache HIT: {cache_key}")
                return cached_value

            logger.debug(f"Cache MISS: {cache_key}")
            result = await func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache_args = args[1:] if args else args
            cache_key = cache._make_key(prefix, *cache_args, **kwargs)

            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache HIT: {cache_key}")
                return cached_value

            logger.debug(f"Cache MISS: {cache_key}")
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def invalidate_cache(prefix: str):
    """
    Decorator to invalidate cache after function execution.

    Usage:
        @invalidate_cache("odds")
        async def update_odds():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            cache.invalidate(prefix)
            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            cache.invalidate(prefix)
            return result

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
