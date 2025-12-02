from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import json
import random

from app.db import (
    Player, PlayerStats, DFSPlayerSalary, DFSProjection, 
    Game, Team, InjuryReport
)

POSITION_CONFIGS = {
    "NFL": {
        "positions": ["QB", "RB", "WR", "TE", "K", "DST", "FLEX"],
        "base_points": {
            "QB": {"mean": 18.0, "std": 6.0},
            "RB": {"mean": 12.0, "std": 7.0},
            "WR": {"mean": 11.0, "std": 6.5},
            "TE": {"mean": 8.0, "std": 5.0},
            "K": {"mean": 8.0, "std": 3.0},
            "DST": {"mean": 7.0, "std": 5.0},
            "FLEX": {"mean": 11.0, "std": 6.0},
        },
        "salary_multiplier": 0.003,
    },
    "NBA": {
        "positions": ["PG", "SG", "SF", "PF", "C", "G", "F", "UTIL"],
        "base_points": {
            "PG": {"mean": 35.0, "std": 12.0},
            "SG": {"mean": 30.0, "std": 11.0},
            "SF": {"mean": 28.0, "std": 10.0},
            "PF": {"mean": 30.0, "std": 11.0},
            "C": {"mean": 32.0, "std": 12.0},
            "G": {"mean": 32.0, "std": 11.0},
            "F": {"mean": 29.0, "std": 10.0},
            "UTIL": {"mean": 30.0, "std": 11.0},
        },
        "salary_multiplier": 0.005,
    },
    "MLB": {
        "positions": ["P", "C", "1B", "2B", "3B", "SS", "OF", "UTIL"],
        "base_points": {
            "P": {"mean": 12.0, "std": 8.0},
            "C": {"mean": 6.0, "std": 4.0},
            "1B": {"mean": 8.0, "std": 5.0},
            "2B": {"mean": 7.0, "std": 4.5},
            "3B": {"mean": 7.5, "std": 5.0},
            "SS": {"mean": 7.0, "std": 4.5},
            "OF": {"mean": 7.5, "std": 5.0},
            "UTIL": {"mean": 7.0, "std": 4.5},
        },
        "salary_multiplier": 0.0015,
    },
    "NHL": {
        "positions": ["C", "W", "D", "G", "UTIL"],
        "base_points": {
            "C": {"mean": 10.0, "std": 5.0},
            "W": {"mean": 9.0, "std": 4.5},
            "D": {"mean": 6.0, "std": 3.5},
            "G": {"mean": 12.0, "std": 8.0},
            "UTIL": {"mean": 8.0, "std": 4.0},
        },
        "salary_multiplier": 0.002,
    },
}


class PlayerProjectionEngine:
    
    def __init__(self, sport: str):
        self.sport = sport
        self.config = POSITION_CONFIGS.get(sport, POSITION_CONFIGS["NFL"])
    
    def project_player(
        self,
        player: Player,
        salary: DFSPlayerSalary,
        stats: Optional[PlayerStats] = None,
        injury: Optional[InjuryReport] = None,
        opponent_team: Optional[Team] = None,
        is_home: bool = True
    ) -> Dict[str, Any]:
        position = salary.position.upper()
        base_config = self.config["base_points"].get(
            position, 
            {"mean": 10.0, "std": 5.0}
        )
        
        base_mean = base_config["mean"]
        base_std = base_config["std"]
        
        salary_factor = 1.0 + (salary.salary - 5000) * self.config["salary_multiplier"]
        salary_factor = max(0.6, min(1.5, salary_factor))
        
        home_boost = 1.03 if is_home else 0.97
        
        injury_factor = 1.0
        if injury and injury.is_active:
            status_map = {
                "out": 0.0,
                "doubtful": 0.3,
                "questionable": 0.7,
                "probable": 0.95,
            }
            injury_factor = status_map.get(injury.status.lower(), 0.9)
        
        recent_form = 1.0
        if stats:
            if stats.fantasy_points_avg:
                expected = base_mean * salary_factor
                form_ratio = stats.fantasy_points_avg / expected
                recent_form = 0.7 + 0.3 * min(1.5, max(0.5, form_ratio))
        
        projected_mean = base_mean * salary_factor * home_boost * injury_factor * recent_form
        projected_std = base_std * (1.0 if injury_factor == 1.0 else 1.2)
        
        floor = max(0, projected_mean - 1.5 * projected_std)
        ceiling = projected_mean + 2.0 * projected_std
        
        value_score = (projected_mean / salary.salary) * 1000
        
        ownership_base = 0.15
        if value_score > 5.0:
            ownership_base = 0.25
        elif value_score > 4.0:
            ownership_base = 0.20
        elif value_score < 3.0:
            ownership_base = 0.08
        
        leverage_score = (projected_mean * 0.6 + ceiling * 0.4) / ownership_base / 100
        
        return {
            "player_id": player.id,
            "player_name": player.name,
            "position": position,
            "team_id": player.team_id,
            "salary": salary.salary,
            "projected_points": round(projected_mean, 2),
            "floor": round(floor, 2),
            "ceiling": round(ceiling, 2),
            "std_dev": round(projected_std, 2),
            "value_score": round(value_score, 2),
            "ownership_projection": round(ownership_base * 100, 1),
            "leverage_score": round(leverage_score, 2),
            "confidence": round(0.7 if injury_factor == 1.0 else 0.5, 2),
            "injury_status": injury.status if injury else None,
            "is_home": is_home,
        }
    
    def project_slate(
        self,
        db: Session,
        platform: str,
        slate_date: datetime
    ) -> List[Dict[str, Any]]:
        salaries = db.query(DFSPlayerSalary).filter(
            DFSPlayerSalary.sport == self.sport,
            DFSPlayerSalary.platform == platform,
            DFSPlayerSalary.slate_date >= slate_date,
            DFSPlayerSalary.slate_date < slate_date + timedelta(days=1)
        ).all()
        
        projections = []
        
        for salary in salaries:
            player = db.query(Player).filter(Player.id == salary.player_id).first()
            if not player:
                continue
            
            stats = db.query(PlayerStats).filter(
                PlayerStats.player_id == player.id,
                PlayerStats.sport == self.sport
            ).order_by(PlayerStats.season.desc()).first()
            
            injury = db.query(InjuryReport).filter(
                InjuryReport.player_id == player.id,
                InjuryReport.is_active == True
            ).first()
            
            opponent = None
            if salary.opponent_team_id:
                opponent = db.query(Team).filter(Team.id == salary.opponent_team_id).first()
            
            proj = self.project_player(
                player=player,
                salary=salary,
                stats=stats,
                injury=injury,
                opponent_team=opponent,
                is_home=salary.is_home
            )
            
            projections.append(proj)
        
        return sorted(projections, key=lambda x: x["value_score"], reverse=True)


def generate_sample_projections(
    db: Session,
    sport: str,
    platform: str = "DraftKings",
    num_players: int = 100
) -> List[Dict[str, Any]]:
    config = POSITION_CONFIGS.get(sport, POSITION_CONFIGS["NFL"])
    positions = config["positions"]
    base_points = config["base_points"]
    
    teams = db.query(Team).filter(Team.sport == sport).all()
    if not teams:
        return []
    
    projections = []
    
    for i in range(num_players):
        position = random.choice(positions[:-1])
        team = random.choice(teams)
        
        base = base_points.get(position, {"mean": 10.0, "std": 5.0})
        
        salary = random.randint(3000, 10000)
        salary_factor = 1.0 + (salary - 5000) * config["salary_multiplier"]
        
        projected = base["mean"] * salary_factor * random.uniform(0.85, 1.15)
        std = base["std"] * random.uniform(0.8, 1.2)
        
        floor = max(0, projected - 1.5 * std)
        ceiling = projected + 2.0 * std
        value = (projected / salary) * 1000
        
        ownership = min(35, max(2, 15 + (value - 4.0) * 5 + random.uniform(-3, 3)))
        
        projections.append({
            "player_id": i + 1,
            "player_name": f"Player {i+1}",
            "position": position,
            "team_id": team.id,
            "team_name": team.name,
            "salary": salary,
            "projected_points": round(projected, 2),
            "floor": round(floor, 2),
            "ceiling": round(ceiling, 2),
            "std_dev": round(std, 2),
            "value_score": round(value, 2),
            "ownership_projection": round(ownership, 1),
            "leverage_score": round(projected / ownership * 0.5, 2),
            "confidence": round(random.uniform(0.6, 0.9), 2),
        })
    
    return sorted(projections, key=lambda x: x["value_score"], reverse=True)


def save_projections_to_db(
    db: Session,
    projections: List[Dict[str, Any]],
    sport: str,
    platform: str,
    slate_date: datetime
) -> int:
    count = 0
    
    for proj in projections:
        db_proj = DFSProjection(
            player_id=proj["player_id"],
            sport=sport,
            platform=platform,
            slate_date=slate_date,
            projected_points=proj["projected_points"],
            floor=proj.get("floor"),
            ceiling=proj.get("ceiling"),
            std_dev=proj.get("std_dev"),
            value_score=proj.get("value_score"),
            leverage_score=proj.get("leverage_score"),
            confidence=proj.get("confidence"),
            stat_projections=json.dumps(proj) if proj else None,
        )
        db.add(db_proj)
        count += 1
    
    db.commit()
    return count
