"""
Add picks for Sunday December 21, 2025.

NFL Week 16 (12 picks), NBA (2 picks), Shadow Soccer (3 picks).

Run with: python -m app.scripts.add_picks_dec21
"""

import sys
import os
import json
import uuid
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db import SessionLocal, TrackedPick, init_db


def create_pick(
    db,
    sport: str,
    away_team: str,
    home_team: str,
    pick: str,
    pick_team: str,
    line_value: float,
    odds: int,
    confidence: float,
    units: float,
    game_time: datetime,
    pick_type: str = "spread",
    note: str = None
):
    """Create a tracked pick."""
    pick_id = f"pick_{uuid.uuid4().hex[:12]}"
    game_id = f"dec21_{away_team.lower().replace(' ', '_')}_{home_team.lower().replace(' ', '_')}"

    # Calculate recommended units based on confidence
    if confidence >= 90:
        recommended_units = 3.0
    elif confidence >= 80:
        recommended_units = 2.0
    elif confidence >= 70:
        recommended_units = 1.5
    elif confidence >= 60:
        recommended_units = 1.0
    else:
        recommended_units = 0.5

    # Create default factors
    factors = {
        "coach_dna": {"score": 55, "detail": f"{pick_team} coach analysis"},
        "referee": {"score": 50, "detail": "Officials pending"},
        "weather": {"score": 50, "detail": "Weather data pending"},
        "line_movement": {"score": 52, "detail": "Line movement tracking"},
        "rest": {"score": 50, "detail": "Rest advantage neutral"},
        "travel": {"score": 50, "detail": "Travel impact neutral"},
        "situational": {"score": 55, "detail": f"{pick_team} situational spot"},
        "public_betting": {"score": 50, "detail": "Public betting data pending"}
    }

    if note:
        factors["note"] = {"score": 0, "detail": note}

    tracked_pick = TrackedPick(
        id=pick_id,
        game_id=game_id,
        sport=sport.upper(),
        home_team=home_team,
        away_team=away_team,
        game_time=game_time,
        pick_type=pick_type,
        pick=pick,
        pick_team=pick_team,
        line_value=line_value,
        odds=odds,
        confidence=confidence,
        recommended_units=recommended_units,
        factors=json.dumps(factors),
        units_wagered=units,
        status="pending"
    )

    db.add(tracked_pick)
    return tracked_pick


def main():
    """Add all picks for December 21, 2025."""
    init_db()
    db = SessionLocal()

    try:
        # Game times for December 21, 2025 (Sunday)
        # NFL early games: 1:00 PM ET
        nfl_early = datetime(2025, 12, 21, 13, 0)
        # NFL late games: 4:05/4:25 PM ET
        nfl_late = datetime(2025, 12, 21, 16, 25)
        # NFL primetime: 8:20 PM ET
        nfl_night = datetime(2025, 12, 21, 20, 20)
        # NBA evening: 7:00 PM ET
        nba_time = datetime(2025, 12, 21, 19, 0)
        # Soccer: Various times (morning/afternoon ET)
        soccer_time = datetime(2025, 12, 21, 11, 0)

        picks_added = []

        # === NFL WEEK 16 (12 picks @ 1.0u each) ===

        # 1. Bills @ Browns - Bills -10.5
        p = create_pick(db, "NFL", "Buffalo Bills", "Cleveland Browns",
                       "Bills -10.5", "Buffalo Bills", -10.5, -110, 65.0, 1.0, nfl_early)
        picks_added.append(p)

        # 2. Bengals @ Dolphins - Dolphins -1.5
        p = create_pick(db, "NFL", "Cincinnati Bengals", "Miami Dolphins",
                       "Dolphins -1.5", "Miami Dolphins", -1.5, -110, 58.0, 1.0, nfl_early)
        picks_added.append(p)

        # 3. Buccaneers @ Panthers - Buccaneers -2.5
        p = create_pick(db, "NFL", "Tampa Bay Buccaneers", "Carolina Panthers",
                       "Buccaneers -2.5", "Tampa Bay Buccaneers", -2.5, -110, 64.0, 1.0, nfl_early)
        picks_added.append(p)

        # 4. Chargers @ Cowboys - Cowboys -1.5
        p = create_pick(db, "NFL", "Los Angeles Chargers", "Dallas Cowboys",
                       "Cowboys -1.5", "Dallas Cowboys", -1.5, -110, 52.0, 1.0, nfl_late)
        picks_added.append(p)

        # 5. Chiefs @ Titans - Chiefs -4.5
        p = create_pick(db, "NFL", "Kansas City Chiefs", "Tennessee Titans",
                       "Chiefs -4.5", "Kansas City Chiefs", -4.5, -110, 66.0, 1.0, nfl_early)
        picks_added.append(p)

        # 6. Vikings @ Giants - Vikings -1.5
        p = create_pick(db, "NFL", "Minnesota Vikings", "New York Giants",
                       "Vikings -1.5", "Minnesota Vikings", -1.5, -110, 60.0, 1.0, nfl_early)
        picks_added.append(p)

        # 7. Jets @ Saints - Saints -4.5
        p = create_pick(db, "NFL", "New York Jets", "New Orleans Saints",
                       "Saints -4.5", "New Orleans Saints", -4.5, -110, 68.0, 1.0, nfl_early)
        picks_added.append(p)

        # 8. Jaguars @ Broncos - Broncos -2.5
        p = create_pick(db, "NFL", "Jacksonville Jaguars", "Denver Broncos",
                       "Broncos -2.5", "Denver Broncos", -2.5, -110, 62.0, 1.0, nfl_late)
        picks_added.append(p)

        # 9. Falcons @ Cardinals - Falcons -1.5
        p = create_pick(db, "NFL", "Atlanta Falcons", "Arizona Cardinals",
                       "Falcons -1.5", "Atlanta Falcons", -1.5, -110, 55.0, 1.0, nfl_late)
        picks_added.append(p)

        # 10. Steelers @ Lions - Lions -7
        p = create_pick(db, "NFL", "Pittsburgh Steelers", "Detroit Lions",
                       "Lions -7", "Detroit Lions", -7.0, -110, 67.0, 1.0, nfl_night)
        picks_added.append(p)

        # 11. Raiders @ Texans - Texans -14.5
        p = create_pick(db, "NFL", "Las Vegas Raiders", "Houston Texans",
                       "Texans -14.5", "Houston Texans", -14.5, -110, 70.0, 1.0, nfl_early)
        picks_added.append(p)

        # 12. Patriots @ Ravens - Ravens -2.5
        p = create_pick(db, "NFL", "New England Patriots", "Baltimore Ravens",
                       "Ravens -2.5", "Baltimore Ravens", -2.5, -110, 63.0, 1.0, nfl_early)
        picks_added.append(p)

        # === NBA (2 picks @ 1.0u each) ===

        # 13. Pacers @ Pelicans - Pelicans -1.5
        p = create_pick(db, "NBA", "Indiana Pacers", "New Orleans Pelicans",
                       "Pelicans -1.5", "New Orleans Pelicans", -1.5, -108, 55.0, 1.0, nba_time)
        picks_added.append(p)

        # 14. Mavericks @ 76ers - 76ers -4.5
        p = create_pick(db, "NBA", "Dallas Mavericks", "Philadelphia 76ers",
                       "76ers -4.5", "Philadelphia 76ers", -4.5, -110, 65.0, 1.0, nba_time)
        picks_added.append(p)

        # === SHADOW TRACKING (3 picks @ 0.0u) ===

        # 15. Aston Villa vs Manchester United - Aston Villa ML
        p = create_pick(db, "SOCCER", "Manchester United", "Aston Villa",
                       "Aston Villa ML", "Aston Villa", 0.0, 108, 60.0, 0.0, soccer_time,
                       pick_type="moneyline",
                       note="SHADOW - Villa on 9-game win streak")
        picks_added.append(p)

        # 16. Villarreal vs Barcelona - Barcelona -0.5
        p = create_pick(db, "SOCCER", "Barcelona", "Villarreal",
                       "Barcelona -0.5", "Barcelona", -0.5, -110, 58.0, 0.0, soccer_time,
                       note="SHADOW - Title race, Barca 7 straight wins")
        picks_added.append(p)

        # 17. Girona vs Atletico Madrid - Atletico Madrid -1.5
        p = create_pick(db, "SOCCER", "Atletico Madrid", "Girona",
                       "Atletico Madrid -1.5", "Atletico Madrid", -1.5, -115, 62.0, 0.0, soccer_time,
                       note="SHADOW - Top 4 battle")
        picks_added.append(p)

        db.commit()

        print(f"\n{'='*60}")
        print(f"PICKS LOGGED FOR SUNDAY DECEMBER 21, 2025")
        print(f"{'='*60}\n")

        nfl_picks = [p for p in picks_added if p.sport == "NFL"]
        nba_picks = [p for p in picks_added if p.sport == "NBA"]
        soccer_picks = [p for p in picks_added if p.sport == "SOCCER"]

        print(f"NFL Week 16: {len(nfl_picks)} picks")
        for p in nfl_picks:
            print(f"  - {p.pick} @ {p.odds} ({p.confidence}% conf, {p.units_wagered}u)")

        print(f"\nNBA: {len(nba_picks)} picks")
        for p in nba_picks:
            print(f"  - {p.pick} @ {p.odds} ({p.confidence}% conf, {p.units_wagered}u)")

        print(f"\nShadow (Soccer): {len(soccer_picks)} picks (0.0u - observation only)")
        for p in soccer_picks:
            print(f"  - {p.pick} @ {p.odds} ({p.confidence}% conf)")

        total_units = sum(p.units_wagered for p in picks_added)
        print(f"\n{'='*60}")
        print(f"TOTAL: {len(picks_added)} picks | {total_units}u wagered")
        print(f"{'='*60}\n")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
