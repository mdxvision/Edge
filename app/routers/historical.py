from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.db import get_db, HistoricalGameResult, BacktestResult, Team, ELORatingHistory
from app.services.historical_data import seed_historical_data, get_team_form, get_head_to_head
from app.services.backtesting import run_full_backtest, get_backtest_summary, BacktestEngine
from app.models.advanced_elo import ADVANCED_MODEL_REGISTRY, fit_all_advanced_models

router = APIRouter(prefix="/historical", tags=["historical"])


@router.post("/seed")
def seed_data(
    seasons: int = Query(3, ge=1, le=5, description="Number of seasons to generate"),
    db: Session = Depends(get_db)
):
    try:
        stats = seed_historical_data(db, seasons=seasons)
        return {
            "message": "Historical data seeded successfully",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/train-models")
def train_models(db: Session = Depends(get_db)):
    try:
        results = fit_all_advanced_models(db)
        return {
            "message": "Models trained successfully",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/games")
def get_historical_games(
    sport: Optional[str] = None,
    season: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    query = db.query(HistoricalGameResult)
    
    if sport:
        query = query.filter(HistoricalGameResult.sport == sport)
    if season:
        query = query.filter(HistoricalGameResult.season == season)
    
    total = query.count()
    games = query.order_by(HistoricalGameResult.game_date.desc()).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "games": [
            {
                "id": g.id,
                "sport": g.sport,
                "season": g.season,
                "date": g.game_date.isoformat(),
                "home_team": g.home_team_name,
                "away_team": g.away_team_name,
                "home_score": g.home_score,
                "away_score": g.away_score,
                "winner": g.winner,
                "margin": g.margin,
                "total": g.total_points,
                "closing_spread": g.closing_spread,
                "closing_total": g.closing_total
            }
            for g in games
        ]
    }


@router.get("/games/stats")
def get_games_stats(db: Session = Depends(get_db)):
    from sqlalchemy import func
    
    stats = db.query(
        HistoricalGameResult.sport,
        HistoricalGameResult.season,
        func.count(HistoricalGameResult.id).label("count")
    ).group_by(
        HistoricalGameResult.sport,
        HistoricalGameResult.season
    ).all()
    
    result = {}
    for sport, season, count in stats:
        if sport not in result:
            result[sport] = {"total": 0, "seasons": {}}
        result[sport]["seasons"][season] = count
        result[sport]["total"] += count
    
    return result


@router.get("/ratings/{sport}")
def get_team_ratings(
    sport: str,
    db: Session = Depends(get_db)
):
    teams = db.query(Team).filter(Team.sport == sport).order_by(Team.rating.desc()).all()
    
    model = ADVANCED_MODEL_REGISTRY.get(sport)
    
    return {
        "sport": sport,
        "teams": [
            {
                "id": t.id,
                "name": t.name,
                "short_name": t.short_name,
                "rating": round(t.rating, 1),
                "model_rating": round(model.get_rating(t.id), 1) if model else None
            }
            for t in teams
        ]
    }


@router.get("/ratings/{sport}/history/{team_id}")
def get_rating_history(
    sport: str,
    team_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    history = db.query(ELORatingHistory).filter(
        ELORatingHistory.sport == sport,
        ELORatingHistory.entity_id == team_id
    ).order_by(ELORatingHistory.recorded_at.desc()).limit(limit).all()
    
    return {
        "team_id": team_id,
        "sport": sport,
        "history": [
            {
                "date": h.recorded_at.isoformat(),
                "rating": round(h.rating, 1),
                "change": round(h.rating_change, 1) if h.rating_change else None,
                "season": h.season
            }
            for h in history
        ]
    }


@router.get("/form/{sport}/{team_id}")
def get_form(
    sport: str,
    team_id: int,
    games: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db)
):
    form = get_team_form(db, team_id, sport, games)
    team = db.query(Team).filter(Team.id == team_id).first()
    
    return {
        "team_id": team_id,
        "team_name": team.name if team else "Unknown",
        "sport": sport,
        **form
    }


@router.get("/h2h/{sport}/{team1_id}/{team2_id}")
def get_h2h(
    sport: str,
    team1_id: int,
    team2_id: int,
    games: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    h2h = get_head_to_head(db, team1_id, team2_id, sport, games)
    
    team1 = db.query(Team).filter(Team.id == team1_id).first()
    team2 = db.query(Team).filter(Team.id == team2_id).first()
    
    return {
        "team1": {"id": team1_id, "name": team1.name if team1 else "Unknown"},
        "team2": {"id": team2_id, "name": team2.name if team2 else "Unknown"},
        "sport": sport,
        **h2h
    }


@router.post("/backtest/{sport}")
def run_backtest(
    sport: str,
    seasons: int = Query(2, ge=1, le=5),
    min_edge: float = Query(0.03, ge=0.0, le=0.2),
    db: Session = Depends(get_db)
):
    if sport not in ADVANCED_MODEL_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Sport {sport} not supported for backtesting")
    
    try:
        result = run_full_backtest(sport, seasons_back=seasons, min_edge=min_edge, db=db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backtest/results")
def get_backtest_results(
    sport: Optional[str] = None,
    db: Session = Depends(get_db)
):
    return get_backtest_summary(db, sport)


@router.get("/backtest/{backtest_id}")
def get_backtest_detail(
    backtest_id: int,
    db: Session = Depends(get_db)
):
    result = db.query(BacktestResult).filter(BacktestResult.id == backtest_id).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Backtest not found")
    
    return {
        "id": result.id,
        "sport": result.sport,
        "model": result.model_name,
        "version": result.model_version,
        "period": {
            "start": result.start_date.isoformat(),
            "end": result.end_date.isoformat()
        },
        "predictions": {
            "total": result.total_predictions,
            "correct": result.correct_predictions,
            "accuracy": round(result.accuracy * 100, 2)
        },
        "betting": {
            "bets": result.total_bets,
            "won": result.winning_bets,
            "roi": round(result.roi * 100, 2) if result.roi else None,
            "avg_edge": round(result.avg_edge * 100, 2) if result.avg_edge else None
        },
        "metrics": {
            "brier_score": round(result.brier_score, 4) if result.brier_score else None,
            "log_loss": round(result.log_loss, 4) if result.log_loss else None,
            "calibration_error": round(result.calibration_error, 4) if result.calibration_error else None,
            "sharpe_ratio": round(result.sharpe_ratio, 2) if result.sharpe_ratio else None,
            "max_drawdown": round(result.max_drawdown, 2) if result.max_drawdown else None
        },
        "parameters": result.parameters,
        "created": result.created_at.isoformat()
    }


@router.get("/model-status")
def get_model_status():
    status = {}
    for sport, model in ADVANCED_MODEL_REGISTRY.items():
        status[sport] = {
            "is_fitted": model.is_fitted,
            "teams_tracked": len(model.team_ratings),
            "k_factor": model.base_k_factor,
            "home_advantage": model.home_advantage,
            "last_update": model.last_update.isoformat() if model.last_update else None
        }
    return status
