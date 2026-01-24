"""
Arbitrage detection service.

Detects arbitrage opportunities across sportsbooks by comparing odds
for the same market and calculating optimal stake distribution.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy.orm import Session

from app.db import Game, Market, Line
from app.utils.logging import get_logger
from app.utils.cache import cache, TTL_SHORT

logger = get_logger(__name__)


@dataclass
class ArbOpportunity:
    """Represents an arbitrage opportunity."""
    game_id: int
    sport: str
    home_team: str
    away_team: str
    market_type: str
    start_time: datetime
    profit_margin: float  # As percentage (e.g., 2.5 for 2.5%)

    # Bet 1 details
    bet1_selection: str
    bet1_sportsbook: str
    bet1_odds: int  # American odds
    bet1_stake_pct: float  # Percentage of total stake

    # Bet 2 details
    bet2_selection: str
    bet2_sportsbook: str
    bet2_odds: int
    bet2_stake_pct: float

    # Optional for 3-way markets
    bet3_selection: Optional[str] = None
    bet3_sportsbook: Optional[str] = None
    bet3_odds: Optional[int] = None
    bet3_stake_pct: Optional[float] = None


def american_to_decimal(american: int) -> float:
    """Convert American odds to decimal odds."""
    if american > 0:
        return (american / 100) + 1
    else:
        return (100 / abs(american)) + 1


def american_to_implied_prob(american: int) -> float:
    """Convert American odds to implied probability."""
    if american > 0:
        return 100 / (american + 100)
    else:
        return abs(american) / (abs(american) + 100)


def calculate_arb_margin(odds_list: List[int]) -> float:
    """
    Calculate arbitrage margin from a list of American odds.

    Returns negative value if arbitrage exists (profit margin).
    Returns positive value if no arbitrage (bookmaker margin).
    """
    total_implied = sum(american_to_implied_prob(odds) for odds in odds_list)
    return (total_implied - 1) * 100  # As percentage


def calculate_stakes(odds_list: List[int], total_stake: float = 100) -> List[float]:
    """
    Calculate optimal stake distribution for arbitrage.

    Returns list of stakes that guarantee equal payout regardless of outcome.
    """
    decimal_odds = [american_to_decimal(o) for o in odds_list]

    # Calculate implied probabilities
    implied_probs = [1 / d for d in decimal_odds]
    total_implied = sum(implied_probs)

    # Stake for each outcome = (implied_prob / total_implied) * total_stake
    stakes = [(ip / total_implied) * total_stake for ip in implied_probs]

    return stakes


def calculate_guaranteed_profit(odds_list: List[int], stakes: List[float]) -> float:
    """Calculate guaranteed profit from arbitrage bet."""
    decimal_odds = [american_to_decimal(o) for o in odds_list]

    # Payout is the same regardless of which outcome wins
    payout = stakes[0] * decimal_odds[0]
    total_stake = sum(stakes)

    return payout - total_stake


def find_best_odds_per_selection(
    lines: List[Line]
) -> Dict[str, Tuple[int, str]]:
    """
    Find best odds for each selection across all sportsbooks.

    Returns dict: {selection: (best_odds, sportsbook)}
    """
    best_odds: Dict[str, Tuple[int, str]] = {}

    for line in lines:
        selection = line.market.selection
        odds = line.american_odds

        if selection not in best_odds:
            best_odds[selection] = (odds, line.sportsbook)
        else:
            current_best, _ = best_odds[selection]
            # Higher American odds are better for positive, lower absolute for negative
            if odds > current_best:
                best_odds[selection] = (odds, line.sportsbook)

    return best_odds


def detect_h2h_arbitrage(
    db: Session,
    game: Game,
    min_profit: float = 0.0
) -> Optional[ArbOpportunity]:
    """
    Detect arbitrage opportunity for head-to-head (moneyline) market.
    """
    # Get all h2h markets for this game
    markets = db.query(Market).filter(
        Market.game_id == game.id,
        Market.market_type == "h2h"
    ).all()

    if not markets:
        return None

    # Collect all lines grouped by selection
    lines_by_selection: Dict[str, List[Line]] = {}

    for market in markets:
        for line in market.lines:
            selection = market.selection
            if selection not in lines_by_selection:
                lines_by_selection[selection] = []
            lines_by_selection[selection].append(line)

    # Need exactly 2 selections for h2h
    selections = list(lines_by_selection.keys())
    if len(selections) != 2:
        return None

    # Find best odds for each selection
    best_odds = {}
    for selection, lines in lines_by_selection.items():
        best_line = max(lines, key=lambda l: l.american_odds)
        best_odds[selection] = (best_line.american_odds, best_line.sportsbook)

    # Calculate arbitrage margin
    odds_list = [best_odds[s][0] for s in selections]
    margin = calculate_arb_margin(odds_list)

    # Negative margin means arbitrage exists
    if margin >= -min_profit:
        return None

    profit_margin = abs(margin)
    stakes = calculate_stakes(odds_list)

    home_name = game.home_team.name if game.home_team else "Home"
    away_name = game.away_team.name if game.away_team else "Away"

    return ArbOpportunity(
        game_id=game.id,
        sport=game.sport,
        home_team=home_name,
        away_team=away_name,
        market_type="h2h",
        start_time=game.start_time,
        profit_margin=round(profit_margin, 2),
        bet1_selection=selections[0],
        bet1_sportsbook=best_odds[selections[0]][1],
        bet1_odds=best_odds[selections[0]][0],
        bet1_stake_pct=round(stakes[0], 2),
        bet2_selection=selections[1],
        bet2_sportsbook=best_odds[selections[1]][1],
        bet2_odds=best_odds[selections[1]][0],
        bet2_stake_pct=round(stakes[1], 2),
    )


def detect_spread_arbitrage(
    db: Session,
    game: Game,
    min_profit: float = 0.0
) -> Optional[ArbOpportunity]:
    """
    Detect arbitrage opportunity for spread markets.

    Looks for opposing spreads at different books (e.g., Team A -3 vs Team B +3).
    """
    markets = db.query(Market).filter(
        Market.game_id == game.id,
        Market.market_type == "spreads"
    ).all()

    if not markets:
        return None

    # Group lines by spread value and selection
    # For arb, we need matching spreads (e.g., -3 and +3)
    spread_lines: Dict[float, Dict[str, List[Line]]] = {}

    for market in markets:
        for line in market.lines:
            spread = line.line_value
            if spread is None:
                continue

            if spread not in spread_lines:
                spread_lines[spread] = {}

            selection = market.selection
            if selection not in spread_lines[spread]:
                spread_lines[spread][selection] = []
            spread_lines[spread][selection].append(line)

    # Look for matching opposite spreads
    for spread, selections in spread_lines.items():
        opposite_spread = -spread
        if opposite_spread not in spread_lines:
            continue

        # Get best odds for each side
        for sel1, lines1 in selections.items():
            best1 = max(lines1, key=lambda l: l.american_odds)

            for sel2, lines2 in spread_lines[opposite_spread].items():
                if sel1 == sel2:
                    continue

                best2 = max(lines2, key=lambda l: l.american_odds)

                odds_list = [best1.american_odds, best2.american_odds]
                margin = calculate_arb_margin(odds_list)

                if margin < -min_profit:
                    profit_margin = abs(margin)
                    stakes = calculate_stakes(odds_list)

                    home_name = game.home_team.name if game.home_team else "Home"
                    away_name = game.away_team.name if game.away_team else "Away"

                    return ArbOpportunity(
                        game_id=game.id,
                        sport=game.sport,
                        home_team=home_name,
                        away_team=away_name,
                        market_type="spreads",
                        start_time=game.start_time,
                        profit_margin=round(profit_margin, 2),
                        bet1_selection=f"{sel1} {spread:+.1f}",
                        bet1_sportsbook=best1.sportsbook,
                        bet1_odds=best1.american_odds,
                        bet1_stake_pct=round(stakes[0], 2),
                        bet2_selection=f"{sel2} {opposite_spread:+.1f}",
                        bet2_sportsbook=best2.sportsbook,
                        bet2_odds=best2.american_odds,
                        bet2_stake_pct=round(stakes[1], 2),
                    )

    return None


def detect_totals_arbitrage(
    db: Session,
    game: Game,
    min_profit: float = 0.0
) -> Optional[ArbOpportunity]:
    """
    Detect arbitrage opportunity for totals (over/under) markets.
    """
    markets = db.query(Market).filter(
        Market.game_id == game.id,
        Market.market_type == "totals"
    ).all()

    if not markets:
        return None

    # Group by total value
    totals_lines: Dict[float, Dict[str, List[Line]]] = {}

    for market in markets:
        for line in market.lines:
            total = line.line_value
            if total is None:
                continue

            if total not in totals_lines:
                totals_lines[total] = {}

            selection = market.selection.lower()  # "over" or "under"
            if selection not in totals_lines[total]:
                totals_lines[total][selection] = []
            totals_lines[total][selection].append(line)

    # Check each total value for arb
    for total, selections in totals_lines.items():
        if "over" not in selections or "under" not in selections:
            continue

        best_over = max(selections["over"], key=lambda l: l.american_odds)
        best_under = max(selections["under"], key=lambda l: l.american_odds)

        odds_list = [best_over.american_odds, best_under.american_odds]
        margin = calculate_arb_margin(odds_list)

        if margin < -min_profit:
            profit_margin = abs(margin)
            stakes = calculate_stakes(odds_list)

            home_name = game.home_team.name if game.home_team else "Home"
            away_name = game.away_team.name if game.away_team else "Away"

            return ArbOpportunity(
                game_id=game.id,
                sport=game.sport,
                home_team=home_name,
                away_team=away_name,
                market_type="totals",
                start_time=game.start_time,
                profit_margin=round(profit_margin, 2),
                bet1_selection=f"Over {total}",
                bet1_sportsbook=best_over.sportsbook,
                bet1_odds=best_over.american_odds,
                bet1_stake_pct=round(stakes[0], 2),
                bet2_selection=f"Under {total}",
                bet2_sportsbook=best_under.sportsbook,
                bet2_odds=best_under.american_odds,
                bet2_stake_pct=round(stakes[1], 2),
            )

    return None


def scan_for_arbitrage(
    db: Session,
    sport: Optional[str] = None,
    min_profit: float = 0.0
) -> List[ArbOpportunity]:
    """
    Scan all upcoming games for arbitrage opportunities.

    Args:
        db: Database session
        sport: Optional sport filter
        min_profit: Minimum profit margin to report (default 0%)

    Returns:
        List of arbitrage opportunities sorted by profit margin
    """
    logger.info(f"Scanning for arbitrage opportunities (sport={sport}, min_profit={min_profit}%)")

    # Get upcoming games
    query = db.query(Game).filter(
        Game.start_time > datetime.utcnow(),
        Game.status == "scheduled"
    )

    if sport:
        query = query.filter(Game.sport == sport)

    games = query.limit(100).all()
    logger.debug(f"Checking {len(games)} games for arbitrage")

    opportunities: List[ArbOpportunity] = []

    for game in games:
        # Check h2h markets
        arb = detect_h2h_arbitrage(db, game, min_profit)
        if arb:
            opportunities.append(arb)
            logger.info(f"Found h2h arb: {arb.home_team} vs {arb.away_team} ({arb.profit_margin}%)")

        # Check spread markets
        arb = detect_spread_arbitrage(db, game, min_profit)
        if arb:
            opportunities.append(arb)
            logger.info(f"Found spread arb: {arb.home_team} vs {arb.away_team} ({arb.profit_margin}%)")

        # Check totals markets
        arb = detect_totals_arbitrage(db, game, min_profit)
        if arb:
            opportunities.append(arb)
            logger.info(f"Found totals arb: {arb.home_team} vs {arb.away_team} ({arb.profit_margin}%)")

    # Sort by profit margin (highest first)
    opportunities.sort(key=lambda x: x.profit_margin, reverse=True)

    logger.info(f"Found {len(opportunities)} arbitrage opportunities")
    return opportunities


def calculate_arb_stakes(
    odds1: int,
    odds2: int,
    total_stake: float,
    odds3: Optional[int] = None
) -> Dict[str, Any]:
    """
    Calculate optimal stakes and expected profit for an arbitrage bet.

    Args:
        odds1: American odds for first outcome
        odds2: American odds for second outcome
        total_stake: Total amount to stake
        odds3: Optional American odds for third outcome (3-way markets)

    Returns:
        Dictionary with stakes, payouts, and profit
    """
    odds_list = [odds1, odds2]
    if odds3:
        odds_list.append(odds3)

    margin = calculate_arb_margin(odds_list)

    if margin >= 0:
        return {
            "is_arb": False,
            "margin": round(margin, 2),
            "message": "No arbitrage opportunity exists"
        }

    stakes = calculate_stakes(odds_list, total_stake)
    decimal_odds = [american_to_decimal(o) for o in odds_list]
    payouts = [s * d for s, d in zip(stakes, decimal_odds)]
    guaranteed_payout = min(payouts)
    profit = guaranteed_payout - total_stake
    roi = (profit / total_stake) * 100

    result = {
        "is_arb": True,
        "margin": round(abs(margin), 2),
        "total_stake": total_stake,
        "stakes": [round(s, 2) for s in stakes],
        "guaranteed_payout": round(guaranteed_payout, 2),
        "profit": round(profit, 2),
        "roi_percent": round(roi, 2)
    }

    return result
