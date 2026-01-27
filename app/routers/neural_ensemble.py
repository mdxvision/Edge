"""
Neural Ensemble Router

API endpoints for neural network predictions:
- Game predictions using ensemble model
- Model information and comparison
- Training and model management
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from app.db import get_db, User, Game, Team, HistoricalGameResult
from app.routers.auth import require_auth
from app.services.neural_ensemble import (
    NeuralEnsemble,
    ModelManager,
    ModelConfig,
    FeatureEngineering,
    predict_game,
    get_model_comparison,
    train_ensemble,
)

router = APIRouter(prefix="/neural", tags=["Neural Ensemble"])


# =============================================================================
# Request/Response Models
# =============================================================================

class GamePredictionRequest(BaseModel):
    """Request model for game prediction."""
    sport: str = Field(..., description="Sport code (NFL, NBA, MLB, NHL, SOCCER)")
    home_team: str = Field(..., description="Home team name")
    away_team: str = Field(..., description="Away team name")

    # Team stats
    home_elo: float = Field(1500, description="Home team ELO rating")
    away_elo: float = Field(1500, description="Away team ELO rating")
    home_recent_win_pct: float = Field(0.5, ge=0, le=1, description="Home team recent win %")
    away_recent_win_pct: float = Field(0.5, ge=0, le=1, description="Away team recent win %")

    # Game context
    home_rest_days: int = Field(3, ge=0, description="Home team rest days")
    away_rest_days: int = Field(3, ge=0, description="Away team rest days")
    away_travel_miles: int = Field(0, ge=0, description="Away team travel distance")
    is_primetime: bool = Field(False, description="Is primetime game")

    # 8-factor scores (0-100)
    line_movement_score: float = Field(50, ge=0, le=100)
    coach_dna_score: float = Field(50, ge=0, le=100)
    situational_score: float = Field(50, ge=0, le=100)
    weather_score: float = Field(50, ge=0, le=100)
    officials_score: float = Field(50, ge=0, le=100)
    public_fade_score: float = Field(50, ge=0, le=100)
    elo_score: float = Field(50, ge=0, le=100)
    social_score: float = Field(50, ge=0, le=100)

    class Config:
        json_schema_extra = {
            "example": {
                "sport": "NFL",
                "home_team": "Buffalo Bills",
                "away_team": "Kansas City Chiefs",
                "home_elo": 1620,
                "away_elo": 1650,
                "home_recent_win_pct": 0.7,
                "away_recent_win_pct": 0.8,
                "home_rest_days": 7,
                "away_rest_days": 7,
                "away_travel_miles": 1200,
                "is_primetime": True,
                "line_movement_score": 65,
                "coach_dna_score": 55,
                "situational_score": 60,
                "weather_score": 50,
                "officials_score": 50,
                "public_fade_score": 45,
                "elo_score": 45,
                "social_score": 55
            }
        }


class TrainingRequest(BaseModel):
    """Request model for model training."""
    sport: Optional[str] = Field(None, description="Limit training to specific sport")
    max_games: int = Field(1000, ge=100, le=10000, description="Maximum games to use")
    validation_split: float = Field(0.2, ge=0.1, le=0.4, description="Validation data fraction")


class ModelWeightsUpdate(BaseModel):
    """Request to update ensemble weights."""
    feedforward_weight: float = Field(..., ge=0, le=1)
    lstm_weight: float = Field(..., ge=0, le=1)
    elo_weight: float = Field(..., ge=0, le=1)


# =============================================================================
# Prediction Endpoints
# =============================================================================

@router.post("/predict")
async def predict_game_outcome(
    request: GamePredictionRequest,
    user: User = Depends(require_auth)
):
    """
    Get neural ensemble prediction for a game.

    Uses three model components:
    - Feedforward network (static features)
    - LSTM network (time series form)
    - ELO baseline (traditional ratings)

    Returns combined prediction with confidence and component breakdowns.
    """
    # Build stats dictionaries
    home_stats = {
        "elo_rating": request.home_elo,
        "recent_win_pct": request.home_recent_win_pct,
        "home_win_pct": 0.55,  # Default
        "offensive_rating": 100,
        "defensive_rating": 100,
        "pace": 100,
        "score_std": 10,
    }

    away_stats = {
        "elo_rating": request.away_elo,
        "recent_win_pct": request.away_recent_win_pct,
        "away_win_pct": 0.45,  # Default
        "offensive_rating": 100,
        "defensive_rating": 100,
        "pace": 100,
        "score_std": 10,
    }

    game_context = {
        "home_rest_days": request.home_rest_days,
        "away_rest_days": request.away_rest_days,
        "away_travel_miles": request.away_travel_miles,
        "is_primetime": request.is_primetime,
        "h2h_home_win_pct": 0.5,
        "h2h_total_games": 0,
    }

    factor_scores = {
        "line_movement": request.line_movement_score,
        "coach_dna": request.coach_dna_score,
        "situational": request.situational_score,
        "weather": request.weather_score,
        "officials": request.officials_score,
        "public_fade": request.public_fade_score,
        "elo": request.elo_score,
        "social": request.social_score,
    }

    prediction = predict_game(
        sport=request.sport,
        home_team=request.home_team,
        away_team=request.away_team,
        home_stats=home_stats,
        away_stats=away_stats,
        game_context=game_context,
        factor_scores=factor_scores,
    )

    return {
        "game": {
            "sport": request.sport,
            "home_team": request.home_team,
            "away_team": request.away_team,
        },
        "prediction": prediction["prediction"],
        "recommended_side": prediction["recommended_side"],
        "edge_pct": round(prediction["edge"], 2),
        "confidence": round(prediction["confidence"], 3),
        "components": prediction["components"],
        "model_version": prediction["model_version"],
    }


@router.get("/predict/game/{game_id}")
async def predict_by_game_id(
    game_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Get neural ensemble prediction for a game by ID.

    Automatically loads team stats and game context from database.
    """
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Get teams
    home_team = db.query(Team).filter(Team.name == game.home_team).first()
    away_team = db.query(Team).filter(Team.name == game.away_team).first()

    home_stats = {
        "elo_rating": home_team.rating if home_team else 1500,
        "recent_win_pct": 0.5,
        "home_win_pct": 0.55,
        "offensive_rating": 100,
        "defensive_rating": 100,
        "pace": 100,
        "score_std": 10,
    }

    away_stats = {
        "elo_rating": away_team.rating if away_team else 1500,
        "recent_win_pct": 0.5,
        "away_win_pct": 0.45,
        "offensive_rating": 100,
        "defensive_rating": 100,
        "pace": 100,
        "score_std": 10,
    }

    game_context = {
        "home_rest_days": 3,
        "away_rest_days": 3,
        "away_travel_miles": 500,
        "is_primetime": False,
        "h2h_home_win_pct": 0.5,
        "h2h_total_games": 0,
    }

    # Default factor scores
    factor_scores = {
        "line_movement": 50,
        "coach_dna": 50,
        "situational": 50,
        "weather": 50,
        "officials": 50,
        "public_fade": 50,
        "elo": 50,
        "social": 50,
    }

    # Get game history for LSTM
    home_history = _get_team_game_history(db, game.home_team, game.sport, limit=10)
    away_history = _get_team_game_history(db, game.away_team, game.sport, limit=10)

    model = ModelManager.get_active_model()
    prediction = model.predict(
        sport=game.sport,
        home_team_stats=home_stats,
        away_team_stats=away_stats,
        game_context=game_context,
        factor_scores=factor_scores,
        home_game_history=home_history,
        away_game_history=away_history,
    )

    return {
        "game_id": game_id,
        "game": {
            "sport": game.sport,
            "home_team": game.home_team,
            "away_team": game.away_team,
            "game_time": game.game_time.isoformat() if game.game_time else None,
        },
        "prediction": prediction["prediction"],
        "recommended_side": prediction["recommended_side"],
        "edge_pct": round(prediction["edge"], 2),
        "confidence": round(prediction["confidence"], 3),
        "components": prediction["components"],
        "model_version": prediction["model_version"],
    }


@router.post("/compare")
async def compare_models(
    request: GamePredictionRequest,
    user: User = Depends(require_auth)
):
    """
    Compare predictions from all model components.

    Shows how each component (feedforward, LSTM, ELO) predicts differently.
    """
    home_stats = {
        "elo_rating": request.home_elo,
        "recent_win_pct": request.home_recent_win_pct,
        "home_win_pct": 0.55,
        "offensive_rating": 100,
        "defensive_rating": 100,
        "pace": 100,
        "score_std": 10,
    }

    away_stats = {
        "elo_rating": request.away_elo,
        "recent_win_pct": request.away_recent_win_pct,
        "away_win_pct": 0.45,
        "offensive_rating": 100,
        "defensive_rating": 100,
        "pace": 100,
        "score_std": 10,
    }

    game_context = {
        "home_rest_days": request.home_rest_days,
        "away_rest_days": request.away_rest_days,
        "away_travel_miles": request.away_travel_miles,
        "is_primetime": request.is_primetime,
        "h2h_home_win_pct": 0.5,
        "h2h_total_games": 0,
    }

    factor_scores = {
        "line_movement": request.line_movement_score,
        "coach_dna": request.coach_dna_score,
        "situational": request.situational_score,
        "weather": request.weather_score,
        "officials": request.officials_score,
        "public_fade": request.public_fade_score,
        "elo": request.elo_score,
        "social": request.social_score,
    }

    comparison = get_model_comparison(
        sport=request.sport,
        home_stats=home_stats,
        away_stats=away_stats,
        game_context=game_context,
        factor_scores=factor_scores,
    )

    return {
        "game": {
            "sport": request.sport,
            "home_team": request.home_team,
            "away_team": request.away_team,
        },
        "comparison": comparison,
        "analysis": _analyze_model_differences(comparison),
    }


# =============================================================================
# Model Management Endpoints
# =============================================================================

@router.get("/model/info")
async def get_model_info(user: User = Depends(require_auth)):
    """
    Get information about the active neural ensemble model.

    Includes version, configuration, and recent accuracy metrics.
    """
    return ModelManager.get_model_info()


@router.get("/model/weights")
async def get_ensemble_weights(user: User = Depends(require_auth)):
    """
    Get current ensemble weights for model components.
    """
    model = ModelManager.get_active_model()
    return {
        "weights": model.ensemble_weights,
        "description": {
            "feedforward": "Static feature network (team stats, factors)",
            "lstm": "Time series network (recent game form)",
            "elo": "Traditional ELO rating baseline",
        }
    }


@router.put("/model/weights")
async def update_ensemble_weights(
    weights: ModelWeightsUpdate,
    user: User = Depends(require_auth)
):
    """
    Update ensemble weights for model components.

    Weights must sum to 1.0.
    """
    total = weights.feedforward_weight + weights.lstm_weight + weights.elo_weight
    if abs(total - 1.0) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Weights must sum to 1.0, got {total}"
        )

    model = ModelManager.get_active_model()
    model.ensemble_weights = {
        "feedforward": weights.feedforward_weight,
        "lstm": weights.lstm_weight,
        "elo": weights.elo_weight,
    }

    return {
        "message": "Weights updated successfully",
        "new_weights": model.ensemble_weights,
    }


@router.get("/model/list")
async def list_models(user: User = Depends(require_auth)):
    """
    List all registered models.
    """
    return {
        "models": ModelManager.list_models(),
        "active_version": ModelManager.get_active_model().version,
    }


@router.post("/model/save")
async def save_model(
    name: str = Query(..., description="Model name"),
    description: str = Query("", description="Model description"),
    user: User = Depends(require_auth)
):
    """
    Save the current model to disk.
    """
    model = ModelManager.get_active_model()
    path = model.save()
    model_id = ModelManager.register_model(model, name, description)

    return {
        "message": "Model saved successfully",
        "model_id": model_id,
        "path": path,
        "version": model.version,
    }


# =============================================================================
# Training Endpoints
# =============================================================================

@router.post("/train")
async def trigger_training(
    request: TrainingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Trigger model training on historical data.

    Training runs in the background. Check /model/info for progress.
    """
    # Gather training data
    query = db.query(HistoricalGameResult)
    if request.sport:
        query = query.filter(HistoricalGameResult.sport == request.sport.upper())

    games = query.order_by(HistoricalGameResult.game_date.desc()).limit(request.max_games).all()

    if len(games) < 100:
        raise HTTPException(
            status_code=400,
            detail=f"Need at least 100 games for training, found {len(games)}"
        )

    # Prepare training data
    training_data = _prepare_training_data(db, games)

    # Run training in background
    background_tasks.add_task(
        _run_training,
        training_data,
        request.validation_split
    )

    return {
        "message": "Training started",
        "games_to_train": len(games),
        "sport": request.sport or "ALL",
        "validation_split": request.validation_split,
    }


@router.get("/train/status")
async def get_training_status(user: User = Depends(require_auth)):
    """
    Get status of model training.
    """
    model = ModelManager.get_active_model()
    return {
        "trained_on_games": model.trained_on_games,
        "accuracy_history": model.accuracy_history[-20:],
        "current_accuracy": model.accuracy_history[-1] if model.accuracy_history else None,
        "version": model.version,
    }


# =============================================================================
# Feature Engineering Endpoints
# =============================================================================

@router.get("/features/static")
async def get_static_feature_info():
    """
    Get information about static features used by the feedforward network.
    """
    return {
        "total_features": 24,
        "feature_groups": [
            {
                "name": "Team Strength",
                "features": ["elo_diff", "home_elo_normalized"],
                "count": 2,
            },
            {
                "name": "Recent Form",
                "features": ["home_recent_win_pct", "away_recent_win_pct"],
                "count": 2,
            },
            {
                "name": "Head-to-Head",
                "features": ["h2h_home_win_pct", "h2h_total_games_normalized"],
                "count": 2,
            },
            {
                "name": "Rest/Travel",
                "features": ["home_rest", "away_rest", "travel_normalized"],
                "count": 3,
            },
            {
                "name": "Home/Away Split",
                "features": ["home_home_record", "away_away_record"],
                "count": 2,
            },
            {
                "name": "8-Factor Scores",
                "features": [
                    "line_movement", "coach_dna", "situational", "weather",
                    "officials", "public_fade", "elo", "social"
                ],
                "count": 8,
            },
            {
                "name": "Efficiency Metrics",
                "features": ["off_diff", "def_diff", "pace", "consistency"],
                "count": 4,
            },
            {
                "name": "Context",
                "features": ["is_primetime"],
                "count": 1,
            },
        ]
    }


@router.get("/features/sequence")
async def get_sequence_feature_info():
    """
    Get information about sequence features used by the LSTM network.
    """
    return {
        "sequence_length": 10,
        "features_per_game": 8,
        "features": [
            {"name": "win_loss", "description": "Game outcome (1=win, 0=loss, 0.5=unknown)"},
            {"name": "margin", "description": "Score margin normalized [-30, 30]"},
            {"name": "total_points", "description": "Total points normalized [30, 250]"},
            {"name": "is_home", "description": "Home/away indicator"},
            {"name": "rest_days", "description": "Rest days normalized [0, 7]"},
            {"name": "covered_spread", "description": "ATS result"},
            {"name": "went_over", "description": "O/U result"},
            {"name": "opponent_elo", "description": "Opponent strength normalized"},
        ]
    }


# =============================================================================
# Demo Endpoint
# =============================================================================

@router.get("/demo")
async def get_demo_prediction():
    """
    Get a demo neural ensemble prediction (no auth required).

    Shows sample output with all model components.
    """
    home_stats = {
        "elo_rating": 1620,
        "recent_win_pct": 0.7,
        "home_win_pct": 0.65,
        "offensive_rating": 112,
        "defensive_rating": 105,
        "pace": 100,
        "score_std": 8,
    }

    away_stats = {
        "elo_rating": 1580,
        "recent_win_pct": 0.6,
        "away_win_pct": 0.45,
        "offensive_rating": 108,
        "defensive_rating": 110,
        "pace": 98,
        "score_std": 12,
    }

    game_context = {
        "home_rest_days": 7,
        "away_rest_days": 3,
        "away_travel_miles": 1500,
        "is_primetime": True,
        "h2h_home_win_pct": 0.6,
        "h2h_total_games": 10,
    }

    factor_scores = {
        "line_movement": 65,
        "coach_dna": 58,
        "situational": 70,
        "weather": 50,
        "officials": 52,
        "public_fade": 55,
        "elo": 60,
        "social": 48,
    }

    prediction = predict_game(
        sport="NFL",
        home_team="Buffalo Bills",
        away_team="Miami Dolphins",
        home_stats=home_stats,
        away_stats=away_stats,
        game_context=game_context,
        factor_scores=factor_scores,
    )

    return {
        "demo": True,
        "description": "Sample NFL game prediction using neural ensemble",
        "game": {
            "sport": "NFL",
            "home_team": "Buffalo Bills",
            "away_team": "Miami Dolphins",
        },
        "inputs": {
            "home_elo": 1620,
            "away_elo": 1580,
            "home_rest_days": 7,
            "away_rest_days": 3,
            "factor_average": 57.25,
        },
        "prediction": prediction["prediction"],
        "recommended_side": prediction["recommended_side"],
        "edge_pct": round(prediction["edge"], 2),
        "confidence": round(prediction["confidence"], 3),
        "components": prediction["components"],
        "model_version": prediction["model_version"],
    }


# =============================================================================
# Helper Functions
# =============================================================================

def _get_team_game_history(
    db: Session,
    team_name: str,
    sport: str,
    limit: int = 10
) -> List[dict]:
    """Get recent game history for LSTM input."""
    games = db.query(HistoricalGameResult).filter(
        (HistoricalGameResult.home_team == team_name) |
        (HistoricalGameResult.away_team == team_name),
        HistoricalGameResult.sport == sport.upper()
    ).order_by(HistoricalGameResult.game_date.desc()).limit(limit).all()

    history = []
    for game in reversed(games):  # Oldest first
        is_home = game.home_team == team_name
        team_score = game.home_score if is_home else game.away_score
        opp_score = game.away_score if is_home else game.home_score

        history.append({
            "won": team_score > opp_score,
            "margin": team_score - opp_score,
            "total_points": team_score + opp_score,
            "is_home": is_home,
            "rest_days": 3,  # Default
            "covered_spread": None,
            "went_over": None,
            "opponent_elo": 1500,
        })

    return history


def _prepare_training_data(db: Session, games: List[HistoricalGameResult]) -> List[dict]:
    """Prepare training data from historical games."""
    training_data = []

    for game in games:
        # Determine outcome
        if game.home_score > game.away_score:
            outcome = "home"
        elif game.away_score > game.home_score:
            outcome = "away"
        else:
            outcome = "draw"

        training_data.append({
            "sport": game.sport,
            "home_team_stats": {
                "elo_rating": 1500,
                "recent_win_pct": 0.5,
            },
            "away_team_stats": {
                "elo_rating": 1500,
                "recent_win_pct": 0.5,
            },
            "game_context": {
                "home_rest_days": 3,
                "away_rest_days": 3,
                "away_travel_miles": 500,
            },
            "factor_scores": {
                "line_movement": 50,
                "coach_dna": 50,
                "situational": 50,
                "weather": 50,
                "officials": 50,
                "public_fade": 50,
                "elo": 50,
                "social": 50,
            },
            "home_game_history": [],
            "away_game_history": [],
            "outcome": outcome,
        })

    return training_data


def _run_training(training_data: List[dict], validation_split: float):
    """Run model training (background task)."""
    from app.utils.logging import get_logger
    logger = get_logger(__name__)

    try:
        logger.info(f"Starting training on {len(training_data)} games")
        model = train_ensemble(training_data, validation_split)
        model.save()
        ModelManager.set_active_model(model)
        logger.info("Training complete, new model activated")
    except Exception as e:
        logger.error(f"Training failed: {e}")


def _analyze_model_differences(comparison: dict) -> dict:
    """Analyze differences between model predictions."""
    components = ["feedforward", "lstm", "elo"]
    home_probs = [comparison[c]["home_win"] for c in components]
    away_probs = [comparison[c]["away_win"] for c in components]

    home_spread = max(home_probs) - min(home_probs)
    away_spread = max(away_probs) - min(away_probs)

    # Find most confident model
    max_conf_idx = 0
    max_conf = 0
    for i, c in enumerate(components):
        conf = max(comparison[c]["home_win"], comparison[c]["away_win"])
        if conf > max_conf:
            max_conf = conf
            max_conf_idx = i

    return {
        "spread": {
            "home_win": round(home_spread, 3),
            "away_win": round(away_spread, 3),
        },
        "most_confident_model": components[max_conf_idx],
        "agreement_level": comparison["model_agreement"],
        "recommendation": (
            "High confidence - models agree"
            if comparison["model_agreement"] == "unanimous"
            else (
                "Moderate confidence - majority agrees"
                if comparison["model_agreement"] == "majority"
                else "Low confidence - models disagree"
            )
        ),
    }
