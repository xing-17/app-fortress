"""Unit tests for ComputeFactory."""

from __future__ import annotations

import pytest

from bastion.control.compute.base.factory import ComputeFactory
from bastion.control.compute.pyentrypoint.pyentrypoint import PyEntrypointCompute


class TestComputeFactory:
    """Test ComputeFactory functionality."""

    def test_load_py_entrypoint_compute(self):
        """Test loading a py_entrypoint compute."""
        data = {
            "name": "test_compute",
            "kind": "py_entrypoint",
            "module": "test_module",
            "entrypoint": "main",
        }

        compute = ComputeFactory.load_from_dict(data)

        assert isinstance(compute, PyEntrypointCompute)
        assert compute.name == "test_compute"
        assert compute.kind == "py_entrypoint"

    def test_load_missing_kind(self):
        """Test error when kind field is missing."""
        data = {
            "name": "test_compute",
            "module": "test_module",
        }

        with pytest.raises(ValueError, match="missing required field: 'kind'"):
            ComputeFactory.load_from_dict(data)

    def test_load_unregistered_kind(self):
        """Test error when kind is not registered."""
        data = {
            "name": "test_compute",
            "kind": "unknown_kind",
            "module": "test_module",
        }

        with pytest.raises(
            ValueError, match="No compute class registered for kind: 'unknown_kind'"
        ):
            ComputeFactory.load_from_dict(data)

    def test_register_custom_compute(self):
        """Test registering a custom compute class."""

        # Create a mock compute class
        class CustomCompute:
            def __init__(self, name: str, kind: str):
                self.name = name
                self.kind = kind

            @classmethod
            def from_dict(cls, data: dict):
                return cls(
                    name=data["name"],
                    kind=data["kind"],
                )

        # Register the custom compute
        ComputeFactory.register(kind="custom", compute_cls=CustomCompute)

        # Load a compute with the custom kind
        data = {
            "name": "custom_compute",
            "kind": "custom",
        }

        compute = ComputeFactory.load_from_dict(data)

        assert isinstance(compute, CustomCompute)
        assert compute.name == "custom_compute"
        assert compute.kind == "custom"
