"""
Pytest configuration and fixtures for bastion.control.compute.base module tests.
"""

import pytest

from bastion.domain.compute.base import BaseComputeModel, ComputeKind


@pytest.fixture
def compute_model_data():
    """Sample compute model data for testing."""
    return {
        "name": "test_compute",
        "kind": "py_entrypoint",
        "tags": {"env": "test", "version": "1.0"},
    }


@pytest.fixture
def compute_model():
    """Basic compute model instance for testing."""
    return BaseComputeModel(
        name="test_compute",
        kind=ComputeKind.PY_ENTRYPOINT,
        tags={"env": "test", "version": "1.0"},
    )
