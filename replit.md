# EdgeBet - Multi-Sport Betting & DFS Recommendation Platform

## Overview
A comprehensive global sports analytics and betting recommendation system covering 15 sports worldwide. The platform uses machine learning models to identify value bets and provides personalized recommendations based on client risk profiles with full transparency on every pick.

**Current State**: Phase 1 Complete - Foundation with full testing suite

## Recent Changes
- 2024-12-01: Phase 1 Complete
  - React TypeScript frontend with Vite + TailwindCSS v4
  - FastAPI backend with SQLite database
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
│   └── agent.py
├── routers/         # API endpoints
└── utils/           # Odds calculations, logging
client/              # React TypeScript Frontend
├── src/
│   ├── pages/       # Dashboard, Games, Recommendations, Profile
│   ├── components/  # Reusable UI components
│   ├── context/     # Auth context provider
│   └── lib/         # API client
├── cypress/         # E2E tests
│   └── e2e/         # Test specs (auth, dashboard, games, recommendations, profile)
└── vite.config.ts   # Vite + TailwindCSS v4 config
tests/               # Pytest API tests
data/                # Sample CSV files
.github/workflows/   # CI configuration
```

### Key Components
- **Backend**: FastAPI with SQLite via SQLAlchemy
- **Frontend**: React 19 + TypeScript + TailwindCSS v4 + React Query
- **Database Models**: Teams, Competitors, Games, Markets, Lines, Clients, BetRecommendations
- **ML Models**: ELO-based rating systems customized per sport
- **API Docs**: Automatic OpenAPI documentation at /docs

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

# Frontend E2E tests (requires Docker or proper Cypress dependencies)
cd client && npm run cypress:run
```

## Key Endpoints
- GET /health - Health check
- POST /clients - Create client
- GET /clients/{id} - Get client details
- PATCH /clients/{id} - Update client
- DELETE /clients/{id} - Delete client
- POST /clients/{id}/recommendations/run - Generate recommendations
- GET /clients/{id}/recommendations/latest - Get latest recommendations
- GET /games - List games with filtering
- GET /games/sports - List supported sports
- GET /games/teams - List teams
- GET /games/competitors - List individual competitors

## Testing

### Backend Tests (Pytest)
Located in `tests/` directory with 51 comprehensive tests covering:
- Health endpoints
- Client CRUD operations with validation
- Recommendations generation and persistence
- Edge calculation and transparency fields
- Staking and probability bounds

### Frontend Tests (Cypress)
Located in `client/cypress/e2e/` with tests for:
- Authentication flow (login, logout, session persistence)
- Dashboard navigation and layout
- Games browser with sport filtering
- Recommendations generation and display
- Profile settings updates

### CI/CD
GitHub Actions workflow in `.github/workflows/test.yml` runs:
1. Backend Pytest tests on Python 3.11
2. Frontend E2E tests using Cypress Docker action

## Implementation Tracker
See `docs/IMPLEMENTATION_STATUS.md` for:
- Complete checklist of done vs pending tasks
- Testing gaps and coverage status
- Data sources needed
- Technical debt tracking
- Recommended next steps
