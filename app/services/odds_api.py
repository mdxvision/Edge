import os
import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.db import Game, Market, Line, Team, OddsSnapshot


THE_ODDS_API_KEY = os.environ.get("THE_ODDS_API_KEY")
THE_ODDS_API_BASE = "https://api.the-odds-api.com/v4"

SPORT_MAPPING = {
    "NFL": "americanfootball_nfl",
    "NBA": "basketball_nba",
    "MLB": "baseball_mlb",
    "NHL": "icehockey_nhl",
    "NCAA_FOOTBALL": "americanfootball_ncaaf",
    "NCAA_BASKETBALL": "basketball_ncaab",
    "SOCCER": "soccer_epl",
    "TENNIS": "tennis_atp_australian_open",
    "MMA": "mma_mixed_martial_arts",
    "BOXING": "boxing_boxing",
}


def is_odds_api_configured() -> bool:
    return bool(THE_ODDS_API_KEY)


async def get_available_sports() -> List[Dict[str, Any]]:
    if not THE_ODDS_API_KEY:
        return []
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{THE_ODDS_API_BASE}/sports",
                params={"apiKey": THE_ODDS_API_KEY}
            )
        
        if response.status_code == 200:
            return response.json()
        return []
    except Exception:
        return []


async def fetch_odds(
    sport: str,
    regions: str = "us",
    markets: str = "h2h,spreads,totals"
) -> List[Dict[str, Any]]:
    if not THE_ODDS_API_KEY:
        return []
    
    api_sport = SPORT_MAPPING.get(sport)
    if not api_sport:
        return []
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{THE_ODDS_API_BASE}/sports/{api_sport}/odds",
                params={
                    "apiKey": THE_ODDS_API_KEY,
                    "regions": regions,
                    "markets": markets,
                    "oddsFormat": "american"
                }
            )
        
        if response.status_code == 200:
            return response.json()
        return []
    except Exception:
        return []


async def fetch_and_store_odds(db: Session, sport: str) -> int:
    games_data = await fetch_odds(sport)
    
    if not games_data:
        return 0
    
    count = 0
    
    for game_data in games_data:
        home_team_name = game_data.get("home_team", "")
        away_team_name = game_data.get("away_team", "")
        commence_time = game_data.get("commence_time", "")
        
        if commence_time:
            start_time = datetime.fromisoformat(commence_time.replace("Z", "+00:00"))
        else:
            start_time = datetime.utcnow()
        
        home_team = db.query(Team).filter(
            Team.sport == sport,
            Team.name.ilike(f"%{home_team_name}%")
        ).first()
        
        away_team = db.query(Team).filter(
            Team.sport == sport,
            Team.name.ilike(f"%{away_team_name}%")
        ).first()
        
        if not home_team:
            home_team = Team(sport=sport, name=home_team_name, short_name=home_team_name[:10])
            db.add(home_team)
            db.flush()
        
        if not away_team:
            away_team = Team(sport=sport, name=away_team_name, short_name=away_team_name[:10])
            db.add(away_team)
            db.flush()
        
        existing_game = db.query(Game).filter(
            Game.sport == sport,
            Game.home_team_id == home_team.id,
            Game.away_team_id == away_team.id,
            Game.start_time == start_time
        ).first()
        
        if existing_game:
            game = existing_game
        else:
            game = Game(
                sport=sport,
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                start_time=start_time
            )
            db.add(game)
            db.flush()
            count += 1
        
        for bookmaker in game_data.get("bookmakers", []):
            sportsbook = bookmaker.get("title", "Unknown")
            
            for market in bookmaker.get("markets", []):
                market_type = market.get("key", "h2h")
                
                for outcome in market.get("outcomes", []):
                    selection = outcome.get("name", "")
                    price = outcome.get("price", 0)
                    point = outcome.get("point")
                    
                    existing_market = db.query(Market).filter(
                        Market.game_id == game.id,
                        Market.market_type == market_type,
                        Market.selection == selection
                    ).first()
                    
                    if existing_market:
                        market_obj = existing_market
                    else:
                        market_obj = Market(
                            game_id=game.id,
                            market_type=market_type,
                            selection=selection
                        )
                        db.add(market_obj)
                        db.flush()
                    
                    existing_line = db.query(Line).filter(
                        Line.market_id == market_obj.id,
                        Line.sportsbook == sportsbook
                    ).first()
                    
                    if existing_line:
                        existing_line.american_odds = price
                        existing_line.line_value = point
                        existing_line.created_at = datetime.utcnow()
                    else:
                        line = Line(
                            market_id=market_obj.id,
                            sportsbook=sportsbook,
                            odds_type="american",
                            american_odds=price,
                            line_value=point
                        )
                        db.add(line)
                    
                    snapshot = OddsSnapshot(
                        game_id=game.id,
                        market_type=market_type,
                        sportsbook=sportsbook,
                        odds=price,
                        line_value=point
                    )
                    db.add(snapshot)
    
    db.commit()
    return count


def get_line_movement(
    db: Session,
    game_id: int,
    market_type: str = "h2h",
    sportsbook: Optional[str] = None
) -> List[Dict[str, Any]]:
    query = db.query(OddsSnapshot).filter(
        OddsSnapshot.game_id == game_id,
        OddsSnapshot.market_type == market_type
    )
    
    if sportsbook:
        query = query.filter(OddsSnapshot.sportsbook == sportsbook)
    
    snapshots = query.order_by(OddsSnapshot.captured_at).all()
    
    movement = []
    for snapshot in snapshots:
        movement.append({
            "sportsbook": snapshot.sportsbook,
            "odds": snapshot.odds,
            "line_value": snapshot.line_value,
            "captured_at": snapshot.captured_at.isoformat()
        })
    
    return movement


def detect_significant_movement(
    db: Session,
    game_id: int,
    threshold: int = 20
) -> List[Dict[str, Any]]:
    snapshots = db.query(OddsSnapshot).filter(
        OddsSnapshot.game_id == game_id
    ).order_by(OddsSnapshot.captured_at).all()
    
    movements_by_key = {}
    
    for snapshot in snapshots:
        key = f"{snapshot.sportsbook}_{snapshot.market_type}"
        if key not in movements_by_key:
            movements_by_key[key] = []
        movements_by_key[key].append(snapshot)
    
    significant = []
    
    for key, snaps in movements_by_key.items():
        if len(snaps) < 2:
            continue
        
        first = snaps[0]
        last = snaps[-1]
        
        diff = abs(last.odds - first.odds)
        if diff >= threshold:
            significant.append({
                "sportsbook": last.sportsbook,
                "market_type": last.market_type,
                "opening_odds": first.odds,
                "current_odds": last.odds,
                "movement": last.odds - first.odds,
                "first_captured": first.captured_at.isoformat(),
                "last_captured": last.captured_at.isoformat()
            })
    
    return significant
