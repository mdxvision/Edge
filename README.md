# Multi-Sport Betting & DFS Recommendation Agent

A global multi-sport betting and DFS (Daily Fantasy Sports) recommendation engine built with Python, FastAPI, and machine learning models.

## DISCLAIMER

**SIMULATION ONLY** - This project is for educational and testing purposes only.

- It does **not** place real bets or connect to actual sportsbooks
- The predictive models are simplified demonstrations and do **not** guarantee profits
- Any real-world deployment would require:
  - More sophisticated models with extensive backtesting
  - Compliance with gambling regulations and licensing
  - Responsible gambling safeguards
  - Legal review in your jurisdiction

## Features

- **15 Sports Covered**:
  - US Major Leagues: NFL, NBA, MLB, NHL
  - College Sports: NCAA Football, NCAA Basketball
  - Global Sports: Soccer (EPL, La Liga, etc.), Cricket, Rugby
  - Individual Sports: Tennis, Golf
  - Combat Sports: MMA, Boxing
  - Other: Motorsports, Esports

- **ML-Powered Predictions**: Each sport has a dedicated prediction model using ELO-style ratings and sport-specific features

- **Value Bet Detection**: Identifies positive expected value (+EV) opportunities by comparing model probabilities against sportsbook odds

- **Bankroll Management**: Kelly Criterion-inspired stake sizing with three risk profiles:
  - Conservative: Lower stakes, higher edge requirements
  - Balanced: Moderate approach
  - Aggressive: Higher stakes, accepts lower edges

- **RESTful API**: Clean FastAPI endpoints for integration with front-ends or chatbots

## Installation

```bash
pip install -r requirements.txt
```

## Running the Application

```bash
uvicorn app.main:app --host 0.0.0.0 --port 5000 --reload
```

The API will be available at `http://localhost:5000`

## API Documentation

Once running, visit:
- Swagger UI: `http://localhost:5000/docs`
- ReDoc: `http://localhost:5000/redoc`

## API Endpoints

### Health Check
```bash
GET /health
```

### Clients

```bash
# Create a client
POST /clients
{
  "name": "John Doe",
  "bankroll": 10000,
  "risk_profile": "balanced"
}

# Get a client
GET /clients/{client_id}

# Update a client
PATCH /clients/{client_id}
{
  "bankroll": 15000,
  "risk_profile": "aggressive"
}

# List all clients
GET /clients
```

### Games

```bash
# List all games
GET /games

# Filter by sport
GET /games?sport=NFL

# List supported sports
GET /games/sports

# List teams
GET /games/teams?sport=NBA

# List competitors (individual sports)
GET /games/competitors?sport=MMA
```

### Recommendations

```bash
# Generate recommendations for a client
POST /clients/{client_id}/recommendations/run
{
  "sports": ["NFL", "NBA", "MMA"],  # optional, defaults to all
  "min_edge": 0.03  # optional, default 3%
}

# Get latest recommendations
GET /clients/{client_id}/recommendations/latest
```

## Example Usage

```bash
# 1. Create a client
curl -X POST http://localhost:5000/clients \
  -H "Content-Type: application/json" \
  -d '{"name": "Demo User", "bankroll": 5000, "risk_profile": "balanced"}'

# 2. Run recommendations for all sports
curl -X POST http://localhost:5000/clients/1/recommendations/run \
  -H "Content-Type: application/json" \
  -d '{"min_edge": 0.03}'

# 3. Get latest recommendations
curl http://localhost:5000/clients/1/recommendations/latest
```

## Project Structure

```
.
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration settings
│   ├── db.py                # Database models (SQLAlchemy)
│   ├── models/              # ML prediction models per sport
│   │   ├── base.py          # Abstract base model class
│   │   ├── nfl.py, nba.py, etc.
│   ├── schemas/             # Pydantic schemas for API
│   ├── services/            # Business logic
│   │   ├── data_ingestion.py
│   │   ├── edge_engine.py   # Value bet detection
│   │   ├── bankroll.py      # Stake sizing
│   │   └── agent.py         # Orchestration
│   ├── routers/             # API endpoints
│   └── utils/               # Helper functions (odds, logging)
├── data/                    # Sample CSV data
├── requirements.txt
└── README.md
```

## How It Works

1. **Data Ingestion**: Sample games, teams, competitors, and betting lines are loaded from CSV files on startup

2. **Prediction Models**: Each sport has a model that uses ELO-style ratings to estimate win probabilities

3. **Edge Detection**: The edge engine compares model probabilities to sportsbook implied probabilities. If the model gives a higher probability than the books, that's a potential value bet.

4. **Bankroll Management**: Based on the client's risk profile and the size of the edge, the system recommends appropriate stake sizes while respecting daily exposure limits.

5. **Recommendations**: The agent orchestrator ties everything together, generating personalized recommendations with explanations.

## Risk Profiles

| Profile | Min Edge | Max Daily Exposure | Single Bet Max |
|---------|----------|-------------------|----------------|
| Conservative | 3% | 3% of bankroll | 2% |
| Balanced | 3% | 6% of bankroll | 2% |
| Aggressive | 2% | 10% of bankroll | 2% |

## Technologies Used

- **Python 3.11**
- **FastAPI** - Modern async web framework
- **SQLAlchemy** - ORM for SQLite database
- **Pydantic** - Data validation
- **pandas/numpy** - Data processing
- **scikit-learn** - ML utilities

## License

This project is for educational purposes only. Use at your own risk.
