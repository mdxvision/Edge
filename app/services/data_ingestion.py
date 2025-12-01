import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db import Team, Competitor, Player, Game, Market, Line, SessionLocal
from app.config import TEAM_SPORTS, INDIVIDUAL_SPORTS
import os


def get_data_path(filename: str) -> str:
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base_path, "data", filename)


def clear_sample_data(db: Session) -> None:
    db.query(Line).delete()
    db.query(Market).delete()
    db.query(Game).delete()
    db.query(Player).delete()
    db.query(Competitor).delete()
    db.query(Team).delete()
    db.commit()


def seed_teams_and_competitors(db: Session, games_df: pd.DataFrame) -> dict:
    teams = {}
    competitors = {}
    
    for _, row in games_df.iterrows():
        sport = row["sport"]
        
        if sport in TEAM_SPORTS:
            home_team = row.get("home_team")
            away_team = row.get("away_team")
            
            if pd.notna(home_team) and home_team not in teams:
                team = Team(
                    sport=sport,
                    name=home_team,
                    short_name=home_team[:3].upper() if home_team else None,
                    rating=float(row.get("home_rating", 1500))
                )
                db.add(team)
                db.flush()
                teams[home_team] = team.id
            
            if pd.notna(away_team) and away_team not in teams:
                team = Team(
                    sport=sport,
                    name=away_team,
                    short_name=away_team[:3].upper() if away_team else None,
                    rating=float(row.get("away_rating", 1500))
                )
                db.add(team)
                db.flush()
                teams[away_team] = team.id
        
        if sport in INDIVIDUAL_SPORTS:
            comp1 = row.get("competitor1")
            comp2 = row.get("competitor2")
            
            if pd.notna(comp1) and comp1 not in competitors:
                competitor = Competitor(
                    sport=sport,
                    name=comp1,
                    rating=float(row.get("competitor1_rating", 1500))
                )
                db.add(competitor)
                db.flush()
                competitors[comp1] = competitor.id
            
            if pd.notna(comp2) and comp2 not in competitors:
                competitor = Competitor(
                    sport=sport,
                    name=comp2,
                    rating=float(row.get("competitor2_rating", 1500))
                )
                db.add(competitor)
                db.flush()
                competitors[comp2] = competitor.id
    
    db.commit()
    return {"teams": teams, "competitors": competitors}


def seed_games(db: Session, games_df: pd.DataFrame, entity_map: dict) -> dict:
    games = {}
    
    for idx, row in games_df.iterrows():
        sport = row["sport"]
        
        start_time_str = row.get("start_time", "")
        try:
            start_time = datetime.strptime(str(start_time_str), "%Y-%m-%d %H:%M:%S")
        except:
            start_time = datetime.now() + timedelta(days=1)
        
        game = Game(
            sport=sport,
            start_time=start_time,
            venue=row.get("venue"),
            league=row.get("league")
        )
        
        if sport in TEAM_SPORTS:
            home_team = row.get("home_team")
            away_team = row.get("away_team")
            if pd.notna(home_team):
                game.home_team_id = entity_map["teams"].get(home_team)
            if pd.notna(away_team):
                game.away_team_id = entity_map["teams"].get(away_team)
        
        if sport in INDIVIDUAL_SPORTS:
            comp1 = row.get("competitor1")
            comp2 = row.get("competitor2")
            if pd.notna(comp1):
                game.competitor1_id = entity_map["competitors"].get(comp1)
            if pd.notna(comp2):
                game.competitor2_id = entity_map["competitors"].get(comp2)
        
        db.add(game)
        db.flush()
        games[idx] = game.id
    
    db.commit()
    return games


def seed_markets_and_lines(db: Session, lines_df: pd.DataFrame, game_map: dict) -> None:
    market_cache = {}
    
    for _, row in lines_df.iterrows():
        game_index = int(row["game_index"])
        game_id = game_map.get(game_index)
        
        if game_id is None:
            continue
        
        market_type = row["market_type"]
        selection = row["selection"]
        
        market_key = (game_id, market_type, selection)
        
        if market_key not in market_cache:
            description = f"{market_type.title()} - {selection}"
            market = Market(
                game_id=game_id,
                market_type=market_type,
                description=description,
                selection=selection
            )
            db.add(market)
            db.flush()
            market_cache[market_key] = market.id
        
        market_id = market_cache[market_key]
        
        line_value = row.get("line_value")
        if pd.isna(line_value):
            line_value = None
        else:
            line_value = float(line_value)
        
        line = Line(
            market_id=market_id,
            sportsbook=row["sportsbook"],
            odds_type=market_type,
            line_value=line_value,
            american_odds=int(row["american_odds"]),
            created_at=datetime.utcnow()
        )
        db.add(line)
    
    db.commit()


def seed_sample_data() -> None:
    db = SessionLocal()
    try:
        existing_games = db.query(Game).first()
        if existing_games:
            return
        
        games_path = get_data_path("sample_games.csv")
        lines_path = get_data_path("sample_lines.csv")
        
        if not os.path.exists(games_path) or not os.path.exists(lines_path):
            print("Sample data files not found. Skipping seed.")
            return
        
        games_df = pd.read_csv(games_path)
        lines_df = pd.read_csv(lines_path)
        
        games_df = games_df.dropna(subset=["sport"])
        games_df = games_df[games_df["sport"].str.strip() != ""]
        
        entity_map = seed_teams_and_competitors(db, games_df)
        game_map = seed_games(db, games_df, entity_map)
        seed_markets_and_lines(db, lines_df, game_map)
        
        print("Sample data seeded successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding data: {e}")
        raise
    finally:
        db.close()


def reseed_sample_data() -> None:
    db = SessionLocal()
    try:
        clear_sample_data(db)
        db.close()
        seed_sample_data()
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()
