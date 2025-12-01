from typing import List, Optional
from sqlalchemy.orm import Session
from app.db import Client, BetRecommendation, SessionLocal
from app.services.edge_engine import find_value_bets_for_sports
from app.services.bankroll import create_bet_recommendations
from app.config import SUPPORTED_SPORTS


def generate_recommendations_for_client(
    client_id: int,
    sports: Optional[List[str]] = None,
    min_edge: float = 0.03,
    db: Session = None
) -> List[BetRecommendation]:
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    
    try:
        client = db.query(Client).filter(Client.id == client_id).first()
        
        if client is None:
            raise ValueError(f"Client with id {client_id} not found")
        
        if sports is None:
            sports = SUPPORTED_SPORTS
        else:
            sports = [s for s in sports if s in SUPPORTED_SPORTS]
        
        bet_candidates = find_value_bets_for_sports(
            sports=sports,
            min_edge=min_edge,
            db=db
        )
        
        recommendations = create_bet_recommendations(client, bet_candidates)
        
        for rec in recommendations:
            db.add(rec)
        
        db.commit()
        
        for rec in recommendations:
            db.refresh(rec)
        
        return recommendations
        
    except Exception as e:
        if db:
            db.rollback()
        raise e
    finally:
        if close_db:
            db.close()


def get_latest_recommendations(
    client_id: int,
    limit: int = 20,
    db: Session = None
) -> List[BetRecommendation]:
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    
    try:
        recommendations = db.query(BetRecommendation).filter(
            BetRecommendation.client_id == client_id
        ).order_by(
            BetRecommendation.created_at.desc()
        ).limit(limit).all()
        
        return recommendations
        
    finally:
        if close_db:
            db.close()
