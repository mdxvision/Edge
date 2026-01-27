from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
import os
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Set timezone to EST
os.environ['TZ'] = 'America/New_York'
try:
    time.tzset()
except AttributeError:
    pass  # tzset not available on Windows

from app.db import init_db
from app.services.data_ingestion import seed_sample_data
from app.routers import health, clients, recommendations, games
from app.routers.historical import router as historical_router
from app.routers.dfs import router as dfs_router
from app.routers.auth import router as auth_router
from app.routers.security import router as security_router
from app.routers.tracking import router as tracking_router
from app.routers.alerts import router as alerts_router
from app.routers.webhooks import router as webhooks_router
from app.routers.parlays import router as parlays_router
from app.routers.currency import router as currency_router
from app.routers.odds import router as odds_router
from app.routers.telegram import router as telegram_router
from app.routers.account import router as account_router
from app.routers.analytics import router as analytics_router
from app.routers.jobs import router as jobs_router
from app.routers.mlb import router as mlb_router
from app.routers.nba import router as nba_router
from app.routers.nfl import router as nfl_router
from app.routers.cbb import router as cbb_router
from app.routers.cfb import router as cfb_router
from app.routers.nhl import router as nhl_router
from app.routers.soccer import router as soccer_router
from app.routers.weather import router as weather_router
from app.routers.coaches import router as coaches_router
from app.routers.officials import router as officials_router
from app.routers.lines import router as lines_router
from app.routers.situations import router as situations_router
from app.routers.social import router as social_router
from app.routers.predictions import router as predictions_router
from app.routers.power_ratings import router as power_ratings_router
from app.routers.paper_trading import router as paper_trading_router
from app.routers.h2h import router as h2h_router
from app.routers.situational_trends import router as situational_trends_router
from app.routers.prediction_accuracy import router as prediction_accuracy_router
from app.routers.billing import router as billing_router
from app.routers.api_keys import router as api_keys_router
from app.routers.devices import router as devices_router
from app.routers.tracker import router as tracker_router
from app.routers.notifications import router as notifications_router
from app.routers.player_props import router as player_props_router
from app.routers.docs import router as docs_router
from app.routers.pinnacle import router as pinnacle_router
from app.routers.sgp import router as sgp_router
from app.routers.monte_carlo import router as monte_carlo_router
from app.routers.pnl_dashboard import router as pnl_dashboard_router
from app.routers.email_digest import router as email_digest_router
from app.middleware.rate_limit import RateLimitMiddleware, AuthRateLimitMiddleware
from app.middleware.security import SecurityHeadersMiddleware
from app.utils.logging import setup_logging, request_logger
from app.services.currency import seed_default_rates
from app.services.data_scheduler import start_schedulers, stop_schedulers
from app.services.background_jobs import alert_scheduler
from app.services.odds_scheduler import odds_scheduler
from app.services.email_digest import digest_scheduler

logger = setup_logging(level=os.environ.get("LOG_LEVEL", "DEBUG"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    is_testing = os.environ.get("TESTING", "").lower() in ("true", "1", "yes")

    init_db()
    seed_sample_data()
    from app.db import SessionLocal
    db = SessionLocal()
    try:
        seed_default_rates(db)
    finally:
        db.close()

    # Skip schedulers during tests to prevent hanging
    if not is_testing:
        # Start data refresh schedulers for MLB/NBA/CBB/Soccer
        start_schedulers()
        logger.info("MLB, NBA, CBB, and Soccer data schedulers started")

        # Start alert, odds, and digest schedulers
        await alert_scheduler.start()
        await odds_scheduler.start()
        await digest_scheduler.start()
        logger.info("Alert, odds, and digest schedulers started")

    yield

    # Cleanup on shutdown
    if not is_testing:
        stop_schedulers()
        await alert_scheduler.stop()
        await odds_scheduler.stop()
        await digest_scheduler.stop()
        logger.info("All schedulers stopped")


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

Rate limits vary by subscription tier:

| Tier | Requests/min | Requests/hour |
|------|-------------|---------------|
| Free | 30 | 500 |
| Premium | 60 | 2,000 |
| Pro | 120 | 5,000 |

Additional limits:
- 5 login attempts per minute
- 10 registration attempts per hour

Response headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
    """,
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "health", "description": "Health check endpoints"},
        {"name": "auth", "description": "User authentication and session management"},
        {"name": "security", "description": "2FA, session management, and audit logs"},
        {"name": "clients", "description": "Client profile management"},
        {"name": "games", "description": "Sports games and events"},
        {"name": "recommendations", "description": "Betting recommendations"},
        {"name": "tracking", "description": "Bet tracking and performance stats"},
        {"name": "parlays", "description": "Parlay analysis and creation"},
        {"name": "alerts", "description": "Custom alert notifications"},
        {"name": "webhooks", "description": "Webhook integrations"},
        {"name": "currency", "description": "Multi-currency support"},
        {"name": "historical", "description": "Historical data and ML model management"},
        {"name": "dfs", "description": "Daily Fantasy Sports optimization"},
        {"name": "analytics", "description": "Advanced analytics, CLV analysis, and line movements"},
        {"name": "MLB", "description": "Real-time MLB data from MLB Stats API"},
        {"name": "NBA", "description": "Real-time NBA data from NBA API"},
        {"name": "NFL", "description": "Real-time NFL data from ESPN API"},
        {"name": "College Basketball", "description": "NCAA Men's College Basketball data from ESPN"},
        {"name": "Soccer", "description": "European soccer data from Football-Data.org"},
        {"name": "Weather", "description": "Weather data and impact analysis for betting edges"},
        {"name": "coaches", "description": "Coach DNA - Situational records and behavioral analysis"},
        {"name": "officials", "description": "Referee/Umpire tendencies and O/U impact analysis"},
        {"name": "lines", "description": "Line movement tracking, steam moves, and sharp money detection"},
        {"name": "situations", "description": "Rest, travel, motivation, and schedule spot analysis"},
        {"name": "social", "description": "Social sentiment analysis and public betting percentages"},
        {"name": "predictions", "description": "Unified ML predictions combining all edge factors"},
        {"name": "power-ratings", "description": "Team power ratings, ATS records, and spread predictions"},
        {"name": "paper-trading", "description": "Virtual bankroll and paper trading for strategy validation"},
        {"name": "Head-to-Head", "description": "Historical H2H matchup data and rivalry analysis"},
        {"name": "Situational Trends", "description": "Team performance in various betting situations"},
        {"name": "Prediction Accuracy", "description": "Track and analyze prediction accuracy and factor performance"},
        {"name": "billing", "description": "Subscription management and Stripe checkout"},
        {"name": "api-keys", "description": "API key management for programmatic access (Pro tier)"},
        {"name": "devices", "description": "Device registration for push notifications"},
        {"name": "player-props", "description": "Player prop predictions and value finding"},
        {"name": "Pinnacle Sharp Lines", "description": "Sharp lines from Pinnacle, CLV tracking, and market efficiency analysis"},
        {"name": "Same Game Parlay", "description": "AI-assisted SGP builder with correlation analysis and EV calculation"},
        {"name": "Monte Carlo Simulation", "description": "Bankroll projections, risk of ruin, and bet sizing strategy analysis"},
        {"name": "P&L Dashboard", "description": "Comprehensive profit/loss tracking, ROI analysis, streaks, and CSV export"},
        {"name": "Email Digest", "description": "Daily email summaries with top edges, yesterday's results, and bankroll updates"},
        {"name": "Documentation", "description": "API documentation, examples, error codes, and Postman export"}
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
app.include_router(security_router)
app.include_router(clients.router)
app.include_router(games.router)
app.include_router(recommendations.router)
app.include_router(tracking_router)
app.include_router(parlays_router)
app.include_router(alerts_router)
app.include_router(webhooks_router)
app.include_router(currency_router)
app.include_router(odds_router)
app.include_router(telegram_router)
app.include_router(account_router)
app.include_router(historical_router)
app.include_router(dfs_router)
app.include_router(analytics_router)
app.include_router(jobs_router)
app.include_router(mlb_router)
app.include_router(nba_router)
app.include_router(nfl_router)
app.include_router(cbb_router)
app.include_router(cfb_router)
app.include_router(nhl_router)
app.include_router(soccer_router)
app.include_router(weather_router)
app.include_router(coaches_router)
app.include_router(officials_router)
app.include_router(lines_router)
app.include_router(situations_router)
app.include_router(social_router)
app.include_router(predictions_router)
app.include_router(power_ratings_router)
app.include_router(paper_trading_router)
app.include_router(h2h_router)
app.include_router(situational_trends_router)
app.include_router(prediction_accuracy_router)
app.include_router(billing_router)
app.include_router(api_keys_router)
app.include_router(devices_router)
app.include_router(tracker_router)
app.include_router(notifications_router)
app.include_router(player_props_router)
app.include_router(pinnacle_router)
app.include_router(sgp_router)
app.include_router(monte_carlo_router)
app.include_router(pnl_dashboard_router)
app.include_router(email_digest_router)
app.include_router(docs_router)


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
