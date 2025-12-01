from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import random
import json

from app.db import (
    SessionLocal, Team, Competitor, HistoricalGameResult, 
    ELORatingHistory, PlayerStats, InjuryReport, Player
)
from app.config import TEAM_SPORTS, INDIVIDUAL_SPORTS, SUPPORTED_SPORTS


NFL_TEAMS = [
    ("Kansas City Chiefs", "KC"), ("San Francisco 49ers", "SF"), ("Philadelphia Eagles", "PHI"),
    ("Buffalo Bills", "BUF"), ("Dallas Cowboys", "DAL"), ("Miami Dolphins", "MIA"),
    ("Baltimore Ravens", "BAL"), ("Detroit Lions", "DET"), ("Cincinnati Bengals", "CIN"),
    ("Jacksonville Jaguars", "JAX"), ("Cleveland Browns", "CLE"), ("Los Angeles Rams", "LAR"),
    ("Seattle Seahawks", "SEA"), ("Green Bay Packers", "GB"), ("New York Jets", "NYJ"),
    ("Minnesota Vikings", "MIN"), ("Pittsburgh Steelers", "PIT"), ("Los Angeles Chargers", "LAC"),
    ("New Orleans Saints", "NO"), ("Denver Broncos", "DEN"), ("Tampa Bay Buccaneers", "TB"),
    ("Houston Texans", "HOU"), ("New England Patriots", "NE"), ("Indianapolis Colts", "IND"),
    ("Atlanta Falcons", "ATL"), ("Las Vegas Raiders", "LV"), ("Tennessee Titans", "TEN"),
    ("Washington Commanders", "WAS"), ("New York Giants", "NYG"), ("Carolina Panthers", "CAR"),
    ("Chicago Bears", "CHI"), ("Arizona Cardinals", "ARI")
]

NBA_TEAMS = [
    ("Boston Celtics", "BOS"), ("Denver Nuggets", "DEN"), ("Milwaukee Bucks", "MIL"),
    ("Phoenix Suns", "PHX"), ("Los Angeles Lakers", "LAL"), ("Golden State Warriors", "GSW"),
    ("Philadelphia 76ers", "PHI"), ("Miami Heat", "MIA"), ("Cleveland Cavaliers", "CLE"),
    ("Brooklyn Nets", "BKN"), ("Dallas Mavericks", "DAL"), ("Memphis Grizzlies", "MEM"),
    ("Sacramento Kings", "SAC"), ("New York Knicks", "NYK"), ("Los Angeles Clippers", "LAC"),
    ("Minnesota Timberwolves", "MIN"), ("New Orleans Pelicans", "NOP"), ("Atlanta Hawks", "ATL"),
    ("Toronto Raptors", "TOR"), ("Chicago Bulls", "CHI"), ("Oklahoma City Thunder", "OKC"),
    ("Utah Jazz", "UTA"), ("Indiana Pacers", "IND"), ("Orlando Magic", "ORL"),
    ("Washington Wizards", "WAS"), ("Portland Trail Blazers", "POR"), ("Charlotte Hornets", "CHA"),
    ("Houston Rockets", "HOU"), ("San Antonio Spurs", "SAS"), ("Detroit Pistons", "DET")
]

MLB_TEAMS = [
    ("Atlanta Braves", "ATL"), ("Los Angeles Dodgers", "LAD"), ("Houston Astros", "HOU"),
    ("Tampa Bay Rays", "TB"), ("Baltimore Orioles", "BAL"), ("Texas Rangers", "TEX"),
    ("Philadelphia Phillies", "PHI"), ("Minnesota Twins", "MIN"), ("Seattle Mariners", "SEA"),
    ("Toronto Blue Jays", "TOR"), ("Arizona Diamondbacks", "ARI"), ("Milwaukee Brewers", "MIL"),
    ("San Diego Padres", "SD"), ("New York Yankees", "NYY"), ("Boston Red Sox", "BOS"),
    ("Chicago Cubs", "CHC"), ("Cincinnati Reds", "CIN"), ("Miami Marlins", "MIA"),
    ("St. Louis Cardinals", "STL"), ("Cleveland Guardians", "CLE"), ("San Francisco Giants", "SF"),
    ("Detroit Tigers", "DET"), ("New York Mets", "NYM"), ("Los Angeles Angels", "LAA"),
    ("Pittsburgh Pirates", "PIT"), ("Kansas City Royals", "KC"), ("Washington Nationals", "WAS"),
    ("Chicago White Sox", "CWS"), ("Colorado Rockies", "COL"), ("Oakland Athletics", "OAK")
]

NHL_TEAMS = [
    ("Vegas Golden Knights", "VGK"), ("Boston Bruins", "BOS"), ("Carolina Hurricanes", "CAR"),
    ("New Jersey Devils", "NJD"), ("Toronto Maple Leafs", "TOR"), ("Edmonton Oilers", "EDM"),
    ("Colorado Avalanche", "COL"), ("Dallas Stars", "DAL"), ("New York Rangers", "NYR"),
    ("Los Angeles Kings", "LAK"), ("Minnesota Wild", "MIN"), ("Seattle Kraken", "SEA"),
    ("Tampa Bay Lightning", "TBL"), ("Florida Panthers", "FLA"), ("Winnipeg Jets", "WPG"),
    ("Calgary Flames", "CGY"), ("Nashville Predators", "NSH"), ("New York Islanders", "NYI"),
    ("Pittsburgh Penguins", "PIT"), ("Buffalo Sabres", "BUF"), ("Detroit Red Wings", "DET"),
    ("Ottawa Senators", "OTT"), ("Philadelphia Flyers", "PHI"), ("Washington Capitals", "WSH"),
    ("St. Louis Blues", "STL"), ("Vancouver Canucks", "VAN"), ("Montreal Canadiens", "MTL"),
    ("Arizona Coyotes", "ARI"), ("Chicago Blackhawks", "CHI"), ("San Jose Sharks", "SJS"),
    ("Columbus Blue Jackets", "CBJ"), ("Anaheim Ducks", "ANA")
]


def get_sport_teams(sport: str) -> List[tuple]:
    teams_map = {
        "NFL": NFL_TEAMS,
        "NBA": NBA_TEAMS,
        "MLB": MLB_TEAMS,
        "NHL": NHL_TEAMS,
    }
    return teams_map.get(sport, [])


def generate_game_score(sport: str, home_rating: float, away_rating: float) -> tuple:
    rating_diff = (home_rating - away_rating) / 100
    
    if sport == "NFL":
        home_base = 21 + rating_diff * 3 + random.gauss(0, 7)
        away_base = 21 - rating_diff * 3 + random.gauss(0, 7)
        home_score = max(0, round(home_base / 7) * 7 + random.choice([0, 3, -3, 0, 0]))
        away_score = max(0, round(away_base / 7) * 7 + random.choice([0, 3, -3, 0, 0]))
    elif sport == "NBA":
        home_base = 110 + rating_diff * 2 + random.gauss(0, 10)
        away_base = 107 - rating_diff * 2 + random.gauss(0, 10)
        home_score = max(80, int(home_base))
        away_score = max(80, int(away_base))
    elif sport == "MLB":
        home_base = 4.5 + rating_diff * 0.5 + random.gauss(0, 2)
        away_base = 4.2 - rating_diff * 0.5 + random.gauss(0, 2)
        home_score = max(0, int(home_base))
        away_score = max(0, int(away_base))
    elif sport == "NHL":
        home_base = 3.0 + rating_diff * 0.3 + random.gauss(0, 1.5)
        away_base = 2.7 - rating_diff * 0.3 + random.gauss(0, 1.5)
        home_score = max(0, int(home_base))
        away_score = max(0, int(away_base))
    else:
        home_score = random.randint(0, 5)
        away_score = random.randint(0, 5)
    
    return home_score, away_score


def calculate_elo_change(
    winner_rating: float,
    loser_rating: float,
    k_factor: float = 32.0,
    margin: float = 0.0,
    sport: str = "NFL"
) -> float:
    expected = 1 / (1 + 10 ** ((loser_rating - winner_rating) / 400))
    
    if sport == "NFL":
        margin_multiplier = min(2.0, 1.0 + abs(margin) / 14)
    elif sport == "NBA":
        margin_multiplier = min(2.0, 1.0 + abs(margin) / 12)
    elif sport == "MLB":
        margin_multiplier = min(1.5, 1.0 + abs(margin) / 5)
    else:
        margin_multiplier = 1.0
    
    change = k_factor * margin_multiplier * (1 - expected)
    return change


def seed_teams_for_sport(db: Session, sport: str) -> Dict[str, Team]:
    teams = get_sport_teams(sport)
    team_dict = {}
    
    for name, short_name in teams:
        existing = db.query(Team).filter(
            Team.sport == sport,
            Team.name == name
        ).first()
        
        if not existing:
            team = Team(
                sport=sport,
                name=name,
                short_name=short_name,
                rating=1500.0 + random.gauss(0, 100)
            )
            db.add(team)
            db.flush()
            team_dict[name] = team
        else:
            team_dict[name] = existing
    
    db.commit()
    return team_dict


def generate_historical_season(
    db: Session,
    sport: str,
    season: str,
    num_games: int = 256
) -> List[HistoricalGameResult]:
    teams = seed_teams_for_sport(db, sport)
    team_list = list(teams.values())
    
    if len(team_list) < 2:
        return []
    
    if sport == "NFL":
        base_date = datetime(int(season.split("-")[0]), 9, 1)
        games_per_week = 16
    elif sport == "NBA":
        base_date = datetime(int(season.split("-")[0]), 10, 15)
        games_per_week = 50
    elif sport == "MLB":
        base_date = datetime(int(season.split("-")[0]), 4, 1)
        games_per_week = 100
    elif sport == "NHL":
        base_date = datetime(int(season.split("-")[0]), 10, 1)
        games_per_week = 45
    else:
        base_date = datetime(int(season.split("-")[0]), 1, 1)
        games_per_week = 20
    
    results = []
    current_ratings = {t.id: t.rating for t in team_list}
    
    for i in range(num_games):
        home_team = random.choice(team_list)
        away_team = random.choice([t for t in team_list if t.id != home_team.id])
        
        game_date = base_date + timedelta(days=(i // games_per_week) * 7 + random.randint(0, 6))
        
        home_rating = current_ratings[home_team.id]
        away_rating = current_ratings[away_team.id]
        
        home_score, away_score = generate_game_score(sport, home_rating, away_rating)
        
        if home_score > away_score:
            winner = "home"
        elif away_score > home_score:
            winner = "away"
        else:
            winner = "draw"
        
        margin = home_score - away_score
        total_points = home_score + away_score
        
        if winner == "home":
            elo_change = calculate_elo_change(home_rating, away_rating, margin=margin, sport=sport)
            current_ratings[home_team.id] += elo_change
            current_ratings[away_team.id] -= elo_change
        elif winner == "away":
            elo_change = calculate_elo_change(away_rating, home_rating, margin=-margin, sport=sport)
            current_ratings[away_team.id] += elo_change
            current_ratings[home_team.id] -= elo_change
        
        implied_home_prob = 1 / (1 + 10 ** ((away_rating - home_rating - 30) / 400))
        if implied_home_prob > 0.5:
            closing_home_ml = int(-100 * implied_home_prob / (1 - implied_home_prob))
            closing_away_ml = int(100 * (1 - implied_home_prob) / implied_home_prob)
        else:
            closing_home_ml = int(100 * (1 - implied_home_prob) / implied_home_prob)
            closing_away_ml = int(-100 * implied_home_prob / (1 - implied_home_prob))
        
        result = HistoricalGameResult(
            sport=sport,
            season=season,
            game_date=game_date,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=home_score,
            away_score=away_score,
            winner=winner,
            margin=margin,
            total_points=total_points,
            home_team_name=home_team.name,
            away_team_name=away_team.name,
            closing_spread=-margin + random.gauss(0, 2),
            closing_total=total_points + random.gauss(0, 3),
            closing_home_ml=closing_home_ml,
            closing_away_ml=closing_away_ml,
            is_neutral_site=random.random() < 0.05
        )
        
        db.add(result)
        results.append(result)
        
        if winner != "draw":
            winner_id = home_team.id if winner == "home" else away_team.id
            winner_name = home_team.name if winner == "home" else away_team.name
            
            elo_record = ELORatingHistory(
                sport=sport,
                entity_type="team",
                entity_id=winner_id,
                entity_name=winner_name,
                rating=current_ratings[winner_id],
                rating_change=elo_change if winner == "home" else -elo_change,
                recorded_at=game_date,
                season=season
            )
            db.add(elo_record)
    
    for team in team_list:
        team.rating = current_ratings[team.id]
    
    db.commit()
    return results


def seed_historical_data(db: Session = None, seasons: int = 3) -> Dict[str, Any]:
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    
    try:
        stats = {}
        current_year = datetime.now().year
        
        for sport in ["NFL", "NBA", "MLB", "NHL"]:
            sport_stats = {"seasons": [], "total_games": 0}
            
            if sport == "NFL":
                num_games = 272
            elif sport == "NBA":
                num_games = 1230
            elif sport == "MLB":
                num_games = 2430
            elif sport == "NHL":
                num_games = 1312
            else:
                num_games = 500
            
            for i in range(seasons):
                season_year = current_year - seasons + i
                season = f"{season_year}-{season_year + 1}"
                
                existing = db.query(HistoricalGameResult).filter(
                    HistoricalGameResult.sport == sport,
                    HistoricalGameResult.season == season
                ).count()
                
                if existing > 0:
                    sport_stats["seasons"].append({"season": season, "games": existing, "status": "existing"})
                    sport_stats["total_games"] += existing
                    continue
                
                results = generate_historical_season(db, sport, season, num_games)
                sport_stats["seasons"].append({"season": season, "games": len(results), "status": "generated"})
                sport_stats["total_games"] += len(results)
            
            stats[sport] = sport_stats
        
        return stats
        
    finally:
        if close_db:
            db.close()


def get_team_form(
    db: Session,
    team_id: int,
    sport: str,
    num_games: int = 5,
    before_date: datetime = None
) -> Dict[str, Any]:
    if before_date is None:
        before_date = datetime.now()
    
    recent_games = db.query(HistoricalGameResult).filter(
        HistoricalGameResult.sport == sport,
        HistoricalGameResult.game_date < before_date,
        (HistoricalGameResult.home_team_id == team_id) | 
        (HistoricalGameResult.away_team_id == team_id)
    ).order_by(HistoricalGameResult.game_date.desc()).limit(num_games).all()
    
    if not recent_games:
        return {"form": "N/A", "wins": 0, "losses": 0, "avg_margin": 0, "games": 0}
    
    wins = 0
    losses = 0
    draws = 0
    total_margin = 0
    
    for game in recent_games:
        is_home = game.home_team_id == team_id
        
        if game.winner == "home" and is_home:
            wins += 1
            total_margin += game.margin
        elif game.winner == "away" and not is_home:
            wins += 1
            total_margin += abs(game.margin)
        elif game.winner == "draw":
            draws += 1
        else:
            losses += 1
            total_margin -= abs(game.margin) if is_home else game.margin
    
    form_str = ""
    for game in recent_games[:5]:
        is_home = game.home_team_id == team_id
        if game.winner == "home" and is_home:
            form_str += "W"
        elif game.winner == "away" and not is_home:
            form_str += "W"
        elif game.winner == "draw":
            form_str += "D"
        else:
            form_str += "L"
    
    return {
        "form": form_str,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "avg_margin": total_margin / len(recent_games) if recent_games else 0,
        "games": len(recent_games)
    }


def get_head_to_head(
    db: Session,
    team1_id: int,
    team2_id: int,
    sport: str,
    num_games: int = 10
) -> Dict[str, Any]:
    h2h_games = db.query(HistoricalGameResult).filter(
        HistoricalGameResult.sport == sport,
        ((HistoricalGameResult.home_team_id == team1_id) & 
         (HistoricalGameResult.away_team_id == team2_id)) |
        ((HistoricalGameResult.home_team_id == team2_id) & 
         (HistoricalGameResult.away_team_id == team1_id))
    ).order_by(HistoricalGameResult.game_date.desc()).limit(num_games).all()
    
    if not h2h_games:
        return {"team1_wins": 0, "team2_wins": 0, "draws": 0, "games": 0}
    
    team1_wins = 0
    team2_wins = 0
    draws = 0
    
    for game in h2h_games:
        if game.winner == "draw":
            draws += 1
        elif (game.winner == "home" and game.home_team_id == team1_id) or \
             (game.winner == "away" and game.away_team_id == team1_id):
            team1_wins += 1
        else:
            team2_wins += 1
    
    return {
        "team1_wins": team1_wins,
        "team2_wins": team2_wins,
        "draws": draws,
        "games": len(h2h_games)
    }
