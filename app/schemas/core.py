from enum import Enum
from typing import Literal

class SportEnum(str, Enum):
    NFL = "NFL"
    NBA = "NBA"
    MLB = "MLB"
    NHL = "NHL"
    NCAA_FOOTBALL = "NCAA_FOOTBALL"
    NCAA_BASKETBALL = "NCAA_BASKETBALL"
    SOCCER = "SOCCER"
    CRICKET = "CRICKET"
    RUGBY = "RUGBY"
    TENNIS = "TENNIS"
    GOLF = "GOLF"
    MMA = "MMA"
    BOXING = "BOXING"
    MOTORSPORTS = "MOTORSPORTS"
    ESPORTS = "ESPORTS"


class RiskProfileEnum(str, Enum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


SportType = Literal[
    "NFL", "NBA", "MLB", "NHL", 
    "NCAA_FOOTBALL", "NCAA_BASKETBALL",
    "SOCCER", "CRICKET", "RUGBY", 
    "TENNIS", "GOLF", 
    "MMA", "BOXING", 
    "MOTORSPORTS", "ESPORTS"
]

RiskProfileType = Literal["conservative", "balanced", "aggressive"]
