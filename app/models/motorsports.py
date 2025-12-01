from typing import Any, Dict, List
from app.models.base import BaseSportModel
import numpy as np


class MotorsportsModel(BaseSportModel):
    sport = "MOTORSPORTS"
    
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
            
            team_rating1 = game.get("team_rating1", 1500.0)
            team_rating2 = game.get("team_rating2", 1500.0)
            
            combined_rating1 = rating1 * 0.6 + team_rating1 * 0.4
            combined_rating2 = rating2 * 0.6 + team_rating2 * 0.4
            
            driver1_win = self._rating_to_probability(
                combined_rating1, combined_rating2,
                home_advantage=0,
                scale=400.0
            )
            driver2_win = 1 - driver1_win
            
            results.append({
                "game_id": game.get("game_id"),
                "competitor1_win": round(driver1_win, 4),
                "competitor2_win": round(driver2_win, 4)
            })
        
        return results
