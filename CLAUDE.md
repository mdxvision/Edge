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
│   └── utils/logging.py    # Logging (use get_logger(__name__))
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
POST /auth/register          # Create account
POST /auth/login             # Login
GET  /games?sport=NBA        # List games
POST /recommendations/run    # Generate picks
GET  /tracker/picks          # Get tracked picks
GET  /analytics/edge-tracker # 8-factor analysis
```

## Database

SQLite at `sports_betting.db`. Key tables:
- `users`, `clients` - User accounts
- `games`, `teams` - Game data
- `tracked_picks` - Bet tracking
- `odds_snapshots` - Line movement history

## Environment Variables

Required in `.env`:
```
THE_ODDS_API_KEY=xxx
DATABASE_URL=sqlite:///sports_betting.db
SESSION_SECRET=xxx
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

## Testing

```bash
pytest tests/ -v
pytest tests/test_auth.py -v  # Single file
```

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
docker-compose up --build
```
