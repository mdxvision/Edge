"""
Social Sentiment API Router

Provides endpoints for social sentiment analysis and public betting data.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.db import get_db
from app.services import social_sentiment, news_monitor

router = APIRouter(prefix="/social", tags=["social"])


@router.get("/sentiment/{team}")
async def get_team_sentiment(
    team: str,
    sport: str = Query("NFL"),
    db: Session = Depends(get_db)
):
    """
    Get Reddit sentiment analysis for a team.

    Returns sentiment score, bullish/bearish breakdown, and key narratives.
    """
    return await social_sentiment.get_reddit_sentiment(team, sport, db)


@router.get("/game/{game_id}")
async def get_game_sentiment(
    game_id: int,
    db: Session = Depends(get_db)
):
    """
    Get complete sentiment analysis for both teams in a game.

    Includes Reddit sentiment, public betting percentages, and fade signals.
    """
    return await social_sentiment.get_sentiment_for_game(game_id, db)


@router.get("/public-betting/{game_id}")
async def get_public_betting(
    game_id: int,
    db: Session = Depends(get_db)
):
    """
    Get public betting percentages for a game.

    Returns bet percentages, money percentages, and sharp side indicators.
    """
    return await social_sentiment.get_public_betting_percentages(game_id, db)


@router.get("/fade-public/{game_id}")
async def get_fade_public_analysis(
    game_id: int,
    db: Session = Depends(get_db)
):
    """
    Get fade-the-public analysis for a game.

    Calculates edge from contrarian betting when public heavily on one side.
    """
    return await social_sentiment.calculate_fade_public_edge(game_id, db)


@router.get("/fade-public")
async def get_todays_fade_plays(
    sport: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get today's fade-the-public plays.

    Returns all games where fading public sentiment is recommended.
    """
    plays = await social_sentiment.get_todays_fade_public_plays(db, sport)
    return {
        "date": "today",
        "sport_filter": sport,
        "plays": plays,
        "count": len(plays)
    }


@router.get("/news")
async def get_breaking_news(
    sport: Optional[str] = Query(None),
    hours: int = Query(6, ge=1, le=48),
    db: Session = Depends(get_db)
):
    """
    Get breaking news feed.

    Returns recent news that could affect betting lines.
    """
    news = await news_monitor.get_breaking_news(sport, hours, db)
    return {
        "hours": hours,
        "sport_filter": sport,
        "news": news,
        "count": len(news)
    }


@router.get("/news/{sport}")
async def get_sport_news(
    sport: str,
    hours: int = Query(6, ge=1, le=48),
    db: Session = Depends(get_db)
):
    """
    Get sport-specific breaking news.
    """
    news = await news_monitor.get_breaking_news(sport, hours, db)
    return {
        "sport": sport,
        "hours": hours,
        "news": news,
        "count": len(news)
    }


@router.get("/news/high-impact")
async def get_high_impact_news(
    sport: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get only high-impact news that significantly affects lines.
    """
    news = await news_monitor.get_high_impact_news(sport, db)
    return {
        "sport_filter": sport,
        "news": news,
        "count": len(news),
        "description": "News items with HIGH impact on betting lines"
    }


@router.get("/injuries/{team}")
async def get_team_injuries(
    team: str,
    db: Session = Depends(get_db)
):
    """
    Get injury report for a team.
    """
    injuries = await news_monitor.get_injury_updates(team, db)
    return {
        "team": team,
        "injuries": injuries,
        "count": len(injuries)
    }


@router.get("/game-news/{home_team}/{away_team}")
async def get_game_news(
    home_team: str,
    away_team: str,
    sport: str = Query("NFL"),
    db: Session = Depends(get_db)
):
    """
    Get all relevant news for a specific game matchup.
    """
    return await news_monitor.get_news_for_game(home_team, away_team, sport, db)
