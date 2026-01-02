# Edge Betting Platform - Architecture

## Last Updated: December 31, 2025

---

## Overview

Edge is a sports betting recommendation engine that uses an 8-factor analysis system to identify value bets. The platform tracks picks, calculates edge, and provides data-driven recommendations.

```
┌─────────────────────────────────────────────────────────────────┐
│                         EDGE PLATFORM                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   React     │    │   FastAPI   │    │   SQLite    │         │
│  │  Frontend   │───▶│   Backend   │───▶│  Database   │         │
│  │  (Vite)     │    │  (Python)   │    │             │         │
│  └─────────────┘    └──────┬──────┘    └─────────────┘         │
│                            │                                    │
│                    ┌───────┴───────┐                           │
│                    │ External APIs │                           │
│                    ├───────────────┤                           │
│                    │ • The Odds API│                           │
│                    │ • MySportsFeeds                           │
│                    │ • NBA API     │                           │
│                    │ • ESPN API    │                           │
│                    │ • Weather API │                           │
│                    └───────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | React + Vite + TailwindCSS | UI, dashboards |
| Backend | FastAPI (Python 3.13) | REST API, business logic |
| Database | SQLite + SQLAlchemy | Data persistence |
| Auth | PBKDF2 + HMAC tokens | User authentication |
| External | Multiple sports APIs | Real-time data |

---

## Directory Structure

```
Edge/
├── app/                          # Backend (FastAPI)
│   ├── main.py                   # App entry point
│   ├── db.py                     # Database models & connection
│   ├── config.py                 # Configuration
│   ├── betting_strategy.py       # Betting logic & rules
│   │
│   ├── routers/                  # API endpoints
│   │   ├── tracker.py            # Pick tracking endpoints
│   │   ├── recommendations.py    # Recommendation engine
│   │   ├── auth.py               # Authentication
│   │   ├── games.py              # Game data
│   │   ├── odds.py               # Odds data
│   │   ├── nba.py                # NBA-specific
│   │   ├── nfl.py                # NFL-specific
│   │   └── ...                   # Other sport routers
│   │
│   ├── services/                 # Business logic
│   │   ├── factor_generator.py   # 8-factor analysis (CORE)
│   │   ├── edge_tracker.py       # Pick tracking service
│   │   ├── edge_engine.py        # Edge calculation
│   │   ├── auto_settler.py       # Auto-settle picks
│   │   ├── nba_stats.py          # NBA data (rest days)
│   │   ├── nfl_stats.py          # NFL data (ESPN API)
│   │   ├── mysportsfeeds.py      # MySportsFeeds API
│   │   ├── weather_integration.py# Weather API
│   │   ├── odds_api.py           # The Odds API
│   │   ├── coach_dna.py          # Coach analysis
│   │   └── ...                   # Other services
│   │
│   ├── middleware/               # Request middleware
│   │   ├── rate_limit.py         # Rate limiting
│   │   └── security.py           # Security headers
│   │
│   └── utils/                    # Utilities
│       ├── cache.py              # Caching
│       └── logging.py            # Logging
│
├── client/                       # Frontend (React)
│   ├── src/
│   │   ├── App.tsx               # Main app
│   │   ├── pages/                # Page components
│   │   ├── components/           # Reusable components
│   │   └── context/              # React context
│   └── package.json
│
├── tests/                        # Test suite
│   └── test_*.py                 # Pytest tests
│
├── docs/                         # Documentation
│   └── IMPLEMENTATION_STATUS.md  # Progress tracking
│
├── .env                          # Environment variables
├── BUILD_CHECKLIST.md            # Build tasks
├── ARCHITECTURE.md               # This file
└── requirements.txt              # Python dependencies
```

---

## Core System: 8-Factor Analysis

The heart of Edge is the **Factor Generator** (`app/services/factor_generator.py`).

### Factor Breakdown

```
┌─────────────────────────────────────────────────────────────┐
│                    8-FACTOR ANALYSIS                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  COACH_DNA  │  │   REFEREE   │  │   WEATHER   │        │
│  │  ATS Data   │  │  Tendencies │  │   Impact    │        │
│  │  (Real)     │  │  (Real)     │  │  (Real)     │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │    REST     │  │   TRAVEL    │  │ LINE_MOVE   │        │
│  │  Days Off   │  │  Distance   │  │  Odds Shift │        │
│  │  (Real)     │  │  (Real)     │  │  (Jan 1)    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐                         │
│  │ SITUATIONAL │  │   PUBLIC    │                         │
│  │  Trends     │  │  Betting %  │                         │
│  │  (Building) │  │  (Manual)   │                         │
│  └─────────────┘  └─────────────┘                         │
│                                                             │
│  Each factor scores 0-100. Average = Overall Edge.         │
│  Score > 55 = Positive edge. Score < 45 = Negative edge.   │
└─────────────────────────────────────────────────────────────┘
```

### Factor Data Sources

| Factor | Source | Status | Data Type |
|--------|--------|--------|-----------|
| COACH_DNA | Sharp Football / Covers | ✅ Real | 62 coaches, ATS % |
| REFEREE | Covers.com | ✅ Real | 10 NBA refs, O/U & ATS |
| WEATHER | Weather API | ✅ Real | Temperature, wind, precip |
| REST | NBA API / ESPN | ✅ Real | Days since last game |
| TRAVEL | Static distances | ✅ Real | Miles between cities |
| LINE_MOVEMENT | The Odds API | ⏸️ Pending | Opening vs current line |
| SITUATIONAL | Own database | 🔄 Building | ATS by situation |
| PUBLIC_BETTING | Action Network | ✅ Manual | % of bets on each side |

---

## Data Flow

### Pick Generation Flow

```
User Request
     │
     ▼
┌─────────────────┐
│ /tracker/analyze│  (API Endpoint)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ FactorGenerator │  (Service)
│ .generate_factors()
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌────────┐
│NBA API │ │ESPN API│  (External)
│rest    │ │rest    │
└────┬───┘ └───┬────┘
     │         │
     └────┬────┘
          │
          ▼
┌─────────────────┐
│ 8 Factor Scores │
│ + Overall Edge  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Recommendation  │
│ LEAN/STRONG/FADE│
└─────────────────┘
```

### Pick Tracking Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Log Pick    │────▶│  Pending     │────▶│  Settled     │
│  /tracker/   │     │  (Waiting)   │     │  (Won/Lost)  │
│  picks POST  │     │              │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
                            │                    │
                            │                    │
                            ▼                    ▼
                     ┌──────────────┐     ┌──────────────┐
                     │ Auto-Settler │     │  Stats       │
                     │ (Background) │     │  Updated     │
                     └──────────────┘     └──────────────┘
```

---

## API Endpoints

### Core Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/tracker/picks` | Log a new pick |
| GET | `/tracker/picks` | Get all picks |
| POST | `/tracker/picks/{id}/settle` | Settle a pick |
| POST | `/tracker/analyze` | Analyze game (no log) |
| GET | `/tracker/stats` | Overall statistics |
| GET | `/tracker/summary` | Dashboard summary |

### Game Data

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/games` | List upcoming games |
| GET | `/games/sports` | List sports |
| GET | `/odds/{sport}` | Get current odds |

### Auth

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Login |
| POST | `/auth/logout` | Logout |
| GET | `/auth/me` | Current user |

---

## Database Schema

### Key Tables

```sql
-- Tracked picks
tracked_picks (
    id VARCHAR(50) PRIMARY KEY,
    sport VARCHAR(50),
    home_team VARCHAR(200),
    away_team VARCHAR(200),
    game_time DATETIME,
    pick VARCHAR(200),
    pick_team VARCHAR(200),
    odds INTEGER,
    confidence FLOAT,
    factors TEXT (JSON),
    status VARCHAR(20),  -- pending, won, lost, push
    units_wagered FLOAT,
    units_result FLOAT
)

-- Bankroll tracking
bankroll_snapshots (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    balance FLOAT,
    pick_id VARCHAR(50)
)

-- Users
users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255),
    username VARCHAR(100),
    password_hash VARCHAR(255)
)
```

---

## External API Integration

### The Odds API
- **Purpose**: Live odds, line movement
- **Endpoint**: `api.the-odds-api.com/v4/`
- **Auth**: API key in header
- **Limit**: 500 requests/month (free)
- **Status**: Key configured, resets Jan 1

### MySportsFeeds
- **Purpose**: Scores, schedules, injuries
- **Endpoint**: `api.mysportsfeeds.com/v2.1/`
- **Auth**: Basic auth (API key)
- **Status**: NBA + NFL active, injuries need $5 add-on

### NBA API (nba_api)
- **Purpose**: Rest days, stats, rosters
- **Library**: `nba_api` Python package
- **Auth**: None (free)
- **Status**: Working

### ESPN API
- **Purpose**: NFL schedules, scores
- **Endpoint**: `site.api.espn.com/apis/`
- **Auth**: None (free, undocumented)
- **Status**: Working

### Weather API
- **Purpose**: Game-day weather for outdoor sports
- **Endpoint**: `api.weatherapi.com/v1/`
- **Auth**: API key
- **Status**: Configured

---

## Betting Strategy

### Current Strategy (Dec 28, 2025+)
```python
UNDERDOG_ML_STRATEGY = {
    "odds_range": (+100, +200),
    "max_spread": 6.0,
    "units_per_bet": 1.5,
    "sports": ["NBA", "NFL"],
    "factors_required": 6,  # out of 8
    "min_edge_score": 52
}
```

### Edge Calculation
```
edge_score = average(all_8_factors)

if edge_score >= 60: "STRONG" recommendation
if edge_score >= 55: "LEAN" recommendation
if edge_score < 45:  "FADE" recommendation
else:                "NEUTRAL"
```

---

## Environment Variables

```bash
# Required
THE_ODDS_API_KEY=xxx          # Live odds
MYSPORTSFEEDS_API_KEY=xxx     # Scores, schedules

# Optional
WEATHER_API_KEY=xxx           # Weather data
DATABASE_URL=sqlite:///...    # Database path
SECRET_KEY=xxx                # Session encryption
```

---

## Running the App

### Backend
```bash
cd /Users/rafaelrodriguez/GitHub/Edge
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### Frontend
```bash
cd /Users/rafaelrodriguez/GitHub/Edge/client
npm run dev
```

### Tests
```bash
pytest tests/ -v
```

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `app/services/factor_generator.py` | 8-factor analysis (CORE) |
| `app/services/edge_tracker.py` | Pick tracking service |
| `app/services/nba_stats.py` | NBA rest day calculation |
| `app/services/nfl_stats.py` | NFL rest day calculation |
| `app/routers/tracker.py` | Tracker API endpoints |
| `app/db.py` | Database models |
| `app/betting_strategy.py` | Betting rules |

---

## Performance & Scaling

### Current
- SQLite database (single file)
- In-memory caching
- Single server deployment

### Future Considerations
- PostgreSQL for production
- Redis for caching
- Background job queue (Celery)
- CDN for frontend

---

## Security

| Feature | Implementation |
|---------|----------------|
| Password hashing | PBKDF2 + SHA256 (100k iterations) |
| Token storage | HMAC-SHA256 hashed |
| Rate limiting | 100/min, 2000/hour |
| Security headers | CSP, HSTS, X-Frame-Options |

---

## Monitoring & Observability

### Endpoints
- `GET /health` - Health check
- `GET /tracker/test/api-status` - External API status

### Logging
- Structured logging via `app/utils/logging.py`
- Request/response logging middleware

---

## Contributing

1. Create feature branch
2. Write tests
3. Update documentation
4. Submit PR

---

## Related Documents

- [BUILD_CHECKLIST.md](./BUILD_CHECKLIST.md) - Current tasks
- [IMPLEMENTATION_STATUS.md](./docs/IMPLEMENTATION_STATUS.md) - Phase tracking
- [FEATURE_BACKLOG.md](./FEATURE_BACKLOG.md) - Test coverage
