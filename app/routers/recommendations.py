from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db import get_db, Client, BetRecommendation, Line, Market, Game
from app.schemas.bets import RecommendationRequest, BetRecommendationRead, RecommendationResponse
from app.services.agent import generate_recommendations_for_client, get_latest_recommendations
from app.config import SUPPORTED_SPORTS, TEAM_SPORTS

router = APIRouter(prefix="/clients/{client_id}/recommendations", tags=["Recommendations"])


def format_game_info(rec: BetRecommendation, db: Session) -> str:
    line = db.query(Line).filter(Line.id == rec.line_id).first()
    if not line:
        return "Unknown game"
    
    market = db.query(Market).filter(Market.id == line.market_id).first()
    if not market:
        return "Unknown game"
    
    game = db.query(Game).filter(Game.id == market.game_id).first()
    if not game:
        return "Unknown game"
    
    if game.sport in TEAM_SPORTS:
        home_name = game.home_team.name if game.home_team else "Unknown"
        away_name = game.away_team.name if game.away_team else "Unknown"
        return f"{home_name} vs {away_name}"
    else:
        comp1_name = game.competitor1.name if game.competitor1 else "Unknown"
        comp2_name = game.competitor2.name if game.competitor2 else "Unknown"
        return f"{comp1_name} vs {comp2_name}"


def get_market_info(rec: BetRecommendation, db: Session) -> tuple:
    line = db.query(Line).filter(Line.id == rec.line_id).first()
    if not line:
        return "moneyline", "unknown", "Unknown", None, -110
    
    market = db.query(Market).filter(Market.id == line.market_id).first()
    if not market:
        return "moneyline", "unknown", "Unknown", None, line.american_odds if line else -110
    
    return market.market_type, market.selection, line.sportsbook, line.line_value, line.american_odds


@router.post("/run", response_model=RecommendationResponse)
def run_recommendations(
    client_id: int,
    request: RecommendationRequest,
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == client_id).first()
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    
    sports = request.sports
    if sports:
        invalid_sports = [s for s in sports if s not in SUPPORTED_SPORTS]
        if invalid_sports:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid sports: {invalid_sports}. Supported: {SUPPORTED_SPORTS}"
            )
    
    try:
        recommendations = generate_recommendations_for_client(
            client_id=client_id,
            sports=sports,
            min_edge=request.min_edge,
            db=db
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    rec_reads = []
    total_stake = 0.0
    
    for rec in recommendations:
        market_type, selection, sportsbook, line_value, american_odds = get_market_info(rec, db)
        game_info = format_game_info(rec, db)
        
        rec_read = BetRecommendationRead(
            id=rec.id,
            client_id=rec.client_id,
            sport=rec.sport,
            game_info=game_info,
            market_type=market_type,
            selection=selection,
            sportsbook=sportsbook,
            american_odds=american_odds,
            line_value=line_value,
            model_probability=rec.model_probability,
            implied_probability=rec.implied_probability,
            edge=rec.edge,
            expected_value=rec.expected_value,
            suggested_stake=rec.suggested_stake,
            explanation=rec.explanation,
            created_at=rec.created_at
        )
        rec_reads.append(rec_read)
        total_stake += rec.suggested_stake
    
    return RecommendationResponse(
        client_id=client_id,
        client_name=client.name,
        recommendations=rec_reads,
        total_recommended_stake=round(total_stake, 2)
    )


@router.get("/latest", response_model=List[BetRecommendationRead])
def get_latest(
    client_id: int,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == client_id).first()
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    
    recommendations = get_latest_recommendations(client_id, limit, db)
    
    rec_reads = []
    for rec in recommendations:
        market_type, selection, sportsbook, line_value, american_odds = get_market_info(rec, db)
        game_info = format_game_info(rec, db)
        
        rec_read = BetRecommendationRead(
            id=rec.id,
            client_id=rec.client_id,
            sport=rec.sport,
            game_info=game_info,
            market_type=market_type,
            selection=selection,
            sportsbook=sportsbook,
            american_odds=american_odds,
            line_value=line_value,
            model_probability=rec.model_probability,
            implied_probability=rec.implied_probability,
            edge=rec.edge,
            expected_value=rec.expected_value,
            suggested_stake=rec.suggested_stake,
            explanation=rec.explanation,
            created_at=rec.created_at
        )
        rec_reads.append(rec_read)
    
    return rec_reads
