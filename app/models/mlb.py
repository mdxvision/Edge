from typing import Any, Dict, List
from app.models.base import BaseSportModel
import numpy as np


class MLBModel(BaseSportModel):
    sport = "MLB"
    
    def __init__(self):
        self.home_advantage = 0.04
        self.avg_total = 8.5
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
            
            base_prob = self._rating_to_probability(
                home_rating, away_rating,
                home_advantage=self.home_advantage * 100,
                scale=350.0
            )
            
            home_win_prob = base_prob
            away_win_prob = 1 - home_win_prob
            
            rating_diff = (home_rating - away_rating) / 100
            expected_margin = rating_diff * 0.8 + 0.3
            
            total_factor = (home_rating + away_rating - 3000) / 300
            expected_total = self.avg_total + total_factor * 1.5
            
            results.append({
                "game_id": game.get("game_id"),
                "home_win": round(home_win_prob, 4),
                "away_win": round(away_win_prob, 4),
                "expected_margin": round(expected_margin, 2),
                "expected_total": round(expected_total, 1)
            })
        
        return results
