from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
import logging

from app.db import init_db
from app.services.data_ingestion import seed_sample_data
from app.routers import health, clients, recommendations, games
from app.routers.historical import router as historical_router
from app.routers.dfs import router as dfs_router
from app.routers.auth import router as auth_router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    
    if process_time > 1.0:
        logger.warning(f"Slow request: {request.method} {request.url.path} took {process_time:.2f}s")
    
    response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal error occurred",
            "type": type(exc).__name__
        }
    )


@app.get("/")
def root():
    return {
        "name": "Multi-Sport Betting & DFS Recommendation Agent",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "features": ["betting_recommendations", "dfs_optimization", "backtesting", "ml_models"],
        "disclaimer": "SIMULATION ONLY - For educational purposes. No real money wagering."
    }
