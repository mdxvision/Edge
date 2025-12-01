from typing import Any, Dict, List
from app.models.base import BaseSportModel
import numpy as np


class MMAModel(BaseSportModel):
    sport = "MMA"
    
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
            
            finish_rate1 = game.get("finish_rate1", 0.5)
            finish_rate2 = game.get("finish_rate2", 0.5)
            
            rating_boost = (finish_rate1 - finish_rate2) * 50
            
            fighter1_win = self._rating_to_probability(
                rating1 + rating_boost, rating2,
                home_advantage=0,
                scale=350.0
            )
            fighter2_win = 1 - fighter1_win
            
            results.append({
                "game_id": game.get("game_id"),
                "competitor1_win": round(fighter1_win, 4),
                "competitor2_win": round(fighter2_win, 4)
            })
        
        return results
