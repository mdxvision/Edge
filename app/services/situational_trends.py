"""
Situational Trends Service
Analyzes team performance in various betting situations
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import and_, or_, desc, func
from sqlalchemy.orm import Session

from app.db import SituationalTrend


# Define all supported situation types
SITUATION_TYPES = {
    # Basic role situations
    "home_favorite": "Home Favorite",
    "road_favorite": "Road Favorite",
    "home_underdog": "Home Underdog",
    "road_underdog": "Road Underdog",

    # Rest-related
    "after_bye_week": "After Bye Week",
    "short_rest": "Short Rest (<4 days)",
    "long_rest": "Long Rest (7+ days)",
    "back_to_back": "Back-to-Back Games",

    # Game type
    "division_game": "Division Game",
    "conference_game": "Conference Game",
    "non_conference": "Non-Conference Game",
    "primetime_game": "Primetime Game",
    "day_game": "Day Game",
    "night_game": "Night Game",

    # Situational spots
    "revenge_game": "Revenge Game (lost last H2H)",
    "letdown_spot": "Letdown Spot (after big win)",
    "lookahead_spot": "Lookahead Spot",
    "trap_game": "Trap Game",

    # Streak-based
    "on_winning_streak": "On Winning Streak (3+)",
    "on_losing_streak": "On Losing Streak (3+)",
    "after_win": "Coming Off Win",
    "after_loss": "Coming Off Loss",
    "after_blowout_win": "After Blowout Win (14+)",
    "after_close_loss": "After Close Loss (3 or less)",

    # Travel-related
    "cross_country_travel": "Cross-Country Travel",
    "travel_west_to_east": "Travel West to East",
    "travel_east_to_west": "Travel East to West",
    "home_after_road_trip": "Home After Road Trip",

    # Special situations
    "as_big_favorite": "Big Favorite (-10 or more)",
    "as_big_underdog": "Big Underdog (+10 or more)",
    "in_close_spread": "Close Spread (3 or less)",
    "high_total_game": "High Total Game (50+)",
    "low_total_game": "Low Total Game (40 or less)",
}


def get_situation_display_name(situation_type: str) -> str:
    """Get the display name for a situation type"""
    return SITUATION_TYPES.get(situation_type, situation_type.replace("_", " ").title())


def update_situational_trend(
    db: Session,
    sport: str,
    team_name: str,
    situation_type: str,
    won: bool,
    covered: bool,
    went_over: bool,
    margin: float,
    total_points: float,
    is_push: bool = False,
    season: Optional[str] = None
) -> SituationalTrend:
    """Update or create a situational trend record"""

    if season is None:
        season = str(datetime.now().year)

    # Find existing trend or create new
    trend = db.query(SituationalTrend).filter(
        SituationalTrend.sport == sport.lower(),
        SituationalTrend.team_name == team_name,
        SituationalTrend.situation_type == situation_type,
        SituationalTrend.season == season
    ).first()

    if not trend:
        trend = SituationalTrend(
            sport=sport.lower(),
            team_name=team_name,
            situation_type=situation_type,
            situation_description=get_situation_display_name(situation_type),
            season=season,
            wins=0,
            losses=0,
            pushes=0,
            ats_wins=0,
            ats_losses=0,
            ats_pushes=0,
            over_wins=0,
            under_wins=0,
            avg_margin=0,
            avg_total=0,
            cover_percentage=0
        )
        db.add(trend)

    # Update straight-up record
    if is_push:
        trend.pushes += 1
    elif won:
        trend.wins += 1
    else:
        trend.losses += 1

    # Update ATS record
    if covered:
        trend.ats_wins += 1
    elif is_push:
        trend.ats_pushes += 1
    else:
        trend.ats_losses += 1

    # Update O/U record
    if went_over:
        trend.over_wins += 1
    else:
        trend.under_wins += 1

    # Update running averages
    total_games = trend.wins + trend.losses + trend.pushes
    if total_games > 0:
        # Recalculate averages (simplified - in production, store running totals)
        if trend.avg_margin is None:
            trend.avg_margin = margin
        else:
            trend.avg_margin = (trend.avg_margin * (total_games - 1) + margin) / total_games

        if trend.avg_total is None:
            trend.avg_total = total_points
        else:
            trend.avg_total = (trend.avg_total * (total_games - 1) + total_points) / total_games

    # Update cover percentage
    ats_total = trend.ats_wins + trend.ats_losses
    if ats_total > 0:
        trend.cover_percentage = round(trend.ats_wins / ats_total * 100, 1)

    db.commit()
    db.refresh(trend)
    return trend


def get_team_trends(
    db: Session,
    sport: str,
    team_name: str,
    season: Optional[str] = None,
    min_games: int = 3
) -> List[Dict[str, Any]]:
    """Get all situational trends for a team"""

    query = db.query(SituationalTrend).filter(
        SituationalTrend.sport == sport.lower(),
        SituationalTrend.team_name.ilike(f"%{team_name}%")
    )

    if season:
        query = query.filter(SituationalTrend.season == season)

    trends = query.all()

    result = []
    for trend in trends:
        total_games = trend.wins + trend.losses + (trend.pushes or 0)
        if total_games < min_games:
            continue

        ats_total = trend.ats_wins + trend.ats_losses
        ou_total = trend.over_wins + trend.under_wins

        result.append({
            "situation": trend.situation_type,
            "display_name": get_situation_display_name(trend.situation_type),
            "season": trend.season,
            "record": f"{trend.wins}-{trend.losses}" + (f"-{trend.pushes}" if trend.pushes else ""),
            "ats_record": f"{trend.ats_wins}-{trend.ats_losses}" + (f"-{trend.ats_pushes}" if trend.ats_pushes else ""),
            "ou_record": f"{trend.over_wins}-{trend.under_wins}",
            "cover_pct": trend.cover_percentage or 0,
            "over_pct": round(trend.over_wins / ou_total * 100, 1) if ou_total > 0 else 0,
            "avg_margin": round(trend.avg_margin or 0, 1),
            "avg_total": round(trend.avg_total or 0, 1),
            "total_games": total_games,
            "edge": round((trend.cover_percentage or 0) - 52.38, 1)  # Break-even is ~52.38%
        })

    # Sort by edge (best to worst)
    result.sort(key=lambda x: x["edge"], reverse=True)
    return result


def get_profitable_situations(
    db: Session,
    sport: str,
    min_games: int = 5,
    min_cover_pct: float = 55.0,
    season: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Find profitable betting situations across all teams"""

    query = db.query(SituationalTrend).filter(
        SituationalTrend.sport == sport.lower(),
        SituationalTrend.cover_percentage >= min_cover_pct
    )

    if season:
        query = query.filter(SituationalTrend.season == season)

    trends = query.order_by(desc(SituationalTrend.cover_percentage)).all()

    result = []
    for trend in trends:
        total_games = trend.wins + trend.losses + (trend.pushes or 0)
        if total_games < min_games:
            continue

        result.append({
            "team": trend.team_name,
            "situation": trend.situation_type,
            "display_name": get_situation_display_name(trend.situation_type),
            "season": trend.season,
            "ats_record": f"{trend.ats_wins}-{trend.ats_losses}",
            "cover_pct": trend.cover_percentage,
            "total_games": total_games,
            "edge": round((trend.cover_percentage or 0) - 52.38, 1),
            "roi": round(((trend.cover_percentage or 0) / 100 * 1.91) - 1, 3) * 100  # Assuming -110 odds
        })

    return result


def get_fade_situations(
    db: Session,
    sport: str,
    min_games: int = 5,
    max_cover_pct: float = 45.0,
    season: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Find situations to fade (bet against)"""

    query = db.query(SituationalTrend).filter(
        SituationalTrend.sport == sport.lower(),
        SituationalTrend.cover_percentage <= max_cover_pct,
        SituationalTrend.cover_percentage > 0  # Exclude 0% (no data)
    )

    if season:
        query = query.filter(SituationalTrend.season == season)

    trends = query.order_by(SituationalTrend.cover_percentage).all()

    result = []
    for trend in trends:
        total_games = trend.wins + trend.losses + (trend.pushes or 0)
        if total_games < min_games:
            continue

        result.append({
            "team": trend.team_name,
            "situation": trend.situation_type,
            "display_name": get_situation_display_name(trend.situation_type),
            "season": trend.season,
            "ats_record": f"{trend.ats_wins}-{trend.ats_losses}",
            "cover_pct": trend.cover_percentage,
            "fade_cover_pct": 100 - (trend.cover_percentage or 0),
            "total_games": total_games,
            "edge": round(100 - (trend.cover_percentage or 0) - 52.38, 1),  # Edge if fading
            "roi": round(((100 - (trend.cover_percentage or 0)) / 100 * 1.91) - 1, 3) * 100
        })

    return result


def analyze_game_situations(
    db: Session,
    sport: str,
    home_team: str,
    away_team: str,
    spread: float,
    total: float,
    is_primetime: bool = False,
    is_division: bool = False,
    home_days_rest: int = 7,
    away_days_rest: int = 7,
    home_last_result: Optional[str] = None,  # "win", "loss", "blowout_win", "close_loss"
    away_last_result: Optional[str] = None,
    season: Optional[str] = None
) -> Dict[str, Any]:
    """Analyze applicable situational trends for a matchup"""

    if season is None:
        season = str(datetime.now().year)

    # Determine applicable situations for each team
    home_situations = []
    away_situations = []

    # Role-based situations
    if spread < 0:  # Home is favorite
        home_situations.append("home_favorite")
        away_situations.append("road_underdog")
        if spread <= -10:
            home_situations.append("as_big_favorite")
            away_situations.append("as_big_underdog")
    else:  # Away is favorite or pick'em
        home_situations.append("home_underdog")
        away_situations.append("road_favorite")
        if spread >= 10:
            home_situations.append("as_big_underdog")
            away_situations.append("as_big_favorite")

    if abs(spread) <= 3:
        home_situations.append("in_close_spread")
        away_situations.append("in_close_spread")

    # Rest situations
    if home_days_rest <= 3:
        home_situations.append("short_rest")
    elif home_days_rest >= 7:
        home_situations.append("long_rest")

    if away_days_rest <= 3:
        away_situations.append("short_rest")
    elif away_days_rest >= 7:
        away_situations.append("long_rest")

    # Last result situations
    if home_last_result == "win":
        home_situations.append("after_win")
    elif home_last_result == "loss":
        home_situations.append("after_loss")
    elif home_last_result == "blowout_win":
        home_situations.extend(["after_win", "after_blowout_win"])
    elif home_last_result == "close_loss":
        home_situations.extend(["after_loss", "after_close_loss"])

    if away_last_result == "win":
        away_situations.append("after_win")
    elif away_last_result == "loss":
        away_situations.append("after_loss")
    elif away_last_result == "blowout_win":
        away_situations.extend(["after_win", "after_blowout_win"])
    elif away_last_result == "close_loss":
        away_situations.extend(["after_loss", "after_close_loss"])

    # Game type situations
    if is_primetime:
        home_situations.append("primetime_game")
        away_situations.append("primetime_game")

    if is_division:
        home_situations.append("division_game")
        away_situations.append("division_game")

    # Total situations
    if total >= 50:
        home_situations.append("high_total_game")
        away_situations.append("high_total_game")
    elif total <= 40:
        home_situations.append("low_total_game")
        away_situations.append("low_total_game")

    # Fetch trends for applicable situations
    def get_trends_for_situations(team_name: str, situations: List[str]) -> List[Dict]:
        trends = []
        for situation in situations:
            trend = db.query(SituationalTrend).filter(
                SituationalTrend.sport == sport.lower(),
                SituationalTrend.team_name.ilike(f"%{team_name}%"),
                SituationalTrend.situation_type == situation,
                SituationalTrend.season == season
            ).first()

            if trend:
                total_games = trend.wins + trend.losses + (trend.pushes or 0)
                if total_games >= 3:
                    trends.append({
                        "situation": situation,
                        "display_name": get_situation_display_name(situation),
                        "ats_record": f"{trend.ats_wins}-{trend.ats_losses}",
                        "cover_pct": trend.cover_percentage or 0,
                        "total_games": total_games,
                        "edge": round((trend.cover_percentage or 0) - 52.38, 1)
                    })
        return trends

    home_trends = get_trends_for_situations(home_team, home_situations)
    away_trends = get_trends_for_situations(away_team, away_situations)

    # Calculate combined edge
    home_edge = sum(t["edge"] for t in home_trends) / len(home_trends) if home_trends else 0
    away_edge = sum(t["edge"] for t in away_trends) / len(away_trends) if away_trends else 0

    # Determine recommendation
    net_edge = home_edge - away_edge
    if net_edge > 5:
        recommendation = f"Lean {home_team} (situational edge: +{net_edge:.1f}%)"
    elif net_edge < -5:
        recommendation = f"Lean {away_team} (situational edge: +{abs(net_edge):.1f}%)"
    else:
        recommendation = "No clear situational edge"

    return {
        "home_team": home_team,
        "away_team": away_team,
        "spread": spread,
        "total": total,
        "home_situations": home_situations,
        "away_situations": away_situations,
        "home_trends": home_trends,
        "away_trends": away_trends,
        "home_combined_edge": round(home_edge, 1),
        "away_combined_edge": round(away_edge, 1),
        "net_edge": round(net_edge, 1),
        "recommendation": recommendation
    }


def seed_situational_trends(db: Session, sport: str) -> Dict[str, Any]:
    """Seed sample situational trends data"""

    sample_data = {
        "nfl": [
            # Chiefs
            {"team": "Kansas City Chiefs", "situations": {
                "home_favorite": (10, 4, 0, 8, 6, 0, 6, 8, 5.2, 48.3),
                "road_favorite": (7, 3, 0, 6, 4, 0, 5, 5, 3.8, 47.1),
                "after_win": (12, 3, 0, 9, 6, 0, 8, 7, 8.1, 49.5),
                "primetime_game": (8, 2, 0, 7, 3, 0, 6, 4, 6.5, 51.2),
                "as_big_favorite": (5, 1, 0, 4, 2, 0, 3, 3, 12.3, 52.0),
            }},
            # 49ers
            {"team": "San Francisco 49ers", "situations": {
                "home_favorite": (9, 3, 0, 8, 4, 0, 5, 7, 7.1, 46.8),
                "road_favorite": (5, 4, 0, 4, 5, 0, 6, 3, 1.2, 44.2),
                "after_loss": (4, 2, 0, 5, 1, 0, 3, 3, 4.5, 45.0),
                "division_game": (5, 1, 0, 5, 1, 0, 4, 2, 9.3, 47.5),
                "primetime_game": (6, 3, 0, 5, 4, 0, 5, 4, 4.2, 48.0),
            }},
            # Eagles
            {"team": "Philadelphia Eagles", "situations": {
                "home_favorite": (8, 4, 0, 7, 5, 0, 7, 5, 4.8, 47.2),
                "road_underdog": (2, 3, 0, 2, 3, 0, 3, 2, -1.5, 43.8),
                "after_win": (9, 4, 0, 7, 6, 0, 8, 5, 5.2, 48.1),
                "short_rest": (3, 2, 0, 2, 3, 0, 3, 2, 1.8, 45.5),
                "division_game": (4, 2, 0, 4, 2, 0, 3, 3, 3.5, 44.2),
            }},
            # Ravens
            {"team": "Baltimore Ravens", "situations": {
                "home_favorite": (9, 2, 0, 8, 3, 0, 7, 4, 8.5, 49.8),
                "road_favorite": (6, 3, 0, 5, 4, 0, 6, 3, 2.1, 46.5),
                "after_blowout_win": (4, 1, 0, 4, 1, 0, 3, 2, 11.0, 52.5),
                "high_total_game": (5, 2, 0, 4, 3, 0, 6, 1, 5.5, 55.2),
            }},
        ],
        "nba": [
            # Lakers
            {"team": "Los Angeles Lakers", "situations": {
                "home_favorite": (22, 10, 0, 18, 14, 0, 18, 14, 3.2, 225.5),
                "road_underdog": (8, 12, 0, 9, 11, 0, 12, 8, -2.5, 221.8),
                "back_to_back": (5, 7, 0, 4, 8, 0, 7, 5, -1.8, 218.5),
                "after_win": (25, 12, 0, 20, 17, 0, 22, 15, 4.1, 227.2),
            }},
            # Celtics
            {"team": "Boston Celtics", "situations": {
                "home_favorite": (28, 5, 0, 22, 11, 0, 15, 18, 8.5, 222.1),
                "road_favorite": (18, 8, 0, 15, 11, 0, 14, 12, 4.2, 218.5),
                "after_loss": (8, 4, 0, 7, 5, 0, 6, 6, 5.0, 220.0),
                "back_to_back": (10, 5, 0, 8, 7, 0, 9, 6, 2.5, 215.8),
            }},
        ],
        "mlb": [
            # Dodgers
            {"team": "Los Angeles Dodgers", "situations": {
                "home_favorite": (45, 20, 0, 38, 27, 0, 32, 33, 2.1, 8.8),
                "road_favorite": (35, 22, 0, 30, 27, 0, 28, 29, 1.5, 8.5),
                "after_win": (55, 30, 0, 45, 40, 0, 42, 43, 2.0, 9.0),
                "day_game": (25, 15, 0, 22, 18, 0, 20, 20, 1.8, 8.2),
            }},
            # Yankees
            {"team": "New York Yankees", "situations": {
                "home_favorite": (42, 18, 0, 35, 25, 0, 30, 30, 2.5, 9.2),
                "road_underdog": (15, 20, 0, 16, 19, 0, 18, 17, -1.2, 8.0),
                "after_loss": (30, 25, 0, 28, 27, 0, 26, 29, 0.5, 8.5),
                "night_game": (50, 30, 0, 42, 38, 0, 40, 40, 1.8, 9.0),
            }},
        ]
    }

    if sport.lower() not in sample_data:
        return {"error": f"No sample data for sport: {sport}"}

    teams_seeded = 0
    trends_added = 0

    for team_data in sample_data[sport.lower()]:
        team_name = team_data["team"]
        for situation, stats in team_data["situations"].items():
            wins, losses, pushes, ats_wins, ats_losses, ats_pushes, overs, unders, avg_margin, avg_total = stats

            total_games = wins + losses + pushes
            ats_total = ats_wins + ats_losses

            trend = SituationalTrend(
                sport=sport.lower(),
                team_name=team_name,
                situation_type=situation,
                situation_description=get_situation_display_name(situation),
                season="2024",
                wins=wins,
                losses=losses,
                pushes=pushes,
                ats_wins=ats_wins,
                ats_losses=ats_losses,
                ats_pushes=ats_pushes,
                over_wins=overs,
                under_wins=unders,
                avg_margin=avg_margin,
                avg_total=avg_total,
                cover_percentage=round(ats_wins / ats_total * 100, 1) if ats_total > 0 else 0
            )
            db.add(trend)
            trends_added += 1

        teams_seeded += 1

    db.commit()

    return {
        "success": True,
        "sport": sport,
        "teams_seeded": teams_seeded,
        "trends_added": trends_added
    }


def get_all_situations() -> List[Dict[str, str]]:
    """Get list of all supported situation types"""
    return [{"value": k, "label": v} for k, v in SITUATION_TYPES.items()]
