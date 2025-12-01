import os
from typing import List

SQLITE_URL = "sqlite:///./sports_betting.db"
DATABASE_URL = SQLITE_URL

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
