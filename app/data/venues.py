"""
Venue Coordinates Database

Comprehensive database of sports venues with coordinates, dome status,
and other relevant information for weather impact calculations.
"""

from typing import Dict, Any, Optional, List

# Dome types
OUTDOOR = "outdoor"
DOME = "dome"
RETRACTABLE = "retractable"

# Surface types
GRASS = "grass"
TURF = "turf"
ARTIFICIAL = "artificial"


# =============================================================================
# MLB STADIUMS (30 teams)
# =============================================================================
MLB_VENUES: Dict[str, Dict[str, Any]] = {
    # American League East
    "yankee_stadium": {
        "name": "Yankee Stadium",
        "team": "New York Yankees",
        "team_abbr": "NYY",
        "city": "Bronx, NY",
        "lat": 40.8296,
        "lon": -73.9262,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 55,
        "timezone": "America/New_York",
        "outfield_direction": 87,  # CF faces ENE
        "left_field_distance": 318,
        "center_field_distance": 408,
        "right_field_distance": 314,
        "capacity": 46537,
    },
    "fenway_park": {
        "name": "Fenway Park",
        "team": "Boston Red Sox",
        "team_abbr": "BOS",
        "city": "Boston, MA",
        "lat": 42.3467,
        "lon": -71.0972,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 21,
        "timezone": "America/New_York",
        "outfield_direction": 67,  # CF faces ENE
        "left_field_distance": 310,  # Green Monster
        "center_field_distance": 390,
        "right_field_distance": 302,
        "capacity": 37755,
    },
    "tropicana_field": {
        "name": "Tropicana Field",
        "team": "Tampa Bay Rays",
        "team_abbr": "TB",
        "city": "St. Petersburg, FL",
        "lat": 27.7682,
        "lon": -82.6534,
        "dome_type": DOME,
        "surface": TURF,
        "altitude_ft": 44,
        "timezone": "America/New_York",
        "outfield_direction": 0,
        "left_field_distance": 315,
        "center_field_distance": 404,
        "right_field_distance": 322,
        "capacity": 25000,
    },
    "rogers_centre": {
        "name": "Rogers Centre",
        "team": "Toronto Blue Jays",
        "team_abbr": "TOR",
        "city": "Toronto, ON",
        "lat": 43.6414,
        "lon": -79.3894,
        "dome_type": RETRACTABLE,
        "surface": TURF,
        "altitude_ft": 269,
        "timezone": "America/Toronto",
        "outfield_direction": 0,
        "left_field_distance": 328,
        "center_field_distance": 400,
        "right_field_distance": 328,
        "capacity": 49282,
    },
    "camden_yards": {
        "name": "Oriole Park at Camden Yards",
        "team": "Baltimore Orioles",
        "team_abbr": "BAL",
        "city": "Baltimore, MD",
        "lat": 39.2839,
        "lon": -76.6217,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 20,
        "timezone": "America/New_York",
        "outfield_direction": 45,  # CF faces NE
        "left_field_distance": 333,
        "center_field_distance": 400,
        "right_field_distance": 318,
        "capacity": 45971,
    },
    # American League Central
    "guaranteed_rate_field": {
        "name": "Guaranteed Rate Field",
        "team": "Chicago White Sox",
        "team_abbr": "CWS",
        "city": "Chicago, IL",
        "lat": 41.8299,
        "lon": -87.6338,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 595,
        "timezone": "America/Chicago",
        "outfield_direction": 0,  # CF faces N
        "left_field_distance": 330,
        "center_field_distance": 400,
        "right_field_distance": 335,
        "capacity": 40615,
    },
    "progressive_field": {
        "name": "Progressive Field",
        "team": "Cleveland Guardians",
        "team_abbr": "CLE",
        "city": "Cleveland, OH",
        "lat": 41.4962,
        "lon": -81.6852,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 653,
        "timezone": "America/New_York",
        "outfield_direction": 0,
        "left_field_distance": 325,
        "center_field_distance": 405,
        "right_field_distance": 325,
        "capacity": 34788,
    },
    "comerica_park": {
        "name": "Comerica Park",
        "team": "Detroit Tigers",
        "team_abbr": "DET",
        "city": "Detroit, MI",
        "lat": 42.3390,
        "lon": -83.0485,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 600,
        "timezone": "America/Detroit",
        "outfield_direction": 0,
        "left_field_distance": 345,
        "center_field_distance": 420,
        "right_field_distance": 330,
        "capacity": 41083,
    },
    "kauffman_stadium": {
        "name": "Kauffman Stadium",
        "team": "Kansas City Royals",
        "team_abbr": "KC",
        "city": "Kansas City, MO",
        "lat": 39.0517,
        "lon": -94.4803,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 820,
        "timezone": "America/Chicago",
        "outfield_direction": 0,
        "left_field_distance": 330,
        "center_field_distance": 410,
        "right_field_distance": 330,
        "capacity": 37903,
    },
    "target_field": {
        "name": "Target Field",
        "team": "Minnesota Twins",
        "team_abbr": "MIN",
        "city": "Minneapolis, MN",
        "lat": 44.9817,
        "lon": -93.2776,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 841,
        "timezone": "America/Chicago",
        "outfield_direction": 0,
        "left_field_distance": 339,
        "center_field_distance": 404,
        "right_field_distance": 328,
        "capacity": 38544,
    },
    # American League West
    "minute_maid_park": {
        "name": "Minute Maid Park",
        "team": "Houston Astros",
        "team_abbr": "HOU",
        "city": "Houston, TX",
        "lat": 29.7573,
        "lon": -95.3555,
        "dome_type": RETRACTABLE,
        "surface": GRASS,
        "altitude_ft": 40,
        "timezone": "America/Chicago",
        "outfield_direction": 0,
        "left_field_distance": 315,
        "center_field_distance": 409,
        "right_field_distance": 326,
        "capacity": 41168,
    },
    "angel_stadium": {
        "name": "Angel Stadium",
        "team": "Los Angeles Angels",
        "team_abbr": "LAA",
        "city": "Anaheim, CA",
        "lat": 33.8003,
        "lon": -117.8827,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 160,
        "timezone": "America/Los_Angeles",
        "outfield_direction": 0,
        "left_field_distance": 330,
        "center_field_distance": 396,
        "right_field_distance": 330,
        "capacity": 45517,
    },
    "oakland_coliseum": {
        "name": "Oakland Coliseum",
        "team": "Oakland Athletics",
        "team_abbr": "OAK",
        "city": "Oakland, CA",
        "lat": 37.7516,
        "lon": -122.2005,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 15,
        "timezone": "America/Los_Angeles",
        "outfield_direction": 180,  # CF faces S
        "left_field_distance": 330,
        "center_field_distance": 400,
        "right_field_distance": 330,
        "capacity": 46847,
    },
    "t_mobile_park": {
        "name": "T-Mobile Park",
        "team": "Seattle Mariners",
        "team_abbr": "SEA",
        "city": "Seattle, WA",
        "lat": 47.5914,
        "lon": -122.3325,
        "dome_type": RETRACTABLE,
        "surface": GRASS,
        "altitude_ft": 17,
        "timezone": "America/Los_Angeles",
        "outfield_direction": 0,
        "left_field_distance": 331,
        "center_field_distance": 401,
        "right_field_distance": 326,
        "capacity": 47929,
    },
    "globe_life_field": {
        "name": "Globe Life Field",
        "team": "Texas Rangers",
        "team_abbr": "TEX",
        "city": "Arlington, TX",
        "lat": 32.7473,
        "lon": -97.0849,
        "dome_type": RETRACTABLE,
        "surface": TURF,
        "altitude_ft": 551,
        "timezone": "America/Chicago",
        "outfield_direction": 0,
        "left_field_distance": 329,
        "center_field_distance": 407,
        "right_field_distance": 326,
        "capacity": 40300,
    },
    # National League East
    "truist_park": {
        "name": "Truist Park",
        "team": "Atlanta Braves",
        "team_abbr": "ATL",
        "city": "Atlanta, GA",
        "lat": 33.8907,
        "lon": -84.4677,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 1050,
        "timezone": "America/New_York",
        "outfield_direction": 0,
        "left_field_distance": 335,
        "center_field_distance": 400,
        "right_field_distance": 325,
        "capacity": 41084,
    },
    "loandepot_park": {
        "name": "loanDepot park",
        "team": "Miami Marlins",
        "team_abbr": "MIA",
        "city": "Miami, FL",
        "lat": 25.7781,
        "lon": -80.2196,
        "dome_type": RETRACTABLE,
        "surface": GRASS,
        "altitude_ft": 10,
        "timezone": "America/New_York",
        "outfield_direction": 0,
        "left_field_distance": 344,
        "center_field_distance": 407,
        "right_field_distance": 335,
        "capacity": 36742,
    },
    "citi_field": {
        "name": "Citi Field",
        "team": "New York Mets",
        "team_abbr": "NYM",
        "city": "Queens, NY",
        "lat": 40.7571,
        "lon": -73.8458,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 15,
        "timezone": "America/New_York",
        "outfield_direction": 0,
        "left_field_distance": 335,
        "center_field_distance": 408,
        "right_field_distance": 330,
        "capacity": 41922,
    },
    "citizens_bank_park": {
        "name": "Citizens Bank Park",
        "team": "Philadelphia Phillies",
        "team_abbr": "PHI",
        "city": "Philadelphia, PA",
        "lat": 39.9061,
        "lon": -75.1665,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 15,
        "timezone": "America/New_York",
        "outfield_direction": 0,
        "left_field_distance": 329,
        "center_field_distance": 401,
        "right_field_distance": 330,
        "capacity": 42792,
    },
    "nationals_park": {
        "name": "Nationals Park",
        "team": "Washington Nationals",
        "team_abbr": "WSH",
        "city": "Washington, DC",
        "lat": 38.8730,
        "lon": -77.0074,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 25,
        "timezone": "America/New_York",
        "outfield_direction": 0,
        "left_field_distance": 336,
        "center_field_distance": 403,
        "right_field_distance": 335,
        "capacity": 41339,
    },
    # National League Central
    "wrigley_field": {
        "name": "Wrigley Field",
        "team": "Chicago Cubs",
        "team_abbr": "CHC",
        "city": "Chicago, IL",
        "lat": 41.9484,
        "lon": -87.6553,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 600,
        "timezone": "America/Chicago",
        "outfield_direction": 0,  # CF faces N - wind off Lake Michigan is crucial
        "left_field_distance": 355,
        "center_field_distance": 400,
        "right_field_distance": 353,
        "capacity": 41649,
        "notes": "Wind off Lake Michigan heavily impacts play",
    },
    "great_american_ball_park": {
        "name": "Great American Ball Park",
        "team": "Cincinnati Reds",
        "team_abbr": "CIN",
        "city": "Cincinnati, OH",
        "lat": 39.0979,
        "lon": -84.5086,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 535,
        "timezone": "America/New_York",
        "outfield_direction": 180,  # CF faces S
        "left_field_distance": 328,
        "center_field_distance": 404,
        "right_field_distance": 325,
        "capacity": 42319,
    },
    "american_family_field": {
        "name": "American Family Field",
        "team": "Milwaukee Brewers",
        "team_abbr": "MIL",
        "city": "Milwaukee, WI",
        "lat": 43.0280,
        "lon": -87.9712,
        "dome_type": RETRACTABLE,
        "surface": GRASS,
        "altitude_ft": 620,
        "timezone": "America/Chicago",
        "outfield_direction": 0,
        "left_field_distance": 344,
        "center_field_distance": 400,
        "right_field_distance": 345,
        "capacity": 41900,
    },
    "pnc_park": {
        "name": "PNC Park",
        "team": "Pittsburgh Pirates",
        "team_abbr": "PIT",
        "city": "Pittsburgh, PA",
        "lat": 40.4469,
        "lon": -80.0057,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 730,
        "timezone": "America/New_York",
        "outfield_direction": 180,
        "left_field_distance": 325,
        "center_field_distance": 399,
        "right_field_distance": 320,
        "capacity": 38362,
    },
    "busch_stadium": {
        "name": "Busch Stadium",
        "team": "St. Louis Cardinals",
        "team_abbr": "STL",
        "city": "St. Louis, MO",
        "lat": 38.6226,
        "lon": -90.1928,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 455,
        "timezone": "America/Chicago",
        "outfield_direction": 0,
        "left_field_distance": 336,
        "center_field_distance": 400,
        "right_field_distance": 335,
        "capacity": 45538,
    },
    # National League West
    "chase_field": {
        "name": "Chase Field",
        "team": "Arizona Diamondbacks",
        "team_abbr": "ARI",
        "city": "Phoenix, AZ",
        "lat": 33.4453,
        "lon": -112.0667,
        "dome_type": RETRACTABLE,
        "surface": GRASS,
        "altitude_ft": 1100,
        "timezone": "America/Phoenix",
        "outfield_direction": 0,
        "left_field_distance": 330,
        "center_field_distance": 407,
        "right_field_distance": 335,
        "capacity": 48686,
    },
    "coors_field": {
        "name": "Coors Field",
        "team": "Colorado Rockies",
        "team_abbr": "COL",
        "city": "Denver, CO",
        "lat": 39.7559,
        "lon": -104.9942,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 5200,  # Mile high - HUGE impact
        "timezone": "America/Denver",
        "outfield_direction": 0,
        "left_field_distance": 347,
        "center_field_distance": 415,
        "right_field_distance": 350,
        "capacity": 50144,
        "notes": "High altitude significantly increases offense",
    },
    "dodger_stadium": {
        "name": "Dodger Stadium",
        "team": "Los Angeles Dodgers",
        "team_abbr": "LAD",
        "city": "Los Angeles, CA",
        "lat": 34.0739,
        "lon": -118.2400,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 515,
        "timezone": "America/Los_Angeles",
        "outfield_direction": 0,
        "left_field_distance": 330,
        "center_field_distance": 395,
        "right_field_distance": 330,
        "capacity": 56000,
    },
    "petco_park": {
        "name": "Petco Park",
        "team": "San Diego Padres",
        "team_abbr": "SD",
        "city": "San Diego, CA",
        "lat": 32.7076,
        "lon": -117.1570,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 15,
        "timezone": "America/Los_Angeles",
        "outfield_direction": 0,
        "left_field_distance": 334,
        "center_field_distance": 396,
        "right_field_distance": 322,
        "capacity": 40209,
    },
    "oracle_park": {
        "name": "Oracle Park",
        "team": "San Francisco Giants",
        "team_abbr": "SF",
        "city": "San Francisco, CA",
        "lat": 37.7786,
        "lon": -122.3893,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 0,
        "timezone": "America/Los_Angeles",
        "outfield_direction": 45,  # CF faces NE toward bay
        "left_field_distance": 339,
        "center_field_distance": 399,
        "right_field_distance": 309,  # McCovey Cove
        "capacity": 41265,
        "notes": "Wind from SF Bay impacts fly balls",
    },
}


# =============================================================================
# NFL STADIUMS (32 teams)
# =============================================================================
NFL_VENUES: Dict[str, Dict[str, Any]] = {
    # AFC East
    "gillette_stadium": {
        "name": "Gillette Stadium",
        "team": "New England Patriots",
        "team_abbr": "NE",
        "city": "Foxborough, MA",
        "lat": 42.0909,
        "lon": -71.2643,
        "dome_type": OUTDOOR,
        "surface": TURF,
        "altitude_ft": 280,
        "timezone": "America/New_York",
        "capacity": 65878,
    },
    "highmark_stadium": {
        "name": "Highmark Stadium",
        "team": "Buffalo Bills",
        "team_abbr": "BUF",
        "city": "Orchard Park, NY",
        "lat": 42.7738,
        "lon": -78.7870,
        "dome_type": OUTDOOR,
        "surface": TURF,
        "altitude_ft": 650,
        "timezone": "America/New_York",
        "capacity": 71608,
        "notes": "Lake effect snow common",
    },
    "metlife_stadium": {
        "name": "MetLife Stadium",
        "team": "New York Jets / Giants",
        "team_abbr": "NYJ/NYG",
        "city": "East Rutherford, NJ",
        "lat": 40.8128,
        "lon": -74.0742,
        "dome_type": OUTDOOR,
        "surface": TURF,
        "altitude_ft": 50,
        "timezone": "America/New_York",
        "capacity": 82500,
    },
    "hard_rock_stadium": {
        "name": "Hard Rock Stadium",
        "team": "Miami Dolphins",
        "team_abbr": "MIA",
        "city": "Miami Gardens, FL",
        "lat": 25.9580,
        "lon": -80.2389,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 10,
        "timezone": "America/New_York",
        "capacity": 65326,
        "notes": "Partial canopy, hot/humid conditions",
    },
    # AFC North
    "acrisure_stadium": {
        "name": "Acrisure Stadium",
        "team": "Pittsburgh Steelers",
        "team_abbr": "PIT",
        "city": "Pittsburgh, PA",
        "lat": 40.4468,
        "lon": -80.0158,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 750,
        "timezone": "America/New_York",
        "capacity": 68400,
    },
    "paycor_stadium": {
        "name": "Paycor Stadium",
        "team": "Cincinnati Bengals",
        "team_abbr": "CIN",
        "city": "Cincinnati, OH",
        "lat": 39.0955,
        "lon": -84.5161,
        "dome_type": OUTDOOR,
        "surface": TURF,
        "altitude_ft": 500,
        "timezone": "America/New_York",
        "capacity": 65515,
    },
    "cleveland_browns_stadium": {
        "name": "Cleveland Browns Stadium",
        "team": "Cleveland Browns",
        "team_abbr": "CLE",
        "city": "Cleveland, OH",
        "lat": 41.5061,
        "lon": -81.6995,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 620,
        "timezone": "America/New_York",
        "capacity": 67431,
        "notes": "Lake Erie wind",
    },
    "mandt_bank_stadium": {
        "name": "M&T Bank Stadium",
        "team": "Baltimore Ravens",
        "team_abbr": "BAL",
        "city": "Baltimore, MD",
        "lat": 39.2780,
        "lon": -76.6227,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 40,
        "timezone": "America/New_York",
        "capacity": 71008,
    },
    # AFC South
    "nissan_stadium": {
        "name": "Nissan Stadium",
        "team": "Tennessee Titans",
        "team_abbr": "TEN",
        "city": "Nashville, TN",
        "lat": 36.1665,
        "lon": -86.7713,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 430,
        "timezone": "America/Chicago",
        "capacity": 69143,
    },
    "lucas_oil_stadium": {
        "name": "Lucas Oil Stadium",
        "team": "Indianapolis Colts",
        "team_abbr": "IND",
        "city": "Indianapolis, IN",
        "lat": 39.7601,
        "lon": -86.1639,
        "dome_type": RETRACTABLE,
        "surface": TURF,
        "altitude_ft": 715,
        "timezone": "America/Indiana/Indianapolis",
        "capacity": 67000,
    },
    "nrg_stadium": {
        "name": "NRG Stadium",
        "team": "Houston Texans",
        "team_abbr": "HOU",
        "city": "Houston, TX",
        "lat": 29.6847,
        "lon": -95.4107,
        "dome_type": RETRACTABLE,
        "surface": TURF,
        "altitude_ft": 50,
        "timezone": "America/Chicago",
        "capacity": 72220,
    },
    "tiaa_bank_field": {
        "name": "TIAA Bank Field",
        "team": "Jacksonville Jaguars",
        "team_abbr": "JAX",
        "city": "Jacksonville, FL",
        "lat": 30.3239,
        "lon": -81.6373,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 15,
        "timezone": "America/New_York",
        "capacity": 67814,
    },
    # AFC West
    "arrowhead_stadium": {
        "name": "Arrowhead Stadium",
        "team": "Kansas City Chiefs",
        "team_abbr": "KC",
        "city": "Kansas City, MO",
        "lat": 39.0489,
        "lon": -94.4839,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 820,
        "timezone": "America/Chicago",
        "capacity": 76416,
    },
    "empower_field": {
        "name": "Empower Field at Mile High",
        "team": "Denver Broncos",
        "team_abbr": "DEN",
        "city": "Denver, CO",
        "lat": 39.7439,
        "lon": -105.0201,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 5280,  # Mile high
        "timezone": "America/Denver",
        "capacity": 76125,
        "notes": "High altitude affects kicking and passing",
    },
    "allegiant_stadium": {
        "name": "Allegiant Stadium",
        "team": "Las Vegas Raiders",
        "team_abbr": "LV",
        "city": "Las Vegas, NV",
        "lat": 36.0909,
        "lon": -115.1833,
        "dome_type": DOME,
        "surface": GRASS,
        "altitude_ft": 2000,
        "timezone": "America/Los_Angeles",
        "capacity": 65000,
    },
    "sofi_stadium": {
        "name": "SoFi Stadium",
        "team": "Los Angeles Rams / Chargers",
        "team_abbr": "LAR/LAC",
        "city": "Inglewood, CA",
        "lat": 33.9535,
        "lon": -118.3392,
        "dome_type": DOME,  # Indoor/outdoor hybrid
        "surface": TURF,
        "altitude_ft": 100,
        "timezone": "America/Los_Angeles",
        "capacity": 70240,
    },
    # NFC East
    "lincoln_financial_field": {
        "name": "Lincoln Financial Field",
        "team": "Philadelphia Eagles",
        "team_abbr": "PHI",
        "city": "Philadelphia, PA",
        "lat": 39.9008,
        "lon": -75.1675,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 40,
        "timezone": "America/New_York",
        "capacity": 69596,
    },
    "att_stadium": {
        "name": "AT&T Stadium",
        "team": "Dallas Cowboys",
        "team_abbr": "DAL",
        "city": "Arlington, TX",
        "lat": 32.7473,
        "lon": -97.0945,
        "dome_type": RETRACTABLE,
        "surface": TURF,
        "altitude_ft": 550,
        "timezone": "America/Chicago",
        "capacity": 80000,
    },
    "fedex_field": {
        "name": "FedEx Field",
        "team": "Washington Commanders",
        "team_abbr": "WAS",
        "city": "Landover, MD",
        "lat": 38.9076,
        "lon": -76.8645,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 180,
        "timezone": "America/New_York",
        "capacity": 67717,
    },
    # NFC North
    "soldier_field": {
        "name": "Soldier Field",
        "team": "Chicago Bears",
        "team_abbr": "CHI",
        "city": "Chicago, IL",
        "lat": 41.8623,
        "lon": -87.6167,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 595,
        "timezone": "America/Chicago",
        "capacity": 61500,
        "notes": "Lake Michigan wind",
    },
    "lambeau_field": {
        "name": "Lambeau Field",
        "team": "Green Bay Packers",
        "team_abbr": "GB",
        "city": "Green Bay, WI",
        "lat": 44.5013,
        "lon": -88.0622,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 640,
        "timezone": "America/Chicago",
        "capacity": 81441,
        "notes": "Frozen Tundra - extreme cold",
    },
    "ford_field": {
        "name": "Ford Field",
        "team": "Detroit Lions",
        "team_abbr": "DET",
        "city": "Detroit, MI",
        "lat": 42.3400,
        "lon": -83.0456,
        "dome_type": DOME,
        "surface": TURF,
        "altitude_ft": 600,
        "timezone": "America/Detroit",
        "capacity": 65000,
    },
    "us_bank_stadium": {
        "name": "U.S. Bank Stadium",
        "team": "Minnesota Vikings",
        "team_abbr": "MIN",
        "city": "Minneapolis, MN",
        "lat": 44.9737,
        "lon": -93.2575,
        "dome_type": DOME,
        "surface": TURF,
        "altitude_ft": 815,
        "timezone": "America/Chicago",
        "capacity": 66860,
    },
    # NFC South
    "bank_of_america_stadium": {
        "name": "Bank of America Stadium",
        "team": "Carolina Panthers",
        "team_abbr": "CAR",
        "city": "Charlotte, NC",
        "lat": 35.2258,
        "lon": -80.8528,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 751,
        "timezone": "America/New_York",
        "capacity": 74867,
    },
    "mercedes_benz_stadium": {
        "name": "Mercedes-Benz Stadium",
        "team": "Atlanta Falcons",
        "team_abbr": "ATL",
        "city": "Atlanta, GA",
        "lat": 33.7554,
        "lon": -84.4010,
        "dome_type": RETRACTABLE,
        "surface": TURF,
        "altitude_ft": 1050,
        "timezone": "America/New_York",
        "capacity": 71000,
    },
    "caesars_superdome": {
        "name": "Caesars Superdome",
        "team": "New Orleans Saints",
        "team_abbr": "NO",
        "city": "New Orleans, LA",
        "lat": 29.9511,
        "lon": -90.0812,
        "dome_type": DOME,
        "surface": TURF,
        "altitude_ft": 10,
        "timezone": "America/Chicago",
        "capacity": 73208,
    },
    "raymond_james_stadium": {
        "name": "Raymond James Stadium",
        "team": "Tampa Bay Buccaneers",
        "team_abbr": "TB",
        "city": "Tampa, FL",
        "lat": 27.9759,
        "lon": -82.5033,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 35,
        "timezone": "America/New_York",
        "capacity": 65890,
    },
    # NFC West
    "state_farm_stadium": {
        "name": "State Farm Stadium",
        "team": "Arizona Cardinals",
        "team_abbr": "ARI",
        "city": "Glendale, AZ",
        "lat": 33.5276,
        "lon": -112.2626,
        "dome_type": RETRACTABLE,
        "surface": GRASS,
        "altitude_ft": 1100,
        "timezone": "America/Phoenix",
        "capacity": 63400,
    },
    "levis_stadium": {
        "name": "Levi's Stadium",
        "team": "San Francisco 49ers",
        "team_abbr": "SF",
        "city": "Santa Clara, CA",
        "lat": 37.4033,
        "lon": -121.9694,
        "dome_type": OUTDOOR,
        "surface": GRASS,
        "altitude_ft": 72,
        "timezone": "America/Los_Angeles",
        "capacity": 68500,
    },
    "lumen_field": {
        "name": "Lumen Field",
        "team": "Seattle Seahawks",
        "team_abbr": "SEA",
        "city": "Seattle, WA",
        "lat": 47.5952,
        "lon": -122.3316,
        "dome_type": OUTDOOR,
        "surface": TURF,
        "altitude_ft": 20,
        "timezone": "America/Los_Angeles",
        "capacity": 68740,
        "notes": "Partial roof coverage",
    },
}


# =============================================================================
# NBA ARENAS (30 teams) - Indoor but included for completeness
# =============================================================================
NBA_VENUES: Dict[str, Dict[str, Any]] = {
    "td_garden": {"name": "TD Garden", "team": "Boston Celtics", "team_abbr": "BOS", "city": "Boston, MA", "lat": 42.3662, "lon": -71.0621, "dome_type": DOME, "capacity": 19580},
    "barclays_center": {"name": "Barclays Center", "team": "Brooklyn Nets", "team_abbr": "BKN", "city": "Brooklyn, NY", "lat": 40.6826, "lon": -73.9754, "dome_type": DOME, "capacity": 17732},
    "madison_square_garden": {"name": "Madison Square Garden", "team": "New York Knicks", "team_abbr": "NYK", "city": "New York, NY", "lat": 40.7505, "lon": -73.9934, "dome_type": DOME, "capacity": 19812},
    "wells_fargo_center": {"name": "Wells Fargo Center", "team": "Philadelphia 76ers", "team_abbr": "PHI", "city": "Philadelphia, PA", "lat": 39.9012, "lon": -75.1720, "dome_type": DOME, "capacity": 21000},
    "scotiabank_arena": {"name": "Scotiabank Arena", "team": "Toronto Raptors", "team_abbr": "TOR", "city": "Toronto, ON", "lat": 43.6435, "lon": -79.3791, "dome_type": DOME, "capacity": 19800},
    "united_center": {"name": "United Center", "team": "Chicago Bulls", "team_abbr": "CHI", "city": "Chicago, IL", "lat": 41.8807, "lon": -87.6742, "dome_type": DOME, "capacity": 20917},
    "rocket_mortgage_fieldhouse": {"name": "Rocket Mortgage FieldHouse", "team": "Cleveland Cavaliers", "team_abbr": "CLE", "city": "Cleveland, OH", "lat": 41.4965, "lon": -81.6882, "dome_type": DOME, "capacity": 19432},
    "little_caesars_arena": {"name": "Little Caesars Arena", "team": "Detroit Pistons", "team_abbr": "DET", "city": "Detroit, MI", "lat": 42.3411, "lon": -83.0553, "dome_type": DOME, "capacity": 20332},
    "gainbridge_fieldhouse": {"name": "Gainbridge Fieldhouse", "team": "Indiana Pacers", "team_abbr": "IND", "city": "Indianapolis, IN", "lat": 39.7640, "lon": -86.1555, "dome_type": DOME, "capacity": 18165},
    "fiserv_forum": {"name": "Fiserv Forum", "team": "Milwaukee Bucks", "team_abbr": "MIL", "city": "Milwaukee, WI", "lat": 43.0451, "lon": -87.9175, "dome_type": DOME, "capacity": 17500},
    "state_farm_arena": {"name": "State Farm Arena", "team": "Atlanta Hawks", "team_abbr": "ATL", "city": "Atlanta, GA", "lat": 33.7573, "lon": -84.3963, "dome_type": DOME, "capacity": 18118},
    "spectrum_center": {"name": "Spectrum Center", "team": "Charlotte Hornets", "team_abbr": "CHA", "city": "Charlotte, NC", "lat": 35.2251, "lon": -80.8392, "dome_type": DOME, "capacity": 19077},
    "kaseya_center": {"name": "Kaseya Center", "team": "Miami Heat", "team_abbr": "MIA", "city": "Miami, FL", "lat": 25.7814, "lon": -80.1870, "dome_type": DOME, "capacity": 19600},
    "amway_center": {"name": "Amway Center", "team": "Orlando Magic", "team_abbr": "ORL", "city": "Orlando, FL", "lat": 28.5392, "lon": -81.3839, "dome_type": DOME, "capacity": 18846},
    "capital_one_arena": {"name": "Capital One Arena", "team": "Washington Wizards", "team_abbr": "WAS", "city": "Washington, DC", "lat": 38.8982, "lon": -77.0208, "dome_type": DOME, "capacity": 20356},
    "ball_arena": {"name": "Ball Arena", "team": "Denver Nuggets", "team_abbr": "DEN", "city": "Denver, CO", "lat": 39.7487, "lon": -105.0077, "dome_type": DOME, "capacity": 19520},
    "target_center": {"name": "Target Center", "team": "Minnesota Timberwolves", "team_abbr": "MIN", "city": "Minneapolis, MN", "lat": 44.9795, "lon": -93.2761, "dome_type": DOME, "capacity": 18978},
    "paycom_center": {"name": "Paycom Center", "team": "Oklahoma City Thunder", "team_abbr": "OKC", "city": "Oklahoma City, OK", "lat": 35.4634, "lon": -97.5151, "dome_type": DOME, "capacity": 18203},
    "moda_center": {"name": "Moda Center", "team": "Portland Trail Blazers", "team_abbr": "POR", "city": "Portland, OR", "lat": 45.5316, "lon": -122.6668, "dome_type": DOME, "capacity": 19393},
    "vivint_arena": {"name": "Vivint Arena", "team": "Utah Jazz", "team_abbr": "UTA", "city": "Salt Lake City, UT", "lat": 40.7683, "lon": -111.9011, "dome_type": DOME, "capacity": 18306},
    "chase_center": {"name": "Chase Center", "team": "Golden State Warriors", "team_abbr": "GSW", "city": "San Francisco, CA", "lat": 37.7680, "lon": -122.3877, "dome_type": DOME, "capacity": 18064},
    "crypto_com_arena": {"name": "Crypto.com Arena", "team": "Los Angeles Lakers / Clippers", "team_abbr": "LAL/LAC", "city": "Los Angeles, CA", "lat": 34.0430, "lon": -118.2673, "dome_type": DOME, "capacity": 19068},
    "footprint_center": {"name": "Footprint Center", "team": "Phoenix Suns", "team_abbr": "PHX", "city": "Phoenix, AZ", "lat": 33.4457, "lon": -112.0712, "dome_type": DOME, "capacity": 17071},
    "golden_1_center": {"name": "Golden 1 Center", "team": "Sacramento Kings", "team_abbr": "SAC", "city": "Sacramento, CA", "lat": 38.5802, "lon": -121.4997, "dome_type": DOME, "capacity": 17608},
    "american_airlines_center": {"name": "American Airlines Center", "team": "Dallas Mavericks", "team_abbr": "DAL", "city": "Dallas, TX", "lat": 32.7905, "lon": -96.8103, "dome_type": DOME, "capacity": 19200},
    "toyota_center": {"name": "Toyota Center", "team": "Houston Rockets", "team_abbr": "HOU", "city": "Houston, TX", "lat": 29.7508, "lon": -95.3621, "dome_type": DOME, "capacity": 18055},
    "smoothie_king_center": {"name": "Smoothie King Center", "team": "New Orleans Pelicans", "team_abbr": "NOP", "city": "New Orleans, LA", "lat": 29.9490, "lon": -90.0821, "dome_type": DOME, "capacity": 16867},
    "frost_bank_center": {"name": "Frost Bank Center", "team": "San Antonio Spurs", "team_abbr": "SAS", "city": "San Antonio, TX", "lat": 29.4270, "lon": -98.4375, "dome_type": DOME, "capacity": 18418},
    "delta_center": {"name": "Delta Center", "team": "Memphis Grizzlies", "team_abbr": "MEM", "city": "Memphis, TN", "lat": 35.1381, "lon": -90.0506, "dome_type": DOME, "capacity": 17794},
    "climate_pledge_arena": {"name": "Climate Pledge Arena", "team": "Seattle Storm", "team_abbr": "SEA", "city": "Seattle, WA", "lat": 47.6221, "lon": -122.3540, "dome_type": DOME, "capacity": 18100},
}


# =============================================================================
# COLLEGE FOOTBALL STADIUMS (Power 5 + Top Programs)
# =============================================================================
CFB_VENUES: Dict[str, Dict[str, Any]] = {
    "michigan_stadium": {"name": "Michigan Stadium", "team": "Michigan Wolverines", "city": "Ann Arbor, MI", "lat": 42.2658, "lon": -83.7486, "dome_type": OUTDOOR, "surface": TURF, "altitude_ft": 840, "capacity": 107601},
    "beaver_stadium": {"name": "Beaver Stadium", "team": "Penn State Nittany Lions", "city": "University Park, PA", "lat": 40.8122, "lon": -77.8561, "dome_type": OUTDOOR, "surface": GRASS, "altitude_ft": 1175, "capacity": 106572},
    "ohio_stadium": {"name": "Ohio Stadium", "team": "Ohio State Buckeyes", "city": "Columbus, OH", "lat": 40.0017, "lon": -83.0197, "dome_type": OUTDOOR, "surface": TURF, "altitude_ft": 730, "capacity": 102780},
    "kyle_field": {"name": "Kyle Field", "team": "Texas A&M Aggies", "city": "College Station, TX", "lat": 30.6100, "lon": -96.3409, "dome_type": OUTDOOR, "surface": GRASS, "altitude_ft": 310, "capacity": 102733},
    "neyland_stadium": {"name": "Neyland Stadium", "team": "Tennessee Volunteers", "city": "Knoxville, TN", "lat": 35.9550, "lon": -83.9250, "dome_type": OUTDOOR, "surface": TURF, "altitude_ft": 900, "capacity": 101915},
    "tiger_stadium": {"name": "Tiger Stadium", "team": "LSU Tigers", "city": "Baton Rouge, LA", "lat": 30.4122, "lon": -91.1837, "dome_type": OUTDOOR, "surface": GRASS, "altitude_ft": 56, "capacity": 102321},
    "bryant_denny_stadium": {"name": "Bryant-Denny Stadium", "team": "Alabama Crimson Tide", "city": "Tuscaloosa, AL", "lat": 33.2084, "lon": -87.5505, "dome_type": OUTDOOR, "surface": GRASS, "altitude_ft": 220, "capacity": 100077},
    "sanford_stadium": {"name": "Sanford Stadium", "team": "Georgia Bulldogs", "city": "Athens, GA", "lat": 33.9497, "lon": -83.3733, "dome_type": OUTDOOR, "surface": GRASS, "altitude_ft": 775, "capacity": 92746},
    "darrell_k_royal": {"name": "Darrell K Royal Memorial Stadium", "team": "Texas Longhorns", "city": "Austin, TX", "lat": 30.2836, "lon": -97.7325, "dome_type": OUTDOOR, "surface": TURF, "altitude_ft": 545, "capacity": 100119},
    "los_angeles_coliseum": {"name": "Los Angeles Memorial Coliseum", "team": "USC Trojans", "city": "Los Angeles, CA", "lat": 34.0141, "lon": -118.2879, "dome_type": OUTDOOR, "surface": GRASS, "altitude_ft": 275, "capacity": 77500},
    "rose_bowl": {"name": "Rose Bowl", "team": "UCLA Bruins", "city": "Pasadena, CA", "lat": 34.1613, "lon": -118.1676, "dome_type": OUTDOOR, "surface": GRASS, "altitude_ft": 850, "capacity": 91136},
    "memorial_stadium_clemson": {"name": "Memorial Stadium", "team": "Clemson Tigers", "city": "Clemson, SC", "lat": 34.6784, "lon": -82.8431, "dome_type": OUTDOOR, "surface": GRASS, "altitude_ft": 850, "capacity": 81500},
    "notre_dame_stadium": {"name": "Notre Dame Stadium", "team": "Notre Dame Fighting Irish", "city": "Notre Dame, IN", "lat": 41.6983, "lon": -86.2340, "dome_type": OUTDOOR, "surface": GRASS, "altitude_ft": 750, "capacity": 77622},
    "autzen_stadium": {"name": "Autzen Stadium", "team": "Oregon Ducks", "city": "Eugene, OR", "lat": 44.0584, "lon": -123.0688, "dome_type": OUTDOOR, "surface": TURF, "altitude_ft": 425, "capacity": 54000},
    "doak_campbell_stadium": {"name": "Doak Campbell Stadium", "team": "Florida State Seminoles", "city": "Tallahassee, FL", "lat": 30.4386, "lon": -84.3041, "dome_type": OUTDOOR, "surface": GRASS, "altitude_ft": 200, "capacity": 79560},
    "ben_hill_griffin_stadium": {"name": "Ben Hill Griffin Stadium", "team": "Florida Gators", "city": "Gainesville, FL", "lat": 29.6500, "lon": -82.3486, "dome_type": OUTDOOR, "surface": GRASS, "altitude_ft": 175, "capacity": 88548},
}


# =============================================================================
# SOCCER STADIUMS (Premier League + Major European)
# =============================================================================
SOCCER_VENUES: Dict[str, Dict[str, Any]] = {
    # Premier League
    "old_trafford": {"name": "Old Trafford", "team": "Manchester United", "city": "Manchester, England", "lat": 53.4631, "lon": -2.2913, "dome_type": OUTDOOR, "surface": GRASS, "capacity": 74310},
    "etihad_stadium": {"name": "Etihad Stadium", "team": "Manchester City", "city": "Manchester, England", "lat": 53.4831, "lon": -2.2004, "dome_type": OUTDOOR, "surface": GRASS, "capacity": 53400},
    "anfield": {"name": "Anfield", "team": "Liverpool", "city": "Liverpool, England", "lat": 53.4308, "lon": -2.9609, "dome_type": OUTDOOR, "surface": GRASS, "capacity": 61276},
    "stamford_bridge": {"name": "Stamford Bridge", "team": "Chelsea", "city": "London, England", "lat": 51.4817, "lon": -0.1910, "dome_type": OUTDOOR, "surface": GRASS, "capacity": 40834},
    "emirates_stadium": {"name": "Emirates Stadium", "team": "Arsenal", "city": "London, England", "lat": 51.5549, "lon": -0.1084, "dome_type": OUTDOOR, "surface": GRASS, "capacity": 60704},
    "tottenham_hotspur_stadium": {"name": "Tottenham Hotspur Stadium", "team": "Tottenham Hotspur", "city": "London, England", "lat": 51.6043, "lon": -0.0665, "dome_type": RETRACTABLE, "surface": GRASS, "capacity": 62850},
    "london_stadium": {"name": "London Stadium", "team": "West Ham United", "city": "London, England", "lat": 51.5387, "lon": -0.0166, "dome_type": OUTDOOR, "surface": GRASS, "capacity": 62500},
    "villa_park": {"name": "Villa Park", "team": "Aston Villa", "city": "Birmingham, England", "lat": 52.5092, "lon": -1.8847, "dome_type": OUTDOOR, "surface": GRASS, "capacity": 42682},
    "st_james_park": {"name": "St James' Park", "team": "Newcastle United", "city": "Newcastle, England", "lat": 54.9756, "lon": -1.6217, "dome_type": OUTDOOR, "surface": GRASS, "capacity": 52305},
    "goodison_park": {"name": "Goodison Park", "team": "Everton", "city": "Liverpool, England", "lat": 53.4388, "lon": -2.9664, "dome_type": OUTDOOR, "surface": GRASS, "capacity": 39414},
    # La Liga
    "santiago_bernabeu": {"name": "Santiago Bernabéu", "team": "Real Madrid", "city": "Madrid, Spain", "lat": 40.4531, "lon": -3.6883, "dome_type": RETRACTABLE, "surface": GRASS, "capacity": 83186},
    "camp_nou": {"name": "Camp Nou", "team": "Barcelona", "city": "Barcelona, Spain", "lat": 41.3809, "lon": 2.1228, "dome_type": OUTDOOR, "surface": GRASS, "capacity": 99354},
    "metropolitano": {"name": "Cívitas Metropolitano", "team": "Atletico Madrid", "city": "Madrid, Spain", "lat": 40.4362, "lon": -3.5995, "dome_type": OUTDOOR, "surface": GRASS, "capacity": 68456},
    # Bundesliga
    "allianz_arena": {"name": "Allianz Arena", "team": "Bayern Munich", "city": "Munich, Germany", "lat": 48.2188, "lon": 11.6247, "dome_type": OUTDOOR, "surface": GRASS, "capacity": 75024},
    "signal_iduna_park": {"name": "Signal Iduna Park", "team": "Borussia Dortmund", "city": "Dortmund, Germany", "lat": 51.4926, "lon": 7.4517, "dome_type": OUTDOOR, "surface": GRASS, "capacity": 81365},
    # Serie A
    "san_siro": {"name": "San Siro", "team": "AC Milan / Inter Milan", "city": "Milan, Italy", "lat": 45.4781, "lon": 9.1240, "dome_type": OUTDOOR, "surface": GRASS, "capacity": 75923},
    "allianz_stadium_turin": {"name": "Allianz Stadium", "team": "Juventus", "city": "Turin, Italy", "lat": 45.1097, "lon": 7.6413, "dome_type": OUTDOOR, "surface": GRASS, "capacity": 41507},
    # Ligue 1
    "parc_des_princes": {"name": "Parc des Princes", "team": "Paris Saint-Germain", "city": "Paris, France", "lat": 48.8414, "lon": 2.2530, "dome_type": OUTDOOR, "surface": GRASS, "capacity": 47929},
}


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_venue_by_name(name: str, sport: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Find a venue by name (case-insensitive partial match).

    Args:
        name: Venue name to search for
        sport: Optional sport filter (mlb, nfl, nba, cfb, soccer)

    Returns:
        Venue dict or None
    """
    name_lower = name.lower()

    venues_to_search = []
    if sport is None or sport.lower() == "mlb":
        venues_to_search.extend(MLB_VENUES.values())
    if sport is None or sport.lower() == "nfl":
        venues_to_search.extend(NFL_VENUES.values())
    if sport is None or sport.lower() == "nba":
        venues_to_search.extend(NBA_VENUES.values())
    if sport is None or sport.lower() in ("cfb", "ncaaf"):
        venues_to_search.extend(CFB_VENUES.values())
    if sport is None or sport.lower() == "soccer":
        venues_to_search.extend(SOCCER_VENUES.values())

    for venue in venues_to_search:
        if name_lower in venue["name"].lower():
            return venue

    return None


def get_venue_by_team(team: str, sport: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Find a venue by team name (case-insensitive partial match).

    Args:
        team: Team name to search for
        sport: Optional sport filter

    Returns:
        Venue dict or None
    """
    team_lower = team.lower()

    venues_to_search = []
    if sport is None or sport.lower() == "mlb":
        venues_to_search.extend(MLB_VENUES.values())
    if sport is None or sport.lower() == "nfl":
        venues_to_search.extend(NFL_VENUES.values())
    if sport is None or sport.lower() == "nba":
        venues_to_search.extend(NBA_VENUES.values())
    if sport is None or sport.lower() in ("cfb", "ncaaf"):
        venues_to_search.extend(CFB_VENUES.values())
    if sport is None or sport.lower() == "soccer":
        venues_to_search.extend(SOCCER_VENUES.values())

    for venue in venues_to_search:
        if team_lower in venue.get("team", "").lower():
            return venue
        if team_lower in venue.get("team_abbr", "").lower():
            return venue

    return None


def get_venue_by_team_abbr(abbr: str, sport: str) -> Optional[Dict[str, Any]]:
    """Find venue by team abbreviation."""
    abbr_upper = abbr.upper()

    if sport.lower() == "mlb":
        for venue in MLB_VENUES.values():
            if venue.get("team_abbr") == abbr_upper:
                return venue
    elif sport.lower() == "nfl":
        for venue in NFL_VENUES.values():
            if abbr_upper in venue.get("team_abbr", ""):
                return venue
    elif sport.lower() == "nba":
        for venue in NBA_VENUES.values():
            if abbr_upper in venue.get("team_abbr", ""):
                return venue

    return None


def get_all_venues(sport: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get all venues, optionally filtered by sport.

    Args:
        sport: Optional sport filter

    Returns:
        List of venue dicts
    """
    venues = []

    if sport is None or sport.lower() == "mlb":
        for key, venue in MLB_VENUES.items():
            venues.append({**venue, "id": key, "sport": "MLB"})
    if sport is None or sport.lower() == "nfl":
        for key, venue in NFL_VENUES.items():
            venues.append({**venue, "id": key, "sport": "NFL"})
    if sport is None or sport.lower() == "nba":
        for key, venue in NBA_VENUES.items():
            venues.append({**venue, "id": key, "sport": "NBA"})
    if sport is None or sport.lower() in ("cfb", "ncaaf"):
        for key, venue in CFB_VENUES.items():
            venues.append({**venue, "id": key, "sport": "CFB"})
    if sport is None or sport.lower() == "soccer":
        for key, venue in SOCCER_VENUES.items():
            venues.append({**venue, "id": key, "sport": "Soccer"})

    return venues


def get_outdoor_venues(sport: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get only outdoor venues where weather matters."""
    all_venues = get_all_venues(sport)
    return [v for v in all_venues if v.get("dome_type") == OUTDOOR]


def is_dome_venue(venue: Dict[str, Any]) -> bool:
    """Check if venue is a dome (weather doesn't affect play)."""
    return venue.get("dome_type") in (DOME, RETRACTABLE)


def get_venue_coordinates(venue_name: str, sport: Optional[str] = None) -> Optional[tuple]:
    """
    Get coordinates for a venue by name.

    Returns:
        Tuple of (lat, lon) or None
    """
    venue = get_venue_by_name(venue_name, sport)
    if venue:
        return (venue["lat"], venue["lon"])
    return None
