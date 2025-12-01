from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db import init_db
from app.services.data_ingestion import seed_sample_data
from app.routers import health, clients, recommendations, games


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_sample_data()
    yield


app = FastAPI(
    title="Multi-Sport Betting & DFS Recommendation Agent",
    description="""
    A global multi-sport betting and DFS recommendation engine.
    
    **DISCLAIMER**: This is a SIMULATION-ONLY system for educational purposes.
    - No real money wagering should be based on these recommendations
    - Models are simplistic and do not guarantee profits
    - Real-world deployment would require stronger models, extensive backtesting,
      and compliance with gambling regulations
    
    **Supported Sports**:
    - US Major Leagues: NFL, NBA, MLB, NHL
    - College Sports: NCAA Football, NCAA Basketball
    - Global Sports: Soccer, Cricket, Rugby
    - Individual Sports: Tennis, Golf
    - Combat Sports: MMA, Boxing
    - Other: Motorsports, Esports
    """,
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(health.router)
app.include_router(clients.router)
app.include_router(games.router)
app.include_router(recommendations.router)


@app.get("/")
def root():
    return {
        "name": "Multi-Sport Betting & DFS Recommendation Agent",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "disclaimer": "SIMULATION ONLY - For educational purposes. No real money wagering."
    }
