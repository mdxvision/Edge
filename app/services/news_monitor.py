"""
News Monitoring Service

Monitors breaking news that affects betting lines:
- Injury updates
- Lineup changes
- Weather changes
- Coach/player comments
"""

import json
import random
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.db import NewsItem


# Mock news sources
NEWS_SOURCES = ["ESPN", "Bleacher Report", "The Athletic", "Yahoo Sports", "CBS Sports", "NFL Network", "NBA.com"]

# Impact templates by type
INJURY_TEMPLATES = [
    {"headline": "{player} ruled OUT for {team} vs {opponent}", "impact": "HIGH", "line_impact": "+3.0 points to opponent"},
    {"headline": "{player} questionable with {injury} for {team}", "impact": "MEDIUM", "line_impact": "+1.5 points to opponent"},
    {"headline": "{player} upgraded to probable for {team}", "impact": "LOW", "line_impact": "-0.5 points to opponent"},
    {"headline": "{player} (knee) returns to practice for {team}", "impact": "MEDIUM", "line_impact": "-1.0 points to opponent"},
    {"headline": "{player} placed on IR by {team}", "impact": "HIGH", "line_impact": "+2.5 points to opponent"},
]

LINEUP_TEMPLATES = [
    {"headline": "{player} to start at {position} for {team}", "impact": "MEDIUM", "line_impact": "TBD"},
    {"headline": "{team} announces starting lineup changes for {opponent} game", "impact": "MEDIUM", "line_impact": "TBD"},
    {"headline": "{player} benched by {team} for disciplinary reasons", "impact": "HIGH", "line_impact": "+2.0 points to opponent"},
]

WEATHER_TEMPLATES = [
    {"headline": "Heavy snow expected for {team} vs {opponent} game", "impact": "HIGH", "line_impact": "UNDER 38"},
    {"headline": "Strong winds (25+ mph) forecast for {team} outdoor game", "impact": "MEDIUM", "line_impact": "UNDER favored"},
    {"headline": "Retractable roof to remain CLOSED for {team} game", "impact": "LOW", "line_impact": "Neutral"},
]

# Star players by team
STAR_PLAYERS = {
    "Chiefs": ["Patrick Mahomes", "Travis Kelce", "Chris Jones"],
    "Bills": ["Josh Allen", "Stefon Diggs", "Von Miller"],
    "Eagles": ["Jalen Hurts", "A.J. Brown", "DeVonta Smith"],
    "Cowboys": ["Dak Prescott", "CeeDee Lamb", "Micah Parsons"],
    "49ers": ["Brock Purdy", "Christian McCaffrey", "Nick Bosa"],
    "Lakers": ["LeBron James", "Anthony Davis", "Austin Reaves"],
    "Celtics": ["Jayson Tatum", "Jaylen Brown", "Kristaps Porzingis"],
    "Warriors": ["Stephen Curry", "Klay Thompson", "Draymond Green"],
    "Nuggets": ["Nikola Jokic", "Jamal Murray", "Michael Porter Jr."],
    "Bucks": ["Giannis Antetokounmpo", "Damian Lillard", "Khris Middleton"],
    "Yankees": ["Aaron Judge", "Juan Soto", "Gerrit Cole"],
    "Dodgers": ["Mookie Betts", "Freddie Freeman", "Shohei Ohtani"],
}

INJURIES = ["ankle injury", "knee injury", "hamstring strain", "back tightness", "illness", "concussion protocol"]


async def get_breaking_news(
    sport: Optional[str] = None,
    hours: int = 6,
    db: Optional[Session] = None
) -> List[Dict[str, Any]]:
    """
    Get recent breaking news that could affect betting.

    In production, this would scrape ESPN, Twitter, etc.
    """
    # Check database for recent news
    if db:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        query = db.query(NewsItem).filter(
            NewsItem.published_at >= cutoff
        )
        if sport:
            query = query.filter(NewsItem.sport == sport)

        existing = query.order_by(NewsItem.published_at.desc()).limit(20).all()

        if existing:
            return [_format_news_item(item) for item in existing]

    # Generate mock news for demonstration
    return _generate_mock_news(sport, hours)


def _generate_mock_news(sport: Optional[str], hours: int) -> List[Dict[str, Any]]:
    """Generate realistic mock news items."""
    news_items = []

    teams_by_sport = {
        "NFL": ["Chiefs", "Bills", "Eagles", "Cowboys", "49ers", "Ravens", "Lions", "Dolphins"],
        "NBA": ["Lakers", "Celtics", "Warriors", "Nuggets", "Bucks", "Heat", "Suns", "Thunder"],
        "MLB": ["Yankees", "Dodgers", "Braves", "Astros", "Phillies", "Orioles", "Rangers", "Twins"],
    }

    sports_to_use = [sport] if sport else ["NFL", "NBA", "MLB"]

    for s in sports_to_use:
        teams = teams_by_sport.get(s, [])

        # Generate 2-4 news items per sport
        num_items = random.randint(2, 4)

        for _ in range(num_items):
            team = random.choice(teams)
            opponent = random.choice([t for t in teams if t != team])

            # Randomly select news type
            news_type = random.choice(["injury", "injury", "injury", "lineup", "weather"])

            if news_type == "injury":
                template = random.choice(INJURY_TEMPLATES)
                players = STAR_PLAYERS.get(team, ["Star Player"])
                player = random.choice(players)
                injury = random.choice(INJURIES)

                headline = template["headline"].format(
                    player=player,
                    team=team,
                    opponent=opponent,
                    injury=injury
                )
            elif news_type == "lineup":
                template = random.choice(LINEUP_TEMPLATES)
                players = STAR_PLAYERS.get(team, ["Star Player"])
                player = random.choice(players)

                headline = template["headline"].format(
                    player=player,
                    team=team,
                    opponent=opponent,
                    position="QB" if s == "NFL" else "PG"
                )
            else:
                template = random.choice(WEATHER_TEMPLATES)
                headline = template["headline"].format(
                    team=team,
                    opponent=opponent
                )

            # Random time in past hours
            minutes_ago = random.randint(5, hours * 60)
            published_at = datetime.utcnow() - timedelta(minutes=minutes_ago)

            news_items.append({
                "headline": headline,
                "source": random.choice(NEWS_SOURCES),
                "timestamp": published_at.isoformat(),
                "teams_affected": [team],
                "impact": template["impact"],
                "line_impact_estimate": template["line_impact"],
                "news_type": news_type,
                "sport": s,
                "is_breaking": minutes_ago < 30
            })

    # Sort by recency
    news_items.sort(key=lambda x: x["timestamp"], reverse=True)

    return news_items


async def get_injury_updates(
    team: str,
    db: Optional[Session] = None
) -> List[Dict[str, Any]]:
    """Get latest injury report for a team."""
    players = STAR_PLAYERS.get(team, ["Player 1", "Player 2", "Player 3"])

    injuries = []

    # Generate 1-3 injuries per team
    num_injuries = random.randint(1, 3)
    injured_players = random.sample(players, min(num_injuries, len(players)))

    statuses = ["OUT", "Questionable", "Doubtful", "Probable", "Day-to-Day"]

    for player in injured_players:
        injury = random.choice(INJURIES)
        status = random.choice(statuses)

        # Calculate impact based on status
        if status in ["OUT", "Doubtful"]:
            impact = "HIGH"
            line_impact = "+2.5 to opponent"
        elif status == "Questionable":
            impact = "MEDIUM"
            line_impact = "+1.0 to opponent"
        else:
            impact = "LOW"
            line_impact = "Minimal"

        injuries.append({
            "player": player,
            "team": team,
            "injury": injury,
            "status": status,
            "impact": impact,
            "line_impact_estimate": line_impact,
            "updated_at": datetime.utcnow().isoformat(),
            "practice_status": random.choice(["DNP", "Limited", "Full"])
        })

    return injuries


async def get_news_for_game(
    home_team: str,
    away_team: str,
    sport: str,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """Get all relevant news for a specific game."""
    home_injuries = await get_injury_updates(home_team, db)
    away_injuries = await get_injury_updates(away_team, db)

    # Get general news
    all_news = await get_breaking_news(sport, hours=24, db=db)

    # Filter for relevant teams
    game_news = [
        n for n in all_news
        if home_team in n.get("teams_affected", []) or
           away_team in n.get("teams_affected", [])
    ]

    # Calculate overall impact
    high_impact_count = sum(1 for n in game_news if n.get("impact") == "HIGH")
    high_impact_count += sum(1 for i in home_injuries if i.get("impact") == "HIGH")
    high_impact_count += sum(1 for i in away_injuries if i.get("impact") == "HIGH")

    return {
        "matchup": f"{away_team} @ {home_team}",
        "sport": sport,
        "home_team": {
            "name": home_team,
            "injuries": home_injuries,
            "injury_impact": _calculate_injury_impact(home_injuries)
        },
        "away_team": {
            "name": away_team,
            "injuries": away_injuries,
            "injury_impact": _calculate_injury_impact(away_injuries)
        },
        "recent_news": game_news,
        "news_count": len(game_news),
        "high_impact_news_count": high_impact_count,
        "overall_impact": "HIGH" if high_impact_count >= 2 else "MEDIUM" if high_impact_count == 1 else "LOW"
    }


def _calculate_injury_impact(injuries: List[Dict]) -> Dict[str, Any]:
    """Calculate combined impact of injuries."""
    if not injuries:
        return {"level": "NONE", "adjustment": 0.0}

    total_adjustment = 0.0

    for injury in injuries:
        status = injury.get("status", "")
        if status in ["OUT", "Doubtful"]:
            total_adjustment += 2.5
        elif status == "Questionable":
            total_adjustment += 1.0
        else:
            total_adjustment += 0.25

    if total_adjustment >= 5:
        level = "SEVERE"
    elif total_adjustment >= 3:
        level = "SIGNIFICANT"
    elif total_adjustment >= 1.5:
        level = "MODERATE"
    else:
        level = "MINOR"

    return {
        "level": level,
        "adjustment": round(total_adjustment, 1),
        "injured_count": len(injuries)
    }


async def store_news_item(
    db: Session,
    headline: str,
    source: str,
    sport: str,
    teams_affected: List[str],
    impact_level: str,
    news_type: str,
    url: Optional[str] = None,
    line_impact: Optional[str] = None
) -> NewsItem:
    """Store a news item in the database."""
    item = NewsItem(
        sport=sport,
        headline=headline,
        source=source,
        url=url,
        teams_affected=json.dumps(teams_affected),
        impact_level=impact_level,
        line_impact_estimate=line_impact,
        news_type=news_type,
        published_at=datetime.utcnow(),
        is_breaking=True
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return item


def _format_news_item(item: NewsItem) -> Dict[str, Any]:
    """Format a NewsItem for API response."""
    teams = []
    if item.teams_affected:
        try:
            teams = json.loads(item.teams_affected)
        except:
            teams = []

    return {
        "id": item.id,
        "headline": item.headline,
        "source": item.source,
        "url": item.url,
        "sport": item.sport,
        "teams_affected": teams,
        "impact": item.impact_level,
        "line_impact_estimate": item.line_impact_estimate,
        "news_type": item.news_type,
        "timestamp": item.published_at.isoformat() if item.published_at else None,
        "is_breaking": item.is_breaking
    }


async def get_high_impact_news(
    sport: Optional[str] = None,
    db: Optional[Session] = None
) -> List[Dict[str, Any]]:
    """Get only high-impact news that significantly affects lines."""
    all_news = await get_breaking_news(sport, hours=12, db=db)

    return [n for n in all_news if n.get("impact") == "HIGH"]
