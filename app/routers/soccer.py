"""
Soccer API Router

Endpoints for soccer/football data from major European leagues.
Uses Football-Data.org API.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
from typing import Optional, List

from app.db import get_db, SoccerCompetition, SoccerTeam, SoccerMatch
from app.services import soccer_stats

router = APIRouter(prefix="/soccer", tags=["Soccer"])


def add_time_display(match_date_str: str) -> str:
    """Convert match date to EST display format."""
    try:
        dt = datetime.fromisoformat(match_date_str.replace("Z", "+00:00"))
        est_dt = dt - timedelta(hours=5)
        return est_dt.strftime("%a, %b %d at %I:%M %p") + " EST"
    except:
        return None


# Supported competitions for reference
SUPPORTED_COMPETITIONS = {
    "PL": "Premier League",
    "PD": "La Liga",
    "BL1": "Bundesliga",
    "SA": "Serie A",
    "FL1": "Ligue 1",
    "ELC": "Championship",
    "CL": "Champions League"
}


@router.get("/competitions")
async def get_competitions(db: Session = Depends(get_db)):
    """
    Get list of available soccer competitions (leagues).

    Free tier includes: Premier League, La Liga, Bundesliga, Serie A,
    Ligue 1, Championship, and Champions League.
    """
    # Try database first
    db_competitions = db.query(SoccerCompetition).all()
    if db_competitions:
        return {
            "count": len(db_competitions),
            "competitions": [
                {
                    "id": comp.id,
                    "code": comp.code,
                    "name": comp.name,
                    "country": comp.country,
                    "emblem_url": comp.emblem_url,
                    "current_matchday": comp.current_matchday
                }
                for comp in db_competitions
            ]
        }

    # Fetch from API
    competitions = await soccer_stats.get_competitions()

    # If API fails, return supported competitions
    if not competitions:
        return {
            "count": len(SUPPORTED_COMPETITIONS),
            "competitions": [
                {"code": code, "name": name, "available": True}
                for code, name in SUPPORTED_COMPETITIONS.items()
            ],
            "note": "API key not configured. Showing supported competitions."
        }

    return {
        "count": len(competitions),
        "competitions": competitions
    }


@router.get("/competition/{code}/standings")
async def get_standings(code: str, db: Session = Depends(get_db)):
    """
    Get league table/standings for a competition.

    Args:
        code: Competition code (e.g., 'PL' for Premier League)
    """
    if code not in SUPPORTED_COMPETITIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Competition '{code}' not available. Supported: {', '.join(SUPPORTED_COMPETITIONS.keys())}"
        )

    standings = await soccer_stats.get_standings(code)

    if not standings:
        return {
            "competition": code,
            "standings": [],
            "note": "Unable to fetch standings. Check API configuration."
        }

    return standings


@router.get("/competition/{code}/matches")
async def get_competition_matches(
    code: str,
    matchday: Optional[int] = None,
    status: Optional[str] = Query(None, description="Filter by status: SCHEDULED, IN_PLAY, FINISHED"),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get matches for a competition.

    Args:
        code: Competition code (e.g., 'PL')
        matchday: Optional matchday number
        status: Optional status filter
        date_from: Optional start date (YYYY-MM-DD)
        date_to: Optional end date (YYYY-MM-DD)
    """
    if code not in SUPPORTED_COMPETITIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Competition '{code}' not available. Supported: {', '.join(SUPPORTED_COMPETITIONS.keys())}"
        )

    # Parse dates
    from_date = None
    to_date = None
    if date_from:
        try:
            from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_from format. Use YYYY-MM-DD")
    if date_to:
        try:
            to_date = datetime.strptime(date_to, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_to format. Use YYYY-MM-DD")

    matches = await soccer_stats.get_matches(code, matchday, status, from_date, to_date)

    # Add game_time_display to each match
    for match in matches:
        match_date = match.get("match_date") or match.get("utcDate")
        if match_date:
            time_display = add_time_display(match_date)
            if time_display:
                match["game_time_display"] = time_display

    return {
        "competition": code,
        "competition_name": SUPPORTED_COMPETITIONS[code],
        "count": len(matches),
        "matches": matches
    }


@router.get("/competition/{code}/scorers")
async def get_top_scorers(
    code: str,
    limit: int = Query(20, le=50, description="Number of top scorers to return")
):
    """
    Get top scorers for a competition.

    Args:
        code: Competition code (e.g., 'PL')
        limit: Number of scorers to return
    """
    if code not in SUPPORTED_COMPETITIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Competition '{code}' not available. Supported: {', '.join(SUPPORTED_COMPETITIONS.keys())}"
        )

    scorers = await soccer_stats.get_scorers(code, limit)

    return {
        "competition": code,
        "competition_name": SUPPORTED_COMPETITIONS[code],
        "count": len(scorers),
        "scorers": scorers
    }


@router.get("/matches/today")
async def get_todays_matches(db: Session = Depends(get_db)):
    """
    Get today's matches across all supported competitions.

    Returns matches from Premier League, La Liga, Bundesliga, Serie A,
    Ligue 1, Championship, and Champions League.
    """
    today = date.today()

    # Try database first
    try:
        db_matches = db.query(SoccerMatch).filter(
            SoccerMatch.match_date >= datetime.combine(today, datetime.min.time()),
            SoccerMatch.match_date <= datetime.combine(today, datetime.max.time())
        ).all()

        if db_matches:
            matches_list = []
            for match in db_matches:
                match_date_iso = match.match_date.isoformat()
                est_dt = match.match_date - timedelta(hours=5)
                matches_list.append({
                    "id": match.id,
                    "competition": match.competition_code,
                    "matchday": match.matchday,
                    "status": match.status,
                    "match_date": match_date_iso,
                    "game_time_display": est_dt.strftime("%a, %b %d at %I:%M %p") + " EST",
                    "venue": match.venue,
                    "home_team": {
                        "name": match.home_team_name,
                        "score": match.home_score
                    },
                    "away_team": {
                        "name": match.away_team_name,
                        "score": match.away_score
                    }
                })
            return {
                "date": today.isoformat(),
                "count": len(matches_list),
                "matches": matches_list
            }
    except Exception:
        # Database table may not exist, fall through to API
        pass

    # Fetch from API
    matches = await soccer_stats.get_todays_matches()

    # Add game_time_display to each match
    for match in matches:
        match_date = match.get("match_date") or match.get("utcDate")
        if match_date:
            time_display = add_time_display(match_date)
            if time_display:
                match["game_time_display"] = time_display

    return {
        "date": today.isoformat(),
        "count": len(matches),
        "matches": matches
    }


@router.get("/games")
async def get_games(db: Session = Depends(get_db)):
    """
    Alias for /matches/today - Get today's soccer games.
    Returns games in same format as other sports endpoints.
    """
    result = await get_todays_matches(db)
    # Return with 'games' key for consistency with other sports
    return {
        "date": result.get("date"),
        "count": result.get("count"),
        "games": result.get("matches", [])
    }


@router.get("/match/{match_id}")
async def get_match_details(match_id: int):
    """
    Get detailed match information.

    Args:
        match_id: Football-Data.org match ID
    """
    match = await soccer_stats.get_match(match_id)

    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    return match


@router.get("/team/{team_id}")
async def get_team(team_id: int, db: Session = Depends(get_db)):
    """
    Get team information.

    Args:
        team_id: Football-Data.org team ID
    """
    # Check database first
    db_team = db.query(SoccerTeam).filter(
        SoccerTeam.football_data_id == team_id
    ).first()

    # Fetch from API for full details
    team = await soccer_stats.get_team(team_id)

    if not team and not db_team:
        raise HTTPException(status_code=404, detail="Team not found")

    if db_team and not team:
        return {
            "id": db_team.id,
            "football_data_id": db_team.football_data_id,
            "name": db_team.name,
            "short_name": db_team.short_name,
            "crest_url": db_team.crest_url,
            "venue": db_team.venue
        }

    return team


@router.get("/team/{team_id}/matches")
async def get_team_matches(
    team_id: int,
    status: Optional[str] = Query(None, description="Filter by status: SCHEDULED, FINISHED"),
    limit: int = Query(10, le=50)
):
    """
    Get matches for a specific team.

    Args:
        team_id: Football-Data.org team ID
        status: Optional status filter
        limit: Maximum matches to return
    """
    matches = await soccer_stats.get_team_matches(team_id, status, limit)

    # Add game_time_display to each match
    for match in matches:
        match_date = match.get("match_date") or match.get("utcDate")
        if match_date:
            time_display = add_time_display(match_date)
            if time_display:
                match["game_time_display"] = time_display

    return {
        "team_id": team_id,
        "count": len(matches),
        "matches": matches
    }


@router.post("/refresh")
async def refresh_soccer_data(db: Session = Depends(get_db)):
    """
    Manually trigger a refresh of soccer data.

    Updates competitions, teams, standings, and matches.
    Note: Subject to API rate limits (10 requests/minute).
    """
    try:
        result = await soccer_stats.refresh_soccer_data(db)

        if result.get("error"):
            return {
                "status": "warning",
                "message": result["error"],
                "details": result
            }

        return {
            "status": "success",
            "message": "Soccer data refreshed successfully",
            "details": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh soccer data: {str(e)}"
        )
