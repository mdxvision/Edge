"""
Dependency validation tests.

Ensures all required dependencies are correctly specified in requirements.txt
and can be imported without errors.
"""
import pytest
import subprocess
import sys
import re
from pathlib import Path


class TestDependencies:
    """Test that all dependencies are properly specified and importable."""

    def test_requirements_file_exists(self):
        """requirements.txt should exist in project root."""
        requirements_path = Path(__file__).parent.parent / "requirements.txt"
        assert requirements_path.exists(), "requirements.txt not found"

    def test_parse_requirements(self):
        """All requirements should be parseable."""
        requirements_path = Path(__file__).parent.parent / "requirements.txt"
        with open(requirements_path) as f:
            lines = f.readlines()

        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                # Should match package name pattern
                match = re.match(r'^([a-zA-Z0-9_-]+)', line)
                assert match, f"Invalid requirement line: {line}"

    def test_core_dependencies_importable(self):
        """Core dependencies should be importable."""
        core_deps = [
            ("fastapi", "FastAPI"),
            ("uvicorn", "uvicorn"),
            ("sqlalchemy", "SQLAlchemy"),
            ("pydantic", "Pydantic"),
            ("pandas", "Pandas"),
            ("numpy", "NumPy"),
        ]

        for module_name, display_name in core_deps:
            try:
                __import__(module_name)
            except ImportError:
                pytest.fail(f"{display_name} ({module_name}) is not installed")

    def test_api_dependencies_importable(self):
        """API-related dependencies should be importable."""
        api_deps = [
            ("httpx", "HTTPX"),
            ("requests", "Requests"),
            ("starlette", "Starlette"),
        ]

        for module_name, display_name in api_deps:
            try:
                __import__(module_name)
            except ImportError:
                pytest.fail(f"{display_name} ({module_name}) is not installed")

    def test_sports_api_dependencies_importable(self):
        """Sports API dependencies should be importable."""
        sports_deps = [
            ("nba_api", "NBA API"),
        ]

        for module_name, display_name in sports_deps:
            try:
                __import__(module_name)
            except ImportError:
                pytest.fail(f"{display_name} ({module_name}) is not installed")

    def test_testing_dependencies_importable(self):
        """Testing dependencies should be importable."""
        test_deps = [
            ("pytest", "Pytest"),
            ("pytest_asyncio", "Pytest-Asyncio"),
        ]

        for module_name, display_name in test_deps:
            try:
                __import__(module_name)
            except ImportError:
                pytest.fail(f"{display_name} ({module_name}) is not installed")

    def test_security_dependencies_importable(self):
        """Security-related dependencies should be importable."""
        security_deps = [
            ("pyotp", "PyOTP"),
            ("qrcode", "QRCode"),
            ("email_validator", "Email Validator"),
        ]

        for module_name, display_name in security_deps:
            try:
                __import__(module_name)
            except ImportError:
                pytest.fail(f"{display_name} ({module_name}) is not installed")

    def test_payment_dependencies_importable(self):
        """Payment-related dependencies should be importable."""
        payment_deps = [
            ("stripe", "Stripe"),
        ]

        for module_name, display_name in payment_deps:
            try:
                __import__(module_name)
            except ImportError:
                pytest.fail(f"{display_name} ({module_name}) is not installed")

    def test_app_modules_importable(self):
        """Core app modules should be importable without errors."""
        app_modules = [
            "app.config",
            "app.db",
            "app.main",
        ]

        for module in app_modules:
            try:
                __import__(module)
            except ImportError as e:
                pytest.fail(f"Failed to import {module}: {e}")


class TestDependencyVersions:
    """Test dependency version requirements."""

    def test_python_version(self):
        """Python version should be 3.10+."""
        assert sys.version_info >= (3, 10), "Python 3.10+ required"

    def test_fastapi_version(self):
        """FastAPI version should be recent."""
        import fastapi
        version = fastapi.__version__
        major, minor = map(int, version.split(".")[:2])
        assert major == 0 and minor >= 100, f"FastAPI 0.100+ required, got {version}"

    def test_pydantic_version(self):
        """Pydantic version should be v2."""
        import pydantic
        version = pydantic.__version__
        major = int(version.split(".")[0])
        assert major >= 2, f"Pydantic v2+ required, got {version}"
