import os
from typing import List

SQLITE_URL = "sqlite:///./sports_betting.db"
POSTGRES_URL = os.environ.get("DATABASE_URL")

DATABASE_URL = POSTGRES_URL if POSTGRES_URL else SQLITE_URL

SESSION_SECRET = os.environ.get("SESSION_SECRET", "default-dev-secret-change-in-prod")
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
REFRESH_TOKEN_EXPIRE_DAYS = 7

DEFAULT_MIN_EDGE = 0.03

SUPPORTED_SPORTS: List[str] = [
    "NFL",
    "NBA", 
    "MLB",
    "NHL",
    "NCAA_FOOTBALL",
    "NCAA_BASKETBALL",
    "SOCCER",
    "CRICKET",
    "RUGBY",
    "TENNIS",
    "GOLF",
    "MMA",
    "BOXING",
    "MOTORSPORTS",
    "ESPORTS",
]

TEAM_SPORTS = ["NFL", "NBA", "MLB", "NHL", "NCAA_FOOTBALL", "NCAA_BASKETBALL", "SOCCER", "CRICKET", "RUGBY"]
INDIVIDUAL_SPORTS = ["TENNIS", "GOLF", "MMA", "BOXING", "MOTORSPORTS", "ESPORTS"]

RISK_PROFILES = ["conservative", "balanced", "aggressive"]
