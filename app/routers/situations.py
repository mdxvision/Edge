"""
Situational Factors API Router

Provides endpoints for rest, travel, motivation, and schedule spot analysis.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from app.db import get_db
from app.services import situations, schedule_spots

router = APIRouter(prefix="/situations", tags=["situations"])


class SituationAnalysisRequest(BaseModel):
    home_team: str
    away_team: str
    sport: str = "NBA"
    game_date: Optional[str] = None
    game_time: Optional[str] = None
    # Rest parameters
    home_days_rest: int = 2
    away_days_rest: int = 2
    home_back_to_back: bool = False
    away_back_to_back: bool = False
    # Travel parameters
    away_origin: Optional[str] = None
    # Motivation parameters
    is_revenge: bool = False
    revenge_team: Optional[str] = None
    revenge_reason: Optional[str] = None
    is_lookahead: bool = False
    lookahead_team: Optional[str] = None
    lookahead_opponent: Optional[str] = None
    is_letdown: bool = False
    letdown_team: Optional[str] = None
    letdown_reason: Optional[str] = None
    is_elimination: bool = False
    nothing_to_play_for: Optional[str] = None


@router.get("/game/{game_id}")
def get_game_situation(
    game_id: int,
    db: Session = Depends(get_db)
):
    """
    Get full situation analysis for a game.

    Returns rest, travel, motivation, and combined edge analysis.
    """
    # Try to load from database first
    from app.db import GameSituation, Game

    # Get game details
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Check for existing situation analysis
    existing = db.query(GameSituation).filter(
        GameSituation.game_id == game_id
    ).first()

    if existing:
        return {
            "game_id": game_id,
            "matchup": f"{existing.away_team} @ {existing.home_team}",
            "sport": existing.sport,
            "date": existing.game_date.isoformat() if existing.game_date else None,
            "rest": {
                "home_rest": existing.home_days_rest,
                "away_rest": existing.away_days_rest,
                "advantage": f"HOME +{existing.rest_advantage}" if existing.rest_advantage and existing.rest_advantage > 0
                             else f"AWAY +{abs(existing.rest_advantage)}" if existing.rest_advantage else "Even",
            },
            "travel": {
                "distance_miles": existing.away_travel_miles,
                "time_zones": existing.away_time_zones_crossed,
                "direction": existing.away_direction,
                "altitude": existing.home_altitude_ft,
            },
            "motivation": {
                "is_rivalry": existing.is_rivalry,
                "is_revenge": existing.is_revenge_game,
                "revenge_team": existing.revenge_team,
                "is_lookahead": existing.is_lookahead_spot,
                "is_letdown": existing.is_letdown_spot,
            },
            "combined": {
                "rest_edge": existing.rest_edge_home,
                "travel_edge": existing.travel_edge_home,
                "motivation_edge": existing.motivation_edge_home,
                "total_edge": existing.total_situation_edge,
                "confidence": existing.confidence,
                "recommendation": existing.recommendation,
            }
        }

    # Generate new analysis if not cached
    analysis = situations.get_full_situation_analysis(
        db,
        game_id=game_id,
        home_team=game.home_team,
        away_team=game.away_team,
        sport=game.sport or "NBA",
        game_date=game.start_time
    )

    return analysis


@router.post("/analyze")
def analyze_situation(
    request: SituationAnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    Analyze situational factors for a game.

    Provide team and context information to get comprehensive analysis.
    """
    game_date = None
    if request.game_date:
        try:
            game_date = datetime.fromisoformat(request.game_date)
        except ValueError:
            pass

    analysis = situations.get_full_situation_analysis(
        db,
        home_team=request.home_team,
        away_team=request.away_team,
        sport=request.sport,
        game_date=game_date,
        game_time=request.game_time,
        home_days_rest=request.home_days_rest,
        away_days_rest=request.away_days_rest,
        home_b2b=request.home_back_to_back,
        away_b2b=request.away_back_to_back,
        away_origin=request.away_origin,
        is_revenge=request.is_revenge,
        revenge_team=request.revenge_team,
        revenge_reason=request.revenge_reason,
        is_lookahead=request.is_lookahead,
        lookahead_team=request.lookahead_team,
        lookahead_opponent=request.lookahead_opponent,
        is_letdown=request.is_letdown,
        letdown_team=request.letdown_team,
        letdown_reason=request.letdown_reason,
        is_elimination=request.is_elimination,
        nothing_to_play_for=request.nothing_to_play_for
    )

    return analysis


@router.get("/rest/{game_id}")
def get_rest_analysis(
    game_id: int,
    db: Session = Depends(get_db)
):
    """
    Get rest analysis for a specific game.
    """
    from app.db import Game

    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Default rest values (would need schedule data for accuracy)
    rest_analysis = situations.calculate_rest_edge(
        home_days_rest=2,
        away_days_rest=2,
        sport=game.sport or "NBA"
    )

    return {
        "game_id": game_id,
        "matchup": f"{game.away_team} @ {game.home_team}",
        "sport": game.sport,
        **rest_analysis
    }


@router.get("/rest/calculate")
def calculate_rest_edge(
    home_rest: int = Query(..., ge=0, le=14),
    away_rest: int = Query(..., ge=0, le=14),
    sport: str = Query("NBA"),
    home_b2b: bool = Query(False),
    away_b2b: bool = Query(False),
):
    """
    Calculate rest edge given rest days for each team.
    """
    return situations.calculate_rest_edge(
        home_rest, away_rest, sport, home_b2b, away_b2b
    )


@router.get("/travel/{game_id}")
def get_travel_analysis(
    game_id: int,
    db: Session = Depends(get_db)
):
    """
    Get travel analysis for a specific game.
    """
    from app.db import Game

    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    travel_analysis = situations.calculate_travel_edge(
        away_team=game.away_team or "",
        home_team=game.home_team or "",
        sport=game.sport or "NBA"
    )

    return {
        "game_id": game_id,
        "matchup": f"{game.away_team} @ {game.home_team}",
        "sport": game.sport,
        **travel_analysis
    }


@router.get("/travel/calculate")
def calculate_travel_edge(
    away_team: str = Query(...),
    home_team: str = Query(...),
    away_origin: Optional[str] = Query(None),
    game_time: Optional[str] = Query(None),
    sport: str = Query("NBA"),
):
    """
    Calculate travel edge between two teams/cities.
    """
    return situations.calculate_travel_edge(
        away_team, home_team, away_origin, game_time, sport
    )


@router.get("/motivation/{game_id}")
def get_motivation_analysis(
    game_id: int,
    is_revenge: bool = Query(False),
    revenge_team: Optional[str] = Query(None),
    is_lookahead: bool = Query(False),
    lookahead_team: Optional[str] = Query(None),
    lookahead_opponent: Optional[str] = Query(None),
    is_letdown: bool = Query(False),
    letdown_team: Optional[str] = Query(None),
    letdown_reason: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get motivation analysis for a specific game.
    """
    from app.db import Game

    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    motivation = situations.calculate_motivation_edge(
        home_team=game.home_team or "",
        away_team=game.away_team or "",
        sport=game.sport or "NBA",
        is_revenge=is_revenge,
        revenge_team=revenge_team,
        is_lookahead=is_lookahead,
        lookahead_team=lookahead_team,
        lookahead_opponent=lookahead_opponent,
        is_letdown=is_letdown,
        letdown_team=letdown_team,
        letdown_reason=letdown_reason
    )

    return {
        "game_id": game_id,
        "matchup": f"{game.away_team} @ {game.home_team}",
        "sport": game.sport,
        **motivation
    }


@router.get("/schedule-spots")
def get_schedule_spots(
    sport: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get all notable schedule spots for today's games.

    Returns lookahead spots, letdown spots, sandwich games, and trap games.
    """
    game_date = None
    if date:
        try:
            game_date = datetime.fromisoformat(date)
        except ValueError:
            game_date = datetime.utcnow()
    else:
        game_date = datetime.utcnow()

    alerts = schedule_spots.get_schedule_spot_alerts(db, sport, game_date)

    return {
        "date": game_date.date().isoformat(),
        "sport_filter": sport,
        "spots": alerts,
        "count": len(alerts)
    }


@router.get("/lookahead")
def get_lookahead_spots(
    sport: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get today's lookahead spots.

    Lookahead: team playing weak opponent before big game.
    """
    spots = schedule_spots.get_todays_lookahead_spots(db, sport)
    return {
        "type": "LOOKAHEAD",
        "description": "Teams that may be looking past current game to bigger matchup",
        "recommendation": "Fade the favorite in these spots",
        "spots": spots,
        "count": len(spots)
    }


@router.get("/letdown")
def get_letdown_spots(
    sport: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get today's letdown spots.

    Letdown: team coming off emotional/OT/big game.
    """
    spots = schedule_spots.get_todays_letdown_spots(db, sport)
    return {
        "type": "LETDOWN",
        "description": "Teams coming off emotional highs (OT, rivalry, clinch)",
        "recommendation": "Fade teams in letdown spots",
        "spots": spots,
        "count": len(spots)
    }


@router.get("/trap-games")
def get_trap_games(
    sport: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get today's trap games.

    Trap: favorite against weak team with schedule concerns.
    """
    spots = schedule_spots.get_todays_trap_games(db, sport)
    return {
        "type": "TRAP",
        "description": "Favorites that may be overvalued by public",
        "recommendation": "Take the underdog or pass",
        "spots": spots,
        "count": len(spots)
    }


@router.get("/historical/{situation_type}")
def get_historical_situation(
    situation_type: str,
    db: Session = Depends(get_db)
):
    """
    Get historical data for a specific situation type.

    Returns ATS record, ROI, and betting implications.
    """
    data = situations.get_historical_situation(db, situation_type)
    if not data:
        raise HTTPException(status_code=404, detail=f"Situation type '{situation_type}' not found")
    return data


@router.get("/historical")
def list_historical_situations(
    sport: Optional[str] = Query(None),
    min_win_pct: Optional[float] = Query(None, ge=0, le=100),
    db: Session = Depends(get_db)
):
    """
    List all historical situations with their track records.

    Filter by sport or minimum win percentage to find profitable angles.
    """
    data = situations.get_all_historical_situations(db, sport, min_win_pct)
    return {
        "situations": data,
        "count": len(data),
        "filters": {
            "sport": sport,
            "min_win_pct": min_win_pct
        }
    }


@router.get("/detect/lookahead")
def detect_lookahead(
    team: str = Query(...),
    current_opponent: str = Query(...),
    next_opponent: str = Query(...),
    sport: str = Query("NBA")
):
    """
    Check if a game is a lookahead spot for a team.
    """
    return schedule_spots.detect_lookahead(team, current_opponent, next_opponent, sport)


@router.get("/detect/letdown")
def detect_letdown(
    team: str = Query(...),
    previous_opponent: str = Query(...),
    previous_game_type: str = Query("normal"),
    sport: str = Query("NBA")
):
    """
    Check if a team is in a letdown spot.

    game_type can be: normal, overtime, rivalry, clinch, upset, national_tv
    """
    return schedule_spots.detect_letdown(team, previous_opponent, previous_game_type, sport)


@router.get("/detect/sandwich")
def detect_sandwich(
    team: str = Query(...),
    previous_opponent: str = Query(...),
    current_opponent: str = Query(...),
    next_opponent: str = Query(...),
    sport: str = Query("NBA")
):
    """
    Check if a team is in a sandwich spot.
    """
    return schedule_spots.detect_sandwich(
        team, previous_opponent, current_opponent, next_opponent, sport
    )


@router.get("/detect/trap")
def detect_trap_game(
    favorite: str = Query(...),
    underdog: str = Query(...),
    spread: float = Query(...),
    sport: str = Query("NBA"),
    is_home_favorite: bool = Query(True),
    previous_opponent: Optional[str] = Query(None),
    next_opponent: Optional[str] = Query(None)
):
    """
    Check if a game is a trap game.
    """
    return schedule_spots.detect_trap_game(
        favorite, underdog, sport, spread,
        is_home_favorite, previous_opponent, next_opponent
    )
