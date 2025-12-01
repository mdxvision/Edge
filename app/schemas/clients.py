from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from app.schemas.core import RiskProfileType


class ClientCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    bankroll: float = Field(default=1000.0, gt=0)
    risk_profile: RiskProfileType = "balanced"


class ClientUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    bankroll: Optional[float] = Field(None, gt=0)
    risk_profile: Optional[RiskProfileType] = None


class ClientRead(BaseModel):
    id: int
    name: str
    bankroll: float
    risk_profile: str
    created_at: datetime
    
    class Config:
        from_attributes = True
