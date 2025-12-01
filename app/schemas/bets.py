from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from app.schemas.core import SportType


class BetCandidate(BaseModel):
    game_id: int
    sport: str
    market_id: int
    line_id: int
    selection: str
    sportsbook: str
    american_odds: int
    line_value: Optional[float] = None
    model_probability: float
    implied_probability: float
    edge: float
    expected_value: float
    
    home_team_name: Optional[str] = None
    away_team_name: Optional[str] = None
    competitor1_name: Optional[str] = None
    competitor2_name: Optional[str] = None
    start_time: Optional[datetime] = None
    league: Optional[str] = None
    market_type: Optional[str] = None
    description: Optional[str] = None


class BetRecommendationRead(BaseModel):
    id: int
    client_id: int
    sport: str
    game_info: str
    market_type: str
    selection: str
    sportsbook: str
    american_odds: int
    line_value: Optional[float] = None
    model_probability: float
    implied_probability: float
    edge: float
    expected_value: float
    suggested_stake: float
    explanation: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class RecommendationRequest(BaseModel):
    sports: Optional[List[str]] = None
    min_edge: float = 0.03


class RecommendationResponse(BaseModel):
    client_id: int
    client_name: str
    recommendations: List[BetRecommendationRead]
    total_recommended_stake: float
    disclaimer: str = "SIMULATION ONLY: This is for educational purposes. Models are simplistic and do not guarantee profits. No real money should be wagered based on these recommendations."
