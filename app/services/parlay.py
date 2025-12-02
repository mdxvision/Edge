from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import json
from sqlalchemy.orm import Session

from app.db import Parlay, BetRecommendation, Line, Game
from app.utils.odds import american_to_probability, american_to_decimal


def calculate_parlay_odds(legs: List[Dict[str, Any]]) -> Tuple[int, float]:
    combined_decimal = 1.0
    combined_prob = 1.0
    
    for leg in legs:
        odds = leg.get("odds", leg.get("american_odds", -110))
        prob = leg.get("probability", american_to_probability(odds))
        decimal_odds = american_to_decimal(odds)
        
        combined_decimal *= decimal_odds
        combined_prob *= prob
    
    if combined_decimal >= 2.0:
        american_odds = int((combined_decimal - 1) * 100)
    else:
        american_odds = int(-100 / (combined_decimal - 1))
    
    return american_odds, combined_prob


def calculate_correlation_adjustment(
    legs: List[Dict[str, Any]],
    db: Session
) -> float:
    if len(legs) < 2:
        return 1.0
    
    adjustment = 1.0
    
    games_in_parlay = {}
    for leg in legs:
        game_id = leg.get("game_id")
        if game_id:
            if game_id not in games_in_parlay:
                games_in_parlay[game_id] = []
            games_in_parlay[game_id].append(leg)
    
    for game_id, game_legs in games_in_parlay.items():
        if len(game_legs) > 1:
            selections = [l.get("selection", "") for l in game_legs]
            
            has_ml = any("moneyline" in s.lower() or "ml" in s.lower() for s in selections)
            has_total = any("over" in s.lower() or "under" in s.lower() for s in selections)
            has_spread = any("spread" in s.lower() or "+" in s or "-" in s for s in selections)
            
            if has_ml and has_spread:
                adjustment *= 0.85
            elif has_ml and has_total:
                adjustment *= 0.95
            elif has_spread and has_total:
                adjustment *= 0.90
    
    sports = list(set(leg.get("sport", "unknown") for leg in legs))
    if len(sports) == 1:
        adjustment *= 0.98
    
    if len(legs) > 4:
        adjustment *= (0.97 ** (len(legs) - 4))
    
    return max(0.5, min(1.0, adjustment))


def create_parlay(
    db: Session,
    user_id: int,
    leg_data: List[Dict[str, Any]],
    name: Optional[str] = None,
    stake: Optional[float] = None,
    bankroll: Optional[float] = None
) -> Parlay:
    combined_odds, combined_prob = calculate_parlay_odds(leg_data)
    correlation_adj = calculate_correlation_adjustment(leg_data, db)
    adjusted_prob = combined_prob * correlation_adj
    
    implied_prob = american_to_probability(combined_odds)
    edge = adjusted_prob - implied_prob
    
    suggested_stake = None
    if bankroll and edge > 0:
        kelly = edge / (american_to_decimal(combined_odds) - 1)
        suggested_stake = min(bankroll * kelly * 0.25, bankroll * 0.05)
    
    potential_profit = None
    if stake:
        decimal_odds = american_to_decimal(combined_odds)
        potential_profit = stake * (decimal_odds - 1)
    elif suggested_stake:
        decimal_odds = american_to_decimal(combined_odds)
        potential_profit = suggested_stake * (decimal_odds - 1)
    
    leg_ids = [str(leg.get("recommendation_id") or leg.get("id", i)) for i, leg in enumerate(leg_data)]
    
    parlay = Parlay(
        user_id=user_id,
        name=name,
        leg_ids=json.dumps(leg_ids),
        leg_count=len(leg_data),
        combined_odds=combined_odds,
        combined_probability=combined_prob,
        correlation_adjustment=correlation_adj,
        adjusted_probability=adjusted_prob,
        suggested_stake=suggested_stake,
        potential_profit=potential_profit,
        edge=edge
    )
    
    db.add(parlay)
    db.commit()
    db.refresh(parlay)
    
    return parlay


def analyze_parlay(
    legs: List[Dict[str, Any]],
    db: Session
) -> Dict[str, Any]:
    combined_odds, combined_prob = calculate_parlay_odds(legs)
    correlation_adj = calculate_correlation_adjustment(legs, db)
    adjusted_prob = combined_prob * correlation_adj
    
    implied_prob = american_to_probability(combined_odds)
    edge = adjusted_prob - implied_prob
    
    individual_evs = []
    for leg in legs:
        odds = leg.get("odds", leg.get("american_odds", -110))
        prob = leg.get("probability", american_to_probability(odds))
        implied = american_to_probability(odds)
        ev = (prob * american_to_decimal(odds)) - 1
        individual_evs.append({
            "selection": leg.get("selection", "Unknown"),
            "odds": odds,
            "probability": round(prob * 100, 2),
            "implied_probability": round(implied * 100, 2),
            "edge": round((prob - implied) * 100, 2),
            "ev": round(ev * 100, 2)
        })
    
    decimal_odds = american_to_decimal(combined_odds)
    ev_per_dollar = (adjusted_prob * decimal_odds) - 1
    
    return {
        "leg_count": len(legs),
        "combined_odds": combined_odds,
        "combined_probability": round(combined_prob * 100, 2),
        "correlation_adjustment": round(correlation_adj, 4),
        "adjusted_probability": round(adjusted_prob * 100, 2),
        "implied_probability": round(implied_prob * 100, 2),
        "edge": round(edge * 100, 2),
        "ev_per_dollar": round(ev_per_dollar * 100, 2),
        "is_positive_ev": edge > 0,
        "legs": individual_evs,
        "risk_assessment": get_risk_assessment(len(legs), adjusted_prob, edge)
    }


def get_risk_assessment(leg_count: int, prob: float, edge: float) -> Dict[str, Any]:
    if leg_count <= 2 and edge > 0.05:
        risk_level = "low"
        recommendation = "Good parlay with positive edge"
    elif leg_count <= 3 and edge > 0.02:
        risk_level = "medium"
        recommendation = "Moderate risk, small positive edge"
    elif leg_count <= 4 and edge > 0:
        risk_level = "high"
        recommendation = "High variance, marginally positive"
    else:
        risk_level = "very_high"
        recommendation = "Not recommended - high variance and/or negative edge"
    
    return {
        "risk_level": risk_level,
        "recommendation": recommendation,
        "win_probability": round(prob * 100, 2),
        "suggested_max_stake_percent": {
            "low": 5.0,
            "medium": 3.0,
            "high": 1.5,
            "very_high": 0.5
        }.get(risk_level, 1.0)
    }


def get_user_parlays(
    db: Session,
    user_id: int,
    status: Optional[str] = None,
    limit: int = 50
) -> List[Parlay]:
    query = db.query(Parlay).filter(Parlay.user_id == user_id)
    
    if status:
        query = query.filter(Parlay.status == status)
    
    return query.order_by(Parlay.created_at.desc()).limit(limit).all()


def settle_parlay(
    db: Session,
    parlay: Parlay,
    result: str,
    profit_loss: Optional[float] = None
) -> Parlay:
    parlay.status = "settled"
    parlay.result = result
    parlay.settled_at = datetime.utcnow()
    
    if profit_loss is not None:
        parlay.profit_loss = profit_loss
    elif result == "won" and parlay.potential_profit:
        parlay.profit_loss = parlay.potential_profit
    elif result == "lost" and parlay.suggested_stake:
        parlay.profit_loss = -parlay.suggested_stake
    
    db.commit()
    db.refresh(parlay)
    
    return parlay


def build_parlay_from_recommendations(
    db: Session,
    recommendation_ids: List[int],
    user_id: int,
    name: Optional[str] = None
) -> Dict[str, Any]:
    recommendations = db.query(BetRecommendation).filter(
        BetRecommendation.id.in_(recommendation_ids)
    ).all()
    
    if len(recommendations) != len(recommendation_ids):
        return {"error": "Some recommendations not found"}
    
    legs = []
    for rec in recommendations:
        line = rec.line
        game = line.market.game if line.market else None
        
        legs.append({
            "recommendation_id": rec.id,
            "game_id": game.id if game else None,
            "sport": rec.sport,
            "selection": f"{line.market.selection} - {line.market.market_type}" if line.market else "Unknown",
            "odds": line.american_odds,
            "probability": rec.model_probability
        })
    
    analysis = analyze_parlay(legs, db)
    
    return {
        "legs": legs,
        "analysis": analysis
    }
