#!/usr/bin/env python3
"""
Manual Odds Entry Script

Adds betting lines manually for games when API quota is exhausted.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, date
from app.db import engine, Game, Team, Market, Line
from sqlalchemy import text
from sqlalchemy.orm import Session


def get_or_create_game(conn, sport: str, home_team: str, away_team: str, start_time: datetime, venue: str = None):
    """Get existing game or create new one."""

    # Try to find existing game
    result = conn.execute(text("""
        SELECT g.id FROM games g
        JOIN teams ht ON g.home_team_id = ht.id
        JOIN teams at ON g.away_team_id = at.id
        WHERE g.sport = :sport
        AND ht.name LIKE :home_team
        AND at.name LIKE :away_team
        AND DATE(g.start_time) = DATE(:start_time)
    """), {
        "sport": sport,
        "home_team": f"%{home_team}%",
        "away_team": f"%{away_team}%",
        "start_time": start_time
    })

    row = result.fetchone()
    if row:
        return row[0]

    # Get or create teams
    home_team_id = get_or_create_team(conn, sport, home_team)
    away_team_id = get_or_create_team(conn, sport, away_team)

    # Create game
    result = conn.execute(text("""
        INSERT INTO games (sport, home_team_id, away_team_id, start_time, venue, league)
        VALUES (:sport, :home_team_id, :away_team_id, :start_time, :venue, :league)
        RETURNING id
    """), {
        "sport": sport,
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
        "start_time": start_time,
        "venue": venue or "TBD",
        "league": sport
    })

    return result.fetchone()[0]


def get_or_create_team(conn, sport: str, team_name: str):
    """Get existing team or create new one."""
    result = conn.execute(text("""
        SELECT id FROM teams WHERE sport = :sport AND name LIKE :name
    """), {"sport": sport, "name": f"%{team_name}%"})

    row = result.fetchone()
    if row:
        return row[0]

    # Create team
    short_name = team_name.split()[-1][:3].upper() if team_name else "UNK"
    result = conn.execute(text("""
        INSERT INTO teams (sport, name, short_name, rating)
        VALUES (:sport, :name, :short_name, 1500)
        RETURNING id
    """), {"sport": sport, "name": team_name, "short_name": short_name})

    return result.fetchone()[0]


def add_odds(conn, game_id: int, sportsbook: str, spread: float = None, spread_odds: int = -110,
             home_ml: int = None, away_ml: int = None, total: float = None,
             over_odds: int = -110, under_odds: int = -110):
    """Add odds for a game."""

    now = datetime.utcnow()

    # Add spread
    if spread is not None:
        # Home spread
        market_id = create_market(conn, game_id, "spread", "home")
        conn.execute(text("""
            INSERT INTO lines (market_id, sportsbook, odds_type, line_value, american_odds, created_at)
            VALUES (:market_id, :sportsbook, 'spread', :line_value, :odds, :created_at)
        """), {"market_id": market_id, "sportsbook": sportsbook, "line_value": spread,
               "odds": spread_odds, "created_at": now})

        # Away spread (opposite)
        market_id = create_market(conn, game_id, "spread", "away")
        conn.execute(text("""
            INSERT INTO lines (market_id, sportsbook, odds_type, line_value, american_odds, created_at)
            VALUES (:market_id, :sportsbook, 'spread', :line_value, :odds, :created_at)
        """), {"market_id": market_id, "sportsbook": sportsbook, "line_value": -spread,
               "odds": spread_odds, "created_at": now})

    # Add moneylines
    if home_ml is not None:
        market_id = create_market(conn, game_id, "moneyline", "home")
        conn.execute(text("""
            INSERT INTO lines (market_id, sportsbook, odds_type, line_value, american_odds, created_at)
            VALUES (:market_id, :sportsbook, 'moneyline', NULL, :odds, :created_at)
        """), {"market_id": market_id, "sportsbook": sportsbook, "odds": home_ml, "created_at": now})

    if away_ml is not None:
        market_id = create_market(conn, game_id, "moneyline", "away")
        conn.execute(text("""
            INSERT INTO lines (market_id, sportsbook, odds_type, line_value, american_odds, created_at)
            VALUES (:market_id, :sportsbook, 'moneyline', NULL, :odds, :created_at)
        """), {"market_id": market_id, "sportsbook": sportsbook, "odds": away_ml, "created_at": now})

    # Add totals
    if total is not None:
        market_id = create_market(conn, game_id, "total", "over")
        conn.execute(text("""
            INSERT INTO lines (market_id, sportsbook, odds_type, line_value, american_odds, created_at)
            VALUES (:market_id, :sportsbook, 'total', :line_value, :odds, :created_at)
        """), {"market_id": market_id, "sportsbook": sportsbook, "line_value": total,
               "odds": over_odds, "created_at": now})

        market_id = create_market(conn, game_id, "total", "under")
        conn.execute(text("""
            INSERT INTO lines (market_id, sportsbook, odds_type, line_value, american_odds, created_at)
            VALUES (:market_id, :sportsbook, 'total', :line_value, :odds, :created_at)
        """), {"market_id": market_id, "sportsbook": sportsbook, "line_value": total,
               "odds": under_odds, "created_at": now})


def create_market(conn, game_id: int, market_type: str, selection: str):
    """Create or get market."""
    result = conn.execute(text("""
        SELECT id FROM markets WHERE game_id = :game_id AND market_type = :market_type AND selection = :selection
    """), {"game_id": game_id, "market_type": market_type, "selection": selection})

    row = result.fetchone()
    if row:
        return row[0]

    result = conn.execute(text("""
        INSERT INTO markets (game_id, market_type, selection)
        VALUES (:game_id, :market_type, :selection)
        RETURNING id
    """), {"game_id": game_id, "market_type": market_type, "selection": selection})

    return result.fetchone()[0]


def add_nba_game_odds(home_team: str, away_team: str, start_time: str,
                      spread: float, home_ml: int, away_ml: int, total: float,
                      sportsbook: str = "Consensus"):
    """Add NBA game with odds."""

    with engine.begin() as conn:
        # Parse start time
        if isinstance(start_time, str):
            if ":" in start_time:
                # Time string like "7:00 PM"
                today = date.today()
                try:
                    time_obj = datetime.strptime(start_time.upper().replace(" ", ""), "%I:%M%p")
                    start_dt = datetime.combine(today, time_obj.time())
                except:
                    start_dt = datetime.combine(today, datetime.min.time())
            else:
                start_dt = datetime.now()
        else:
            start_dt = start_time

        game_id = get_or_create_game(conn, "NBA", home_team, away_team, start_dt)
        add_odds(conn, game_id, sportsbook, spread=spread, home_ml=home_ml, away_ml=away_ml, total=total)

        print(f"Added: {away_team} @ {home_team}")
        print(f"  Spread: {home_team} {spread:+.1f}")
        print(f"  ML: {home_team} {home_ml:+d} | {away_team} {away_ml:+d}")
        print(f"  Total: {total}")
        print()

        return game_id


if __name__ == "__main__":
    print("=" * 60)
    print("MANUAL ODDS ENTRY - NBA Games for Today")
    print("=" * 60)
    print()
    print("Use add_nba_game_odds() to add games:")
    print()
    print('add_nba_game_odds(')
    print('    home_team="Boston Celtics",')
    print('    away_team="Miami Heat",')
    print('    start_time="7:00 PM",')
    print('    spread=-6.5,  # Home team spread')
    print('    home_ml=-250,')
    print('    away_ml=+210,')
    print('    total=215.5')
    print(')')
