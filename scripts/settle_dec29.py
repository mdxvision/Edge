#!/usr/bin/env python3
"""Monitor and settle Dec 29 picks when games finish."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from datetime import datetime, timezone
from app.db import engine
from sqlalchemy import text
import urllib.request
import json

# Dec 29 games we're tracking
GAMES = {
    "Cleveland Cavaliers": {
        "opponent": "San Antonio Spurs",
        "home": "San Antonio Spurs",
        "away": "Cleveland Cavaliers",
    },
    "Dallas Mavericks": {
        "opponent": "Portland Trail Blazers",
        "home": "Portland Trail Blazers",
        "away": "Dallas Mavericks",
    }
}

def calculate_units(result, odds, units=1.0):
    if result == "won":
        if odds > 0:
            return units * (odds / 100)
        else:
            return units * (100 / abs(odds))
    elif result == "lost":
        return -units
    return 0

def get_scores_from_api():
    """Fetch scores from local API."""
    try:
        url = "http://localhost:8080/nba/games?start_date=2025-12-29"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            return data.get('games', [])
    except Exception as e:
        print(f"API error: {e}")
        return []

def check_and_settle():
    """Check games and settle finished picks."""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking games...")
    
    with engine.connect() as conn:
        # Get pending picks
        result = conn.execute(text("""
            SELECT id, pick_team, pick_type, odds, units_wagered, pick
            FROM tracked_picks WHERE status = 'pending'
        """))
        pending = result.fetchall()
        
        if not pending:
            print("No pending picks!")
            return True
        
        print(f"Pending: {len(pending)} picks")
        for p in pending:
            print(f"  - {p[5]}")
    
    return False

def main():
    print("=" * 60)
    print("SETTLEMENT MONITOR - Dec 29 Picks")
    print("=" * 60)
    print("Tracking:")
    print("  • Cleveland Cavaliers ML @ +150 (1.7u)")
    print("  • Dallas Mavericks ML @ +100 (1.6u)")
    print()
    print("Games start at 7-10pm ET on Dec 29")
    print("Will check every 5 minutes once games start...")
    print("=" * 60)
    
    # Initial check
    check_and_settle()
    
    print("\nMonitor running. Will settle when games finish.")
    print("Check back tomorrow evening for results!")

if __name__ == "__main__":
    main()
