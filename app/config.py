import os
from typing import List

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sports_betting.db")

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
