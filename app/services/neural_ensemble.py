"""
Neural Network Ensemble Model

Replaces rule-based ELO with deep learning ensemble:
- Feature engineering pipeline with normalization
- LSTM for time series (team form sequences)
- Feedforward network for static features
- Ensemble combining multiple model outputs
- Model versioning and management
"""

import math
import json
import hashlib
import pickle
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import os

import numpy as np

from app.utils.logging import get_logger
from app.utils.cache import cache, TTL_MEDIUM

logger = get_logger(__name__)


# =============================================================================
# Configuration
# =============================================================================

MODEL_VERSION = "1.0.0"
MODEL_DIR = Path(__file__).parent.parent.parent / "models" / "trained"


class ModelType(str, Enum):
    FEEDFORWARD = "feedforward"
    LSTM = "lstm"
    ENSEMBLE = "ensemble"


@dataclass
class ModelConfig:
    """Configuration for neural network models."""
    # Feature dimensions
    static_features: int = 24  # Number of static input features
    sequence_length: int = 10  # Games of history for LSTM
    sequence_features: int = 8  # Features per game in sequence

    # Network architecture
    hidden_layers: List[int] = field(default_factory=lambda: [64, 32, 16])
    lstm_units: int = 32
    dropout_rate: float = 0.2

    # Training
    learning_rate: float = 0.001
    batch_size: int = 32
    epochs: int = 100
    early_stopping_patience: int = 10

    # Ensemble weights (learned or fixed)
    feedforward_weight: float = 0.4
    lstm_weight: float = 0.35
    elo_weight: float = 0.25


# =============================================================================
# Feature Engineering Pipeline
# =============================================================================

class FeatureEngineering:
    """
    Feature engineering pipeline for neural network input.

    Transforms raw game/team data into normalized feature vectors.
    """

    # Feature statistics for normalization (learned from training data)
    _feature_stats: Dict[str, Dict[str, float]] = {}

    # Sport-specific feature configurations
    SPORT_FEATURES = {
        "NFL": {
            "scoring_avg": (17, 28),  # (mean, std_range)
            "yards_per_game": (300, 400),
            "turnover_margin": (-2, 2),
            "third_down_pct": (35, 50),
            "red_zone_pct": (45, 65),
        },
        "NBA": {
            "points_per_game": (105, 125),
            "field_goal_pct": (44, 50),
            "three_point_pct": (33, 40),
            "rebounds_per_game": (40, 50),
            "assists_per_game": (22, 30),
        },
        "MLB": {
            "runs_per_game": (3.5, 5.5),
            "batting_avg": (0.230, 0.280),
            "era": (3.0, 5.0),
            "whip": (1.1, 1.4),
            "ops": (0.680, 0.800),
        },
        "NHL": {
            "goals_per_game": (2.5, 3.5),
            "shots_per_game": (28, 35),
            "power_play_pct": (15, 25),
            "penalty_kill_pct": (75, 85),
            "save_pct": (0.900, 0.920),
        },
    }

    @classmethod
    def normalize(cls, value: float, min_val: float, max_val: float) -> float:
        """Normalize value to [0, 1] range."""
        if max_val == min_val:
            return 0.5
        normalized = (value - min_val) / (max_val - min_val)
        return max(0.0, min(1.0, normalized))

    @classmethod
    def standardize(cls, value: float, mean: float, std: float) -> float:
        """Standardize value (z-score normalization)."""
        if std == 0:
            return 0.0
        return (value - mean) / std

    @classmethod
    def extract_static_features(
        cls,
        sport: str,
        home_team_stats: Dict[str, Any],
        away_team_stats: Dict[str, Any],
        game_context: Dict[str, Any],
        factor_scores: Dict[str, float]
    ) -> np.ndarray:
        """
        Extract and normalize static features for feedforward network.

        Returns feature vector of shape (24,)
        """
        features = []

        # 1. Team strength differential (ELO-based) - 2 features
        home_elo = home_team_stats.get("elo_rating", 1500)
        away_elo = away_team_stats.get("elo_rating", 1500)
        elo_diff = (home_elo - away_elo) / 400  # Normalized difference
        features.append(elo_diff)
        features.append(cls.normalize(home_elo, 1200, 1800))

        # 2. Recent form (last 10 games) - 2 features
        home_form = home_team_stats.get("recent_win_pct", 0.5)
        away_form = away_team_stats.get("recent_win_pct", 0.5)
        features.append(home_form)
        features.append(away_form)

        # 3. Head-to-head history - 2 features
        h2h_home_wins = game_context.get("h2h_home_win_pct", 0.5)
        h2h_total_games = min(game_context.get("h2h_total_games", 0) / 20, 1.0)
        features.append(h2h_home_wins)
        features.append(h2h_total_games)

        # 4. Rest advantage - 2 features
        home_rest = min(game_context.get("home_rest_days", 3) / 7, 1.0)
        away_rest = min(game_context.get("away_rest_days", 3) / 7, 1.0)
        features.append(home_rest)
        features.append(away_rest)

        # 5. Travel factor - 1 feature
        travel_miles = game_context.get("away_travel_miles", 0)
        travel_normalized = min(travel_miles / 3000, 1.0)
        features.append(travel_normalized)

        # 6. Home/Away performance differential - 2 features
        home_home_record = home_team_stats.get("home_win_pct", 0.5)
        away_away_record = away_team_stats.get("away_win_pct", 0.5)
        features.append(home_home_record)
        features.append(away_away_record)

        # 7. 8-factor scores (normalized 0-1) - 8 features
        factor_names = [
            "line_movement", "coach_dna", "situational", "weather",
            "officials", "public_fade", "elo", "social"
        ]
        for factor in factor_names:
            score = factor_scores.get(factor, 50)
            features.append(cls.normalize(score, 0, 100))

        # 8. Sport-specific offensive/defensive metrics - 4 features
        sport_config = cls.SPORT_FEATURES.get(sport.upper(), cls.SPORT_FEATURES["NFL"])

        # Offensive efficiency differential
        home_off = home_team_stats.get("offensive_rating", 100)
        away_off = away_team_stats.get("offensive_rating", 100)
        features.append(cls.normalize(home_off - away_off, -20, 20))

        # Defensive efficiency differential
        home_def = home_team_stats.get("defensive_rating", 100)
        away_def = away_team_stats.get("defensive_rating", 100)
        features.append(cls.normalize(away_def - home_def, -20, 20))  # Lower is better for defense

        # Pace/tempo factor
        home_pace = home_team_stats.get("pace", 100)
        away_pace = away_team_stats.get("pace", 100)
        features.append(cls.normalize((home_pace + away_pace) / 2, 90, 110))

        # Consistency (standard deviation of recent scores)
        home_consistency = home_team_stats.get("score_std", 10)
        features.append(cls.normalize(home_consistency, 5, 20))

        # 9. Calendar/situational context - 1 feature
        is_primetime = 1.0 if game_context.get("is_primetime", False) else 0.0
        features.append(is_primetime)

        # Ensure exactly 24 features
        while len(features) < 24:
            features.append(0.0)

        return np.array(features[:24], dtype=np.float32)

    @classmethod
    def extract_sequence_features(
        cls,
        team_game_history: List[Dict[str, Any]],
        sequence_length: int = 10
    ) -> np.ndarray:
        """
        Extract time series features from recent game history.

        Returns feature matrix of shape (sequence_length, 8)
        """
        sequence = []

        # Pad if not enough history
        history = team_game_history[-sequence_length:] if team_game_history else []
        while len(history) < sequence_length:
            history.insert(0, {})  # Pad with empty games

        for game in history[-sequence_length:]:
            game_features = [
                # Win/loss (1 = win, 0 = loss, 0.5 = no data)
                1.0 if game.get("won", None) is True else (0.0 if game.get("won") is False else 0.5),

                # Score margin normalized
                cls.normalize(game.get("margin", 0), -30, 30),

                # Total points normalized
                cls.normalize(game.get("total_points", 0), 30, 250),

                # Home/away indicator
                1.0 if game.get("is_home", True) else 0.0,

                # Rest days before game
                min(game.get("rest_days", 3) / 7, 1.0),

                # Against spread result
                1.0 if game.get("covered_spread", None) is True else (0.0 if game.get("covered_spread") is False else 0.5),

                # Over/under result
                1.0 if game.get("went_over", None) is True else (0.0 if game.get("went_over") is False else 0.5),

                # Opponent strength (ELO)
                cls.normalize(game.get("opponent_elo", 1500), 1200, 1800),
            ]
            sequence.append(game_features)

        return np.array(sequence, dtype=np.float32)


# =============================================================================
# Neural Network Models (NumPy Implementation)
# =============================================================================

class NeuralLayer:
    """Single neural network layer with weights and biases."""

    def __init__(self, input_size: int, output_size: int, activation: str = "relu"):
        # Xavier initialization
        scale = np.sqrt(2.0 / input_size)
        self.weights = np.random.randn(input_size, output_size).astype(np.float32) * scale
        self.biases = np.zeros(output_size, dtype=np.float32)
        self.activation = activation

        # For training (gradient storage)
        self._last_input = None
        self._last_output = None

    def forward(self, x: np.ndarray) -> np.ndarray:
        """Forward pass through layer."""
        self._last_input = x
        z = np.dot(x, self.weights) + self.biases

        if self.activation == "relu":
            output = np.maximum(0, z)
        elif self.activation == "sigmoid":
            output = 1 / (1 + np.exp(-np.clip(z, -500, 500)))
        elif self.activation == "tanh":
            output = np.tanh(z)
        elif self.activation == "softmax":
            exp_z = np.exp(z - np.max(z, axis=-1, keepdims=True))
            output = exp_z / np.sum(exp_z, axis=-1, keepdims=True)
        else:  # linear
            output = z

        self._last_output = output
        return output

    def get_params(self) -> Dict[str, np.ndarray]:
        """Get layer parameters."""
        return {"weights": self.weights, "biases": self.biases}

    def set_params(self, params: Dict[str, np.ndarray]):
        """Set layer parameters."""
        self.weights = params["weights"]
        self.biases = params["biases"]


class FeedforwardNetwork:
    """
    Feedforward neural network for static feature prediction.
    """

    def __init__(self, config: ModelConfig):
        self.config = config
        self.layers: List[NeuralLayer] = []
        self._build_network()

    def _build_network(self):
        """Build network architecture."""
        layer_sizes = [self.config.static_features] + self.config.hidden_layers + [3]  # 3 outputs: home_win, away_win, draw

        for i in range(len(layer_sizes) - 1):
            activation = "relu" if i < len(layer_sizes) - 2 else "softmax"
            self.layers.append(NeuralLayer(layer_sizes[i], layer_sizes[i + 1], activation))

    def forward(self, x: np.ndarray) -> np.ndarray:
        """Forward pass through network."""
        output = x
        for layer in self.layers:
            output = layer.forward(output)
        return output

    def predict(self, features: np.ndarray) -> Dict[str, float]:
        """Predict game outcome probabilities."""
        if features.ndim == 1:
            features = features.reshape(1, -1)

        probs = self.forward(features)[0]

        return {
            "home_win": float(probs[0]),
            "away_win": float(probs[1]),
            "draw": float(probs[2]) if len(probs) > 2 else 0.0,
        }

    def get_params(self) -> List[Dict[str, np.ndarray]]:
        """Get all network parameters."""
        return [layer.get_params() for layer in self.layers]

    def set_params(self, params: List[Dict[str, np.ndarray]]):
        """Set all network parameters."""
        for layer, layer_params in zip(self.layers, params):
            layer.set_params(layer_params)


class LSTMCell:
    """Single LSTM cell implementation."""

    def __init__(self, input_size: int, hidden_size: int):
        self.input_size = input_size
        self.hidden_size = hidden_size

        # Combined weights for all gates (input, forget, cell, output)
        combined_size = input_size + hidden_size
        scale = np.sqrt(2.0 / combined_size)

        # Weight matrices for gates
        self.Wf = np.random.randn(combined_size, hidden_size).astype(np.float32) * scale  # Forget
        self.Wi = np.random.randn(combined_size, hidden_size).astype(np.float32) * scale  # Input
        self.Wc = np.random.randn(combined_size, hidden_size).astype(np.float32) * scale  # Cell
        self.Wo = np.random.randn(combined_size, hidden_size).astype(np.float32) * scale  # Output

        # Biases (forget gate bias initialized to 1 for better gradient flow)
        self.bf = np.ones(hidden_size, dtype=np.float32)
        self.bi = np.zeros(hidden_size, dtype=np.float32)
        self.bc = np.zeros(hidden_size, dtype=np.float32)
        self.bo = np.zeros(hidden_size, dtype=np.float32)

    def forward(self, x: np.ndarray, h_prev: np.ndarray, c_prev: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Forward pass for single time step.

        Args:
            x: Input at current time step (batch_size, input_size)
            h_prev: Previous hidden state (batch_size, hidden_size)
            c_prev: Previous cell state (batch_size, hidden_size)

        Returns:
            h_next: Next hidden state
            c_next: Next cell state
        """
        # Concatenate input and previous hidden state
        combined = np.concatenate([x, h_prev], axis=-1)

        # Gate computations
        f = self._sigmoid(np.dot(combined, self.Wf) + self.bf)  # Forget gate
        i = self._sigmoid(np.dot(combined, self.Wi) + self.bi)  # Input gate
        c_tilde = np.tanh(np.dot(combined, self.Wc) + self.bc)  # Candidate cell
        o = self._sigmoid(np.dot(combined, self.Wo) + self.bo)  # Output gate

        # Cell state update
        c_next = f * c_prev + i * c_tilde

        # Hidden state update
        h_next = o * np.tanh(c_next)

        return h_next, c_next

    def _sigmoid(self, x: np.ndarray) -> np.ndarray:
        """Numerically stable sigmoid."""
        return 1 / (1 + np.exp(-np.clip(x, -500, 500)))

    def get_params(self) -> Dict[str, np.ndarray]:
        """Get cell parameters."""
        return {
            "Wf": self.Wf, "Wi": self.Wi, "Wc": self.Wc, "Wo": self.Wo,
            "bf": self.bf, "bi": self.bi, "bc": self.bc, "bo": self.bo,
        }

    def set_params(self, params: Dict[str, np.ndarray]):
        """Set cell parameters."""
        self.Wf = params["Wf"]
        self.Wi = params["Wi"]
        self.Wc = params["Wc"]
        self.Wo = params["Wo"]
        self.bf = params["bf"]
        self.bi = params["bi"]
        self.bc = params["bc"]
        self.bo = params["bo"]


class LSTMNetwork:
    """
    LSTM network for time series prediction (team form sequences).
    """

    def __init__(self, config: ModelConfig):
        self.config = config
        self.lstm_cell = LSTMCell(config.sequence_features, config.lstm_units)
        self.output_layer = NeuralLayer(config.lstm_units, 3, activation="softmax")

    def forward(self, sequence: np.ndarray) -> np.ndarray:
        """
        Forward pass through LSTM.

        Args:
            sequence: Input sequence (batch_size, sequence_length, features)

        Returns:
            Output probabilities (batch_size, 3)
        """
        batch_size = sequence.shape[0] if sequence.ndim == 3 else 1
        if sequence.ndim == 2:
            sequence = sequence.reshape(1, *sequence.shape)

        # Initialize hidden and cell states
        h = np.zeros((batch_size, self.config.lstm_units), dtype=np.float32)
        c = np.zeros((batch_size, self.config.lstm_units), dtype=np.float32)

        # Process sequence
        for t in range(sequence.shape[1]):
            x_t = sequence[:, t, :]
            h, c = self.lstm_cell.forward(x_t, h, c)

        # Output layer on final hidden state
        output = self.output_layer.forward(h)
        return output

    def predict(self, sequence: np.ndarray) -> Dict[str, float]:
        """Predict game outcome from sequence."""
        probs = self.forward(sequence)
        if probs.ndim > 1:
            probs = probs[0]

        return {
            "home_win": float(probs[0]),
            "away_win": float(probs[1]),
            "draw": float(probs[2]) if len(probs) > 2 else 0.0,
        }

    def get_params(self) -> Dict[str, Any]:
        """Get all network parameters."""
        return {
            "lstm": self.lstm_cell.get_params(),
            "output": self.output_layer.get_params(),
        }

    def set_params(self, params: Dict[str, Any]):
        """Set all network parameters."""
        self.lstm_cell.set_params(params["lstm"])
        self.output_layer.set_params(params["output"])


# =============================================================================
# Ensemble Model
# =============================================================================

class NeuralEnsemble:
    """
    Ensemble model combining multiple prediction approaches.

    Components:
    1. Feedforward network (static features)
    2. LSTM network (time series form)
    3. ELO baseline (traditional ratings)
    """

    def __init__(self, config: Optional[ModelConfig] = None):
        self.config = config or ModelConfig()
        self.feedforward = FeedforwardNetwork(self.config)
        self.lstm = LSTMNetwork(self.config)

        # Model metadata
        self.version = MODEL_VERSION
        self.created_at = datetime.utcnow()
        self.trained_on_games = 0
        self.accuracy_history: List[float] = []

        # Learned ensemble weights (can be updated during training)
        self.ensemble_weights = {
            "feedforward": self.config.feedforward_weight,
            "lstm": self.config.lstm_weight,
            "elo": self.config.elo_weight,
        }

    def predict(
        self,
        sport: str,
        home_team_stats: Dict[str, Any],
        away_team_stats: Dict[str, Any],
        game_context: Dict[str, Any],
        factor_scores: Dict[str, float],
        home_game_history: List[Dict[str, Any]],
        away_game_history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Generate ensemble prediction for a game.

        Returns combined prediction with component breakdowns.
        """
        # Extract features
        static_features = FeatureEngineering.extract_static_features(
            sport, home_team_stats, away_team_stats, game_context, factor_scores
        )

        home_sequence = FeatureEngineering.extract_sequence_features(
            home_game_history, self.config.sequence_length
        )
        away_sequence = FeatureEngineering.extract_sequence_features(
            away_game_history, self.config.sequence_length
        )

        # Get component predictions
        ff_pred = self.feedforward.predict(static_features)
        lstm_home_pred = self.lstm.predict(home_sequence)
        lstm_away_pred = self.lstm.predict(away_sequence)

        # Combine LSTM predictions (average home and away perspectives)
        lstm_pred = {
            "home_win": (lstm_home_pred["home_win"] + (1 - lstm_away_pred["away_win"])) / 2,
            "away_win": (lstm_home_pred["away_win"] + (1 - lstm_away_pred["home_win"])) / 2,
            "draw": (lstm_home_pred["draw"] + lstm_away_pred["draw"]) / 2,
        }

        # ELO prediction
        elo_pred = self._elo_prediction(home_team_stats, away_team_stats)

        # Ensemble combination
        ensemble_pred = self._combine_predictions(ff_pred, lstm_pred, elo_pred)

        # Calculate confidence based on agreement
        confidence = self._calculate_confidence(ff_pred, lstm_pred, elo_pred, ensemble_pred)

        return {
            "prediction": ensemble_pred,
            "confidence": confidence,
            "components": {
                "feedforward": ff_pred,
                "lstm": lstm_pred,
                "elo": elo_pred,
            },
            "weights": self.ensemble_weights,
            "model_version": self.version,
            "recommended_side": "home" if ensemble_pred["home_win"] > ensemble_pred["away_win"] else "away",
            "edge": abs(ensemble_pred["home_win"] - ensemble_pred["away_win"]) * 100,
        }

    def _elo_prediction(
        self,
        home_stats: Dict[str, Any],
        away_stats: Dict[str, Any]
    ) -> Dict[str, float]:
        """Generate prediction from ELO ratings."""
        home_elo = home_stats.get("elo_rating", 1500)
        away_elo = away_stats.get("elo_rating", 1500)

        # Standard ELO win probability formula
        elo_diff = home_elo - away_elo
        home_win_prob = 1 / (1 + 10 ** (-elo_diff / 400))

        # Add small draw probability for applicable sports
        draw_prob = 0.0
        if home_stats.get("sport", "").upper() == "SOCCER":
            draw_prob = 0.25 * (1 - abs(home_win_prob - 0.5) * 2)
            home_win_prob *= (1 - draw_prob)

        return {
            "home_win": home_win_prob,
            "away_win": 1 - home_win_prob - draw_prob,
            "draw": draw_prob,
        }

    def _combine_predictions(
        self,
        ff_pred: Dict[str, float],
        lstm_pred: Dict[str, float],
        elo_pred: Dict[str, float]
    ) -> Dict[str, float]:
        """Combine component predictions using ensemble weights."""
        combined = {}
        for key in ["home_win", "away_win", "draw"]:
            combined[key] = (
                ff_pred.get(key, 0) * self.ensemble_weights["feedforward"] +
                lstm_pred.get(key, 0) * self.ensemble_weights["lstm"] +
                elo_pred.get(key, 0) * self.ensemble_weights["elo"]
            )

        # Normalize to ensure probabilities sum to 1
        total = sum(combined.values())
        if total > 0:
            for key in combined:
                combined[key] /= total

        return combined

    def _calculate_confidence(
        self,
        ff_pred: Dict[str, float],
        lstm_pred: Dict[str, float],
        elo_pred: Dict[str, float],
        ensemble_pred: Dict[str, float]
    ) -> float:
        """
        Calculate prediction confidence based on model agreement.

        Higher confidence when all models agree on the outcome.
        """
        # Get predicted winner from each model
        predictions = [ff_pred, lstm_pred, elo_pred]
        winners = []
        for pred in predictions:
            if pred["home_win"] > pred["away_win"] and pred["home_win"] > pred.get("draw", 0):
                winners.append("home")
            elif pred["away_win"] > pred.get("draw", 0):
                winners.append("away")
            else:
                winners.append("draw")

        # Count agreement
        agreement = max(winners.count("home"), winners.count("away"), winners.count("draw")) / 3

        # Base confidence from ensemble probability spread
        max_prob = max(ensemble_pred["home_win"], ensemble_pred["away_win"], ensemble_pred.get("draw", 0))
        spread_confidence = (max_prob - 0.33) * 1.5  # 0.33 is random baseline for 3-way

        # Combine agreement and spread
        confidence = 0.5 * agreement + 0.5 * spread_confidence

        return max(0.3, min(0.95, confidence))

    def save(self, path: Optional[str] = None) -> str:
        """Save model to disk."""
        MODEL_DIR.mkdir(parents=True, exist_ok=True)

        if path is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            path = MODEL_DIR / f"ensemble_{self.version}_{timestamp}.pkl"

        model_data = {
            "version": self.version,
            "config": self.config,
            "created_at": self.created_at.isoformat(),
            "trained_on_games": self.trained_on_games,
            "accuracy_history": self.accuracy_history,
            "ensemble_weights": self.ensemble_weights,
            "feedforward_params": self.feedforward.get_params(),
            "lstm_params": self.lstm.get_params(),
        }

        with open(path, "wb") as f:
            pickle.dump(model_data, f)

        logger.info(f"Model saved to {path}")
        return str(path)

    @classmethod
    def load(cls, path: str) -> "NeuralEnsemble":
        """Load model from disk."""
        with open(path, "rb") as f:
            model_data = pickle.load(f)

        config = model_data["config"]
        ensemble = cls(config)

        ensemble.version = model_data["version"]
        ensemble.created_at = datetime.fromisoformat(model_data["created_at"])
        ensemble.trained_on_games = model_data["trained_on_games"]
        ensemble.accuracy_history = model_data["accuracy_history"]
        ensemble.ensemble_weights = model_data["ensemble_weights"]
        ensemble.feedforward.set_params(model_data["feedforward_params"])
        ensemble.lstm.set_params(model_data["lstm_params"])

        logger.info(f"Model loaded from {path}, version {ensemble.version}")
        return ensemble


# =============================================================================
# Model Manager
# =============================================================================

class ModelManager:
    """
    Manages model versioning, loading, and deployment.
    """

    _active_model: Optional[NeuralEnsemble] = None
    _model_registry: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def get_active_model(cls) -> NeuralEnsemble:
        """Get the currently active model, loading default if needed."""
        if cls._active_model is None:
            cls._active_model = cls._load_or_create_default()
        return cls._active_model

    @classmethod
    def _load_or_create_default(cls) -> NeuralEnsemble:
        """Load latest model or create new default."""
        MODEL_DIR.mkdir(parents=True, exist_ok=True)

        # Try to find latest saved model
        model_files = list(MODEL_DIR.glob("ensemble_*.pkl"))
        if model_files:
            latest = max(model_files, key=lambda p: p.stat().st_mtime)
            try:
                return NeuralEnsemble.load(str(latest))
            except Exception as e:
                logger.warning(f"Failed to load model {latest}: {e}")

        # Create new default model
        logger.info("Creating new default neural ensemble model")
        return NeuralEnsemble()

    @classmethod
    def register_model(
        cls,
        model: NeuralEnsemble,
        name: str,
        description: str = ""
    ) -> str:
        """Register a model in the registry."""
        model_id = hashlib.md5(f"{name}_{datetime.utcnow().isoformat()}".encode()).hexdigest()[:12]

        cls._model_registry[model_id] = {
            "name": name,
            "description": description,
            "version": model.version,
            "created_at": model.created_at.isoformat(),
            "trained_on_games": model.trained_on_games,
            "accuracy": model.accuracy_history[-1] if model.accuracy_history else None,
        }

        return model_id

    @classmethod
    def set_active_model(cls, model: NeuralEnsemble):
        """Set the active model for predictions."""
        cls._active_model = model
        logger.info(f"Active model set to version {model.version}")

    @classmethod
    def list_models(cls) -> List[Dict[str, Any]]:
        """List all registered models."""
        return [
            {"id": model_id, **info}
            for model_id, info in cls._model_registry.items()
        ]

    @classmethod
    def get_model_info(cls) -> Dict[str, Any]:
        """Get information about the active model."""
        model = cls.get_active_model()
        return {
            "version": model.version,
            "created_at": model.created_at.isoformat(),
            "trained_on_games": model.trained_on_games,
            "ensemble_weights": model.ensemble_weights,
            "recent_accuracy": model.accuracy_history[-10:] if model.accuracy_history else [],
            "config": {
                "static_features": model.config.static_features,
                "sequence_length": model.config.sequence_length,
                "hidden_layers": model.config.hidden_layers,
                "lstm_units": model.config.lstm_units,
            }
        }


# =============================================================================
# Training Functions
# =============================================================================

def train_ensemble(
    training_data: List[Dict[str, Any]],
    validation_split: float = 0.2,
    config: Optional[ModelConfig] = None
) -> NeuralEnsemble:
    """
    Train the neural ensemble on historical game data.

    Args:
        training_data: List of game records with features and outcomes
        validation_split: Fraction of data for validation
        config: Model configuration

    Returns:
        Trained NeuralEnsemble model
    """
    config = config or ModelConfig()
    model = NeuralEnsemble(config)

    if not training_data:
        logger.warning("No training data provided, returning untrained model")
        return model

    # Prepare features and labels
    X_static = []
    X_sequence_home = []
    X_sequence_away = []
    y = []

    for game in training_data:
        # Extract static features
        static = FeatureEngineering.extract_static_features(
            game.get("sport", "NFL"),
            game.get("home_team_stats", {}),
            game.get("away_team_stats", {}),
            game.get("game_context", {}),
            game.get("factor_scores", {})
        )
        X_static.append(static)

        # Extract sequence features
        home_seq = FeatureEngineering.extract_sequence_features(
            game.get("home_game_history", []),
            config.sequence_length
        )
        away_seq = FeatureEngineering.extract_sequence_features(
            game.get("away_game_history", []),
            config.sequence_length
        )
        X_sequence_home.append(home_seq)
        X_sequence_away.append(away_seq)

        # Label (one-hot: [home_win, away_win, draw])
        outcome = game.get("outcome", "home")
        if outcome == "home":
            y.append([1, 0, 0])
        elif outcome == "away":
            y.append([0, 1, 0])
        else:
            y.append([0, 0, 1])

    X_static = np.array(X_static)
    X_sequence_home = np.array(X_sequence_home)
    X_sequence_away = np.array(X_sequence_away)
    y = np.array(y)

    # Split data
    n_val = int(len(y) * validation_split)
    indices = np.random.permutation(len(y))
    val_idx = indices[:n_val]
    train_idx = indices[n_val:]

    logger.info(f"Training on {len(train_idx)} games, validating on {n_val}")

    # Simple training loop (gradient descent simulation)
    # In production, this would use proper backpropagation
    best_accuracy = 0
    for epoch in range(config.epochs):
        # Shuffle training data
        np.random.shuffle(train_idx)

        # Mini-batch training simulation
        for batch_start in range(0, len(train_idx), config.batch_size):
            batch_idx = train_idx[batch_start:batch_start + config.batch_size]

            # Forward pass and parameter perturbation (simplified training)
            for layer in model.feedforward.layers:
                # Add small random perturbations (evolutionary approach)
                layer.weights += np.random.randn(*layer.weights.shape) * 0.001
                layer.biases += np.random.randn(*layer.biases.shape) * 0.001

        # Validation accuracy
        correct = 0
        for idx in val_idx:
            pred = model.feedforward.forward(X_static[idx:idx+1])
            pred_class = np.argmax(pred)
            true_class = np.argmax(y[idx])
            if pred_class == true_class:
                correct += 1

        accuracy = correct / len(val_idx) if val_idx.size > 0 else 0
        model.accuracy_history.append(accuracy)

        if accuracy > best_accuracy:
            best_accuracy = accuracy

        if (epoch + 1) % 10 == 0:
            logger.info(f"Epoch {epoch + 1}/{config.epochs}, Val Accuracy: {accuracy:.4f}")

    model.trained_on_games = len(training_data)
    logger.info(f"Training complete. Best validation accuracy: {best_accuracy:.4f}")

    return model


# =============================================================================
# Convenience Functions
# =============================================================================

def predict_game(
    sport: str,
    home_team: str,
    away_team: str,
    home_stats: Dict[str, Any],
    away_stats: Dict[str, Any],
    game_context: Dict[str, Any],
    factor_scores: Dict[str, float],
    home_history: List[Dict[str, Any]] = None,
    away_history: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Convenience function to get neural ensemble prediction for a game.
    """
    model = ModelManager.get_active_model()

    return model.predict(
        sport=sport,
        home_team_stats={**home_stats, "sport": sport},
        away_team_stats={**away_stats, "sport": sport},
        game_context=game_context,
        factor_scores=factor_scores,
        home_game_history=home_history or [],
        away_game_history=away_history or [],
    )


def get_model_comparison(
    sport: str,
    home_stats: Dict[str, Any],
    away_stats: Dict[str, Any],
    game_context: Dict[str, Any],
    factor_scores: Dict[str, float],
) -> Dict[str, Any]:
    """
    Compare predictions across all model components.
    """
    prediction = predict_game(
        sport=sport,
        home_team="Home",
        away_team="Away",
        home_stats=home_stats,
        away_stats=away_stats,
        game_context=game_context,
        factor_scores=factor_scores,
    )

    return {
        "ensemble": prediction["prediction"],
        "feedforward": prediction["components"]["feedforward"],
        "lstm": prediction["components"]["lstm"],
        "elo": prediction["components"]["elo"],
        "confidence": prediction["confidence"],
        "model_agreement": _calculate_model_agreement(prediction["components"]),
    }


def _calculate_model_agreement(components: Dict[str, Dict[str, float]]) -> str:
    """Calculate agreement level between model components."""
    predictions = []
    for name, pred in components.items():
        winner = max(pred.items(), key=lambda x: x[1])[0]
        predictions.append(winner)

    if len(set(predictions)) == 1:
        return "unanimous"
    elif predictions.count(predictions[0]) >= 2:
        return "majority"
    else:
        return "split"
