from typing import Any, Dict, List
from app.models.base import BaseSportModel
import numpy as np


class BoxingModel(BaseSportModel):
    sport = "BOXING"
    
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
            
            ko_rate1 = game.get("ko_rate1", 0.4)
            ko_rate2 = game.get("ko_rate2", 0.4)
            
            rating_boost = (ko_rate1 - ko_rate2) * 40
            
            draw_prob = 0.03
            
            base_fighter1_win = self._rating_to_probability(
                rating1 + rating_boost, rating2,
                home_advantage=0,
                scale=350.0
            )
            
            remaining_prob = 1 - draw_prob
            fighter1_win = base_fighter1_win * remaining_prob
            fighter2_win = (1 - base_fighter1_win) * remaining_prob
            
            results.append({
                "game_id": game.get("game_id"),
                "competitor1_win": round(fighter1_win, 4),
                "competitor2_win": round(fighter2_win, 4),
                "draw": round(draw_prob, 4)
            })
        
        return results
