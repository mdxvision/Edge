from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from datetime import datetime
from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Team(Base):
    __tablename__ = "teams"
    
    id = Column(Integer, primary_key=True, index=True)
    sport = Column(String(50), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    short_name = Column(String(50), nullable=True)
    rating = Column(Float, default=1500.0)
    
    players = relationship("Player", back_populates="team")
    home_games = relationship("Game", foreign_keys="Game.home_team_id", back_populates="home_team")
    away_games = relationship("Game", foreign_keys="Game.away_team_id", back_populates="away_team")


class Competitor(Base):
    __tablename__ = "competitors"
    
    id = Column(Integer, primary_key=True, index=True)
    sport = Column(String(50), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    country = Column(String(100), nullable=True)
    rating = Column(Float, default=1500.0)
    
    games_as_competitor1 = relationship("Game", foreign_keys="Game.competitor1_id", back_populates="competitor1")
    games_as_competitor2 = relationship("Game", foreign_keys="Game.competitor2_id", back_populates="competitor2")


class Player(Base):
    __tablename__ = "players"
    
    id = Column(Integer, primary_key=True, index=True)
    sport = Column(String(50), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    name = Column(String(200), nullable=False)
    position = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    
    team = relationship("Team", back_populates="players")


class Game(Base):
    __tablename__ = "games"
    
    id = Column(Integer, primary_key=True, index=True)
    sport = Column(String(50), nullable=False, index=True)
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    competitor1_id = Column(Integer, ForeignKey("competitors.id"), nullable=True)
    competitor2_id = Column(Integer, ForeignKey("competitors.id"), nullable=True)
    start_time = Column(DateTime, nullable=False)
    venue = Column(String(200), nullable=True)
    league = Column(String(100), nullable=True)
    
    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_games")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_games")
    competitor1 = relationship("Competitor", foreign_keys=[competitor1_id], back_populates="games_as_competitor1")
    competitor2 = relationship("Competitor", foreign_keys=[competitor2_id], back_populates="games_as_competitor2")
    markets = relationship("Market", back_populates="game")


class Market(Base):
    __tablename__ = "markets"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    market_type = Column(String(50), nullable=False)
    description = Column(String(200), nullable=True)
    selection = Column(String(50), nullable=False)
    
    game = relationship("Game", back_populates="markets")
    lines = relationship("Line", back_populates="market")


class Line(Base):
    __tablename__ = "lines"
    
    id = Column(Integer, primary_key=True, index=True)
    market_id = Column(Integer, ForeignKey("markets.id"), nullable=False)
    sportsbook = Column(String(100), nullable=False)
    odds_type = Column(String(50), nullable=False)
    line_value = Column(Float, nullable=True)
    american_odds = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    market = relationship("Market", back_populates="lines")


class Client(Base):
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    bankroll = Column(Float, nullable=False, default=1000.0)
    risk_profile = Column(String(50), nullable=False, default="balanced")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    recommendations = relationship("BetRecommendation", back_populates="client")


class BetRecommendation(Base):
    __tablename__ = "bet_recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    line_id = Column(Integer, ForeignKey("lines.id"), nullable=False)
    sport = Column(String(50), nullable=False)
    suggested_stake = Column(Float, nullable=False)
    model_probability = Column(Float, nullable=False)
    implied_probability = Column(Float, nullable=False)
    edge = Column(Float, nullable=False)
    expected_value = Column(Float, nullable=False)
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    client = relationship("Client", back_populates="recommendations")
    line = relationship("Line")


def init_db():
    Base.metadata.create_all(bind=engine)
