"""Test configuration and fixtures."""

import os

import pytest
from fastapi.testclient import TestClient

# Set environment variables for testing
os.environ["EMULATE_DEVICES"] = "true"
os.environ["N_VIRTUAL_PUMPS"] = "2"
os.environ["N_VIRTUAL_SPECTROPHOTOMETERS"] = "1"
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["RESCAN_INTERVAL_SEC"] = "0"  # Disable periodic rescan in tests

from bioexperiment_api.app import create_app


@pytest.fixture()
def client():
    """Create test client."""
    app = create_app()
    with TestClient(app) as client:
        yield client


@pytest.fixture()
def app():
    """Create FastAPI app for testing."""
    return create_app()
