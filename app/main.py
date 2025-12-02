from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
import os

from app.db import init_db
from app.services.data_ingestion import seed_sample_data
from app.routers import health, clients, recommendations, games
from app.routers.historical import router as historical_router
from app.routers.dfs import router as dfs_router
from app.routers.auth import router as auth_router
from app.middleware.rate_limit import RateLimitMiddleware, AuthRateLimitMiddleware
from app.middleware.security import SecurityHeadersMiddleware
from app.utils.logging import setup_logging, request_logger

logger = setup_logging(level=os.environ.get("LOG_LEVEL", "INFO"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_sample_data()
    yield


app = FastAPI(
    title="EdgeBet - Multi-Sport Betting & DFS Platform",
    description="""
# EdgeBet API

A comprehensive global sports analytics and betting recommendation system covering 15 sports worldwide.

## IMPORTANT DISCLAIMER

**SIMULATION ONLY** - This is an educational platform for sports analytics.
- No real money wagering should be based on these recommendations
- Models are for demonstration and learning purposes
- Real-world deployment requires extensive backtesting and regulatory compliance

## Features

- **ML-Powered Predictions**: ELO-based rating systems customized per sport
- **Edge Detection**: Identifies value bets using Kelly Criterion
- **DFS Optimization**: Lineup optimization with salary constraints
- **Backtesting**: Historical model performance validation
- **Risk Management**: Personalized bankroll recommendations

## Supported Sports

| Category | Sports |
|----------|--------|
| US Major Leagues | NFL, NBA, MLB, NHL |
| College Sports | NCAA Football, NCAA Basketball |
| Global Sports | Soccer, Cricket, Rugby |
| Individual Sports | Tennis, Golf |
| Combat Sports | MMA, Boxing |
| Other | Motorsports, Esports |

## Authentication

This API uses session-based authentication. Register an account, then include your session token in the `Authorization` header:

```
Authorization: Bearer <session_token>
```

## Rate Limits

- 100 requests per minute
- 2000 requests per hour
- 5 login attempts per minute
- 10 registration attempts per hour
    """,
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "health", "description": "Health check endpoints"},
        {"name": "auth", "description": "User authentication and session management"},
        {"name": "clients", "description": "Client profile management"},
        {"name": "games", "description": "Sports games and events"},
        {"name": "recommendations", "description": "Betting recommendations"},
        {"name": "historical", "description": "Historical data and ML model management"},
        {"name": "dfs", "description": "Daily Fantasy Sports optimization"}
    ]
)

allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    expose_headers=["X-Process-Time", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AuthRateLimitMiddleware, login_attempts_per_minute=5, register_attempts_per_hour=10)
app.add_middleware(RateLimitMiddleware, requests_per_minute=100, requests_per_hour=2000, burst_limit=20)

app.include_router(health.router)
app.include_router(auth_router)
app.include_router(clients.router)
app.include_router(games.router)
app.include_router(recommendations.router)
app.include_router(historical_router)
app.include_router(dfs_router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    process_time_ms = process_time * 1000
    
    client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or (
        request.client.host if request.client else "unknown"
    )
    
    if process_time > 1.0:
        logger.warning(f"Slow request: {request.method} {request.url.path} took {process_time:.2f}s")
    
    request_logger.log_request(
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=process_time_ms,
        client_ip=client_ip
    )
    
    response.headers["X-Process-Time"] = str(round(process_time_ms, 2))
    
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or (
        request.client.host if request.client else "unknown"
    )
    
    request_logger.log_error(
        message=f"Unhandled exception: {type(exc).__name__}",
        exception=exc,
        path=request.url.path,
        client_ip=client_ip
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal error occurred",
            "type": type(exc).__name__
        }
    )


@app.get("/", tags=["health"])
def root():
    return {
        "name": "EdgeBet - Multi-Sport Betting & DFS Platform",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
        "features": [
            "betting_recommendations",
            "dfs_optimization", 
            "backtesting",
            "ml_models",
            "user_authentication"
        ],
        "sports_count": 15,
        "disclaimer": "SIMULATION ONLY - For educational purposes. No real money wagering."
    }
