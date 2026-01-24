from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db import get_db, Game, Team, Competitor
from app.schemas.games import GameRead, TeamRead, CompetitorRead
from app.config import SUPPORTED_SPORTS, TEAM_SPORTS
from app.utils.cache import cache, TTL_SHORT, PREFIX_GAMES, PREFIX_TEAMS

router = APIRouter(prefix="/games", tags=["Games"])


@router.get("/", response_model=List[GameRead])
def list_games(
    sport: Optional[str] = Query(None, description="Filter by sport"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List games with optional sport filter. Cached for 1 minute."""
    cache_key = f"{PREFIX_GAMES}:list:{sport or 'all'}:{limit}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    query = db.query(Game)

    if sport:
        query = query.filter(Game.sport == sport)

    games = query.order_by(Game.start_time).limit(limit).all()

    result = []
    for game in games:
        game_read = GameRead(
            id=game.id,
            sport=game.sport,
            home_team_id=game.home_team_id,
            away_team_id=game.away_team_id,
            home_team_name=game.home_team.name if game.home_team else None,
            away_team_name=game.away_team.name if game.away_team else None,
            competitor1_id=game.competitor1_id,
            competitor2_id=game.competitor2_id,
            competitor1_name=game.competitor1.name if game.competitor1 else None,
            competitor2_name=game.competitor2.name if game.competitor2 else None,
            start_time=game.start_time,
            venue=game.venue,
            league=game.league
        )
        result.append(game_read)

    cache.set(cache_key, [r.model_dump() for r in result], TTL_SHORT)
    return result


@router.get("/sports")
def list_sports():
    return {
        "supported_sports": SUPPORTED_SPORTS,
        "team_sports": TEAM_SPORTS,
        "individual_sports": [s for s in SUPPORTED_SPORTS if s not in TEAM_SPORTS]
    }


@router.get("/teams", response_model=List[TeamRead])
def list_teams(
    sport: Optional[str] = Query(None, description="Filter by sport"),
    db: Session = Depends(get_db)
):
    """List teams with optional sport filter. Cached for 1 minute."""
    cache_key = f"{PREFIX_TEAMS}:list:{sport or 'all'}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    query = db.query(Team)

    if sport:
        query = query.filter(Team.sport == sport)

    teams = query.all()
    cache.set(cache_key, [TeamRead.model_validate(t).model_dump() for t in teams], TTL_SHORT)
    return teams


@router.get("/competitors", response_model=List[CompetitorRead])
def list_competitors(
    sport: Optional[str] = Query(None, description="Filter by sport"),
    db: Session = Depends(get_db)
):
    """List competitors with optional sport filter. Cached for 1 minute."""
    cache_key = f"{PREFIX_TEAMS}:competitors:{sport or 'all'}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    query = db.query(Competitor)

    if sport:
        query = query.filter(Competitor.sport == sport)

    competitors = query.all()
    cache.set(cache_key, [CompetitorRead.model_validate(c).model_dump() for c in competitors], TTL_SHORT)
    return competitors
