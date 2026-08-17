"""
Unit tests for compute base module.
"""

from bastion.domain.compute.base import BaseComputeModel, ComputeKind


class TestComputeKind:
    """Test ComputeKind enum."""

    def test_py_entrypoint_value(self):
        """Test PY_ENTRYPOINT enum value."""
        assert ComputeKind.PY_ENTRYPOINT.value == "py_entrypoint"


class TestBaseComputeModel:
    """Test BaseComputeModel class."""

    def test_create_compute_model(self):
        """Test creating a BaseComputeModel instance."""
        compute = BaseComputeModel(
            name="test_compute",
            kind=ComputeKind.PY_ENTRYPOINT,
            tags={"env": "test"},
        )
        assert compute.name == "test_compute"
        assert compute.kind == ComputeKind.PY_ENTRYPOINT
        assert compute.tags == {"env": "test"}

    def test_create_compute_model_with_default_tags(self):
        """Test creating a BaseComputeModel with default tags."""
        compute = BaseComputeModel(
            name="test_compute",
            kind=ComputeKind.PY_ENTRYPOINT,
        )
        assert compute.tags == {}

    def test_export(self):
        """Test export method returns correct dictionary."""
        compute = BaseComputeModel(
            name="test_compute",
            kind=ComputeKind.PY_ENTRYPOINT,
            tags={"env": "prod", "version": "1.0"},
        )
        exported = compute.export()

        assert exported["name"] == "test_compute"
        assert exported["kind"] == "py_entrypoint"
        assert exported["tags"] == {"env": "prod", "version": "1.0"}

    def test_export_with_empty_tags(self):
        """Test export method with empty tags."""
        compute = BaseComputeModel(
            name="simple_compute",
            kind=ComputeKind.PY_ENTRYPOINT,
        )
        exported = compute.export()

        assert exported["name"] == "simple_compute"
        assert exported["kind"] == "py_entrypoint"
        assert exported["tags"] == {}

    def test_from_any_with_dict(self):
        """Test from_any creates model from dictionary."""
        data = {
            "name": "test_compute",
            "kind": "py_entrypoint",
            "tags": {"env": "test", "version": "2.0"},
        }
        compute = BaseComputeModel.from_any(data)
        assert compute.name == "test_compute"
        assert compute.kind == ComputeKind.PY_ENTRYPOINT
        assert compute.tags == {"env": "test", "version": "2.0"}

    def test_from_any_with_model_instance(self):
        """Test from_any returns same instance when given model."""
        original = BaseComputeModel(
            name="test_compute",
            kind=ComputeKind.PY_ENTRYPOINT,
        )
        result = BaseComputeModel.from_any(original)
        assert result is original

    def test_roundtrip_export_from_any(self):
        """Test export and from_any roundtrip conversion."""
        original = BaseComputeModel(
            name="roundtrip_compute",
            kind=ComputeKind.PY_ENTRYPOINT,
            tags={"env": "staging", "owner": "team-a", "version": "3.1"},
        )
        # Export to dict
        exported = original.export()
        # Recreate from dict
        restored = BaseComputeModel.from_any(exported)
        # Verify all fields match
        assert restored.name == original.name
        assert restored.kind == original.kind
        assert restored.tags == original.tags
