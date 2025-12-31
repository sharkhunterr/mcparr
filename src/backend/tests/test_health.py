"""Basic health check tests."""

import pytest


def test_placeholder():
    """Placeholder test to ensure pytest collects tests."""
    assert True, "Basic test should pass"


def test_sample_fixture(sample_fixture):
    """Test using the sample fixture."""
    assert sample_fixture["status"] == "ok"
