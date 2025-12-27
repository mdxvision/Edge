"""
Edge Validation Tracker API Router

Endpoints for tracking picks, analyzing edge, and exporting data.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel
import csv
import io

from app.db import get_db
from app.services.edge_tracker import EdgeTracker, get_edge_tracker
from app.services.auto_settler import AutoSettler, get_auto_settler
from app.services.weather_integration import WeatherService, get_weather_service
from app.services.mysportsfeeds import MySportsFeedsService, get_mysportsfeeds_service
from app.services.factor_generator import FactorGenerator, get_factor_generator

router = APIRouter(prefix="/tracker", tags=["Edge Tracker"])


# Request/Response Models
class FactorScore(BaseModel):
    score: float
    detail: str


class LogPickRequest(BaseModel):
    game_id: str
    sport: str
    home_team: str
    away_team: str
    game_time: datetime
    pick_type: str  # spread, moneyline, total
    pick: str  # "Chiefs -3", "Over 45.5", "Lakers ML"
    odds: int  # American odds: -110, +150
    confidence: float  # 0-100
    units_wagered: Optional[float] = 1.0  # Units wagered, default 1.0
    factors: Optional[dict] = None  # All 8 factors with scores
    pick_team: Optional[str] = None
    line_value: Optional[float] = None
    weather_data: Optional[dict] = None


class SettlePickRequest(BaseModel):
    result: str  # won, lost, push
    home_score: int
    away_score: int


class ManualSettleRequest(BaseModel):
    result: str  # won, lost, push
    actual_score: str  # "Chiefs 27, Raiders 20"
    spread_result: Optional[float] = None
    total_result: Optional[float] = None


class AnalyzeGameRequest(BaseModel):
    game_id: str
    sport: str
    home_team: str
    away_team: str
    game_time: datetime
    pick_type: str  # spread, moneyline, total
    pick: str  # "Chiefs -3", "Over 45.5", "Lakers ML"
    line_value: Optional[float] = None


# Routes

@router.post("/picks")
async def log_pick(
    request: LogPickRequest,
    db: Session = Depends(get_db)
):
    """
    Log a new pick with all factors

    Records a pick with confidence score, odds, and factor breakdown.
    Automatically generates 8-factor breakdown if not provided.
    Automatically fetches weather data if not provided.
    Returns pick ID and recommended units.
    """
    tracker = get_edge_tracker(db)
    weather_service = get_weather_service()
    factor_generator = get_factor_generator(weather_service)

    # Auto-fetch weather if not provided and sport is outdoor
    weather_data = request.weather_data
    if not weather_data and request.sport.upper() in ["NFL", "MLB", "NCAAF"]:
        try:
            # Try to get weather using home team name as venue hint
            venue = request.home_team
            weather = await weather_service.get_game_weather(venue, request.game_time)
            if weather and not weather.get("error"):
                weather_data = weather
        except Exception as e:
            # Don't fail the pick if weather fetch fails
            pass

    # Auto-generate factors if not provided
    factors = request.factors
    if not factors:
        try:
            # Determine pick_team from the pick string if not explicitly provided
            pick_team = request.pick_team
            if not pick_team:
                # Try to extract team from pick string (e.g., "Cavaliers -5.5" -> "Cavaliers")
                pick_str = request.pick.lower()
                if request.home_team.lower() in pick_str or any(
                    word in pick_str for word in request.home_team.lower().split()
                ):
                    pick_team = request.home_team
                elif request.away_team.lower() in pick_str or any(
                    word in pick_str for word in request.away_team.lower().split()
                ):
                    pick_team = request.away_team
                else:
                    pick_team = request.home_team  # Default to home team

            factors = await factor_generator.generate_factors(
                sport=request.sport,
                home_team=request.home_team,
                away_team=request.away_team,
                pick_team=pick_team,
                pick_type=request.pick_type,
                line_value=request.line_value,
                game_time=request.game_time,
                weather_data=weather_data
            )
        except Exception as e:
            # Log error but don't fail - create default factors
            import logging
            logging.error(f"Factor generation failed: {e}")
            factors = _create_default_factors(request.pick_team or request.home_team)

    result = tracker.log_pick(
        game_id=request.game_id,
        sport=request.sport,
        home_team=request.home_team,
        away_team=request.away_team,
        game_time=request.game_time,
        pick_type=request.pick_type,
        pick=request.pick,
        odds=request.odds,
        confidence=request.confidence,
        factors=factors,
        pick_team=request.pick_team,
        line_value=request.line_value,
        weather_data=weather_data,
        units_wagered=request.units_wagered
    )

    return result


@router.post("/analyze")
async def analyze_game(
    request: AnalyzeGameRequest,
    db: Session = Depends(get_db)
):
    """
    Analyze a game and return 8-factor breakdown without logging a pick

    Returns factor scores and data quality assessment.
    Data quality is determined by how many factors have live data vs pending/estimated.
    """
    weather_service = get_weather_service()
    factor_generator = get_factor_generator(weather_service)

    # Auto-fetch weather if sport is outdoor
    weather_data = None
    if request.sport.upper() in ["NFL", "MLB", "NCAAF"]:
        try:
            venue = request.home_team
            weather = await weather_service.get_game_weather(venue, request.game_time)
            if weather and not weather.get("error"):
                weather_data = weather
        except Exception:
            pass

    # Determine pick_team from the pick string
    pick_team = None
    pick_str = request.pick.lower()
    if request.home_team.lower() in pick_str or any(
        word in pick_str for word in request.home_team.lower().split()
    ):
        pick_team = request.home_team
    elif request.away_team.lower() in pick_str or any(
        word in pick_str for word in request.away_team.lower().split()
    ):
        pick_team = request.away_team
    else:
        pick_team = request.home_team

    # Generate factors
    try:
        factors = await factor_generator.generate_factors(
            sport=request.sport,
            home_team=request.home_team,
            away_team=request.away_team,
            pick_team=pick_team,
            pick_type=request.pick_type,
            line_value=request.line_value,
            game_time=request.game_time,
            weather_data=weather_data
        )
    except Exception as e:
        import logging
        logging.error(f"Factor generation failed: {e}")
        factors = _create_default_factors(pick_team)

    # Calculate data quality
    # A factor is considered "live" if its detail doesn't contain pending/estimated/not yet
    pending_keywords = ["pending", "estimated", "not yet", "unknown", "data unavailable"]
    live_factors = 0

    # Transform factors to include status
    transformed_factors = {}
    for factor_name, factor_data in factors.items():
        detail = factor_data.get("detail", "")
        is_live = not any(keyword in detail.lower() for keyword in pending_keywords)
        if is_live:
            live_factors += 1
        transformed_factors[factor_name] = {
            "score": factor_data.get("score", 50),
            "status": "live" if is_live else "pending",
            "details": detail
        }

    total_factors = len(factors)
    data_quality_pct = (live_factors / total_factors) * 100 if total_factors > 0 else 0

    # Calculate average score (overall edge)
    avg_score = sum(f.get("score", 50) for f in factors.values()) / len(factors) if factors else 50

    # Calculate confidence based on data quality and score spread
    confidence = min(85, max(45, avg_score + (data_quality_pct - 50) * 0.2))

    # Generate recommendation
    if avg_score >= 60:
        strength = "STRONG" if avg_score >= 70 else "LEAN"
    else:
        strength = "FADE" if avg_score < 45 else "NEUTRAL"
    recommendation = f"{strength} {request.pick}"

    return {
        "game_id": request.game_id,
        "sport": request.sport,
        "home_team": request.home_team,
        "away_team": request.away_team,
        "pick": request.pick,
        "pick_type": request.pick_type,
        "factors": transformed_factors,
        "data_quality": round(data_quality_pct, 1),
        "overall_edge": round(avg_score, 1),
        "confidence": round(confidence, 1),
        "recommendation": recommendation,
        "meets_threshold": data_quality_pct >= 60,
        "weather_data": weather_data
    }


def _create_default_factors(pick_team: str) -> dict:
    """Create default factors when generation fails"""
    import random
    return {
        "coach_dna": {
            "score": random.randint(48, 65),
            "detail": f"{pick_team} coach record (estimated)"
        },
        "referee": {
            "score": 50,
            "detail": "Officials not yet assigned"
        },
        "weather": {
            "score": 50,
            "detail": "Weather data pending"
        },
        "line_movement": {
            "score": random.randint(48, 58),
            "detail": "Line movement analysis pending"
        },
        "rest": {
            "score": 50,
            "detail": "Rest data pending"
        },
        "travel": {
            "score": 50,
            "detail": "Travel data pending"
        },
        "situational": {
            "score": random.randint(48, 60),
            "detail": f"{pick_team} situational ATS (estimated)"
        },
        "public_betting": {
            "score": 50,
            "detail": "Public betting data pending"
        }
    }


@router.get("/picks")
async def get_picks(
    sport: Optional[str] = Query(None, description="Filter by sport (NFL, NBA, MLB, etc.)"),
    status: Optional[str] = Query(None, description="Filter by status (pending, won, lost, push)"),
    days: Optional[int] = Query(30, description="Number of days to look back"),
    limit: int = Query(50, le=200, description="Maximum picks to return"),
    db: Session = Depends(get_db)
):
    """
    Get all picks with filters

    Returns picks filtered by sport, status, and date range.
    """
    tracker = get_edge_tracker(db)

    start_date = datetime.utcnow() - timedelta(days=days) if days else None

    picks = tracker.get_picks(
        sport=sport,
        status=status,
        start_date=start_date,
        limit=limit
    )

    return {
        "count": len(picks),
        "picks": picks
    }


@router.get("/picks/{pick_id}")
async def get_pick(
    pick_id: str,
    db: Session = Depends(get_db)
):
    """
    Get single pick details

    Returns full pick details including factor breakdown.
    """
    tracker = get_edge_tracker(db)
    pick = tracker.get_pick(pick_id)

    if not pick:
        raise HTTPException(status_code=404, detail="Pick not found")

    return pick


@router.post("/picks/{pick_id}/settle")
async def settle_pick(
    pick_id: str,
    request: ManualSettleRequest,
    db: Session = Depends(get_db)
):
    """
    Manually settle a pick

    Use when auto-settlement doesn't work or for manual override.
    """
    tracker = get_edge_tracker(db)

    result = tracker.settle_pick(
        pick_id=pick_id,
        result=request.result,
        actual_score=request.actual_score,
        spread_result=request.spread_result,
        total_result=request.total_result
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/picks/{pick_id}/settle-with-score")
async def settle_pick_with_score(
    pick_id: str,
    request: SettlePickRequest,
    db: Session = Depends(get_db)
):
    """
    Settle a pick by providing final scores

    Automatically calculates result based on pick type and scores.
    """
    settler = get_auto_settler(db)

    result = await settler.settle_single_pick(
        pick_id=pick_id,
        result=request.result,
        home_score=request.home_score,
        away_score=request.away_score
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/stats")
async def get_edge_stats(db: Session = Depends(get_db)):
    """
    Get overall edge statistics

    Returns win rate, ROI, p-value, confidence intervals, and statistical significance.
    """
    tracker = get_edge_tracker(db)
    return tracker.get_edge_stats()


@router.get("/stats/by-sport")
async def get_stats_by_sport(db: Session = Depends(get_db)):
    """
    Get edge stats broken down by sport

    Shows which sports have the best edge.
    """
    tracker = get_edge_tracker(db)
    return tracker.get_stats_by_sport()


@router.get("/stats/by-confidence")
async def get_stats_by_confidence(db: Session = Depends(get_db)):
    """
    Get stats by confidence tier

    Validates if higher confidence picks perform better.
    """
    tracker = get_edge_tracker(db)
    return tracker.get_stats_by_confidence_tier()


@router.get("/factors")
async def get_factor_analysis(db: Session = Depends(get_db)):
    """
    Get factor analysis breakdown

    Shows which factors correlate most with wins.
    """
    tracker = get_edge_tracker(db)
    return tracker.get_factor_analysis()


@router.get("/bankroll")
async def get_bankroll_history(db: Session = Depends(get_db)):
    """
    Get bankroll history over time

    Returns snapshots of bankroll balance and performance metrics.
    """
    tracker = get_edge_tracker(db)
    return {
        "starting_balance": 100.0,
        "history": tracker.get_bankroll_history()
    }


@router.get("/streaks")
async def get_streak_analysis(db: Session = Depends(get_db)):
    """
    Get win/loss streak analysis

    Returns current streak, longest streaks, and max drawdown.
    """
    tracker = get_edge_tracker(db)
    return tracker.get_streak_analysis()


@router.post("/auto-settle")
async def run_auto_settlement(db: Session = Depends(get_db)):
    """
    Manually trigger auto-settlement

    Checks all pending picks and settles completed games.
    """
    settler = get_auto_settler(db)
    result = await settler.check_and_settle_pending()
    return result


@router.get("/export")
async def export_data(
    format: str = Query("json", description="Export format (json or csv)"),
    db: Session = Depends(get_db)
):
    """
    Export all data for external analysis

    Returns all picks with full factor breakdown.
    """
    tracker = get_edge_tracker(db)
    data = tracker.export_data()

    if format.lower() == "csv":
        # Create CSV response
        output = io.StringIO()
        if data:
            # Flatten factors for CSV
            flat_data = []
            for pick in data:
                flat_pick = {k: v for k, v in pick.items() if k not in ["factors", "weather_data"]}

                # Add factor scores as separate columns
                factors = pick.get("factors", {}) or {}
                for factor_name in ["coach_dna", "referee", "weather", "line_movement",
                                    "rest", "travel", "situational", "public_betting"]:
                    factor_data = factors.get(factor_name, {})
                    flat_pick[f"{factor_name}_score"] = factor_data.get("score", "")
                    flat_pick[f"{factor_name}_detail"] = factor_data.get("detail", "")

                flat_data.append(flat_pick)

            if flat_data:
                writer = csv.DictWriter(output, fieldnames=flat_data[0].keys())
                writer.writeheader()
                writer.writerows(flat_data)

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=edge_tracker_export.csv"}
        )

    return {
        "count": len(data),
        "picks": data
    }


@router.get("/weather/{venue}")
async def get_venue_weather(
    venue: str,
    game_time: Optional[datetime] = Query(None, description="Game time (defaults to now)"),
    sport: str = Query("NFL", description="Sport for impact analysis")
):
    """
    Get weather data and impact analysis for a venue

    Returns weather conditions and sport-specific impact score.
    """
    weather_service = get_weather_service()

    game_dt = game_time or datetime.utcnow()
    weather = await weather_service.get_game_weather(venue, game_dt)

    if weather.get("error"):
        raise HTTPException(status_code=400, detail=weather["error"])

    impact = weather_service.calculate_weather_impact(weather, sport)

    return {
        "venue": venue,
        "game_time": game_dt.isoformat(),
        "weather": weather,
        "impact": impact
    }


@router.get("/summary")
async def get_tracker_summary(db: Session = Depends(get_db)):
    """
    Get comprehensive tracker summary

    Returns all key metrics in one response for dashboard.
    """
    tracker = get_edge_tracker(db)

    stats = tracker.get_edge_stats()
    streaks = tracker.get_streak_analysis()
    by_sport = tracker.get_stats_by_sport()
    by_confidence = tracker.get_stats_by_confidence_tier()
    recent_picks = tracker.get_picks(limit=20)
    bankroll = tracker.get_bankroll_history()

    # Get validation status
    validation_status = "INSUFFICIENT_DATA"
    if stats["total_picks"] >= 200:
        if stats["is_significant"] and stats["edge"] > 2:
            validation_status = "VALIDATED"
        elif stats["edge"] > 0:
            validation_status = "PROMISING"
        else:
            validation_status = "NO_EDGE"
    elif stats["total_picks"] >= 100:
        validation_status = "NEEDS_MORE_DATA"

    return {
        "validation_status": validation_status,
        "stats": stats,
        "streaks": streaks,
        "by_sport": by_sport,
        "by_confidence": by_confidence,
        "recent_picks": recent_picks,
        "current_bankroll": bankroll[-1]["balance"] if bankroll else 100.0,
        "bankroll_history": bankroll
    }


# Data Management Endpoints

@router.delete("/picks/{pick_id}")
async def delete_pick(
    pick_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a single pick

    Removes a pick from tracking. Use for removing test/dummy data.
    """
    from app.db import TrackedPick

    pick = db.query(TrackedPick).filter(TrackedPick.id == pick_id).first()
    if not pick:
        raise HTTPException(status_code=404, detail="Pick not found")

    db.delete(pick)
    db.commit()

    return {"message": f"Pick {pick_id} deleted", "success": True}


@router.delete("/picks")
async def delete_all_picks(
    confirm: bool = Query(False, description="Must be true to confirm deletion"),
    db: Session = Depends(get_db)
):
    """
    Delete all picks (requires confirmation)

    Clears all tracked picks. Use for resetting tracker.
    """
    if not confirm:
        return {
            "warning": "This will delete ALL picks. Set confirm=true to proceed.",
            "success": False
        }

    from app.db import TrackedPick, BankrollSnapshot

    # Delete all picks
    pick_count = db.query(TrackedPick).delete()

    # Delete all bankroll snapshots
    snapshot_count = db.query(BankrollSnapshot).delete()

    db.commit()

    return {
        "message": f"Deleted {pick_count} picks and {snapshot_count} snapshots",
        "success": True,
        "picks_deleted": pick_count,
        "snapshots_deleted": snapshot_count
    }


# Test Endpoints for API Connections

@router.get("/test/mysportsfeeds")
async def test_mysportsfeeds_connection():
    """
    Test MySportsFeeds API connection

    Returns connection status and sample data if successful.
    """
    service = get_mysportsfeeds_service()
    result = await service.test_connection()

    if result.get("success"):
        # Try to get some sample data
        try:
            games = await service.get_games("NFL", days_back=7)
            result["sample_games_count"] = len(games)
            if games:
                result["sample_game"] = games[0]
        except Exception as e:
            result["sample_error"] = str(e)

    return result


@router.get("/test/weather")
async def test_weather_connection(
    venue: str = Query("Arrowhead Stadium", description="Test venue name"),
    sport: str = Query("NFL", description="Sport for impact analysis")
):
    """
    Test WeatherAPI connection

    Returns weather data for a test venue.
    """
    weather_service = get_weather_service()

    try:
        weather = await weather_service.get_game_weather(venue, datetime.utcnow())
        impact = weather_service.calculate_weather_impact(weather, sport)

        return {
            "success": True,
            "venue": venue,
            "weather": weather,
            "impact": impact
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/test/games/{sport}")
async def test_get_games(
    sport: str,
    days_back: int = Query(3, description="Days to look back for games")
):
    """
    Test fetching games for a sport

    Returns recent games from MySportsFeeds.
    """
    service = get_mysportsfeeds_service()

    if not service.is_configured():
        return {
            "success": False,
            "error": "MYSPORTSFEEDS_API_KEY not configured"
        }

    try:
        games = await service.get_games(sport, days_back=days_back)
        completed = [g for g in games if g.get("status") == "COMPLETED"]

        return {
            "success": True,
            "sport": sport.upper(),
            "total_games": len(games),
            "completed_games": len(completed),
            "games": games[:10]  # Return first 10
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/test/api-status")
async def test_all_apis():
    """
    Test all external API connections

    Returns status for MySportsFeeds and WeatherAPI.
    """
    import os

    results = {
        "mysportsfeeds": {
            "configured": bool(os.environ.get("MYSPORTSFEEDS_API_KEY")),
            "status": "unknown"
        },
        "weather_api": {
            "configured": bool(os.environ.get("WEATHER_API_KEY")),
            "status": "unknown"
        },
        "odds_api": {
            "configured": bool(os.environ.get("THE_ODDS_API_KEY")),
            "status": "unknown"
        }
    }

    # Test MySportsFeeds
    if results["mysportsfeeds"]["configured"]:
        msf_service = get_mysportsfeeds_service()
        msf_result = await msf_service.test_connection()
        results["mysportsfeeds"]["status"] = "connected" if msf_result.get("success") else "error"
        results["mysportsfeeds"]["message"] = msf_result.get("message") or msf_result.get("error")

    # Test WeatherAPI
    if results["weather_api"]["configured"]:
        weather_service = get_weather_service()
        try:
            weather = await weather_service.get_game_weather("Kansas City", datetime.utcnow())
            results["weather_api"]["status"] = "connected" if not weather.get("error") else "error"
            results["weather_api"]["source"] = weather.get("source")
        except Exception as e:
            results["weather_api"]["status"] = "error"
            results["weather_api"]["message"] = str(e)

    return results
