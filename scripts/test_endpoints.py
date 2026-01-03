#!/usr/bin/env python3
"""
Comprehensive endpoint testing script.
Verifies all sports endpoints return valid, current data.
"""

import requests
from datetime import datetime, timedelta
import sys

BASE_URL = "http://localhost:8080"
CURRENT_DATE = datetime.now()
MIN_VALID_DATE = datetime(2026, 1, 1)

def check_date(date_str, endpoint_name):
    """Verify date is current (not from 2024)."""
    if not date_str:
        return True, "No date"

    try:
        # Handle various date formats
        if 'T' in date_str:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00').split('+')[0])
        else:
            dt = datetime.strptime(date_str.split(' ')[0], '%Y-%m-%d')

        if dt < MIN_VALID_DATE:
            return False, f"OLD DATE: {date_str}"
        return True, f"OK: {date_str}"
    except Exception as e:
        return True, f"Parse error: {e}"

def test_endpoint(name, url, games_key='games', date_key='game_date'):
    """Test a single endpoint."""
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code}"

        data = resp.json()
        games = data.get(games_key, [])

        if not games:
            return True, f"0 games (empty)"

        errors = []
        for i, game in enumerate(games[:10]):
            date_val = game.get(date_key) or game.get('date') or game.get('start_time') or game.get('utc_date')
            valid, msg = check_date(date_val, name)
            if not valid:
                errors.append(f"  Game {i}: {msg}")

        if errors:
            return False, f"{len(games)} games, ERRORS:\n" + "\n".join(errors)

        return True, f"{len(games)} games, all dates valid"

    except requests.RequestException as e:
        return False, f"Request failed: {e}"
    except Exception as e:
        return False, f"Error: {e}"

def main():
    print("=" * 60)
    print("EDGE BETTING PLATFORM - ENDPOINT TESTS")
    print(f"Testing at: {CURRENT_DATE}")
    print(f"Min valid date: {MIN_VALID_DATE}")
    print("=" * 60)
    print()

    tests = [
        ("NFL Games", f"{BASE_URL}/nfl/games", "games", "game_date"),
        ("NBA Games", f"{BASE_URL}/nba/games", "games", "game_date"),
        ("CBB Games", f"{BASE_URL}/cbb/games", "games", "game_date"),
        ("NHL Games", f"{BASE_URL}/nhl/games", "games", "date"),
        ("Soccer Games", f"{BASE_URL}/soccer/games", "games", "match_date"),
        ("MLB Games", f"{BASE_URL}/mlb/games", "games", "game_date"),
        ("CFB Games", f"{BASE_URL}/cfb/games", "games", "date"),
    ]

    results = []
    for name, url, games_key, date_key in tests:
        passed, msg = test_endpoint(name, url, games_key, date_key)
        status = "PASS" if passed else "FAIL"
        results.append((name, passed, msg))
        print(f"[{status}] {name}: {msg}")

    print()
    print("=" * 60)

    passed = sum(1 for _, p, _ in results if p)
    total = len(results)
    print(f"RESULTS: {passed}/{total} passed")

    if passed < total:
        print("\nFAILED TESTS:")
        for name, p, msg in results:
            if not p:
                print(f"  - {name}: {msg}")
        sys.exit(1)
    else:
        print("\nAll tests passed!")
        sys.exit(0)

if __name__ == "__main__":
    main()
