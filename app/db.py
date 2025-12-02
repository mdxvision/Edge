from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from datetime import datetime
from app.config import DATABASE_URL

is_sqlite = DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine_options = {
    "pool_pre_ping": True,
}
if not is_sqlite:
    engine_options["pool_recycle"] = 300

engine = create_engine(DATABASE_URL, connect_args=connect_args, **engine_options)
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


class HistoricalGameResult(Base):
    __tablename__ = "historical_game_results"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=True)
    sport = Column(String(50), nullable=False, index=True)
    season = Column(String(20), nullable=False, index=True)
    game_date = Column(DateTime, nullable=False, index=True)
    
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    competitor1_id = Column(Integer, ForeignKey("competitors.id"), nullable=True)
    competitor2_id = Column(Integer, ForeignKey("competitors.id"), nullable=True)
    
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)
    competitor1_score = Column(Float, nullable=True)
    competitor2_score = Column(Float, nullable=True)
    
    winner = Column(String(20), nullable=True)
    margin = Column(Float, nullable=True)
    total_points = Column(Float, nullable=True)
    
    home_team_name = Column(String(200), nullable=True)
    away_team_name = Column(String(200), nullable=True)
    competitor1_name = Column(String(200), nullable=True)
    competitor2_name = Column(String(200), nullable=True)
    
    venue = Column(String(200), nullable=True)
    is_neutral_site = Column(Boolean, default=False)
    weather_condition = Column(String(100), nullable=True)
    temperature = Column(Float, nullable=True)
    
    closing_spread = Column(Float, nullable=True)
    closing_total = Column(Float, nullable=True)
    closing_home_ml = Column(Integer, nullable=True)
    closing_away_ml = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class ELORatingHistory(Base):
    __tablename__ = "elo_rating_history"
    
    id = Column(Integer, primary_key=True, index=True)
    sport = Column(String(50), nullable=False, index=True)
    entity_type = Column(String(20), nullable=False)
    entity_id = Column(Integer, nullable=False, index=True)
    entity_name = Column(String(200), nullable=False)
    
    rating = Column(Float, nullable=False)
    rating_change = Column(Float, nullable=True)
    game_id = Column(Integer, nullable=True)
    
    recorded_at = Column(DateTime, nullable=False, index=True)
    season = Column(String(20), nullable=True)
    
    games_played = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    draws = Column(Integer, default=0)


class PlayerStats(Base):
    __tablename__ = "player_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    sport = Column(String(50), nullable=False, index=True)
    season = Column(String(20), nullable=False, index=True)
    
    games_played = Column(Integer, default=0)
    minutes_per_game = Column(Float, nullable=True)
    
    points_per_game = Column(Float, nullable=True)
    rebounds_per_game = Column(Float, nullable=True)
    assists_per_game = Column(Float, nullable=True)
    
    passing_yards = Column(Float, nullable=True)
    rushing_yards = Column(Float, nullable=True)
    touchdowns = Column(Float, nullable=True)
    
    batting_average = Column(Float, nullable=True)
    home_runs = Column(Float, nullable=True)
    rbi = Column(Float, nullable=True)
    era = Column(Float, nullable=True)
    
    goals = Column(Float, nullable=True)
    assists_hockey = Column(Float, nullable=True)
    save_percentage = Column(Float, nullable=True)
    
    fantasy_points_avg = Column(Float, nullable=True)
    consistency_score = Column(Float, nullable=True)
    
    updated_at = Column(DateTime, default=datetime.utcnow)


class InjuryReport(Base):
    __tablename__ = "injury_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    sport = Column(String(50), nullable=False, index=True)
    
    injury_type = Column(String(100), nullable=False)
    body_part = Column(String(100), nullable=True)
    status = Column(String(50), nullable=False)
    
    reported_date = Column(DateTime, nullable=False)
    expected_return = Column(DateTime, nullable=True)
    
    impact_rating = Column(Float, nullable=True)
    
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    
    updated_at = Column(DateTime, default=datetime.utcnow)


class BacktestResult(Base):
    __tablename__ = "backtest_results"
    
    id = Column(Integer, primary_key=True, index=True)
    sport = Column(String(50), nullable=False, index=True)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), nullable=True)
    
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    
    total_predictions = Column(Integer, nullable=False)
    correct_predictions = Column(Integer, nullable=False)
    accuracy = Column(Float, nullable=False)
    
    total_bets = Column(Integer, nullable=True)
    winning_bets = Column(Integer, nullable=True)
    roi = Column(Float, nullable=True)
    
    avg_edge = Column(Float, nullable=True)
    avg_odds = Column(Float, nullable=True)
    
    brier_score = Column(Float, nullable=True)
    log_loss = Column(Float, nullable=True)
    calibration_error = Column(Float, nullable=True)
    
    sharpe_ratio = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    
    parameters = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class ModelPrediction(Base):
    __tablename__ = "model_predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    game_result_id = Column(Integer, ForeignKey("historical_game_results.id"), nullable=False)
    sport = Column(String(50), nullable=False, index=True)
    model_name = Column(String(100), nullable=False)
    
    home_win_prob = Column(Float, nullable=True)
    away_win_prob = Column(Float, nullable=True)
    draw_prob = Column(Float, nullable=True)
    
    predicted_winner = Column(String(20), nullable=True)
    predicted_margin = Column(Float, nullable=True)
    predicted_total = Column(Float, nullable=True)
    
    actual_winner = Column(String(20), nullable=True)
    was_correct = Column(Boolean, nullable=True)
    
    edge_on_home = Column(Float, nullable=True)
    edge_on_away = Column(Float, nullable=True)
    
    bet_placed = Column(Boolean, default=False)
    bet_selection = Column(String(50), nullable=True)
    bet_odds = Column(Integer, nullable=True)
    bet_result = Column(String(20), nullable=True)
    profit_loss = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class DFSContest(Base):
    __tablename__ = "dfs_contests"
    
    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False)
    sport = Column(String(50), nullable=False, index=True)
    contest_type = Column(String(50), nullable=False)
    name = Column(String(200), nullable=False)
    
    entry_fee = Column(Float, nullable=False)
    prize_pool = Column(Float, nullable=True)
    max_entries = Column(Integer, nullable=True)
    
    salary_cap = Column(Integer, nullable=False)
    roster_size = Column(Integer, nullable=False)
    roster_positions = Column(Text, nullable=False)
    
    start_time = Column(DateTime, nullable=False)
    lock_time = Column(DateTime, nullable=False)
    
    slate_id = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    lineups = relationship("DFSLineup", back_populates="contest")


class DFSPlayerSalary(Base):
    __tablename__ = "dfs_player_salaries"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    contest_id = Column(Integer, ForeignKey("dfs_contests.id"), nullable=True)
    
    platform = Column(String(50), nullable=False)
    sport = Column(String(50), nullable=False, index=True)
    slate_date = Column(DateTime, nullable=False, index=True)
    
    salary = Column(Integer, nullable=False)
    position = Column(String(20), nullable=False)
    positions_eligible = Column(String(100), nullable=True)
    
    game_id = Column(Integer, ForeignKey("games.id"), nullable=True)
    opponent_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    is_home = Column(Boolean, default=True)
    
    ownership_projection = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    player = relationship("Player")


class DFSProjection(Base):
    __tablename__ = "dfs_projections"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    salary_id = Column(Integer, ForeignKey("dfs_player_salaries.id"), nullable=True)
    
    sport = Column(String(50), nullable=False, index=True)
    platform = Column(String(50), nullable=False)
    slate_date = Column(DateTime, nullable=False, index=True)
    
    projected_points = Column(Float, nullable=False)
    floor = Column(Float, nullable=True)
    ceiling = Column(Float, nullable=True)
    std_dev = Column(Float, nullable=True)
    
    value_score = Column(Float, nullable=True)
    leverage_score = Column(Float, nullable=True)
    
    confidence = Column(Float, nullable=True)
    model_version = Column(String(50), nullable=True)
    
    stat_projections = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    player = relationship("Player")


class DFSLineup(Base):
    __tablename__ = "dfs_lineups"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    contest_id = Column(Integer, ForeignKey("dfs_contests.id"), nullable=True)
    
    sport = Column(String(50), nullable=False, index=True)
    platform = Column(String(50), nullable=False)
    slate_date = Column(DateTime, nullable=False)
    
    player_ids = Column(Text, nullable=False)
    positions = Column(Text, nullable=False)
    
    total_salary = Column(Integer, nullable=False)
    salary_remaining = Column(Integer, nullable=True)
    
    projected_points = Column(Float, nullable=False)
    projected_ownership = Column(Float, nullable=True)
    leverage_score = Column(Float, nullable=True)
    
    lineup_type = Column(String(50), default="balanced")
    optimization_notes = Column(Text, nullable=True)
    
    actual_points = Column(Float, nullable=True)
    finish_position = Column(Integer, nullable=True)
    winnings = Column(Float, nullable=True)
    
    is_submitted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    client = relationship("Client")
    contest = relationship("DFSContest", back_populates="lineups")


class DFSCorrelation(Base):
    __tablename__ = "dfs_correlations"
    
    id = Column(Integer, primary_key=True, index=True)
    sport = Column(String(50), nullable=False, index=True)
    
    position1 = Column(String(50), nullable=False)
    position2 = Column(String(50), nullable=False)
    
    correlation_type = Column(String(50), nullable=False)
    correlation_value = Column(Float, nullable=False)
    
    sample_size = Column(Integer, nullable=True)
    confidence_interval = Column(Float, nullable=True)
    
    is_same_team = Column(Boolean, default=True)
    is_same_game = Column(Boolean, default=True)
    
    notes = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    sessions = relationship("UserSession", back_populates="user")


class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    refresh_token = Column(String(255), unique=True, nullable=True)
    
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    expires_at = Column(DateTime, nullable=False)
    is_valid = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="sessions")


def init_db():
    Base.metadata.create_all(bind=engine)
