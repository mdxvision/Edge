from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db import Game, Market, Line, Team, Competitor, SessionLocal
from app.models import SPORT_MODEL_REGISTRY
from app.utils.odds import american_to_implied_probability, expected_value, edge as calc_edge
from app.schemas.bets import BetCandidate
from app.config import TEAM_SPORTS, INDIVIDUAL_SPORTS, SUPPORTED_SPORTS
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Maximum realistic edge for sports betting (anything higher is likely a bug)
MAX_REALISTIC_EDGE = 0.15  # 15% max edge
MIN_REALISTIC_CONFIDENCE = 0.45  # 45% minimum
MAX_REALISTIC_CONFIDENCE = 0.85  # 85% maximum


def get_upcoming_games(db: Session, sport: str, days_ahead: int = 2) -> List[Game]:
    """
    Get games for the next 48 hours only.
    Only returns games that are actually scheduled for today or tomorrow.
    """
    now = datetime.utcnow()
    end = now + timedelta(days=days_ahead)

    return db.query(Game).filter(
        Game.sport == sport,
        Game.start_time >= now,
        Game.start_time <= end
    ).all()


def build_game_data(game: Game, db: Session) -> dict:
    data = {
        "game_id": game.id,
        "sport": game.sport,
        "league": game.league
    }
    
    if game.sport in TEAM_SPORTS:
        if game.home_team:
            data["home_rating"] = game.home_team.rating or 1500.0
            data["home_team_name"] = game.home_team.name
        else:
            data["home_rating"] = 1500.0
            data["home_team_name"] = "Unknown"
            
        if game.away_team:
            data["away_rating"] = game.away_team.rating or 1500.0
            data["away_team_name"] = game.away_team.name
        else:
            data["away_rating"] = 1500.0
            data["away_team_name"] = "Unknown"
    
    if game.sport in INDIVIDUAL_SPORTS:
        if game.competitor1:
            data["competitor1_rating"] = game.competitor1.rating or 1500.0
            data["competitor1_name"] = game.competitor1.name
        else:
            data["competitor1_rating"] = 1500.0
            data["competitor1_name"] = "Unknown"
            
        if game.competitor2:
            data["competitor2_rating"] = game.competitor2.rating or 1500.0
            data["competitor2_name"] = game.competitor2.name
        else:
            data["competitor2_rating"] = 1500.0
            data["competitor2_name"] = "Unknown"
    
    return data


def map_selection_to_probability(
    selection: str, 
    predictions: dict,
    sport: str
) -> Optional[float]:
    if selection == "home":
        return predictions.get("home_win")
    elif selection == "away":
        return predictions.get("away_win")
    elif selection == "draw":
        return predictions.get("draw")
    elif selection == "competitor1":
        return predictions.get("competitor1_win")
    elif selection == "competitor2":
        return predictions.get("competitor2_win")
    elif selection == "over":
        return 0.50
    elif selection == "under":
        return 0.50
    
    return None


def find_value_bets_for_sport(
    sport: str,
    min_edge: float = 0.02,  # Lowered to 2% to find more realistic edges
    db: Session = None
) -> List[BetCandidate]:
    """
    Find value bets for a sport using real games from the database.

    Edge calculation:
    - Get odds from sportsbook (e.g., -110 = 52.4% implied)
    - Use power ratings to estimate actual win probability
    - Edge = (actual probability - implied probability)
    - Only return picks with 2%+ edge and realistic confidence
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        if sport not in SPORT_MODEL_REGISTRY:
            logger.warning(f"No model registered for sport: {sport}")
            return []

        model = SPORT_MODEL_REGISTRY[sport]
        logger.debug(f"Finding value bets for {sport} (min_edge={min_edge})")

        games = get_upcoming_games(db, sport)

        if not games:
            logger.info(f"No upcoming games found for {sport}")
            return []

        logger.debug(f"Found {len(games)} upcoming games for {sport}")
        game_data_list = [build_game_data(g, db) for g in games]
        predictions_list = model.predict_game_probabilities(game_data_list)
        logger.debug(f"Generated predictions for {len(predictions_list)} games")

        predictions_by_game = {p["game_id"]: p for p in predictions_list}

        value_bets = []
        seen_games = set()  # Track unique games to avoid duplicates

        for game, game_data in zip(games, game_data_list):
            predictions = predictions_by_game.get(game.id, {})

            # Skip if no markets/lines (no real odds data)
            if not game.markets:
                continue

            for market in game.markets:
                for line in market.lines:
                    # Skip if no valid odds
                    if not line.american_odds or abs(line.american_odds) < 100:
                        continue

                    model_prob = map_selection_to_probability(
                        market.selection,
                        predictions,
                        sport
                    )

                    if model_prob is None:
                        continue

                    # Ensure model probability is realistic (not too close to 0 or 1)
                    model_prob = max(MIN_REALISTIC_CONFIDENCE, min(MAX_REALISTIC_CONFIDENCE, model_prob))

                    implied_prob = american_to_implied_probability(line.american_odds)
                    edge_value = calc_edge(model_prob, implied_prob)

                    # Cap edge at realistic maximum
                    if edge_value > MAX_REALISTIC_EDGE:
                        edge_value = MAX_REALISTIC_EDGE

                    # Only include positive edges meeting minimum threshold
                    if edge_value >= min_edge and edge_value <= MAX_REALISTIC_EDGE:
                        # Avoid duplicate picks for the same game
                        game_key = f"{game.id}_{market.market_type}_{market.selection}"
                        if game_key in seen_games:
                            continue
                        seen_games.add(game_key)

                        ev = expected_value(model_prob, line.american_odds, 1.0)

                        candidate = BetCandidate(
                            game_id=game.id,
                            sport=sport,
                            market_id=market.id,
                            line_id=line.id,
                            selection=market.selection,
                            sportsbook=line.sportsbook,
                            american_odds=line.american_odds,
                            line_value=line.line_value,
                            model_probability=round(model_prob, 4),
                            implied_probability=round(implied_prob, 4),
                            edge=round(edge_value, 4),
                            expected_value=round(ev, 4),
                            home_team_name=game_data.get("home_team_name"),
                            away_team_name=game_data.get("away_team_name"),
                            competitor1_name=game_data.get("competitor1_name"),
                            competitor2_name=game_data.get("competitor2_name"),
                            start_time=game.start_time,
                            league=game.league,
                            market_type=market.market_type,
                            description=market.description
                        )

                        value_bets.append(candidate)

        # Sort by edge and limit to top picks
        value_bets.sort(key=lambda x: x.edge, reverse=True)
        top_bets = value_bets[:20]  # Limit to top 20 picks

        if top_bets:
            logger.info(f"Found {len(top_bets)} value bets for {sport}, top edge: {top_bets[0].edge:.2%}")
        else:
            logger.debug(f"No value bets found for {sport} with min_edge={min_edge}")

        return top_bets

    finally:
        if close_db:
            db.close()


def find_value_bets_for_sports(
    sports: Optional[List[str]] = None,
    min_edge: float = 0.03,
    db: Session = None
) -> List[BetCandidate]:
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        if sports is None:
            sports = SUPPORTED_SPORTS

        logger.info(f"Scanning {len(sports)} sports for value bets (min_edge={min_edge})")
        all_candidates = []

        for sport in sports:
            candidates = find_value_bets_for_sport(sport, min_edge, db)
            all_candidates.extend(candidates)

        all_candidates.sort(key=lambda x: x.edge, reverse=True)
        logger.info(f"Total value bets found across all sports: {len(all_candidates)}")
        return all_candidates

    finally:
        if close_db:
            db.close()
