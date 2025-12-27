"""
Settle the soccer picks for December 21, 2025.

Results:
- Aston Villa 2-1 Manchester United → Aston Villa ML WON
- Villarreal 0-2 Barcelona → Barcelona -0.5 WON
- Girona 0-3 Atletico Madrid → Atletico Madrid -1.5 WON

Run with: python -m app.scripts.settle_soccer_dec21
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db import SessionLocal, TrackedPick, init_db
from app.services.edge_tracker import EdgeTracker


def main():
    init_db()
    db = SessionLocal()

    try:
        edge_tracker = EdgeTracker(db)

        # Find and settle the soccer picks
        soccer_picks = db.query(TrackedPick).filter(
            TrackedPick.sport == "SOCCER",
            TrackedPick.status == "pending"
        ).all()

        print(f"Found {len(soccer_picks)} pending soccer picks")

        for pick in soccer_picks:
            print(f"\nProcessing: {pick.pick}")

            # Aston Villa vs Manchester United
            if "Aston Villa" in pick.home_team or "Aston Villa" in pick.away_team:
                # Aston Villa 2-1 Manchester United, Aston Villa ML WON
                result = edge_tracker.settle_pick(
                    pick_id=pick.id,
                    result="won",
                    actual_score="Aston Villa 2, Manchester United 1",
                    spread_result=1,  # Home won by 1
                    total_result=3
                )
                print(f"  Settled: {result}")

            # Barcelona vs Villarreal
            elif "Barcelona" in pick.pick_team:
                # Villarreal 0-2 Barcelona, Barcelona -0.5 WON
                result = edge_tracker.settle_pick(
                    pick_id=pick.id,
                    result="won",
                    actual_score="Villarreal 0, Barcelona 2",
                    spread_result=-2,  # Away won by 2
                    total_result=2
                )
                print(f"  Settled: {result}")

            # Atletico Madrid vs Girona
            elif "Atletico" in pick.pick_team:
                # Girona 0-3 Atletico Madrid, Atletico -1.5 WON
                result = edge_tracker.settle_pick(
                    pick_id=pick.id,
                    result="won",
                    actual_score="Girona 0, Atletico Madrid 3",
                    spread_result=-3,  # Away won by 3
                    total_result=3
                )
                print(f"  Settled: {result}")

        print("\n✓ All soccer picks settled!")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
