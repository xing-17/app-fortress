"""
Unit tests for bastion.control.compute.pyentrypoint module.
"""

import pytest

from bastion.control.compute.pyentrypoint import PyEntrypointCompute, PyEntrypointModel
from bastion.control.run import Run
from bastion.domain.compute.base import ComputeKind
from bastion.domain.run import RunStatus


class TestPyEntrypointModel:
    """Test PyEntrypointModel class."""

    def test_create_pyentrypoint_model_minimal(self):
        """Test creating a basic pyentrypoint model."""
        model = PyEntrypointModel(
            name="test_compute",
            entrypoint="os.path.join",
        )
        assert model.name == "test_compute"
        assert model.kind == ComputeKind.PY_ENTRYPOINT
        assert model.entrypoint == "os.path.join"
        assert model.tags == {}

    def test_create_pyentrypoint_model_with_tags(self):
        """Test creating pyentrypoint model with tags."""
        model = PyEntrypointModel(
            name="test_compute",
            entrypoint="os.path.join",
            tags={"env": "dev", "version": "1.0"},
        )
        assert model.name == "test_compute"
        assert model.entrypoint == "os.path.join"
        assert model.tags == {"env": "dev", "version": "1.0"}

    def test_pyentrypoint_kind_is_set(self):
        """Test that kind is automatically set to PY_ENTRYPOINT."""
        model = PyEntrypointModel(
            name="test_compute",
            entrypoint="os.path.join",
        )
        assert model.kind == ComputeKind.PY_ENTRYPOINT

    def test_missing_name_raises(self):
        """Test creating pyentrypoint model without name raises error."""
        with pytest.raises((TypeError, ValueError)):
            PyEntrypointModel(entrypoint="os.path.join")

    def test_missing_entrypoint_raises(self):
        """Test creating pyentrypoint model without entrypoint raises error."""
        with pytest.raises((TypeError, ValueError)):
            PyEntrypointModel(name="test_compute")


class TestPyEntrypointModelSerialization:
    """Test PyEntrypointModel serialization and deserialization."""

    def test_export(self, pyentrypoint_model):
        """Test export method returns correct dictionary."""
        exported = pyentrypoint_model.export()

        assert isinstance(exported, dict)
        assert exported["name"] == "test_pyentrypoint"
        assert exported["kind"] == "py_entrypoint"
        assert exported["entrypoint"] == "builtins.print"
        assert exported["tags"] == {"env": "test"}

    def test_from_dict(self, pyentrypoint_model_data):
        """Test from_any creates PyEntrypointModel from dictionary."""
        model = PyEntrypointModel.from_any(pyentrypoint_model_data)
        assert model.name == "test_pyentrypoint"
        assert model.kind == ComputeKind.PY_ENTRYPOINT
        assert model.entrypoint == "builtins.print"
        assert model.tags == {"env": "test"}

    def test_roundtrip_export_from_dict(self, pyentrypoint_model):
        """Test export and from_any roundtrip conversion."""
        original = pyentrypoint_model

        # Export to dict
        exported = original.export()
        # Recreate from dict
        restored = PyEntrypointModel.from_any(exported)

        # Verify all fields match
        assert restored.name == original.name
        assert restored.kind == original.kind
        assert restored.entrypoint == original.entrypoint
        assert restored.tags == original.tags
        assert restored.sha256 == original.sha256


class TestPyEntrypointCompute:
    """Test PyEntrypointCompute class."""

    def test_create_pyentrypoint_compute_minimal(self):
        """Test creating a basic pyentrypoint compute."""
        compute = PyEntrypointCompute(
            name="test_compute",
            entrypoint="os.path.join",
        )
        assert compute.name == "test_compute"
        assert compute.kind == ComputeKind.PY_ENTRYPOINT
        assert compute.domain.entrypoint == "os.path.join"
        assert compute.tags == {}

    def test_create_pyentrypoint_compute_with_tags(self):
        """Test creating pyentrypoint compute with tags."""
        compute = PyEntrypointCompute(
            name="test_compute",
            entrypoint="os.path.join",
            tags={"env": "dev", "version": "1.0"},
        )
        assert compute.name == "test_compute"
        assert compute.domain.entrypoint == "os.path.join"
        assert compute.tags == {"env": "dev", "version": "1.0"}

    def test_missing_name_raises(self):
        """Test creating pyentrypoint compute without name raises error."""
        with pytest.raises(TypeError):
            PyEntrypointCompute(entrypoint="os.path.join")

    def test_missing_entrypoint_raises(self):
        """Test creating pyentrypoint compute without entrypoint raises error."""
        with pytest.raises(TypeError):
            PyEntrypointCompute(name="test_compute")


class TestPyEntrypointComputeSerialization:
    """Test PyEntrypointCompute serialization and deserialization."""

    def test_export(self, pyentrypoint_compute):
        """Test export method returns correct dictionary."""
        exported = pyentrypoint_compute.export()

        assert isinstance(exported, dict)
        assert exported["name"] == "test_pyentrypoint"
        assert exported["kind"] == "py_entrypoint"
        assert exported["entrypoint"] == "builtins.print"
        assert exported["tags"] == {"env": "test"}

    def test_from_dict(self, pyentrypoint_model_data):
        """Test from_dict creates PyEntrypointCompute from dictionary."""
        compute = PyEntrypointCompute.from_dict(pyentrypoint_model_data)
        assert compute.name == "test_pyentrypoint"
        assert compute.kind == ComputeKind.PY_ENTRYPOINT
        assert compute.domain.entrypoint == "builtins.print"
        assert compute.tags == {"env": "test"}

    def test_from_domain(self, pyentrypoint_model):
        """Test from_domain creates PyEntrypointCompute from domain model."""
        compute = PyEntrypointCompute.from_domain(pyentrypoint_model)
        assert compute.name == "test_pyentrypoint"
        assert compute.kind == ComputeKind.PY_ENTRYPOINT
        assert compute.domain.entrypoint == "builtins.print"

    def test_roundtrip_export_from_dict(self, pyentrypoint_compute):
        """Test export and from_dict roundtrip conversion."""
        original = pyentrypoint_compute

        # Export to dict
        exported = original.export()
        # Recreate from dict
        restored = PyEntrypointCompute.from_dict(exported)

        # Verify all fields match
        assert restored.name == original.name
        assert restored.kind == original.kind
        assert restored.domain.entrypoint == original.domain.entrypoint
        assert restored.tags == original.tags
        assert restored.sha256 == original.sha256


class TestPyEntrypointExecution:
    """Test PyEntrypointCompute execution functionality."""

    def test_get_entrypoint_resolves_function(self):
        """Test get_entrypoint resolves a real function."""
        compute = PyEntrypointCompute(
            name="test_compute",
            entrypoint="os.path.join",
        )
        func = compute.get_entrypoint()
        assert callable(func)
        # Test it works
        result = func("a", "b", "c")
        assert result == "a/b/c" or result == "a\\b\\c"  # OS dependent

    def test_get_entrypoint_with_builtin(self):
        """Test get_entrypoint works with builtins."""
        compute = PyEntrypointCompute(
            name="test_compute",
            entrypoint="builtins.len",
        )
        func = compute.get_entrypoint()
        assert callable(func)
        assert func([1, 2, 3]) == 3

    def test_get_entrypoint_with_test_function(self):
        """Test get_entrypoint with a test function."""
        compute = PyEntrypointCompute(
            name="test_compute",
            entrypoint="bastion.control.compute.pyentrypoint.tests.conftest.sample_function_no_params",
        )
        func = compute.get_entrypoint()
        assert callable(func)
        result = func()
        assert result == "success"

    def test_execute_with_no_params(self):
        """Test execute method with function that takes no params."""
        compute = PyEntrypointCompute(
            name="test_compute",
            entrypoint="bastion.control.compute.pyentrypoint.tests.conftest.sample_function_no_params",
        )
        run = Run(bridge_name="test_bridge")

        compute.execute(run=run, store=None, params={})

        assert run.status == RunStatus.SUCCEEDED
        assert run.started_at is not None
        assert run.finished_at is not None

    def test_execute_with_params(self):
        """Test execute method with function that takes params."""
        compute = PyEntrypointCompute(
            name="test_compute",
            entrypoint="bastion.control.compute.pyentrypoint.tests.conftest.sample_function_with_params",
        )
        run = Run(bridge_name="test_bridge")

        compute.execute(
            run=run,
            store=None,
            params={"message": "hello", "count": "3"},
        )

        assert run.status == RunStatus.SUCCEEDED
        assert run.started_at is not None
        assert run.finished_at is not None

    def test_execute_with_side_effects(self):
        """Test execute method with function that has side effects."""
        # Clear tracker
        from bastion.control.compute.pyentrypoint.tests.conftest import _call_tracker

        _call_tracker.clear()

        compute = PyEntrypointCompute(
            name="test_compute",
            entrypoint="bastion.control.compute.pyentrypoint.tests.conftest.sample_function_with_side_effect",
        )
        run = Run(bridge_name="test_bridge")

        compute.execute(
            run=run,
            store=None,
            params={"value": "test_value"},
        )

        assert run.status == RunStatus.SUCCEEDED
        assert "test_value" in _call_tracker

    def test_execute_starts_run(self):
        """Test execute method starts the run."""
        compute = PyEntrypointCompute(
            name="test_compute",
            entrypoint="bastion.control.compute.pyentrypoint.tests.conftest.sample_function_no_params",
        )
        run = Run(bridge_name="test_bridge")
        assert run.status == RunStatus.PENDING
        assert run.started_at is None

        compute.execute(run=run, store=None)

        assert run.status == RunStatus.SUCCEEDED
        assert run.started_at is not None

    def test_execute_handles_errors(self):
        """Test execute method handles errors and marks run as failed."""
        compute = PyEntrypointCompute(
            name="test_compute",
            entrypoint="bastion.control.compute.pyentrypoint.tests.conftest.sample_function_raises_error",
        )
        run = Run(bridge_name="test_bridge")

        with pytest.raises(ValueError, match="Intentional test error"):
            compute.execute(run=run, store=None)

        # Run should be marked as failed
        assert run.status == RunStatus.FAILED
        assert run.started_at is not None
        assert run.finished_at is not None

    def test_execute_with_none_params(self):
        """Test execute method with None params defaults to empty dict."""
        compute = PyEntrypointCompute(
            name="test_compute",
            entrypoint="bastion.control.compute.pyentrypoint.tests.conftest.sample_function_no_params",
        )
        run = Run(bridge_name="test_bridge")

        # Should not raise error with None params
        compute.execute(run=run, store=None, params=None)

        assert run.status == RunStatus.SUCCEEDED

    def test_execute_full_workflow(self):
        """Test complete execute workflow."""
        compute = PyEntrypointCompute(
            name="test_compute",
            entrypoint="bastion.control.compute.pyentrypoint.tests.conftest.sample_function_with_params",
            tags={"env": "test"},
        )
        run = Run(bridge_name="test_bridge", name="test_run")

        # Initial state
        assert run.status == RunStatus.PENDING
        assert run.started_at is None
        assert run.finished_at is None

        # Execute
        compute.execute(
            run=run,
            store=None,
            params={"message": "workflow", "count": "5"},
        )

        # Final state
        assert run.status == RunStatus.SUCCEEDED
        assert run.started_at is not None
        assert run.finished_at is not None
        assert run.started_at < run.finished_at


class TestPyEntrypointInvalidEntrypoints:
    """Test PyEntrypointCompute with invalid entrypoints."""

    def test_invalid_module_raises(self):
        """Test that invalid module raises ImportError."""
        compute = PyEntrypointCompute(
            name="test_compute",
            entrypoint="nonexistent.module.function",
        )
        with pytest.raises(ImportError):
            compute.get_entrypoint()

    def test_invalid_function_raises(self):
        """Test that invalid function name raises AttributeError."""
        compute = PyEntrypointCompute(
            name="test_compute",
            entrypoint="os.path.nonexistent_function",
        )
        with pytest.raises(AttributeError):
            compute.get_entrypoint()

    def test_malformed_entrypoint_raises(self):
        """Test that malformed entrypoint raises error."""
        compute = PyEntrypointCompute(
            name="test_compute",
            entrypoint="no_dot_separator",
        )
        with pytest.raises(ValueError):
            compute.get_entrypoint()
