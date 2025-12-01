from typing import List, Tuple
from app.schemas.bets import BetCandidate
from app.db import Client, BetRecommendation
from app.config import TEAM_SPORTS


def get_stake_multiplier(edge: float, risk_profile: str) -> float:
    if risk_profile == "conservative":
        if edge >= 0.05:
            return 0.5
        elif edge >= 0.03:
            return 0.25
        else:
            return 0.0
    
    elif risk_profile == "balanced":
        if edge >= 0.05:
            return 1.0
        elif edge >= 0.03:
            return 0.5
        else:
            return 0.0
    
    elif risk_profile == "aggressive":
        if edge >= 0.07:
            return 2.0
        elif edge >= 0.04:
            return 1.0
        elif edge >= 0.02:
            return 0.5
        else:
            return 0.0
    
    return 0.0


def get_daily_exposure_cap(risk_profile: str) -> float:
    if risk_profile == "conservative":
        return 0.03
    elif risk_profile == "balanced":
        return 0.06
    elif risk_profile == "aggressive":
        return 0.10
    return 0.05


def get_min_edge_threshold(risk_profile: str) -> float:
    if risk_profile == "conservative":
        return 0.03
    elif risk_profile == "balanced":
        return 0.03
    elif risk_profile == "aggressive":
        return 0.02
    return 0.03


def size_bets(
    client: Client,
    candidates: List[BetCandidate]
) -> List[Tuple[BetCandidate, float, str]]:
    bankroll = client.bankroll
    risk_profile = client.risk_profile
    
    base_unit = bankroll * 0.01
    
    daily_cap = get_daily_exposure_cap(risk_profile) * bankroll
    max_single_bet = bankroll * 0.02
    
    min_edge = get_min_edge_threshold(risk_profile)
    
    filtered_candidates = [c for c in candidates if c.edge >= min_edge]
    filtered_candidates.sort(key=lambda x: x.edge, reverse=True)
    
    results = []
    total_exposure = 0.0
    
    for candidate in filtered_candidates:
        multiplier = get_stake_multiplier(candidate.edge, risk_profile)
        
        if multiplier == 0:
            continue
        
        stake = base_unit * multiplier
        
        stake = min(stake, max_single_bet)
        
        if total_exposure + stake > daily_cap:
            remaining = daily_cap - total_exposure
            if remaining >= base_unit * 0.25:
                stake = remaining
            else:
                continue
        
        total_exposure += stake
        
        explanation = generate_explanation(candidate, stake, bankroll, risk_profile)
        
        results.append((candidate, stake, explanation))
        
        if total_exposure >= daily_cap:
            break
    
    return results


def generate_explanation(
    candidate: BetCandidate, 
    stake: float, 
    bankroll: float,
    risk_profile: str
) -> str:
    stake_pct = (stake / bankroll) * 100
    
    if candidate.sport in TEAM_SPORTS:
        matchup = f"{candidate.home_team_name} vs {candidate.away_team_name}"
        selection_desc = f"{candidate.selection} team"
    else:
        matchup = f"{candidate.competitor1_name} vs {candidate.competitor2_name}"
        if candidate.selection == "competitor1":
            selection_desc = candidate.competitor1_name
        elif candidate.selection == "competitor2":
            selection_desc = candidate.competitor2_name
        else:
            selection_desc = candidate.selection
    
    odds_str = f"+{candidate.american_odds}" if candidate.american_odds > 0 else str(candidate.american_odds)
    
    line_info = ""
    if candidate.line_value is not None:
        line_info = f" ({candidate.line_value:+.1f})"
    
    explanation = (
        f"{candidate.sport}: {matchup} - {candidate.market_type} {selection_desc}{line_info} at {odds_str}. "
        f"Model probability: {candidate.model_probability:.1%}, implied: {candidate.implied_probability:.1%}. "
        f"Edge: {candidate.edge:+.1%}. "
        f"Suggested stake: {stake_pct:.1f}% of bankroll (${stake:.2f}, {risk_profile} profile)."
    )
    
    return explanation


def create_bet_recommendations(
    client: Client,
    candidates: List[BetCandidate]
) -> List[BetRecommendation]:
    sized_bets = size_bets(client, candidates)
    
    recommendations = []
    
    for candidate, stake, explanation in sized_bets:
        rec = BetRecommendation(
            client_id=client.id,
            line_id=candidate.line_id,
            sport=candidate.sport,
            suggested_stake=stake,
            model_probability=candidate.model_probability,
            implied_probability=candidate.implied_probability,
            edge=candidate.edge,
            expected_value=candidate.expected_value,
            explanation=explanation
        )
        recommendations.append(rec)
    
    return recommendations
