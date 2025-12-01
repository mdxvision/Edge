from typing import Any, Dict, List
from app.models.base import BaseSportModel
import numpy as np


class CricketModel(BaseSportModel):
    sport = "CRICKET"
    
    def __init__(self):
        self.home_advantage = 0.08
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
            league = game.get("league", "T20")
            
            if "Test" in str(league):
                draw_prob = 0.30
            elif "ODI" in str(league):
                draw_prob = 0.02
            else:
                draw_prob = 0.01
            
            base_home_prob = self._rating_to_probability(
                home_rating, away_rating,
                home_advantage=self.home_advantage * 100,
                scale=300.0
            )
            
            remaining_prob = 1 - draw_prob
            home_win = base_home_prob * remaining_prob
            away_win = (1 - base_home_prob) * remaining_prob
            
            probs = {"home_win": home_win, "away_win": away_win, "draw": draw_prob}
            probs = self._ensure_probabilities_sum(probs, ["home_win", "away_win", "draw"])
            
            results.append({
                "game_id": game.get("game_id"),
                "home_win": round(probs["home_win"], 4),
                "away_win": round(probs["away_win"], 4),
                "draw": round(probs["draw"], 4)
            })
        
        return results
