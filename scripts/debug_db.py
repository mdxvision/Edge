from sqlalchemy import create_engine, text
from app.config import DATABASE_URL

def debug_db():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        # Get one recent NBA game
        result = conn.execute(text("SELECT id, home_team_id, away_team_id, start_time, external_id FROM games WHERE sport='NBA' ORDER BY start_time DESC LIMIT 1"))
        row = result.fetchone()
        if row:
            print(f"Found Game: {row}")
            game_id = row[0]
            
            # Manually update its external_id to a 'test_id' we can query
            test_ext_id = "999999999"
            conn.execute(text(f"UPDATE games SET external_id = '{test_ext_id}' WHERE id = {game_id}"))
            conn.commit()
            print(f"Updated Game {game_id} with external_id='{test_ext_id}'")
        else:
            print("No NBA games found in DB")

if __name__ == "__main__":
    debug_db()
