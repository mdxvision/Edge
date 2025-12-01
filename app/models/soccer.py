from typing import Any, Dict, List
from app.models.base import BaseSportModel
import numpy as np


class SoccerModel(BaseSportModel):
    sport = "SOCCER"
    
    def __init__(self):
        self.home_advantage = 0.10
        self.base_draw_prob = 0.25
        self.avg_total = 2.5
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
            
            rating_diff = home_rating - away_rating
            
            draw_adjustment = max(0, 0.05 - abs(rating_diff) / 2000)
            draw_prob = self.base_draw_prob + draw_adjustment
            
            base_home_prob = self._rating_to_probability(
                home_rating, away_rating,
                home_advantage=self.home_advantage * 100,
                scale=350.0
            )
            
            remaining_prob = 1 - draw_prob
            home_win = base_home_prob * remaining_prob
            away_win = (1 - base_home_prob) * remaining_prob
            
            probs = {"home_win": home_win, "away_win": away_win, "draw": draw_prob}
            probs = self._ensure_probabilities_sum(probs, ["home_win", "away_win", "draw"])
            
            total_factor = (home_rating + away_rating - 3000) / 500
            expected_total = self.avg_total + total_factor * 0.5
            
            results.append({
                "game_id": game.get("game_id"),
                "home_win": round(probs["home_win"], 4),
                "away_win": round(probs["away_win"], 4),
                "draw": round(probs["draw"], 4),
                "expected_total": round(expected_total, 2)
            })
        
        return results
