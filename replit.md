# Multi-Sport Betting & DFS Recommendation Agent

## Overview
A comprehensive Python-based sports analytics and betting recommendation system covering 15 sports globally. The system uses machine learning models to identify value bets and provides personalized recommendations based on client risk profiles.

**Current State**: Complete MVP with working API

## Recent Changes
- 2024-12-01: Initial implementation of complete system
  - FastAPI backend with SQLite database
  - 15 sport-specific ML prediction models
  - Edge detection engine for value bet identification
  - Kelly Criterion-based bankroll management
  - Sample data seeding for all sports

## Project Architecture

### Directory Structure
```
app/
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
data/                # Sample CSV files
```

### Key Components
- **Database**: SQLite via SQLAlchemy with models for Teams, Competitors, Games, Markets, Lines, Clients, and BetRecommendations
- **ML Models**: ELO-based rating systems customized per sport
- **API**: FastAPI with automatic OpenAPI documentation at /docs

### Supported Sports
NFL, NBA, MLB, NHL, NCAA_FOOTBALL, NCAA_BASKETBALL, SOCCER, CRICKET, RUGBY, TENNIS, GOLF, MMA, BOXING, MOTORSPORTS, ESPORTS

## User Preferences
- None specified yet

## Running the Project
```bash
uvicorn app.main:app --host 0.0.0.0 --port 5000
```

## Key Endpoints
- GET /health - Health check
- POST /clients - Create client
- POST /clients/{id}/recommendations/run - Generate recommendations
- GET /clients/{id}/recommendations/latest - Get latest recommendations
- GET /games - List games
- GET /games/sports - List supported sports
