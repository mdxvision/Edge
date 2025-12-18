"""
Seed script for Coach DNA database.

Populates the database with historical coach data and situational records.
Run with: python -m app.scripts.seed_coaches
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db import SessionLocal, Coach, CoachSituationalRecord, CoachTendency, init_db


def create_coach(
    db,
    name: str,
    sport: str,
    current_team: str,
    years_exp: int,
    career_wins: int,
    career_losses: int,
    ats_wins: int,
    ats_losses: int,
    ats_pushes: int,
    over_wins: int,
    under_wins: int
) -> Coach:
    """Create or update a coach record."""
    existing = db.query(Coach).filter(Coach.name == name, Coach.sport == sport).first()

    if existing:
        existing.current_team = current_team
        existing.years_experience = years_exp
        existing.career_wins = career_wins
        existing.career_losses = career_losses
        existing.career_ats_wins = ats_wins
        existing.career_ats_losses = ats_losses
        existing.career_ats_pushes = ats_pushes
        existing.career_over_wins = over_wins
        existing.career_under_wins = under_wins
        return existing

    coach = Coach(
        name=name,
        sport=sport,
        current_team=current_team,
        years_experience=years_exp,
        career_wins=career_wins,
        career_losses=career_losses,
        career_ats_wins=ats_wins,
        career_ats_losses=ats_losses,
        career_ats_pushes=ats_pushes,
        career_over_wins=over_wins,
        career_under_wins=under_wins
    )
    db.add(coach)
    return coach


def add_situational_record(
    db,
    coach: Coach,
    situation: str,
    wins: int,
    losses: int,
    pushes: int,
    ats_wins: int,
    ats_losses: int,
    roi: float = None
):
    """Add or update a situational record."""
    existing = db.query(CoachSituationalRecord).filter(
        CoachSituationalRecord.coach_id == coach.id,
        CoachSituationalRecord.situation == situation
    ).first()

    total_games = wins + losses + pushes

    if existing:
        existing.wins = wins
        existing.losses = losses
        existing.pushes = pushes
        existing.ats_wins = ats_wins
        existing.ats_losses = ats_losses
        existing.total_games = total_games
        existing.roi_percentage = roi
        return existing

    record = CoachSituationalRecord(
        coach_id=coach.id,
        situation=situation,
        wins=wins,
        losses=losses,
        pushes=pushes,
        ats_wins=ats_wins,
        ats_losses=ats_losses,
        total_games=total_games,
        roi_percentage=roi
    )
    db.add(record)
    return record


def add_tendency(
    db,
    coach: Coach,
    tendency_type: str,
    value: float,
    league_avg: float,
    percentile: int,
    notes: str = None
):
    """Add or update a coach tendency."""
    existing = db.query(CoachTendency).filter(
        CoachTendency.coach_id == coach.id,
        CoachTendency.tendency_type == tendency_type
    ).first()

    if existing:
        existing.value = value
        existing.league_average = league_avg
        existing.percentile = percentile
        existing.notes = notes
        return existing

    tendency = CoachTendency(
        coach_id=coach.id,
        tendency_type=tendency_type,
        value=value,
        league_average=league_avg,
        percentile=percentile,
        notes=notes
    )
    db.add(tendency)
    return tendency


def seed_nfl_coaches(db):
    """Seed NFL coaches with realistic data."""
    print("Seeding NFL coaches...")

    # Andy Reid - Kansas City Chiefs
    coach = create_coach(db, "Andy Reid", "NFL", "Kansas City Chiefs", 26,
                         career_wins=267, career_losses=142, ats_wins=145, ats_losses=120, ats_pushes=5,
                         over_wins=130, under_wins=135)
    db.flush()
    add_situational_record(db, coach, "as_underdog", 35, 20, 0, 38, 17, 15.2)
    add_situational_record(db, coach, "as_favorite", 180, 85, 0, 107, 103, 2.1)
    add_situational_record(db, coach, "primetime", 52, 28, 0, 48, 32, 8.5)
    add_situational_record(db, coach, "after_bye_week", 18, 6, 0, 16, 8, 12.5)
    add_situational_record(db, coach, "in_playoffs", 25, 10, 0, 22, 13, 9.8)
    add_situational_record(db, coach, "after_loss", 45, 30, 0, 42, 33, 5.2)
    add_situational_record(db, coach, "monday_night", 22, 12, 0, 20, 14, 7.8)
    add_tendency(db, coach, "4th_down_aggressiveness", 72.5, 55.0, 85, "Very aggressive on 4th down")
    add_tendency(db, coach, "red_zone_td_rate", 62.8, 56.2, 78, "Above average red zone efficiency")

    # Bill Belichick - Free Agent (formerly Patriots)
    coach = create_coach(db, "Bill Belichick", "NFL", "Free Agent", 29,
                         career_wins=302, career_losses=165, ats_wins=158, ats_losses=140, ats_pushes=8,
                         over_wins=145, under_wins=160)
    db.flush()
    add_situational_record(db, coach, "as_favorite", 220, 95, 0, 125, 130, -1.8)
    add_situational_record(db, coach, "as_big_favorite", 85, 28, 0, 48, 65, -8.5)
    add_situational_record(db, coach, "after_bye_week", 22, 4, 0, 20, 6, 18.5)
    add_situational_record(db, coach, "primetime", 58, 32, 0, 52, 38, 6.8)
    add_situational_record(db, coach, "in_playoffs", 31, 13, 0, 25, 19, 5.2)
    add_situational_record(db, coach, "vs_division", 72, 35, 0, 58, 49, 4.1)
    add_situational_record(db, coach, "after_loss", 55, 25, 0, 48, 32, 8.5)
    add_tendency(db, coach, "defensive_scheme_complexity", 92.0, 65.0, 98, "Most complex defensive schemes")
    add_tendency(db, coach, "situational_preparation", 95.0, 70.0, 99, "Elite game preparation")

    # Sean McVay - Los Angeles Rams
    coach = create_coach(db, "Sean McVay", "NFL", "Los Angeles Rams", 8,
                         career_wins=75, career_losses=43, ats_wins=58, ats_losses=55, ats_pushes=5,
                         over_wins=65, under_wins=48)
    db.flush()
    add_situational_record(db, coach, "as_favorite", 55, 28, 0, 38, 42, -3.5)
    add_situational_record(db, coach, "primetime", 18, 10, 0, 16, 12, 5.8)
    add_situational_record(db, coach, "monday_night", 8, 4, 0, 8, 4, 12.5)
    add_situational_record(db, coach, "after_bye_week", 6, 1, 0, 5, 2, 15.0)
    add_situational_record(db, coach, "vs_division", 22, 14, 0, 20, 16, 4.2)
    add_situational_record(db, coach, "in_playoffs", 8, 4, 0, 7, 5, 6.8)
    add_tendency(db, coach, "play_action_rate", 28.5, 22.0, 82, "Heavy play-action user")

    # Kyle Shanahan - San Francisco 49ers
    coach = create_coach(db, "Kyle Shanahan", "NFL", "San Francisco 49ers", 8,
                         career_wins=70, career_losses=50, ats_wins=62, ats_losses=53, ats_pushes=5,
                         over_wins=55, under_wins=60)
    db.flush()
    add_situational_record(db, coach, "as_favorite", 48, 25, 0, 38, 32, 4.8)
    add_situational_record(db, coach, "after_bye_week", 5, 2, 0, 6, 1, 22.5)
    add_situational_record(db, coach, "primetime", 15, 8, 0, 14, 9, 7.5)
    add_situational_record(db, coach, "in_playoffs", 7, 5, 0, 6, 6, 0.0)
    add_situational_record(db, coach, "vs_division", 20, 16, 0, 22, 14, 8.5)
    add_situational_record(db, coach, "outdoor", 42, 30, 0, 40, 32, 4.8)
    add_tendency(db, coach, "run_rate", 48.2, 42.5, 88, "Run-heavy offense")

    # Mike Tomlin - Pittsburgh Steelers
    coach = create_coach(db, "Mike Tomlin", "NFL", "Pittsburgh Steelers", 18,
                         career_wins=183, career_losses=107, ats_wins=142, ats_losses=138, ats_pushes=10,
                         over_wins=135, under_wins=145)
    db.flush()
    add_situational_record(db, coach, "as_underdog", 42, 28, 0, 45, 25, 12.8)
    add_situational_record(db, coach, "primetime", 38, 22, 0, 35, 25, 6.8)
    add_situational_record(db, coach, "after_loss", 50, 28, 0, 48, 30, 8.2)
    add_situational_record(db, coach, "vs_division", 52, 38, 0, 48, 42, 3.2)
    add_situational_record(db, coach, "in_playoffs", 8, 10, 0, 9, 9, 0.0)
    add_situational_record(db, coach, "monday_night", 15, 8, 0, 14, 9, 7.5)
    add_tendency(db, coach, "never_losing_season", 100.0, 35.0, 100, "Never had a losing season")

    # John Harbaugh - Baltimore Ravens
    coach = create_coach(db, "John Harbaugh", "NFL", "Baltimore Ravens", 17,
                         career_wins=172, career_losses=100, ats_wins=138, ats_losses=125, ats_pushes=9,
                         over_wins=125, under_wins=140)
    db.flush()
    add_situational_record(db, coach, "as_favorite", 110, 55, 0, 82, 78, 1.5)
    add_situational_record(db, coach, "primetime", 32, 18, 0, 28, 22, 5.2)
    add_situational_record(db, coach, "after_bye_week", 12, 4, 0, 11, 5, 12.5)
    add_situational_record(db, coach, "in_playoffs", 11, 9, 0, 12, 8, 8.5)
    add_situational_record(db, coach, "vs_division", 48, 32, 0, 45, 35, 5.8)
    add_situational_record(db, coach, "cold_weather", 35, 18, 0, 32, 21, 7.8)
    add_tendency(db, coach, "defensive_rating", 82.5, 75.0, 75, "Consistently strong defense")

    # Sean McDermott - Buffalo Bills
    coach = create_coach(db, "Sean McDermott", "NFL", "Buffalo Bills", 8,
                         career_wins=72, career_losses=40, ats_wins=58, ats_losses=48, ats_pushes=6,
                         over_wins=52, under_wins=55)
    db.flush()
    add_situational_record(db, coach, "at_home", 42, 15, 0, 35, 22, 8.5)
    add_situational_record(db, coach, "as_favorite", 52, 28, 0, 40, 38, 1.8)
    add_situational_record(db, coach, "cold_weather", 28, 8, 0, 24, 12, 12.5)
    add_situational_record(db, coach, "after_loss", 22, 12, 0, 20, 14, 7.5)
    add_situational_record(db, coach, "in_playoffs", 5, 4, 0, 4, 5, -4.5)
    add_situational_record(db, coach, "vs_division", 28, 14, 0, 25, 17, 7.2)
    add_tendency(db, coach, "defensive_background", 88.0, 50.0, 90, "Defensive coordinator background")

    # Kevin Stefanski - Cleveland Browns
    coach = create_coach(db, "Kevin Stefanski", "NFL", "Cleveland Browns", 5,
                         career_wins=42, career_losses=33, ats_wins=38, ats_losses=32, ats_pushes=5,
                         over_wins=35, under_wins=38)
    db.flush()
    add_situational_record(db, coach, "as_underdog", 18, 12, 0, 19, 11, 10.5)
    add_situational_record(db, coach, "after_bye_week", 3, 1, 0, 3, 1, 15.0)
    add_situational_record(db, coach, "primetime", 8, 6, 0, 8, 6, 5.8)
    add_situational_record(db, coach, "vs_division", 15, 12, 0, 15, 12, 4.2)
    add_situational_record(db, coach, "after_loss", 15, 10, 0, 14, 11, 4.5)
    add_tendency(db, coach, "run_rate", 52.5, 42.5, 92, "Very run-heavy scheme")

    # Matt LaFleur - Green Bay Packers
    coach = create_coach(db, "Matt LaFleur", "NFL", "Green Bay Packers", 6,
                         career_wins=63, career_losses=31, ats_wins=48, ats_losses=42, ats_pushes=4,
                         over_wins=45, under_wins=42)
    db.flush()
    add_situational_record(db, coach, "at_home", 35, 10, 0, 28, 17, 9.5)
    add_situational_record(db, coach, "as_favorite", 48, 22, 0, 35, 32, 2.5)
    add_situational_record(db, coach, "cold_weather", 22, 6, 0, 18, 10, 10.5)
    add_situational_record(db, coach, "after_bye_week", 4, 1, 0, 4, 1, 18.5)
    add_situational_record(db, coach, "vs_division", 20, 10, 0, 18, 12, 8.5)
    add_situational_record(db, coach, "primetime", 12, 8, 0, 11, 9, 4.5)
    add_tendency(db, coach, "play_action_rate", 30.2, 22.0, 88, "Elite play-action usage")

    # Nick Sirianni - Philadelphia Eagles
    coach = create_coach(db, "Nick Sirianni", "NFL", "Philadelphia Eagles", 4,
                         career_wins=44, career_losses=20, ats_wins=35, ats_losses=26, ats_pushes=3,
                         over_wins=32, under_wins=30)
    db.flush()
    add_situational_record(db, coach, "at_home", 25, 7, 0, 20, 12, 9.5)
    add_situational_record(db, coach, "as_favorite", 35, 15, 0, 25, 22, 3.2)
    add_situational_record(db, coach, "primetime", 10, 5, 0, 9, 6, 8.5)
    add_situational_record(db, coach, "in_playoffs", 4, 2, 0, 4, 2, 12.5)
    add_situational_record(db, coach, "after_loss", 12, 6, 0, 11, 7, 8.2)
    add_tendency(db, coach, "rpo_rate", 18.5, 12.0, 85, "Heavy RPO usage")

    # Dan Campbell - Detroit Lions
    coach = create_coach(db, "Dan Campbell", "NFL", "Detroit Lions", 4,
                         career_wins=34, career_losses=21, ats_wins=32, ats_losses=20, ats_pushes=3,
                         over_wins=30, under_wins=22)
    db.flush()
    add_situational_record(db, coach, "as_underdog", 12, 8, 0, 14, 6, 15.5)
    add_situational_record(db, coach, "at_home", 20, 8, 0, 18, 10, 10.5)
    add_situational_record(db, coach, "after_loss", 10, 5, 0, 10, 5, 12.5)
    add_situational_record(db, coach, "primetime", 8, 4, 0, 8, 4, 12.5)
    add_situational_record(db, coach, "vs_division", 12, 6, 0, 12, 6, 12.5)
    add_tendency(db, coach, "4th_down_aggressiveness", 85.0, 55.0, 98, "Most aggressive 4th down coach in NFL")

    # DeMeco Ryans - Houston Texans
    coach = create_coach(db, "DeMeco Ryans", "NFL", "Houston Texans", 2,
                         career_wins=19, career_losses=15, ats_wins=20, ats_losses=14, ats_pushes=0,
                         over_wins=16, under_wins=18)
    db.flush()
    add_situational_record(db, coach, "as_underdog", 8, 5, 0, 9, 4, 15.2)
    add_situational_record(db, coach, "at_home", 12, 5, 0, 12, 5, 14.2)
    add_situational_record(db, coach, "after_loss", 6, 4, 0, 7, 3, 14.5)
    add_situational_record(db, coach, "in_playoffs", 2, 1, 0, 2, 1, 12.5)
    add_situational_record(db, coach, "vs_division", 6, 6, 0, 7, 5, 6.8)
    add_tendency(db, coach, "defensive_scheme_complexity", 78.0, 65.0, 72, "Complex defensive schemes")

    # Mike McDaniel - Miami Dolphins
    coach = create_coach(db, "Mike McDaniel", "NFL", "Miami Dolphins", 3,
                         career_wins=28, career_losses=23, ats_wins=26, ats_losses=23, ats_pushes=2,
                         over_wins=28, under_wins=20)
    db.flush()
    add_situational_record(db, coach, "at_home", 18, 8, 0, 16, 10, 8.5)
    add_situational_record(db, coach, "as_favorite", 20, 12, 0, 16, 14, 3.2)
    add_situational_record(db, coach, "hot_weather", 12, 4, 0, 11, 5, 12.5)
    add_situational_record(db, coach, "primetime", 6, 5, 0, 5, 6, -4.2)
    add_situational_record(db, coach, "after_loss", 8, 8, 0, 8, 8, 0.0)
    add_tendency(db, coach, "pace_of_play", 88.0, 60.0, 92, "Fast-paced offense")

    # Pete Carroll - Las Vegas Raiders
    coach = create_coach(db, "Pete Carroll", "NFL", "Las Vegas Raiders", 18,
                         career_wins=170, career_losses=120, ats_wins=145, ats_losses=138, ats_pushes=7,
                         over_wins=135, under_wins=145)
    db.flush()
    add_situational_record(db, coach, "at_home", 85, 45, 0, 72, 58, 5.8)
    add_situational_record(db, coach, "as_underdog", 38, 32, 0, 42, 28, 8.5)
    add_situational_record(db, coach, "primetime", 35, 25, 0, 32, 28, 3.2)
    add_situational_record(db, coach, "in_playoffs", 10, 8, 0, 9, 9, 0.0)
    add_situational_record(db, coach, "vs_division", 55, 35, 0, 48, 42, 3.8)
    add_tendency(db, coach, "run_rate", 46.5, 42.5, 72, "Run-first philosophy")

    # Todd Bowles - Tampa Bay Buccaneers
    coach = create_coach(db, "Todd Bowles", "NFL", "Tampa Bay Buccaneers", 8,
                         career_wins=48, career_losses=58, ats_wins=52, ats_losses=50, ats_pushes=4,
                         over_wins=48, under_wins=52)
    db.flush()
    add_situational_record(db, coach, "as_underdog", 22, 18, 0, 25, 15, 10.5)
    add_situational_record(db, coach, "primetime", 12, 10, 0, 13, 9, 6.8)
    add_situational_record(db, coach, "vs_division", 18, 12, 0, 17, 13, 5.2)
    add_situational_record(db, coach, "in_playoffs", 2, 2, 0, 2, 2, 0.0)
    add_situational_record(db, coach, "after_loss", 18, 20, 0, 20, 18, 2.8)
    add_tendency(db, coach, "blitz_rate", 38.5, 28.0, 88, "Heavy blitz package")

    print(f"  Seeded 15 NFL coaches")


def seed_nba_coaches(db):
    """Seed NBA coaches with realistic data."""
    print("Seeding NBA coaches...")

    # Erik Spoelstra - Miami Heat
    coach = create_coach(db, "Erik Spoelstra", "NBA", "Miami Heat", 17,
                         career_wins=725, career_losses=482, ats_wins=580, ats_losses=550, ats_pushes=20,
                         over_wins=560, under_wins=580)
    db.flush()
    add_situational_record(db, coach, "back_to_back", 85, 72, 0, 92, 65, 14.5)
    add_situational_record(db, coach, "as_underdog", 145, 120, 0, 155, 110, 12.8)
    add_situational_record(db, coach, "in_playoffs", 95, 65, 0, 88, 72, 7.5)
    add_situational_record(db, coach, "at_home", 420, 200, 0, 335, 280, 5.2)
    add_situational_record(db, coach, "after_loss", 180, 140, 0, 185, 135, 8.5)
    add_situational_record(db, coach, "primetime", 120, 85, 0, 115, 90, 5.8)
    add_tendency(db, coach, "defensive_rating", 108.5, 112.0, 85, "Elite defensive coach")
    add_tendency(db, coach, "zone_usage", 28.5, 12.0, 95, "Most zone defense in NBA")

    # Gregg Popovich - San Antonio Spurs
    coach = create_coach(db, "Gregg Popovich", "NBA", "San Antonio Spurs", 29,
                         career_wins=1390, career_losses=750, ats_wins=1050, ats_losses=980, ats_pushes=60,
                         over_wins=980, under_wins=1040)
    db.flush()
    add_situational_record(db, coach, "in_playoffs", 170, 114, 0, 152, 132, 4.2)
    add_situational_record(db, coach, "back_to_back", 180, 160, 0, 190, 150, 8.5)
    add_situational_record(db, coach, "as_favorite", 850, 380, 0, 620, 580, 2.5)
    add_situational_record(db, coach, "road_trip", 280, 220, 0, 275, 225, 4.8)
    add_situational_record(db, coach, "after_loss", 350, 220, 0, 320, 250, 5.8)
    add_tendency(db, coach, "rest_management", 95.0, 50.0, 99, "Pioneer of load management")

    # Steve Kerr - Golden State Warriors
    coach = create_coach(db, "Steve Kerr", "NBA", "Golden State Warriors", 10,
                         career_wins=550, career_losses=280, ats_wins=420, ats_losses=380, ats_pushes=30,
                         over_wins=430, under_wins=380)
    db.flush()
    add_situational_record(db, coach, "in_playoffs", 98, 45, 0, 78, 65, 6.5)
    add_situational_record(db, coach, "at_home", 320, 100, 0, 230, 190, 5.8)
    add_situational_record(db, coach, "as_favorite", 380, 165, 0, 285, 260, 2.8)
    add_situational_record(db, coach, "primetime", 95, 55, 0, 82, 68, 5.2)
    add_situational_record(db, coach, "back_to_back", 65, 55, 0, 68, 52, 6.8)
    add_tendency(db, coach, "three_point_rate", 42.5, 38.0, 82, "Three-point heavy offense")

    # Tyronn Lue - Los Angeles Clippers
    coach = create_coach(db, "Tyronn Lue", "NBA", "Los Angeles Clippers", 9,
                         career_wins=340, career_losses=215, ats_wins=285, ats_losses=255, ats_pushes=15,
                         over_wins=275, under_wins=265)
    db.flush()
    add_situational_record(db, coach, "in_playoffs", 55, 42, 0, 52, 45, 4.5)
    add_situational_record(db, coach, "as_underdog", 85, 68, 0, 90, 63, 12.2)
    add_situational_record(db, coach, "primetime", 65, 45, 0, 60, 50, 5.8)
    add_situational_record(db, coach, "back_to_back", 45, 42, 0, 50, 37, 9.5)
    add_situational_record(db, coach, "after_loss", 85, 55, 0, 80, 60, 6.8)
    add_tendency(db, coach, "playoff_adjustments", 88.0, 60.0, 90, "Elite in-series adjustments")

    # Joe Mazzulla - Boston Celtics
    coach = create_coach(db, "Joe Mazzulla", "NBA", "Boston Celtics", 3,
                         career_wins=130, career_losses=50, ats_wins=98, ats_losses=78, ats_pushes=4,
                         over_wins=92, under_wins=85)
    db.flush()
    add_situational_record(db, coach, "at_home", 75, 18, 0, 55, 38, 9.2)
    add_situational_record(db, coach, "as_big_favorite", 65, 15, 0, 42, 38, 3.2)
    add_situational_record(db, coach, "in_playoffs", 23, 6, 0, 18, 11, 10.5)
    add_situational_record(db, coach, "back_to_back", 18, 12, 0, 18, 12, 8.5)
    add_situational_record(db, coach, "primetime", 32, 15, 0, 28, 19, 7.5)
    add_tendency(db, coach, "three_point_rate", 45.2, 38.0, 95, "Highest 3PA rate in NBA")

    # Mike Budenholzer - Phoenix Suns
    coach = create_coach(db, "Mike Budenholzer", "NBA", "Phoenix Suns", 11,
                         career_wins=480, career_losses=340, ats_wins=415, ats_losses=385, ats_pushes=20,
                         over_wins=410, under_wins=395)
    db.flush()
    add_situational_record(db, coach, "as_favorite", 320, 180, 0, 265, 235, 3.2)
    add_situational_record(db, coach, "at_home", 290, 130, 0, 225, 195, 4.2)
    add_situational_record(db, coach, "in_playoffs", 48, 42, 0, 45, 45, 0.0)
    add_situational_record(db, coach, "back_to_back", 58, 52, 0, 62, 48, 6.8)
    add_situational_record(db, coach, "after_loss", 125, 95, 0, 118, 102, 4.2)
    add_tendency(db, coach, "pace", 102.5, 99.0, 75, "Moderate pace offense")

    # Tom Thibodeau - New York Knicks
    coach = create_coach(db, "Tom Thibodeau", "NBA", "New York Knicks", 14,
                         career_wins=520, career_losses=382, ats_wins=465, ats_losses=420, ats_pushes=17,
                         over_wins=420, under_wins=480)
    db.flush()
    add_situational_record(db, coach, "as_underdog", 135, 95, 0, 145, 85, 14.5)
    add_situational_record(db, coach, "at_home", 300, 155, 0, 255, 200, 6.2)
    add_situational_record(db, coach, "back_to_back", 72, 68, 0, 85, 55, 13.5)
    add_situational_record(db, coach, "in_playoffs", 35, 38, 0, 38, 35, 2.8)
    add_situational_record(db, coach, "after_loss", 145, 105, 0, 140, 110, 5.8)
    add_tendency(db, coach, "defensive_rating", 106.8, 112.0, 92, "Elite defensive coach")
    add_tendency(db, coach, "minutes_distribution", 38.5, 34.0, 98, "Heavy starter minutes")

    # Jason Kidd - Dallas Mavericks
    coach = create_coach(db, "Jason Kidd", "NBA", "Dallas Mavericks", 9,
                         career_wins=320, career_losses=280, ats_wins=305, ats_losses=285, ats_pushes=10,
                         over_wins=295, under_wins=290)
    db.flush()
    add_situational_record(db, coach, "in_playoffs", 32, 25, 0, 30, 27, 3.5)
    add_situational_record(db, coach, "as_underdog", 95, 85, 0, 105, 75, 10.5)
    add_situational_record(db, coach, "primetime", 55, 45, 0, 55, 45, 5.5)
    add_situational_record(db, coach, "back_to_back", 42, 45, 0, 48, 39, 5.8)
    add_situational_record(db, coach, "at_home", 185, 125, 0, 170, 140, 5.2)
    add_tendency(db, coach, "defensive_scheme", 72.0, 65.0, 65, "Switching defense")

    # Rick Carlisle - Indiana Pacers
    coach = create_coach(db, "Rick Carlisle", "NBA", "Indiana Pacers", 22,
                         career_wins=880, career_losses=720, ats_wins=810, ats_losses=750, ats_pushes=40,
                         over_wins=780, under_wins=800)
    db.flush()
    add_situational_record(db, coach, "as_underdog", 280, 240, 0, 305, 215, 12.2)
    add_situational_record(db, coach, "at_home", 520, 310, 0, 445, 385, 4.2)
    add_situational_record(db, coach, "in_playoffs", 55, 58, 0, 58, 55, 1.8)
    add_situational_record(db, coach, "back_to_back", 115, 110, 0, 125, 100, 5.5)
    add_situational_record(db, coach, "after_loss", 245, 205, 0, 248, 202, 4.8)
    add_tendency(db, coach, "offensive_creativity", 78.0, 70.0, 72, "Creative play designer")

    # Taylor Jenkins - Memphis Grizzlies
    coach = create_coach(db, "Taylor Jenkins", "NBA", "Memphis Grizzlies", 6,
                         career_wins=225, career_losses=175, ats_wins=210, ats_losses=180, ats_pushes=10,
                         over_wins=215, under_wins=180)
    db.flush()
    add_situational_record(db, coach, "as_underdog", 65, 55, 0, 72, 48, 12.5)
    add_situational_record(db, coach, "at_home", 135, 70, 0, 115, 90, 6.8)
    add_situational_record(db, coach, "back_to_back", 32, 28, 0, 35, 25, 9.2)
    add_situational_record(db, coach, "in_playoffs", 15, 16, 0, 16, 15, 2.2)
    add_situational_record(db, coach, "after_loss", 62, 48, 0, 65, 45, 8.5)
    add_tendency(db, coach, "pace", 104.8, 99.0, 88, "Fast-paced offense")

    print(f"  Seeded 10 NBA coaches")


def seed_cbb_coaches(db):
    """Seed College Basketball coaches with realistic data."""
    print("Seeding College Basketball coaches...")

    # John Calipari - Arkansas (formerly Kentucky)
    coach = create_coach(db, "John Calipari", "CBB", "Arkansas Razorbacks", 32,
                         career_wins=820, career_losses=265, ats_wins=520, ats_losses=485, ats_pushes=35,
                         over_wins=500, under_wins=510)
    db.flush()
    add_situational_record(db, coach, "as_favorite", 620, 145, 0, 385, 380, 0.5)
    add_situational_record(db, coach, "as_big_favorite", 450, 85, 0, 260, 275, -2.8)
    add_situational_record(db, coach, "in_playoffs", 52, 26, 0, 42, 36, 4.5)
    add_situational_record(db, coach, "vs_conference", 280, 95, 0, 195, 180, 2.8)
    add_situational_record(db, coach, "after_loss", 85, 45, 0, 75, 55, 8.5)
    add_tendency(db, coach, "recruiting_rank", 95.0, 50.0, 98, "Elite recruiter")
    add_tendency(db, coach, "nba_players_developed", 58, 15, 99, "NBA factory")

    # Bill Self - Kansas Jayhawks
    coach = create_coach(db, "Bill Self", "CBB", "Kansas Jayhawks", 31,
                         career_wins=790, career_losses=230, ats_wins=515, ats_losses=465, ats_pushes=40,
                         over_wins=480, under_wins=510)
    db.flush()
    add_situational_record(db, coach, "at_home", 385, 35, 0, 225, 195, 4.2)
    add_situational_record(db, coach, "as_favorite", 580, 150, 0, 380, 350, 2.5)
    add_situational_record(db, coach, "in_playoffs", 48, 22, 0, 38, 32, 4.8)
    add_situational_record(db, coach, "vs_conference", 295, 85, 0, 200, 180, 3.5)
    add_situational_record(db, coach, "after_loss", 75, 40, 0, 65, 50, 6.2)
    add_tendency(db, coach, "home_court_advantage", 92.0, 65.0, 98, "Allen Fieldhouse dominance")

    # Tom Izzo - Michigan State Spartans
    coach = create_coach(db, "Tom Izzo", "CBB", "Michigan State Spartans", 30,
                         career_wins=720, career_losses=290, ats_wins=510, ats_losses=465, ats_pushes=35,
                         over_wins=485, under_wins=505)
    db.flush()
    add_situational_record(db, coach, "in_playoffs", 58, 23, 0, 48, 33, 9.5)
    add_situational_record(db, coach, "as_underdog", 95, 72, 0, 102, 65, 14.2)
    add_situational_record(db, coach, "vs_conference", 285, 120, 0, 215, 190, 3.8)
    add_situational_record(db, coach, "after_loss", 82, 48, 0, 78, 52, 8.5)
    add_situational_record(db, coach, "at_home", 380, 85, 0, 255, 210, 5.8)
    add_tendency(db, coach, "march_performance", 95.0, 50.0, 99, "Mr. March - Elite tournament coach")

    # Jay Wright - Retired (formerly Villanova)
    coach = create_coach(db, "Jay Wright", "CBB", "Retired (Villanova)", 26,
                         career_wins=642, career_losses=282, ats_wins=475, ats_losses=420, ats_pushes=29,
                         over_wins=440, under_wins=470)
    db.flush()
    add_situational_record(db, coach, "in_playoffs", 42, 18, 0, 38, 22, 12.5)
    add_situational_record(db, coach, "as_favorite", 480, 165, 0, 345, 300, 4.2)
    add_situational_record(db, coach, "vs_conference", 245, 95, 0, 185, 155, 5.8)
    add_situational_record(db, coach, "after_loss", 68, 42, 0, 62, 48, 6.2)
    add_situational_record(db, coach, "primetime", 85, 45, 0, 72, 58, 5.8)
    add_tendency(db, coach, "three_point_shooting", 38.5, 34.0, 92, "Elite shooting teams")

    # Mark Few - Gonzaga Bulldogs
    coach = create_coach(db, "Mark Few", "CBB", "Gonzaga Bulldogs", 26,
                         career_wins=720, career_losses=140, ats_wins=435, ats_losses=395, ats_pushes=30,
                         over_wins=450, under_wins=405)
    db.flush()
    add_situational_record(db, coach, "at_home", 365, 25, 0, 215, 175, 5.8)
    add_situational_record(db, coach, "as_big_favorite", 380, 55, 0, 210, 225, -3.2)
    add_situational_record(db, coach, "in_playoffs", 35, 16, 0, 28, 23, 4.8)
    add_situational_record(db, coach, "vs_non_conference", 285, 65, 0, 185, 165, 3.5)
    add_situational_record(db, coach, "after_loss", 42, 28, 0, 40, 30, 6.8)
    add_tendency(db, coach, "offensive_efficiency", 118.5, 105.0, 98, "Elite offensive system")

    # Dan Hurley - Connecticut Huskies
    coach = create_coach(db, "Dan Hurley", "CBB", "Connecticut Huskies", 14,
                         career_wins=340, career_losses=165, ats_wins=265, ats_losses=225, ats_pushes=15,
                         over_wins=250, under_wins=255)
    db.flush()
    add_situational_record(db, coach, "in_playoffs", 18, 4, 0, 16, 6, 18.5)
    add_situational_record(db, coach, "as_favorite", 245, 95, 0, 185, 155, 5.2)
    add_situational_record(db, coach, "vs_conference", 135, 55, 0, 105, 85, 5.8)
    add_situational_record(db, coach, "at_home", 175, 55, 0, 125, 105, 5.2)
    add_situational_record(db, coach, "after_loss", 52, 32, 0, 48, 36, 6.8)
    add_tendency(db, coach, "defensive_intensity", 88.0, 70.0, 92, "High-pressure defense")

    # Scott Drew - Baylor Bears
    coach = create_coach(db, "Scott Drew", "CBB", "Baylor Bears", 22,
                         career_wins=420, career_losses=230, ats_wins=340, ats_losses=295, ats_pushes=15,
                         over_wins=320, under_wins=330)
    db.flush()
    add_situational_record(db, coach, "at_home", 225, 65, 0, 165, 125, 7.2)
    add_situational_record(db, coach, "in_playoffs", 18, 12, 0, 17, 13, 5.2)
    add_situational_record(db, coach, "as_favorite", 295, 135, 0, 230, 200, 4.2)
    add_situational_record(db, coach, "vs_conference", 175, 95, 0, 145, 125, 4.2)
    add_situational_record(db, coach, "after_loss", 65, 42, 0, 58, 49, 4.5)
    add_tendency(db, coach, "program_building", 95.0, 50.0, 98, "Elite program builder")

    # Eric Musselman - USC Trojans
    coach = create_coach(db, "Eric Musselman", "CBB", "USC Trojans", 9,
                         career_wins=205, career_losses=75, ats_wins=155, ats_losses=115, ats_pushes=10,
                         over_wins=145, under_wins=130)
    db.flush()
    add_situational_record(db, coach, "in_playoffs", 12, 5, 0, 11, 6, 10.5)
    add_situational_record(db, coach, "as_underdog", 42, 32, 0, 48, 26, 15.5)
    add_situational_record(db, coach, "at_home", 115, 25, 0, 85, 55, 9.5)
    add_situational_record(db, coach, "vs_conference", 85, 45, 0, 72, 58, 5.2)
    add_situational_record(db, coach, "after_loss", 28, 18, 0, 28, 18, 8.5)
    add_tendency(db, coach, "transfer_portal", 92.0, 50.0, 96, "Transfer portal master")

    # Kelvin Sampson - Houston Cougars
    coach = create_coach(db, "Kelvin Sampson", "CBB", "Houston Cougars", 35,
                         career_wins=720, career_losses=335, ats_wins=545, ats_losses=475, ats_pushes=35,
                         over_wins=490, under_wins=530)
    db.flush()
    add_situational_record(db, coach, "as_favorite", 420, 185, 0, 325, 280, 4.2)
    add_situational_record(db, coach, "at_home", 385, 95, 0, 265, 215, 5.8)
    add_situational_record(db, coach, "in_playoffs", 22, 15, 0, 20, 17, 4.2)
    add_situational_record(db, coach, "vs_conference", 245, 115, 0, 195, 165, 4.8)
    add_situational_record(db, coach, "after_loss", 95, 65, 0, 88, 72, 4.8)
    add_tendency(db, coach, "defensive_rating", 92.5, 100.0, 92, "Elite defensive coach")

    # Bruce Pearl - Auburn Tigers
    coach = create_coach(db, "Bruce Pearl", "CBB", "Auburn Tigers", 22,
                         career_wins=535, career_losses=255, ats_wins=420, ats_losses=350, ats_pushes=20,
                         over_wins=415, under_wins=375)
    db.flush()
    add_situational_record(db, coach, "at_home", 295, 75, 0, 210, 160, 7.5)
    add_situational_record(db, coach, "as_underdog", 85, 72, 0, 95, 62, 13.2)
    add_situational_record(db, coach, "in_playoffs", 18, 12, 0, 17, 13, 5.2)
    add_situational_record(db, coach, "vs_conference", 195, 105, 0, 165, 135, 5.5)
    add_situational_record(db, coach, "after_loss", 72, 48, 0, 68, 52, 6.8)
    add_tendency(db, coach, "crowd_energy", 88.0, 60.0, 90, "Elite home atmosphere")

    print(f"  Seeded 10 College Basketball coaches")


def main():
    """Main function to seed all coaches."""
    print("=" * 50)
    print("Coach DNA Database Seed Script")
    print("=" * 50)

    # Initialize database
    init_db()

    db = SessionLocal()
    try:
        # Seed all coaches
        seed_nfl_coaches(db)
        seed_nba_coaches(db)
        seed_cbb_coaches(db)

        # Commit all changes
        db.commit()

        # Print summary
        coach_count = db.query(Coach).count()
        record_count = db.query(CoachSituationalRecord).count()
        tendency_count = db.query(CoachTendency).count()

        print("\n" + "=" * 50)
        print("Seeding Complete!")
        print(f"  Total Coaches: {coach_count}")
        print(f"  Total Situational Records: {record_count}")
        print(f"  Total Tendencies: {tendency_count}")
        print("=" * 50)

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
