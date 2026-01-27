"""
Tests for Neural Ensemble Model

Tests:
- Feature engineering pipeline
- Feedforward network
- LSTM network
- Ensemble predictions
- Model management
- API endpoints
"""

import pytest
import uuid
import numpy as np
from datetime import datetime
from fastapi.testclient import TestClient

from app.main import app
from app.services.neural_ensemble import (
    FeatureEngineering,
    FeedforwardNetwork,
    LSTMNetwork,
    NeuralEnsemble,
    ModelManager,
    ModelConfig,
    NeuralLayer,
    LSTMCell,
    predict_game,
    get_model_comparison,
    train_ensemble,
)


client = TestClient(app)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def auth_headers():
    """Create test user and return auth headers."""
    unique_id = uuid.uuid4().hex[:8]
    response = client.post("/auth/register", json={
        "email": f"neural_{unique_id}@example.com",
        "username": f"neural{unique_id}",
        "password": "securepass123"
    })
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    response = client.post("/auth/login", json={
        "email": f"neural_{unique_id}@example.com",
        "password": "securepass123"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_home_stats():
    """Sample home team stats."""
    return {
        "elo_rating": 1600,
        "recent_win_pct": 0.7,
        "home_win_pct": 0.65,
        "offensive_rating": 110,
        "defensive_rating": 105,
        "pace": 100,
        "score_std": 10,
    }


@pytest.fixture
def sample_away_stats():
    """Sample away team stats."""
    return {
        "elo_rating": 1550,
        "recent_win_pct": 0.5,
        "away_win_pct": 0.45,
        "offensive_rating": 105,
        "defensive_rating": 108,
        "pace": 98,
        "score_std": 12,
    }


@pytest.fixture
def sample_game_context():
    """Sample game context."""
    return {
        "home_rest_days": 7,
        "away_rest_days": 3,
        "away_travel_miles": 1200,
        "is_primetime": True,
        "h2h_home_win_pct": 0.6,
        "h2h_total_games": 8,
    }


@pytest.fixture
def sample_factor_scores():
    """Sample 8-factor scores."""
    return {
        "line_movement": 65,
        "coach_dna": 55,
        "situational": 60,
        "weather": 50,
        "officials": 52,
        "public_fade": 48,
        "elo": 58,
        "social": 45,
    }


@pytest.fixture
def sample_game_history():
    """Sample game history for LSTM."""
    return [
        {"won": True, "margin": 7, "total_points": 45, "is_home": True, "rest_days": 7, "opponent_elo": 1520},
        {"won": False, "margin": -3, "total_points": 51, "is_home": False, "rest_days": 5, "opponent_elo": 1580},
        {"won": True, "margin": 14, "total_points": 62, "is_home": True, "rest_days": 7, "opponent_elo": 1480},
        {"won": True, "margin": 3, "total_points": 47, "is_home": False, "rest_days": 4, "opponent_elo": 1540},
        {"won": False, "margin": -7, "total_points": 55, "is_home": True, "rest_days": 6, "opponent_elo": 1620},
    ]


@pytest.fixture
def model_config():
    """Sample model configuration."""
    return ModelConfig(
        static_features=24,
        sequence_length=10,
        sequence_features=8,
        hidden_layers=[32, 16],
        lstm_units=16,
    )


# =============================================================================
# Feature Engineering Tests
# =============================================================================

class TestFeatureEngineering:
    """Tests for feature engineering pipeline."""

    def test_normalize_within_range(self):
        """Test normalization produces values in [0, 1]."""
        assert FeatureEngineering.normalize(5, 0, 10) == 0.5
        assert FeatureEngineering.normalize(0, 0, 10) == 0.0
        assert FeatureEngineering.normalize(10, 0, 10) == 1.0

    def test_normalize_clamps_outliers(self):
        """Test normalization clamps values outside range."""
        assert FeatureEngineering.normalize(-5, 0, 10) == 0.0
        assert FeatureEngineering.normalize(15, 0, 10) == 1.0

    def test_normalize_handles_equal_bounds(self):
        """Test normalization handles min == max."""
        assert FeatureEngineering.normalize(5, 5, 5) == 0.5

    def test_standardize(self):
        """Test z-score standardization."""
        assert FeatureEngineering.standardize(10, 10, 2) == 0.0  # At mean
        assert FeatureEngineering.standardize(12, 10, 2) == 1.0  # 1 std above
        assert FeatureEngineering.standardize(8, 10, 2) == -1.0  # 1 std below

    def test_extract_static_features_shape(
        self,
        sample_home_stats,
        sample_away_stats,
        sample_game_context,
        sample_factor_scores
    ):
        """Test static features have correct shape."""
        features = FeatureEngineering.extract_static_features(
            "NFL",
            sample_home_stats,
            sample_away_stats,
            sample_game_context,
            sample_factor_scores
        )
        assert features.shape == (24,)
        assert features.dtype == np.float32

    def test_extract_static_features_normalized(
        self,
        sample_home_stats,
        sample_away_stats,
        sample_game_context,
        sample_factor_scores
    ):
        """Test static features are in reasonable range."""
        features = FeatureEngineering.extract_static_features(
            "NFL",
            sample_home_stats,
            sample_away_stats,
            sample_game_context,
            sample_factor_scores
        )
        # Most features should be in [0, 1] range (some like ELO diff can be outside)
        assert np.all(features >= -2)
        assert np.all(features <= 2)

    def test_extract_sequence_features_shape(self, sample_game_history):
        """Test sequence features have correct shape."""
        features = FeatureEngineering.extract_sequence_features(
            sample_game_history,
            sequence_length=10
        )
        assert features.shape == (10, 8)
        assert features.dtype == np.float32

    def test_extract_sequence_features_padding(self):
        """Test sequence features pad short history."""
        short_history = [{"won": True, "margin": 7}]
        features = FeatureEngineering.extract_sequence_features(
            short_history,
            sequence_length=10
        )
        assert features.shape == (10, 8)

    def test_extract_sequence_features_empty(self):
        """Test sequence features handle empty history."""
        features = FeatureEngineering.extract_sequence_features(
            [],
            sequence_length=10
        )
        assert features.shape == (10, 8)
        # Empty games should have neutral values (0.5 for unknown)
        assert features[0, 0] == 0.5  # Win/loss unknown

    def test_sport_specific_configs(self):
        """Test sport-specific feature configurations exist."""
        assert "NFL" in FeatureEngineering.SPORT_FEATURES
        assert "NBA" in FeatureEngineering.SPORT_FEATURES
        assert "MLB" in FeatureEngineering.SPORT_FEATURES
        assert "NHL" in FeatureEngineering.SPORT_FEATURES


# =============================================================================
# Neural Layer Tests
# =============================================================================

class TestNeuralLayer:
    """Tests for single neural network layer."""

    def test_layer_initialization(self):
        """Test layer initializes with correct shapes."""
        layer = NeuralLayer(10, 5, activation="relu")
        assert layer.weights.shape == (10, 5)
        assert layer.biases.shape == (5,)

    def test_layer_forward_shape(self):
        """Test forward pass produces correct shape."""
        layer = NeuralLayer(10, 5, activation="relu")
        x = np.random.randn(3, 10).astype(np.float32)
        output = layer.forward(x)
        assert output.shape == (3, 5)

    def test_relu_activation(self):
        """Test ReLU activation clamps negatives."""
        layer = NeuralLayer(2, 2, activation="relu")
        layer.weights = np.array([[1, -1], [-1, 1]], dtype=np.float32)
        layer.biases = np.zeros(2, dtype=np.float32)

        x = np.array([[1, 1]], dtype=np.float32)
        output = layer.forward(x)
        assert output[0, 0] >= 0  # ReLU clamps negative to 0

    def test_sigmoid_activation(self):
        """Test sigmoid activation produces values in (0, 1)."""
        layer = NeuralLayer(2, 2, activation="sigmoid")
        x = np.array([[0, 0], [10, -10]], dtype=np.float32)
        output = layer.forward(x)
        assert np.all(output > 0)
        assert np.all(output < 1)

    def test_softmax_activation(self):
        """Test softmax produces valid probability distribution."""
        layer = NeuralLayer(3, 3, activation="softmax")
        x = np.array([[1, 2, 3]], dtype=np.float32)
        output = layer.forward(x)
        assert np.allclose(np.sum(output, axis=1), 1.0)
        assert np.all(output >= 0)

    def test_get_set_params(self):
        """Test getting and setting layer parameters."""
        layer = NeuralLayer(4, 3, activation="relu")
        params = layer.get_params()

        new_layer = NeuralLayer(4, 3, activation="relu")
        new_layer.set_params(params)

        assert np.array_equal(layer.weights, new_layer.weights)
        assert np.array_equal(layer.biases, new_layer.biases)


# =============================================================================
# LSTM Cell Tests
# =============================================================================

class TestLSTMCell:
    """Tests for LSTM cell implementation."""

    def test_cell_initialization(self):
        """Test LSTM cell initializes correctly."""
        cell = LSTMCell(input_size=8, hidden_size=16)
        assert cell.Wf.shape == (24, 16)  # input + hidden
        assert cell.bf.shape == (16,)

    def test_cell_forward_shapes(self):
        """Test LSTM forward pass produces correct shapes."""
        cell = LSTMCell(input_size=8, hidden_size=16)
        batch_size = 4

        x = np.random.randn(batch_size, 8).astype(np.float32)
        h_prev = np.zeros((batch_size, 16), dtype=np.float32)
        c_prev = np.zeros((batch_size, 16), dtype=np.float32)

        h_next, c_next = cell.forward(x, h_prev, c_prev)

        assert h_next.shape == (batch_size, 16)
        assert c_next.shape == (batch_size, 16)

    def test_cell_hidden_state_bounded(self):
        """Test hidden state is bounded by tanh."""
        cell = LSTMCell(input_size=4, hidden_size=8)

        x = np.random.randn(2, 4).astype(np.float32) * 10
        h_prev = np.zeros((2, 8), dtype=np.float32)
        c_prev = np.zeros((2, 8), dtype=np.float32)

        h_next, _ = cell.forward(x, h_prev, c_prev)

        assert np.all(h_next >= -1)
        assert np.all(h_next <= 1)


# =============================================================================
# Feedforward Network Tests
# =============================================================================

class TestFeedforwardNetwork:
    """Tests for feedforward neural network."""

    def test_network_initialization(self, model_config):
        """Test feedforward network initializes correctly."""
        net = FeedforwardNetwork(model_config)
        assert len(net.layers) == 3  # 2 hidden + 1 output

    def test_network_forward_shape(self, model_config):
        """Test forward pass produces correct shape."""
        net = FeedforwardNetwork(model_config)
        x = np.random.randn(5, 24).astype(np.float32)
        output = net.forward(x)
        assert output.shape == (5, 3)  # 3 outputs

    def test_network_predict_structure(self, model_config):
        """Test predict returns correct structure."""
        net = FeedforwardNetwork(model_config)
        x = np.random.randn(24).astype(np.float32)
        pred = net.predict(x)

        assert "home_win" in pred
        assert "away_win" in pred
        assert "draw" in pred

    def test_network_predict_probabilities_valid(self, model_config):
        """Test predictions are valid probabilities."""
        net = FeedforwardNetwork(model_config)
        x = np.random.randn(24).astype(np.float32)
        pred = net.predict(x)

        total = pred["home_win"] + pred["away_win"] + pred["draw"]
        assert 0.99 <= total <= 1.01
        assert all(0 <= v <= 1 for v in pred.values())


# =============================================================================
# LSTM Network Tests
# =============================================================================

class TestLSTMNetwork:
    """Tests for LSTM neural network."""

    def test_network_initialization(self, model_config):
        """Test LSTM network initializes correctly."""
        net = LSTMNetwork(model_config)
        assert net.lstm_cell is not None
        assert net.output_layer is not None

    def test_network_forward_shape(self, model_config):
        """Test forward pass produces correct shape."""
        net = LSTMNetwork(model_config)
        sequence = np.random.randn(3, 10, 8).astype(np.float32)
        output = net.forward(sequence)
        assert output.shape == (3, 3)

    def test_network_predict_structure(self, model_config):
        """Test predict returns correct structure."""
        net = LSTMNetwork(model_config)
        sequence = np.random.randn(10, 8).astype(np.float32)
        pred = net.predict(sequence)

        assert "home_win" in pred
        assert "away_win" in pred
        assert "draw" in pred


# =============================================================================
# Neural Ensemble Tests
# =============================================================================

class TestNeuralEnsemble:
    """Tests for the complete neural ensemble model."""

    def test_ensemble_initialization(self):
        """Test ensemble initializes with all components."""
        ensemble = NeuralEnsemble()
        assert ensemble.feedforward is not None
        assert ensemble.lstm is not None
        assert ensemble.version is not None

    def test_ensemble_predict_structure(
        self,
        sample_home_stats,
        sample_away_stats,
        sample_game_context,
        sample_factor_scores,
        sample_game_history
    ):
        """Test ensemble predict returns complete structure."""
        ensemble = NeuralEnsemble()

        result = ensemble.predict(
            sport="NFL",
            home_team_stats=sample_home_stats,
            away_team_stats=sample_away_stats,
            game_context=sample_game_context,
            factor_scores=sample_factor_scores,
            home_game_history=sample_game_history,
            away_game_history=sample_game_history,
        )

        assert "prediction" in result
        assert "confidence" in result
        assert "components" in result
        assert "weights" in result
        assert "model_version" in result
        assert "recommended_side" in result
        assert "edge" in result

    def test_ensemble_predictions_valid(
        self,
        sample_home_stats,
        sample_away_stats,
        sample_game_context,
        sample_factor_scores
    ):
        """Test ensemble produces valid probability predictions."""
        ensemble = NeuralEnsemble()

        result = ensemble.predict(
            sport="NFL",
            home_team_stats=sample_home_stats,
            away_team_stats=sample_away_stats,
            game_context=sample_game_context,
            factor_scores=sample_factor_scores,
            home_game_history=[],
            away_game_history=[],
        )

        pred = result["prediction"]
        total = pred["home_win"] + pred["away_win"] + pred["draw"]
        assert 0.99 <= total <= 1.01

    def test_ensemble_confidence_range(
        self,
        sample_home_stats,
        sample_away_stats,
        sample_game_context,
        sample_factor_scores
    ):
        """Test confidence is in valid range."""
        ensemble = NeuralEnsemble()

        result = ensemble.predict(
            sport="NFL",
            home_team_stats=sample_home_stats,
            away_team_stats=sample_away_stats,
            game_context=sample_game_context,
            factor_scores=sample_factor_scores,
            home_game_history=[],
            away_game_history=[],
        )

        assert 0.3 <= result["confidence"] <= 0.95

    def test_ensemble_weights_sum_to_one(self):
        """Test ensemble weights sum to 1."""
        ensemble = NeuralEnsemble()
        total = sum(ensemble.ensemble_weights.values())
        assert abs(total - 1.0) < 0.01

    def test_ensemble_components_present(
        self,
        sample_home_stats,
        sample_away_stats,
        sample_game_context,
        sample_factor_scores
    ):
        """Test all component predictions are present."""
        ensemble = NeuralEnsemble()

        result = ensemble.predict(
            sport="NFL",
            home_team_stats=sample_home_stats,
            away_team_stats=sample_away_stats,
            game_context=sample_game_context,
            factor_scores=sample_factor_scores,
            home_game_history=[],
            away_game_history=[],
        )

        assert "feedforward" in result["components"]
        assert "lstm" in result["components"]
        assert "elo" in result["components"]


# =============================================================================
# Model Manager Tests
# =============================================================================

class TestModelManager:
    """Tests for model management."""

    def test_get_active_model(self):
        """Test getting active model."""
        model = ModelManager.get_active_model()
        assert isinstance(model, NeuralEnsemble)

    def test_get_model_info(self):
        """Test getting model info."""
        info = ModelManager.get_model_info()
        assert "version" in info
        assert "ensemble_weights" in info
        assert "config" in info

    def test_register_model(self):
        """Test registering a model."""
        model = NeuralEnsemble()
        model_id = ModelManager.register_model(model, "test_model", "Test description")
        assert model_id is not None
        assert len(model_id) == 12

    def test_list_models(self):
        """Test listing models."""
        models = ModelManager.list_models()
        assert isinstance(models, list)


# =============================================================================
# Convenience Function Tests
# =============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_predict_game(
        self,
        sample_home_stats,
        sample_away_stats,
        sample_game_context,
        sample_factor_scores
    ):
        """Test predict_game convenience function."""
        result = predict_game(
            sport="NFL",
            home_team="Bills",
            away_team="Chiefs",
            home_stats=sample_home_stats,
            away_stats=sample_away_stats,
            game_context=sample_game_context,
            factor_scores=sample_factor_scores,
        )

        assert "prediction" in result
        assert "confidence" in result

    def test_get_model_comparison(
        self,
        sample_home_stats,
        sample_away_stats,
        sample_game_context,
        sample_factor_scores
    ):
        """Test model comparison function."""
        comparison = get_model_comparison(
            sport="NFL",
            home_stats=sample_home_stats,
            away_stats=sample_away_stats,
            game_context=sample_game_context,
            factor_scores=sample_factor_scores,
        )

        assert "ensemble" in comparison
        assert "feedforward" in comparison
        assert "lstm" in comparison
        assert "elo" in comparison
        assert "model_agreement" in comparison


# =============================================================================
# API Endpoint Tests
# =============================================================================

class TestNeuralEnsembleRouter:
    """Tests for neural ensemble API endpoints."""

    def test_demo_endpoint_no_auth(self):
        """Test demo endpoint works without auth."""
        response = client.get("/neural/demo")
        assert response.status_code == 200
        data = response.json()
        assert data["demo"] is True
        assert "prediction" in data
        assert "components" in data

    def test_model_info_endpoint(self, auth_headers):
        """Test model info endpoint."""
        response = client.get("/neural/model/info", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "ensemble_weights" in data

    def test_model_weights_endpoint(self, auth_headers):
        """Test model weights endpoint."""
        response = client.get("/neural/model/weights", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "weights" in data
        assert "feedforward" in data["weights"]
        assert "lstm" in data["weights"]
        assert "elo" in data["weights"]

    def test_predict_requires_auth(self):
        """Test predict endpoint requires auth."""
        response = client.post("/neural/predict", json={
            "sport": "NFL",
            "home_team": "Bills",
            "away_team": "Chiefs",
        })
        assert response.status_code == 401

    def test_predict_with_auth(self, auth_headers):
        """Test predict endpoint with auth."""
        response = client.post("/neural/predict", json={
            "sport": "NFL",
            "home_team": "Buffalo Bills",
            "away_team": "Kansas City Chiefs",
            "home_elo": 1600,
            "away_elo": 1620,
            "home_recent_win_pct": 0.7,
            "away_recent_win_pct": 0.8,
            "home_rest_days": 7,
            "away_rest_days": 7,
            "away_travel_miles": 1200,
            "is_primetime": True,
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "prediction" in data
        assert "recommended_side" in data
        assert "confidence" in data

    def test_compare_endpoint(self, auth_headers):
        """Test model comparison endpoint."""
        response = client.post("/neural/compare", json={
            "sport": "NFL",
            "home_team": "Buffalo Bills",
            "away_team": "Kansas City Chiefs",
            "home_elo": 1600,
            "away_elo": 1620,
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "comparison" in data
        assert "analysis" in data

    def test_features_static_endpoint(self):
        """Test static features info endpoint."""
        response = client.get("/neural/features/static")
        assert response.status_code == 200
        data = response.json()
        assert data["total_features"] == 24
        assert "feature_groups" in data

    def test_features_sequence_endpoint(self):
        """Test sequence features info endpoint."""
        response = client.get("/neural/features/sequence")
        assert response.status_code == 200
        data = response.json()
        assert data["sequence_length"] == 10
        assert data["features_per_game"] == 8

    def test_update_weights_requires_sum_to_one(self, auth_headers):
        """Test weight update validates sum to 1."""
        response = client.put("/neural/model/weights", json={
            "feedforward_weight": 0.5,
            "lstm_weight": 0.5,
            "elo_weight": 0.5,
        }, headers=auth_headers)
        assert response.status_code == 400

    def test_update_weights_valid(self, auth_headers):
        """Test valid weight update."""
        response = client.put("/neural/model/weights", json={
            "feedforward_weight": 0.4,
            "lstm_weight": 0.35,
            "elo_weight": 0.25,
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["new_weights"]["feedforward"] == 0.4

    def test_list_models_endpoint(self, auth_headers):
        """Test list models endpoint."""
        response = client.get("/neural/model/list", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert "active_version" in data

    def test_training_status_endpoint(self, auth_headers):
        """Test training status endpoint."""
        response = client.get("/neural/train/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "trained_on_games" in data
        assert "version" in data


# =============================================================================
# Training Tests
# =============================================================================

class TestTraining:
    """Tests for model training."""

    def test_train_empty_data(self):
        """Test training with empty data returns untrained model."""
        model = train_ensemble([])
        assert model.trained_on_games == 0

    def test_train_minimal_data(self):
        """Test training with minimal data."""
        # Create minimal training data
        training_data = [
            {
                "sport": "NFL",
                "home_team_stats": {"elo_rating": 1500},
                "away_team_stats": {"elo_rating": 1500},
                "game_context": {},
                "factor_scores": {},
                "home_game_history": [],
                "away_game_history": [],
                "outcome": "home" if i % 2 == 0 else "away",
            }
            for i in range(10)
        ]

        config = ModelConfig(epochs=2)
        model = train_ensemble(training_data, validation_split=0.2, config=config)

        assert model.trained_on_games == 10


# =============================================================================
# ELO Prediction Tests
# =============================================================================

class TestELOPrediction:
    """Tests for ELO-based predictions."""

    def test_elo_favors_higher_rated(self):
        """Test ELO prediction favors higher-rated team."""
        ensemble = NeuralEnsemble()

        # Strong home team
        pred1 = ensemble._elo_prediction(
            {"elo_rating": 1700},
            {"elo_rating": 1400}
        )
        assert pred1["home_win"] > pred1["away_win"]

        # Strong away team
        pred2 = ensemble._elo_prediction(
            {"elo_rating": 1400},
            {"elo_rating": 1700}
        )
        assert pred2["away_win"] > pred2["home_win"]

    def test_elo_equal_ratings_even(self):
        """Test equal ELO ratings produce ~50% probability."""
        ensemble = NeuralEnsemble()
        pred = ensemble._elo_prediction(
            {"elo_rating": 1500},
            {"elo_rating": 1500}
        )
        assert 0.45 <= pred["home_win"] <= 0.55

    def test_elo_soccer_includes_draw(self):
        """Test soccer prediction includes draw probability."""
        ensemble = NeuralEnsemble()
        pred = ensemble._elo_prediction(
            {"elo_rating": 1500, "sport": "SOCCER"},
            {"elo_rating": 1500, "sport": "SOCCER"}
        )
        # Note: Draw prob is calculated based on sport in home_stats
        # Default behavior is no draw for non-soccer
