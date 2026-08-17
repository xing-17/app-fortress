"""
Pytest configuration and fixtures for bastion.control.compute.pyentrypoint module tests.
"""

import pytest

from bastion.control.compute.pyentrypoint import PyEntrypointCompute, PyEntrypointModel
from bastion.domain.compute.base import ComputeKind


@pytest.fixture
def pyentrypoint_model_data():
    """Sample pyentrypoint model data for testing."""
    return {
        "name": "test_pyentrypoint",
        "kind": "py_entrypoint",
        "entrypoint": "builtins.print",
        "tags": {"env": "test"},
    }


@pytest.fixture
def pyentrypoint_model():
    """Basic pyentrypoint model instance for testing."""
    return PyEntrypointModel(
        name="test_pyentrypoint",
        kind=ComputeKind.PY_ENTRYPOINT,
        entrypoint="builtins.print",
        tags={"env": "test"},
    )


@pytest.fixture
def pyentrypoint_compute():
    """Basic pyentrypoint compute instance for testing."""
    return PyEntrypointCompute(
        name="test_pyentrypoint",
        entrypoint="builtins.print",
        tags={"env": "test"},
    )


# Test functions that can be used as entrypoints
def sample_function_no_params():
    """Sample function with no parameters."""
    return "success"


def sample_function_with_params(message: str, count: int = 1):
    """Sample function with parameters."""
    return f"{message} x {count}"


def sample_function_raises_error():
    """Sample function that raises an error."""
    raise ValueError("Intentional test error")


# Global variable to track function calls
_call_tracker = []


def sample_function_with_side_effect(value: str):
    """Sample function that has side effects for testing."""
    _call_tracker.append(value)
    return value
