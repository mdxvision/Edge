import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.services.nba_stats import get_live_nba_scores
from app.services.data_scheduler import refresh_nba_live_scores_task

async def verify():
    print("1. Testing get_live_nba_scores()...")
    try:
        live_data = get_live_nba_scores()
        print(f"   Success! Received {len(live_data)} live/active games.")
        if live_data:
            print(f"   Sample data: {live_data[0]}")
        else:
            print("   (No live games currently active, which is expected if no games are on)")
    except Exception as e:
        print(f"   FAILED: {e}")
        return

    print("\n2. Testing refresh_nba_live_scores_task()...")
    try:
        result = await refresh_nba_live_scores_task()
        print(f"   Success! Result: {result}")
    except Exception as e:
        print(f"   FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(verify())
