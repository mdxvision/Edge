from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
import json
import itertools
import random

from app.db import DFSLineup, DFSContest, Client


ROSTER_CONFIGS = {
    "NFL_DK": {
        "positions": ["QB", "RB", "RB", "WR", "WR", "WR", "TE", "FLEX", "DST"],
        "salary_cap": 50000,
        "flex_positions": ["RB", "WR", "TE"],
    },
    "NFL_FD": {
        "positions": ["QB", "RB", "RB", "WR", "WR", "WR", "TE", "FLEX", "DEF"],
        "salary_cap": 60000,
        "flex_positions": ["RB", "WR", "TE"],
    },
    "NBA_DK": {
        "positions": ["PG", "SG", "SF", "PF", "C", "G", "F", "UTIL"],
        "salary_cap": 50000,
        "flex_positions": {
            "G": ["PG", "SG"],
            "F": ["SF", "PF"],
            "UTIL": ["PG", "SG", "SF", "PF", "C"],
        },
    },
    "NBA_FD": {
        "positions": ["PG", "PG", "SG", "SG", "SF", "SF", "PF", "PF", "C"],
        "salary_cap": 60000,
        "flex_positions": {},
    },
    "MLB_DK": {
        "positions": ["P", "P", "C", "1B", "2B", "3B", "SS", "OF", "OF", "OF"],
        "salary_cap": 50000,
        "flex_positions": {},
    },
    "NHL_DK": {
        "positions": ["C", "C", "W", "W", "W", "D", "D", "G", "UTIL"],
        "salary_cap": 50000,
        "flex_positions": {"UTIL": ["C", "W", "D"]},
    },
}


class LineupOptimizer:
    
    def __init__(self, sport: str, platform: str = "DraftKings"):
        self.sport = sport
        self.platform = platform
        config_key = f"{sport}_{'DK' if 'Draft' in platform else 'FD'}"
        self.config = ROSTER_CONFIGS.get(config_key, ROSTER_CONFIGS["NFL_DK"])
        self.salary_cap = self.config["salary_cap"]
        self.positions = self.config["positions"]
        self.flex_positions = self.config.get("flex_positions", {})
    
    def can_fill_position(self, player_pos: str, roster_pos: str) -> bool:
        if player_pos == roster_pos:
            return True
        
        if roster_pos == "FLEX":
            return player_pos in self.flex_positions.get("FLEX", ["RB", "WR", "TE"])
        
        if roster_pos in self.flex_positions:
            return player_pos in self.flex_positions[roster_pos]
        
        return False
    
    def group_by_position(self, players: List[Dict]) -> Dict[str, List[Dict]]:
        groups = {}
        for p in players:
            pos = p["position"]
            if pos not in groups:
                groups[pos] = []
            groups[pos].append(p)
        return groups
    
    def optimize_greedy(
        self,
        projections: List[Dict[str, Any]],
        lineup_type: str = "balanced",
        max_exposure: float = 0.5,
        min_salary: int = 0,
        locked_players: Optional[List[int]] = None,
        excluded_players: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        locked_players = locked_players or []
        excluded_players = excluded_players or []
        
        available = [
            p for p in projections 
            if p["player_id"] not in excluded_players
        ]
        
        if lineup_type == "cash":
            available.sort(key=lambda x: x["projected_points"], reverse=True)
        elif lineup_type == "gpp":
            available.sort(key=lambda x: x["ceiling"], reverse=True)
        else:
            available.sort(key=lambda x: x["value_score"], reverse=True)
        
        lineup = []
        used_ids = set()
        total_salary = 0
        
        for player_id in locked_players:
            player = next((p for p in available if p["player_id"] == player_id), None)
            if player:
                lineup.append(player)
                used_ids.add(player_id)
                total_salary += player["salary"]
        
        remaining_positions = list(self.positions)
        for player in lineup:
            for i, pos in enumerate(remaining_positions):
                if self.can_fill_position(player["position"], pos):
                    remaining_positions.pop(i)
                    break
        
        for roster_pos in remaining_positions:
            best_player = None
            best_score = -1
            
            for player in available:
                if player["player_id"] in used_ids:
                    continue
                
                if not self.can_fill_position(player["position"], roster_pos):
                    continue
                
                if total_salary + player["salary"] > self.salary_cap:
                    continue
                
                remaining_spots = len(remaining_positions) - len(lineup) + len(locked_players) - 1
                if remaining_spots > 0:
                    avg_remaining = (self.salary_cap - total_salary - player["salary"]) / remaining_spots
                    if avg_remaining < 3000:
                        continue
                
                if lineup_type == "cash":
                    score = player["projected_points"]
                elif lineup_type == "gpp":
                    score = player["ceiling"] * (1 - player.get("ownership_projection", 15) / 100)
                else:
                    score = player["value_score"]
                
                if score > best_score:
                    best_score = score
                    best_player = player
            
            if best_player:
                lineup.append(best_player)
                used_ids.add(best_player["player_id"])
                total_salary += best_player["salary"]
        
        if len(lineup) < len(self.positions):
            return {
                "success": False,
                "error": "Could not fill all positions within salary cap",
                "lineup": lineup,
            }
        
        proj_points = sum(p["projected_points"] for p in lineup)
        ownership = sum(p.get("ownership_projection", 10) for p in lineup) / len(lineup)
        
        return {
            "success": True,
            "lineup": lineup,
            "total_salary": total_salary,
            "salary_remaining": self.salary_cap - total_salary,
            "projected_points": round(proj_points, 2),
            "projected_ownership": round(ownership, 1),
            "lineup_type": lineup_type,
        }
    
    def generate_multiple_lineups(
        self,
        projections: List[Dict[str, Any]],
        num_lineups: int = 20,
        lineup_type: str = "balanced",
        max_exposure: float = 0.5,
        unique_players: int = 3
    ) -> List[Dict[str, Any]]:
        lineups = []
        player_exposure = {}
        
        for _ in range(num_lineups * 3):
            if len(lineups) >= num_lineups:
                break
            
            excluded = []
            for pid, count in player_exposure.items():
                if count / max(1, len(lineups)) >= max_exposure:
                    excluded.append(pid)
            
            result = self.optimize_greedy(
                projections=projections,
                lineup_type=lineup_type,
                excluded_players=excluded
            )
            
            if not result["success"]:
                continue
            
            lineup_ids = {p["player_id"] for p in result["lineup"]}
            
            is_unique = True
            for existing in lineups:
                existing_ids = {p["player_id"] for p in existing["lineup"]}
                overlap = len(lineup_ids & existing_ids)
                if len(self.positions) - overlap < unique_players:
                    is_unique = False
                    break
            
            if is_unique:
                lineups.append(result)
                for player in result["lineup"]:
                    pid = player["player_id"]
                    player_exposure[pid] = player_exposure.get(pid, 0) + 1
        
        return lineups
    
    def calculate_correlation_boost(
        self,
        lineup: List[Dict],
        correlations: Dict[Tuple[str, str], float]
    ) -> float:
        boost = 0.0
        
        team_players = {}
        for p in lineup:
            team_id = p.get("team_id")
            if team_id:
                if team_id not in team_players:
                    team_players[team_id] = []
                team_players[team_id].append(p)
        
        for team_id, players in team_players.items():
            if len(players) >= 2:
                for i, p1 in enumerate(players):
                    for p2 in players[i+1:]:
                        key = (p1["position"], p2["position"])
                        rev_key = (p2["position"], p1["position"])
                        corr = correlations.get(key) or correlations.get(rev_key) or 0.1
                        boost += corr * 2
        
        return boost


def save_lineup_to_db(
    db: Session,
    client_id: int,
    lineup_result: Dict[str, Any],
    sport: str,
    platform: str,
    slate_date: datetime,
    contest_id: Optional[int] = None
) -> DFSLineup:
    lineup = lineup_result["lineup"]
    
    player_ids = json.dumps([p["player_id"] for p in lineup])
    positions = json.dumps([p["position"] for p in lineup])
    
    db_lineup = DFSLineup(
        client_id=client_id,
        contest_id=contest_id,
        sport=sport,
        platform=platform,
        slate_date=slate_date,
        player_ids=player_ids,
        positions=positions,
        total_salary=lineup_result["total_salary"],
        salary_remaining=lineup_result["salary_remaining"],
        projected_points=lineup_result["projected_points"],
        projected_ownership=lineup_result.get("projected_ownership"),
        leverage_score=None,
        lineup_type=lineup_result.get("lineup_type", "balanced"),
        optimization_notes=json.dumps({"players": [p["player_name"] for p in lineup]}),
    )
    
    db.add(db_lineup)
    db.commit()
    db.refresh(db_lineup)
    
    return db_lineup


def get_client_lineups(
    db: Session,
    client_id: int,
    sport: Optional[str] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    query = db.query(DFSLineup).filter(DFSLineup.client_id == client_id)
    
    if sport:
        query = query.filter(DFSLineup.sport == sport)
    
    lineups = query.order_by(DFSLineup.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": l.id,
            "sport": l.sport,
            "platform": l.platform,
            "slate_date": l.slate_date.isoformat(),
            "total_salary": l.total_salary,
            "salary_remaining": l.salary_remaining,
            "projected_points": l.projected_points,
            "projected_ownership": l.projected_ownership,
            "lineup_type": l.lineup_type,
            "player_ids": json.loads(l.player_ids) if l.player_ids else [],
            "positions": json.loads(l.positions) if l.positions else [],
            "actual_points": l.actual_points,
            "finish_position": l.finish_position,
            "is_submitted": l.is_submitted,
            "created_at": l.created_at.isoformat(),
        }
        for l in lineups
    ]
