"""
Historical Head-to-Head (H2H) Data Service
Provides matchup history, trends, and statistics for team pairings
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import and_, or_, desc, func
from sqlalchemy.orm import Session

from app.db import HeadToHeadGame


def normalize_team_name(name: str) -> str:
    """Normalize team name for consistent matching"""
    return name.strip().lower().replace(".", "").replace("'", "")


def add_h2h_game(
    db: Session,
    sport: str,
    team1_name: str,
    team2_name: str,
    team1_score: int,
    team2_score: int,
    game_date: datetime,
    season: Optional[str] = None,
    spread: Optional[float] = None,
    total_line: Optional[float] = None,
    venue: Optional[str] = None,
    is_neutral_site: bool = False,
    is_playoff: bool = False,
    game_type: str = "regular"
) -> HeadToHeadGame:
    """Add a historical H2H game to the database"""

    # Determine spread result if spread provided
    spread_result = None
    if spread is not None:
        score_diff = team1_score - team2_score
        adjusted_diff = score_diff + spread
        if adjusted_diff > 0:
            spread_result = "team1_cover"
        elif adjusted_diff < 0:
            spread_result = "team2_cover"
        else:
            spread_result = "push"

    # Determine total result if total line provided
    total_result = None
    if total_line is not None:
        total_score = team1_score + team2_score
        if total_score > total_line:
            total_result = "over"
        elif total_score < total_line:
            total_result = "under"
        else:
            total_result = "push"

    game = HeadToHeadGame(
        sport=sport.lower(),
        team1_name=team1_name,
        team2_name=team2_name,
        team1_score=team1_score,
        team2_score=team2_score,
        game_date=game_date,
        season=season,
        spread=spread,
        spread_result=spread_result,
        total_line=total_line,
        total_result=total_result,
        venue=venue,
        is_neutral_site=is_neutral_site,
        is_playoff=is_playoff,
        game_type=game_type
    )

    db.add(game)
    db.commit()
    db.refresh(game)
    return game


def get_h2h_games(
    db: Session,
    sport: str,
    team1: str,
    team2: str,
    limit: int = 20,
    include_playoffs: bool = True,
    seasons: Optional[List[str]] = None
) -> List[HeadToHeadGame]:
    """Get historical games between two teams"""

    team1_normalized = normalize_team_name(team1)
    team2_normalized = normalize_team_name(team2)

    query = db.query(HeadToHeadGame).filter(
        HeadToHeadGame.sport == sport.lower(),
        or_(
            and_(
                func.lower(HeadToHeadGame.team1_name).contains(team1_normalized),
                func.lower(HeadToHeadGame.team2_name).contains(team2_normalized)
            ),
            and_(
                func.lower(HeadToHeadGame.team1_name).contains(team2_normalized),
                func.lower(HeadToHeadGame.team2_name).contains(team1_normalized)
            )
        )
    )

    if not include_playoffs:
        query = query.filter(HeadToHeadGame.is_playoff == False)

    if seasons:
        query = query.filter(HeadToHeadGame.season.in_(seasons))

    return query.order_by(desc(HeadToHeadGame.game_date)).limit(limit).all()


def calculate_h2h_stats(
    db: Session,
    sport: str,
    team1: str,
    team2: str,
    limit: int = 20
) -> Dict[str, Any]:
    """Calculate comprehensive H2H statistics between two teams"""

    games = get_h2h_games(db, sport, team1, team2, limit)

    if not games:
        return {
            "team1": team1,
            "team2": team2,
            "total_games": 0,
            "message": "No head-to-head history found"
        }

    team1_normalized = normalize_team_name(team1)

    stats = {
        "team1": team1,
        "team2": team2,
        "total_games": len(games),
        "team1_wins": 0,
        "team2_wins": 0,
        "ties": 0,
        "team1_ats_wins": 0,
        "team2_ats_wins": 0,
        "ats_pushes": 0,
        "overs": 0,
        "unders": 0,
        "ou_pushes": 0,
        "team1_avg_score": 0.0,
        "team2_avg_score": 0.0,
        "avg_total": 0.0,
        "avg_margin": 0.0,
        "last_5": [],
        "recent_trend": "",
        "ats_trend": "",
        "ou_trend": "",
        "home_away_split": {
            "team1_home_record": {"wins": 0, "losses": 0},
            "team2_home_record": {"wins": 0, "losses": 0}
        },
        "scoring_trends": {
            "highest_combined": 0,
            "lowest_combined": float("inf"),
            "blowouts": 0,  # margin > 14
            "close_games": 0  # margin <= 7
        }
    }

    team1_scores = []
    team2_scores = []
    margins = []

    for game in games:
        # Determine which team is "team1" in this game
        game_team1_is_our_team1 = team1_normalized in normalize_team_name(game.team1_name)

        if game_team1_is_our_team1:
            t1_score = game.team1_score
            t2_score = game.team2_score
            spread_result = game.spread_result
        else:
            t1_score = game.team2_score
            t2_score = game.team1_score
            # Flip the spread result
            if game.spread_result == "team1_cover":
                spread_result = "team2_cover"
            elif game.spread_result == "team2_cover":
                spread_result = "team1_cover"
            else:
                spread_result = game.spread_result

        team1_scores.append(t1_score)
        team2_scores.append(t2_score)
        margin = t1_score - t2_score
        margins.append(margin)

        # Win/Loss
        if t1_score > t2_score:
            stats["team1_wins"] += 1
        elif t2_score > t1_score:
            stats["team2_wins"] += 1
        else:
            stats["ties"] += 1

        # ATS
        if spread_result == "team1_cover":
            stats["team1_ats_wins"] += 1
        elif spread_result == "team2_cover":
            stats["team2_ats_wins"] += 1
        elif spread_result == "push":
            stats["ats_pushes"] += 1

        # Over/Under
        if game.total_result == "over":
            stats["overs"] += 1
        elif game.total_result == "under":
            stats["unders"] += 1
        elif game.total_result == "push":
            stats["ou_pushes"] += 1

        # Combined scoring
        combined = t1_score + t2_score
        stats["scoring_trends"]["highest_combined"] = max(
            stats["scoring_trends"]["highest_combined"], combined
        )
        stats["scoring_trends"]["lowest_combined"] = min(
            stats["scoring_trends"]["lowest_combined"], combined
        )

        # Margin analysis
        abs_margin = abs(margin)
        if abs_margin > 14:
            stats["scoring_trends"]["blowouts"] += 1
        elif abs_margin <= 7:
            stats["scoring_trends"]["close_games"] += 1

        # Home/Away tracking
        if not game.is_neutral_site:
            if game_team1_is_our_team1:
                # Team1 was the home team (listed first)
                if t1_score > t2_score:
                    stats["home_away_split"]["team1_home_record"]["wins"] += 1
                else:
                    stats["home_away_split"]["team1_home_record"]["losses"] += 1
            else:
                # Team2 was the home team
                if t2_score > t1_score:
                    stats["home_away_split"]["team2_home_record"]["wins"] += 1
                else:
                    stats["home_away_split"]["team2_home_record"]["losses"] += 1

    # Calculate averages
    stats["team1_avg_score"] = round(sum(team1_scores) / len(team1_scores), 1)
    stats["team2_avg_score"] = round(sum(team2_scores) / len(team2_scores), 1)
    stats["avg_total"] = round(stats["team1_avg_score"] + stats["team2_avg_score"], 1)
    stats["avg_margin"] = round(sum(margins) / len(margins), 1)

    # Handle edge case for lowest_combined
    if stats["scoring_trends"]["lowest_combined"] == float("inf"):
        stats["scoring_trends"]["lowest_combined"] = 0

    # Last 5 games summary
    for i, game in enumerate(games[:5]):
        game_team1_is_our_team1 = team1_normalized in normalize_team_name(game.team1_name)
        if game_team1_is_our_team1:
            winner = team1 if game.team1_score > game.team2_score else team2
            score = f"{game.team1_score}-{game.team2_score}"
        else:
            winner = team1 if game.team2_score > game.team1_score else team2
            score = f"{game.team2_score}-{game.team1_score}"

        stats["last_5"].append({
            "date": game.game_date.strftime("%Y-%m-%d"),
            "winner": winner,
            "score": score,
            "is_playoff": game.is_playoff
        })

    # Determine trends
    if stats["team1_wins"] > stats["team2_wins"]:
        lead = stats["team1_wins"] - stats["team2_wins"]
        stats["recent_trend"] = f"{team1} leads series {stats['team1_wins']}-{stats['team2_wins']}"
    elif stats["team2_wins"] > stats["team1_wins"]:
        stats["recent_trend"] = f"{team2} leads series {stats['team2_wins']}-{stats['team1_wins']}"
    else:
        stats["recent_trend"] = f"Series tied {stats['team1_wins']}-{stats['team2_wins']}"

    # ATS trend
    ats_total = stats["team1_ats_wins"] + stats["team2_ats_wins"]
    if ats_total > 0:
        if stats["team1_ats_wins"] > stats["team2_ats_wins"]:
            pct = round(stats["team1_ats_wins"] / ats_total * 100)
            stats["ats_trend"] = f"{team1} covers {pct}% of matchups"
        else:
            pct = round(stats["team2_ats_wins"] / ats_total * 100)
            stats["ats_trend"] = f"{team2} covers {pct}% of matchups"

    # O/U trend
    ou_total = stats["overs"] + stats["unders"]
    if ou_total > 0:
        over_pct = round(stats["overs"] / ou_total * 100)
        if over_pct >= 60:
            stats["ou_trend"] = f"OVER hits {over_pct}% ({stats['overs']}-{stats['unders']})"
        elif over_pct <= 40:
            stats["ou_trend"] = f"UNDER hits {100 - over_pct}% ({stats['unders']}-{stats['overs']})"
        else:
            stats["ou_trend"] = f"O/U split {stats['overs']}-{stats['unders']}"

    # Calculate win percentages
    total_decided = stats["team1_wins"] + stats["team2_wins"]
    if total_decided > 0:
        stats["team1_win_pct"] = round(stats["team1_wins"] / total_decided * 100, 1)
        stats["team2_win_pct"] = round(stats["team2_wins"] / total_decided * 100, 1)
    else:
        stats["team1_win_pct"] = 0
        stats["team2_win_pct"] = 0

    return stats


def get_h2h_summary(
    db: Session,
    sport: str,
    team1: str,
    team2: str,
    limit: int = 10
) -> Dict[str, Any]:
    """Get a compact H2H summary suitable for game cards"""

    stats = calculate_h2h_stats(db, sport, team1, team2, limit)

    if stats.get("total_games", 0) == 0:
        return {
            "has_history": False,
            "message": "No H2H history"
        }

    return {
        "has_history": True,
        "games_played": stats["total_games"],
        "series_record": f"{stats['team1_wins']}-{stats['team2_wins']}",
        "team1_win_pct": stats.get("team1_win_pct", 0),
        "avg_total": stats["avg_total"],
        "trend": stats["recent_trend"],
        "ats_trend": stats.get("ats_trend", ""),
        "ou_trend": stats.get("ou_trend", ""),
        "last_meeting": stats["last_5"][0] if stats["last_5"] else None
    }


def seed_h2h_data(db: Session, sport: str) -> Dict[str, Any]:
    """Seed sample H2H data for demonstration"""

    # Sample matchups by sport
    sample_data = {
        "nfl": [
            # Chiefs vs Raiders rivalry
            {"team1": "Kansas City Chiefs", "team2": "Las Vegas Raiders", "games": [
                {"t1": 27, "t2": 20, "date": "2024-12-25", "spread": -7.5, "total": 47.5},
                {"t1": 17, "t2": 14, "date": "2024-10-27", "spread": -3.5, "total": 44.5},
                {"t1": 31, "t2": 17, "date": "2024-01-07", "spread": -10, "total": 49.5},
                {"t1": 14, "t2": 20, "date": "2023-12-25", "spread": -6.5, "total": 45},
                {"t1": 30, "t2": 29, "date": "2023-10-07", "spread": -3, "total": 48.5},
            ]},
            # Cowboys vs Eagles rivalry
            {"team1": "Dallas Cowboys", "team2": "Philadelphia Eagles", "games": [
                {"t1": 20, "t2": 34, "date": "2024-11-10", "spread": 3, "total": 45.5},
                {"t1": 33, "t2": 13, "date": "2024-09-29", "spread": -3, "total": 46},
                {"t1": 17, "t2": 28, "date": "2023-12-10", "spread": 3.5, "total": 44.5},
                {"t1": 10, "t2": 28, "date": "2023-11-05", "spread": 7, "total": 47},
                {"t1": 27, "t2": 17, "date": "2023-01-14", "spread": -2.5, "total": 44},
            ]},
            # 49ers vs Seahawks rivalry
            {"team1": "San Francisco 49ers", "team2": "Seattle Seahawks", "games": [
                {"t1": 36, "t2": 24, "date": "2024-11-17", "spread": -6.5, "total": 49},
                {"t1": 28, "t2": 21, "date": "2024-10-10", "spread": -3.5, "total": 48.5},
                {"t1": 31, "t2": 13, "date": "2024-01-14", "spread": -10, "total": 47},
                {"t1": 42, "t2": 19, "date": "2023-11-23", "spread": -7, "total": 46.5},
                {"t1": 30, "t2": 23, "date": "2023-09-17", "spread": -4, "total": 45},
            ]},
        ],
        "nba": [
            # Lakers vs Celtics rivalry
            {"team1": "Los Angeles Lakers", "team2": "Boston Celtics", "games": [
                {"t1": 117, "t2": 96, "date": "2024-12-15", "spread": 6, "total": 220.5},
                {"t1": 114, "t2": 105, "date": "2024-02-01", "spread": 5.5, "total": 228},
                {"t1": 106, "t2": 122, "date": "2023-12-23", "spread": 7, "total": 226.5},
                {"t1": 118, "t2": 100, "date": "2023-01-28", "spread": 4.5, "total": 224},
                {"t1": 130, "t2": 108, "date": "2022-12-13", "spread": 2.5, "total": 222.5},
            ]},
            # Warriors vs Cavaliers
            {"team1": "Golden State Warriors", "team2": "Cleveland Cavaliers", "games": [
                {"t1": 120, "t2": 118, "date": "2024-11-05", "spread": -1.5, "total": 232.5},
                {"t1": 106, "t2": 112, "date": "2024-01-20", "spread": 3, "total": 229},
                {"t1": 129, "t2": 118, "date": "2023-11-11", "spread": -3, "total": 231},
                {"t1": 111, "t2": 104, "date": "2023-01-09", "spread": -5.5, "total": 225.5},
            ]},
        ],
        "mlb": [
            # Yankees vs Red Sox rivalry
            {"team1": "New York Yankees", "team2": "Boston Red Sox", "games": [
                {"t1": 5, "t2": 3, "date": "2024-09-15", "spread": -1.5, "total": 9.5},
                {"t1": 8, "t2": 2, "date": "2024-08-03", "spread": -1.5, "total": 8.5},
                {"t1": 3, "t2": 7, "date": "2024-07-07", "spread": -1.5, "total": 9},
                {"t1": 6, "t2": 1, "date": "2024-06-15", "spread": -1.5, "total": 8.5},
                {"t1": 2, "t2": 5, "date": "2024-05-20", "spread": -1.5, "total": 9},
                {"t1": 4, "t2": 4, "date": "2024-04-10", "spread": -1.5, "total": 8.5},
            ]},
            # Dodgers vs Giants rivalry
            {"team1": "Los Angeles Dodgers", "team2": "San Francisco Giants", "games": [
                {"t1": 7, "t2": 2, "date": "2024-09-20", "spread": -1.5, "total": 8},
                {"t1": 4, "t2": 5, "date": "2024-08-15", "spread": -1.5, "total": 8.5},
                {"t1": 10, "t2": 3, "date": "2024-07-25", "spread": -1.5, "total": 9},
                {"t1": 6, "t2": 4, "date": "2024-06-10", "spread": -1.5, "total": 8.5},
                {"t1": 3, "t2": 1, "date": "2024-05-05", "spread": -1.5, "total": 7.5},
            ]},
        ]
    }

    if sport.lower() not in sample_data:
        return {"error": f"No sample data for sport: {sport}"}

    games_added = 0
    matchups_seeded = []

    for matchup in sample_data[sport.lower()]:
        team1 = matchup["team1"]
        team2 = matchup["team2"]

        for game in matchup["games"]:
            add_h2h_game(
                db=db,
                sport=sport,
                team1_name=team1,
                team2_name=team2,
                team1_score=game["t1"],
                team2_score=game["t2"],
                game_date=datetime.strptime(game["date"], "%Y-%m-%d"),
                season="2024",
                spread=game.get("spread"),
                total_line=game.get("total"),
                is_playoff=game.get("playoff", False),
                game_type="regular"
            )
            games_added += 1

        matchups_seeded.append(f"{team1} vs {team2}")

    return {
        "success": True,
        "sport": sport,
        "games_added": games_added,
        "matchups": matchups_seeded
    }


def get_rivalry_rankings(
    db: Session,
    sport: str,
    min_games: int = 3
) -> List[Dict[str, Any]]:
    """Get rankings of rivalries by competitiveness"""

    # Get all unique matchups
    games = db.query(HeadToHeadGame).filter(
        HeadToHeadGame.sport == sport.lower()
    ).all()

    if not games:
        return []

    # Group games by matchup
    matchups = {}
    for game in games:
        key = tuple(sorted([game.team1_name, game.team2_name]))
        if key not in matchups:
            matchups[key] = []
        matchups[key].append(game)

    # Calculate competitiveness for each matchup
    rankings = []
    for (team1, team2), games in matchups.items():
        if len(games) < min_games:
            continue

        team1_wins = 0
        team2_wins = 0
        close_games = 0
        total_margin = 0

        for game in games:
            if game.team1_name == team1:
                if game.team1_score > game.team2_score:
                    team1_wins += 1
                else:
                    team2_wins += 1
                margin = abs(game.team1_score - game.team2_score)
            else:
                if game.team2_score > game.team1_score:
                    team1_wins += 1
                else:
                    team2_wins += 1
                margin = abs(game.team2_score - game.team1_score)

            total_margin += margin
            if margin <= 7:
                close_games += 1

        # Competitiveness score based on:
        # - Balance of series (50-50 is most competitive)
        # - Percentage of close games
        # - Number of games played
        balance = 1 - abs(team1_wins - team2_wins) / len(games)
        close_pct = close_games / len(games)
        avg_margin = total_margin / len(games)

        competitiveness = round((balance * 50) + (close_pct * 30) + min(20, len(games) * 2), 1)

        rankings.append({
            "team1": team1,
            "team2": team2,
            "games_played": len(games),
            "record": f"{team1_wins}-{team2_wins}",
            "close_games": close_games,
            "avg_margin": round(avg_margin, 1),
            "competitiveness_score": competitiveness
        })

    # Sort by competitiveness
    rankings.sort(key=lambda x: x["competitiveness_score"], reverse=True)
    return rankings


def get_recent_h2h_trends(
    db: Session,
    sport: str,
    team: str,
    limit: int = 5
) -> Dict[str, Any]:
    """Get recent H2H trends for a specific team against all opponents"""

    team_normalized = normalize_team_name(team)

    # Get recent games involving this team
    games = db.query(HeadToHeadGame).filter(
        HeadToHeadGame.sport == sport.lower(),
        or_(
            func.lower(HeadToHeadGame.team1_name).contains(team_normalized),
            func.lower(HeadToHeadGame.team2_name).contains(team_normalized)
        )
    ).order_by(desc(HeadToHeadGame.game_date)).limit(limit * 3).all()

    # Group by opponent
    opponents = {}
    for game in games:
        is_team1 = team_normalized in normalize_team_name(game.team1_name)
        opponent = game.team2_name if is_team1 else game.team1_name

        if opponent not in opponents:
            opponents[opponent] = []

        opponents[opponent].append({
            "date": game.game_date.strftime("%Y-%m-%d"),
            "score": f"{game.team1_score}-{game.team2_score}" if is_team1 else f"{game.team2_score}-{game.team1_score}",
            "won": (game.team1_score > game.team2_score) if is_team1 else (game.team2_score > game.team1_score)
        })

    return {
        "team": team,
        "sport": sport,
        "h2h_by_opponent": opponents
    }
