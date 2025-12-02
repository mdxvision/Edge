from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.db import UserAlert, User, BetRecommendation


def create_alert(
    db: Session,
    user_id: int,
    name: str,
    alert_type: str,
    sport: Optional[str] = None,
    team_id: Optional[int] = None,
    min_edge: Optional[float] = None,
    max_odds: Optional[int] = None,
    min_odds: Optional[int] = None,
    notify_email: bool = False,
    notify_push: bool = True,
    notify_telegram: bool = False
) -> UserAlert:
    alert = UserAlert(
        user_id=user_id,
        name=name,
        alert_type=alert_type,
        sport=sport,
        team_id=team_id,
        min_edge=min_edge,
        max_odds=max_odds,
        min_odds=min_odds,
        notify_email=notify_email,
        notify_push=notify_push,
        notify_telegram=notify_telegram
    )
    
    db.add(alert)
    db.commit()
    db.refresh(alert)
    
    return alert


def get_user_alerts(db: Session, user_id: int) -> List[UserAlert]:
    return db.query(UserAlert).filter(
        UserAlert.user_id == user_id
    ).order_by(UserAlert.created_at.desc()).all()


def get_alert_by_id(db: Session, alert_id: int, user_id: int) -> Optional[UserAlert]:
    return db.query(UserAlert).filter(
        UserAlert.id == alert_id,
        UserAlert.user_id == user_id
    ).first()


def update_alert(
    db: Session,
    alert: UserAlert,
    updates: Dict[str, Any]
) -> UserAlert:
    for key, value in updates.items():
        if hasattr(alert, key):
            setattr(alert, key, value)
    
    alert.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(alert)
    
    return alert


def delete_alert(db: Session, alert: UserAlert) -> bool:
    db.delete(alert)
    db.commit()
    return True


def toggle_alert(db: Session, alert: UserAlert) -> UserAlert:
    alert.is_active = not alert.is_active
    alert.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(alert)
    return alert


def check_recommendation_matches_alert(
    alert: UserAlert,
    recommendation: BetRecommendation
) -> bool:
    if alert.sport and alert.sport != recommendation.sport:
        return False
    
    if alert.min_edge and recommendation.edge < alert.min_edge:
        return False
    
    if alert.min_odds and recommendation.line.american_odds < alert.min_odds:
        return False
    
    if alert.max_odds and recommendation.line.american_odds > alert.max_odds:
        return False
    
    return True


def get_matching_alerts(
    db: Session,
    recommendation: BetRecommendation
) -> List[UserAlert]:
    alerts = db.query(UserAlert).filter(
        UserAlert.is_active == True,
        UserAlert.alert_type == "recommendation"
    ).all()
    
    matching = []
    for alert in alerts:
        if check_recommendation_matches_alert(alert, recommendation):
            matching.append(alert)
    
    return matching


def trigger_alert(db: Session, alert: UserAlert) -> None:
    alert.last_triggered = datetime.utcnow()
    alert.trigger_count += 1
    db.commit()


ALERT_TYPES = {
    "recommendation": "New recommendation matching criteria",
    "high_edge": "High edge opportunity detected",
    "game_start": "Game starting soon",
    "result": "Bet result notification",
    "line_movement": "Significant line movement",
    "injury": "Key player injury update",
}


def get_alert_types() -> Dict[str, str]:
    return ALERT_TYPES
