from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import numpy as np
import math

from app.models.base import BaseSportModel
from app.db import SessionLocal, Team, HistoricalGameResult, ELORatingHistory


class AdvancedELOModel(BaseSportModel):
    
    def __init__(
        self,
        sport: str,
        base_k_factor: float = 32.0,
        home_advantage: float = 50.0,
        recency_weight: float = 0.95,
        margin_factor: float = 1.0,
        avg_total: float = 100.0
    ):
        self.sport = sport
        self.base_k_factor = base_k_factor
        self.home_advantage = home_advantage
        self.recency_weight = recency_weight
        self.margin_factor = margin_factor
        self.avg_total = avg_total
        self.is_fitted = False
        
        self.team_ratings: Dict[int, float] = {}
        self.team_games_played: Dict[int, int] = {}
        self.team_form: Dict[int, List[str]] = {}
        self.last_update: Optional[datetime] = None
    
    def _get_k_factor(self, games_played: int) -> float:
        if games_played < 10:
            return self.base_k_factor * 1.5
        elif games_played < 30:
            return self.base_k_factor
        else:
            return self.base_k_factor * 0.8
    
    def _margin_multiplier(self, margin: float) -> float:
        if self.sport == "NFL":
            return min(2.0, 1.0 + abs(margin) / 14 * self.margin_factor)
        elif self.sport == "NBA":
            return min(2.0, 1.0 + abs(margin) / 12 * self.margin_factor)
        elif self.sport == "MLB":
            return min(1.5, 1.0 + abs(margin) / 5 * self.margin_factor)
        elif self.sport == "NHL":
            return min(1.5, 1.0 + abs(margin) / 3 * self.margin_factor)
        else:
            return 1.0 + abs(margin) / 10 * self.margin_factor
    
    def _recency_decay(self, days_ago: int) -> float:
        return self.recency_weight ** (days_ago / 30)
    
    def update_rating(
        self,
        winner_id: int,
        loser_id: int,
        margin: float,
        game_date: datetime,
        is_draw: bool = False
    ) -> tuple:
        winner_rating = self.team_ratings.get(winner_id, 1500.0)
        loser_rating = self.team_ratings.get(loser_id, 1500.0)
        
        winner_games = self.team_games_played.get(winner_id, 0)
        loser_games = self.team_games_played.get(loser_id, 0)
        
        expected_winner = 1 / (1 + 10 ** ((loser_rating - winner_rating) / 400))
        expected_loser = 1 - expected_winner
        
        k_winner = self._get_k_factor(winner_games)
        k_loser = self._get_k_factor(loser_games)
        
        margin_mult = self._margin_multiplier(margin)
        
        if is_draw:
            actual_winner = 0.5
            actual_loser = 0.5
        else:
            actual_winner = 1.0
            actual_loser = 0.0
        
        change_winner = k_winner * margin_mult * (actual_winner - expected_winner)
        change_loser = k_loser * margin_mult * (actual_loser - expected_loser)
        
        self.team_ratings[winner_id] = winner_rating + change_winner
        self.team_ratings[loser_id] = loser_rating + change_loser
        
        self.team_games_played[winner_id] = winner_games + 1
        self.team_games_played[loser_id] = loser_games + 1
        
        if winner_id not in self.team_form:
            self.team_form[winner_id] = []
        if loser_id not in self.team_form:
            self.team_form[loser_id] = []
        
        if is_draw:
            self.team_form[winner_id].append("D")
            self.team_form[loser_id].append("D")
        else:
            self.team_form[winner_id].append("W")
            self.team_form[loser_id].append("L")
        
        self.team_form[winner_id] = self.team_form[winner_id][-10:]
        self.team_form[loser_id] = self.team_form[loser_id][-10:]
        
        self.last_update = game_date
        
        return change_winner, change_loser
    
    def get_form_factor(self, team_id: int, num_games: int = 5) -> float:
        form = self.team_form.get(team_id, [])
        if not form:
            return 1.0
        
        recent = form[-num_games:]
        wins = sum(1 for r in recent if r == "W")
        draws = sum(1 for r in recent if r == "D")
        
        form_score = (wins + draws * 0.5) / len(recent)
        return 0.9 + form_score * 0.2
    
    def fit(self, data: Any = None, db: Session = None) -> None:
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True
        
        try:
            games = db.query(HistoricalGameResult).filter(
                HistoricalGameResult.sport == self.sport
            ).order_by(HistoricalGameResult.game_date.asc()).all()
            
            self.team_ratings = {}
            self.team_games_played = {}
            self.team_form = {}
            
            for game in games:
                if game.home_team_id is None or game.away_team_id is None:
                    continue
                
                if game.home_team_id not in self.team_ratings:
                    self.team_ratings[game.home_team_id] = 1500.0
                if game.away_team_id not in self.team_ratings:
                    self.team_ratings[game.away_team_id] = 1500.0
                
                if game.winner == "home":
                    self.update_rating(
                        game.home_team_id,
                        game.away_team_id,
                        game.margin or 0,
                        game.game_date
                    )
                elif game.winner == "away":
                    self.update_rating(
                        game.away_team_id,
                        game.home_team_id,
                        -(game.margin or 0),
                        game.game_date
                    )
                else:
                    self.update_rating(
                        game.home_team_id,
                        game.away_team_id,
                        0,
                        game.game_date,
                        is_draw=True
                    )
            
            for team_id, rating in self.team_ratings.items():
                team = db.query(Team).filter(Team.id == team_id).first()
                if team:
                    team.rating = rating
            
            db.commit()
            self.is_fitted = True
            
        finally:
            if close_db:
                db.close()
    
    def predict_game_probabilities(
        self,
        games: List[Dict[str, Any]]
    ) -> List[Dict[str, float]]:
        results = []
        
        for game in games:
            home_rating = game.get("home_rating", 1500.0)
            away_rating = game.get("away_rating", 1500.0)
            
            home_id = game.get("home_team_id")
            away_id = game.get("away_team_id")
            
            if home_id and home_id in self.team_ratings:
                home_rating = self.team_ratings[home_id]
            if away_id and away_id in self.team_ratings:
                away_rating = self.team_ratings[away_id]
            
            home_form = self.get_form_factor(home_id) if home_id else 1.0
            away_form = self.get_form_factor(away_id) if away_id else 1.0
            
            adjusted_home = home_rating * home_form
            adjusted_away = away_rating * away_form
            
            home_win_prob = self._rating_to_probability(
                adjusted_home,
                adjusted_away,
                home_advantage=self.home_advantage
            )
            away_win_prob = 1 - home_win_prob
            
            rating_diff = (adjusted_home - adjusted_away + self.home_advantage) / 100
            
            if self.sport == "NFL":
                expected_margin = rating_diff * 3
            elif self.sport == "NBA":
                expected_margin = rating_diff * 2.5
            elif self.sport == "MLB":
                expected_margin = rating_diff * 0.5
            elif self.sport == "NHL":
                expected_margin = rating_diff * 0.3
            else:
                expected_margin = rating_diff
            
            total_rating = (home_rating + away_rating) / 2
            total_adjustment = (total_rating - 1500) / 200
            expected_total = self.avg_total + total_adjustment * 5
            
            results.append({
                "game_id": game.get("game_id"),
                "home_win": round(home_win_prob, 4),
                "away_win": round(away_win_prob, 4),
                "expected_margin": round(expected_margin, 1),
                "expected_total": round(expected_total, 1),
                "home_rating": round(home_rating, 1),
                "away_rating": round(away_rating, 1),
                "home_form": home_form,
                "away_form": away_form
            })
        
        return results
    
    def get_rating(self, team_id: int) -> float:
        return self.team_ratings.get(team_id, 1500.0)
    
    def get_all_ratings(self) -> Dict[int, float]:
        return self.team_ratings.copy()


class NFLAdvancedModel(AdvancedELOModel):
    def __init__(self):
        super().__init__(
            sport="NFL",
            base_k_factor=32.0,
            home_advantage=48.0,
            recency_weight=0.92,
            margin_factor=1.0,
            avg_total=45.0
        )


class NBAAdvancedModel(AdvancedELOModel):
    def __init__(self):
        super().__init__(
            sport="NBA",
            base_k_factor=28.0,
            home_advantage=35.0,
            recency_weight=0.96,
            margin_factor=0.8,
            avg_total=225.0
        )


class MLBAdvancedModel(AdvancedELOModel):
    def __init__(self):
        super().__init__(
            sport="MLB",
            base_k_factor=12.0,
            home_advantage=25.0,
            recency_weight=0.98,
            margin_factor=0.5,
            avg_total=8.5
        )


class NHLAdvancedModel(AdvancedELOModel):
    def __init__(self):
        super().__init__(
            sport="NHL",
            base_k_factor=20.0,
            home_advantage=30.0,
            recency_weight=0.95,
            margin_factor=0.6,
            avg_total=5.5
        )


ADVANCED_MODEL_REGISTRY = {
    "NFL": NFLAdvancedModel(),
    "NBA": NBAAdvancedModel(),
    "MLB": MLBAdvancedModel(),
    "NHL": NHLAdvancedModel(),
}


def fit_all_advanced_models(db: Session = None) -> Dict[str, bool]:
    results = {}
    for sport, model in ADVANCED_MODEL_REGISTRY.items():
        try:
            model.fit(db=db)
            results[sport] = True
        except Exception as e:
            print(f"Error fitting {sport} model: {e}")
            results[sport] = False
    return results
