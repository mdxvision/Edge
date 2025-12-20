"""
Tests for currency router.
"""
import pytest
from fastapi.testclient import TestClient


class TestCurrencyConversion:
    """Tests for currency conversion."""

    def test_convert_usd_to_eur(self, client: TestClient):
        """Test USD to EUR conversion."""
        response = client.post("/currency/convert", json={
            "amount": 100,
            "from_currency": "USD",
            "to_currency": "EUR"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["original_amount"] == 100
        assert data["from_currency"] == "USD"
        assert data["to_currency"] == "EUR"
        assert "converted_amount" in data
        assert data["converted_amount"] > 0

    def test_convert_same_currency(self, client: TestClient):
        """Test conversion to same currency."""
        response = client.post("/currency/convert", json={
            "amount": 100,
            "from_currency": "USD",
            "to_currency": "USD"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["converted_amount"] == 100

    def test_convert_invalid_currency(self, client: TestClient):
        """Test conversion with invalid currency."""
        response = client.post("/currency/convert", json={
            "amount": 100,
            "from_currency": "USD",
            "to_currency": "INVALID"
        })
        assert response.status_code == 400


class TestCurrencyRates:
    """Tests for currency rates."""

    def test_get_rates(self, client: TestClient):
        """Test getting all currency rates."""
        response = client.get("/currency/rates")
        assert response.status_code == 200
        data = response.json()
        assert "base" in data
        assert "rates" in data
        assert isinstance(data["rates"], dict)

    def test_get_rates_has_common_currencies(self, client: TestClient):
        """Test that rates include common currencies."""
        response = client.get("/currency/rates")
        assert response.status_code == 200
        data = response.json()
        assert "USD" in data["rates"]
        assert "EUR" in data["rates"]


class TestSupportedCurrencies:
    """Tests for supported currencies."""

    def test_get_supported_currencies(self, client: TestClient):
        """Test getting list of supported currencies."""
        response = client.get("/currency/list")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "USD" in data
        assert "EUR" in data
        assert "GBP" in data
