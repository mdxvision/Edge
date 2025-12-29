#!/usr/bin/env python3
"""
Monitor and settle tonight's picks when games finish.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import time
from datetime import datetime
from app.db import engine
from sqlalchemy import text

# Our picks for tonight (Dec 27)
PICKS = {
    'Cleveland Cavaliers': {
        'opponent': 'Houston Rockets',
        'type': 'moneyline',
        'odds': 136,
        'units': 1.5,
        'pick_id': None
    },
    'Milwaukee Bucks': {
        'opponent': 'Chicago Bulls',
        'type': 'moneyline',
        'odds': 100,
        'units': 1.0,
        'pick_id': None
    },
    'New York Knicks': {
        'opponent': 'Atlanta Hawks',
        'type': 'spread',
        'line': 6,
        'odds': -110,
        'units': 1.0,
        'pick_id': None
    },
    'Denver Nuggets': {
        'opponent': 'Orlando Magic',
        'type': 'moneyline',
        'odds': -174,
        'units': 1.7,
        'pick_id': None
    },
    'Indiana Pacers': {
        'opponent': 'Miami Heat',
        'type': 'spread',
        'line': 6.5,
        'odds': -110,
        'units': 1.0,
        'pick_id': None
    }
}

def get_pick_ids():
    """Get pick IDs from database."""
    with engine.connect() as conn:
        for team, pick in PICKS.items():
            result = conn.execute(text("""
                SELECT id FROM tracked_picks
                WHERE pick_team LIKE :team
                AND pick_type = :pick_type
                AND status = 'pending'
                ORDER BY created_at DESC
                LIMIT 1
            """), {"team": f"%{team}%", "pick_type": pick['type']})
            row = result.fetchone()
            if row:
                pick['pick_id'] = row[0]
                print(f"Found pick ID {row[0]} for {team}")


def get_game_results():
    """Fetch current game results from API."""
    try:
        resp = requests.get("http://localhost:8000/nba/games?start_date=2025-12-27", timeout=10)
        if resp.status_code == 200:
            return resp.json().get('games', [])
    except Exception as e:
        print(f"Error fetching games: {e}")
    return []


def calculate_result(pick, our_score, opp_score):
    """Calculate if pick won or lost."""
    if pick['type'] == 'moneyline':
        return 'won' if our_score > opp_score else 'lost'
    elif pick['type'] == 'spread':
        # Spread pick: our_score + line > opp_score means we cover
        margin = our_score - opp_score
        return 'won' if margin > -pick['line'] else 'lost'
    return None


def calculate_units_result(status, odds, units):
    """Calculate units won/lost."""
    if status == 'won':
        if odds > 0:
            return units * (odds / 100)
        else:
            return units * (100 / abs(odds))
    else:
        return -units


def settle_pick(pick_id, status, score, units_result):
    """Update pick in database."""
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE tracked_picks
            SET status = :status,
                result_score = :score,
                units_result = :units_result,
                settled_at = :settled_at
            WHERE id = :pick_id
        """), {
            "status": status,
            "score": score,
            "units_result": units_result,
            "settled_at": datetime.utcnow(),
            "pick_id": pick_id
        })
    print(f"  Settled: {status.upper()} ({units_result:+.2f}u)")


def check_and_settle():
    """Check games and settle finished ones."""
    games = get_game_results()
    settled_count = 0

    for game in games:
        home = game['home_team']['name']
        away = game['away_team']['name']
        status = game.get('game_status', '').strip()

        # Check if this is one of our games and it's finished
        for team, pick in PICKS.items():
            if pick['pick_id'] is None:
                continue

            # Match the game
            if not ((team == home or team == away) and pick['opponent'] in [home, away]):
                continue

            # Check if game is final
            if status.lower() != 'final':
                print(f"{away} @ {home}: {status} - Still in progress")
                continue

            # Get scores
            home_score = game.get('home_score', 0) or 0
            away_score = game.get('away_score', 0) or 0

            if not home_score and not away_score:
                print(f"{away} @ {home}: Final but no scores yet")
                continue

            # Determine our score vs opponent score
            if team == home:
                our_score = home_score
                opp_score = away_score
            else:
                our_score = away_score
                opp_score = home_score

            # Calculate result
            result = calculate_result(pick, our_score, opp_score)
            if result:
                score_str = f"{away_score}-{home_score}" if team == home else f"{our_score}-{opp_score}"
                units_result = calculate_units_result(result, pick['odds'], pick['units'])

                print(f"\n{away} @ {home}: FINAL {away_score}-{home_score}")
                print(f"  Pick: {team} {pick['type'].upper()}")
                settle_pick(pick['pick_id'], result, score_str, units_result)

                # Mark as settled so we don't process again
                pick['pick_id'] = None
                settled_count += 1

    return settled_count


def main():
    print("=" * 60)
    print("SETTLING TONIGHT'S PICKS")
    print("=" * 60)
    print()

    # Get pick IDs
    get_pick_ids()
    print()

    # Initial check
    pending = sum(1 for p in PICKS.values() if p['pick_id'] is not None)
    print(f"Monitoring {pending} pending picks...")
    print()

    # Check games
    settled = check_and_settle()

    # Summary
    print()
    print("=" * 60)
    print(f"Settled {settled} picks")

    # Show remaining pending
    remaining = sum(1 for p in PICKS.values() if p['pick_id'] is not None)
    if remaining > 0:
        print(f"{remaining} picks still pending - games in progress")
        print("Run this script again when games finish.")


if __name__ == "__main__":
    main()
