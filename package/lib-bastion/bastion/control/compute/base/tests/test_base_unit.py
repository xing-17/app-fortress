"""
Unit tests for bastion.control.compute.base module.
"""

import pytest

from bastion.control.compute.base.base import IComputeLike
from bastion.domain.compute.base import BaseComputeModel, ComputeKind


class TestBaseComputeModel:
    """Test BaseComputeModel class."""

    def test_create_compute_model_minimal(self):
        """Test creating a basic compute model."""
        model = BaseComputeModel(
            name="test_compute",
            kind=ComputeKind.PY_ENTRYPOINT,
        )
        assert model.name == "test_compute"
        assert model.kind == ComputeKind.PY_ENTRYPOINT
        assert model.tags == {}

    def test_create_compute_model_with_tags(self):
        """Test creating compute model with tags."""
        model = BaseComputeModel(
            name="test_compute",
            kind=ComputeKind.PY_ENTRYPOINT,
            tags={"env": "dev", "version": "1.0"},
        )
        assert model.name == "test_compute"
        assert model.kind == ComputeKind.PY_ENTRYPOINT
        assert model.tags == {"env": "dev", "version": "1.0"}

    def test_create_compute_model_with_kind_string(self):
        """Test creating compute model with kind as string."""
        model = BaseComputeModel(
            name="test_compute",
            kind="py_entrypoint",
            tags={},
        )
        assert model.kind == ComputeKind.PY_ENTRYPOINT

    def test_missing_name_raises(self):
        """Test creating compute model without name raises error."""
        with pytest.raises((TypeError, ValueError)):
            BaseComputeModel(kind=ComputeKind.PY_ENTRYPOINT)

    def test_missing_kind_raises(self):
        """Test creating compute model without kind raises error."""
        with pytest.raises((TypeError, ValueError)):
            BaseComputeModel(name="test_compute")

    def test_tags_default_to_empty_dict(self):
        """Test tags default to empty dictionary."""
        model = BaseComputeModel(
            name="test_compute",
            kind=ComputeKind.PY_ENTRYPOINT,
        )
        assert model.tags == {}
        assert isinstance(model.tags, dict)


class TestBaseComputeModelSerialization:
    """Test BaseComputeModel serialization and deserialization."""

    def test_export(self, compute_model):
        """Test export method returns correct dictionary."""
        exported = compute_model.export()

        assert isinstance(exported, dict)
        assert exported["name"] == "test_compute"
        assert exported["kind"] == "py_entrypoint"
        assert exported["tags"] == {"env": "test", "version": "1.0"}

    def test_from_dict(self, compute_model_data):
        """Test from_any creates BaseComputeModel from dictionary."""
        model = BaseComputeModel.from_any(compute_model_data)
        assert model.name == "test_compute"
        assert model.kind == ComputeKind.PY_ENTRYPOINT
        assert model.tags == {"env": "test", "version": "1.0"}

    def test_roundtrip_export_from_dict(self, compute_model):
        """Test export and from_any roundtrip conversion."""
        original = compute_model

        # Export to dict
        exported = original.export()
        # Recreate from dict
        restored = BaseComputeModel.from_any(exported)

        # Verify all fields match
        assert restored.name == original.name
        assert restored.kind == original.kind
        assert restored.tags == original.tags
        assert restored.sha256 == original.sha256

    def test_describe_returns_json_string(self, compute_model):
        """Test describe returns JSON string representation."""
        description = compute_model.describe()
        assert isinstance(description, str)
        assert "test_compute" in description
        assert "py_entrypoint" in description

    def test_clone_with_updates(self, compute_model):
        """Test clone method creates copy with updates."""
        cloned = compute_model.clone(name="cloned_compute")
        assert cloned.name == "cloned_compute"
        assert cloned.kind == compute_model.kind
        assert cloned.tags == compute_model.tags
        assert cloned.sha256 != compute_model.sha256  # SHA changes with name


class TestComputeKind:
    """Test ComputeKind enum."""

    def test_compute_kind_values(self):
        """Test ComputeKind enum has expected values."""
        assert ComputeKind.PY_ENTRYPOINT == "py_entrypoint"

    def test_compute_kind_from_string(self):
        """Test creating ComputeKind from string."""
        kind = ComputeKind("py_entrypoint")
        assert kind == ComputeKind.PY_ENTRYPOINT

    def test_compute_kind_comparison(self):
        """Test ComputeKind comparison."""
        assert ComputeKind.PY_ENTRYPOINT == "py_entrypoint"
        assert ComputeKind.PY_ENTRYPOINT == ComputeKind.PY_ENTRYPOINT


class TestIComputeLikeProtocol:
    """Test IComputeLike protocol definition."""

    def test_protocol_has_required_methods(self):
        """Test IComputeLike protocol defines required methods."""
        # Check protocol has expected methods in annotations
        annotations = IComputeLike.__annotations__
        assert "domain" in annotations
        assert "name" in annotations
        assert "kind" in annotations
        assert "tags" in annotations
