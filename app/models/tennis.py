from typing import Any, Dict, List
from app.models.base import BaseSportModel
import numpy as np


class TennisModel(BaseSportModel):
    sport = "TENNIS"
    
    def __init__(self):
        self.is_fitted = False
    
    def fit(self, data: Any = None) -> None:
        self.is_fitted = True
    
    def predict_game_probabilities(
        self,
        games: List[Dict[str, Any]]
    ) -> List[Dict[str, float]]:
        results = []
        
        for game in games:
            rating1 = game.get("competitor1_rating", 1500.0)
            rating2 = game.get("competitor2_rating", 1500.0)
            
            surface = game.get("surface", "hard").lower()
            surface_boost = 0
            if surface == "clay":
                surface_boost = 20
            elif surface == "grass":
                surface_boost = 15
            
            competitor1_win = self._rating_to_probability(
                rating1 + surface_boost, rating2,
                home_advantage=0,
                scale=350.0
            )
            competitor2_win = 1 - competitor1_win
            
            results.append({
                "game_id": game.get("game_id"),
                "competitor1_win": round(competitor1_win, 4),
                "competitor2_win": round(competitor2_win, 4)
            })
        
        return results
