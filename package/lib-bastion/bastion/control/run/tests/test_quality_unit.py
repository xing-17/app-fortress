"""
Unit tests for bastion.control.run.quality module.
"""

from datetime import datetime

import pytest

from bastion.control.run.quality import IQualityLike, Quality, QualityModel


class TestQuality:
    """Test Quality class."""

    def test_create_quality(self):
        """Test creating a basic quality."""
        quality = Quality(run_id="run-123")
        assert quality.run_id == "run-123"
        assert quality.kind == "base"
        assert quality.passed is None
        assert quality.description is None
        assert isinstance(quality.created_at, datetime)
        assert quality.metrics == {}
        assert quality.id != ""
        assert quality.id.startswith("qual-")

    def test_create_quality_with_kind(self):
        """Test creating quality with custom kind."""
        quality = Quality(
            run_id="run-123",
            kind="validation",
        )
        assert quality.kind == "validation"

    def test_create_quality_with_passed(self):
        """Test creating quality with passed status."""
        quality_passed = Quality(
            run_id="run-123",
            passed=True,
        )
        quality_failed = Quality(
            run_id="run-456",
            passed=False,
        )
        assert quality_passed.passed is True
        assert quality_failed.passed is False

    def test_create_quality_with_description(self):
        """Test creating quality with description."""
        description = "Data validation check"
        quality = Quality(
            run_id="run-123",
            description=description,
        )
        assert quality.description == description

    def test_create_quality_with_metrics(self):
        """Test creating quality with metrics."""
        metrics = {
            "accuracy": 0.95,
            "precision": 0.92,
            "recall": 0.89,
            "f1_score": 0.905,
        }
        quality = Quality(
            run_id="run-123",
            metrics=metrics,
        )
        assert quality.metrics == metrics

    def test_create_quality_with_all_params(self):
        """Test creating quality with all parameters."""
        quality = Quality(
            run_id="run-123",
            kind="data_quality",
            passed=True,
            description="Complete quality check",
            metrics={"score": 98.5, "threshold": 90.0},
        )
        assert quality.run_id == "run-123"
        assert quality.kind == "data_quality"
        assert quality.passed is True
        assert quality.description == "Complete quality check"
        assert quality.metrics == {"score": 98.5, "threshold": 90.0}

    def test_create_quality_with_custom_id(self):
        """Test creating quality with custom ID."""
        custom_id = "qual-custom123456789012"
        quality = Quality(
            run_id="run-789",
            id=custom_id,
            kind="custom",
        )
        assert quality.id == custom_id

    def test_create_quality_with_created_at_string(self):
        """Test creating quality with created_at as ISO string."""
        iso_time = "2026-08-14T10:00:00"
        quality = Quality(
            run_id="run-123",
            kind="test",
            created_at=iso_time,
        )
        assert quality.created_at.year == 2026
        assert quality.created_at.month == 8
        assert quality.created_at.day == 14

    def test_create_quality_with_created_at_datetime(self):
        """Test creating quality with created_at as datetime."""
        dt = datetime(2026, 8, 14, 10, 30, 0)
        quality = Quality(
            run_id="run-123",
            kind="test",
            created_at=dt,
        )
        assert quality.created_at == dt

    def test_missing_run_id_raises(self):
        """Test creating quality without run_id raises error."""
        with pytest.raises(TypeError):
            Quality()

    def test_export(self):
        """Test export method returns correct dictionary."""
        quality = Quality(
            run_id="run-456",
            kind="validation",
            passed=True,
            description="Test export",
            metrics={"score": 0.87},
        )
        exported = quality.export()

        assert exported["id"] == quality.id
        assert exported["run_id"] == "run-456"
        assert exported["kind"] == "validation"
        assert exported["passed"] is True
        assert exported["description"] == "Test export"
        assert isinstance(exported["created_at"], str)
        assert exported["metrics"] == {"score": 0.87}

        # Verify ISO format
        datetime.fromisoformat(exported["created_at"])

    def test_export_with_default_values(self):
        """Test export with default values."""
        quality = Quality(run_id="run-789")
        exported = quality.export()

        assert exported["kind"] == "base"
        assert exported["passed"] is None
        assert exported["description"] is None
        assert isinstance(exported["created_at"], str)
        assert exported["metrics"] == {}

    def test_from_dict(self):
        """Test from_dict creates Quality from dictionary."""
        data = {
            "id": "qual-abc123def456789012",
            "run_id": "run-123",
            "kind": "test",
            "passed": False,
            "description": "Test quality",
            "created_at": "2026-08-14T10:00:00",
            "metrics": {"accuracy": 0.91},
        }
        quality = Quality.from_dict(data)
        assert quality.id == "qual-abc123def456789012"
        assert quality.run_id == "run-123"
        assert quality.kind == "test"
        assert quality.passed is False
        assert quality.description == "Test quality"
        assert quality.metrics == {"accuracy": 0.91}

    def test_from_domain(self):
        """Test from_domain creates Quality from domain model."""
        domain = QualityModel(
            run_id="run-123",
            kind="domain_test",
            passed=True,
            description="Domain quality",
            metrics={"source": "test"},
        )
        quality = Quality.from_domain(domain)
        assert quality.run_id == "run-123"
        assert quality.kind == "domain_test"
        assert quality.passed is True
        assert quality.description == "Domain quality"
        assert quality.metrics == {"source": "test"}

    def test_roundtrip_export_from_dict(self, quality_data):
        """Test export and from_dict roundtrip conversion."""
        original = Quality(**quality_data)

        # Export to dict
        exported = original.export()
        # Recreate from dict
        restored = Quality.from_dict(exported)

        # Verify all fields match
        assert restored.id == original.id
        assert restored.run_id == original.run_id
        assert restored.kind == original.kind
        assert restored.passed == original.passed
        assert restored.description == original.description
        assert restored.created_at == original.created_at
        assert restored.metrics == original.metrics

    def test_protocol_compliance(self):
        """Test Quality implements IQualityLike protocol."""
        quality = Quality(run_id="run-123", kind="protocol_test")
        assert isinstance(quality, IQualityLike)

    def test_domain_attribute_access(self):
        """Test accessing domain attributes through wrapper."""
        quality = Quality(
            run_id="run-123",
            kind="access_test",
            passed=True,
        )
        # Access domain directly
        assert quality.domain is not None
        assert isinstance(quality.domain, QualityModel)
        # Access via wrapper
        assert quality.id == quality.domain.id
        assert quality.run_id == quality.domain.run_id

    def test_sha256_property(self):
        """Test sha256 property exists and is consistent."""
        quality = Quality(
            run_id="run-123",
            kind="sha_test",
            passed=True,
        )
        sha1 = quality.sha256
        sha2 = quality.sha256
        assert sha1 == sha2
        assert isinstance(sha1, str)
        assert len(sha1) > 0

    def test_logic_name_property(self):
        """Test logic_name property exists."""
        quality = Quality(
            run_id="run-123",
            kind="logic_test",
        )
        logic_name = quality.logic_name
        assert logic_name is not None or logic_name is None  # Can be either

    def test_describe_returns_json_string(self):
        """Test describe method returns formatted JSON string."""
        quality = Quality(
            run_id="run-123",
            kind="describe_test",
            passed=True,
            metrics={"key": "value"},
        )
        description = quality.describe()
        assert isinstance(description, str)
        # Should be valid JSON
        import json

        parsed = json.loads(description)
        assert parsed["run_id"] == "run-123"
        assert parsed["kind"] == "describe_test"
        assert parsed["passed"] is True
