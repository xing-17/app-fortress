"""Unit tests for PyAsyncEntrypoint compute."""

from __future__ import annotations

import signal
import time
from multiprocessing import Queue
from typing import Any
from unittest.mock import Mock, patch

import pytest

from bastion.control.compute.base.base import IComputeLike
from bastion.control.compute.pyasyncentrypoint import (
    PyAsyncEntrypointCompute,
    PyAsyncEntrypointModel,
    run_in_async,
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
    run.cancel = Mock()
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


# Helper functions for testing
def sample_success_function(message: str = "success") -> dict[str, Any]:
    """Sample function that succeeds."""
    return {"status": message, "success": True}


def sample_failure_function(message: str = "error") -> None:
    """Sample function that raises an exception."""
    raise RuntimeError(message)


def sample_slow_function(duration: float = 0.1) -> dict[str, Any]:
    """Sample function that takes time to execute."""
    time.sleep(float(duration))
    return {"status": "completed", "duration": duration}


class TestRunInAsync:
    """Test run_in_async helper function."""

    def test_run_in_async_success(self):
        """Test successful execution in async."""
        queue = Queue()
        entrypoint = "bastion.control.compute.pyasyncentrypoint.tests.test_pyasyncentrypoint_unit.sample_success_function"
        params = {"message": "test_success"}

        run_in_async(entrypoint, params, queue)

        success, exc = queue.get(timeout=1)
        assert success is True
        assert exc is None

    def test_run_in_async_with_exception(self):
        """Test exception handling in async."""
        queue = Queue()
        entrypoint = "bastion.control.compute.pyasyncentrypoint.tests.test_pyasyncentrypoint_unit.sample_failure_function"
        params = {"message": "test_error"}

        run_in_async(entrypoint, params, queue)

        success, exc = queue.get(timeout=1)
        assert success is False
        assert isinstance(exc, RuntimeError)
        assert str(exc) == "test_error"

    def test_run_in_async_invalid_entrypoint(self):
        """Test invalid entrypoint handling."""
        queue = Queue()
        entrypoint = "nonexistent.module.function"
        params = {}

        run_in_async(entrypoint, params, queue)

        success, exc = queue.get(timeout=1)
        assert success is False
        assert isinstance(exc, (ImportError, ModuleNotFoundError))

    def test_run_in_async_invalid_function(self):
        """Test invalid function name handling."""
        queue = Queue()
        entrypoint = "bastion.control.compute.pyasyncentrypoint.tests.test_pyasyncentrypoint_unit.nonexistent_function"
        params = {}

        run_in_async(entrypoint, params, queue)

        success, exc = queue.get(timeout=1)
        assert success is False
        assert isinstance(exc, AttributeError)


class TestPyAsyncEntrypointModel:
    """Test PyAsyncEntrypointModel domain model."""

    def test_create_model(self):
        """Test creating a PyAsyncEntrypointModel."""
        model = PyAsyncEntrypointModel(
            name="test_compute",
            entrypoint="bastion.control.compute.pyasyncentrypoint.test_func",
        )

        assert model.name == "test_compute"
        assert model.kind == ComputeKind.PY_ASYNC_ENTRYPOINT
        assert model.entrypoint == "bastion.control.compute.pyasyncentrypoint.test_func"

    def test_model_kind_is_py_async_entrypoint(self):
        """Test that model kind is PY_ASYNC_ENTRYPOINT."""
        model = PyAsyncEntrypointModel(
            name="test",
            entrypoint="module.func",
        )

        assert model.kind == ComputeKind.PY_ASYNC_ENTRYPOINT

    def test_model_export(self):
        """Test exporting model to dict."""
        model = PyAsyncEntrypointModel(
            name="test_compute",
            entrypoint="module.function",
            tags={"env": "test"},
        )

        exported = model.export()

        assert exported["name"] == "test_compute"
        assert exported["kind"] == "py_async_entrypoint"
        assert exported["entrypoint"] == "module.function"
        assert exported["tags"] == {"env": "test"}

    def test_model_with_tags(self):
        """Test creating model with tags."""
        model = PyAsyncEntrypointModel(
            name="compute",
            entrypoint="module.func",
            tags={"version": "1.0", "team": "data"},
        )

        assert model.tags == {"version": "1.0", "team": "data"}


class TestPyAsyncEntrypointComputeCreation:
    """Test PyAsyncEntrypointCompute creation and initialization."""

    def test_create_from_dict(self):
        """Test creating compute from dictionary."""
        data = {
            "name": "test_compute",
            "entrypoint": "module.function",
        }

        compute = PyAsyncEntrypointCompute.from_dict(data)

        assert compute.name == "test_compute"
        assert compute.domain.entrypoint == "module.function"
        assert compute.kind == ComputeKind.PY_ASYNC_ENTRYPOINT
        assert compute._process is None
        assert compute._queue is None

    def test_create_from_domain(self):
        """Test creating compute from domain model."""
        domain = PyAsyncEntrypointModel(
            name="test_compute",
            entrypoint="module.func",
        )

        compute = PyAsyncEntrypointCompute.from_domain(domain)

        assert compute.name == "test_compute"
        assert compute.domain.entrypoint == "module.func"
        assert isinstance(compute.domain, PyAsyncEntrypointModel)
        assert compute._process is None
        assert compute._queue is None

    def test_create_with_init(self):
        """Test creating compute directly with __init__."""
        compute = PyAsyncEntrypointCompute(
            name="test_compute",
            entrypoint="module.function",
            tags={"env": "test"},
        )

        assert compute.name == "test_compute"
        assert compute.domain.entrypoint == "module.function"
        assert compute.tags == {"env": "test"}
        assert compute._process is None
        assert compute._queue is None

    def test_implements_icomputelike_protocol(self):
        """Test that PyAsyncEntrypointCompute implements IComputeLike protocol."""
        compute = PyAsyncEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "module.func",
            }
        )

        assert isinstance(compute, IComputeLike)

    def test_compute_attributes(self):
        """Test compute required attributes."""
        compute = PyAsyncEntrypointCompute.from_dict(
            {
                "name": "test_compute",
                "entrypoint": "module.function",
                "tags": {"env": "prod"},
            }
        )

        assert compute.name == "test_compute"
        assert compute.kind == ComputeKind.PY_ASYNC_ENTRYPOINT
        assert compute.tags == {"env": "prod"}
        assert hasattr(compute, "domain")
        assert hasattr(compute, "_process")
        assert hasattr(compute, "_queue")


class TestExecuteMethod:
    """Test execute method with multiprocessing."""

    def test_execute_success(self, mock_run, mock_store):
        """Test successful execution."""
        compute = PyAsyncEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "bastion.control.compute.pyasyncentrypoint.tests.test_pyasyncentrypoint_unit.sample_success_function",
            }
        )

        params = {"message": "test_success"}
        compute.execute(run=mock_run, store=mock_store, params=params)

        # Verify run lifecycle
        mock_run.start.assert_called_once()
        mock_run.succeed.assert_called_once()
        mock_run.fail.assert_not_called()
        mock_run.cancel.assert_not_called()

        # Verify store was called twice (before and after execution)
        assert mock_store.save_run.call_count == 2
        mock_store.save_run.assert_called_with(mock_run)

        # Process and queue should be cleaned up
        assert compute._process is None
        assert compute._queue is None

    def test_execute_without_params(self, mock_run, mock_store):
        """Test execution without parameters."""
        compute = PyAsyncEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "bastion.control.compute.pyasyncentrypoint.tests.test_pyasyncentrypoint_unit.sample_success_function",
            }
        )

        compute.execute(run=mock_run, store=mock_store)

        # Should succeed with default params
        mock_run.start.assert_called_once()
        mock_run.succeed.assert_called_once()

    def test_execute_without_store(self, mock_run):
        """Test execution without store (no persistence)."""
        compute = PyAsyncEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "bastion.control.compute.pyasyncentrypoint.tests.test_pyasyncentrypoint_unit.sample_success_function",
            }
        )

        # Should not raise error even without store
        compute.execute(run=mock_run, store=None)

        mock_run.start.assert_called_once()
        mock_run.succeed.assert_called_once()

    def test_execute_failure(self, mock_run, mock_store):
        """Test execution failure handling."""
        compute = PyAsyncEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "bastion.control.compute.pyasyncentrypoint.tests.test_pyasyncentrypoint_unit.sample_failure_function",
            }
        )

        params = {"message": "test_error"}

        with pytest.raises(RuntimeError, match="test_error"):
            compute.execute(run=mock_run, store=mock_store, params=params)

        # Verify run lifecycle on failure
        mock_run.start.assert_called_once()
        mock_run.fail.assert_called_once()
        mock_run.succeed.assert_not_called()

        # Verify store was called twice (before and after execution)
        assert mock_store.save_run.call_count == 2

        # Process and queue should be cleaned up
        assert compute._process is None
        assert compute._queue is None

    def test_execute_slow_function(self, mock_run, mock_store):
        """Test execution of slow function (tests process waiting)."""
        compute = PyAsyncEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "bastion.control.compute.pyasyncentrypoint.tests.test_pyasyncentrypoint_unit.sample_slow_function",
            }
        )

        params = {"duration": "0.2"}
        start_time = time.time()
        compute.execute(run=mock_run, store=mock_store, params=params)
        elapsed = time.time() - start_time

        # Should wait for process to complete
        assert elapsed >= 0.2
        mock_run.succeed.assert_called_once()

    @patch("bastion.control.compute.pyasyncentrypoint.pyasyncentrypoint.Process")
    def test_execute_process_exitcode_handling(self, mock_process_class, mock_run, mock_store):
        """Test handling of different process exit codes."""
        # Test normal exit (exitcode 0, but function failed)
        mock_process = Mock()
        mock_process.exitcode = 0
        mock_process.is_alive.return_value = False
        mock_process_class.return_value = mock_process

        compute = PyAsyncEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "module.func",
            }
        )

        # Mock queue to return failure
        with patch.object(compute, "_queue", Mock()):
            compute._queue.get_nowait = Mock(return_value=(False, RuntimeError("test")))

            with pytest.raises(RuntimeError):
                compute.execute(run=mock_run, store=mock_store)

            mock_run.fail.assert_called_once()

    @patch("bastion.control.compute.pyasyncentrypoint.pyasyncentrypoint.Process")
    def test_execute_sigterm_handling(self, mock_process_class, mock_run, mock_store):
        """Test handling of SIGTERM (process termination)."""
        mock_process = Mock()
        mock_process.exitcode = -signal.SIGTERM
        mock_process.is_alive.return_value = False
        mock_process_class.return_value = mock_process

        compute = PyAsyncEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "module.func",
            }
        )

        with patch.object(compute, "_queue", Mock()):
            compute.execute(run=mock_run, store=mock_store)

            mock_run.cancel.assert_called_once()
            mock_run.succeed.assert_not_called()
            mock_run.fail.assert_not_called()

    @patch("bastion.control.compute.pyasyncentrypoint.pyasyncentrypoint.Process")
    def test_execute_abnormal_exitcode(self, mock_process_class, mock_run, mock_store):
        """Test handling of abnormal exit codes."""
        mock_process = Mock()
        mock_process.exitcode = 1  # Non-zero, non-SIGTERM exit code
        mock_process.is_alive.return_value = False
        mock_process_class.return_value = mock_process

        compute = PyAsyncEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "module.func",
            }
        )

        with patch.object(compute, "_queue", Mock()):
            compute.execute(run=mock_run, store=mock_store)

            mock_run.fail.assert_called_once()
            mock_run.succeed.assert_not_called()


class TestCancelMethod:
    """Test cancel method."""

    @patch("bastion.control.compute.pyasyncentrypoint.pyasyncentrypoint.Process")
    def test_cancel_running_process(self, mock_process_class):
        """Test canceling a running process."""
        mock_process = Mock()
        mock_process.is_alive.return_value = True
        mock_process_class.return_value = mock_process

        compute = PyAsyncEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "module.func",
            }
        )

        # Set up a running process
        compute._process = mock_process

        compute.cancel()

        # Verify process was terminated
        mock_process.terminate.assert_called_once()
        mock_process.join.assert_called_once()

    def test_cancel_no_process(self):
        """Test cancel when no process is running."""
        compute = PyAsyncEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "module.func",
            }
        )

        # Should not raise any error
        compute.cancel()

    @patch("bastion.control.compute.pyasyncentrypoint.pyasyncentrypoint.Process")
    def test_cancel_dead_process(self, mock_process_class):
        """Test cancel when process is already dead."""
        mock_process = Mock()
        mock_process.is_alive.return_value = False
        mock_process_class.return_value = mock_process

        compute = PyAsyncEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "module.func",
            }
        )

        compute._process = mock_process

        compute.cancel()

        # Should not try to terminate a dead process
        mock_process.terminate.assert_not_called()

    def test_cancel_with_kwargs(self):
        """Test cancel with keyword arguments (should be accepted)."""
        compute = PyAsyncEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "module.func",
            }
        )

        # Should not raise any error
        compute.cancel(run=Mock(), store=Mock())


class TestSaveRunMethod:
    """Test _save_run method."""

    def test_save_run_with_store(self, mock_run, mock_store):
        """Test saving run with store."""
        compute = PyAsyncEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "module.func",
            }
        )

        compute._save_run(mock_run, mock_store)

        mock_store.save_run.assert_called_once_with(mock_run)

    def test_save_run_without_store(self, mock_run):
        """Test saving run without store (should not raise error)."""
        compute = PyAsyncEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "module.func",
            }
        )

        # Should not raise error
        compute._save_run(mock_run, None)


class TestIntegration:
    """Integration tests for PyAsyncEntrypointCompute."""

    def test_full_execution_lifecycle(self, mock_run, mock_store):
        """Test complete execution lifecycle."""
        compute = PyAsyncEntrypointCompute.from_dict(
            {
                "name": "test_compute",
                "entrypoint": "bastion.control.compute.pyasyncentrypoint.tests.test_pyasyncentrypoint_unit.sample_success_function",
            }
        )

        # Initial state
        assert compute._process is None
        assert compute._queue is None

        # Execute
        params = {"message": "integration_test"}
        compute.execute(run=mock_run, store=mock_store, params=params)

        # Final state - should be cleaned up
        assert compute._process is None
        assert compute._queue is None

        # Verify run lifecycle
        mock_run.start.assert_called_once()
        mock_run.succeed.assert_called_once()
        assert mock_store.save_run.call_count == 2

    def test_multiple_executions(self, mock_store):
        """Test multiple sequential executions."""
        compute = PyAsyncEntrypointCompute.from_dict(
            {
                "name": "test_compute",
                "entrypoint": "bastion.control.compute.pyasyncentrypoint.tests.test_pyasyncentrypoint_unit.sample_success_function",
            }
        )

        # Execute multiple times
        for i in range(3):
            mock_run = Mock()
            mock_run.start = Mock()
            mock_run.succeed = Mock()
            mock_run.fail = Mock()

            compute.execute(run=mock_run, store=mock_store, params={"message": f"run_{i}"})

            mock_run.succeed.assert_called_once()
            # Should clean up after each execution
            assert compute._process is None
            assert compute._queue is None

    def test_execution_with_actual_run(self, mock_store):
        """Test execution with actual Run object (not mock)."""
        compute = PyAsyncEntrypointCompute.from_dict(
            {
                "name": "test_compute",
                "entrypoint": "bastion.control.compute.pyasyncentrypoint.tests.test_pyasyncentrypoint_unit.sample_success_function",
            }
        )

        # Create actual Run object
        run = Run(
            compute_name="test_compute",
            name="test_run",
        )

        initial_status = run.status
        compute.execute(run=run, store=mock_store)

        # Verify status changed
        assert initial_status == RunStatus.PENDING
        assert run.status == RunStatus.SUCCEEDED


class TestErrorScenarios:
    """Test various error scenarios."""

    def test_invalid_entrypoint_format(self, mock_run, mock_store):
        """Test entrypoint without module path."""
        compute = PyAsyncEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "just_function_name",
            }
        )

        with pytest.raises(ValueError):
            compute.execute(run=mock_run, store=mock_store)

        mock_run.fail.assert_called_once()

    def test_module_not_found(self, mock_run, mock_store):
        """Test with non-existent module."""
        compute = PyAsyncEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "nonexistent.module.function",
            }
        )

        with pytest.raises((ImportError, ModuleNotFoundError)):
            compute.execute(run=mock_run, store=mock_store)

        mock_run.fail.assert_called_once()

    def test_function_not_found(self, mock_run, mock_store):
        """Test with non-existent function."""
        compute = PyAsyncEntrypointCompute.from_dict(
            {
                "name": "test",
                "entrypoint": "bastion.control.compute.pyasyncentrypoint.tests.test_pyasyncentrypoint_unit.nonexistent_function",
            }
        )

        with pytest.raises(AttributeError):
            compute.execute(run=mock_run, store=mock_store)

        mock_run.fail.assert_called_once()
