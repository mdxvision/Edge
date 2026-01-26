"""
Pinnacle Integration Service

Provides access to sharp lines from Pinnacle sportsbook.
Pinnacle is known as the market-setting book - their lines are considered
the most accurate reflection of true probabilities.

Uses The Odds API to fetch Pinnacle odds (Pinnacle is included as a bookmaker).
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db import Game, Market, Line, OddsSnapshot, Team
from app.utils.logging import get_logger
from app.utils.cache import cached, cache, TTL_MEDIUM, TTL_SHORT
from app.services.odds_api import fetch_odds, is_odds_api_configured

logger = get_logger(__name__)

PINNACLE_SPORTSBOOK = "Pinnacle"

# Pinnacle specific constants
PINNACLE_VIG_THRESHOLD = 2.5  # Pinnacle typically has <2.5% vig
SHARP_LINE_MOVEMENT_THRESHOLD = 10  # cents movement is significant


def american_to_decimal(american: int) -> float:
    """Convert American odds to decimal."""
    if american > 0:
        return 1 + (american / 100)
    else:
        return 1 + (100 / abs(american))


def american_to_implied_prob(american: int) -> float:
    """Convert American odds to implied probability."""
    if american > 0:
        return 100 / (american + 100)
    else:
        return abs(american) / (abs(american) + 100)


def calculate_vig(odds1: int, odds2: int) -> float:
    """Calculate vigorish (overround) from two-way odds."""
    prob1 = american_to_implied_prob(odds1)
    prob2 = american_to_implied_prob(odds2)
    total_prob = prob1 + prob2
    vig = (total_prob - 1) * 100
    return round(vig, 2)


def calculate_no_vig_odds(odds1: int, odds2: int) -> Dict[str, float]:
    """Remove vig and calculate fair odds."""
    prob1 = american_to_implied_prob(odds1)
    prob2 = american_to_implied_prob(odds2)
    total_prob = prob1 + prob2

    # Normalize to remove vig
    fair_prob1 = prob1 / total_prob
    fair_prob2 = prob2 / total_prob

    return {
        "fair_prob1": round(fair_prob1 * 100, 2),
        "fair_prob2": round(fair_prob2 * 100, 2),
    }


@cached("pinnacle", ttl=TTL_SHORT)
async def fetch_pinnacle_odds(sport: str) -> List[Dict[str, Any]]:
    """
    Fetch Pinnacle-specific odds for a sport.

    Filters The Odds API results to only include Pinnacle lines.

    Args:
        sport: Sport code (NFL, NBA, MLB, etc.)

    Returns:
        List of games with Pinnacle odds
    """
    if not is_odds_api_configured():
        logger.warning("Odds API not configured for Pinnacle fetch")
        return []

    logger.debug(f"Fetching Pinnacle odds for {sport}")

    # Fetch from The Odds API (Pinnacle is included as a bookmaker)
    all_odds = await fetch_odds(sport, regions="eu,us", markets="h2h,spreads,totals")

    if not all_odds:
        return []

    pinnacle_games = []

    for game in all_odds:
        pinnacle_data = None

        for bookmaker in game.get("bookmakers", []):
            if bookmaker.get("title", "").lower() == "pinnacle":
                pinnacle_data = bookmaker
                break

        if pinnacle_data:
            pinnacle_games.append({
                "id": game.get("id"),
                "sport": sport,
                "home_team": game.get("home_team"),
                "away_team": game.get("away_team"),
                "commence_time": game.get("commence_time"),
                "pinnacle_markets": pinnacle_data.get("markets", []),
                "last_update": pinnacle_data.get("last_update"),
            })

    logger.info(f"Found {len(pinnacle_games)} games with Pinnacle odds for {sport}")
    return pinnacle_games


async def get_pinnacle_lines(sport: str) -> List[Dict[str, Any]]:
    """
    Get current Pinnacle lines formatted for display.

    Returns:
        List of games with sharp lines
    """
    games = await fetch_pinnacle_odds(sport)

    formatted = []
    for game in games:
        game_data = {
            "home_team": game["home_team"],
            "away_team": game["away_team"],
            "commence_time": game["commence_time"],
            "markets": {}
        }

        for market in game.get("pinnacle_markets", []):
            market_key = market.get("key", "h2h")
            outcomes = market.get("outcomes", [])

            market_data = {"outcomes": []}
            for outcome in outcomes:
                market_data["outcomes"].append({
                    "name": outcome.get("name"),
                    "price": outcome.get("price"),
                    "point": outcome.get("point"),
                })

            # Calculate vig for two-way markets
            if len(outcomes) == 2:
                prices = [o.get("price", 0) for o in outcomes]
                if all(prices):
                    market_data["vig"] = calculate_vig(prices[0], prices[1])
                    market_data["no_vig"] = calculate_no_vig_odds(prices[0], prices[1])

            game_data["markets"][market_key] = market_data

        formatted.append(game_data)

    return formatted


async def compare_to_pinnacle(
    sport: str,
    sportsbook: str,
    db: Session
) -> List[Dict[str, Any]]:
    """
    Compare another sportsbook's lines to Pinnacle.

    Identifies value opportunities where the other book offers
    better odds than Pinnacle (the sharp line).

    Args:
        sport: Sport code
        sportsbook: Sportsbook to compare
        db: Database session

    Returns:
        List of value opportunities
    """
    pinnacle_odds = await fetch_pinnacle_odds(sport)

    if not pinnacle_odds:
        return []

    # Fetch lines from the other sportsbook
    all_odds = await fetch_odds(sport, regions="us", markets="h2h,spreads,totals")

    opportunities = []

    for pinn_game in pinnacle_odds:
        home_team = pinn_game["home_team"]
        away_team = pinn_game["away_team"]

        # Find the same game in other sportsbook data
        other_game = None
        for game in all_odds:
            if game.get("home_team") == home_team and game.get("away_team") == away_team:
                other_game = game
                break

        if not other_game:
            continue

        # Find the target sportsbook
        other_book = None
        for bookmaker in other_game.get("bookmakers", []):
            if bookmaker.get("title", "").lower() == sportsbook.lower():
                other_book = bookmaker
                break

        if not other_book:
            continue

        # Compare markets
        for pinn_market in pinn_game.get("pinnacle_markets", []):
            market_key = pinn_market.get("key")
            pinn_outcomes = {o["name"]: o for o in pinn_market.get("outcomes", [])}

            for other_market in other_book.get("markets", []):
                if other_market.get("key") != market_key:
                    continue

                for outcome in other_market.get("outcomes", []):
                    name = outcome.get("name")
                    other_price = outcome.get("price")
                    pinn_outcome = pinn_outcomes.get(name)

                    if not pinn_outcome or not other_price:
                        continue

                    pinn_price = pinn_outcome.get("price")

                    # Calculate edge vs Pinnacle
                    pinn_prob = american_to_implied_prob(pinn_price)
                    other_prob = american_to_implied_prob(other_price)

                    # If other book's implied prob is lower, that's value
                    if other_prob < pinn_prob:
                        edge = (pinn_prob - other_prob) * 100

                        if edge >= 1.0:  # At least 1% edge
                            opportunities.append({
                                "home_team": home_team,
                                "away_team": away_team,
                                "market": market_key,
                                "selection": name,
                                "pinnacle_odds": pinn_price,
                                "pinnacle_implied": round(pinn_prob * 100, 2),
                                f"{sportsbook}_odds": other_price,
                                f"{sportsbook}_implied": round(other_prob * 100, 2),
                                "edge_vs_pinnacle": round(edge, 2),
                                "point": outcome.get("point"),
                                "commence_time": pinn_game["commence_time"],
                            })

    # Sort by edge
    opportunities.sort(key=lambda x: x["edge_vs_pinnacle"], reverse=True)

    return opportunities


def get_pinnacle_closing_line(
    db: Session,
    game_id: int,
    market_type: str,
) -> Optional[Dict[str, Any]]:
    """
    Get the Pinnacle closing line for a game.

    The closing line from Pinnacle is the gold standard for CLV calculation.
    """
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        return None

    # Get last Pinnacle snapshot before game start
    snapshot = db.query(OddsSnapshot).filter(
        OddsSnapshot.game_id == game_id,
        OddsSnapshot.market_type == market_type,
        OddsSnapshot.sportsbook == PINNACLE_SPORTSBOOK,
        OddsSnapshot.captured_at < game.start_time
    ).order_by(OddsSnapshot.captured_at.desc()).first()

    if snapshot:
        return {
            "odds": snapshot.odds,
            "line_value": snapshot.line_value,
            "captured_at": snapshot.captured_at.isoformat(),
        }

    # Fallback: check current lines
    market = db.query(Market).filter(
        Market.game_id == game_id,
        Market.market_type == market_type
    ).first()

    if market:
        for line in market.lines:
            if line.sportsbook == PINNACLE_SPORTSBOOK:
                return {
                    "odds": line.american_odds,
                    "line_value": line.line_value,
                    "captured_at": line.created_at.isoformat() if line.created_at else None,
                }

    return None


def calculate_clv_vs_pinnacle(
    bet_odds: int,
    pinnacle_closing_odds: int
) -> Dict[str, Any]:
    """
    Calculate CLV specifically against Pinnacle closing line.

    This is the most meaningful CLV metric as Pinnacle represents
    the sharpest market.
    """
    bet_prob = american_to_implied_prob(bet_odds)
    pinn_prob = american_to_implied_prob(pinnacle_closing_odds)

    # Positive CLV = you got better odds than Pinnacle closed at
    clv_percentage = ((pinn_prob - bet_prob) / bet_prob) * 100

    return {
        "bet_odds": bet_odds,
        "pinnacle_closing": pinnacle_closing_odds,
        "bet_implied_prob": round(bet_prob * 100, 2),
        "pinnacle_implied_prob": round(pinn_prob * 100, 2),
        "clv_percentage": round(clv_percentage, 2),
        "is_positive_clv": clv_percentage > 0,
    }


def get_market_efficiency(
    db: Session,
    game_id: int,
    market_type: str = "h2h"
) -> Dict[str, Any]:
    """
    Analyze market efficiency by comparing all sportsbooks to Pinnacle.

    Returns:
        Market efficiency analysis
    """
    market = db.query(Market).filter(
        Market.game_id == game_id,
        Market.market_type == market_type
    ).first()

    if not market or not market.lines:
        return {"error": "No market data found"}

    # Find Pinnacle line
    pinnacle_line = None
    other_lines = []

    for line in market.lines:
        if line.sportsbook == PINNACLE_SPORTSBOOK:
            pinnacle_line = line
        else:
            other_lines.append(line)

    if not pinnacle_line:
        return {"error": "No Pinnacle line found"}

    pinn_odds = pinnacle_line.american_odds
    pinn_prob = american_to_implied_prob(pinn_odds)

    comparisons = []
    total_deviation = 0

    for line in other_lines:
        line_prob = american_to_implied_prob(line.american_odds)
        deviation = abs(line_prob - pinn_prob) * 100
        total_deviation += deviation

        comparisons.append({
            "sportsbook": line.sportsbook,
            "odds": line.american_odds,
            "implied_prob": round(line_prob * 100, 2),
            "deviation_from_pinnacle": round(deviation, 2),
            "has_value": line_prob < pinn_prob,  # Lower prob = better odds
        })

    avg_deviation = total_deviation / len(other_lines) if other_lines else 0

    # Determine efficiency rating
    if avg_deviation < 1:
        efficiency_rating = "Very High"
    elif avg_deviation < 2:
        efficiency_rating = "High"
    elif avg_deviation < 3:
        efficiency_rating = "Moderate"
    else:
        efficiency_rating = "Low"

    return {
        "pinnacle_baseline": {
            "odds": pinn_odds,
            "implied_prob": round(pinn_prob * 100, 2),
        },
        "sportsbook_comparisons": comparisons,
        "average_deviation": round(avg_deviation, 2),
        "efficiency_rating": efficiency_rating,
        "value_opportunities": len([c for c in comparisons if c["has_value"]]),
    }


async def store_pinnacle_odds(db: Session, sport: str) -> Dict[str, Any]:
    """
    Fetch and store Pinnacle odds in the database.

    Creates snapshots for CLV tracking.
    """
    pinnacle_games = await fetch_pinnacle_odds(sport)

    if not pinnacle_games:
        return {"stored": 0, "message": "No Pinnacle odds found"}

    stored = 0
    now = datetime.utcnow()

    for game_data in pinnacle_games:
        home_team_name = game_data["home_team"]
        away_team_name = game_data["away_team"]

        # Find or create teams
        home_team = db.query(Team).filter(
            Team.sport == sport,
            Team.name.ilike(f"%{home_team_name}%")
        ).first()

        if not home_team:
            home_team = Team(sport=sport, name=home_team_name, short_name=home_team_name[:10])
            db.add(home_team)
            db.flush()

        away_team = db.query(Team).filter(
            Team.sport == sport,
            Team.name.ilike(f"%{away_team_name}%")
        ).first()

        if not away_team:
            away_team = Team(sport=sport, name=away_team_name, short_name=away_team_name[:10])
            db.add(away_team)
            db.flush()

        # Parse commence time
        commence_str = game_data.get("commence_time", "")
        if commence_str:
            start_time = datetime.fromisoformat(commence_str.replace("Z", "+00:00"))
        else:
            start_time = now

        # Find or create game
        game = db.query(Game).filter(
            Game.sport == sport,
            Game.home_team_id == home_team.id,
            Game.away_team_id == away_team.id,
            Game.start_time == start_time
        ).first()

        if not game:
            game = Game(
                sport=sport,
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                start_time=start_time
            )
            db.add(game)
            db.flush()

        # Store Pinnacle odds snapshots
        for market in game_data.get("pinnacle_markets", []):
            market_type = market.get("key", "h2h")

            for outcome in market.get("outcomes", []):
                price = outcome.get("price")
                point = outcome.get("point")

                if price:
                    snapshot = OddsSnapshot(
                        game_id=game.id,
                        market_type=market_type,
                        sportsbook=PINNACLE_SPORTSBOOK,
                        odds=price,
                        line_value=point,
                        captured_at=now
                    )
                    db.add(snapshot)
                    stored += 1

    db.commit()

    logger.info(f"Stored {stored} Pinnacle odds snapshots for {sport}")
    return {
        "stored": stored,
        "games": len(pinnacle_games),
        "sport": sport,
        "timestamp": now.isoformat()
    }


def get_pinnacle_line_history(
    db: Session,
    game_id: int,
    market_type: str = "h2h"
) -> List[Dict[str, Any]]:
    """
    Get historical Pinnacle line movements for a game.
    """
    snapshots = db.query(OddsSnapshot).filter(
        OddsSnapshot.game_id == game_id,
        OddsSnapshot.market_type == market_type,
        OddsSnapshot.sportsbook == PINNACLE_SPORTSBOOK
    ).order_by(OddsSnapshot.captured_at).all()

    history = []
    prev_odds = None

    for snapshot in snapshots:
        movement = None
        if prev_odds is not None:
            movement = snapshot.odds - prev_odds

        history.append({
            "odds": snapshot.odds,
            "line_value": snapshot.line_value,
            "captured_at": snapshot.captured_at.isoformat(),
            "movement": movement,
        })

        prev_odds = snapshot.odds

    return history


def detect_sharp_line_movement(
    db: Session,
    sport: str,
    threshold_cents: int = SHARP_LINE_MOVEMENT_THRESHOLD
) -> List[Dict[str, Any]]:
    """
    Detect significant Pinnacle line movements.

    Sharp money causes Pinnacle to move their lines.
    Large movements indicate professional betting action.
    """
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=24)

    # Get recent games
    games = db.query(Game).filter(
        Game.sport == sport,
        Game.start_time > now,  # Future games only
        Game.status == "scheduled"
    ).all()

    significant_moves = []

    for game in games:
        # Get Pinnacle snapshots
        snapshots = db.query(OddsSnapshot).filter(
            OddsSnapshot.game_id == game.id,
            OddsSnapshot.sportsbook == PINNACLE_SPORTSBOOK,
            OddsSnapshot.captured_at >= cutoff
        ).order_by(OddsSnapshot.captured_at).all()

        if len(snapshots) < 2:
            continue

        first = snapshots[0]
        last = snapshots[-1]

        movement = last.odds - first.odds

        if abs(movement) >= threshold_cents:
            significant_moves.append({
                "game_id": game.id,
                "home_team": game.home_team.name if game.home_team else "Unknown",
                "away_team": game.away_team.name if game.away_team else "Unknown",
                "start_time": game.start_time.isoformat(),
                "market_type": last.market_type,
                "opening_odds": first.odds,
                "current_odds": last.odds,
                "movement": movement,
                "direction": "favorite" if movement < 0 else "underdog",
                "first_captured": first.captured_at.isoformat(),
                "last_captured": last.captured_at.isoformat(),
                "snapshots_count": len(snapshots),
            })

    # Sort by absolute movement
    significant_moves.sort(key=lambda x: abs(x["movement"]), reverse=True)

    return significant_moves
