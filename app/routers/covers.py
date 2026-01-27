"""
Covers.com Data Router

API endpoints for ATS records, O/U trends, consensus picks, and expert picks
from Covers.com data.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.db import get_db, User
from app.routers.auth import require_auth
from app.services import covers_scraper

router = APIRouter(prefix="/covers", tags=["Covers.com"])


# =============================================================================
# ATS Records
# =============================================================================

@router.get("/ats/{sport}")
async def get_ats_records(
    sport: str,
    season: Optional[str] = Query(None, description="Season (e.g., '2024')"),
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Get ATS (Against The Spread) records for all teams in a sport.

    Returns:
    - Overall ATS record (wins-losses-pushes)
    - Home/Away splits
    - Favorite/Underdog splits
    - Current ATS streak

    **Usage:** Identify teams that consistently cover or fail to cover spreads.
    """
    sport = sport.upper()
    if sport not in ["NFL", "NBA", "MLB", "NHL", "NCAAF", "NCAAB"]:
        raise HTTPException(status_code=400, detail="Unsupported sport")

    records = await covers_scraper.get_team_ats_records(sport, db, season)

    return {
        "sport": sport,
        "season": season or "current",
        "teams": records,
        "count": len(records),
        "source": "covers.com"
    }


@router.get("/ats/{sport}/{team}")
async def get_team_ats(
    sport: str,
    team: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Get ATS record for a specific team.

    Returns detailed ATS breakdown including situational splits.
    """
    sport = sport.upper()
    record = await covers_scraper.get_team_ats_record(team, sport, db)

    if "error" in record:
        raise HTTPException(status_code=404, detail=record["error"])

    return record


# =============================================================================
# Over/Under Trends
# =============================================================================

@router.get("/ou/{sport}")
async def get_ou_trends(
    sport: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Get Over/Under trends for all teams in a sport.

    Returns:
    - Overall O/U record
    - Home/Away O/U splits
    - Average totals set vs actual
    - Current O/U streak

    **Usage:** Identify teams whose games consistently go over or under.
    """
    sport = sport.upper()
    if sport not in ["NFL", "NBA", "MLB", "NHL", "NCAAF", "NCAAB"]:
        raise HTTPException(status_code=400, detail="Unsupported sport")

    trends = await covers_scraper.get_team_ou_trends(sport, db)

    return {
        "sport": sport,
        "teams": trends,
        "count": len(trends),
        "source": "covers.com"
    }


@router.get("/ou/{sport}/{team}")
async def get_team_ou(
    sport: str,
    team: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Get O/U trend for a specific team.

    Returns detailed over/under breakdown.
    """
    sport = sport.upper()
    trend = await covers_scraper.get_team_ou_trend(team, sport, db)

    if "error" in trend:
        raise HTTPException(status_code=404, detail=trend["error"])

    return trend


# =============================================================================
# Consensus Picks
# =============================================================================

@router.get("/consensus/{sport}")
async def get_consensus_picks(
    sport: str,
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Get consensus picks for a sport on a given date.

    Returns:
    - Expert pick percentages (home vs away)
    - Public betting percentages
    - Sharp vs public divergence indicator
    - Consensus pick (if clear majority)

    **Usage:** Identify games where experts and public disagree (contrarian value).
    """
    sport = sport.upper()
    if sport not in ["NFL", "NBA", "MLB", "NHL", "NCAAF", "NCAAB"]:
        raise HTTPException(status_code=400, detail="Unsupported sport")

    # Parse date
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        target_date = datetime.utcnow()

    picks = await covers_scraper.get_consensus_picks(sport, db, target_date)

    return {
        "sport": sport,
        "date": target_date.date().isoformat(),
        "picks": picks,
        "count": len(picks),
        "source": "covers.com"
    }


@router.get("/consensus/game/{game_id}")
async def get_game_consensus(
    game_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Get consensus picks for a specific game.

    Returns expert and public betting breakdown with divergence analysis.
    """
    result = await covers_scraper.get_game_consensus(game_id, db)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


# =============================================================================
# Expert Picks
# =============================================================================

@router.get("/experts/{sport}")
async def get_expert_picks(
    sport: str,
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Get expert picks for a sport.

    Returns:
    - Individual expert predictions
    - Expert track records (win %, ROI)
    - Today's picks with confidence levels
    - Expert specialties

    **Usage:** Follow experts with proven track records in specific sports.
    """
    sport = sport.upper()
    if sport not in ["NFL", "NBA", "MLB", "NHL", "NCAAF", "NCAAB"]:
        raise HTTPException(status_code=400, detail="Unsupported sport")

    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        target_date = datetime.utcnow()

    picks = await covers_scraper.get_expert_picks(sport, db, target_date)

    # Filter by sport specialty
    relevant_picks = [p for p in picks if p.get("specialty") == sport or p.get("best_sport") == sport]

    return {
        "sport": sport,
        "date": target_date.date().isoformat(),
        "experts": picks,
        "sport_specialists": relevant_picks,
        "count": len(picks),
        "source": "covers.com"
    }


@router.get("/experts/leaderboard")
async def get_expert_leaderboard(
    sport: Optional[str] = Query(None, description="Filter by sport"),
    min_picks: int = Query(100, ge=10, description="Minimum picks for inclusion"),
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Get expert leaderboard ranked by ROI.

    Returns experts sorted by return on investment with minimum pick requirements.
    """
    # Get all experts
    all_experts = await covers_scraper.get_expert_picks(
        sport or "NFL", db, datetime.utcnow()
    )

    # Filter by minimum picks
    qualified = [
        e for e in all_experts
        if e.get("track_record", {}).get("total_picks", 0) >= min_picks
    ]

    # Sort by ROI
    qualified.sort(
        key=lambda x: x.get("track_record", {}).get("roi", 0),
        reverse=True
    )

    return {
        "sport_filter": sport,
        "min_picks": min_picks,
        "experts": qualified,
        "count": len(qualified)
    }


# =============================================================================
# Team Trends Summary
# =============================================================================

@router.get("/trends/{sport}/{team}")
async def get_team_trends(
    sport: str,
    team: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Get comprehensive trends summary for a team.

    Combines:
    - ATS record (overall, home/away, fav/dog)
    - O/U trends
    - Situational records (after loss, primetime, etc.)
    - Recent form (last 5 games)
    - Key betting angles

    **Usage:** Complete team profile for betting research.
    """
    sport = sport.upper()
    trends = await covers_scraper.get_team_trends(team, sport, db)

    if "error" in trends:
        raise HTTPException(status_code=404, detail=trends["error"])

    return trends


# =============================================================================
# Best Bets / Value Plays
# =============================================================================

@router.get("/best-bets/{sport}")
async def get_best_bets(
    sport: str,
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Get best bets based on consensus and trends.

    Identifies games with:
    - Strong expert consensus (65%+)
    - Sharp vs public divergence
    - Favorable team trends

    Returns games ranked by confidence level.
    """
    sport = sport.upper()
    if sport not in ["NFL", "NBA", "MLB", "NHL", "NCAAF", "NCAAB"]:
        raise HTTPException(status_code=400, detail="Unsupported sport")

    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        target_date = datetime.utcnow()

    consensus = await covers_scraper.get_consensus_picks(sport, db, target_date)

    best_bets = []
    for pick in consensus:
        spread_data = pick.get("spread", {})
        expert_picks = spread_data.get("expert_picks", {})

        # Check for strong consensus
        home_pct = expert_picks.get("home_pct", 50)
        away_pct = expert_picks.get("away_pct", 50)

        strong_consensus = max(home_pct, away_pct) >= 65
        divergence = spread_data.get("sharp_public_divergence", False)

        if strong_consensus or divergence:
            confidence = "high" if strong_consensus and divergence else "medium"

            best_bets.append({
                "game_id": pick.get("game_id"),
                "matchup": pick.get("matchup"),
                "start_time": pick.get("start_time"),
                "pick": {
                    "side": "home" if home_pct > away_pct else "away",
                    "expert_pct": max(home_pct, away_pct),
                    "type": "spread",
                },
                "confidence": confidence,
                "factors": {
                    "strong_consensus": strong_consensus,
                    "sharp_public_divergence": divergence,
                },
            })

    # Sort by confidence
    best_bets.sort(key=lambda x: (x["confidence"] == "high", x["pick"]["expert_pct"]), reverse=True)

    return {
        "sport": sport,
        "date": target_date.date().isoformat(),
        "best_bets": best_bets,
        "count": len(best_bets),
        "source": "covers.com"
    }


# =============================================================================
# Configuration & Admin
# =============================================================================

@router.get("/status")
def get_covers_status():
    """
    Check Covers.com integration status.

    Returns whether scraping is enabled and data freshness info.
    """
    return {
        "scraping_enabled": covers_scraper.is_scraping_enabled(),
        "data_source": "Covers.com" if covers_scraper.is_scraping_enabled() else "Simulated",
        "supported_sports": ["NFL", "NBA", "MLB", "NHL", "NCAAF", "NCAAB"],
        "features": {
            "ats_records": True,
            "ou_trends": True,
            "consensus_picks": True,
            "expert_picks": True,
            "team_trends": True,
        },
        "cache_duration": {
            "ats_records": "4 hours",
            "ou_trends": "4 hours",
            "consensus": "15 minutes",
            "expert_picks": "1 hour",
        },
        "note": "Enable real scraping with COVERS_SCRAPING_ENABLED=true"
    }


@router.post("/refresh/{sport}")
async def refresh_covers_data(
    sport: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Refresh all Covers.com data for a sport.

    Admin endpoint to force refresh cached data.
    """
    if user.subscription_tier != "pro":
        raise HTTPException(status_code=403, detail="Pro subscription required")

    sport = sport.upper()
    if sport not in ["NFL", "NBA", "MLB", "NHL", "NCAAF", "NCAAB"]:
        raise HTTPException(status_code=400, detail="Unsupported sport")

    result = await covers_scraper.refresh_all_data(sport, db)

    return result
