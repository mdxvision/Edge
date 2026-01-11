from sqlalchemy import create_engine, text
from app.config import DATABASE_URL

def migrate():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        # Check if external_id column exists
        try:
            conn.execute(text("SELECT external_id FROM games LIMIT 1"))
            print("Column 'external_id' already exists in 'games' table.")
        except Exception:
            print("Adding 'external_id' column to 'games' table...")
            conn.execute(text("ALTER TABLE games ADD COLUMN external_id VARCHAR(100)"))
            conn.execute(text("CREATE INDEX ix_games_external_id ON games (external_id)"))
            conn.commit()
            print("Migration successful: added 'external_id' column.")

if __name__ == "__main__":
    migrate()
