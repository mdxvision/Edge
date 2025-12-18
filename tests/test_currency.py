"""
Tests for currency router.
"""
import pytest
from fastapi.testclient import TestClient


class TestCurrencyConversion:
    """Tests for currency conversion."""

    def test_convert_usd_to_eur(self, client: TestClient):
        """Test USD to EUR conversion."""
        response = client.get("/currency/convert", params={
            "amount": 100,
            "from_currency": "USD",
            "to_currency": "EUR"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["from_amount"] == 100
        assert data["from_currency"] == "USD"
        assert data["to_currency"] == "EUR"
        assert "converted_amount" in data
        assert data["converted_amount"] > 0

    def test_convert_same_currency(self, client: TestClient):
        """Test conversion to same currency."""
        response = client.get("/currency/convert", params={
            "amount": 100,
            "from_currency": "USD",
            "to_currency": "USD"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["converted_amount"] == 100

    def test_convert_invalid_currency(self, client: TestClient):
        """Test conversion with invalid currency."""
        response = client.get("/currency/convert", params={
            "amount": 100,
            "from_currency": "USD",
            "to_currency": "INVALID"
        })
        assert response.status_code in [400, 404]


class TestCurrencyRates:
    """Tests for currency rates."""

    def test_get_rates(self, client: TestClient):
        """Test getting all currency rates."""
        response = client.get("/currency/rates")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_specific_rate(self, client: TestClient):
        """Test getting specific currency rate."""
        response = client.get("/currency/rates/EUR")
        assert response.status_code == 200
        data = response.json()
        assert data["currency"] == "EUR"
        assert "rate" in data


class TestSupportedCurrencies:
    """Tests for supported currencies."""

    def test_get_supported_currencies(self, client: TestClient):
        """Test getting list of supported currencies."""
        response = client.get("/currency/supported")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert "USD" in data
        assert "EUR" in data
        assert "GBP" in data
