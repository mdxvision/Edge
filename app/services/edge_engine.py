from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db import Game, Market, Line, Team, Competitor, SessionLocal
from app.models import SPORT_MODEL_REGISTRY
from app.utils.odds import american_to_implied_probability, expected_value, edge as calc_edge
from app.schemas.bets import BetCandidate
from app.config import TEAM_SPORTS, INDIVIDUAL_SPORTS, SUPPORTED_SPORTS


def get_upcoming_games(db: Session, sport: str, days_ahead: int = 30) -> List[Game]:
    now = datetime.now() - timedelta(days=365)
    end = now + timedelta(days=days_ahead + 365)
    
    return db.query(Game).filter(
        Game.sport == sport,
        Game.start_time >= now,
        Game.start_time <= end
    ).all()


def build_game_data(game: Game, db: Session) -> dict:
    data = {
        "game_id": game.id,
        "sport": game.sport,
        "league": game.league
    }
    
    if game.sport in TEAM_SPORTS:
        if game.home_team:
            data["home_rating"] = game.home_team.rating or 1500.0
            data["home_team_name"] = game.home_team.name
        else:
            data["home_rating"] = 1500.0
            data["home_team_name"] = "Unknown"
            
        if game.away_team:
            data["away_rating"] = game.away_team.rating or 1500.0
            data["away_team_name"] = game.away_team.name
        else:
            data["away_rating"] = 1500.0
            data["away_team_name"] = "Unknown"
    
    if game.sport in INDIVIDUAL_SPORTS:
        if game.competitor1:
            data["competitor1_rating"] = game.competitor1.rating or 1500.0
            data["competitor1_name"] = game.competitor1.name
        else:
            data["competitor1_rating"] = 1500.0
            data["competitor1_name"] = "Unknown"
            
        if game.competitor2:
            data["competitor2_rating"] = game.competitor2.rating or 1500.0
            data["competitor2_name"] = game.competitor2.name
        else:
            data["competitor2_rating"] = 1500.0
            data["competitor2_name"] = "Unknown"
    
    return data


def map_selection_to_probability(
    selection: str, 
    predictions: dict,
    sport: str
) -> Optional[float]:
    if selection == "home":
        return predictions.get("home_win")
    elif selection == "away":
        return predictions.get("away_win")
    elif selection == "draw":
        return predictions.get("draw")
    elif selection == "competitor1":
        return predictions.get("competitor1_win")
    elif selection == "competitor2":
        return predictions.get("competitor2_win")
    elif selection == "over":
        return 0.50
    elif selection == "under":
        return 0.50
    
    return None


def find_value_bets_for_sport(
    sport: str,
    min_edge: float = 0.03,
    db: Session = None
) -> List[BetCandidate]:
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    
    try:
        if sport not in SPORT_MODEL_REGISTRY:
            return []
        
        model = SPORT_MODEL_REGISTRY[sport]
        games = get_upcoming_games(db, sport)
        
        if not games:
            return []
        
        game_data_list = [build_game_data(g, db) for g in games]
        predictions_list = model.predict_game_probabilities(game_data_list)
        
        predictions_by_game = {p["game_id"]: p for p in predictions_list}
        
        value_bets = []
        
        for game, game_data in zip(games, game_data_list):
            predictions = predictions_by_game.get(game.id, {})
            
            for market in game.markets:
                for line in market.lines:
                    model_prob = map_selection_to_probability(
                        market.selection, 
                        predictions,
                        sport
                    )
                    
                    if model_prob is None:
                        continue
                    
                    implied_prob = american_to_implied_probability(line.american_odds)
                    edge_value = calc_edge(model_prob, implied_prob)
                    
                    if edge_value >= min_edge:
                        ev = expected_value(model_prob, line.american_odds, 1.0)
                        
                        candidate = BetCandidate(
                            game_id=game.id,
                            sport=sport,
                            market_id=market.id,
                            line_id=line.id,
                            selection=market.selection,
                            sportsbook=line.sportsbook,
                            american_odds=line.american_odds,
                            line_value=line.line_value,
                            model_probability=round(model_prob, 4),
                            implied_probability=round(implied_prob, 4),
                            edge=round(edge_value, 4),
                            expected_value=round(ev, 4),
                            home_team_name=game_data.get("home_team_name"),
                            away_team_name=game_data.get("away_team_name"),
                            competitor1_name=game_data.get("competitor1_name"),
                            competitor2_name=game_data.get("competitor2_name"),
                            start_time=game.start_time,
                            league=game.league,
                            market_type=market.market_type,
                            description=market.description
                        )
                        
                        value_bets.append(candidate)
        
        value_bets.sort(key=lambda x: x.edge, reverse=True)
        return value_bets
        
    finally:
        if close_db:
            db.close()


def find_value_bets_for_sports(
    sports: Optional[List[str]] = None,
    min_edge: float = 0.03,
    db: Session = None
) -> List[BetCandidate]:
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    
    try:
        if sports is None:
            sports = SUPPORTED_SPORTS
        
        all_candidates = []
        
        for sport in sports:
            candidates = find_value_bets_for_sport(sport, min_edge, db)
            all_candidates.extend(candidates)
        
        all_candidates.sort(key=lambda x: x.edge, reverse=True)
        return all_candidates
        
    finally:
        if close_db:
            db.close()
