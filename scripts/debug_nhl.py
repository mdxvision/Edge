import asyncio
import sys
import os
from datetime import datetime

# Add app to path
sys.path.append(os.getcwd())

from app.services.nhl_stats import get_scoreboard

async def main():
    print("Fetching NHL Scoreboard...")
    games = await get_scoreboard()
    print(f"Found {len(games)} games.")
    
    for game in games:
        print(f"Game: {game['name']}")
        print(f"  Status: {game['status']}")
        print(f"  Score: {game['home_team']['score']} - {game['away_team']['score']}")
        print(f"  Period: {game['period']}")
        print(f"  Clock: {game['clock']}")
        print("-" * 30)

if __name__ == "__main__":
    asyncio.run(main())
