from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.schemas.core import SportType


class GameBase(BaseModel):
    sport: SportType
    start_time: datetime
    venue: Optional[str] = None
    league: Optional[str] = None


class TeamGameCreate(GameBase):
    home_team_id: int
    away_team_id: int


class IndividualGameCreate(GameBase):
    competitor1_id: int
    competitor2_id: int


class GameRead(BaseModel):
    id: int
    sport: str
    home_team_id: Optional[int] = None
    away_team_id: Optional[int] = None
    home_team_name: Optional[str] = None
    away_team_name: Optional[str] = None
    competitor1_id: Optional[int] = None
    competitor2_id: Optional[int] = None
    competitor1_name: Optional[str] = None
    competitor2_name: Optional[str] = None
    start_time: datetime
    venue: Optional[str] = None
    league: Optional[str] = None
    
    class Config:
        from_attributes = True


class TeamRead(BaseModel):
    id: int
    sport: str
    name: str
    short_name: Optional[str] = None
    rating: float
    
    class Config:
        from_attributes = True


class CompetitorRead(BaseModel):
    id: int
    sport: str
    name: str
    country: Optional[str] = None
    rating: float
    
    class Config:
        from_attributes = True


class MarketRead(BaseModel):
    id: int
    game_id: int
    market_type: str
    description: Optional[str] = None
    selection: str
    
    class Config:
        from_attributes = True


class LineRead(BaseModel):
    id: int
    market_id: int
    sportsbook: str
    odds_type: str
    line_value: Optional[float] = None
    american_odds: int
    created_at: datetime
    
    class Config:
        from_attributes = True
