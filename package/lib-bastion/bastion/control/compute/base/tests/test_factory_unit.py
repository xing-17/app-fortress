"""Unit tests for compute base factory."""

from __future__ import annotations

import pytest

from bastion.control.compute.base.factory import ComputeFactory
from bastion.control.compute.pyentrypoint import PyEntrypointCompute
from bastion.domain.compute import ComputeKind


class TestComputeFactory:
    """Test ComputeFactory registration and loading."""

    def test_register_and_load_from_dict(self):
        """Test registering compute kind and loading from dict."""
        ComputeFactory._registry.clear()

        @ComputeFactory.register("test_kind")
        class TestCompute:
            pass

        assert "test_kind" in ComputeFactory._registry
        assert ComputeFactory._registry["test_kind"] is TestCompute

    def test_register_duplicate_kind_raises(self):
        """Test duplicate kind registration raises ValueError."""
        ComputeFactory._registry.clear()

        @ComputeFactory.register("test_kind")
        class FirstCompute:
            pass

        with pytest.raises(ValueError, match="already registered"):

            @ComputeFactory.register("test_kind")
            class SecondCompute:
                pass

    def test_load_from_dict(self):
        """Test loading compute from dictionary."""
        ComputeFactory._registry.clear()
        ComputeFactory.register(ComputeKind.PY_ENTRYPOINT.value)(PyEntrypointCompute)

        data = {
            "name": "test_compute",
            "kind": ComputeKind.PY_ENTRYPOINT.value,
            "entrypoint": "module.function",
        }

        compute = ComputeFactory.load(data)
        assert isinstance(compute, PyEntrypointCompute)
        assert compute.name == "test_compute"
        assert compute.kind == ComputeKind.PY_ENTRYPOINT

    def test_load_from_domain_model(self):
        """Test loading compute from domain model."""
        from bastion.control.compute.pyentrypoint import PyEntrypointModel

        ComputeFactory._registry.clear()
        ComputeFactory.register(ComputeKind.PY_ENTRYPOINT.value)(PyEntrypointCompute)

        domain = PyEntrypointModel(
            name="test_compute",
            entrypoint="module.function",
        )

        compute = ComputeFactory.load(domain)
        assert isinstance(compute, PyEntrypointCompute)
        assert compute.name == "test_compute"
        assert compute.domain.entrypoint == "module.function"

    def test_load_missing_kind_from_dict_raises(self):
        """Test loading without kind field from dict raises ValueError."""
        ComputeFactory._registry.clear()

        with pytest.raises(ValueError, match="missing required field"):
            ComputeFactory.load({"name": "test"})

    def test_load_unregistered_kind_raises(self):
        """Test loading unregistered kind raises ValueError."""
        ComputeFactory._registry.clear()

        data = {
            "name": "test_compute",
            "kind": "nonexistent_kind",
            "entrypoint": "module.function",
        }

        with pytest.raises(ValueError, match="No compute class registered"):
            ComputeFactory.load(data)

    def test_register_decorator_returns_class(self):
        """Test register decorator returns the original class."""
        ComputeFactory._registry.clear()

        @ComputeFactory.register("test_kind")
        class TestCompute:
            pass

        # Verify the decorator returns the class itself
        assert TestCompute.__name__ == "TestCompute"

    def test_load_preserves_compute_attributes(self):
        """Test that loading preserves all compute attributes."""
        ComputeFactory._registry.clear()
        ComputeFactory.register(ComputeKind.PY_ENTRYPOINT.value)(PyEntrypointCompute)

        data = {
            "name": "test_compute",
            "kind": ComputeKind.PY_ENTRYPOINT.value,
            "entrypoint": "bastion.module.function",
            "tags": {"env": "test", "version": "1.0"},
        }

        compute = ComputeFactory.load(data)
        assert compute.name == "test_compute"
        assert compute.kind == ComputeKind.PY_ENTRYPOINT
        assert compute.domain.entrypoint == "bastion.module.function"
        assert compute.tags == {"env": "test", "version": "1.0"}

    def test_load_with_empty_kind_raises(self):
        """Test loading with empty string kind raises ValueError."""
        ComputeFactory._registry.clear()

        data = {
            "name": "test_compute",
            "kind": "",
            "entrypoint": "module.function",
        }

        with pytest.raises(ValueError, match="missing required field"):
            ComputeFactory.load(data)

    def test_load_with_none_kind_raises(self):
        """Test loading with None kind raises ValueError."""
        ComputeFactory._registry.clear()

        data = {
            "name": "test_compute",
            "kind": None,
            "entrypoint": "module.function",
        }

        with pytest.raises(ValueError, match="missing required field"):
            ComputeFactory.load(data)

    def test_registry_is_shared_across_instances(self):
        """Test that registry is shared as class variable."""
        ComputeFactory._registry.clear()

        @ComputeFactory.register("shared_test")
        class SharedCompute:
            pass

        # Verify registry is accessible from class
        assert "shared_test" in ComputeFactory._registry
        assert ComputeFactory._registry["shared_test"] is SharedCompute

    def test_multiple_registrations(self):
        """Test registering multiple different compute kinds."""
        ComputeFactory._registry.clear()

        @ComputeFactory.register("kind_a")
        class ComputeA:
            @classmethod
            def from_dict(cls, data):
                return cls()

            @classmethod
            def from_domain(cls, domain):
                return cls()

        @ComputeFactory.register("kind_b")
        class ComputeB:
            @classmethod
            def from_dict(cls, data):
                return cls()

            @classmethod
            def from_domain(cls, domain):
                return cls()

        assert len(ComputeFactory._registry) == 2
        assert "kind_a" in ComputeFactory._registry
        assert "kind_b" in ComputeFactory._registry
