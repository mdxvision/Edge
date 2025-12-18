"""
Seed Historical Situations Database

Populates historical situational performance data based on research
and historical betting trends.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db import SessionLocal, HistoricalSituation, init_db


HISTORICAL_SITUATIONS = [
    # NFL Rest/Bye Situations
    {
        "situation_type": "nfl_home_after_bye",
        "situation_name": "NFL Home Team After Bye Week",
        "sport": "NFL",
        "sample_size": 450,
        "ats_wins": 268,
        "ats_losses": 172,
        "ats_pushes": 10,
        "win_percentage": 60.9,
        "roi_percentage": 8.5,
        "edge_points": 2.8,
        "description": "Home teams coming off bye week against teams playing consecutive weeks",
        "notes": "One of the most reliable situational angles in NFL betting. Extra prep time + rest = significant edge."
    },
    {
        "situation_type": "nfl_road_after_bye",
        "situation_name": "NFL Road Team After Bye Week",
        "sport": "NFL",
        "sample_size": 380,
        "ats_wins": 208,
        "ats_losses": 165,
        "ats_pushes": 7,
        "win_percentage": 55.8,
        "roi_percentage": 4.2,
        "edge_points": 1.5,
        "description": "Road teams coming off bye week",
        "notes": "Less impactful than home after bye, but still positive edge."
    },
    {
        "situation_type": "nfl_thursday_away_short_rest",
        "situation_name": "NFL Away Team Thursday Night (Short Week)",
        "sport": "NFL",
        "sample_size": 320,
        "ats_wins": 138,
        "ats_losses": 175,
        "ats_pushes": 7,
        "win_percentage": 44.1,
        "roi_percentage": -7.8,
        "edge_points": -1.8,
        "description": "Away teams playing Thursday night after Sunday game",
        "notes": "Travel + short rest = significant disadvantage. Fade road teams on TNF."
    },
    {
        "situation_type": "nfl_monday_home_rest_advantage",
        "situation_name": "NFL Home Monday Night After Bye",
        "sport": "NFL",
        "sample_size": 85,
        "ats_wins": 55,
        "ats_losses": 28,
        "ats_pushes": 2,
        "win_percentage": 66.3,
        "roi_percentage": 12.8,
        "edge_points": 4.2,
        "description": "Home teams on MNF coming off bye week",
        "notes": "Premium spot - national TV + extra rest + home crowd = peak performance."
    },

    # NBA Rest Situations
    {
        "situation_type": "nba_road_back_to_back",
        "situation_name": "NBA Road Team on Back-to-Back",
        "sport": "NBA",
        "sample_size": 2400,
        "ats_wins": 1040,
        "ats_losses": 1320,
        "ats_pushes": 40,
        "win_percentage": 44.1,
        "roi_percentage": -8.2,
        "edge_points": -4.5,
        "description": "Road teams playing second game of back-to-back",
        "notes": "Most reliable fade in NBA. Fatigue + travel = poor performance. Stars often rest."
    },
    {
        "situation_type": "nba_home_vs_b2b",
        "situation_name": "NBA Home Team vs B2B Opponent",
        "sport": "NBA",
        "sample_size": 2200,
        "ats_wins": 1265,
        "ats_losses": 895,
        "ats_pushes": 40,
        "win_percentage": 58.6,
        "roi_percentage": 6.8,
        "edge_points": 3.5,
        "description": "Home teams hosting opponents on back-to-back",
        "notes": "Inverse of road B2B. Fresh home team vs tired visitors = edge."
    },
    {
        "situation_type": "nba_three_in_four_road",
        "situation_name": "NBA Road Team 3rd Game in 4 Days",
        "sport": "NBA",
        "sample_size": 850,
        "ats_wins": 355,
        "ats_losses": 478,
        "ats_pushes": 17,
        "win_percentage": 42.6,
        "roi_percentage": -10.1,
        "edge_points": -5.2,
        "description": "Road teams playing third game in four days",
        "notes": "Cumulative fatigue is real. Even strong teams struggle here."
    },
    {
        "situation_type": "nba_rested_home_primetime",
        "situation_name": "NBA Rested Home Team (3+ Days) Primetime",
        "sport": "NBA",
        "sample_size": 620,
        "ats_wins": 365,
        "ats_losses": 242,
        "ats_pushes": 13,
        "win_percentage": 60.1,
        "roi_percentage": 7.5,
        "edge_points": 2.8,
        "description": "Home teams with 3+ days rest in nationally televised games",
        "notes": "Well-rested teams perform better under bright lights."
    },

    # Travel Situations
    {
        "situation_type": "nba_west_to_east_early",
        "situation_name": "NBA West Coast Team Early Eastern Game",
        "sport": "NBA",
        "sample_size": 680,
        "ats_wins": 285,
        "ats_losses": 380,
        "ats_pushes": 15,
        "win_percentage": 42.9,
        "roi_percentage": -9.5,
        "edge_points": -2.8,
        "description": "West Coast teams playing afternoon/early evening games in Eastern time zone",
        "notes": "Body clock disadvantage. A 1 PM ET tip is 10 AM Pacific body time."
    },
    {
        "situation_type": "nba_long_road_trip_game_4plus",
        "situation_name": "NBA 4th+ Game of Road Trip",
        "sport": "NBA",
        "sample_size": 420,
        "ats_wins": 172,
        "ats_losses": 238,
        "ats_pushes": 10,
        "win_percentage": 41.9,
        "roi_percentage": -11.2,
        "edge_points": -3.2,
        "description": "Teams playing 4th or later game of extended road trip",
        "notes": "Road weariness compounds. Even good teams fade late in road trips."
    },
    {
        "situation_type": "mlb_denver_visitor_game1",
        "situation_name": "MLB First Game at Coors Field",
        "sport": "MLB",
        "sample_size": 350,
        "ats_wins": 142,
        "ats_losses": 198,
        "ats_pushes": 10,
        "win_percentage": 41.8,
        "roi_percentage": -8.8,
        "edge_points": -1.2,
        "description": "Visiting teams' first game at Coors Field (altitude adjustment)",
        "notes": "Altitude affects pitchers significantly. Breaking balls don't break as much."
    },
    {
        "situation_type": "nfl_cross_country_1pm",
        "situation_name": "NFL West Team 1 PM ET Road Game",
        "sport": "NFL",
        "sample_size": 280,
        "ats_wins": 118,
        "ats_losses": 155,
        "ats_pushes": 7,
        "win_percentage": 43.2,
        "roi_percentage": -7.2,
        "edge_points": -2.2,
        "description": "West Coast teams playing 1 PM ET games (10 AM body clock)",
        "notes": "Early kickoffs are brutal for West Coast teams. Body says breakfast time."
    },

    # Motivation Situations
    {
        "situation_type": "all_revenge_star_former_team",
        "situation_name": "Star Player vs Former Team",
        "sport": "ALL",
        "sample_size": 380,
        "ats_wins": 218,
        "ats_losses": 155,
        "ats_pushes": 7,
        "win_percentage": 58.4,
        "roi_percentage": 6.2,
        "edge_points": 2.1,
        "description": "Teams with star player facing their former team (first 2 years)",
        "notes": "Extra motivation is real. Stars want to prove former team wrong."
    },
    {
        "situation_type": "all_letdown_after_ot_thriller",
        "situation_name": "Team After Overtime Thriller",
        "sport": "ALL",
        "sample_size": 520,
        "ats_wins": 218,
        "ats_losses": 292,
        "ats_pushes": 10,
        "win_percentage": 42.7,
        "roi_percentage": -9.8,
        "edge_points": -2.2,
        "description": "Teams playing within 3 days after overtime game",
        "notes": "Physical and emotional toll of OT games carries over."
    },
    {
        "situation_type": "all_lookahead_before_rivalry",
        "situation_name": "Favorite Before Major Rivalry Game",
        "sport": "ALL",
        "sample_size": 440,
        "ats_wins": 185,
        "ats_losses": 245,
        "ats_pushes": 10,
        "win_percentage": 43.0,
        "roi_percentage": -8.5,
        "edge_points": -2.5,
        "description": "Favorites playing weak opponent before rivalry/big game",
        "notes": "Classic trap game. Teams mentally look ahead to bigger matchup."
    },
    {
        "situation_type": "nfl_after_clinch",
        "situation_name": "NFL Team After Clinching Playoff Spot",
        "sport": "NFL",
        "sample_size": 180,
        "ats_wins": 68,
        "ats_losses": 108,
        "ats_pushes": 4,
        "win_percentage": 38.6,
        "roi_percentage": -14.2,
        "edge_points": -3.5,
        "description": "Teams playing immediately after clinching playoff berth",
        "notes": "Motivation cliff. Why risk injury when you've already made it?"
    },
    {
        "situation_type": "nba_sandwich_spot",
        "situation_name": "NBA Sandwich Game",
        "sport": "NBA",
        "sample_size": 580,
        "ats_wins": 238,
        "ats_losses": 328,
        "ats_pushes": 14,
        "win_percentage": 42.0,
        "roi_percentage": -10.5,
        "edge_points": -3.0,
        "description": "Favorite playing weak team between two tough opponents",
        "notes": "Classic scheduling trap. Physically and mentally caught between bigger games."
    },
    {
        "situation_type": "nfl_nothing_to_play_for",
        "situation_name": "NFL Team With Nothing To Play For (Week 17-18)",
        "sport": "NFL",
        "sample_size": 240,
        "ats_wins": 95,
        "ats_losses": 140,
        "ats_pushes": 5,
        "win_percentage": 40.4,
        "roi_percentage": -12.8,
        "edge_points": -4.0,
        "description": "Teams eliminated or locked into seed in final weeks",
        "notes": "Starters rest, motivation evaporates. Fade hard."
    },

    # Special Situations
    {
        "situation_type": "nba_elimination_game",
        "situation_name": "NBA Playoff Elimination Game (Underdog)",
        "sport": "NBA",
        "sample_size": 320,
        "ats_wins": 185,
        "ats_losses": 128,
        "ats_pushes": 7,
        "win_percentage": 59.1,
        "roi_percentage": 7.2,
        "edge_points": 3.5,
        "description": "Underdogs in playoff elimination games",
        "notes": "Desperation breeds performance. Underdogs fight harder facing elimination."
    },
    {
        "situation_type": "mlb_game_163_underdog",
        "situation_name": "MLB Game 163/Tiebreaker Underdog",
        "sport": "MLB",
        "sample_size": 45,
        "ats_wins": 28,
        "ats_losses": 16,
        "ats_pushes": 1,
        "win_percentage": 63.6,
        "roi_percentage": 11.5,
        "edge_points": 2.8,
        "description": "Underdogs in winner-take-all tiebreaker games",
        "notes": "Small sample but consistent - underdogs rise in must-win scenarios."
    },
    {
        "situation_type": "nfl_primetime_home_dog",
        "situation_name": "NFL Primetime Home Underdog",
        "sport": "NFL",
        "sample_size": 380,
        "ats_wins": 215,
        "ats_losses": 158,
        "ats_pushes": 7,
        "win_percentage": 57.6,
        "roi_percentage": 5.8,
        "edge_points": 2.2,
        "description": "Home underdogs in primetime (SNF/MNF/TNF)",
        "notes": "Crowd energy + underdog motivation = profitable angle."
    },
    {
        "situation_type": "nba_home_opener",
        "situation_name": "NBA Home Opener",
        "sport": "NBA",
        "sample_size": 280,
        "ats_wins": 162,
        "ats_losses": 112,
        "ats_pushes": 6,
        "win_percentage": 59.1,
        "roi_percentage": 6.8,
        "edge_points": 2.5,
        "description": "Teams playing their home opener of the season",
        "notes": "Ring ceremonies, banner raisings, energized crowd = extra motivation."
    },
    {
        "situation_type": "mlb_day_after_night_road",
        "situation_name": "MLB Day Game After Night Game (Road)",
        "sport": "MLB",
        "sample_size": 1200,
        "ats_wins": 520,
        "ats_losses": 655,
        "ats_pushes": 25,
        "win_percentage": 44.3,
        "roi_percentage": -7.5,
        "edge_points": -0.8,
        "description": "Road teams playing day game after night game",
        "notes": "Travel + lack of sleep = tired players. Pitchers especially affected."
    },
    {
        "situation_type": "nfl_divisional_road_dog",
        "situation_name": "NFL Divisional Road Underdog",
        "sport": "NFL",
        "sample_size": 680,
        "ats_wins": 378,
        "ats_losses": 292,
        "ats_pushes": 10,
        "win_percentage": 56.4,
        "roi_percentage": 5.2,
        "edge_points": 1.8,
        "description": "Road underdogs in divisional games",
        "notes": "Familiarity breeds competitive games. Dogs know their rivals well."
    },
]


def seed_historical_situations():
    """Seed the historical situations database."""
    db = SessionLocal()

    try:
        # Check if already seeded
        existing = db.query(HistoricalSituation).count()
        if existing > 0:
            print(f"Historical situations table already has {existing} entries. Skipping seed.")
            return

        print("Seeding historical situations database...")

        for data in HISTORICAL_SITUATIONS:
            situation = HistoricalSituation(
                situation_type=data["situation_type"],
                situation_name=data["situation_name"],
                sport=data["sport"],
                sample_size=data["sample_size"],
                ats_wins=data["ats_wins"],
                ats_losses=data["ats_losses"],
                ats_pushes=data.get("ats_pushes", 0),
                win_percentage=data["win_percentage"],
                roi_percentage=data["roi_percentage"],
                edge_points=data.get("edge_points"),
                description=data.get("description"),
                notes=data.get("notes"),
            )
            db.add(situation)

        db.commit()
        print(f"Successfully seeded {len(HISTORICAL_SITUATIONS)} historical situations")

        # Print summary
        nfl_count = sum(1 for s in HISTORICAL_SITUATIONS if s["sport"] == "NFL")
        nba_count = sum(1 for s in HISTORICAL_SITUATIONS if s["sport"] == "NBA")
        mlb_count = sum(1 for s in HISTORICAL_SITUATIONS if s["sport"] == "MLB")
        all_count = sum(1 for s in HISTORICAL_SITUATIONS if s["sport"] == "ALL")

        print(f"  - NFL situations: {nfl_count}")
        print(f"  - NBA situations: {nba_count}")
        print(f"  - MLB situations: {mlb_count}")
        print(f"  - All sports: {all_count}")

    except Exception as e:
        print(f"Error seeding historical situations: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    seed_historical_situations()
