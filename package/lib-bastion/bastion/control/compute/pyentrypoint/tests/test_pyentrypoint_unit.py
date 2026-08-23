"""Unit tests for PyEntrypoint compute."""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock, patch

import pytest

from bastion.control.compute.base.base import IComputeLike
from bastion.control.compute.pyentrypoint import (
    PyEntrypointCompute,
    PyEntrypointModel,
)
from bastion.control.run.run import Run
from bastion.domain.compute import ComputeKind
from bastion.domain.runstatus import RunStatus


# Test fixtures
@pytest.fixture
def mock_run():
    """Create a mock run object."""
    run = Mock()
    run.start = Mock()
    run.succeed = Mock()
    run.fail = Mock()
    run.status = RunStatus.PENDING
    run.compute_name = "test_compute"
    run.name = "test_run"
    return run


@pytest.fixture
def mock_store():
    """Create a mock store object."""
    store = Mock()
    store.save_run = Mock()
    return store


@pytest.fixture
def sample_entrypoint():
    """Create a sample entrypoint function for testing."""

    def test_function(arg1: str = "default", arg2: int = 0) -> dict[str, Any]:
        """Sample test function."""
        return {"arg1": arg1, "arg2": arg2, "success": True}

    return test_function


class TestPyEntrypointModel:
    """Test PyEntrypointModel domain model."""

    def test_create_model(self):
        """Test creating a PyEntrypointModel."""
        model = PyEntrypointModel(
            name="test_compute",
            entrypoint="bastion.control.compute.pyentrypoint.test_func",
        )

        assert model.name == "test_compute"
        assert model.kind == ComputeKind.PY_ENTRYPOINT
        assert model.entrypoint == "bastion.control.compute.pyentrypoint.test_func"

    def test_model_kind_is_py_entrypoint(self):
        """Test that model kind is PY_ENTRYPOINT."""
        model = PyEntrypointModel(
            name="test",
            entrypoint="module.func",
        )

        assert model.kind == ComputeKind.PY_ENTRYPOINT

    def test_model_export(self):
        """Test exporting model to dict."""
        model = PyEntrypointModel(
            name="test_compute",
            entrypoint="module.function",
            tags={"env": "test"},
        )

        exported = model.export()

        assert exported["name"] == "test_compute"
        assert exported["kind"] == "py_entrypoint"
        assert exported["entrypoint"] == "module.function"
        assert exported["tags"] == {"env": "test"}

    def test_model_with_tags(self):
        """Test creating model with tags."""
        model = PyEntrypointModel(
            name="compute",
            entrypoint="module.func",
            tags={"version": "1.0", "team": "data"},
        )

        assert model.tags == {"version": "1.0", "team": "data"}


class TestPyEntrypointComputeCreation:
    """Test PyEntrypointCompute creation and initialization."""

    def test_create_from_dict(self):
        """Test creating compute from dictionary."""
        data = {
            "name": "test_compute",
            "entrypoint": "module.function",
        }

        compute = PyEntrypointCompute.from_dict(data)

        assert compute.name == "test_compute"
        assert compute.domain.entrypoint == "module.function"
        assert compute.kind == ComputeKind.PY_ENTRYPOINT

    def test_create_from_domain(self):
        """Test creating compute from domain model."""
        domain = PyEntrypointModel(
            name="test_compute",
            entrypoint="module.func",
        )

        compute = PyEntrypointCompute.from_domain(domain)

        assert compute.name == "test_compute"
        assert compute.domain.entrypoint == "module.func"
        assert isinstance(compute.domain, PyEntrypointModel)

    def test_implements_icomputelike_protocol(self):
        """Test that PyEntrypointCompute implements IComputeLike protocol."""
        compute = PyEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "module.func",
            }
        )

        assert isinstance(compute, IComputeLike)

    def test_compute_attributes(self):
        """Test compute required attributes."""
        compute = PyEntrypointCompute.from_dict(
            {
                "name": "test_compute",
                "entrypoint": "module.function",
                "tags": {"env": "prod"},
            }
        )

        assert compute.name == "test_compute"
        assert compute.kind == ComputeKind.PY_ENTRYPOINT
        assert compute.tags == {"env": "prod"}
        assert hasattr(compute, "domain")


class TestResolveEntrypoint:
    """Test _resolve_entrypoint method."""

    def test_resolve_builtin_function(self):
        """Test resolving a built-in function."""
        compute = PyEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "json.dumps",
            }
        )

        func = compute._resolve_entrypoint()

        assert callable(func)
        assert func.__name__ == "dumps"

    def test_resolve_standard_library_function(self):
        """Test resolving a standard library function."""
        compute = PyEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "os.path.exists",
            }
        )

        func = compute._resolve_entrypoint()

        assert callable(func)
        assert func.__name__ == "exists"

    def test_resolve_invalid_module(self):
        """Test resolving with invalid module raises ImportError."""
        compute = PyEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "nonexistent_module.function",
            }
        )

        with pytest.raises(ImportError):
            compute._resolve_entrypoint()

    def test_resolve_invalid_function(self):
        """Test resolving with invalid function raises AttributeError."""
        compute = PyEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "json.nonexistent_function",
            }
        )

        with pytest.raises(AttributeError):
            compute._resolve_entrypoint()

    def test_resolve_entrypoint_without_dot(self):
        """Test resolving entrypoint without module path raises ValueError."""
        compute = PyEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "function_only",
            }
        )

        with pytest.raises(ValueError):
            compute._resolve_entrypoint()


class TestExecuteMethod:
    """Test execute method."""

    @patch("bastion.control.compute.pyentrypoint.pyentrypoint.importlib.import_module")
    def test_execute_success(self, mock_import, mock_run, mock_store):
        """Test successful execution."""
        # Setup mock function
        mock_func = Mock(return_value={"result": "success"})
        mock_module = Mock()
        mock_module.test_func = mock_func
        mock_import.return_value = mock_module

        compute = PyEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "module.test_func",
            }
        )

        params = {"arg1": "value1", "arg2": "value2"}
        compute.execute(run=mock_run, store=mock_store, params=params)

        # Verify run lifecycle
        mock_run.start.assert_called_once()
        mock_run.succeed.assert_called_once()
        mock_run.fail.assert_not_called()

        # Verify store was called twice (before and after execution)
        assert mock_store.save_run.call_count == 2
        mock_store.save_run.assert_called_with(mock_run)

        # Verify function was called with correct params
        mock_func.assert_called_once_with(**params)

    @patch("bastion.control.compute.pyentrypoint.pyentrypoint.importlib.import_module")
    def test_execute_without_params(self, mock_import, mock_run, mock_store):
        """Test execution without parameters."""
        mock_func = Mock()
        mock_module = Mock()
        mock_module.test_func = mock_func
        mock_import.return_value = mock_module

        compute = PyEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "module.test_func",
            }
        )

        compute.execute(run=mock_run, store=mock_store)

        # Verify function was called with empty params
        mock_func.assert_called_once_with()

    @patch("bastion.control.compute.pyentrypoint.pyentrypoint.importlib.import_module")
    def test_execute_without_store(self, mock_import, mock_run):
        """Test execution without store (no persistence)."""
        mock_func = Mock()
        mock_module = Mock()
        mock_module.test_func = mock_func
        mock_import.return_value = mock_module

        compute = PyEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "module.test_func",
            }
        )

        # Should not raise error even without store
        compute.execute(run=mock_run, store=None)

        mock_run.start.assert_called_once()
        mock_run.succeed.assert_called_once()

    @patch("bastion.control.compute.pyentrypoint.pyentrypoint.importlib.import_module")
    def test_execute_failure(self, mock_import, mock_run, mock_store):
        """Test execution failure handling."""
        # Setup mock function that raises exception
        mock_func = Mock(side_effect=RuntimeError("Execution failed"))
        mock_module = Mock()
        mock_module.test_func = mock_func
        mock_import.return_value = mock_module

        compute = PyEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "module.test_func",
            }
        )

        with pytest.raises(RuntimeError, match="Execution failed"):
            compute.execute(run=mock_run, store=mock_store)

        # Verify run lifecycle on failure
        mock_run.start.assert_called_once()
        mock_run.fail.assert_called_once()
        mock_run.succeed.assert_not_called()

        # Verify store was called twice (before and after execution)
        assert mock_store.save_run.call_count == 2

    @patch("bastion.control.compute.pyentrypoint.pyentrypoint.importlib.import_module")
    def test_execute_with_different_exception_types(self, mock_import, mock_run, mock_store):
        """Test execution handles different exception types."""
        exceptions = [
            ValueError("Invalid value"),
            KeyError("missing_key"),
            TypeError("Type error"),
            Exception("Generic error"),
        ]

        for exc in exceptions:
            # Reset mocks
            mock_run.reset_mock()
            mock_store.reset_mock()

            mock_func = Mock(side_effect=exc)
            mock_module = Mock()
            mock_module.test_func = mock_func
            mock_import.return_value = mock_module

            compute = PyEntrypointCompute.from_dict(
                {
                    "name": "test",
                    "entrypoint": "module.test_func",
                }
            )

            with pytest.raises(type(exc)):
                compute.execute(run=mock_run, store=mock_store)

            mock_run.fail.assert_called_once()
            assert mock_store.save_run.call_count == 2


class TestCancelMethod:
    """Test cancel method."""

    def test_cancel_is_noop(self):
        """Test that cancel method is a no-op."""
        compute = PyEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "module.func",
            }
        )

        # Should not raise any error
        compute.cancel()

    def test_cancel_with_kwargs(self):
        """Test cancel with keyword arguments (should be ignored)."""
        compute = PyEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "module.func",
            }
        )

        # Should not raise any error
        compute.cancel(run=Mock(), store=Mock(), adaptor=Mock())


class TestSaveRunMethod:
    """Test _save_run method."""

    def test_save_run_with_store(self, mock_run, mock_store):
        """Test saving run with store."""
        compute = PyEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "module.func",
            }
        )

        compute._save_run(run=mock_run, store=mock_store)

        mock_store.save_run.assert_called_once_with(mock_run)

    def test_save_run_without_store(self, mock_run):
        """Test saving run without store (should not raise error)."""
        compute = PyEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "module.func",
            }
        )

        # Should not raise error
        compute._save_run(run=mock_run, store=None)


class TestComputeExportAndDescribe:
    """Test export and describe methods."""

    def test_export(self):
        """Test exporting compute to dict."""
        compute = PyEntrypointCompute.from_dict(
            {
                "name": "test_compute",
                "entrypoint": "module.function",
                "tags": {"env": "test"},
            }
        )

        exported = compute.export()

        assert exported["name"] == "test_compute"
        assert exported["kind"] == "py_entrypoint"
        assert exported["entrypoint"] == "module.function"
        assert exported["tags"] == {"env": "test"}

    def test_describe(self):
        """Test describing compute as string."""
        compute = PyEntrypointCompute.from_dict(
            {
                "name": "test_compute",
                "entrypoint": "module.function",
            }
        )

        description = compute.describe()

        assert isinstance(description, str)
        assert "test_compute" in description
        assert "py_entrypoint" in description


class TestIntegration:
    """Integration tests using real functions."""

    def test_execute_with_real_function(self, mock_store):
        """Test execution with a real Python function."""
        compute = PyEntrypointCompute.from_dict(
            {
                "name": "json_test",
                "entrypoint": "json.dumps",
            }
        )

        run = Run(compute_name="json_test")

        # This should execute json.dumps with the provided params
        params = {"obj": {"key": "value"}}
        compute.execute(run=run, store=mock_store, params=params)

        assert run.status == RunStatus.SUCCEEDED
        assert mock_store.save_run.call_count == 2

    def test_full_lifecycle(self, mock_store):
        """Test full lifecycle from creation to execution."""
        # Create compute
        compute = PyEntrypointCompute.from_dict(
            {
                "name": "test_compute",
                "entrypoint": "os.path.exists",
                "tags": {"env": "test"},
            }
        )

        # Create run
        run = Run(compute_name="test_compute")

        # Execute
        params = {"path": "/tmp"}
        compute.execute(run=run, store=mock_store, params=params)

        # Verify
        assert run.status == RunStatus.SUCCEEDED
        assert compute.name == "test_compute"
        assert compute.kind == ComputeKind.PY_ENTRYPOINT
