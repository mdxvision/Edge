# EdgeBet - Multi-Sport Betting & DFS Recommendation Platform

## Overview
A comprehensive global sports analytics and betting recommendation system covering 15 sports worldwide. The platform uses machine learning models to identify value bets and provides personalized recommendations based on client risk profiles with full transparency on every pick.

**Current State**: All Phases Complete - Production Ready

## Progress Summary

| Phase | Status | Completion |
|-------|--------|------------|
| Phase 1: Foundation & Frontend | Complete | 100% |
| Phase 2: Advanced ML & Historical Data | Complete | 100% |
| Phase 3: DFS Integration | Complete | 100% |
| Phase 4: Production Readiness | Complete | 100% |

## Recent Changes
- 2024-12-02: Phase 4 Complete - Production Infrastructure
  - PostgreSQL database migration (from SQLite)
  - User authentication system with secure session tokens
  - Password hashing with PBKDF2 (100,000 iterations)
  - HMAC token storage (tokens hashed before database storage)
  - Refresh token rotation on each use
  - Session invalidation on password change
  - Rate limiting middleware (100 req/min, 2000 req/hour)
  - Auth-specific rate limits (5 login attempts/min, 10 registrations/hour)
  - Security headers (CSP, HSTS, X-Frame-Options, etc.)
  - Structured logging with request tracking
  - In-memory caching layer with TTL
  - Enhanced API documentation with OpenAPI tags

- 2024-12-01: Phase 3 Complete - DFS Integration
  - Player projections engine with sport-specific factors
  - Lineup optimizer using PuLP linear programming
  - Salary cap and roster constraints per sport
  - Ownership projections and correlation analysis
  - DFS frontend page with lineup builder

- 2024-12-01: Phase 2 Complete - Advanced ML & Historical Data
  - Historical data models (GameResult, ELOHistory, PlayerStats, Injuries)
  - Historical data seeding with 2-3 seasons per sport
  - Advanced ELO system with recency weighting and sport-specific K-factors
  - Backtesting engine with accuracy, ROI, Brier score, Sharpe ratio
  - Model Performance page with team rankings and backtest results

- 2024-12-01: Phase 1 Complete
  - React TypeScript frontend with Vite + TailwindCSS v4
  - FastAPI backend with PostgreSQL database
  - 15 sport-specific ML prediction models (ELO-based)
  - Edge detection engine for value bet identification
  - Kelly Criterion-based bankroll management
  - 51 Pytest API tests (CI-ready)
  - Cypress E2E tests for frontend user flows
  - GitHub Actions CI workflow configured

## Project Architecture

### Directory Structure
```
app/                 # FastAPI Backend
├── main.py          # FastAPI entry point
├── config.py        # Configuration constants
├── db.py            # SQLAlchemy models
├── models/          # ML models (15 sport-specific)
├── schemas/         # Pydantic validation schemas
├── services/        # Business logic
│   ├── data_ingestion.py
│   ├── edge_engine.py
│   ├── bankroll.py
│   ├── auth.py          # Authentication service
│   ├── dfs_projections.py
│   ├── lineup_optimizer.py
│   └── agent.py
├── routers/         # API endpoints
│   ├── auth.py          # Authentication routes
│   ├── dfs.py           # DFS routes
│   ├── historical.py    # ML/Historical routes
│   └── ...
├── middleware/      # Custom middleware
│   ├── rate_limit.py    # Rate limiting
│   └── security.py      # Security headers
└── utils/           # Utilities
    ├── logging.py       # Structured logging
    ├── cache.py         # Caching layer
    └── odds.py          # Odds calculations
client/              # React TypeScript Frontend
├── src/
│   ├── pages/       # Dashboard, Games, Recommendations, Models, DFS, Profile
│   ├── components/  # Reusable UI components
│   ├── context/     # Auth context provider
│   └── lib/         # API client
├── cypress/         # E2E tests
│   └── e2e/         # Test specs
└── vite.config.ts   # Vite + TailwindCSS v4 config
tests/               # Pytest API tests
docs/                # Documentation
.github/workflows/   # CI configuration
```

### Key Components
- **Backend**: FastAPI with PostgreSQL via SQLAlchemy
- **Frontend**: React 19 + TypeScript + TailwindCSS v4 + React Query
- **Database Models**: Teams, Competitors, Games, Markets, Lines, Clients, BetRecommendations, Users, UserSessions
- **Authentication**: Session-based auth with PBKDF2 password hashing and HMAC token storage
- **ML Models**: ELO-based rating systems customized per sport
- **DFS Engine**: PuLP-based lineup optimizer with salary constraints
- **API Docs**: OpenAPI documentation at /docs and /redoc

### Supported Sports
NFL, NBA, MLB, NHL, NCAA_FOOTBALL, NCAA_BASKETBALL, SOCCER, CRICKET, RUGBY, TENNIS, GOLF, MMA, BOXING, MOTORSPORTS, ESPORTS

## User Preferences
- Clean professional design (NOT sports-themed)
- Transparency-first approach - show confidence, edge, and explanation for every pick
- Dark/Light mode toggle
- Mobile-responsive design

## Running the Project

### Development (both servers)
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
cd client && npm run dev
```

### Running Tests
```bash
# Backend API tests (51 tests)
python -m pytest tests/ -v

# Frontend E2E tests
cd client && npm run cypress:run
```

## Key Endpoints

### Core
- GET / - API information
- GET /health - Health check
- GET /docs - OpenAPI documentation
- GET /redoc - ReDoc documentation

### Authentication
- POST /auth/register - Register new user
- POST /auth/login - Login with email or username
- POST /auth/logout - Logout current session
- POST /auth/refresh - Refresh access token (rotates tokens)
- GET /auth/me - Get current user info
- POST /auth/change-password - Change password (invalidates all sessions)
- GET /auth/validate - Validate session token

### Clients
- POST /clients - Create client
- GET /clients/{id} - Get client details
- PATCH /clients/{id} - Update client
- DELETE /clients/{id} - Delete client

### Games
- GET /games - List games with filtering
- GET /games/sports - List supported sports
- GET /games/teams - List teams
- GET /games/competitors - List individual competitors

### Recommendations
- POST /clients/{id}/recommendations/run - Generate recommendations
- GET /clients/{id}/recommendations/latest - Get latest recommendations

### Historical/ML
- POST /historical/seed - Seed historical game data
- POST /historical/train-models - Train ELO models
- GET /historical/model-status - Get model training status
- GET /historical/ratings/{sport} - Get team power rankings
- POST /historical/backtest/{sport} - Run backtest
- GET /historical/backtest/results - Get backtest results

### DFS
- GET /dfs/projections - Get player projections
- POST /dfs/optimize - Generate optimal lineup
- GET /dfs/ownership - Get ownership projections

## Testing

### Backend Tests (Pytest)
51 comprehensive tests covering:
- Health endpoints
- Client CRUD operations with validation
- Recommendations generation and persistence
- Edge calculation and transparency fields
- Staking and probability bounds

### Frontend Tests (Cypress)
5 test files covering:
- Authentication flow (login, logout, session persistence)
- Dashboard navigation and layout
- Games browser with sport filtering
- Recommendations generation and display
- Profile settings updates

### CI/CD
GitHub Actions workflow runs:
1. Backend Pytest tests on Python 3.11
2. Frontend E2E tests using Cypress

## Security Features

### Authentication
- Passwords hashed with PBKDF2-SHA256 (100,000 iterations)
- Session/refresh tokens stored as HMAC-SHA256 hashes
- Refresh tokens rotated on each use (old tokens invalidated)
- All sessions invalidated when password is changed
- Timing-safe token comparison to prevent timing attacks

### Rate Limiting
- 100 requests per minute (general)
- 2000 requests per hour (general)
- 20 requests burst limit
- 5 login attempts per minute
- 10 registration attempts per hour

### Security Headers
- Content-Security-Policy
- Strict-Transport-Security
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Referrer-Policy: strict-origin-when-cross-origin
- Permissions-Policy

## Implementation Tracker
See `docs/IMPLEMENTATION_STATUS.md` for complete implementation details.
