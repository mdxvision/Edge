import asyncio
import sys
import os

# Add app to path
sys.path.append(os.getcwd())

from app.db import SessionLocal
from app.services.nba_stats import refresh_nba_data

def main():
    print("Starting manual NBA data refresh...")
    db = SessionLocal()
    try:
        result = refresh_nba_data(db)
        print("Refresh Result:", result)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()
        print("Done.")

if __name__ == "__main__":
    main()
