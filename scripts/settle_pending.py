#!/usr/bin/env python3
"""Monitor and settle pending picks when games finish."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import time
from datetime import datetime, timezone
from app.db import engine
from sqlalchemy import text

def get_nba_scores():
    """Fetch current NBA scores."""
    try:
        resp = requests.get("http://localhost:8080/nba/games?start_date=2025-12-28", timeout=10)
        if resp.status_code == 200:
            return resp.json().get('games', [])
    except Exception as e:
        print(f"Error fetching games: {e}")
    return []

def calculate_units(result, odds, units=1.0):
    if result == "won":
        if odds > 0:
            return units * (odds / 100)
        else:
            return units * (100 / abs(odds))
    elif result == "lost":
        return -units
    return 0

def settle_pick(conn, pick_id, result, score, odds, units):
    units_result = calculate_units(result, odds, units)
    conn.execute(text("""
        UPDATE tracked_picks
        SET status = :status,
            result_score = :score,
            units_result = :units_result,
            settled_at = :settled_at
        WHERE id = :pick_id
    """), {
        "status": result,
        "score": score,
        "units_result": round(units_result, 2),
        "settled_at": datetime.now(timezone.utc),
        "pick_id": pick_id
    })
    return units_result

def check_and_settle():
    """Check games and settle finished picks."""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Checking for finished games...")
    
    with engine.begin() as conn:
        # Get pending picks
        result = conn.execute(text("""
            SELECT id, pick_team, pick_type, odds, units_wagered, pick, line_value
            FROM tracked_picks WHERE status = 'pending'
        """))
        pending = result.fetchall()
        
        if not pending:
            print("No pending picks!")
            return True
        
        print(f"Pending: {len(pending)} picks")
        
        # Get game scores from web
        games = get_nba_scores()
        
        settled = 0
        for pick in pending:
            pick_id, pick_team, pick_type, odds, units, pick_desc, line_value = pick
            units = units or 1.0
            
            # Find matching game
            for game in games:
                home = game['home_team']['name']
                away = game['away_team']['name']
                status = game.get('game_status', '').strip().lower()
                
                # Check if this pick matches the game
                if pick_team not in [home, away]:
                    continue
                
                if 'final' not in status:
                    print(f"  {pick_desc}: Game still in progress ({status})")
                    continue
                
                # Get scores (need to fetch from API with scores)
                home_score = game.get('home_score', 0) or 0
                away_score = game.get('away_score', 0) or 0
                
                if not home_score and not away_score:
                    print(f"  {pick_desc}: Final but no scores yet")
                    continue
                
                # Determine result
                if pick_team == home:
                    our_score, opp_score = home_score, away_score
                else:
                    our_score, opp_score = away_score, home_score
                
                score_str = f"{away} {away_score} - {home} {home_score}"
                
                if pick_type == "moneyline":
                    result = "won" if our_score > opp_score else "lost"
                elif pick_type == "spread":
                    margin = our_score - opp_score
                    # line_value is from our team's perspective
                    # e.g., Lakers -13.5 means Lakers need to win by more than 13.5
                    # Kings +5.5 means Kings can lose by up to 5.5
                    if line_value < 0:  # Favorite (e.g., -13.5)
                        result = "won" if margin > abs(line_value) else "lost"
                    else:  # Underdog (e.g., +5.5)
                        result = "won" if margin > -line_value else "lost"
                else:
                    continue
                
                units_result = settle_pick(conn, pick_id, result, score_str, odds, units)
                icon = "✓" if result == "won" else "✗"
                print(f"  {icon} {pick_desc}: {result.upper()} | {units_result:+.2f}u")
                settled += 1
                break
        
        # Check remaining
        result = conn.execute(text("SELECT COUNT(*) FROM tracked_picks WHERE status = 'pending'"))
        remaining = result.scalar()
        
        print(f"\nSettled: {settled} | Remaining: {remaining}")
        return remaining == 0

def main():
    print("=" * 60)
    print("MONITORING PENDING PICKS")
    print("=" * 60)
    print("Will check every 2 minutes until all games finish...")
    print("Press Ctrl+C to stop")
    
    while True:
        all_done = check_and_settle()
        if all_done:
            print("\n✓ All picks settled!")
            break
        time.sleep(120)  # Check every 2 minutes

if __name__ == "__main__":
    main()
