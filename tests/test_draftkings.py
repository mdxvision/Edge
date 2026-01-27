"""
Tests for DraftKings API Integration

Tests:
- Odds fetching
- Event listing
- Line movement tracking
- Steam move detection
- Market data
- API endpoints
"""

import pytest
import uuid
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.services.draftkings import (
    DraftKingsClient,
    DraftKingsOdds,
    DraftKingsEvent,
    LineMovement,
    get_live_odds,
    get_event_odds,
    get_best_odds,
    get_events,
    get_live_events,
    get_event_details,
    get_line_movements,
    detect_steam_moves,
    detect_reverse_line_movement,
    get_markets,
    get_player_props,
    _american_to_probability,
    _american_to_decimal,
    _decimal_to_american,
    _simulate_odds,
    _simulate_events,
    _simulate_line_movements,
    _simulate_markets,
    SPORT_IDS,
    MARKET_TYPES,
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
        "email": f"draftkings_{unique_id}@example.com",
        "username": f"draftkings{unique_id}",
        "password": "securepass123"
    })
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    response = client.post("/auth/login", json={
        "email": f"draftkings_{unique_id}@example.com",
        "password": "securepass123"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# Client Tests
# =============================================================================

class TestDraftKingsClient:
    """Tests for DraftKings API client."""

    def test_client_initialization(self):
        """Test client initializes correctly."""
        client = DraftKingsClient()
        assert client.base_url is not None

    def test_client_not_configured_without_keys(self):
        """Test client reports not configured without API keys."""
        client = DraftKingsClient(api_key="", api_secret="")
        assert not client.is_configured

    def test_client_configured_with_keys(self):
        """Test client reports configured with API keys."""
        client = DraftKingsClient(api_key="test_key", api_secret="test_secret")
        assert client.is_configured

    def test_get_headers(self):
        """Test request headers are generated."""
        client = DraftKingsClient(api_key="test_key", api_secret="test_secret")
        headers = client._get_headers()

        assert "Content-Type" in headers
        assert "X-API-Key" in headers
        assert "X-Timestamp" in headers
        assert "X-Signature" in headers
        assert headers["X-API-Key"] == "test_key"


# =============================================================================
# Odds Conversion Tests
# =============================================================================

class TestOddsConversion:
    """Tests for odds conversion functions."""

    def test_american_to_probability_favorite(self):
        """Test converting favorite odds to probability."""
        prob = _american_to_probability(-150)
        assert 0.59 <= prob <= 0.61  # ~60%

    def test_american_to_probability_underdog(self):
        """Test converting underdog odds to probability."""
        prob = _american_to_probability(150)
        assert 0.39 <= prob <= 0.41  # ~40%

    def test_american_to_probability_even(self):
        """Test converting even odds to probability."""
        prob = _american_to_probability(100)
        assert prob == 0.5

    def test_american_to_decimal_favorite(self):
        """Test converting favorite to decimal."""
        decimal = _american_to_decimal(-200)
        assert decimal == 1.5

    def test_american_to_decimal_underdog(self):
        """Test converting underdog to decimal."""
        decimal = _american_to_decimal(200)
        assert decimal == 3.0

    def test_decimal_to_american_favorite(self):
        """Test converting decimal favorite to American."""
        american = _decimal_to_american(1.5)
        assert american == -200

    def test_decimal_to_american_underdog(self):
        """Test converting decimal underdog to American."""
        american = _decimal_to_american(3.0)
        assert american == 200


# =============================================================================
# Simulation Tests
# =============================================================================

class TestSimulation:
    """Tests for simulation functions."""

    def test_simulate_odds_moneyline(self):
        """Test simulating moneyline odds."""
        odds = _simulate_odds("NFL", "MONEYLINE")
        assert len(odds) >= 6  # At least 3 games × 2 sides
        assert all(isinstance(o, DraftKingsOdds) for o in odds)

    def test_simulate_odds_spread(self):
        """Test simulating spread odds."""
        odds = _simulate_odds("NFL", "SPREAD")
        assert len(odds) >= 6
        assert all(o.line is not None for o in odds)

    def test_simulate_odds_total(self):
        """Test simulating total odds."""
        odds = _simulate_odds("NBA", "TOTAL")
        assert len(odds) >= 6
        # NBA totals should be higher than NFL
        lines = [o.line for o in odds if o.line]
        assert all(line > 100 for line in lines)  # NBA totals are 200+

    def test_simulate_events(self):
        """Test simulating events."""
        events = _simulate_events("NFL")
        assert len(events) >= 3
        assert all(isinstance(e, DraftKingsEvent) for e in events)

    def test_simulate_events_has_live(self):
        """Test simulated events include live game."""
        events = _simulate_events("NBA")
        live_events = [e for e in events if e.status == "live"]
        assert len(live_events) >= 1

    def test_simulate_line_movements(self):
        """Test simulating line movements."""
        movements = _simulate_line_movements("test_event", "SPREAD")
        assert len(movements) >= 1
        assert all(isinstance(m, LineMovement) for m in movements)

    def test_simulate_line_movements_has_history(self):
        """Test simulated movements have timestamp history."""
        movements = _simulate_line_movements("test_event", "SPREAD")
        for movement in movements:
            assert len(movement.timestamps) >= 2

    def test_simulate_markets(self):
        """Test simulating markets."""
        markets = _simulate_markets("test_event")
        assert len(markets) >= 3  # ML, spread, total at minimum
        types = [m.get("type") for m in markets]
        assert "moneyline" in types
        assert "spread" in types
        assert "total" in types


# =============================================================================
# Service Function Tests
# =============================================================================

class TestOddsFunctions:
    """Tests for odds service functions."""

    @pytest.mark.asyncio
    async def test_get_live_odds_returns_list(self):
        """Test get_live_odds returns list of odds."""
        odds = await get_live_odds("NFL", "MONEYLINE")
        assert isinstance(odds, list)
        assert len(odds) > 0

    @pytest.mark.asyncio
    async def test_get_live_odds_has_required_fields(self):
        """Test odds have required fields."""
        odds = await get_live_odds("NBA", "SPREAD")
        for o in odds:
            assert o.event_id is not None
            assert o.odds_american != 0
            assert o.odds_decimal > 0

    @pytest.mark.asyncio
    async def test_get_event_odds(self):
        """Test getting odds for specific event."""
        odds = await get_event_odds("dk_nfl_1")
        assert "event_id" in odds
        assert "moneyline" in odds or "simulated" in odds

    @pytest.mark.asyncio
    async def test_get_best_odds(self):
        """Test getting best value odds."""
        best = await get_best_odds("NFL", min_events=3)
        assert len(best) >= 1
        # Should be sorted by vig
        if len(best) >= 2:
            assert best[0]["vig_pct"] <= best[-1]["vig_pct"]


class TestEventFunctions:
    """Tests for event service functions."""

    @pytest.mark.asyncio
    async def test_get_events_returns_list(self):
        """Test get_events returns list."""
        events = await get_events("NFL")
        assert isinstance(events, list)
        assert len(events) > 0

    @pytest.mark.asyncio
    async def test_get_events_has_required_fields(self):
        """Test events have required fields."""
        events = await get_events("NBA")
        for e in events:
            assert e.event_id is not None
            assert e.home_team is not None
            assert e.away_team is not None
            assert e.status in ["scheduled", "live", "final"]

    @pytest.mark.asyncio
    async def test_get_live_events(self):
        """Test getting only live events."""
        live = await get_live_events("NFL")
        assert all(e.status == "live" for e in live)

    @pytest.mark.asyncio
    async def test_get_event_details(self):
        """Test getting event details."""
        event = await get_event_details("dk_nfl_1")
        assert event is not None
        assert isinstance(event, DraftKingsEvent)


class TestLineMovementFunctions:
    """Tests for line movement functions."""

    @pytest.mark.asyncio
    async def test_get_line_movements(self):
        """Test getting line movements."""
        movements = await get_line_movements("dk_nfl_1", "SPREAD")
        assert isinstance(movements, list)

    @pytest.mark.asyncio
    async def test_line_movement_has_direction(self):
        """Test line movements have direction."""
        movements = await get_line_movements("dk_nba_1", "TOTAL")
        for m in movements:
            assert m.direction in ["steam", "reverse", "drift", "stable"]

    @pytest.mark.asyncio
    async def test_detect_steam_moves(self):
        """Test steam move detection."""
        steam = await detect_steam_moves("NFL")
        assert isinstance(steam, list)

    @pytest.mark.asyncio
    async def test_detect_rlm(self):
        """Test reverse line movement detection."""
        rlm = await detect_reverse_line_movement("NBA")
        assert isinstance(rlm, list)


class TestMarketFunctions:
    """Tests for market functions."""

    @pytest.mark.asyncio
    async def test_get_markets(self):
        """Test getting all markets."""
        markets = await get_markets("dk_nfl_1")
        assert isinstance(markets, list)
        assert len(markets) >= 3

    @pytest.mark.asyncio
    async def test_get_markets_filtered(self):
        """Test getting filtered markets."""
        markets = await get_markets("dk_nfl_1", ["player_prop"])
        assert all(m.get("type") == "player_prop" for m in markets)

    @pytest.mark.asyncio
    async def test_get_player_props(self):
        """Test getting player props."""
        props = await get_player_props("dk_nfl_1")
        assert isinstance(props, list)


# =============================================================================
# Data Class Tests
# =============================================================================

class TestDataClasses:
    """Tests for data classes."""

    def test_draftkings_odds_creation(self):
        """Test creating DraftKingsOdds."""
        odds = DraftKingsOdds(
            event_id="test_1",
            market_id="test_ml",
            market_type="moneyline",
            selection_id="sel_1",
            selection_name="Team A",
            odds_american=-150,
            odds_decimal=1.67,
        )
        assert odds.event_id == "test_1"
        assert odds.odds_american == -150

    def test_draftkings_event_creation(self):
        """Test creating DraftKingsEvent."""
        event = DraftKingsEvent(
            event_id="test_1",
            sport="NFL",
            league="NFL Regular Season",
            home_team="Bills",
            away_team="Chiefs",
            start_time=datetime.utcnow(),
            status="scheduled",
        )
        assert event.home_team == "Bills"
        assert event.status == "scheduled"

    def test_line_movement_creation(self):
        """Test creating LineMovement."""
        movement = LineMovement(
            event_id="test_1",
            market_type="spread",
            selection="Home",
            opening_line=-3,
            current_line=-4,
            opening_odds=-110,
            current_odds=-110,
            movement=-1,
            movement_pct=33.3,
            direction="steam",
        )
        assert movement.movement == -1
        assert movement.direction == "steam"


# =============================================================================
# Configuration Tests
# =============================================================================

class TestConfiguration:
    """Tests for configuration."""

    def test_sport_ids_defined(self):
        """Test sport IDs are defined."""
        assert "NFL" in SPORT_IDS
        assert "NBA" in SPORT_IDS
        assert "MLB" in SPORT_IDS
        assert "NHL" in SPORT_IDS

    def test_market_types_defined(self):
        """Test market types are defined."""
        assert "MONEYLINE" in MARKET_TYPES
        assert "SPREAD" in MARKET_TYPES
        assert "TOTAL" in MARKET_TYPES
        assert "PLAYER_PROP" in MARKET_TYPES


# =============================================================================
# Router Endpoint Tests
# =============================================================================

class TestDraftKingsRouter:
    """Tests for DraftKings API endpoints."""

    def test_demo_endpoint_no_auth(self):
        """Test demo endpoint works without auth."""
        response = client.get("/draftkings/demo")
        assert response.status_code == 200
        data = response.json()
        assert data["demo"] is True
        assert "sample_odds" in data
        assert "sample_events" in data

    def test_status_endpoint(self):
        """Test status endpoint."""
        response = client.get("/draftkings/status")
        assert response.status_code == 200
        data = response.json()
        assert "configured" in data
        assert "mode" in data
        assert "supported_sports" in data

    def test_odds_requires_auth(self):
        """Test odds endpoint requires auth."""
        response = client.get("/draftkings/odds/NFL")
        assert response.status_code == 401

    def test_odds_with_auth(self, auth_headers):
        """Test odds endpoint with auth."""
        response = client.get("/draftkings/odds/NFL", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["sport"] == "NFL"
        assert "odds" in data

    def test_odds_with_market_type(self, auth_headers):
        """Test odds endpoint with market type."""
        response = client.get(
            "/draftkings/odds/NBA?market_type=SPREAD",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["market_type"] == "SPREAD"

    def test_odds_invalid_sport(self, auth_headers):
        """Test odds endpoint with invalid sport."""
        response = client.get("/draftkings/odds/CURLING", headers=auth_headers)
        assert response.status_code == 400

    def test_odds_invalid_market_type(self, auth_headers):
        """Test odds endpoint with invalid market type."""
        response = client.get(
            "/draftkings/odds/NFL?market_type=INVALID",
            headers=auth_headers
        )
        assert response.status_code == 400

    def test_events_endpoint(self, auth_headers):
        """Test events endpoint."""
        response = client.get("/draftkings/events/NFL", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["sport"] == "NFL"
        assert "events" in data
        assert "live_count" in data

    def test_live_events_endpoint(self, auth_headers):
        """Test live events endpoint."""
        response = client.get("/draftkings/events/NBA/live", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "live_count" in data

    def test_event_details_endpoint(self, auth_headers):
        """Test event details endpoint."""
        response = client.get("/draftkings/event/dk_nfl_1", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "event_id" in data
        assert "matchup" in data

    def test_best_odds_endpoint(self, auth_headers):
        """Test best odds endpoint."""
        response = client.get("/draftkings/odds/best/NFL", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "events" in data

    def test_line_movements_endpoint(self, auth_headers):
        """Test line movements endpoint."""
        response = client.get(
            "/draftkings/lines/dk_nfl_1",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "movements" in data

    def test_steam_moves_endpoint(self, auth_headers):
        """Test steam moves endpoint."""
        response = client.get("/draftkings/lines/steam/NFL", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "steam_moves_detected" in data

    def test_rlm_endpoint(self, auth_headers):
        """Test RLM endpoint."""
        response = client.get("/draftkings/lines/rlm/NBA", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "rlm_alerts" in data

    def test_markets_endpoint(self, auth_headers):
        """Test markets endpoint."""
        response = client.get("/draftkings/markets/dk_nfl_1", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "markets" in data
        assert "market_count" in data

    def test_props_endpoint(self, auth_headers):
        """Test player props endpoint."""
        response = client.get("/draftkings/props/dk_nfl_1", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "props" in data

    def test_compare_odds_endpoint(self, auth_headers):
        """Test odds comparison endpoint."""
        response = client.get(
            "/draftkings/compare/odds/dk_nfl_1?home_fair_prob=0.55",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "draftkings_odds" in data
        assert "your_fair_value" in data
        assert "edge" in data
        assert "recommendation" in data

    def test_compare_odds_detects_edge(self, auth_headers):
        """Test odds comparison detects edge."""
        # Using extreme probability to ensure edge is detected
        response = client.get(
            "/draftkings/compare/odds/dk_nfl_1?home_fair_prob=0.75",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        # Should detect home edge when fair prob is 75%
        assert "edge" in data["recommendation"].lower() or "home" in data["recommendation"].lower()
