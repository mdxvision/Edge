from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.db import get_db, DFSContest, DFSLineup, Client, Team
from app.services.dfs_projections import (
    PlayerProjectionEngine, 
    generate_sample_projections
)
from app.services.lineup_optimizer import (
    LineupOptimizer, 
    save_lineup_to_db, 
    get_client_lineups
)
from app.services.dfs_correlations import (
    analyze_lineup_correlations,
    get_optimal_stacks,
    seed_correlations_to_db
)


router = APIRouter(prefix="/dfs", tags=["dfs"])


class OptimizeRequest(BaseModel):
    sport: str
    platform: str = "DraftKings"
    lineup_type: str = "balanced"
    num_lineups: int = 1
    locked_players: Optional[List[int]] = None
    excluded_players: Optional[List[int]] = None


class AnalyzeLineupRequest(BaseModel):
    sport: str
    lineup: List[dict]


@router.get("/sports")
def get_dfs_sports():
    return {
        "sports": [
            {"id": "NFL", "name": "NFL Football", "platforms": ["DraftKings", "FanDuel"]},
            {"id": "NBA", "name": "NBA Basketball", "platforms": ["DraftKings", "FanDuel"]},
            {"id": "MLB", "name": "MLB Baseball", "platforms": ["DraftKings", "FanDuel"]},
            {"id": "NHL", "name": "NHL Hockey", "platforms": ["DraftKings", "FanDuel"]},
        ]
    }


@router.get("/projections/{sport}")
def get_projections(
    sport: str,
    platform: str = Query("DraftKings"),
    limit: int = Query(100, ge=10, le=500),
    db: Session = Depends(get_db)
):
    if sport not in ["NFL", "NBA", "MLB", "NHL"]:
        raise HTTPException(status_code=400, detail=f"Sport {sport} not supported for DFS")
    
    projections = generate_sample_projections(db, sport, platform, limit)
    
    return {
        "sport": sport,
        "platform": platform,
        "count": len(projections),
        "projections": projections
    }


@router.post("/optimize/{client_id}")
def optimize_lineup(
    client_id: int,
    request: OptimizeRequest,
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if request.sport not in ["NFL", "NBA", "MLB", "NHL"]:
        raise HTTPException(status_code=400, detail=f"Sport {request.sport} not supported")
    
    projections = generate_sample_projections(
        db, 
        request.sport, 
        request.platform, 
        num_players=150
    )
    
    optimizer = LineupOptimizer(request.sport, request.platform)
    
    if request.num_lineups == 1:
        result = optimizer.optimize_greedy(
            projections=projections,
            lineup_type=request.lineup_type,
            locked_players=request.locked_players or [],
            excluded_players=request.excluded_players or []
        )
        
        if result["success"]:
            db_lineup = save_lineup_to_db(
                db=db,
                client_id=client_id,
                lineup_result=result,
                sport=request.sport,
                platform=request.platform,
                slate_date=datetime.utcnow()
            )
            result["lineup_id"] = db_lineup.id
            
            correlation_analysis = analyze_lineup_correlations(
                result["lineup"],
                request.sport
            )
            result["correlation_analysis"] = correlation_analysis
        
        return result
    else:
        lineups = optimizer.generate_multiple_lineups(
            projections=projections,
            num_lineups=request.num_lineups,
            lineup_type=request.lineup_type
        )
        
        saved_ids = []
        for lineup_result in lineups:
            if lineup_result["success"]:
                db_lineup = save_lineup_to_db(
                    db=db,
                    client_id=client_id,
                    lineup_result=lineup_result,
                    sport=request.sport,
                    platform=request.platform,
                    slate_date=datetime.utcnow()
                )
                saved_ids.append(db_lineup.id)
        
        return {
            "success": True,
            "lineups_generated": len(lineups),
            "lineups_saved": len(saved_ids),
            "lineup_ids": saved_ids,
            "lineups": lineups
        }


@router.get("/lineups/{client_id}")
def get_lineups(
    client_id: int,
    sport: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    lineups = get_client_lineups(db, client_id, sport, limit)
    
    return {
        "client_id": client_id,
        "count": len(lineups),
        "lineups": lineups
    }


@router.get("/lineups/{client_id}/{lineup_id}")
def get_lineup_detail(
    client_id: int,
    lineup_id: int,
    db: Session = Depends(get_db)
):
    lineup = db.query(DFSLineup).filter(
        DFSLineup.id == lineup_id,
        DFSLineup.client_id == client_id
    ).first()
    
    if not lineup:
        raise HTTPException(status_code=404, detail="Lineup not found")
    
    import json
    player_ids = json.loads(lineup.player_ids) if lineup.player_ids else []
    positions = json.loads(lineup.positions) if lineup.positions else []
    notes = json.loads(lineup.optimization_notes) if lineup.optimization_notes else {}
    
    return {
        "id": lineup.id,
        "sport": lineup.sport,
        "platform": lineup.platform,
        "slate_date": lineup.slate_date.isoformat(),
        "lineup": {
            "player_ids": player_ids,
            "positions": positions,
            "player_names": notes.get("players", [])
        },
        "total_salary": lineup.total_salary,
        "salary_remaining": lineup.salary_remaining,
        "projected_points": lineup.projected_points,
        "projected_ownership": lineup.projected_ownership,
        "lineup_type": lineup.lineup_type,
        "actual_points": lineup.actual_points,
        "finish_position": lineup.finish_position,
        "winnings": lineup.winnings,
        "is_submitted": lineup.is_submitted,
        "created_at": lineup.created_at.isoformat()
    }


@router.delete("/lineups/{client_id}/{lineup_id}")
def delete_lineup(
    client_id: int,
    lineup_id: int,
    db: Session = Depends(get_db)
):
    lineup = db.query(DFSLineup).filter(
        DFSLineup.id == lineup_id,
        DFSLineup.client_id == client_id
    ).first()
    
    if not lineup:
        raise HTTPException(status_code=404, detail="Lineup not found")
    
    db.delete(lineup)
    db.commit()
    
    return {"message": "Lineup deleted successfully"}


@router.post("/analyze-correlation")
def analyze_correlation(request: AnalyzeLineupRequest):
    if request.sport not in ["NFL", "NBA", "MLB", "NHL"]:
        raise HTTPException(status_code=400, detail=f"Sport {request.sport} not supported")
    
    analysis = analyze_lineup_correlations(request.lineup, request.sport)
    
    return {
        "sport": request.sport,
        "analysis": analysis
    }


@router.get("/stacks/{sport}")
def get_stacks(sport: str):
    if sport not in ["NFL", "NBA", "MLB", "NHL"]:
        raise HTTPException(status_code=400, detail=f"Sport {sport} not supported")
    
    stacks = get_optimal_stacks(sport)
    
    return {
        "sport": sport,
        "stacks": stacks
    }


@router.get("/contests")
def get_contests(
    sport: Optional[str] = None,
    platform: str = "DraftKings",
    db: Session = Depends(get_db)
):
    query = db.query(DFSContest).filter(DFSContest.platform == platform)
    
    if sport:
        query = query.filter(DFSContest.sport == sport)
    
    contests = query.filter(
        DFSContest.is_active == True,
        DFSContest.lock_time > datetime.utcnow()
    ).order_by(DFSContest.start_time.asc()).limit(50).all()
    
    return {
        "platform": platform,
        "count": len(contests),
        "contests": [
            {
                "id": c.id,
                "sport": c.sport,
                "name": c.name,
                "contest_type": c.contest_type,
                "entry_fee": c.entry_fee,
                "prize_pool": c.prize_pool,
                "salary_cap": c.salary_cap,
                "roster_size": c.roster_size,
                "start_time": c.start_time.isoformat(),
                "lock_time": c.lock_time.isoformat(),
            }
            for c in contests
        ]
    }


@router.post("/seed-correlations")
def seed_correlations(db: Session = Depends(get_db)):
    count = seed_correlations_to_db(db)
    return {"message": f"Seeded {count} correlation records"}


@router.get("/value-plays/{sport}")
def get_value_plays(
    sport: str,
    platform: str = "DraftKings",
    limit: int = Query(10, ge=5, le=50),
    db: Session = Depends(get_db)
):
    projections = generate_sample_projections(db, sport, platform, 100)
    
    value_plays = sorted(
        projections, 
        key=lambda x: x["value_score"], 
        reverse=True
    )[:limit]
    
    return {
        "sport": sport,
        "platform": platform,
        "value_plays": value_plays
    }


@router.get("/leverage-plays/{sport}")
def get_leverage_plays(
    sport: str,
    platform: str = "DraftKings",
    limit: int = Query(10, ge=5, le=50),
    db: Session = Depends(get_db)
):
    projections = generate_sample_projections(db, sport, platform, 100)
    
    leverage_plays = sorted(
        projections,
        key=lambda x: x["leverage_score"],
        reverse=True
    )[:limit]
    
    return {
        "sport": sport,
        "platform": platform,
        "leverage_plays": leverage_plays
    }
