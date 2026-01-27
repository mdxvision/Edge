#!/usr/bin/env python3
"""
Seed sample games and odds data for testing picks generation.
Run this when The Odds API quota is exhausted.

Usage: python scripts/seed_odds_data.py
"""

import sys
import os
import random
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import SessionLocal, Game, Market, Line, Team

SPORTSBOOKS = ["DraftKings", "FanDuel", "BetMGM", "Caesars"]

SAMPLE_GAMES = [
    # NBA games
    {"sport": "NBA", "home": "Los Angeles Lakers", "away": "Boston Celtics", "hours_ahead": 6},
    {"sport": "NBA", "home": "Golden State Warriors", "away": "Phoenix Suns", "hours_ahead": 8},
    {"sport": "NBA", "home": "Miami Heat", "away": "Milwaukee Bucks", "hours_ahead": 24},
    {"sport": "NBA", "home": "Denver Nuggets", "away": "Dallas Mavericks", "hours_ahead": 30},
    # NFL games
    {"sport": "NFL", "home": "Kansas City Chiefs", "away": "Buffalo Bills", "hours_ahead": 12},
    {"sport": "NFL", "home": "Philadelphia Eagles", "away": "San Francisco 49ers", "hours_ahead": 36},
    # NHL games
    {"sport": "NHL", "home": "Toronto Maple Leafs", "away": "Montreal Canadiens", "hours_ahead": 10},
    {"sport": "NHL", "home": "New York Rangers", "away": "Boston Bruins", "hours_ahead": 26},
]


def get_or_create_team(db, sport: str, name: str):
    """Get existing team or create new one."""
    team = db.query(Team).filter(Team.sport == sport, Team.name == name).first()
    if not team:
        team = Team(sport=sport, name=name, rating=1500 + random.randint(-100, 100))
        db.add(team)
        db.flush()
    return team


def generate_realistic_odds():
    """Generate realistic American odds for a moneyline."""
    # Favorite vs underdog
    if random.random() > 0.5:
        # Home team favorite
        home_odds = random.choice([-110, -115, -120, -130, -140, -150, -160, -180, -200])
        # Calculate corresponding underdog odds
        if home_odds == -110:
            away_odds = random.choice([-105, -110, +100, +105])
        elif home_odds == -120:
            away_odds = random.choice([+100, +105, +110])
        elif home_odds <= -150:
            away_odds = random.choice([+120, +130, +140, +150])
        else:
            away_odds = random.choice([+105, +110, +115, +120])
    else:
        # Home team underdog
        home_odds = random.choice([+100, +110, +120, +130, +140, +150])
        away_odds = random.choice([-110, -115, -120, -130, -140, -150])

    return home_odds, away_odds


def create_sample_games(db):
    """Create sample games for the next 48 hours."""
    now = datetime.now(timezone.utc)
    games_created = 0

    for game_info in SAMPLE_GAMES:
        start_time = now + timedelta(hours=game_info["hours_ahead"])

        # Check if similar game exists
        home_team = get_or_create_team(db, game_info["sport"], game_info["home"])
        away_team = get_or_create_team(db, game_info["sport"], game_info["away"])

        # Check for existing game with same teams and close start time
        existing = db.query(Game).filter(
            Game.sport == game_info["sport"],
            Game.home_team_id == home_team.id,
            Game.away_team_id == away_team.id,
            Game.start_time >= now,
            Game.start_time <= now + timedelta(days=3)
        ).first()

        if not existing:
            game = Game(
                sport=game_info["sport"],
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                start_time=start_time,
                venue=f"{game_info['home']} Arena",
                league=game_info["sport"]
            )
            db.add(game)
            games_created += 1

    db.flush()
    print(f"Created {games_created} sample games")
    return games_created


def seed_odds_for_games():
    db = SessionLocal()

    try:
        # First create sample games
        create_sample_games(db)

        # Get games in the next 48 hours without markets
        now = datetime.now(timezone.utc)
        end = now + timedelta(days=2)

        games = db.query(Game).filter(
            Game.start_time >= now,
            Game.start_time <= end
        ).all()

        games_without_markets = []
        for game in games:
            existing_markets = db.query(Market).filter(Market.game_id == game.id).count()
            if existing_markets == 0:
                games_without_markets.append(game)

        print(f"Found {len(games_without_markets)} games without odds in the next 48 hours")

        markets_created = 0
        lines_created = 0

        for game in games_without_markets:
            home_ml, away_ml = generate_realistic_odds()

            # Create moneyline markets
            home_market = Market(
                game_id=game.id,
                market_type="moneyline",
                description=f"Moneyline - {game.sport}",
                selection="home"
            )
            away_market = Market(
                game_id=game.id,
                market_type="moneyline",
                description=f"Moneyline - {game.sport}",
                selection="away"
            )

            db.add(home_market)
            db.add(away_market)
            db.flush()
            markets_created += 2

            # Add lines from multiple sportsbooks
            for book in SPORTSBOOKS[:2]:  # Use 2 sportsbooks per game
                # Home line with slight variation
                home_line = Line(
                    market_id=home_market.id,
                    sportsbook=book,
                    odds_type="american",
                    american_odds=home_ml + random.choice([-5, 0, 5])
                )
                away_line = Line(
                    market_id=away_market.id,
                    sportsbook=book,
                    odds_type="american",
                    american_odds=away_ml + random.choice([-5, 0, 5])
                )
                db.add(home_line)
                db.add(away_line)
                lines_created += 2

            # Create spread market for team sports
            if game.sport in ["NFL", "NBA", "NHL", "MLB", "CFB", "CBB", "SOCCER"]:
                spread_value = random.choice([1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5])

                home_spread = Market(
                    game_id=game.id,
                    market_type="spread",
                    description=f"Point Spread - {game.sport}",
                    selection="home"
                )
                away_spread = Market(
                    game_id=game.id,
                    market_type="spread",
                    description=f"Point Spread - {game.sport}",
                    selection="away"
                )

                db.add(home_spread)
                db.add(away_spread)
                db.flush()
                markets_created += 2

                for book in SPORTSBOOKS[:2]:
                    home_spread_line = Line(
                        market_id=home_spread.id,
                        sportsbook=book,
                        odds_type="american",
                        line_value=-spread_value,
                        american_odds=-110 + random.choice([-5, 0, 5])
                    )
                    away_spread_line = Line(
                        market_id=away_spread.id,
                        sportsbook=book,
                        odds_type="american",
                        line_value=spread_value,
                        american_odds=-110 + random.choice([-5, 0, 5])
                    )
                    db.add(home_spread_line)
                    db.add(away_spread_line)
                    lines_created += 2

            # Create total market
            if game.sport == "NBA":
                total = random.choice([210.5, 215.5, 220.5, 225.5, 230.5])
            elif game.sport == "NFL":
                total = random.choice([40.5, 43.5, 45.5, 47.5, 50.5])
            elif game.sport == "NHL":
                total = random.choice([5.5, 6.0, 6.5])
            elif game.sport == "MLB":
                total = random.choice([7.5, 8.0, 8.5, 9.0])
            else:
                total = random.choice([2.5, 3.0, 3.5])  # Soccer

            over_market = Market(
                game_id=game.id,
                market_type="total",
                description=f"Total Points - {game.sport}",
                selection="over"
            )
            under_market = Market(
                game_id=game.id,
                market_type="total",
                description=f"Total Points - {game.sport}",
                selection="under"
            )

            db.add(over_market)
            db.add(under_market)
            db.flush()
            markets_created += 2

            for book in SPORTSBOOKS[:2]:
                over_line = Line(
                    market_id=over_market.id,
                    sportsbook=book,
                    odds_type="american",
                    line_value=total,
                    american_odds=-110 + random.choice([-5, 0, 5])
                )
                under_line = Line(
                    market_id=under_market.id,
                    sportsbook=book,
                    odds_type="american",
                    line_value=total,
                    american_odds=-110 + random.choice([-5, 0, 5])
                )
                db.add(over_line)
                db.add(under_line)
                lines_created += 2

        db.commit()
        print(f"Created {markets_created} markets and {lines_created} lines")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_odds_for_games()
