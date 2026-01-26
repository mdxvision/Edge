# Edge - Sports Betting Platform

## Quick Start

```bash
# Start app (both backend + frontend)
./start_app.sh

# Watch logs in another terminal
./watch_logs.sh
```

**URLs:**
- Backend: http://localhost:8080
- Frontend: http://localhost:5001
- API Docs: http://localhost:8080/docs

## Project Structure

```
Edge/
├── app/                    # FastAPI backend
│   ├── main.py             # Entry point
│   ├── db.py               # SQLAlchemy models
│   ├── routers/            # API endpoints
│   ├── services/           # Business logic
│   └── utils/
│       ├── logging.py      # Logging (use get_logger(__name__))
│       └── cache.py        # Redis cache with in-memory fallback
├── client/                 # React + Vite frontend
├── tests/                  # Pytest tests
└── scripts/                # Utility scripts
```

## Key Services

| Service | Purpose |
|---------|---------|
| `edge_engine.py` | Value bet detection |
| `factor_generator.py` | 8-factor analysis |
| `odds_api.py` | The Odds API integration |
| `mlb_stats.py` | MLB Stats API |
| `nba_stats.py` | NBA API (nba_api package) |
| `nfl_stats.py` | ESPN API for NFL |
| `auth.py` | User authentication |
| `arbitrage.py` | Cross-book arb detection |
| `push_notifications.py` | Firebase push notifications |
| `edge_alerts.py` | Alert trigger system |
| `clv_tracker.py` | CLV capture & calibration |
| `player_props.py` | Player prop predictions |

## 8-Factor Edge System

| Factor | Weight | Source |
|--------|--------|--------|
| Line Movement | 20% | The Odds API |
| Coach DNA | 18% | Covers.com |
| Situational | 17% | Internal |
| Weather | 12% | Weather API |
| Officials | 10% | Covers.com |
| Public Fade | 10% | Action Network |
| ELO | 8% | Internal ratings |
| Social | 5% | Sentiment |

## API Endpoints (Main)

```
POST /auth/register              # Create account
POST /auth/login                 # Login
GET  /games?sport=NBA            # List games
POST /recommendations/run        # Generate picks
GET  /tracker/picks              # Get tracked picks
GET  /analytics/edge-tracker     # 8-factor analysis
GET  /analytics/arbitrage        # Find arb opportunities
POST /analytics/arbitrage/calculate  # Stake calculator
POST /player-props/predict       # Get prop prediction
GET  /player-props/value         # Find value props
```

## Database

Supports SQLite (dev) and PostgreSQL (prod). Key tables:
- `users`, `clients` - User accounts
- `games`, `teams` - Game data
- `tracked_picks` - Bet tracking
- `odds_snapshots` - Line movement history

**Migrate to PostgreSQL:**
```bash
python scripts/migrate_to_postgres.py \
  --sqlite ./sports_betting.db \
  --postgres postgresql://edge:password@localhost:5432/edge_db
```

## Environment Variables

See `.env.example` for all options. Required:
```
DATABASE_URL=postgresql://user:pass@localhost:5432/edge_db  # or sqlite:///...
THE_ODDS_API_KEY=xxx
SESSION_SECRET=xxx
REDIS_URL=redis://localhost:6379/0  # optional, falls back to in-memory
```

## Logging

Use the logging utility:
```python
from app.utils.logging import get_logger
logger = get_logger(__name__)

logger.debug("Detailed info")
logger.info("Normal operation")
logger.warning("Something unexpected")
logger.error("Failed", exc_info=True)
```

Logs write to `app.log` - watch with `./watch_logs.sh`

## Caching

Redis-backed with in-memory fallback:
```python
from app.utils.cache import cache, cached, TTL_MEDIUM

# Direct access
cache.set("key", value, ttl=300)
value = cache.get("key")

# Decorator (auto-generates cache key)
@cached("odds", ttl=TTL_MEDIUM)
async def fetch_odds(sport: str):
    ...
```

Check cache stats: `curl http://localhost:8080/health/cache`

## Rate Limiting

API rate limiting with Redis support and API key tiers:

**Tier Limits:**
| Tier | Requests/min | Requests/hour | Burst |
|------|-------------|---------------|-------|
| Free | 30 | 500 | 5 |
| Premium | 60 | 2,000 | 10 |
| Pro | 120 | 5,000 | 20 |

**Per-Endpoint Limits:** Heavy endpoints like `/recommendations/run` have stricter limits (5/min).

**API Key Headers:**
```bash
# Include X-API-Key for tier-based limits
curl -H "X-API-Key: pro_your_key" http://localhost:8080/games
```

**Response Headers:**
- `X-RateLimit-Limit` - Max requests per minute
- `X-RateLimit-Remaining` - Requests remaining in window
- `X-RateLimit-Reset` - Unix timestamp when limit resets
- `X-RateLimit-Tier` - Current rate limit tier

Check rate limit stats: `curl http://localhost:8080/health/rate-limit`

Disable for testing: Set `DISABLE_RATE_LIMIT=true` environment variable.

## Testing

**Before pushing, run all tests:**
```bash
./scripts/run-tests.sh           # Full suite (requires servers running)
./scripts/run-tests.sh --skip-e2e  # Skip Cypress (faster)
```

**Individual test commands:**
```bash
# Backend unit tests
pytest tests/ -v
pytest tests/test_auth.py -v  # Single file

# Frontend build check
cd client && npm run build

# Cypress E2E tests (requires servers running)
cd client && CYPRESS_BASE_URL=http://localhost:5173 npx cypress run
```

**Pre-push hook:** Automatically runs tests before push (local only)

## Common Tasks

**Refresh odds manually:**
```bash
curl -X POST http://localhost:8080/analytics/scheduler/refresh-now
```

**Check API status:**
```bash
curl http://localhost:8080/health
```

## GitHub Issues

Track work via GitHub issues: https://github.com/MDx-Vision/Edge/issues

## Documentation

- `docs/ARCHITECTURE.md` - System design
- `docs/BUILD_CHECKLIST.md` - Build tasks
- `docs/TEST_PLAN.md` - Testing strategy

## Docker

```bash
cd infrastructure/docker

# Development (no secrets needed)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Production (requires secrets setup first)
./setup-secrets.sh  # Run once, then edit secrets/*.txt
docker-compose up --build -d
```

**Services:** PostgreSQL, Redis, Backend (FastAPI), Frontend (nginx)

**Secrets:** Stored in `infrastructure/docker/secrets/` (gitignored)
