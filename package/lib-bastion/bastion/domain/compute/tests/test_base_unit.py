"""
Unit tests for compute base module.
"""

import pytest

from bastion.domain.compute.base import BaseComputeModel, ComputeKind


class TestComputeKind:
    """Test ComputeKind enum."""

    def test_local_py_fn_value(self):
        """Test LOCAL_PY_FN enum value."""
        assert ComputeKind.LOCAL_PY_FN.value == "local_py_fn"

    def test_from_any_with_string(self):
        """Test from_any with string value."""
        kind = ComputeKind.from_any("local_py_fn")
        assert kind == ComputeKind.LOCAL_PY_FN

    def test_from_any_with_enum(self):
        """Test from_any with ComputeKind enum."""
        kind = ComputeKind.from_any(ComputeKind.LOCAL_PY_FN)
        assert kind == ComputeKind.LOCAL_PY_FN

    def test_from_any_with_invalid_value(self):
        """Test from_any with invalid value raises ValueError."""
        with pytest.raises(ValueError, match="Invalid ComputeKind value"):
            ComputeKind.from_any("invalid_kind")


class TestBaseComputeModel:
    """Test BaseComputeModel class."""

    def test_create_compute_model(self):
        """Test creating a BaseComputeModel instance."""
        compute = BaseComputeModel(
            name="test_compute",
            kind=ComputeKind.LOCAL_PY_FN,
            tags={"env": "test"},
        )
        assert compute.name == "test_compute"
        assert compute.kind == ComputeKind.LOCAL_PY_FN
        assert compute.tags == {"env": "test"}

    def test_create_compute_model_with_default_tags(self):
        """Test creating a BaseComputeModel with default tags."""
        compute = BaseComputeModel(
            name="test_compute",
            kind=ComputeKind.LOCAL_PY_FN,
        )
        assert compute.tags == {}

    def test_export(self):
        """Test export method returns correct dictionary."""
        compute = BaseComputeModel(
            name="test_compute",
            kind=ComputeKind.LOCAL_PY_FN,
            tags={"env": "prod", "version": "1.0"},
        )
        exported = compute.export()

        assert exported["name"] == "test_compute"
        assert exported["kind"] == "local_py_fn"
        assert exported["tags"] == {"env": "prod", "version": "1.0"}

    def test_export_with_empty_tags(self):
        """Test export method with empty tags."""
        compute = BaseComputeModel(
            name="simple_compute",
            kind=ComputeKind.LOCAL_PY_FN,
        )
        exported = compute.export()

        assert exported["name"] == "simple_compute"
        assert exported["kind"] == "local_py_fn"
        assert exported["tags"] == {}
