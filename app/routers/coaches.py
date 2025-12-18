"""
Coach DNA API Router

Provides endpoints for coach behavioral analysis and situational records.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from app.db import get_db
from app.services import coach_dna

router = APIRouter(prefix="/coaches", tags=["coaches"])


# Pydantic models for request/response
class GameContextRequest(BaseModel):
    spread: float = 0
    is_home: bool = True
    is_primetime: bool = False
    is_monday_night: bool = False
    is_thursday_night: bool = False
    is_sunday_night: bool = False
    previous_result: str = ""  # "win", "loss", "blowout_win", "blowout_loss"
    is_after_bye: bool = False
    is_division_game: bool = False
    is_conference_game: bool = False
    is_playoff: bool = False
    is_back_to_back: bool = False
    days_rest: int = 3
    opponent_winning: bool = False
    opponent_losing: bool = False


class MatchupRequest(BaseModel):
    coach1_id: int
    coach2_id: int
    spread: float  # From coach1's perspective
    is_coach1_home: bool = True
    is_primetime: bool = False
    is_monday_night: bool = False
    is_thursday_night: bool = False
    is_sunday_night: bool = False
    previous_result_coach1: str = ""
    previous_result_coach2: str = ""
    is_after_bye_coach1: bool = False
    is_after_bye_coach2: bool = False
    is_division_game: bool = False
    is_conference_game: bool = False
    is_playoff: bool = False


@router.get("")
def list_coaches(
    sport: Optional[str] = Query(None, description="Filter by sport (NFL, NBA, CBB)"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    List all coaches, optionally filtered by sport.

    Returns basic info for each coach including career ATS record.
    """
    coaches = coach_dna.get_all_coaches(db, sport=sport, limit=limit)
    return {
        "coaches": coaches,
        "count": len(coaches),
        "sport_filter": sport
    }


@router.get("/situations")
def list_situations():
    """
    Get list of all available situations that can be tracked.

    Returns situation keys and display names.
    """
    situations = coach_dna.get_available_situations()
    return {
        "situations": situations,
        "count": len(situations)
    }


@router.get("/search")
def search_coaches(
    name: str = Query(..., min_length=2, description="Coach name to search"),
    db: Session = Depends(get_db)
):
    """
    Search for coaches by name.

    Case-insensitive partial match search.
    """
    coach = coach_dna.get_coach_by_name(db, name)
    if not coach:
        raise HTTPException(status_code=404, detail=f"No coach found matching '{name}'")
    return coach


@router.get("/leaderboard/{situation}")
def get_leaderboard(
    situation: str,
    sport: Optional[str] = Query(None, description="Filter by sport"),
    min_games: int = Query(10, ge=1, description="Minimum games required"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get leaderboard of best coaches for a specific situation.

    Coaches ranked by ATS win percentage in the given situation.
    """
    leaderboard = coach_dna.get_best_coaches_for_situation(
        db, situation, sport=sport, min_games=min_games
    )

    return {
        "situation": situation,
        "display_name": coach_dna.SITUATION_DISPLAY_NAMES.get(
            situation, situation.replace("_", " ").title()
        ),
        "sport_filter": sport,
        "min_games": min_games,
        "leaderboard": leaderboard[:limit],
        "count": len(leaderboard[:limit])
    }


@router.get("/fade-list/{situation}")
def get_fade_list(
    situation: str,
    sport: Optional[str] = Query(None, description="Filter by sport"),
    min_games: int = Query(10, ge=1, description="Minimum games required"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get list of worst coaches for a specific situation (fade list).

    Coaches ranked by lowest ATS win percentage in the given situation.
    """
    fade_list = coach_dna.get_worst_coaches_for_situation(
        db, situation, sport=sport, min_games=min_games
    )

    return {
        "situation": situation,
        "display_name": coach_dna.SITUATION_DISPLAY_NAMES.get(
            situation, situation.replace("_", " ").title()
        ),
        "sport_filter": sport,
        "min_games": min_games,
        "fade_list": fade_list[:limit],
        "count": len(fade_list[:limit])
    }


@router.get("/compare")
def compare_coaches_endpoint(
    coach1_id: int = Query(..., description="First coach ID"),
    coach2_id: int = Query(..., description="Second coach ID"),
    spread: Optional[float] = Query(None, description="Spread from coach1's perspective"),
    is_home: bool = Query(True, description="Is coach1 home team"),
    db: Session = Depends(get_db)
):
    """
    Compare two coaches head-to-head.

    If spread is provided, includes edge calculation.
    """
    game_context = None
    if spread is not None:
        game_context = {
            "spread": spread,
            "is_home": is_home
        }

    comparison = coach_dna.compare_coaches(
        db, coach1_id, coach2_id, game_context
    )

    if "error" in comparison:
        raise HTTPException(status_code=404, detail=comparison["error"])

    return comparison


@router.get("/{coach_id}")
def get_coach(
    coach_id: int,
    db: Session = Depends(get_db)
):
    """
    Get coach details with all situational records and tendencies.
    """
    coach = coach_dna.get_coach_by_id(db, coach_id)
    if not coach:
        raise HTTPException(status_code=404, detail="Coach not found")
    return coach


@router.get("/{coach_id}/situations")
def get_coach_situations(
    coach_id: int,
    db: Session = Depends(get_db)
):
    """
    Get situational breakdown for a specific coach.

    Returns all situations with records and edges.
    """
    coach = coach_dna.get_coach_by_id(db, coach_id)
    if not coach:
        raise HTTPException(status_code=404, detail="Coach not found")

    return {
        "coach_id": coach_id,
        "coach_name": coach["name"],
        "team": coach["current_team"],
        "situations": coach["situational_records"],
        "count": len(coach["situational_records"])
    }


@router.get("/{coach_id}/situation/{situation}")
def get_coach_single_situation(
    coach_id: int,
    situation: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific situational record for a coach.
    """
    record = coach_dna.get_coach_situational_record(db, coach_id, situation)
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"No record found for coach {coach_id} in situation '{situation}'"
        )
    return record


@router.get("/{coach_id}/edge")
def get_coach_edge(
    coach_id: int,
    spread: float = Query(0, description="Spread (negative for favorite)"),
    is_home: bool = Query(True, description="Is home team"),
    is_primetime: bool = Query(False, description="Primetime game"),
    is_monday_night: bool = Query(False, description="Monday Night game"),
    is_thursday_night: bool = Query(False, description="Thursday Night game"),
    is_sunday_night: bool = Query(False, description="Sunday Night game"),
    previous_result: str = Query("", description="Previous game result"),
    is_after_bye: bool = Query(False, description="After bye week"),
    is_division_game: bool = Query(False, description="Division game"),
    is_conference_game: bool = Query(False, description="Conference game"),
    is_playoff: bool = Query(False, description="Playoff game"),
    is_back_to_back: bool = Query(False, description="Back-to-back (NBA)"),
    days_rest: int = Query(3, description="Days of rest"),
    opponent_winning: bool = Query(False, description="Opponent has winning record"),
    opponent_losing: bool = Query(False, description="Opponent has losing record"),
    db: Session = Depends(get_db)
):
    """
    Calculate edge for a specific game context.

    Returns applicable situations, individual edges, and combined edge.
    """
    game_context = {
        "spread": spread,
        "is_home": is_home,
        "is_primetime": is_primetime,
        "is_monday_night": is_monday_night,
        "is_thursday_night": is_thursday_night,
        "is_sunday_night": is_sunday_night,
        "previous_result": previous_result,
        "is_after_bye": is_after_bye,
        "is_division_game": is_division_game,
        "is_conference_game": is_conference_game,
        "is_playoff": is_playoff,
        "is_back_to_back": is_back_to_back,
        "days_rest": days_rest,
        "opponent_winning": opponent_winning,
        "opponent_losing": opponent_losing
    }

    edge = coach_dna.get_coach_edge(db, coach_id, game_context)

    if "error" in edge:
        raise HTTPException(status_code=404, detail=edge["error"])

    return edge


@router.post("/{coach_id}/edge")
def calculate_coach_edge(
    coach_id: int,
    context: GameContextRequest,
    db: Session = Depends(get_db)
):
    """
    Calculate edge for a specific game context (POST version).

    Accepts game context as JSON body.
    """
    edge = coach_dna.get_coach_edge(db, coach_id, context.model_dump())

    if "error" in edge:
        raise HTTPException(status_code=404, detail=edge["error"])

    return edge


@router.post("/analyze-matchup")
def analyze_matchup(
    request: MatchupRequest,
    db: Session = Depends(get_db)
):
    """
    Full matchup analysis between two coaches.

    Calculates edges for both coaches and provides recommendation.
    """
    additional_context = {
        "is_primetime": request.is_primetime,
        "is_monday_night": request.is_monday_night,
        "is_thursday_night": request.is_thursday_night,
        "is_sunday_night": request.is_sunday_night,
        "is_after_bye": request.is_after_bye_coach1,
        "is_division_game": request.is_division_game,
        "is_conference_game": request.is_conference_game,
        "is_playoff": request.is_playoff,
        "previous_result": request.previous_result_coach1
    }

    analysis = coach_dna.analyze_matchup(
        db,
        request.coach1_id,
        request.coach2_id,
        request.spread,
        request.is_coach1_home,
        additional_context
    )

    if "error" in analysis:
        raise HTTPException(status_code=404, detail=analysis["error"])

    return analysis


@router.get("/{coach_id}/tendencies")
def get_coach_tendencies(
    coach_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all tendencies for a specific coach.

    Returns behavioral tendencies with league comparisons.
    """
    coach = coach_dna.get_coach_by_id(db, coach_id)
    if not coach:
        raise HTTPException(status_code=404, detail="Coach not found")

    return {
        "coach_id": coach_id,
        "coach_name": coach["name"],
        "team": coach["current_team"],
        "tendencies": coach["tendencies"],
        "count": len(coach["tendencies"])
    }
