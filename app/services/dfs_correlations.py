from typing import Dict, List, Any, Tuple
from sqlalchemy.orm import Session

from app.db import DFSCorrelation

NFL_CORRELATIONS = {
    ("QB", "WR"): 0.45,
    ("QB", "TE"): 0.35,
    ("QB", "RB"): 0.15,
    ("WR", "WR"): 0.10,
    ("RB", "DST"): -0.05,
    ("QB", "DST"): -0.20,
}

NBA_CORRELATIONS = {
    ("PG", "SG"): 0.15,
    ("PG", "C"): 0.20,
    ("SG", "SF"): 0.15,
    ("PF", "C"): 0.25,
    ("PG", "PF"): 0.10,
}

MLB_CORRELATIONS = {
    ("P", "C"): 0.05,
    ("1B", "3B"): 0.25,
    ("2B", "SS"): 0.20,
    ("OF", "OF"): 0.30,
}

NHL_CORRELATIONS = {
    ("C", "W"): 0.40,
    ("W", "W"): 0.35,
    ("C", "D"): 0.15,
    ("W", "D"): 0.10,
    ("D", "G"): 0.20,
}

SPORT_CORRELATIONS = {
    "NFL": NFL_CORRELATIONS,
    "NBA": NBA_CORRELATIONS,
    "MLB": MLB_CORRELATIONS,
    "NHL": NHL_CORRELATIONS,
}


def get_correlation(sport: str, pos1: str, pos2: str, same_team: bool = True) -> float:
    correlations = SPORT_CORRELATIONS.get(sport, {})
    
    key = (pos1, pos2)
    rev_key = (pos2, pos1)
    
    base_corr = correlations.get(key) or correlations.get(rev_key) or 0.0
    
    if not same_team:
        if base_corr > 0:
            base_corr = -base_corr * 0.3
        else:
            base_corr = abs(base_corr) * 0.2
    
    return base_corr


def get_game_stack_correlation(sport: str, pos1: str, pos2: str, opposing: bool = True) -> float:
    base = get_correlation(sport, pos1, pos2, same_team=False)
    
    if opposing:
        game_stack_boosts = {
            "NFL": {("QB", "WR"): 0.15, ("QB", "RB"): 0.05},
            "NBA": {("PG", "PG"): 0.10, ("C", "C"): 0.15},
            "NHL": {("C", "W"): 0.10, ("G", "G"): -0.30},
        }
        
        boosts = game_stack_boosts.get(sport, {})
        key = (pos1, pos2)
        rev_key = (pos2, pos1)
        boost = boosts.get(key) or boosts.get(rev_key) or 0.0
        
        base += boost
    
    return base


def analyze_lineup_correlations(
    lineup: List[Dict[str, Any]],
    sport: str
) -> Dict[str, Any]:
    team_players = {}
    for p in lineup:
        team_id = p.get("team_id")
        if team_id:
            if team_id not in team_players:
                team_players[team_id] = []
            team_players[team_id].append(p)
    
    stacks = []
    for team_id, players in team_players.items():
        if len(players) >= 2:
            positions = [p["position"] for p in players]
            team_name = players[0].get("team_name", f"Team {team_id}")
            stacks.append({
                "team_id": team_id,
                "team_name": team_name,
                "size": len(players),
                "positions": positions,
            })
    
    total_correlation = 0.0
    correlation_pairs = []
    
    for team_id, players in team_players.items():
        for i, p1 in enumerate(players):
            for p2 in players[i+1:]:
                corr = get_correlation(sport, p1["position"], p2["position"], same_team=True)
                total_correlation += corr
                if abs(corr) > 0.05:
                    correlation_pairs.append({
                        "player1": p1.get("player_name", f"Player {p1['player_id']}"),
                        "player2": p2.get("player_name", f"Player {p2['player_id']}"),
                        "correlation": round(corr, 3),
                        "type": "same_team",
                    })
    
    game_groups = {}
    for p in lineup:
        game_id = p.get("game_id")
        if game_id:
            if game_id not in game_groups:
                game_groups[game_id] = []
            game_groups[game_id].append(p)
    
    game_stacks = []
    for game_id, players in game_groups.items():
        teams = set(p.get("team_id") for p in players)
        if len(teams) >= 2 and len(players) >= 2:
            game_stacks.append({
                "game_id": game_id,
                "size": len(players),
                "teams": len(teams),
            })
            
            for i, p1 in enumerate(players):
                for p2 in players[i+1:]:
                    if p1.get("team_id") != p2.get("team_id"):
                        corr = get_game_stack_correlation(
                            sport, 
                            p1["position"], 
                            p2["position"],
                            opposing=True
                        )
                        total_correlation += corr * 0.5
    
    lineup_rating = "neutral"
    if total_correlation > 0.5:
        lineup_rating = "highly_correlated"
    elif total_correlation > 0.2:
        lineup_rating = "well_correlated"
    elif total_correlation < -0.1:
        lineup_rating = "contrarian"
    
    return {
        "total_correlation": round(total_correlation, 3),
        "lineup_rating": lineup_rating,
        "stacks": stacks,
        "game_stacks": game_stacks,
        "correlation_pairs": correlation_pairs,
        "recommendation": _get_correlation_recommendation(lineup_rating, stacks),
    }


def _get_correlation_recommendation(rating: str, stacks: List[Dict]) -> str:
    if rating == "highly_correlated":
        return "Strong team stacking. Best for GPP tournaments with high upside."
    elif rating == "well_correlated":
        return "Good correlation. Balanced lineup suitable for both cash and GPP."
    elif rating == "contrarian":
        return "Low ownership lineup. High risk but potential for differentiation."
    else:
        if not stacks:
            return "No team stacks. Consider adding correlated players for upside."
        return "Moderate correlation. May want to strengthen stacks for GPP."


def seed_correlations_to_db(db: Session) -> int:
    count = 0
    
    for sport, correlations in SPORT_CORRELATIONS.items():
        for (pos1, pos2), value in correlations.items():
            existing = db.query(DFSCorrelation).filter(
                DFSCorrelation.sport == sport,
                DFSCorrelation.position1 == pos1,
                DFSCorrelation.position2 == pos2
            ).first()
            
            if not existing:
                corr = DFSCorrelation(
                    sport=sport,
                    position1=pos1,
                    position2=pos2,
                    correlation_type="same_team",
                    correlation_value=value,
                    sample_size=1000,
                    is_same_team=True,
                    is_same_game=True,
                )
                db.add(corr)
                count += 1
    
    db.commit()
    return count


def get_optimal_stacks(sport: str, contest_type: str = "gpp") -> List[Dict[str, Any]]:
    stacks = {
        "NFL": [
            {"name": "QB + WR Stack", "positions": ["QB", "WR"], "correlation": 0.45, "notes": "Primary stack for NFL"},
            {"name": "QB + WR + WR", "positions": ["QB", "WR", "WR"], "correlation": 0.55, "notes": "Double stack for GPP"},
            {"name": "QB + TE Stack", "positions": ["QB", "TE"], "correlation": 0.35, "notes": "Secondary option"},
            {"name": "RB + DST", "positions": ["RB", "DST"], "correlation": 0.10, "notes": "Game script correlation"},
        ],
        "NBA": [
            {"name": "PG + C Stack", "positions": ["PG", "C"], "correlation": 0.20, "notes": "Pick and roll synergy"},
            {"name": "PF + C Stack", "positions": ["PF", "C"], "correlation": 0.25, "notes": "Frontcourt stack"},
            {"name": "Backcourt Duo", "positions": ["PG", "SG"], "correlation": 0.15, "notes": "Guard pairing"},
        ],
        "MLB": [
            {"name": "Lineup Stack (3+)", "positions": ["1B", "3B", "OF"], "correlation": 0.35, "notes": "Batting order correlation"},
            {"name": "Coors Stack", "positions": ["1B", "OF", "OF"], "correlation": 0.40, "notes": "High-scoring environment"},
        ],
        "NHL": [
            {"name": "Line Stack", "positions": ["C", "W", "W"], "correlation": 0.50, "notes": "Same line plays together"},
            {"name": "PP Stack", "positions": ["C", "W", "D"], "correlation": 0.40, "notes": "Power play unit"},
            {"name": "Goalie + D", "positions": ["G", "D", "D"], "correlation": 0.30, "notes": "Defensive stack"},
        ],
    }
    
    return stacks.get(sport, [])
