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
    status = Column(String(50), default="scheduled")  # scheduled, in_progress, final, etc.
    current_score = Column(String(50), nullable=True)  # e.g. "105-98"
    external_id = Column(String(100), nullable=True, index=True)  # ID from external API (ESPN/NBA/etc)
    
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
    
    display_name = Column(String(100), nullable=True)
    
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_age_verified = Column(Boolean, default=False)
    date_of_birth = Column(DateTime, nullable=True)
    
    totp_secret = Column(String(64), nullable=True)
    totp_enabled = Column(Boolean, default=False)
    totp_verified_at = Column(DateTime, nullable=True)
    backup_codes = Column(Text, nullable=True)
    
    preferred_currency = Column(String(10), default="USD")

    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)

    # Stripe subscription fields
    stripe_customer_id = Column(String(255), nullable=True, index=True)
    subscription_tier = Column(String(20), default="free")  # free, premium, pro
    subscription_status = Column(String(20), default="inactive")  # active, past_due, canceled, inactive
    subscription_id = Column(String(255), nullable=True)
    subscription_expires = Column(DateTime, nullable=True)

    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sessions = relationship("UserSession", back_populates="user")
    alerts = relationship("UserAlert", back_populates="user")
    tracked_bets = relationship("TrackedBet", back_populates="user")
    api_keys = relationship("APIKey", back_populates="user")
    devices = relationship("UserDevice", back_populates="user")


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


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(Integer, nullable=True)
    
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    
    status = Column(String(20), default="success")
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class UserAlert(Base):
    __tablename__ = "user_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    name = Column(String(200), nullable=False)
    alert_type = Column(String(50), nullable=False)
    
    sport = Column(String(50), nullable=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    min_edge = Column(Float, nullable=True)
    max_odds = Column(Integer, nullable=True)
    min_odds = Column(Integer, nullable=True)
    
    notify_email = Column(Boolean, default=False)
    notify_push = Column(Boolean, default=True)
    notify_telegram = Column(Boolean, default=False)
    
    is_active = Column(Boolean, default=True)
    last_triggered = Column(DateTime, nullable=True)
    trigger_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="alerts")


class TrackedBet(Base):
    __tablename__ = "tracked_bets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recommendation_id = Column(Integer, ForeignKey("bet_recommendations.id"), nullable=True)

    sport = Column(String(50), nullable=False, index=True)
    bet_type = Column(String(50), nullable=False)
    selection = Column(String(200), nullable=False)

    odds = Column(Integer, nullable=False)
    stake = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")

    potential_profit = Column(Float, nullable=False)

    status = Column(String(20), default="pending", index=True)
    result = Column(String(20), nullable=True)
    profit_loss = Column(Float, nullable=True)

    # CLV tracking
    closing_odds = Column(Integer, nullable=True)
    clv_percentage = Column(Float, nullable=True)

    placed_at = Column(DateTime, default=datetime.utcnow)
    settled_at = Column(DateTime, nullable=True)

    sportsbook = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    game_id = Column(Integer, ForeignKey("games.id"), nullable=True)
    game_date = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="tracked_bets")
    recommendation = relationship("BetRecommendation")


class LeaderboardEntry(Base):
    __tablename__ = "leaderboard_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    
    display_name = Column(String(100), nullable=False)
    
    total_bets = Column(Integer, default=0)
    winning_bets = Column(Integer, default=0)
    total_profit = Column(Float, default=0.0)
    roi_percentage = Column(Float, default=0.0)
    
    current_streak = Column(Integer, default=0)
    best_streak = Column(Integer, default=0)
    
    rank = Column(Integer, nullable=True, index=True)
    previous_rank = Column(Integer, nullable=True)
    
    weekly_profit = Column(Float, default=0.0)
    monthly_profit = Column(Float, default=0.0)
    
    is_public = Column(Boolean, default=True)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Webhook(Base):
    __tablename__ = "webhooks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    name = Column(String(200), nullable=False)
    url = Column(String(500), nullable=False)
    secret = Column(String(255), nullable=True)
    
    events = Column(Text, nullable=False)
    
    is_active = Column(Boolean, default=True)
    last_triggered = Column(DateTime, nullable=True)
    last_status = Column(Integer, nullable=True)
    failure_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Parlay(Base):
    __tablename__ = "parlays"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    name = Column(String(200), nullable=True)
    
    leg_ids = Column(Text, nullable=False)
    leg_count = Column(Integer, nullable=False)
    
    combined_odds = Column(Integer, nullable=False)
    combined_probability = Column(Float, nullable=False)
    correlation_adjustment = Column(Float, default=1.0)
    adjusted_probability = Column(Float, nullable=False)
    
    suggested_stake = Column(Float, nullable=True)
    potential_profit = Column(Float, nullable=True)
    edge = Column(Float, nullable=True)
    
    status = Column(String(20), default="pending")
    result = Column(String(20), nullable=True)
    profit_loss = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    settled_at = Column(DateTime, nullable=True)


class CurrencyRate(Base):
    __tablename__ = "currency_rates"
    
    id = Column(Integer, primary_key=True, index=True)
    base_currency = Column(String(10), default="USD")
    target_currency = Column(String(10), nullable=False, index=True)
    rate = Column(Float, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    endpoint = Column(Text, nullable=False)
    p256dh_key = Column(String(255), nullable=False)
    auth_key = Column(String(255), nullable=False)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class TelegramUser(Base):
    __tablename__ = "telegram_users"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    
    telegram_chat_id = Column(String(100), nullable=False, unique=True)
    telegram_username = Column(String(100), nullable=True)
    
    is_active = Column(Boolean, default=True)
    notify_recommendations = Column(Boolean, default=True)
    notify_results = Column(Boolean, default=True)
    notify_alerts = Column(Boolean, default=True)
    
    linked_at = Column(DateTime, default=datetime.utcnow)


class OddsSnapshot(Base):
    __tablename__ = "odds_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    market_type = Column(String(50), nullable=False)
    
    sportsbook = Column(String(100), nullable=False)
    odds = Column(Integer, nullable=False)
    line_value = Column(Float, nullable=True)
    
    captured_at = Column(DateTime, default=datetime.utcnow, index=True)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    token_hash = Column(String(255), nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)


class TelegramLinkCode(Base):
    __tablename__ = "telegram_link_codes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    code = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)


class LineMovement(Base):
    __tablename__ = "line_movements"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    market_type = Column(String(50), nullable=False)
    sportsbook = Column(String(100), nullable=False)

    previous_odds = Column(Integer, nullable=True)
    current_odds = Column(Integer, nullable=False)
    previous_line = Column(Float, nullable=True)
    current_line = Column(Float, nullable=True)

    movement_percentage = Column(Float, nullable=True)
    direction = Column(String(20), nullable=True)  # 'steam', 'reverse', 'sharp', 'public'

    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)


class BankrollHistory(Base):
    __tablename__ = "bankroll_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    bankroll_value = Column(Float, nullable=False)
    change_amount = Column(Float, nullable=True)
    change_reason = Column(String(50), nullable=True)  # 'bet_won', 'bet_lost', 'deposit', 'withdrawal'
    bet_id = Column(Integer, ForeignKey("tracked_bets.id"), nullable=True)

    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)


# MLB-specific models
class MLBTeamStats(Base):
    __tablename__ = "mlb_team_stats"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    mlb_team_id = Column(Integer, nullable=True)  # External MLB API ID
    season = Column(Integer, nullable=False, index=True)

    # Batting stats
    games_played = Column(Integer, default=0)
    at_bats = Column(Integer, default=0)
    runs = Column(Integer, default=0)
    hits = Column(Integer, default=0)
    doubles = Column(Integer, default=0)
    triples = Column(Integer, default=0)
    home_runs = Column(Integer, default=0)
    rbi = Column(Integer, default=0)
    stolen_bases = Column(Integer, default=0)
    walks = Column(Integer, default=0)
    strikeouts = Column(Integer, default=0)
    batting_avg = Column(Float, nullable=True)
    obp = Column(Float, nullable=True)
    slg = Column(Float, nullable=True)
    ops = Column(Float, nullable=True)

    # Pitching stats
    pitching_wins = Column(Integer, default=0)
    pitching_losses = Column(Integer, default=0)
    era = Column(Float, nullable=True)
    innings_pitched = Column(Float, nullable=True)
    hits_allowed = Column(Integer, default=0)
    runs_allowed = Column(Integer, default=0)
    earned_runs = Column(Integer, default=0)
    home_runs_allowed = Column(Integer, default=0)
    pitching_walks = Column(Integer, default=0)
    pitching_strikeouts = Column(Integer, default=0)
    whip = Column(Float, nullable=True)

    # Fielding stats
    fielding_pct = Column(Float, nullable=True)
    errors = Column(Integer, default=0)
    double_plays = Column(Integer, default=0)

    updated_at = Column(DateTime, default=datetime.utcnow)


class MLBPlayerStats(Base):
    __tablename__ = "mlb_player_stats"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    mlb_player_id = Column(Integer, nullable=True)  # External MLB API ID
    season = Column(Integer, nullable=False, index=True)

    # Batting stats
    games = Column(Integer, default=0)
    at_bats = Column(Integer, default=0)
    runs = Column(Integer, default=0)
    hits = Column(Integer, default=0)
    doubles = Column(Integer, default=0)
    triples = Column(Integer, default=0)
    home_runs = Column(Integer, default=0)
    rbi = Column(Integer, default=0)
    stolen_bases = Column(Integer, default=0)
    walks = Column(Integer, default=0)
    strikeouts = Column(Integer, default=0)
    batting_avg = Column(Float, nullable=True)
    obp = Column(Float, nullable=True)
    slg = Column(Float, nullable=True)
    ops = Column(Float, nullable=True)

    # Pitching stats (for pitchers)
    pitching_games = Column(Integer, default=0)
    games_started = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    era = Column(Float, nullable=True)
    innings_pitched = Column(Float, nullable=True)
    hits_allowed = Column(Integer, default=0)
    earned_runs = Column(Integer, default=0)
    home_runs_allowed = Column(Integer, default=0)
    pitching_walks = Column(Integer, default=0)
    pitching_strikeouts = Column(Integer, default=0)
    whip = Column(Float, nullable=True)
    k_per_9 = Column(Float, nullable=True)
    bb_per_9 = Column(Float, nullable=True)

    updated_at = Column(DateTime, default=datetime.utcnow)


class MLBPitcherGameLog(Base):
    __tablename__ = "mlb_pitcher_game_logs"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    mlb_player_id = Column(Integer, nullable=True)
    game_date = Column(DateTime, nullable=False, index=True)

    opponent = Column(String(100), nullable=True)
    is_home = Column(Boolean, default=True)
    result = Column(String(20), nullable=True)  # W, L, ND

    innings_pitched = Column(Float, nullable=True)
    hits_allowed = Column(Integer, default=0)
    runs_allowed = Column(Integer, default=0)
    earned_runs = Column(Integer, default=0)
    walks = Column(Integer, default=0)
    strikeouts = Column(Integer, default=0)
    home_runs_allowed = Column(Integer, default=0)
    pitches = Column(Integer, default=0)
    strikes = Column(Integer, default=0)
    game_score = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


# NBA-specific models
class NBATeamStats(Base):
    __tablename__ = "nba_team_stats"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    nba_team_id = Column(Integer, nullable=True)  # External NBA API ID
    season = Column(String(20), nullable=False, index=True)  # e.g., "2024-25"

    # Basic stats
    games_played = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    win_pct = Column(Float, nullable=True)

    # Offensive stats
    points_per_game = Column(Float, nullable=True)
    field_goal_pct = Column(Float, nullable=True)
    three_point_pct = Column(Float, nullable=True)
    free_throw_pct = Column(Float, nullable=True)
    offensive_rebounds = Column(Float, nullable=True)
    assists_per_game = Column(Float, nullable=True)
    turnovers_per_game = Column(Float, nullable=True)

    # Defensive stats
    points_allowed_per_game = Column(Float, nullable=True)
    defensive_rebounds = Column(Float, nullable=True)
    steals_per_game = Column(Float, nullable=True)
    blocks_per_game = Column(Float, nullable=True)

    # Advanced stats
    pace = Column(Float, nullable=True)  # Possessions per 48 minutes
    offensive_rating = Column(Float, nullable=True)
    defensive_rating = Column(Float, nullable=True)
    net_rating = Column(Float, nullable=True)
    true_shooting_pct = Column(Float, nullable=True)
    effective_fg_pct = Column(Float, nullable=True)

    updated_at = Column(DateTime, default=datetime.utcnow)


class NBAPlayerStats(Base):
    __tablename__ = "nba_player_stats"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    nba_player_id = Column(Integer, nullable=True)  # External NBA API ID
    season = Column(String(20), nullable=False, index=True)

    # Per game stats
    games_played = Column(Integer, default=0)
    games_started = Column(Integer, default=0)
    minutes_per_game = Column(Float, nullable=True)
    points_per_game = Column(Float, nullable=True)
    rebounds_per_game = Column(Float, nullable=True)
    assists_per_game = Column(Float, nullable=True)
    steals_per_game = Column(Float, nullable=True)
    blocks_per_game = Column(Float, nullable=True)
    turnovers_per_game = Column(Float, nullable=True)

    # Shooting stats
    field_goal_pct = Column(Float, nullable=True)
    three_point_pct = Column(Float, nullable=True)
    free_throw_pct = Column(Float, nullable=True)
    true_shooting_pct = Column(Float, nullable=True)
    effective_fg_pct = Column(Float, nullable=True)

    # Advanced stats
    player_efficiency_rating = Column(Float, nullable=True)
    usage_rate = Column(Float, nullable=True)
    offensive_rating = Column(Float, nullable=True)
    defensive_rating = Column(Float, nullable=True)
    box_plus_minus = Column(Float, nullable=True)
    value_over_replacement = Column(Float, nullable=True)

    updated_at = Column(DateTime, default=datetime.utcnow)


class NBAGameSchedule(Base):
    __tablename__ = "nba_game_schedule"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=True)
    nba_game_id = Column(String(50), nullable=True)  # External NBA game ID

    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    game_date = Column(DateTime, nullable=False, index=True)

    # Rest analysis
    home_rest_days = Column(Integer, nullable=True)
    away_rest_days = Column(Integer, nullable=True)
    home_is_back_to_back = Column(Boolean, default=False)
    away_is_back_to_back = Column(Boolean, default=False)

    # Travel analysis
    home_miles_traveled = Column(Float, nullable=True)
    away_miles_traveled = Column(Float, nullable=True)

    venue = Column(String(200), nullable=True)
    is_national_tv = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)


# College Basketball (CBB) Models
class CBBTeam(Base):
    __tablename__ = "cbb_teams"

    id = Column(Integer, primary_key=True, index=True)
    espn_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    short_name = Column(String(100), nullable=True)
    abbreviation = Column(String(20), nullable=True)
    location = Column(String(200), nullable=True)
    conference_id = Column(String(50), nullable=True, index=True)
    conference_name = Column(String(200), nullable=True)
    logo_url = Column(String(500), nullable=True)
    color = Column(String(20), nullable=True)

    # Rankings
    ap_rank = Column(Integer, nullable=True)
    net_rank = Column(Integer, nullable=True)
    coaches_rank = Column(Integer, nullable=True)

    # Record
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    conference_wins = Column(Integer, default=0)
    conference_losses = Column(Integer, default=0)

    updated_at = Column(DateTime, default=datetime.utcnow)


class CBBTeamStats(Base):
    __tablename__ = "cbb_team_stats"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("cbb_teams.id"), nullable=False)
    season = Column(String(20), nullable=False, index=True)

    # Offensive stats
    points_per_game = Column(Float, nullable=True)
    field_goal_pct = Column(Float, nullable=True)
    three_point_pct = Column(Float, nullable=True)
    free_throw_pct = Column(Float, nullable=True)
    offensive_rebounds = Column(Float, nullable=True)
    assists_per_game = Column(Float, nullable=True)
    turnovers_per_game = Column(Float, nullable=True)

    # Defensive stats
    points_allowed_per_game = Column(Float, nullable=True)
    defensive_rebounds = Column(Float, nullable=True)
    steals_per_game = Column(Float, nullable=True)
    blocks_per_game = Column(Float, nullable=True)

    # Advanced stats (KenPom-style)
    offensive_efficiency = Column(Float, nullable=True)
    defensive_efficiency = Column(Float, nullable=True)
    tempo = Column(Float, nullable=True)  # Possessions per 40 minutes
    strength_of_schedule = Column(Float, nullable=True)

    updated_at = Column(DateTime, default=datetime.utcnow)


class CBBGame(Base):
    __tablename__ = "cbb_games"

    id = Column(Integer, primary_key=True, index=True)
    espn_id = Column(String(50), unique=True, nullable=True, index=True)

    home_team_id = Column(Integer, ForeignKey("cbb_teams.id"), nullable=True)
    away_team_id = Column(Integer, ForeignKey("cbb_teams.id"), nullable=True)
    home_team_name = Column(String(200), nullable=True)
    away_team_name = Column(String(200), nullable=True)
    home_team_rank = Column(Integer, nullable=True)
    away_team_rank = Column(Integer, nullable=True)

    game_date = Column(DateTime, nullable=False, index=True)
    venue = Column(String(300), nullable=True)

    status = Column(String(50), default="scheduled")  # scheduled, in_progress, final
    period = Column(Integer, nullable=True)
    clock = Column(String(20), nullable=True)

    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)

    spread = Column(Float, nullable=True)
    over_under = Column(Float, nullable=True)

    is_conference_game = Column(Boolean, default=False)
    is_neutral_site = Column(Boolean, default=False)
    is_tournament = Column(Boolean, default=False)
    tournament_name = Column(String(200), nullable=True)

    broadcast = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class CBBRanking(Base):
    __tablename__ = "cbb_rankings"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("cbb_teams.id"), nullable=False)

    ranking_type = Column(String(50), nullable=False)  # AP, NET, Coaches, KenPom
    rank = Column(Integer, nullable=False)
    previous_rank = Column(Integer, nullable=True)
    points = Column(Integer, nullable=True)
    first_place_votes = Column(Integer, nullable=True)

    week = Column(Integer, nullable=True)
    season = Column(String(20), nullable=False, index=True)

    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)


# Soccer Models
class SoccerCompetition(Base):
    __tablename__ = "soccer_competitions"

    id = Column(Integer, primary_key=True, index=True)
    football_data_id = Column(Integer, nullable=True, unique=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    country = Column(String(100), nullable=True)
    emblem_url = Column(String(500), nullable=True)
    type = Column(String(50), nullable=True)  # LEAGUE, CUP

    current_season_start = Column(DateTime, nullable=True)
    current_season_end = Column(DateTime, nullable=True)
    current_matchday = Column(Integer, nullable=True)

    updated_at = Column(DateTime, default=datetime.utcnow)


class SoccerTeam(Base):
    __tablename__ = "soccer_teams"

    id = Column(Integer, primary_key=True, index=True)
    football_data_id = Column(Integer, unique=True, nullable=True, index=True)

    name = Column(String(200), nullable=False)
    short_name = Column(String(100), nullable=True)
    tla = Column(String(10), nullable=True)  # Three-letter abbreviation
    crest_url = Column(String(500), nullable=True)

    competition_id = Column(Integer, ForeignKey("soccer_competitions.id"), nullable=True)

    address = Column(String(500), nullable=True)
    website = Column(String(500), nullable=True)
    founded = Column(Integer, nullable=True)
    club_colors = Column(String(100), nullable=True)
    venue = Column(String(200), nullable=True)

    updated_at = Column(DateTime, default=datetime.utcnow)


class SoccerMatch(Base):
    __tablename__ = "soccer_matches"

    id = Column(Integer, primary_key=True, index=True)
    football_data_id = Column(Integer, unique=True, nullable=True, index=True)

    competition_id = Column(Integer, ForeignKey("soccer_competitions.id"), nullable=True)
    competition_code = Column(String(20), nullable=True, index=True)

    matchday = Column(Integer, nullable=True)
    stage = Column(String(100), nullable=True)
    group_name = Column(String(50), nullable=True)

    home_team_id = Column(Integer, ForeignKey("soccer_teams.id"), nullable=True)
    away_team_id = Column(Integer, ForeignKey("soccer_teams.id"), nullable=True)
    home_team_name = Column(String(200), nullable=True)
    away_team_name = Column(String(200), nullable=True)

    match_date = Column(DateTime, nullable=False, index=True)
    status = Column(String(50), default="SCHEDULED")  # SCHEDULED, TIMED, IN_PLAY, PAUSED, FINISHED, POSTPONED, CANCELLED

    venue = Column(String(300), nullable=True)

    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)
    home_score_ht = Column(Integer, nullable=True)  # Half-time score
    away_score_ht = Column(Integer, nullable=True)

    winner = Column(String(20), nullable=True)  # HOME_TEAM, AWAY_TEAM, DRAW

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class SoccerStandings(Base):
    __tablename__ = "soccer_standings"

    id = Column(Integer, primary_key=True, index=True)
    competition_id = Column(Integer, ForeignKey("soccer_competitions.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("soccer_teams.id"), nullable=False)

    season = Column(String(20), nullable=False, index=True)
    position = Column(Integer, nullable=False)

    played = Column(Integer, default=0)
    won = Column(Integer, default=0)
    drawn = Column(Integer, default=0)
    lost = Column(Integer, default=0)

    goals_for = Column(Integer, default=0)
    goals_against = Column(Integer, default=0)
    goal_difference = Column(Integer, default=0)

    points = Column(Integer, default=0)
    form = Column(String(20), nullable=True)  # e.g., "W,W,D,L,W"

    updated_at = Column(DateTime, default=datetime.utcnow)


class SoccerPlayerStats(Base):
    __tablename__ = "soccer_player_stats"

    id = Column(Integer, primary_key=True, index=True)
    football_data_id = Column(Integer, nullable=True)

    name = Column(String(200), nullable=False)
    nationality = Column(String(100), nullable=True)
    position = Column(String(50), nullable=True)

    team_id = Column(Integer, ForeignKey("soccer_teams.id"), nullable=True)
    competition_id = Column(Integer, ForeignKey("soccer_competitions.id"), nullable=True)

    season = Column(String(20), nullable=False, index=True)

    goals = Column(Integer, default=0)
    assists = Column(Integer, nullable=True)
    penalties = Column(Integer, nullable=True)
    played_matches = Column(Integer, default=0)

    updated_at = Column(DateTime, default=datetime.utcnow)


# NFL Models
class NFLTeam(Base):
    __tablename__ = "nfl_teams"

    id = Column(Integer, primary_key=True, index=True)
    espn_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    short_name = Column(String(100), nullable=True)
    abbreviation = Column(String(20), nullable=True)
    location = Column(String(200), nullable=True)
    logo_url = Column(String(500), nullable=True)
    color = Column(String(20), nullable=True)

    conference = Column(String(10), nullable=True)  # AFC, NFC
    division = Column(String(20), nullable=True)  # North, South, East, West

    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    ties = Column(Integer, default=0)

    updated_at = Column(DateTime, default=datetime.utcnow)


class NFLGame(Base):
    __tablename__ = "nfl_games"

    id = Column(Integer, primary_key=True, index=True)
    espn_id = Column(String(50), unique=True, nullable=True, index=True)

    home_team_id = Column(Integer, ForeignKey("nfl_teams.id"), nullable=True)
    away_team_id = Column(Integer, ForeignKey("nfl_teams.id"), nullable=True)
    home_team_name = Column(String(200), nullable=True)
    away_team_name = Column(String(200), nullable=True)

    game_date = Column(DateTime, nullable=False, index=True)
    venue = Column(String(300), nullable=True)
    week = Column(Integer, nullable=True)

    status = Column(String(50), default="Scheduled")  # Scheduled, In Progress, Final
    quarter = Column(Integer, nullable=True)
    time_remaining = Column(String(20), nullable=True)

    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)

    spread = Column(Float, nullable=True)
    over_under = Column(Float, nullable=True)

    broadcast = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


# Weather Models
class Venue(Base):
    __tablename__ = "venues"

    id = Column(Integer, primary_key=True, index=True)
    venue_key = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(300), nullable=False)
    team = Column(String(200), nullable=True)
    team_abbr = Column(String(20), nullable=True)
    city = Column(String(200), nullable=True)
    sport = Column(String(50), nullable=False, index=True)

    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)

    dome_type = Column(String(20), nullable=False)  # outdoor, dome, retractable
    surface = Column(String(20), nullable=True)  # grass, turf, artificial
    altitude_ft = Column(Integer, default=0)
    timezone = Column(String(100), nullable=True)

    # MLB-specific
    outfield_direction = Column(Integer, nullable=True)  # degrees
    left_field_distance = Column(Integer, nullable=True)
    center_field_distance = Column(Integer, nullable=True)
    right_field_distance = Column(Integer, nullable=True)

    capacity = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class GameWeather(Base):
    __tablename__ = "game_weather"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=True)

    sport = Column(String(50), nullable=False, index=True)
    game_date = Column(DateTime, nullable=False, index=True)

    # Weather conditions
    temperature_f = Column(Float, nullable=True)
    humidity = Column(Integer, nullable=True)
    precipitation_in = Column(Float, nullable=True)
    rain_in = Column(Float, nullable=True)
    snowfall_in = Column(Float, nullable=True)

    weather_code = Column(Integer, nullable=True)
    conditions = Column(String(100), nullable=True)

    wind_speed_mph = Column(Float, nullable=True)
    wind_direction_degrees = Column(Integer, nullable=True)
    wind_direction = Column(String(10), nullable=True)
    wind_gusts_mph = Column(Float, nullable=True)

    # Metadata
    weather_type = Column(String(20), nullable=True)  # current, forecast, historical
    is_dome_closed = Column(Boolean, nullable=True)

    fetched_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class WeatherImpactFactor(Base):
    __tablename__ = "weather_impact_factors"

    id = Column(Integer, primary_key=True, index=True)
    game_weather_id = Column(Integer, ForeignKey("game_weather.id"), nullable=False)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=True)

    sport = Column(String(50), nullable=False, index=True)

    # Impact calculations
    total_adjustment = Column(Float, nullable=False)  # Points/runs adjustment
    scoring_factor = Column(Float, default=1.0)  # Multiplier for scoring

    # Sport-specific factors
    hr_factor = Column(Float, nullable=True)  # MLB: HR probability multiplier
    pass_yards_factor = Column(Float, nullable=True)  # NFL: Pass yards multiplier
    rush_yards_factor = Column(Float, nullable=True)  # NFL: Rush yards multiplier
    turnover_factor = Column(Float, nullable=True)  # NFL: Turnover multiplier
    goals_factor = Column(Float, nullable=True)  # Soccer: Goals multiplier

    # Recommendation
    recommendation = Column(String(20), nullable=True)  # OVER, UNDER, NEUTRAL
    confidence = Column(Float, nullable=True)  # 0-1 confidence score

    # Explanation
    factors = Column(Text, nullable=True)  # JSON list of factor explanations

    created_at = Column(DateTime, default=datetime.utcnow)


# Coach DNA Models
class Coach(Base):
    __tablename__ = "coaches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    sport = Column(String(50), nullable=False, index=True)
    current_team = Column(String(200), nullable=True)

    years_experience = Column(Integer, default=0)

    # Career records
    career_wins = Column(Integer, default=0)
    career_losses = Column(Integer, default=0)

    # ATS (Against The Spread) records
    career_ats_wins = Column(Integer, default=0)
    career_ats_losses = Column(Integer, default=0)
    career_ats_pushes = Column(Integer, default=0)

    # Over/Under records
    career_over_wins = Column(Integer, default=0)
    career_under_wins = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    situational_records = relationship("CoachSituationalRecord", back_populates="coach", cascade="all, delete-orphan")
    tendencies = relationship("CoachTendency", back_populates="coach", cascade="all, delete-orphan")


class CoachSituationalRecord(Base):
    __tablename__ = "coach_situational_records"

    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey("coaches.id"), nullable=False, index=True)

    situation = Column(String(100), nullable=False, index=True)  # "as_underdog", "after_loss", "primetime", etc.

    # Straight up record
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    pushes = Column(Integer, default=0)

    # ATS record for this situation
    ats_wins = Column(Integer, default=0)
    ats_losses = Column(Integer, default=0)

    total_games = Column(Integer, default=0)
    roi_percentage = Column(Float, nullable=True)

    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    coach = relationship("Coach", back_populates="situational_records")


class CoachTendency(Base):
    __tablename__ = "coach_tendencies"

    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey("coaches.id"), nullable=False, index=True)

    tendency_type = Column(String(100), nullable=False)  # "4th_down_aggressiveness", "timeout_usage", etc.
    value = Column(Float, nullable=False)
    league_average = Column(Float, nullable=True)
    percentile = Column(Integer, nullable=True)  # 0-100

    notes = Column(Text, nullable=True)

    coach = relationship("Coach", back_populates="tendencies")


# Official (Referee/Umpire) Models
class Official(Base):
    __tablename__ = "officials"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    sport = Column(String(50), nullable=False, index=True)

    years_experience = Column(Integer, default=0)
    games_officiated = Column(Integer, default=0)

    # Tendencies
    avg_total_score = Column(Float, nullable=True)  # Average total points in their games
    avg_penalties_per_game = Column(Float, nullable=True)  # NFL
    avg_fouls_per_game = Column(Float, nullable=True)  # NBA
    avg_penalty_yards_per_game = Column(Float, nullable=True)  # NFL

    # O/U tendency
    over_percentage = Column(Float, nullable=True)  # How often games go over
    over_wins = Column(Integer, default=0)
    under_wins = Column(Integer, default=0)

    # Home team stats
    home_team_win_pct = Column(Float, nullable=True)
    home_team_cover_pct = Column(Float, nullable=True)
    home_team_foul_differential = Column(Float, nullable=True)  # NBA: positive = more fouls on away

    # MLB-specific
    strike_zone_runs_per_9 = Column(Float, nullable=True)  # Runs allowed when behind plate
    ejection_rate = Column(Float, nullable=True)  # Ejections per 100 games

    # NBA-specific
    star_foul_rate = Column(Float, nullable=True)  # Foul rate on star players vs average

    # Photo/profile
    photo_url = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    game_logs = relationship("OfficialGameLog", back_populates="official", cascade="all, delete-orphan")


class OfficialGameLog(Base):
    __tablename__ = "official_game_logs"

    id = Column(Integer, primary_key=True, index=True)
    official_id = Column(Integer, ForeignKey("officials.id"), nullable=False, index=True)

    game_id = Column(Integer, ForeignKey("games.id"), nullable=True)
    game_date = Column(DateTime, nullable=False, index=True)
    sport = Column(String(50), nullable=False, index=True)

    home_team = Column(String(200), nullable=True)
    away_team = Column(String(200), nullable=True)

    # Scores
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)
    total_score = Column(Integer, nullable=True)

    # O/U tracking
    over_under_line = Column(Float, nullable=True)
    went_over = Column(Boolean, nullable=True)

    # Home team result
    home_team_won = Column(Boolean, nullable=True)
    spread = Column(Float, nullable=True)
    home_covered = Column(Boolean, nullable=True)

    # Sport-specific stats
    penalties_called = Column(Integer, nullable=True)  # NFL
    penalty_yards = Column(Integer, nullable=True)  # NFL
    fouls_called = Column(Integer, nullable=True)  # NBA
    home_fouls = Column(Integer, nullable=True)  # NBA
    away_fouls = Column(Integer, nullable=True)  # NBA
    ejections = Column(Integer, default=0)

    # MLB-specific
    runs_scored = Column(Integer, nullable=True)
    strikeouts = Column(Integer, nullable=True)
    walks = Column(Integer, nullable=True)

    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    official = relationship("Official", back_populates="game_logs")


# Line Movement Summary Model
class LineMovementSummary(Base):
    __tablename__ = "line_movement_summaries"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False, index=True)
    sport = Column(String(50), nullable=False, index=True)

    market_type = Column(String(50), nullable=False)  # spread, total, moneyline

    opening_line = Column(Float, nullable=True)
    current_line = Column(Float, nullable=True)
    closing_line = Column(Float, nullable=True)

    opening_odds = Column(Integer, nullable=True)
    current_odds = Column(Integer, nullable=True)
    closing_odds = Column(Integer, nullable=True)

    total_movement = Column(Float, nullable=True)

    # Direction analysis
    movement_direction = Column(String(50), nullable=True)  # toward_favorite, toward_underdog, toward_over, toward_under

    # Sharp money indicators
    reverse_line_movement = Column(Boolean, default=False)  # Line moved opposite of public
    steam_move_detected = Column(Boolean, default=False)  # Rapid coordinated movement
    sharp_book_originated = Column(Boolean, default=False)  # Pinnacle/Circa moved first

    # Public betting percentages (if available)
    public_bet_percentage = Column(Float, nullable=True)
    public_money_percentage = Column(Float, nullable=True)

    first_move_book = Column(String(100), nullable=True)  # Which book moved first
    steam_move_time = Column(DateTime, nullable=True)  # When steam move was detected

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Situational Factors Models
class GameSituation(Base):
    __tablename__ = "game_situations"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=True, index=True)
    sport = Column(String(50), nullable=False, index=True)

    home_team = Column(String(200), nullable=False)
    away_team = Column(String(200), nullable=False)
    game_date = Column(DateTime, nullable=False, index=True)
    game_time = Column(String(20), nullable=True)

    # Rest factors
    home_days_rest = Column(Integer, nullable=True)
    away_days_rest = Column(Integer, nullable=True)
    rest_advantage = Column(Integer, nullable=True)  # positive = home advantage
    home_back_to_back = Column(Boolean, default=False)
    away_back_to_back = Column(Boolean, default=False)
    home_three_in_four = Column(Boolean, default=False)
    away_three_in_four = Column(Boolean, default=False)

    # Travel factors
    away_travel_miles = Column(Integer, nullable=True)
    away_time_zones_crossed = Column(Integer, nullable=True)
    away_direction = Column(String(20), nullable=True)  # east_to_west, west_to_east, same
    home_altitude_ft = Column(Integer, nullable=True)
    away_origin_city = Column(String(100), nullable=True)

    # Motivation factors
    is_rivalry = Column(Boolean, default=False)
    rivalry_name = Column(String(100), nullable=True)
    is_revenge_game = Column(Boolean, default=False)
    revenge_team = Column(String(200), nullable=True)
    revenge_reason = Column(Text, nullable=True)
    is_lookahead_spot = Column(Boolean, default=False)
    lookahead_team = Column(String(200), nullable=True)
    lookahead_opponent = Column(String(200), nullable=True)
    is_letdown_spot = Column(Boolean, default=False)
    letdown_team = Column(String(200), nullable=True)
    letdown_reason = Column(Text, nullable=True)
    is_elimination = Column(Boolean, default=False)
    is_nothing_to_play_for = Column(Boolean, default=False)
    nothing_team = Column(String(200), nullable=True)
    is_home_opener = Column(Boolean, default=False)
    is_season_finale = Column(Boolean, default=False)

    # Schedule spot flags
    is_sandwich_spot = Column(Boolean, default=False)
    sandwich_team = Column(String(200), nullable=True)
    is_trap_game = Column(Boolean, default=False)
    trap_team = Column(String(200), nullable=True)

    # Calculated edges
    rest_edge_home = Column(Float, nullable=True)
    travel_edge_home = Column(Float, nullable=True)
    motivation_edge_home = Column(Float, nullable=True)
    schedule_edge_home = Column(Float, nullable=True)
    total_situation_edge = Column(Float, nullable=True)  # positive = home edge
    confidence = Column(Float, nullable=True)  # 0-1
    recommendation = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HistoricalSituation(Base):
    __tablename__ = "historical_situations"

    id = Column(Integer, primary_key=True, index=True)
    situation_type = Column(String(100), nullable=False, unique=True, index=True)
    situation_name = Column(String(200), nullable=False)
    sport = Column(String(50), nullable=False, index=True)  # NFL, NBA, MLB, ALL

    sample_size = Column(Integer, default=0)
    ats_wins = Column(Integer, default=0)
    ats_losses = Column(Integer, default=0)
    ats_pushes = Column(Integer, default=0)
    win_percentage = Column(Float, nullable=True)
    roi_percentage = Column(Float, nullable=True)

    # Over/Under stats for some situations
    ou_overs = Column(Integer, nullable=True)
    ou_unders = Column(Integer, nullable=True)
    ou_over_percentage = Column(Float, nullable=True)

    # Additional context
    edge_points = Column(Float, nullable=True)  # Estimated point spread impact
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Social Sentiment Models
class SocialSentiment(Base):
    __tablename__ = "social_sentiments"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=True, index=True)
    sport = Column(String(50), nullable=False, index=True)

    team_name = Column(String(200), nullable=False, index=True)
    source = Column(String(50), nullable=False)  # reddit, twitter, news

    sentiment_score = Column(Float, nullable=True)  # -1 to +1
    volume = Column(Integer, default=0)  # Number of mentions
    sample_size = Column(Integer, default=0)

    bullish_percentage = Column(Float, nullable=True)
    bearish_percentage = Column(Float, nullable=True)
    neutral_percentage = Column(Float, nullable=True)

    notable_mentions = Column(Text, nullable=True)  # JSON list of key quotes/posts
    key_narratives = Column(Text, nullable=True)  # JSON list of narratives

    fade_signal = Column(Boolean, default=False)
    confidence = Column(Float, nullable=True)

    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PublicBettingData(Base):
    __tablename__ = "public_betting_data"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=True, index=True)
    sport = Column(String(50), nullable=False, index=True)

    # Spread betting percentages
    spread_bet_pct_home = Column(Float, nullable=True)
    spread_bet_pct_away = Column(Float, nullable=True)
    spread_money_pct_home = Column(Float, nullable=True)
    spread_money_pct_away = Column(Float, nullable=True)

    # Moneyline percentages
    ml_bet_pct_home = Column(Float, nullable=True)
    ml_bet_pct_away = Column(Float, nullable=True)
    ml_money_pct_home = Column(Float, nullable=True)
    ml_money_pct_away = Column(Float, nullable=True)

    # Total betting percentages
    total_bet_pct_over = Column(Float, nullable=True)
    total_bet_pct_under = Column(Float, nullable=True)
    total_money_pct_over = Column(Float, nullable=True)
    total_money_pct_under = Column(Float, nullable=True)

    ticket_count_estimated = Column(Integer, nullable=True)

    # Sharp vs public divergence
    sharp_vs_public_divergence = Column(Boolean, default=False)
    sharp_side_spread = Column(String(50), nullable=True)  # home, away
    sharp_side_total = Column(String(50), nullable=True)  # over, under

    # Fade signals
    fade_public_spread = Column(Boolean, default=False)
    fade_public_total = Column(Boolean, default=False)

    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Unified Prediction Models
class UnifiedPrediction(Base):
    __tablename__ = "unified_predictions"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False, index=True)
    sport = Column(String(50), nullable=False, index=True)

    home_team = Column(String(200), nullable=False)
    away_team = Column(String(200), nullable=False)
    game_date = Column(DateTime, nullable=False, index=True)

    market_type = Column(String(50), nullable=False)  # spread, total, moneyline
    line_value = Column(Float, nullable=True)

    # Individual factor edges (positive = home/over edge)
    line_movement_edge = Column(Float, nullable=True)
    line_movement_direction = Column(String(50), nullable=True)
    line_movement_signal = Column(Text, nullable=True)

    coach_dna_edge = Column(Float, nullable=True)
    coach_dna_direction = Column(String(50), nullable=True)
    coach_dna_signal = Column(Text, nullable=True)

    situational_edge = Column(Float, nullable=True)
    situational_direction = Column(String(50), nullable=True)
    situational_signal = Column(Text, nullable=True)

    weather_edge = Column(Float, nullable=True)
    weather_direction = Column(String(50), nullable=True)
    weather_signal = Column(Text, nullable=True)

    officials_edge = Column(Float, nullable=True)
    officials_direction = Column(String(50), nullable=True)
    officials_signal = Column(Text, nullable=True)

    public_fade_edge = Column(Float, nullable=True)
    public_fade_direction = Column(String(50), nullable=True)
    public_fade_signal = Column(Text, nullable=True)

    historical_elo_edge = Column(Float, nullable=True)
    historical_elo_direction = Column(String(50), nullable=True)
    historical_elo_signal = Column(Text, nullable=True)

    social_sentiment_edge = Column(Float, nullable=True)
    social_sentiment_direction = Column(String(50), nullable=True)
    social_sentiment_signal = Column(Text, nullable=True)

    # Aggregated analysis
    confirming_factors = Column(Integer, default=0)
    conflicting_factors = Column(Integer, default=0)
    alignment_score = Column(Float, nullable=True)

    # Final prediction
    predicted_side = Column(String(200), nullable=True)  # e.g., "Bills +3.5"
    raw_edge = Column(Float, nullable=True)  # Total weighted edge
    confidence = Column(Float, nullable=True)  # 0-1
    confidence_label = Column(String(50), nullable=True)  # VERY HIGH, HIGH, MEDIUM, LOW
    expected_value = Column(Float, nullable=True)
    kelly_fraction = Column(Float, nullable=True)

    recommendation = Column(String(50), nullable=True)  # STRONG BET, BET, LEAN, MONITOR, AVOID
    unit_size = Column(Float, nullable=True)

    explanation = Column(Text, nullable=True)

    # Star rating (1-5)
    star_rating = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NewsItem(Base):
    __tablename__ = "news_items"

    id = Column(Integer, primary_key=True, index=True)
    sport = Column(String(50), nullable=False, index=True)

    headline = Column(String(500), nullable=False)
    source = Column(String(100), nullable=True)
    url = Column(String(1000), nullable=True)

    teams_affected = Column(Text, nullable=True)  # JSON list
    players_affected = Column(Text, nullable=True)  # JSON list

    impact_level = Column(String(20), nullable=True)  # HIGH, MEDIUM, LOW
    line_impact_estimate = Column(String(200), nullable=True)

    news_type = Column(String(50), nullable=True)  # injury, lineup, weather, trade, suspension

    published_at = Column(DateTime, nullable=True, index=True)
    expires_at = Column(DateTime, nullable=True)

    is_breaking = Column(Boolean, default=False)
    is_processed = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================
# POWER RATINGS & ATS TRACKING (Phase 1)
# ============================================

class TeamPowerRating(Base):
    """Team power ratings for betting analysis"""
    __tablename__ = "team_power_ratings"

    id = Column(Integer, primary_key=True, index=True)
    sport = Column(String(50), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    team_name = Column(String(200), nullable=False)
    team_abbrev = Column(String(20), nullable=True)

    # Core ratings (scale 0-100)
    power_rating = Column(Float, nullable=False, default=50.0)
    offensive_rating = Column(Float, nullable=True)  # Points per 100 possessions
    defensive_rating = Column(Float, nullable=True)  # Points allowed per 100 possessions
    net_rating = Column(Float, nullable=True)  # Off - Def

    # Home field advantage
    home_field_advantage = Column(Float, default=3.0)  # Points added at home

    # ATS Record (Against The Spread)
    ats_wins = Column(Integer, default=0)
    ats_losses = Column(Integer, default=0)
    ats_pushes = Column(Integer, default=0)
    ats_percentage = Column(Float, nullable=True)

    # Straight Up Record
    su_wins = Column(Integer, default=0)
    su_losses = Column(Integer, default=0)

    # Over/Under Record
    over_wins = Column(Integer, default=0)
    under_wins = Column(Integer, default=0)

    # Recent form (last 5 games)
    last_5_ats = Column(String(20), nullable=True)  # "WWLWL"
    last_5_su = Column(String(20), nullable=True)
    recent_form_rating = Column(Float, nullable=True)

    # Strength of schedule
    sos_rating = Column(Float, nullable=True)  # 0-100
    sos_rank = Column(Integer, nullable=True)

    # Ranking
    power_rank = Column(Integer, nullable=True)

    season = Column(String(20), nullable=True)  # "2024-25"
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class ATSRecord(Base):
    """Detailed ATS record tracking by situation"""
    __tablename__ = "ats_records"

    id = Column(Integer, primary_key=True, index=True)
    sport = Column(String(50), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    team_name = Column(String(200), nullable=False, index=True)
    season = Column(String(20), nullable=False, index=True)  # "2024-25"

    # Overall ATS
    total_ats_wins = Column(Integer, default=0)
    total_ats_losses = Column(Integer, default=0)
    total_ats_pushes = Column(Integer, default=0)

    # Home/Away splits
    home_ats_wins = Column(Integer, default=0)
    home_ats_losses = Column(Integer, default=0)
    home_ats_pushes = Column(Integer, default=0)
    away_ats_wins = Column(Integer, default=0)
    away_ats_losses = Column(Integer, default=0)
    away_ats_pushes = Column(Integer, default=0)

    # Favorite/Underdog splits
    as_favorite_wins = Column(Integer, default=0)
    as_favorite_losses = Column(Integer, default=0)
    as_favorite_pushes = Column(Integer, default=0)
    as_underdog_wins = Column(Integer, default=0)
    as_underdog_losses = Column(Integer, default=0)
    as_underdog_pushes = Column(Integer, default=0)

    # Big favorite/underdog (7+ points)
    as_big_favorite_wins = Column(Integer, default=0)
    as_big_favorite_losses = Column(Integer, default=0)
    as_big_underdog_wins = Column(Integer, default=0)
    as_big_underdog_losses = Column(Integer, default=0)

    # O/U Record
    over_wins = Column(Integer, default=0)
    over_losses = Column(Integer, default=0)
    under_wins = Column(Integer, default=0)
    under_losses = Column(Integer, default=0)

    # Trend tracking
    last_10_ats = Column(String(20), nullable=True)  # "WWLWLWWLLW"
    current_ats_streak = Column(Integer, default=0)  # Positive = covers, negative = fails

    # Calculated fields
    ats_percentage = Column(Float, nullable=True)
    home_ats_percentage = Column(Float, nullable=True)
    away_ats_percentage = Column(Float, nullable=True)
    favorite_ats_percentage = Column(Float, nullable=True)
    underdog_ats_percentage = Column(Float, nullable=True)

    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SituationalTrend(Base):
    """Situational betting trends"""
    __tablename__ = "situational_trends"

    id = Column(Integer, primary_key=True, index=True)
    sport = Column(String(50), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    team_name = Column(String(200), nullable=False, index=True)
    season = Column(String(20), nullable=False, index=True)

    # Situation type
    situation_type = Column(String(100), nullable=False, index=True)
    # Examples: home_favorite, road_favorite, home_underdog, road_underdog,
    # after_bye_week, short_rest, long_rest, division_game, conference_game,
    # primetime_game, revenge_game, back_to_back, day_game, night_game

    situation_description = Column(String(500), nullable=True)

    # Record in situation
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    pushes = Column(Integer, default=0)

    # ATS in situation
    ats_wins = Column(Integer, default=0)
    ats_losses = Column(Integer, default=0)
    ats_pushes = Column(Integer, default=0)

    # O/U in situation
    over_wins = Column(Integer, default=0)
    under_wins = Column(Integer, default=0)

    # Stats
    avg_margin = Column(Float, nullable=True)
    avg_total = Column(Float, nullable=True)
    cover_percentage = Column(Float, nullable=True)

    # Significance
    sample_size = Column(Integer, default=0)
    is_significant = Column(Boolean, default=False)  # True if sample >= 10
    trend_strength = Column(String(20), nullable=True)  # "STRONG", "MODERATE", "WEAK"

    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HeadToHeadGame(Base):
    """Historical head-to-head matchup results"""
    __tablename__ = "head_to_head_games"

    id = Column(Integer, primary_key=True, index=True)
    sport = Column(String(50), nullable=False, index=True)

    team1_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    team2_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    team1_name = Column(String(200), nullable=False, index=True)
    team2_name = Column(String(200), nullable=False, index=True)

    game_date = Column(DateTime, nullable=False, index=True)
    season = Column(String(20), nullable=True)

    # Scores
    team1_score = Column(Integer, nullable=False)
    team2_score = Column(Integer, nullable=False)

    # Betting lines
    spread = Column(Float, nullable=True)  # Team1 spread (negative = favorite)
    spread_result = Column(String(20), nullable=True)  # "team1_cover", "team2_cover", "push"
    total_line = Column(Float, nullable=True)
    total_result = Column(String(20), nullable=True)  # "over", "under", "push"

    # Game context
    venue = Column(String(200), nullable=True)
    is_neutral_site = Column(Boolean, default=False)
    is_playoff = Column(Boolean, default=False)
    game_type = Column(String(50), nullable=True)  # "regular", "playoff", "championship"

    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================
# PAPER TRADING SYSTEM (Phase 2)
# ============================================

class PaperTrade(Base):
    """Virtual betting for paper trading"""
    __tablename__ = "paper_trades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # Game info
    sport = Column(String(50), nullable=False, index=True)
    game_id = Column(String(100), nullable=True)  # From Odds API
    game_description = Column(String(500), nullable=True)  # "Bills vs Chiefs"

    # Bet details
    bet_type = Column(String(50), nullable=False)  # "spread", "moneyline", "total", "prop"
    selection = Column(String(200), nullable=False)  # Team name or "over"/"under"
    line_value = Column(Float, nullable=True)  # The spread/total number
    odds = Column(Integer, nullable=False)  # American odds (-110, +150, etc.)

    # Stake and potential payout
    stake = Column(Float, nullable=False)
    potential_payout = Column(Float, nullable=False)

    # Timing
    placed_at = Column(DateTime, default=datetime.utcnow, index=True)
    game_date = Column(DateTime, nullable=True, index=True)
    settled_at = Column(DateTime, nullable=True)

    # Result
    status = Column(String(20), default="pending", index=True)  # "pending", "won", "lost", "push", "cancelled"
    result_score = Column(String(100), nullable=True)  # "Team1 24 - Team2 21"
    profit_loss = Column(Float, nullable=True)

    # Analysis
    edge_at_placement = Column(Float, nullable=True)  # EdgeBet's calculated edge
    closing_line_value = Column(Float, nullable=True)  # What the line closed at

    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PaperBankroll(Base):
    """Virtual bankroll tracking"""
    __tablename__ = "paper_bankrolls"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # Balance
    starting_balance = Column(Float, default=10000.0)  # $10,000 default
    current_balance = Column(Float, default=10000.0)
    high_water_mark = Column(Float, default=10000.0)  # Highest balance reached
    low_water_mark = Column(Float, default=10000.0)  # Lowest balance

    # Bet counts
    total_bets = Column(Integer, default=0)
    pending_bets = Column(Integer, default=0)
    winning_bets = Column(Integer, default=0)
    losing_bets = Column(Integer, default=0)
    pushes = Column(Integer, default=0)

    # Financial stats
    total_wagered = Column(Float, default=0.0)
    total_won = Column(Float, default=0.0)
    total_lost = Column(Float, default=0.0)
    total_profit_loss = Column(Float, default=0.0)

    # Performance metrics
    win_percentage = Column(Float, nullable=True)
    roi_percentage = Column(Float, nullable=True)  # (profit / total_wagered) * 100
    units_won = Column(Float, default=0.0)  # Profit in "units" (typically 1% of bankroll)

    # Streaks
    current_streak = Column(Integer, default=0)  # Positive = winning, negative = losing
    longest_win_streak = Column(Integer, default=0)
    longest_lose_streak = Column(Integer, default=0)

    # By sport tracking (JSON)
    stats_by_sport = Column(Text, nullable=True)  # JSON: {"NFL": {"wins": 5, "losses": 3}, ...}

    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PaperBankrollHistory(Base):
    """Daily paper bankroll snapshots for charting"""
    __tablename__ = "paper_bankroll_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    bankroll_id = Column(Integer, ForeignKey("paper_bankrolls.id"), nullable=True)

    date = Column(DateTime, nullable=False, index=True)
    balance = Column(Float, nullable=False)
    daily_profit_loss = Column(Float, default=0.0)
    bets_placed = Column(Integer, default=0)
    bets_settled = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================
# PREDICTION TRACKING (Phase 3)
# ============================================

class PredictionRecord(Base):
    """Track prediction accuracy"""
    __tablename__ = "prediction_records"

    id = Column(Integer, primary_key=True, index=True)
    sport = Column(String(50), nullable=False, index=True)

    # Game reference
    game_id = Column(String(100), nullable=True, index=True)
    game_description = Column(String(500), nullable=True)
    game_date = Column(DateTime, nullable=True, index=True)

    # Prediction details
    prediction_type = Column(String(50), nullable=False)  # "spread", "moneyline", "total"
    prediction = Column(String(200), nullable=False)  # "Team A -3.5", "Over 220.5"
    predicted_edge = Column(Float, nullable=True)  # EdgeBet's calculated edge %
    confidence_score = Column(Float, nullable=True)  # 0-100

    # Factors used (JSON)
    factors_used = Column(Text, nullable=True)  # {"coach_dna": 2.5, "weather": 1.0, ...}

    # Result
    actual_result = Column(String(200), nullable=True)  # "Team A won by 7"
    was_correct = Column(Boolean, nullable=True)

    # Analysis
    edge_realized = Column(Float, nullable=True)  # Actual vs predicted
    closing_line = Column(Float, nullable=True)
    clv_captured = Column(Float, nullable=True)  # Closing Line Value

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    settled_at = Column(DateTime, nullable=True)


class FactorPerformance(Base):
    """Track how each prediction factor performs"""
    __tablename__ = "factor_performance"

    id = Column(Integer, primary_key=True, index=True)
    factor_name = Column(String(100), nullable=False, index=True)
    # coach_dna, officials, weather, line_movement, rest_days, travel, divisional, public_fade

    sport = Column(String(50), nullable=True, index=True)  # NULL = all sports

    # When factor was present
    times_used = Column(Integer, default=0)
    correct_predictions = Column(Integer, default=0)
    incorrect_predictions = Column(Integer, default=0)

    # Hit rate
    hit_rate = Column(Float, nullable=True)  # correct / total

    # Edge contribution
    avg_edge_when_present = Column(Float, nullable=True)
    avg_edge_when_correct = Column(Float, nullable=True)
    avg_edge_when_incorrect = Column(Float, nullable=True)

    # Current weight in model
    current_weight = Column(Float, default=1.0)
    recommended_weight = Column(Float, nullable=True)

    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# API Key Management for Pro users
class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    key_prefix = Column(String(20), nullable=False)  # First 16 chars for identification
    name = Column(String(100), nullable=False)

    is_active = Column(Boolean, default=True)
    rate_limit = Column(Integer, default=100)  # Requests per minute
    monthly_limit = Column(Integer, default=50000)  # Total requests per month
    current_month_usage = Column(Integer, default=0)

    last_used = Column(DateTime, nullable=True)
    last_reset = Column(DateTime, default=datetime.utcnow)  # For monthly usage reset

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="api_keys")
    usage_logs = relationship("APIUsage", back_populates="api_key")


class APIUsage(Base):
    __tablename__ = "api_usage"

    id = Column(Integer, primary_key=True, index=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=False)

    endpoint = Column(String(200), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Integer, nullable=True)

    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    api_key = relationship("APIKey", back_populates="usage_logs")


# User Device for Push Notifications
class UserDevice(Base):
    __tablename__ = "user_devices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    device_token = Column(String(500), unique=True, nullable=False, index=True)
    device_type = Column(String(20), nullable=False)  # ios, android, web
    device_name = Column(String(100), nullable=True)

    is_active = Column(Boolean, default=True)

    last_used = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="devices")


# Subscription Payment History
class PaymentHistory(Base):
    __tablename__ = "payment_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    stripe_payment_id = Column(String(255), nullable=True, index=True)
    stripe_invoice_id = Column(String(255), nullable=True)

    amount = Column(Integer, nullable=False)  # Amount in cents
    currency = Column(String(10), default="usd")
    status = Column(String(50), nullable=False)  # succeeded, failed, pending, refunded

    description = Column(String(500), nullable=True)
    tier = Column(String(20), nullable=True)  # premium, pro
    billing_period = Column(String(20), nullable=True)  # monthly, yearly

    created_at = Column(DateTime, default=datetime.utcnow)


# Edge Validation Tracker - Tracked Pick
class TrackedPick(Base):
    __tablename__ = "tracked_picks"

    id = Column(String(50), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    settled_at = Column(DateTime, nullable=True)

    # Game info
    game_id = Column(String(100), index=True)
    sport = Column(String(50), nullable=False, index=True)
    home_team = Column(String(200), nullable=False)
    away_team = Column(String(200), nullable=False)
    game_time = Column(DateTime, nullable=False)

    # Pick info
    pick_type = Column(String(50), nullable=False)  # spread, moneyline, total
    pick = Column(String(200), nullable=False)  # "Chiefs -3", "Over 45.5"
    pick_team = Column(String(200), nullable=True)  # Team picked (for spread/ML)
    line_value = Column(Float, nullable=True)  # -3, 45.5, etc.
    odds = Column(Integer, nullable=False)  # American odds: -110, +150

    # EdgeBet analysis
    confidence = Column(Float, nullable=False)  # 0-100
    recommended_units = Column(Float, default=1.0)  # 1-5 based on confidence

    # Factor breakdown (stored as JSON string)
    factors = Column(Text, nullable=True)

    # Weather at game time
    weather_data = Column(Text, nullable=True)

    # Result
    status = Column(String(20), default="pending", index=True)  # pending, won, lost, push
    result_score = Column(String(100), nullable=True)  # "Chiefs 27, Raiders 20"
    spread_result = Column(Float, nullable=True)  # Actual margin: -7 (home won by 7)
    total_result = Column(Float, nullable=True)  # Actual total points

    # Bankroll impact
    units_wagered = Column(Float, default=1.0)
    units_result = Column(Float, nullable=True)  # +0.91 or -1.0
    bankroll_after = Column(Float, nullable=True)


# Bankroll Snapshots for tracking over time
class BankrollSnapshot(Base):
    __tablename__ = "bankroll_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    balance = Column(Float, nullable=False)
    total_picks = Column(Integer, default=0)
    total_wins = Column(Integer, default=0)
    total_losses = Column(Integer, default=0)
    total_pushes = Column(Integer, default=0)

    total_wagered = Column(Float, default=0.0)
    total_won = Column(Float, default=0.0)
    total_lost = Column(Float, default=0.0)

    roi = Column(Float, default=0.0)
    win_rate = Column(Float, default=0.0)


def init_db():
    Base.metadata.create_all(bind=engine)
