import sqlite3
import os

DB_PATH = "sports_betting.db"

def migrate_db():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if columns exist
        cursor.execute("PRAGMA table_info(games)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "status" not in columns:
            print("Adding 'status' column to games table...")
            cursor.execute("ALTER TABLE games ADD COLUMN status TEXT DEFAULT 'scheduled'")
        else:
            print("'status' column already exists.")

        if "current_score" not in columns:
            print("Adding 'current_score' column to games table...")
            cursor.execute("ALTER TABLE games ADD COLUMN current_score TEXT")
        else:
            print("'current_score' column already exists.")

        conn.commit()
        print("Migration completed successfully.")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_db()
