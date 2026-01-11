import asyncio
import sys
import os

# Add app to path
sys.path.append(os.getcwd())

from app.services.data_scheduler import refresh_nhl_live_scores_task
from app.db import SessionLocal, Game, Team

async def main():
    print("Testing NHL Live Score Persistence...")
    
    # 1. Run the task
    result = await refresh_nhl_live_scores_task()
    print(f"Task Result: {result}")
    
    # 2. Verify DB
    db = SessionLocal()
    try:
        # Check specific games mentioned by user
        # Note: Teams might be home or away
        target_teams = ["Kraken", "Wild"]
        
        for team_name in target_teams:
            # First find the team to get its ID safely
            team = db.query(Team).filter(Team.sport == "NHL", Team.name.ilike(f"%{team_name}%")).first()
            if not team:
                print(f"Team {team_name} not found in DB.")
                continue

            # Query games for this team
            games = db.query(Game).filter(
                Game.sport == "NHL",
                (Game.home_team_id == team.id) | (Game.away_team_id == team.id)
            ).order_by(Game.start_time.desc()).limit(3).all()
            
            print(f"--- Games for {team_name} ---")
            for game in games:
                print(f"Game: {game.home_team.name} vs {game.away_team.name}")
                print(f"  Date: {game.start_time}")
                print(f"  Score: {game.current_score}")
                print(f"  Status: {game.status}")
                print(f"  External ID: {game.external_id}")
                print("-" * 20)
             
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
