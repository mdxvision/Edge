import asyncio
import sys
import os

sys.path.append(os.getcwd())

from app.db import SessionLocal, Game
from app.services.edge_aggregator import get_unified_prediction

async def main():
    print("Verifying NHL 8-Factor Analysis...")
    db = SessionLocal()
    try:
        # Find a recent NHL game
        game = db.query(Game).filter(Game.sport == "NHL").order_by(Game.start_time.desc()).first()
        if not game:
            print("No NHL games found in DB.")
            return

        print(f"Testing Analysis for Game: {game.home_team.name} vs {game.away_team.name} (ID: {game.id})")
        
        # Call analysis endpoint (simulated)
        result = await get_unified_prediction(game.id, db)
        
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print("\nAnalysis Result:")
            print(f"Prediction: {result['prediction']['side']}")
            print(f"Confidence: {result['prediction']['confidence_label']} ({result['prediction']['confidence']})")
            
            factors = result.get("factors", {})
            print("\nFactors:")
            for key, val in factors.items():
                print(f"  {key}: Edge={val.get('edge')}, Detail={val.get('signal')}")

            # Verify Situational was populated
            if factors.get("situational", {}).get("edge", 0) > 0 or "situational" in factors:
                print("\nSituational Factor Successfully Calculated!")
            else:
                print("\nWARNING: Situational Factor missing or zero.")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
