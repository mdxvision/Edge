#!/usr/bin/env python3
"""
Refresh games and odds from The Odds API.

This script:
1. Clears old games from the database
2. Fetches fresh games from The Odds API
3. Stores them in the database for the recommendations engine
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import SessionLocal, Game, Market, Line, Team, BetRecommendation, UnifiedPrediction, OddsSnapshot
from app.services.odds_api import fetch_and_store_odds, is_odds_api_configured

SPORTS_TO_FETCH = ["NFL", "NBA", "MLB", "NHL", "NCAA_FOOTBALL", "NCAA_BASKETBALL", "SOCCER"]


async def clear_old_games(db):
    """Clear games older than 24 hours ago."""
    cutoff = datetime.utcnow() - timedelta(hours=24)

    # First delete dependent records
    old_games = db.query(Game).filter(Game.start_time < cutoff).all()
    old_game_ids = [g.id for g in old_games]

    if old_game_ids:
        # Delete unified predictions first (foreign key constraint)
        db.query(UnifiedPrediction).filter(UnifiedPrediction.game_id.in_(old_game_ids)).delete(synchronize_session=False)

        # Delete odds snapshots
        db.query(OddsSnapshot).filter(OddsSnapshot.game_id.in_(old_game_ids)).delete(synchronize_session=False)

        # Delete markets and lines for old games
        old_markets = db.query(Market).filter(Market.game_id.in_(old_game_ids)).all()
        old_market_ids = [m.id for m in old_markets]

        if old_market_ids:
            db.query(Line).filter(Line.market_id.in_(old_market_ids)).delete(synchronize_session=False)

        db.query(Market).filter(Market.game_id.in_(old_game_ids)).delete(synchronize_session=False)
        db.query(Game).filter(Game.id.in_(old_game_ids)).delete(synchronize_session=False)
        db.commit()

        print(f"Cleared {len(old_game_ids)} old games from database")
    else:
        print("No old games to clear")


async def fetch_all_sports(db):
    """Fetch games from all configured sports."""
    if not is_odds_api_configured():
        print("ERROR: THE_ODDS_API_KEY is not configured!")
        return 0

    total_games = 0

    for sport in SPORTS_TO_FETCH:
        try:
            count = await fetch_and_store_odds(db, sport)
            print(f"Fetched {count} games for {sport}")
            total_games += count
        except Exception as e:
            print(f"Error fetching {sport}: {e}")

    return total_games


async def show_upcoming_games(db):
    """Show games currently in the database."""
    now = datetime.utcnow()
    end = now + timedelta(hours=48)

    games = db.query(Game).filter(
        Game.start_time >= now,
        Game.start_time <= end
    ).order_by(Game.start_time).all()

    print(f"\n=== {len(games)} upcoming games in next 48 hours ===")

    for game in games:
        home_team = db.query(Team).filter(Team.id == game.home_team_id).first()
        away_team = db.query(Team).filter(Team.id == game.away_team_id).first()

        home_name = home_team.name if home_team else "Unknown"
        away_name = away_team.name if away_team else "Unknown"

        print(f"{game.sport}: {away_name} @ {home_name} - {game.start_time}")


async def main():
    print("=" * 60)
    print("REFRESHING ODDS DATA FROM THE ODDS API")
    print("=" * 60)

    db = SessionLocal()

    try:
        # Clear old games
        await clear_old_games(db)

        # Fetch fresh games
        total = await fetch_all_sports(db)
        print(f"\nTotal new games fetched: {total}")

        # Show upcoming games
        await show_upcoming_games(db)

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
