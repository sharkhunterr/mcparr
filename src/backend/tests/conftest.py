"""Pytest configuration and fixtures for MCParr tests."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def sample_fixture():
    """Sample fixture for future tests."""
    return {"status": "ok"}
