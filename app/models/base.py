from abc import ABC, abstractmethod
from typing import Any, Dict, List
import numpy as np


class BaseSportModel(ABC):
    sport: str
    
    @abstractmethod
    def fit(self, data: Any) -> None:
        pass
    
    @abstractmethod
    def predict_game_probabilities(
        self,
        games: List[Dict[str, Any]]
    ) -> List[Dict[str, float]]:
        pass
    
    def _sigmoid(self, x: float) -> float:
        return 1 / (1 + np.exp(-x))
    
    def _rating_to_probability(
        self, 
        rating1: float, 
        rating2: float, 
        home_advantage: float = 0.0,
        scale: float = 400.0
    ) -> float:
        diff = (rating1 - rating2 + home_advantage) / scale
        return self._sigmoid(diff * np.log(10))
    
    def _ensure_probabilities_sum(self, probs: Dict[str, float], keys: List[str]) -> Dict[str, float]:
        total = sum(probs.get(k, 0) for k in keys)
        if total > 0:
            for k in keys:
                if k in probs:
                    probs[k] = probs[k] / total
        return probs
