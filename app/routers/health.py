from fastapi import APIRouter
from app.utils.cache import cache
from app.middleware.rate_limit import get_rate_limit_stats

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "Multi-Sport Betting Agent API is running",
        "disclaimer": "SIMULATION ONLY - For educational purposes. No real money wagering."
    }


@router.get("/health/cache")
def cache_stats():
    """Get cache statistics."""
    stats = cache.stats()
    return {
        "status": "ok",
        "cache": stats
    }


@router.get("/health/rate-limit")
def rate_limit_stats():
    """Get rate limiting statistics and configuration."""
    stats = get_rate_limit_stats()
    return {
        "status": "ok",
        "rate_limit": stats
    }
