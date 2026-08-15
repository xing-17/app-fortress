from __future__ import annotations

import pytest

from bastion.metadata.quality import Quality


class TestQuality:
    """Test suite for Quality class."""

    def test_quality_initialization(self):
        """Test basic quality initialization."""
        quality = Quality(run_id="run-123", passed=True)
        assert quality.run_id == "run-123"
        assert quality.id is not None
        assert quality.domain.passed is True
        assert quality.domain.kind == "base"

    def test_quality_with_metrics(self):
        """Test quality initialization with metrics."""
        metrics = {"accuracy": 0.95, "precision": 0.92}
        quality = Quality(
            run_id="run-123",
            passed=True,
            description="Model validation",
            metrics=metrics,
        )
        assert quality.domain.metrics == metrics
        assert quality.domain.description == "Model validation"

    def test_quality_failed(self):
        """Test quality initialization with failed status."""
        quality = Quality(
            run_id="run-123",
            passed=False,
            description="Validation failed",
        )
        assert quality.domain.passed is False

    def test_quality_from_dict(self):
        """Test creating quality from dictionary."""
        data = {
            "run_id": "run-123",
            "passed": True,
            "kind": "validation",
            "description": "Data quality check",
            "metrics": {"rows": 1000},
        }
        quality = Quality.from_any(data)
        assert quality.run_id == "run-123"
        assert quality.domain.passed is True
        assert quality.domain.kind == "validation"
        assert quality.domain.metrics == {"rows": 1000}

    def test_quality_from_quality(self):
        """Test creating quality from another quality instance."""
        quality1 = Quality(run_id="run-123", passed=True)
        quality2 = Quality.from_any(quality1)
        assert quality1.id == quality2.id
        assert quality1.run_id == quality2.run_id

    def test_quality_export(self):
        """Test quality export to dictionary."""
        quality = Quality(
            run_id="run-123",
            passed=True,
            description="Test quality",
            metrics={"score": 0.9},
        )
        exported = quality.export()
        assert exported["run_id"] == "run-123"
        assert exported["passed"] is True
        assert exported["description"] == "Test quality"
        assert exported["metrics"] == {"score": 0.9}
        assert "id" in exported
        assert "created_at" in exported

    def test_quality_sha256_key(self):
        """Test quality SHA256 key generation."""
        quality = Quality(run_id="run-123", passed=True)
        sha_key = quality._sha256_key
        assert isinstance(sha_key, str)
        assert len(sha_key) > 0

    def test_quality_from_invalid_data(self):
        """Test quality creation with invalid data."""
        with pytest.raises(ValueError):
            Quality.from_any({"invalid": "data"})
