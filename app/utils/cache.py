from functools import wraps
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


class SimpleCache:
    def __init__(self, default_ttl: int = 300):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        self.hits = 0
        self.misses = 0
    
    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_data.encode()).hexdigest()[:16]
        return f"{prefix}:{key_hash}"
    
    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            entry = self._cache[key]
            if datetime.utcnow() < entry["expires_at"]:
                self.hits += 1
                return entry["value"]
            else:
                del self._cache[key]
        
        self.misses += 1
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        ttl = ttl or self.default_ttl
        self._cache[key] = {
            "value": value,
            "expires_at": datetime.utcnow() + timedelta(seconds=ttl),
            "created_at": datetime.utcnow()
        }
    
    def delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def clear(self) -> int:
        count = len(self._cache)
        self._cache.clear()
        return count
    
    def clear_prefix(self, prefix: str) -> int:
        keys_to_delete = [k for k in self._cache.keys() if k.startswith(prefix)]
        for key in keys_to_delete:
            del self._cache[key]
        return len(keys_to_delete)
    
    def cleanup_expired(self) -> int:
        now = datetime.utcnow()
        expired_keys = [
            k for k, v in self._cache.items()
            if v["expires_at"] < now
        ]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)
    
    def stats(self) -> Dict[str, Any]:
        total = self.hits + self.misses
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / total if total > 0 else 0,
            "size": len(self._cache)
        }


cache = SimpleCache(default_ttl=300)


def cached(prefix: str, ttl: Optional[int] = None):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = cache._make_key(prefix, *args[1:], **kwargs)
            
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator


def invalidate_cache(prefix: str):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            cleared = cache.clear_prefix(prefix)
            if cleared > 0:
                logger.debug(f"Invalidated {cleared} cache entries with prefix '{prefix}'")
            return result
        return wrapper
    return decorator
