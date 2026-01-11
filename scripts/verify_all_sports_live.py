import asyncio
import sys
import os

sys.path.append(os.getcwd())

from app.services.data_scheduler import refresh_nfl_live_scores_task, refresh_cbb_live_scores_task
from app.services.situations import analyze_game_situation
from app.db import SessionLocal, Game, CBBGame

async def main():
    print("Verifying Live Score Tasks...")
    
    # NFL
    print("\n1. Running NFL Live Score Task...")
    try:
        res = await refresh_nfl_live_scores_task()
        print(f"   Result: {res}")
    except Exception as e:
        print(f"   Error: {e}")

    # CBB
    print("\n2. Running CBB Live Score Task...")
    try:
        res = await refresh_cbb_live_scores_task()
        print(f"   Result: {res}")
    except Exception as e:
        print(f"   Error: {e}")
        
    print("\nVerifying CBB Situational Analysis (Dry Run)...")
    # Finding a CBB game
    db = SessionLocal()
    try:
        # Just check if we can import logic without error
        from app.services.cbb_stats import calculate_rest_days
        print("   Successfully imported calculate_rest_days")
        
    except Exception as e:
        print(f"   Error importing CBB stats: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
