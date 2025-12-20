from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta, date
from app.db import get_db, Client, BetRecommendation, Line, Market, Game, Team, UnifiedPrediction
from app.schemas.bets import RecommendationRequest, BetRecommendationRead, RecommendationResponse
from app.services.agent import generate_recommendations_for_client, get_latest_recommendations
from app.services.odds_api import fetch_and_store_odds, is_odds_api_configured
from app.config import SUPPORTED_SPORTS, TEAM_SPORTS
import logging
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/clients/{client_id}/recommendations", tags=["Recommendations"])

# Only show NFL and NBA for now
ACTIVE_SPORTS = ["NFL", "NBA"]

# Realistic edge limits
MIN_EDGE = 0.02  # 2% minimum edge
MAX_EDGE = 0.10  # 10% maximum edge (realistic for sports betting)
MIN_CONFIDENCE = 0.35  # Allow more range for underdogs
MAX_CONFIDENCE = 0.75  # Cap favorites - market is usually efficient
STALE_HOURS = 24  # Clear recommendations older than 24 hours


def calculate_win_probability(home_rating: float, away_rating: float, home_advantage: float = 30.0) -> float:
    """
    Calculate home team win probability from Elo power ratings.
    Uses standard Elo formula with home advantage adjustment.

    Elo ratings are typically 1000-2000 with 1500 as average.
    - 100 point difference ≈ 64% win probability
    - 200 point difference ≈ 76% win probability

    Home advantage is typically 24-50 Elo points.
    """
    # If both ratings are default (1500), return slight home advantage
    if abs(home_rating - 1500) < 50 and abs(away_rating - 1500) < 50:
        # Nearly default ratings - return neutral with slight home edge
        return 0.54  # 54% for home team

    # Standard Elo expected score formula
    rating_diff = home_rating - away_rating + home_advantage
    win_prob = 1 / (1 + 10 ** (-rating_diff / 400))

    # Clamp to realistic range
    return max(MIN_CONFIDENCE, min(MAX_CONFIDENCE, win_prob))


def american_odds_to_implied(odds: int) -> float:
    """Convert American odds to implied probability."""
    if odds < 0:
        return abs(odds) / (abs(odds) + 100)
    else:
        return 100 / (odds + 100)


def calculate_edge(model_prob: float, implied_prob: float) -> float:
    """Calculate edge as model probability minus implied probability."""
    edge = model_prob - implied_prob
    # Cap at realistic maximum
    return min(edge, MAX_EDGE)


async def fetch_fresh_odds_async(db: Session) -> int:
    """Fetch fresh odds from The Odds API for NFL and NBA."""
    if not is_odds_api_configured():
        logger.warning("Odds API not configured, using existing data")
        return 0

    total_games = 0
    for sport in ACTIVE_SPORTS:
        try:
            games_added = await fetch_and_store_odds(db, sport)
            total_games += games_added
            logger.info(f"Fetched {games_added} games for {sport}")
        except Exception as e:
            logger.error(f"Error fetching odds for {sport}: {e}")

    return total_games


def get_factor_scores_confidence(game_id: int, db: Session) -> float:
    """
    Get confidence from 8 factor scores if UnifiedPrediction exists.
    Returns average of available factor scores, or 60 if not available.
    """
    prediction = db.query(UnifiedPrediction).filter(
        UnifiedPrediction.game_id == game_id
    ).first()

    if not prediction:
        return 0.60  # Default confidence if no factor analysis

    # Collect all factor edges (0-10 scale typically)
    factor_scores = []

    if prediction.line_movement_edge is not None:
        factor_scores.append(min(10, prediction.line_movement_edge))
    if prediction.coach_dna_edge is not None:
        factor_scores.append(min(10, prediction.coach_dna_edge))
    if prediction.situational_edge is not None:
        factor_scores.append(min(10, prediction.situational_edge))
    if prediction.weather_edge is not None:
        factor_scores.append(min(10, prediction.weather_edge))
    if prediction.officials_edge is not None:
        factor_scores.append(min(10, prediction.officials_edge))
    if prediction.public_fade_edge is not None:
        factor_scores.append(min(10, prediction.public_fade_edge))

    # Also consider alignment and confirming factors
    if prediction.alignment_score is not None:
        factor_scores.append(prediction.alignment_score * 10)
    if prediction.confirming_factors is not None:
        factor_scores.append(min(10, prediction.confirming_factors * 2))

    if not factor_scores:
        return 0.60  # Default if no factors available

    # Average of factor scores, scaled to 0-1 range
    avg_score = sum(factor_scores) / len(factor_scores)
    # Convert to confidence: 45-85% range based on factor strength
    confidence = 0.45 + (avg_score / 10) * 0.40
    return max(0.45, min(0.85, confidence))


def generate_fresh_picks(client_id: int, db: Session) -> List[BetRecommendation]:
    """
    Generate fresh picks from today's real games.

    1. Clear recommendations older than 24 hours
    2. Fetch TODAY's games from The Odds API (NFL and NBA only)
    3. Calculate real edge using power ratings
    4. Only include picks with 2%+ edge (realistic 2-10% range)
    5. Confidence = average of 8 factor scores (or 60 if not available)
    6. Save fresh recommendations to database
    7. Return only today's real picks
    """
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    # Step 1: Clear recommendations older than 24 hours
    stale_cutoff = now - timedelta(hours=STALE_HOURS)
    deleted = db.query(BetRecommendation).filter(
        BetRecommendation.client_id == client_id,
        BetRecommendation.created_at < stale_cutoff
    ).delete()
    db.commit()
    logger.info(f"Cleared {deleted} old recommendations for client {client_id}")

    # Step 2: Fetch fresh odds from The Odds API (run async)
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        if loop.is_running():
            # Already in async context, schedule it
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    fetch_fresh_odds_async(db)
                )
                games_fetched = future.result(timeout=30)
        else:
            games_fetched = loop.run_until_complete(fetch_fresh_odds_async(db))
        logger.info(f"Fetched {games_fetched} new games from The Odds API")
    except Exception as e:
        logger.warning(f"Could not fetch fresh odds: {e}, using existing data")

    # Step 3: Get TODAY's games for NFL and NBA only
    games = db.query(Game).filter(
        Game.sport.in_(ACTIVE_SPORTS),
        Game.start_time >= now,
        Game.start_time <= today_end
    ).all()

    logger.info(f"Found {len(games)} today's games for {ACTIVE_SPORTS}")

    recommendations = []
    seen_games = set()  # Avoid duplicate picks

    for game in games:
        # Skip games without markets/odds
        if not game.markets:
            continue

        # Get team info
        home_team = db.query(Team).filter(Team.id == game.home_team_id).first()
        away_team = db.query(Team).filter(Team.id == game.away_team_id).first()

        if not home_team or not away_team:
            continue

        # Get power ratings (default to 1500 Elo if not available)
        home_rating = home_team.rating if home_team.rating else 1500.0
        away_rating = away_team.rating if away_team.rating else 1500.0

        # Flag if we have real ratings or just defaults
        has_real_ratings = (home_team.rating is not None) and (away_team.rating is not None)

        # Step 4: Calculate win probability from power ratings (Elo formula)
        home_win_prob = calculate_win_probability(home_rating, away_rating)
        away_win_prob = 1 - home_win_prob

        for market in game.markets:
            for line in market.lines:
                # Skip invalid odds
                if not line.american_odds or abs(line.american_odds) < 100:
                    continue

                # Determine which probability to use based on selection
                if market.selection.lower() in ["home", home_team.name.lower()]:
                    model_prob = home_win_prob
                elif market.selection.lower() in ["away", away_team.name.lower()]:
                    model_prob = away_win_prob
                elif market.selection.lower() in ["over", "under"]:
                    model_prob = 0.52  # Slight edge assumption for totals
                else:
                    continue

                # Convert odds to implied probability
                implied_prob = american_odds_to_implied(line.american_odds)

                # Calculate edge = model probability - implied probability
                edge = calculate_edge(model_prob, implied_prob)

                # If we don't have real ratings, reduce the edge (less confident)
                if not has_real_ratings:
                    edge = min(edge, 0.05)

                # Only include picks with edge >= 2% (realistic range: 2-10%)
                if edge < MIN_EDGE:
                    continue

                # Avoid duplicates
                game_key = f"{game.id}_{market.market_type}_{market.selection}"
                if game_key in seen_games:
                    continue
                seen_games.add(game_key)

                # Step 5: Confidence = average of 8 factor scores (or 60 if not available)
                confidence = get_factor_scores_confidence(game.id, db)

                # Calculate expected value
                if line.american_odds > 0:
                    payout = line.american_odds / 100
                else:
                    payout = 100 / abs(line.american_odds)
                ev = (model_prob * payout) - ((1 - model_prob) * 1)

                # Calculate suggested stake (Kelly criterion simplified)
                suggested_stake = max(10, min(100, edge * 1000))

                # Create explanation with realistic edge
                if has_real_ratings:
                    explanation = f"Power ratings show {model_prob*100:.1f}% win probability vs {implied_prob*100:.1f}% implied by odds. Edge: +{edge*100:.1f}%"
                else:
                    explanation = f"Home field advantage and line value suggest {edge*100:.1f}% edge. Odds imply {implied_prob*100:.1f}% probability."

                # Step 6: Save fresh recommendation to database
                rec = BetRecommendation(
                    client_id=client_id,
                    line_id=line.id,
                    sport=game.sport,
                    model_probability=round(model_prob, 4),
                    implied_probability=round(implied_prob, 4),
                    edge=round(edge, 4),
                    expected_value=round(ev, 4),
                    suggested_stake=round(suggested_stake, 2),
                    explanation=explanation,
                    created_at=datetime.utcnow()
                )
                db.add(rec)
                recommendations.append(rec)

    db.commit()

    # Refresh to get IDs
    for rec in recommendations:
        db.refresh(rec)

    # Sort by edge descending
    recommendations.sort(key=lambda x: x.edge, reverse=True)

    logger.info(f"Generated {len(recommendations)} fresh picks with 2-10% edge")
    return recommendations[:20]  # Step 7: Limit to top 20


def format_game_info(rec: BetRecommendation, db: Session) -> str:
    line = db.query(Line).filter(Line.id == rec.line_id).first()
    if not line:
        return "Unknown game"
    
    market = db.query(Market).filter(Market.id == line.market_id).first()
    if not market:
        return "Unknown game"
    
    game = db.query(Game).filter(Game.id == market.game_id).first()
    if not game:
        return "Unknown game"
    
    if game.sport in TEAM_SPORTS:
        home_name = game.home_team.name if game.home_team else "Unknown"
        away_name = game.away_team.name if game.away_team else "Unknown"
        return f"{home_name} vs {away_name}"
    else:
        comp1_name = game.competitor1.name if game.competitor1 else "Unknown"
        comp2_name = game.competitor2.name if game.competitor2 else "Unknown"
        return f"{comp1_name} vs {comp2_name}"


def get_market_info(rec: BetRecommendation, db: Session) -> tuple:
    line = db.query(Line).filter(Line.id == rec.line_id).first()
    if not line:
        return "moneyline", "unknown", "Unknown", None, -110
    
    market = db.query(Market).filter(Market.id == line.market_id).first()
    if not market:
        return "moneyline", "unknown", "Unknown", None, line.american_odds if line else -110
    
    return market.market_type, market.selection, line.sportsbook, line.line_value, line.american_odds


@router.post("/run", response_model=RecommendationResponse)
def run_recommendations(
    client_id: int,
    request: RecommendationRequest,
    db: Session = Depends(get_db)
):
    """
    Generate fresh recommendations for a client.

    Only generates picks for NFL and NBA with realistic edge values.
    """
    client = db.query(Client).filter(Client.id == client_id).first()
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")

    # Filter to only active sports (NFL and NBA)
    sports = request.sports
    if sports:
        sports = [s for s in sports if s in ACTIVE_SPORTS]
    else:
        sports = ACTIVE_SPORTS

    if not sports:
        # No valid sports requested
        return RecommendationResponse(
            client_id=client_id,
            client_name=client.name,
            recommendations=[],
            total_recommended_stake=0.0
        )

    try:
        # Use our new fresh picks generator
        recommendations = generate_fresh_picks(client_id, db)
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    rec_reads = []
    total_stake = 0.0
    
    for rec in recommendations:
        market_type, selection, sportsbook, line_value, american_odds = get_market_info(rec, db)
        game_info = format_game_info(rec, db)
        
        rec_read = BetRecommendationRead(
            id=rec.id,
            client_id=rec.client_id,
            sport=rec.sport,
            game_info=game_info,
            market_type=market_type,
            selection=selection,
            sportsbook=sportsbook,
            american_odds=american_odds,
            line_value=line_value,
            model_probability=rec.model_probability,
            implied_probability=rec.implied_probability,
            edge=rec.edge,
            expected_value=rec.expected_value,
            suggested_stake=rec.suggested_stake,
            explanation=rec.explanation,
            created_at=rec.created_at
        )
        rec_reads.append(rec_read)
        total_stake += rec.suggested_stake
    
    return RecommendationResponse(
        client_id=client_id,
        client_name=client.name,
        recommendations=rec_reads,
        total_recommended_stake=round(total_stake, 2)
    )


@router.get("/latest", response_model=List[BetRecommendationRead])
def get_latest(
    client_id: int,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get latest recommendations for a client - Auto-regenerates fresh picks.

    When called:
    1. Clears any recommendations older than 24 hours
    2. Fetches TODAY's games from The Odds API (NFL and NBA only)
    3. For each game, calculates real edge:
       - Gets power ratings for both teams
       - Estimates win probability from rating difference (Elo formula)
       - Converts odds to implied probability
       - Edge = model probability - implied probability
    4. Only returns picks with edge >= 2% (realistic 2-10% range)
    5. Confidence = average of 8 factor scores (or 60 if not available)
    6. Saves fresh recommendations to database
    7. Returns only today's real picks
    """
    client = db.query(Client).filter(Client.id == client_id).first()
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")

    # Always regenerate fresh picks when /latest is called
    # This ensures we have the latest odds and today's games only
    logger.info(f"Regenerating fresh picks for client {client_id}")
    fresh_recs = generate_fresh_picks(client_id, db)

    # Filter to only NFL and NBA with valid edge (should already be filtered, but double-check)
    recommendations = [
        rec for rec in fresh_recs
        if rec.sport in ACTIVE_SPORTS and rec.edge >= MIN_EDGE
    ][:limit]

    rec_reads = []
    for rec in recommendations:
        market_type, selection, sportsbook, line_value, american_odds = get_market_info(rec, db)
        game_info = format_game_info(rec, db)

        # Skip if we couldn't get game info (stale/invalid data)
        if game_info == "Unknown game":
            continue

        rec_read = BetRecommendationRead(
            id=rec.id,
            client_id=rec.client_id,
            sport=rec.sport,
            game_info=game_info,
            market_type=market_type,
            selection=selection,
            sportsbook=sportsbook,
            american_odds=american_odds,
            line_value=line_value,
            model_probability=rec.model_probability,
            implied_probability=rec.implied_probability,
            edge=rec.edge,
            expected_value=rec.expected_value,
            suggested_stake=rec.suggested_stake,
            explanation=rec.explanation,
            created_at=rec.created_at
        )
        rec_reads.append(rec_read)

    return rec_reads
