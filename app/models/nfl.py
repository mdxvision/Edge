from typing import Any, Dict, List
from app.models.base import BaseSportModel
import numpy as np


class NFLModel(BaseSportModel):
    sport = "NFL"
    
    def __init__(self):
        self.home_advantage = 2.5
        self.avg_total = 45.0
        self.is_fitted = False
    
    def fit(self, data: Any = None) -> None:
        self.is_fitted = True
    
    def predict_game_probabilities(
        self,
        games: List[Dict[str, Any]]
    ) -> List[Dict[str, float]]:
        results = []
        
        for game in games:
            home_rating = game.get("home_rating", 1500.0)
            away_rating = game.get("away_rating", 1500.0)
            
            home_win_prob = self._rating_to_probability(
                home_rating, away_rating, 
                home_advantage=self.home_advantage * 10
            )
            away_win_prob = 1 - home_win_prob
            
            rating_diff = (home_rating - away_rating) / 100
            expected_margin = rating_diff * 3 + self.home_advantage
            
            total_factor = (home_rating + away_rating - 3000) / 200
            expected_total = self.avg_total + total_factor * 3
            
            results.append({
                "game_id": game.get("game_id"),
                "home_win": round(home_win_prob, 4),
                "away_win": round(away_win_prob, 4),
                "expected_margin": round(expected_margin, 1),
                "expected_total": round(expected_total, 1)
            })
        
        return results
