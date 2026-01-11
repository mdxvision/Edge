import asyncio
import httpx
import sys
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8080"

async def test_endpoint(client, url, name, params=None):
    print(f"\n--- Testing {name} ---")
    print(f"URL: {url}")
    if params:
        print(f"Params: {params}")
        
    try:
        response = await client.get(url, params=params)
        print(f"Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error: {response.text}")
            return False
            
        data = response.json()
        
        # Handle different response structures
        if "games" in data:
            games = data["games"]
        elif "matches" in data:
            games = data["matches"]
        else:
            print("Warning: Could not find 'games' or 'matches' list in response")
            print(f"Keys found: {list(data.keys())}")
            return True # Pass but with warning
            
        count = len(games)
        print(f"Games found: {count}")
        
        # Analyze statuses
        statuses = {}
        for game in games:
            status = game.get("status", "Unknown")
            statuses[status] = statuses.get(status, 0) + 1
            
            # Print first finished game as sample
            if status in ["Final", "STATUS_FINAL", "FT", "Finished"] and statuses[status] == 1:
                print("Sample Finished Game:")
                print(f"  ID: {game.get('id') or game.get('game_id')}")
                home = game.get('home_team', {}).get('name')
                away = game.get('away_team', {}).get('name')
                print(f"  Matchup: {away} @ {home}")
                print(f"  Score: {game.get('away_team', {}).get('score')} - {game.get('home_team', {}).get('score')}")

        print("Status Breakdown:")
        for s, c in statuses.items():
            print(f"  {s}: {c}")
            
        if count > 0:
            return True
        else:
            print("Note: Zero games returned (might be expected for off-season/no-games days)")
            return True
            
    except Exception as e:
        print(f"Exception calling endpoint: {e}")
        return False

async def main():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        
        # 1. NBA (Active Season)
        # Should show today's games, including finished ones if any
        await test_endpoint(client, "/nba/games", "NBA Today", params={"include_finished": "true"})
        
        # 2. NHL (Active Season)
        await test_endpoint(client, "/nhl/games", "NHL Today")
        
        # 3. CBB (Active Season)
        await test_endpoint(client, "/cbb/games", "CBB Today")
        
        # 4. NFL (Playoffs/Late Season)
        # Check specific date if known, or just default
        await test_endpoint(client, "/nfl/games", "NFL Current Week")
        
        # 5. MLB (Off-Season)
        # Query a chaotic date: Oct 25, 2024 (World Series Game 1: Dodgers vs Yankees)
        await test_endpoint(
            client, 
            "/mlb/games", 
            "MLB Historic (World Series G1)", 
            params={"start_date": "2024-10-25", "end_date": "2024-10-25"}
        )
        
        # 6. Soccer (Active)
        await test_endpoint(client, "/soccer/games", "Soccer Today")

if __name__ == "__main__":
    asyncio.run(main())
