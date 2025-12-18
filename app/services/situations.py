"""
Situational Factors Analysis Service

Calculates edges from rest, travel, motivation, and schedule spots.
These are hidden edges that sharps exploit but casual bettors ignore.
"""

from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
import math
import logging

from app.db import GameSituation, HistoricalSituation, Game

logger = logging.getLogger(__name__)


# ============================================================================
# CITY DATA - Coordinates, Time Zones, Altitudes
# ============================================================================

CITY_DATA = {
    # NBA/NHL Cities
    "Boston": {"lat": 42.36, "lon": -71.06, "tz": -5, "alt": 20},
    "New York": {"lat": 40.71, "lon": -74.01, "tz": -5, "alt": 33},
    "Brooklyn": {"lat": 40.68, "lon": -73.98, "tz": -5, "alt": 33},
    "Philadelphia": {"lat": 39.95, "lon": -75.17, "tz": -5, "alt": 39},
    "Toronto": {"lat": 43.65, "lon": -79.38, "tz": -5, "alt": 76},
    "Miami": {"lat": 25.76, "lon": -80.19, "tz": -5, "alt": 6},
    "Orlando": {"lat": 28.54, "lon": -81.38, "tz": -5, "alt": 82},
    "Atlanta": {"lat": 33.75, "lon": -84.39, "tz": -5, "alt": 1050},
    "Charlotte": {"lat": 35.23, "lon": -80.84, "tz": -5, "alt": 751},
    "Washington": {"lat": 38.91, "lon": -77.04, "tz": -5, "alt": 125},
    "Cleveland": {"lat": 41.50, "lon": -81.69, "tz": -5, "alt": 653},
    "Detroit": {"lat": 42.33, "lon": -83.05, "tz": -5, "alt": 600},
    "Indiana": {"lat": 39.77, "lon": -86.16, "tz": -5, "alt": 715},
    "Indianapolis": {"lat": 39.77, "lon": -86.16, "tz": -5, "alt": 715},
    "Chicago": {"lat": 41.88, "lon": -87.63, "tz": -6, "alt": 594},
    "Milwaukee": {"lat": 43.04, "lon": -87.91, "tz": -6, "alt": 617},
    "Minnesota": {"lat": 44.98, "lon": -93.27, "tz": -6, "alt": 830},
    "Minneapolis": {"lat": 44.98, "lon": -93.27, "tz": -6, "alt": 830},
    "Oklahoma City": {"lat": 35.47, "lon": -97.52, "tz": -6, "alt": 1201},
    "San Antonio": {"lat": 29.42, "lon": -98.49, "tz": -6, "alt": 650},
    "Dallas": {"lat": 32.78, "lon": -96.80, "tz": -6, "alt": 430},
    "Houston": {"lat": 29.76, "lon": -95.37, "tz": -6, "alt": 80},
    "Memphis": {"lat": 35.15, "lon": -90.05, "tz": -6, "alt": 337},
    "New Orleans": {"lat": 29.95, "lon": -90.07, "tz": -6, "alt": 7},
    "Denver": {"lat": 39.74, "lon": -104.99, "tz": -7, "alt": 5280},
    "Utah": {"lat": 40.77, "lon": -111.89, "tz": -7, "alt": 4226},
    "Salt Lake City": {"lat": 40.77, "lon": -111.89, "tz": -7, "alt": 4226},
    "Phoenix": {"lat": 33.45, "lon": -112.07, "tz": -7, "alt": 1086},
    "Portland": {"lat": 45.52, "lon": -122.68, "tz": -8, "alt": 50},
    "Seattle": {"lat": 47.61, "lon": -122.33, "tz": -8, "alt": 175},
    "Sacramento": {"lat": 38.58, "lon": -121.49, "tz": -8, "alt": 30},
    "Golden State": {"lat": 37.77, "lon": -122.42, "tz": -8, "alt": 52},
    "San Francisco": {"lat": 37.77, "lon": -122.42, "tz": -8, "alt": 52},
    "Los Angeles": {"lat": 34.05, "lon": -118.24, "tz": -8, "alt": 285},
    "LA Clippers": {"lat": 34.05, "lon": -118.24, "tz": -8, "alt": 285},
    "LA Lakers": {"lat": 34.05, "lon": -118.24, "tz": -8, "alt": 285},

    # NFL Cities
    "Baltimore": {"lat": 39.29, "lon": -76.61, "tz": -5, "alt": 33},
    "Pittsburgh": {"lat": 40.44, "lon": -80.00, "tz": -5, "alt": 1223},
    "Cincinnati": {"lat": 39.10, "lon": -84.51, "tz": -5, "alt": 482},
    "Jacksonville": {"lat": 30.33, "lon": -81.66, "tz": -5, "alt": 16},
    "Tampa Bay": {"lat": 27.95, "lon": -82.46, "tz": -5, "alt": 48},
    "Tampa": {"lat": 27.95, "lon": -82.46, "tz": -5, "alt": 48},
    "Carolina": {"lat": 35.23, "lon": -80.84, "tz": -5, "alt": 751},
    "Buffalo": {"lat": 42.89, "lon": -78.88, "tz": -5, "alt": 600},
    "Green Bay": {"lat": 44.51, "lon": -88.02, "tz": -6, "alt": 594},
    "Kansas City": {"lat": 39.10, "lon": -94.58, "tz": -6, "alt": 910},
    "Tennessee": {"lat": 36.17, "lon": -86.78, "tz": -6, "alt": 597},
    "Nashville": {"lat": 36.17, "lon": -86.78, "tz": -6, "alt": 597},
    "Arizona": {"lat": 33.45, "lon": -112.07, "tz": -7, "alt": 1086},
    "Las Vegas": {"lat": 36.17, "lon": -115.14, "tz": -8, "alt": 2001},
    "San Diego": {"lat": 32.72, "lon": -117.16, "tz": -8, "alt": 62},
    "Oakland": {"lat": 37.80, "lon": -122.27, "tz": -8, "alt": 42},

    # MLB Cities
    "St. Louis": {"lat": 38.63, "lon": -90.20, "tz": -6, "alt": 466},
    "Colorado": {"lat": 39.74, "lon": -104.99, "tz": -7, "alt": 5280},
    "Anaheim": {"lat": 33.80, "lon": -117.88, "tz": -8, "alt": 157},
    "Texas": {"lat": 32.75, "lon": -97.08, "tz": -6, "alt": 551},
    "Arlington": {"lat": 32.75, "lon": -97.08, "tz": -6, "alt": 551},

    # Default for unknown cities
    "Unknown": {"lat": 39.0, "lon": -98.0, "tz": -6, "alt": 500},
}


# Team city mapping for common team names
TEAM_CITIES = {
    # NBA
    "Lakers": "Los Angeles", "Clippers": "Los Angeles", "Celtics": "Boston",
    "Knicks": "New York", "Nets": "Brooklyn", "76ers": "Philadelphia",
    "Raptors": "Toronto", "Heat": "Miami", "Magic": "Orlando",
    "Hawks": "Atlanta", "Hornets": "Charlotte", "Wizards": "Washington",
    "Cavaliers": "Cleveland", "Pistons": "Detroit", "Pacers": "Indianapolis",
    "Bulls": "Chicago", "Bucks": "Milwaukee", "Timberwolves": "Minneapolis",
    "Thunder": "Oklahoma City", "Spurs": "San Antonio", "Mavericks": "Dallas",
    "Rockets": "Houston", "Grizzlies": "Memphis", "Pelicans": "New Orleans",
    "Nuggets": "Denver", "Jazz": "Salt Lake City", "Suns": "Phoenix",
    "Trail Blazers": "Portland", "Blazers": "Portland", "SuperSonics": "Seattle",
    "Kings": "Sacramento", "Warriors": "San Francisco",

    # NFL
    "Patriots": "Boston", "Bills": "Buffalo", "Dolphins": "Miami",
    "Jets": "New York", "Giants": "New York", "Eagles": "Philadelphia",
    "Cowboys": "Dallas", "Commanders": "Washington", "Ravens": "Baltimore",
    "Steelers": "Pittsburgh", "Browns": "Cleveland", "Bengals": "Cincinnati",
    "Colts": "Indianapolis", "Titans": "Nashville", "Texans": "Houston",
    "Jaguars": "Jacksonville", "Chiefs": "Kansas City", "Raiders": "Las Vegas",
    "Broncos": "Denver", "Chargers": "Los Angeles", "Packers": "Green Bay",
    "Vikings": "Minneapolis", "Bears": "Chicago", "Lions": "Detroit",
    "Saints": "New Orleans", "Falcons": "Atlanta", "Buccaneers": "Tampa",
    "Panthers": "Charlotte", "49ers": "San Francisco", "Seahawks": "Seattle",
    "Rams": "Los Angeles", "Cardinals": "Phoenix",

    # MLB
    "Red Sox": "Boston", "Yankees": "New York", "Blue Jays": "Toronto",
    "Rays": "Tampa", "Orioles": "Baltimore", "White Sox": "Chicago",
    "Guardians": "Cleveland", "Tigers": "Detroit", "Royals": "Kansas City",
    "Twins": "Minneapolis", "Astros": "Houston", "Angels": "Anaheim",
    "Athletics": "Oakland", "Mariners": "Seattle", "Rangers": "Arlington",
    "Braves": "Atlanta", "Marlins": "Miami", "Mets": "New York",
    "Phillies": "Philadelphia", "Nationals": "Washington", "Cubs": "Chicago",
    "Reds": "Cincinnati", "Brewers": "Milwaukee", "Pirates": "Pittsburgh",
    "Cardinals": "St. Louis", "Diamondbacks": "Phoenix", "Rockies": "Denver",
    "Dodgers": "Los Angeles", "Padres": "San Diego", "Giants": "San Francisco",
}


# Known rivalries
RIVALRIES = {
    "NBA": [
        ("Lakers", "Celtics", "Historic NBA Rivalry"),
        ("Bulls", "Pistons", "Bad Boys Rivalry"),
        ("Knicks", "Heat", "90s Playoff Battles"),
        ("Lakers", "Clippers", "LA Battle"),
        ("Celtics", "76ers", "Atlantic Division"),
        ("Warriors", "Cavaliers", "Finals Rivalry"),
        ("Mavericks", "Spurs", "Texas Rivalry"),
    ],
    "NFL": [
        ("Cowboys", "Eagles", "NFC East Rivalry"),
        ("Cowboys", "Giants", "NFC East Rivalry"),
        ("Cowboys", "Commanders", "NFC East Rivalry"),
        ("Packers", "Bears", "Oldest NFL Rivalry"),
        ("Steelers", "Ravens", "AFC North"),
        ("Patriots", "Jets", "AFC East"),
        ("49ers", "Cowboys", "Historic Rivalry"),
        ("49ers", "Seahawks", "NFC West"),
        ("Chiefs", "Raiders", "AFC West"),
        ("Broncos", "Raiders", "AFC West"),
    ],
    "MLB": [
        ("Yankees", "Red Sox", "Greatest MLB Rivalry"),
        ("Cubs", "Cardinals", "NL Central"),
        ("Dodgers", "Giants", "West Coast Classic"),
        ("Mets", "Phillies", "NL East"),
    ],
}


# ============================================================================
# REST ANALYSIS
# ============================================================================

def calculate_rest_edge(
    home_days_rest: int,
    away_days_rest: int,
    sport: str,
    home_b2b: bool = False,
    away_b2b: bool = False
) -> Dict[str, Any]:
    """
    Calculate edge from rest differential.

    NBA rest impact (most significant):
    - Team on 0 days rest (B2B) vs rested team: -4 to -6 points
    - Team on 3+ days rest vs 1 day: +2 points

    NFL rest impact:
    - After bye week: +2.5 to 3 points historically
    - Short week (TNF): -1.5 points for away team
    """
    rest_diff = home_days_rest - away_days_rest

    # Sport-specific impact multipliers
    if sport == "NBA":
        # NBA has the most significant rest impact
        base_impact = rest_diff * 1.5  # ~1.5 points per day of rest advantage

        # Back-to-back is huge in NBA
        if away_b2b and not home_b2b:
            base_impact += 4.0
        elif home_b2b and not away_b2b:
            base_impact -= 4.0

        # Very rested (4+ days) can actually be negative (rust)
        if home_days_rest >= 4:
            base_impact -= 0.5
        if away_days_rest >= 4:
            base_impact += 0.5

        historical_ats = "58-42 (58%)" if rest_diff > 0 else "42-58 (42%)" if rest_diff < 0 else "50-50"

    elif sport == "NFL":
        # NFL bye week is significant
        base_impact = 0
        if home_days_rest >= 10:  # Bye week
            base_impact += 2.8
        elif away_days_rest >= 10:
            base_impact -= 2.8

        # Short week (TNF after Sunday)
        if away_days_rest <= 3:
            base_impact += 1.5
        if home_days_rest <= 3:
            base_impact -= 1.0  # Less impact for home team

        historical_ats = "60-40 (60%)" if home_days_rest >= 10 else "50-50"

    elif sport == "MLB":
        # MLB has less rest impact due to daily games
        base_impact = rest_diff * 0.3
        # Doubleheader fatigue
        if away_days_rest == 0:
            base_impact += 0.5

        historical_ats = "52-48" if rest_diff > 0 else "48-52" if rest_diff < 0 else "50-50"

    else:
        base_impact = rest_diff * 0.8
        historical_ats = "Unknown"

    # Calculate edge percentage (convert points to percentage)
    edge_pct = base_impact * 1.5  # Rough conversion

    # Determine advantage string
    if rest_diff > 0:
        advantage = f"HOME +{rest_diff} days"
    elif rest_diff < 0:
        advantage = f"AWAY +{abs(rest_diff)} days"
    else:
        advantage = "Even rest"

    notes = []
    if home_b2b:
        notes.append("Home team on back-to-back")
    if away_b2b:
        notes.append("Away team on back-to-back")
    if home_days_rest >= 10:
        notes.append("Home team coming off bye week")
    if away_days_rest >= 10:
        notes.append("Away team coming off bye week")

    return {
        "home_rest": home_days_rest,
        "away_rest": away_days_rest,
        "rest_differential": rest_diff,
        "advantage": advantage,
        "estimated_impact_points": round(base_impact, 1),
        "edge_percentage": round(edge_pct, 1),
        "historical_ats": historical_ats,
        "home_back_to_back": home_b2b,
        "away_back_to_back": away_b2b,
        "notes": notes if notes else ["Standard rest situation"]
    }


# ============================================================================
# TRAVEL ANALYSIS
# ============================================================================

def get_city_data(team_or_city: str) -> Dict[str, Any]:
    """Get city data for a team or city name."""
    # Try direct city lookup
    if team_or_city in CITY_DATA:
        return CITY_DATA[team_or_city]

    # Try team name lookup
    for team, city in TEAM_CITIES.items():
        if team.lower() in team_or_city.lower():
            return CITY_DATA.get(city, CITY_DATA["Unknown"])

    # Try partial city match
    for city in CITY_DATA:
        if city.lower() in team_or_city.lower():
            return CITY_DATA[city]

    return CITY_DATA["Unknown"]


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """Calculate distance between two points in miles using Haversine formula."""
    R = 3959  # Earth's radius in miles

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return int(R * c)


def calculate_travel_edge(
    away_team: str,
    home_team: str,
    away_origin: Optional[str] = None,
    game_time: Optional[str] = None,
    sport: str = "NBA"
) -> Dict[str, Any]:
    """
    Calculate edge from travel factors.

    Key factors:
    - West to East travel (worst): body clock issue, early games feel earlier
    - Distance over 1500 miles: fatigue factor
    - Altitude change to Denver/Mexico City: affects cardio
    - Back-to-back road games: compound fatigue
    """
    # Get city data
    home_data = get_city_data(home_team)
    origin = away_origin if away_origin else away_team
    away_data = get_city_data(origin)

    # Calculate distance
    distance = calculate_distance(
        away_data["lat"], away_data["lon"],
        home_data["lat"], home_data["lon"]
    )

    # Time zones crossed
    tz_diff = abs(home_data["tz"] - away_data["tz"])

    # Direction of travel
    if away_data["tz"] < home_data["tz"]:
        direction = "west_to_east"
        direction_label = "West → East (hardest)"
    elif away_data["tz"] > home_data["tz"]:
        direction = "east_to_west"
        direction_label = "East → West"
    else:
        direction = "same"
        direction_label = "Same time zone"

    # Altitude change
    altitude_change = home_data["alt"] - away_data["alt"]
    home_altitude = home_data["alt"]

    # Calculate impact
    travel_impact = 0.0
    notes = []

    # Distance impact
    if distance >= 2500:
        travel_impact += 2.5
        notes.append(f"Long distance travel ({distance} miles)")
    elif distance >= 1500:
        travel_impact += 1.5
        notes.append(f"Significant travel ({distance} miles)")
    elif distance >= 500:
        travel_impact += 0.5

    # Time zone impact (West to East is worst)
    if direction == "west_to_east" and tz_diff >= 2:
        travel_impact += tz_diff * 0.8
        notes.append(f"West to East travel ({tz_diff} time zones) - body clock disadvantage")
    elif direction == "east_to_west" and tz_diff >= 2:
        travel_impact += tz_diff * 0.4
        notes.append(f"East to West travel ({tz_diff} time zones)")

    # Altitude impact (Denver is king)
    if home_altitude >= 5000:
        altitude_impact = 2.0 if sport in ["NBA", "NFL"] else 1.5
        travel_impact += altitude_impact
        notes.append(f"High altitude game ({home_altitude} ft) - cardio disadvantage")
    elif home_altitude >= 4000:
        travel_impact += 1.0
        notes.append(f"Elevated venue ({home_altitude} ft)")

    # Early game for West Coast team traveling East
    if game_time and direction == "west_to_east":
        try:
            hour = int(game_time.split(":")[0])
            if hour <= 13:  # 1 PM or earlier Eastern = 10 AM Pacific
                travel_impact += 1.0
                notes.append("Early tip for West Coast team")
        except (ValueError, IndexError):
            pass

    # Convert to edge percentage
    edge_pct = travel_impact * 1.5

    # Historical ATS for long travel
    if distance >= 2000:
        historical = "Teams traveling 2000+ mi cover 46% ATS"
    elif distance >= 1000:
        historical = "Teams traveling 1000+ mi cover 48% ATS"
    else:
        historical = "Minimal travel impact"

    return {
        "distance_miles": distance,
        "time_zones_crossed": tz_diff,
        "direction": direction,
        "direction_label": direction_label,
        "altitude_change": altitude_change,
        "home_altitude": home_altitude,
        "estimated_impact_points": round(travel_impact, 1),
        "edge_percentage": round(edge_pct, 1),
        "favors": "HOME" if travel_impact > 0 else "NEUTRAL",
        "historical_ats": historical,
        "notes": notes if notes else ["Minimal travel factors"]
    }


# ============================================================================
# MOTIVATION ANALYSIS
# ============================================================================

def check_rivalry(home_team: str, away_team: str, sport: str) -> Optional[Tuple[str, str]]:
    """Check if this is a rivalry game."""
    sport_rivalries = RIVALRIES.get(sport, [])

    for team1, team2, name in sport_rivalries:
        if (team1.lower() in home_team.lower() or team1.lower() in away_team.lower()) and \
           (team2.lower() in home_team.lower() or team2.lower() in away_team.lower()):
            return (name, "Both teams motivated - rivalry intensity")

    return None


def calculate_motivation_edge(
    home_team: str,
    away_team: str,
    sport: str,
    is_revenge: bool = False,
    revenge_team: Optional[str] = None,
    revenge_reason: Optional[str] = None,
    is_lookahead: bool = False,
    lookahead_team: Optional[str] = None,
    lookahead_opponent: Optional[str] = None,
    is_letdown: bool = False,
    letdown_team: Optional[str] = None,
    letdown_reason: Optional[str] = None,
    is_elimination: bool = False,
    elimination_team: Optional[str] = None,
    nothing_to_play_for: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyze motivational factors.

    REVENGE GAMES: +1.5 to +2 points for motivated team
    LOOKAHEAD SPOTS: -2 to -3 points for distracted team
    LETDOWN SPOTS: -1.5 to -2 points for team after emotional win
    ELIMINATION: Underdog covers more often (+3-4% edge)
    """
    factors = []
    net_edge_home = 0.0

    # Check rivalry
    rivalry = check_rivalry(home_team, away_team, sport)
    if rivalry:
        factors.append({
            "type": "RIVALRY",
            "teams": "Both",
            "impact_points": 0,
            "reason": rivalry[0],
            "notes": rivalry[1]
        })

    # Revenge game
    if is_revenge and revenge_team:
        revenge_impact = 2.0
        is_home_revenge = revenge_team.lower() in home_team.lower()

        if is_home_revenge:
            net_edge_home += revenge_impact
        else:
            net_edge_home -= revenge_impact

        factors.append({
            "type": "REVENGE",
            "team": revenge_team,
            "impact_points": revenge_impact if is_home_revenge else -revenge_impact,
            "reason": revenge_reason or "Revenge motivation",
            "notes": f"{revenge_team} extra motivated"
        })

    # Lookahead spot (distraction)
    if is_lookahead and lookahead_team:
        lookahead_impact = -2.5  # Negative because team is distracted
        is_home_lookahead = lookahead_team.lower() in home_team.lower()

        if is_home_lookahead:
            net_edge_home += lookahead_impact  # Home team distracted = negative home edge
        else:
            net_edge_home -= lookahead_impact  # Away team distracted = positive home edge

        factors.append({
            "type": "LOOKAHEAD",
            "team": lookahead_team,
            "impact_points": lookahead_impact if is_home_lookahead else -lookahead_impact,
            "reason": f"Big game vs {lookahead_opponent} coming up",
            "notes": f"{lookahead_team} may be looking ahead - trap game potential"
        })

    # Letdown spot
    if is_letdown and letdown_team:
        letdown_impact = -1.8
        is_home_letdown = letdown_team.lower() in home_team.lower()

        if is_home_letdown:
            net_edge_home += letdown_impact
        else:
            net_edge_home -= letdown_impact

        factors.append({
            "type": "LETDOWN",
            "team": letdown_team,
            "impact_points": letdown_impact if is_home_letdown else -letdown_impact,
            "reason": letdown_reason or "After emotional game",
            "notes": f"{letdown_team} potential letdown after big game"
        })

    # Elimination game
    if is_elimination:
        factors.append({
            "type": "ELIMINATION",
            "team": elimination_team or "Underdog",
            "impact_points": 0,
            "reason": "Must-win game",
            "notes": "Underdogs historically cover in elimination games (+4% edge)"
        })

    # Nothing to play for
    if nothing_to_play_for:
        nothing_impact = -2.0
        is_home_nothing = nothing_to_play_for.lower() in home_team.lower()

        if is_home_nothing:
            net_edge_home += nothing_impact
        else:
            net_edge_home -= nothing_impact

        factors.append({
            "type": "NOTHING_TO_PLAY_FOR",
            "team": nothing_to_play_for,
            "impact_points": nothing_impact if is_home_nothing else -nothing_impact,
            "reason": "Playoff position locked/eliminated",
            "notes": f"{nothing_to_play_for} has no motivation - fade opportunity"
        })

    # Determine who edge favors
    if net_edge_home > 0.5:
        favors = home_team
    elif net_edge_home < -0.5:
        favors = away_team
    else:
        favors = "Neither"

    # Calculate confidence based on number and strength of factors
    confidence = min(0.3 + len(factors) * 0.15 + abs(net_edge_home) * 0.05, 0.95)

    return {
        "factors": factors,
        "net_motivation_edge_home": round(net_edge_home, 1),
        "edge_percentage": round(net_edge_home * 1.5, 1),
        "favors": favors,
        "confidence": round(confidence, 2),
        "factor_count": len(factors)
    }


# ============================================================================
# COMBINED SITUATION ANALYSIS
# ============================================================================

def get_full_situation_analysis(
    db: Session,
    game_id: Optional[int] = None,
    home_team: Optional[str] = None,
    away_team: Optional[str] = None,
    sport: str = "NBA",
    game_date: Optional[datetime] = None,
    game_time: Optional[str] = None,
    # Rest parameters
    home_days_rest: int = 2,
    away_days_rest: int = 2,
    home_b2b: bool = False,
    away_b2b: bool = False,
    # Travel parameters
    away_origin: Optional[str] = None,
    # Motivation parameters
    is_revenge: bool = False,
    revenge_team: Optional[str] = None,
    revenge_reason: Optional[str] = None,
    is_lookahead: bool = False,
    lookahead_team: Optional[str] = None,
    lookahead_opponent: Optional[str] = None,
    is_letdown: bool = False,
    letdown_team: Optional[str] = None,
    letdown_reason: Optional[str] = None,
    is_elimination: bool = False,
    nothing_to_play_for: Optional[str] = None
) -> Dict[str, Any]:
    """
    Combine all situational factors for a game.
    """
    if not home_team or not away_team:
        return {"error": "Home and away teams required"}

    # Calculate individual edges
    rest_analysis = calculate_rest_edge(
        home_days_rest, away_days_rest, sport, home_b2b, away_b2b
    )

    travel_analysis = calculate_travel_edge(
        away_team, home_team, away_origin, game_time, sport
    )

    motivation_analysis = calculate_motivation_edge(
        home_team, away_team, sport,
        is_revenge=is_revenge, revenge_team=revenge_team, revenge_reason=revenge_reason,
        is_lookahead=is_lookahead, lookahead_team=lookahead_team, lookahead_opponent=lookahead_opponent,
        is_letdown=is_letdown, letdown_team=letdown_team, letdown_reason=letdown_reason,
        is_elimination=is_elimination, nothing_to_play_for=nothing_to_play_for
    )

    # Combine edges (all in terms of home team advantage)
    rest_edge = rest_analysis["edge_percentage"]
    travel_edge = travel_analysis["edge_percentage"]  # Already favors home
    motivation_edge = motivation_analysis["edge_percentage"]

    combined_edge = rest_edge + travel_edge + motivation_edge

    # Build summary of factors
    factors_summary = []

    if abs(rest_edge) >= 1.0:
        direction = "advantage" if rest_edge > 0 else "disadvantage"
        team = home_team if rest_edge > 0 else away_team
        factors_summary.append(f"{team} rest {direction}: {rest_edge:+.1f}%")

    if travel_edge >= 1.0:
        factors_summary.append(f"{away_team} travel fatigue: +{travel_edge:.1f}% home edge")

    for factor in motivation_analysis["factors"]:
        if abs(factor.get("impact_points", 0)) >= 1.0:
            factors_summary.append(f"{factor['type']}: {factor['reason']}")

    # Calculate confidence
    factor_count = len(factors_summary)
    confidence = min(0.4 + factor_count * 0.12 + abs(combined_edge) * 0.02, 0.92)

    # Generate recommendation
    if combined_edge >= 5:
        recommendation = f"STRONG LEAN {home_team}"
    elif combined_edge >= 2:
        recommendation = f"LEAN {home_team}"
    elif combined_edge <= -5:
        recommendation = f"STRONG LEAN {away_team}"
    elif combined_edge <= -2:
        recommendation = f"LEAN {away_team}"
    else:
        recommendation = "No significant situational edge"

    return {
        "game_id": game_id,
        "matchup": f"{away_team} @ {home_team}",
        "home_team": home_team,
        "away_team": away_team,
        "sport": sport,
        "date": game_date.isoformat() if game_date else None,

        "rest": rest_analysis,
        "travel": travel_analysis,
        "motivation": motivation_analysis,

        "combined": {
            "rest_edge_home": round(rest_edge, 1),
            "travel_edge_home": round(travel_edge, 1),
            "motivation_edge_home": round(motivation_edge, 1),
            "total_edge": round(combined_edge, 1),
            "favors": home_team if combined_edge > 0 else away_team if combined_edge < 0 else "Neither",
            "confidence": round(confidence, 2),
            "factors_summary": factors_summary,
            "recommendation": recommendation
        }
    }


# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

def save_game_situation(db: Session, analysis: Dict[str, Any]) -> GameSituation:
    """Save a game situation analysis to the database."""
    situation = GameSituation(
        game_id=analysis.get("game_id"),
        sport=analysis.get("sport", ""),
        home_team=analysis.get("home_team", ""),
        away_team=analysis.get("away_team", ""),
        game_date=datetime.fromisoformat(analysis["date"]) if analysis.get("date") else datetime.utcnow(),

        # Rest
        home_days_rest=analysis.get("rest", {}).get("home_rest"),
        away_days_rest=analysis.get("rest", {}).get("away_rest"),
        rest_advantage=analysis.get("rest", {}).get("rest_differential"),
        home_back_to_back=analysis.get("rest", {}).get("home_back_to_back", False),
        away_back_to_back=analysis.get("rest", {}).get("away_back_to_back", False),

        # Travel
        away_travel_miles=analysis.get("travel", {}).get("distance_miles"),
        away_time_zones_crossed=analysis.get("travel", {}).get("time_zones_crossed"),
        away_direction=analysis.get("travel", {}).get("direction"),
        home_altitude_ft=analysis.get("travel", {}).get("home_altitude"),

        # Edges
        rest_edge_home=analysis.get("combined", {}).get("rest_edge_home"),
        travel_edge_home=analysis.get("combined", {}).get("travel_edge_home"),
        motivation_edge_home=analysis.get("combined", {}).get("motivation_edge_home"),
        total_situation_edge=analysis.get("combined", {}).get("total_edge"),
        confidence=analysis.get("combined", {}).get("confidence"),
        recommendation=analysis.get("combined", {}).get("recommendation"),
    )

    db.add(situation)
    db.commit()
    db.refresh(situation)
    return situation


def get_historical_situation(db: Session, situation_type: str) -> Optional[Dict[str, Any]]:
    """Get historical data for a specific situation type."""
    hist = db.query(HistoricalSituation).filter(
        HistoricalSituation.situation_type == situation_type
    ).first()

    if not hist:
        return None

    return {
        "situation_type": hist.situation_type,
        "situation_name": hist.situation_name,
        "sport": hist.sport,
        "sample_size": hist.sample_size,
        "ats_record": f"{hist.ats_wins}-{hist.ats_losses}" + (f"-{hist.ats_pushes}" if hist.ats_pushes else ""),
        "win_percentage": hist.win_percentage,
        "roi_percentage": hist.roi_percentage,
        "edge_points": hist.edge_points,
        "description": hist.description,
        "notes": hist.notes
    }


def get_all_historical_situations(
    db: Session,
    sport: Optional[str] = None,
    min_win_pct: Optional[float] = None
) -> List[Dict[str, Any]]:
    """Get all historical situations, optionally filtered."""
    query = db.query(HistoricalSituation)

    if sport:
        query = query.filter(
            (HistoricalSituation.sport == sport) | (HistoricalSituation.sport == "ALL")
        )

    if min_win_pct:
        query = query.filter(HistoricalSituation.win_percentage >= min_win_pct)

    situations = query.order_by(desc(HistoricalSituation.win_percentage)).all()

    return [
        {
            "situation_type": s.situation_type,
            "situation_name": s.situation_name,
            "sport": s.sport,
            "sample_size": s.sample_size,
            "ats_record": f"{s.ats_wins}-{s.ats_losses}",
            "win_percentage": s.win_percentage,
            "roi_percentage": s.roi_percentage,
            "edge_points": s.edge_points,
            "notes": s.notes
        }
        for s in situations
    ]
