from typing import Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import hashlib
import hmac
import secrets
import os

from app.db import User, UserSession, Client
from app.config import SESSION_SECRET, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
from app.utils.logging import get_logger

logger = get_logger(__name__)


def hash_password(password: str) -> str:
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + key.hex()


def verify_password(stored_hash: str, password: str) -> bool:
    salt = bytes.fromhex(stored_hash[:64])
    stored_key = stored_hash[64:]
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return key.hex() == stored_key


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hmac.new(
        SESSION_SECRET.encode('utf-8'),
        token.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def verify_token_hash(token: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_token(token), stored_hash)


def create_user(
    db: Session,
    email: str,
    username: str,
    password: str,
    initial_bankroll: float = 10000.0,
    risk_profile: str = "balanced"
) -> User:
    logger.info(f"Creating new user: {username} ({email})")

    existing_email = db.query(User).filter(User.email == email).first()
    if existing_email:
        logger.warning(f"Registration failed: email already exists - {email}")
        raise ValueError("Email already registered")

    existing_username = db.query(User).filter(User.username == username).first()
    if existing_username:
        logger.warning(f"Registration failed: username already taken - {username}")
        raise ValueError("Username already taken")

    client = Client(
        name=username,
        bankroll=initial_bankroll,
        risk_profile=risk_profile
    )
    db.add(client)
    db.flush()

    user = User(
        email=email,
        username=username,
        password_hash=hash_password(password),
        client_id=client.id,
        is_active=True,
        is_verified=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(f"User created successfully: {username} (id={user.id}, client_id={client.id})")
    return user


def authenticate_user(
    db: Session,
    email_or_username: str,
    password: str
) -> Optional[User]:
    logger.debug(f"Authentication attempt for: {email_or_username}")

    user = db.query(User).filter(
        (User.email == email_or_username) | (User.username == email_or_username)
    ).first()

    if not user:
        logger.warning(f"Auth failed: user not found - {email_or_username}")
        return None

    if not user.is_active:
        logger.warning(f"Auth failed: user inactive - {email_or_username} (id={user.id})")
        return None

    if not verify_password(user.password_hash, password):
        logger.warning(f"Auth failed: invalid password - {email_or_username} (id={user.id})")
        return None

    user.last_login = datetime.utcnow()
    db.commit()

    logger.info(f"Auth successful: {user.username} (id={user.id})")
    return user


def create_session(
    db: Session,
    user: User,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> Tuple[str, str, datetime]:
    logger.debug(f"Creating session for user {user.username} (id={user.id}) from {ip_address}")

    session_token = generate_token()
    refresh_token = generate_token()
    expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    session = UserSession(
        user_id=user.id,
        session_token=hash_token(session_token),
        refresh_token=hash_token(refresh_token),
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=expires_at,
        is_valid=True
    )
    db.add(session)
    db.commit()

    logger.info(f"Session created for {user.username}, expires at {expires_at}")
    return session_token, refresh_token, expires_at


def validate_session(db: Session, session_token: str) -> Optional[User]:
    token_hash = hash_token(session_token)
    session = db.query(UserSession).filter(
        UserSession.session_token == token_hash,
        UserSession.is_valid == True,
        UserSession.expires_at > datetime.utcnow()
    ).first()

    if not session:
        logger.debug("Session validation failed: token not found or expired")
        return None

    user = db.query(User).filter(User.id == session.user_id).first()
    if user and user.is_active:
        logger.debug(f"Session valid for user {user.username} (id={user.id})")
        return user

    logger.warning(f"Session validation failed: user inactive or not found (user_id={session.user_id})")
    return None


def refresh_session(
    db: Session,
    refresh_token: str
) -> Optional[Tuple[str, str, datetime]]:
    token_hash = hash_token(refresh_token)
    session = db.query(UserSession).filter(
        UserSession.refresh_token == token_hash,
        UserSession.is_valid == True
    ).first()
    
    if not session:
        return None
    
    refresh_expires = session.created_at + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    if datetime.utcnow() > refresh_expires:
        session.is_valid = False
        db.commit()
        return None
    
    new_session_token = generate_token()
    new_refresh_token = generate_token()
    
    session.session_token = hash_token(new_session_token)
    session.refresh_token = hash_token(new_refresh_token)
    session.expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    db.commit()
    
    return new_session_token, new_refresh_token, session.expires_at


def invalidate_session(db: Session, session_token: str) -> bool:
    token_hash = hash_token(session_token)
    session = db.query(UserSession).filter(
        UserSession.session_token == token_hash
    ).first()
    
    if not session:
        return False
    
    session.is_valid = False
    db.commit()
    return True


def invalidate_all_sessions(db: Session, user_id: int) -> int:
    count = db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.is_valid == True
    ).update({"is_valid": False})
    db.commit()
    return count


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def update_password(db: Session, user: User, new_password: str) -> bool:
    invalidate_all_sessions(db, user.id)
    
    user.password_hash = hash_password(new_password)
    user.updated_at = datetime.utcnow()
    db.commit()
    return True


def delete_user(db: Session, user: User) -> bool:
    invalidate_all_sessions(db, user.id)
    
    user.is_active = False
    user.email = f"deleted_{user.id}_{user.email}"
    user.updated_at = datetime.utcnow()
    db.commit()
    return True
