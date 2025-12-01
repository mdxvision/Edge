from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import numpy as np
import json

from app.db import (
    SessionLocal, HistoricalGameResult, BacktestResult, 
    ModelPrediction, Team
)
from app.models.advanced_elo import ADVANCED_MODEL_REGISTRY, AdvancedELOModel
from app.utils.odds import american_to_implied_probability


class BacktestEngine:
    
    def __init__(self, sport: str, model: Optional[AdvancedELOModel] = None):
        self.sport = sport
        self.model = model or ADVANCED_MODEL_REGISTRY.get(sport)
        
        if self.model is None:
            raise ValueError(f"No model available for sport: {sport}")
    
    def run_backtest(
        self,
        db: Session,
        start_date: datetime,
        end_date: datetime,
        min_edge: float = 0.03,
        stake_size: float = 100.0,
        model_name: str = "AdvancedELO"
    ) -> Dict[str, Any]:
        games = db.query(HistoricalGameResult).filter(
            HistoricalGameResult.sport == self.sport,
            HistoricalGameResult.game_date >= start_date,
            HistoricalGameResult.game_date <= end_date
        ).order_by(HistoricalGameResult.game_date.asc()).all()
        
        if not games:
            return {"error": "No games found in date range"}
        
        training_games = db.query(HistoricalGameResult).filter(
            HistoricalGameResult.sport == self.sport,
            HistoricalGameResult.game_date < start_date
        ).order_by(HistoricalGameResult.game_date.asc()).all()
        
        self.model.team_ratings = {}
        self.model.team_games_played = {}
        self.model.team_form = {}
        
        for game in training_games:
            self._process_game_for_training(game)
        
        predictions = []
        correct = 0
        total = 0
        
        bets_placed = 0
        bets_won = 0
        total_profit = 0.0
        
        home_probs = []
        actual_home_wins = []
        
        for game in games:
            if game.home_team_id is None or game.away_team_id is None:
                continue
            
            home_rating = self.model.get_rating(game.home_team_id)
            away_rating = self.model.get_rating(game.away_team_id)
            
            game_data = {
                "game_id": game.id,
                "home_team_id": game.home_team_id,
                "away_team_id": game.away_team_id,
                "home_rating": home_rating,
                "away_rating": away_rating
            }
            
            pred = self.model.predict_game_probabilities([game_data])[0]
            
            predicted_winner = "home" if pred["home_win"] > pred["away_win"] else "away"
            was_correct = predicted_winner == game.winner
            
            total += 1
            if was_correct:
                correct += 1
            
            home_probs.append(pred["home_win"])
            actual_home_wins.append(1 if game.winner == "home" else 0)
            
            home_edge = None
            away_edge = None
            bet_placed = False
            bet_selection = None
            bet_result = None
            profit_loss = 0.0
            
            if game.closing_home_ml and game.closing_away_ml:
                implied_home = american_to_implied_probability(game.closing_home_ml)
                implied_away = american_to_implied_probability(game.closing_away_ml)
                
                home_edge = pred["home_win"] - implied_home
                away_edge = pred["away_win"] - implied_away
                
                if home_edge >= min_edge:
                    bet_placed = True
                    bet_selection = "home"
                    bets_placed += 1
                    
                    if game.winner == "home":
                        bets_won += 1
                        if game.closing_home_ml > 0:
                            profit = stake_size * (game.closing_home_ml / 100)
                        else:
                            profit = stake_size * (100 / abs(game.closing_home_ml))
                        profit_loss = profit
                        bet_result = "win"
                    else:
                        profit_loss = -stake_size
                        bet_result = "loss"
                    
                    total_profit += profit_loss
                
                elif away_edge >= min_edge:
                    bet_placed = True
                    bet_selection = "away"
                    bets_placed += 1
                    
                    if game.winner == "away":
                        bets_won += 1
                        if game.closing_away_ml > 0:
                            profit = stake_size * (game.closing_away_ml / 100)
                        else:
                            profit = stake_size * (100 / abs(game.closing_away_ml))
                        profit_loss = profit
                        bet_result = "win"
                    else:
                        profit_loss = -stake_size
                        bet_result = "loss"
                    
                    total_profit += profit_loss
            
            prediction = ModelPrediction(
                game_result_id=game.id,
                sport=self.sport,
                model_name=model_name,
                home_win_prob=pred["home_win"],
                away_win_prob=pred["away_win"],
                predicted_winner=predicted_winner,
                predicted_margin=pred.get("expected_margin"),
                predicted_total=pred.get("expected_total"),
                actual_winner=game.winner,
                was_correct=was_correct,
                edge_on_home=home_edge,
                edge_on_away=away_edge,
                bet_placed=bet_placed,
                bet_selection=bet_selection,
                bet_odds=game.closing_home_ml if bet_selection == "home" else game.closing_away_ml,
                bet_result=bet_result,
                profit_loss=profit_loss if bet_placed else None
            )
            
            db.add(prediction)
            predictions.append(prediction)
            
            self._process_game_for_training(game)
        
        accuracy = correct / total if total > 0 else 0
        roi = (total_profit / (bets_placed * stake_size)) if bets_placed > 0 else 0
        
        brier_score = self._calculate_brier_score(home_probs, actual_home_wins)
        log_loss = self._calculate_log_loss(home_probs, actual_home_wins)
        calibration_error = self._calculate_calibration_error(home_probs, actual_home_wins)
        
        profit_history = []
        cumulative = 0.0
        for pred in predictions:
            if pred.bet_placed and pred.profit_loss is not None:
                cumulative += pred.profit_loss
                profit_history.append(cumulative)
        
        max_drawdown = self._calculate_max_drawdown(profit_history)
        sharpe = self._calculate_sharpe_ratio(profit_history, stake_size)
        
        result = BacktestResult(
            sport=self.sport,
            model_name=model_name,
            model_version="1.0",
            start_date=start_date,
            end_date=end_date,
            total_predictions=total,
            correct_predictions=correct,
            accuracy=accuracy,
            total_bets=bets_placed,
            winning_bets=bets_won,
            roi=roi,
            avg_edge=np.mean([p.edge_on_home or p.edge_on_away or 0 for p in predictions if p.bet_placed]) if bets_placed > 0 else None,
            brier_score=brier_score,
            log_loss=log_loss,
            calibration_error=calibration_error,
            sharpe_ratio=sharpe,
            max_drawdown=max_drawdown,
            parameters=json.dumps({
                "min_edge": min_edge,
                "stake_size": stake_size,
                "k_factor": self.model.base_k_factor,
                "home_advantage": self.model.home_advantage
            })
        )
        
        db.add(result)
        db.commit()
        
        return {
            "backtest_id": result.id,
            "sport": self.sport,
            "period": f"{start_date.date()} to {end_date.date()}",
            "total_games": total,
            "accuracy": round(accuracy * 100, 2),
            "bets_placed": bets_placed,
            "bets_won": bets_won,
            "win_rate": round(bets_won / bets_placed * 100, 2) if bets_placed > 0 else 0,
            "total_profit": round(total_profit, 2),
            "roi": round(roi * 100, 2),
            "brier_score": round(brier_score, 4),
            "log_loss": round(log_loss, 4) if log_loss else None,
            "calibration_error": round(calibration_error, 4),
            "sharpe_ratio": round(sharpe, 2) if sharpe else None,
            "max_drawdown": round(max_drawdown, 2) if max_drawdown else None
        }
    
    def _process_game_for_training(self, game: HistoricalGameResult):
        if game.home_team_id is None or game.away_team_id is None:
            return
        
        if game.home_team_id not in self.model.team_ratings:
            self.model.team_ratings[game.home_team_id] = 1500.0
        if game.away_team_id not in self.model.team_ratings:
            self.model.team_ratings[game.away_team_id] = 1500.0
        
        if game.winner == "home":
            self.model.update_rating(
                game.home_team_id,
                game.away_team_id,
                game.margin or 0,
                game.game_date
            )
        elif game.winner == "away":
            self.model.update_rating(
                game.away_team_id,
                game.home_team_id,
                -(game.margin or 0),
                game.game_date
            )
        else:
            self.model.update_rating(
                game.home_team_id,
                game.away_team_id,
                0,
                game.game_date,
                is_draw=True
            )
    
    def _calculate_brier_score(self, probs: List[float], actuals: List[int]) -> float:
        if not probs:
            return 0.0
        return np.mean([(p - a) ** 2 for p, a in zip(probs, actuals)])
    
    def _calculate_log_loss(self, probs: List[float], actuals: List[int]) -> Optional[float]:
        if not probs:
            return None
        eps = 1e-15
        clipped = [max(eps, min(1 - eps, p)) for p in probs]
        return -np.mean([
            a * np.log(p) + (1 - a) * np.log(1 - p)
            for p, a in zip(clipped, actuals)
        ])
    
    def _calculate_calibration_error(self, probs: List[float], actuals: List[int]) -> float:
        if not probs:
            return 0.0
        
        bins = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        errors = []
        
        for i in range(len(bins) - 1):
            bin_probs = [p for p in probs if bins[i] <= p < bins[i+1]]
            bin_actuals = [a for p, a in zip(probs, actuals) if bins[i] <= p < bins[i+1]]
            
            if bin_probs:
                predicted = np.mean(bin_probs)
                actual = np.mean(bin_actuals)
                errors.append(abs(predicted - actual))
        
        return np.mean(errors) if errors else 0.0
    
    def _calculate_max_drawdown(self, profit_history: List[float]) -> Optional[float]:
        if not profit_history:
            return None
        
        peak = profit_history[0]
        max_dd = 0.0
        
        for value in profit_history:
            if value > peak:
                peak = value
            drawdown = peak - value
            if drawdown > max_dd:
                max_dd = drawdown
        
        return max_dd
    
    def _calculate_sharpe_ratio(self, profit_history: List[float], stake: float) -> Optional[float]:
        if len(profit_history) < 2:
            return None
        
        returns = []
        for i in range(1, len(profit_history)):
            ret = (profit_history[i] - profit_history[i-1]) / stake
            returns.append(ret)
        
        if not returns:
            return None
        
        mean_ret = np.mean(returns)
        std_ret = np.std(returns)
        
        if std_ret == 0:
            return None
        
        return (mean_ret / std_ret) * np.sqrt(252)


def run_full_backtest(
    sport: str,
    seasons_back: int = 2,
    min_edge: float = 0.03,
    db: Session = None
) -> Dict[str, Any]:
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    
    try:
        engine = BacktestEngine(sport)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * seasons_back)
        
        training_end = start_date - timedelta(days=1)
        training_start = training_end - timedelta(days=365)
        
        training_games = db.query(HistoricalGameResult).filter(
            HistoricalGameResult.sport == sport,
            HistoricalGameResult.game_date >= training_start,
            HistoricalGameResult.game_date <= training_end
        ).count()
        
        result = engine.run_backtest(
            db=db,
            start_date=start_date,
            end_date=end_date,
            min_edge=min_edge
        )
        
        result["training_games"] = training_games
        return result
        
    finally:
        if close_db:
            db.close()


def get_backtest_summary(db: Session, sport: Optional[str] = None) -> List[Dict[str, Any]]:
    query = db.query(BacktestResult)
    
    if sport:
        query = query.filter(BacktestResult.sport == sport)
    
    results = query.order_by(BacktestResult.created_at.desc()).limit(20).all()
    
    return [
        {
            "id": r.id,
            "sport": r.sport,
            "model": r.model_name,
            "period": f"{r.start_date.date()} to {r.end_date.date()}",
            "accuracy": round(r.accuracy * 100, 2),
            "roi": round(r.roi * 100, 2) if r.roi else None,
            "bets": r.total_bets,
            "brier_score": round(r.brier_score, 4) if r.brier_score else None,
            "created": r.created_at.isoformat()
        }
        for r in results
    ]
