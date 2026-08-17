"""
Pytest configuration and fixtures for bastion.control.run module tests.
"""

import pytest

from bastion.control.run.run import Run


@pytest.fixture
def run_basic():
    """Basic run instance for testing."""
    return Run(
        bridge_name="test_bridge",
        name="test_run",
    )


@pytest.fixture
def run_with_id():
    """Run instance with predefined ID for testing."""
    return Run(
        bridge_name="test_bridge",
        name="test_run",
        id="run-test123456789a",
    )


@pytest.fixture
def event_data():
    """Sample event data for testing."""
    return {
        "run_id": "run-123456789abcdef0",
        "message": "Test event message",
        "metadata": {"key": "value", "count": 42},
    }


@pytest.fixture
def quality_data():
    """Sample quality data for testing."""
    return {
        "run_id": "run-123456789abcdef0",
        "kind": "validation",
        "passed": True,
        "description": "Test quality check",
        "metrics": {"accuracy": 0.95, "precision": 0.92},
    }
