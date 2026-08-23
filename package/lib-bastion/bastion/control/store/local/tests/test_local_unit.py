"""Unit tests for local store."""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from bastion.control.run.run import Run
from bastion.control.store.base.base import IStoreLike
from bastion.control.store.local.local import LocalStore
from bastion.domain.run import RunModel, RunStatus


class TestIStoreLikeProtocol:
    """Test IStoreLike protocol definition."""

    def test_protocol_check_with_local_store(self):
        """Test that LocalStore implements IStoreLike protocol."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalStore(name="test_store", path=tmpdir)

            assert isinstance(store, IStoreLike)
            store.close()

    def test_protocol_required_attributes(self):
        """Test protocol required attributes are accessible."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalStore(name="test_store", path=tmpdir)

            # Test protocol attributes
            assert store.name == "test_store"
            assert isinstance(store.path, Path)
            store.close()

    def test_protocol_required_methods(self):
        """Test protocol required methods exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalStore(name="test_store", path=tmpdir)

            # Test protocol methods
            assert hasattr(store, "init")
            assert hasattr(store, "save_run")
            assert hasattr(store, "get_run")
            assert hasattr(store, "list_runs")
            assert hasattr(store, "delete_run")
            assert callable(store.init)
            assert callable(store.save_run)
            assert callable(store.get_run)
            assert callable(store.list_runs)
            assert callable(store.delete_run)
            store.close()

    def test_protocol_context_manager_methods(self):
        """Test protocol context manager methods exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalStore(name="test_store", path=tmpdir)

            # Test context manager protocol
            assert hasattr(store, "__enter__")
            assert hasattr(store, "__exit__")
            assert callable(store.__enter__)
            assert callable(store.__exit__)
            store.close()


class TestLocalStoreCreation:
    """Test LocalStore creation and initialization."""

    def test_create_with_name_only(self):
        """Test creating store with name only creates default path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Change to temp directory
            import os

            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                store = LocalStore(name="test_store")

                assert store.name == "test_store"
                assert store.path.exists()
                assert store.path.name == "test_store.db"
                assert ".bastion" in str(store.path)
                store.close()
            finally:
                os.chdir(original_cwd)

    def test_create_with_directory_path(self):
        """Test creating store with directory path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalStore(name="test_store", path=tmpdir)

            assert store.name == "test_store"
            assert store.path.exists()
            assert store.path.parent == Path(tmpdir).resolve()
            assert store.path.name == "test_store.db"
            store.close()

    def test_create_with_file_path(self):
        """Test creating store with explicit file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "custom.db"
            store = LocalStore(name="test_store", path=db_path)

            assert store.name == "test_store"
            assert store.path.exists()
            assert store.path == db_path.resolve()
            store.close()

    def test_create_initializes_database(self):
        """Test that creating store initializes the database tables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalStore(name="test_store", path=tmpdir)

            # Query table existence
            result = store._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                [store._table_runs],
            ).fetchone()

            assert result is not None
            assert result[0] == store._table_runs
            store.close()

    def test_context_manager_entry_returns_store(self):
        """Test that context manager __enter__ returns the store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with LocalStore(name="test_store", path=tmpdir) as store:
                assert isinstance(store, LocalStore)
                assert store.name == "test_store"

    def test_context_manager_exit_closes_connection(self):
        """Test that context manager __exit__ closes the connection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with LocalStore(name="test_store", path=tmpdir) as store:
                conn = store._conn

            # Connection should be closed after exiting context
            with pytest.raises(Exception):
                conn.execute("SELECT 1")


class TestLocalStoreSaveRun:
    """Test LocalStore save_run functionality."""

    def test_save_run_from_run_object(self):
        """Test saving run from Run object."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with LocalStore(name="test_store", path=tmpdir) as store:
                run = Run(compute_name="test_compute", name="test_run")

                store.save_run(run)

                # Verify run was saved
                result = store._conn.execute(
                    f"SELECT id, compute_name FROM {store._table_runs} WHERE id = ?",
                    [run.id],
                ).fetchone()

                assert result is not None
                assert result[0] == run.id
                assert result[1] == "test_compute"

    def test_save_run_from_domain_model(self):
        """Test saving run from RunModel domain object."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with LocalStore(name="test_store", path=tmpdir) as store:
                domain = RunModel(
                    compute_name="test_compute",
                    name="test_run",
                )

                store.save_run(domain)

                # Verify run was saved
                result = store._conn.execute(
                    f"SELECT id, compute_name FROM {store._table_runs} WHERE id = ?",
                    [domain.id],
                ).fetchone()

                assert result is not None
                assert result[0] == domain.id
                assert result[1] == "test_compute"

    def test_save_run_updates_existing_run(self):
        """Test that saving existing run updates the record."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with LocalStore(name="test_store", path=tmpdir) as store:
                run = Run(compute_name="test_compute", name="test_run")
                store.save_run(run)

                # Modify run and save again
                run.start()
                store.save_run(run)

                # Verify only one record exists
                count = store._conn.execute(
                    f"SELECT COUNT(*) FROM {store._table_runs} WHERE id = ?",
                    [run.id],
                ).fetchone()[0]

                assert count == 1

                # Verify run was updated
                retrieved_run = store.get_run(run.id)
                assert retrieved_run is not None
                assert retrieved_run.status == RunStatus.RUNNING

    def test_save_run_preserves_all_data(self):
        """Test that save_run preserves all run data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with LocalStore(name="test_store", path=tmpdir) as store:
                run = Run(compute_name="test_compute", name="test_run")
                run.start()
                run.event("Test event", metadata={"key": "value"})

                store.save_run(run)
                retrieved_run = store.get_run(run.id)

                assert retrieved_run is not None
                assert retrieved_run.id == run.id
                assert retrieved_run.compute_name == run.compute_name
                assert retrieved_run.name == run.name
                assert retrieved_run.status == RunStatus.RUNNING
                assert retrieved_run.started_at is not None
                assert len(retrieved_run.events) == 1
                assert retrieved_run.events[0].message == "Test event"


class TestLocalStoreGetRun:
    """Test LocalStore get_run functionality."""

    def test_get_run_returns_existing_run(self):
        """Test getting an existing run."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with LocalStore(name="test_store", path=tmpdir) as store:
                run = Run(compute_name="test_compute", name="test_run")
                store.save_run(run)

                retrieved_run = store.get_run(run.id)

                assert retrieved_run is not None
                assert retrieved_run.id == run.id
                assert retrieved_run.compute_name == "test_compute"
                assert retrieved_run.name == "test_run"

    def test_get_run_returns_none_for_nonexistent_run(self):
        """Test getting a nonexistent run returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with LocalStore(name="test_store", path=tmpdir) as store:
                retrieved_run = store.get_run("nonexistent-id")

                assert retrieved_run is None

    def test_get_run_returns_run_with_correct_type(self):
        """Test that get_run returns a Run object."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with LocalStore(name="test_store", path=tmpdir) as store:
                run = Run(compute_name="test_compute", name="test_run")
                store.save_run(run)

                retrieved_run = store.get_run(run.id)

                assert isinstance(retrieved_run, Run)


class TestLocalStoreListRuns:
    """Test LocalStore list_runs functionality."""

    def test_list_runs_returns_all_runs(self):
        """Test listing all runs without filters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with LocalStore(name="test_store", path=tmpdir) as store:
                run1 = Run(compute_name="compute1", name="run1")
                run2 = Run(compute_name="compute2", name="run2")
                run3 = Run(compute_name="compute3", name="run3")

                store.save_run(run1)
                store.save_run(run2)
                store.save_run(run3)

                runs = store.list_runs()

                assert len(runs) == 3
                run_ids = [r.id for r in runs]
                assert run1.id in run_ids
                assert run2.id in run_ids
                assert run3.id in run_ids

    def test_list_runs_filters_by_compute_name(self):
        """Test listing runs filtered by compute_name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with LocalStore(name="test_store", path=tmpdir) as store:
                run1 = Run(compute_name="compute1", name="run1")
                run2 = Run(compute_name="compute1", name="run2")
                run3 = Run(compute_name="compute2", name="run3")

                store.save_run(run1)
                store.save_run(run2)
                store.save_run(run3)

                runs = store.list_runs(compute_name="compute1")

                assert len(runs) == 2
                assert all(r.compute_name == "compute1" for r in runs)

    def test_list_runs_filters_by_since(self):
        """Test listing runs filtered by since timestamp."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with LocalStore(name="test_store", path=tmpdir) as store:
                # Create runs with different timestamps
                now = datetime.now(UTC)

                # Create older run
                old_domain = RunModel(
                    compute_name="compute1",
                    name="old_run",
                )
                old_domain.created_at = now - timedelta(hours=2)
                store.save_run(old_domain)

                # Create newer run
                new_run = Run(compute_name="compute1", name="new_run")
                store.save_run(new_run)

                # Filter by timestamp
                since_time = now - timedelta(hours=1)
                runs = store.list_runs(since=since_time)

                assert len(runs) == 1
                assert runs[0].name == "new_run"

    def test_list_runs_filters_by_until(self):
        """Test listing runs filtered by until timestamp."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with LocalStore(name="test_store", path=tmpdir) as store:
                # Create runs with different timestamps
                now = datetime.now(UTC)

                # Create older run
                old_domain = RunModel(
                    compute_name="compute1",
                    name="old_run",
                )
                old_domain.created_at = now - timedelta(hours=2)
                store.save_run(old_domain)

                # Create newer run
                new_run = Run(compute_name="compute1", name="new_run")
                store.save_run(new_run)

                # Filter by timestamp
                until_time = now - timedelta(hours=1)
                runs = store.list_runs(until=until_time)

                assert len(runs) == 1
                assert runs[0].name == "old_run"

    def test_list_runs_filters_by_limit(self):
        """Test listing runs with limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with LocalStore(name="test_store", path=tmpdir) as store:
                # Create multiple runs
                for i in range(5):
                    run = Run(compute_name="compute1", name=f"run{i}")
                    store.save_run(run)

                runs = store.list_runs(limit=3)

                assert len(runs) == 3

    def test_list_runs_combines_multiple_filters(self):
        """Test listing runs with multiple filters combined."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with LocalStore(name="test_store", path=tmpdir) as store:
                now = datetime.now(UTC)

                # Create runs with different compute names and timestamps
                old_compute1 = RunModel(compute_name="compute1", name="old_c1")
                old_compute1.created_at = now - timedelta(hours=2)
                store.save_run(old_compute1)

                new_compute1 = Run(compute_name="compute1", name="new_c1")
                store.save_run(new_compute1)

                new_compute2 = Run(compute_name="compute2", name="new_c2")
                store.save_run(new_compute2)

                # Filter by compute_name and since
                since_time = now - timedelta(hours=1)
                runs = store.list_runs(compute_name="compute1", since=since_time)

                assert len(runs) == 1
                assert runs[0].name == "new_c1"

    def test_list_runs_returns_empty_list_when_no_matches(self):
        """Test that list_runs returns empty list when no runs match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with LocalStore(name="test_store", path=tmpdir) as store:
                run = Run(compute_name="compute1", name="run1")
                store.save_run(run)

                runs = store.list_runs(compute_name="nonexistent")

                assert runs == []


class TestLocalStoreDeleteRun:
    """Test LocalStore delete_run functionality."""

    def test_delete_run_removes_run(self):
        """Test that delete_run removes the run."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with LocalStore(name="test_store", path=tmpdir) as store:
                run = Run(compute_name="test_compute", name="test_run")
                store.save_run(run)

                # Verify run exists
                assert store.get_run(run.id) is not None

                # Delete run
                store.delete_run(run.id)

                # Verify run no longer exists
                assert store.get_run(run.id) is None

    def test_delete_run_does_not_affect_other_runs(self):
        """Test that deleting one run doesn't affect others."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with LocalStore(name="test_store", path=tmpdir) as store:
                run1 = Run(compute_name="compute1", name="run1")
                run2 = Run(compute_name="compute2", name="run2")

                store.save_run(run1)
                store.save_run(run2)

                # Delete run1
                store.delete_run(run1.id)

                # Verify run1 is deleted
                assert store.get_run(run1.id) is None

                # Verify run2 still exists
                assert store.get_run(run2.id) is not None

    def test_delete_nonexistent_run_does_not_raise(self):
        """Test that deleting a nonexistent run doesn't raise an error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with LocalStore(name="test_store", path=tmpdir) as store:
                # Should not raise an exception
                store.delete_run("nonexistent-id")


class TestLocalStoreIntegration:
    """Integration tests for LocalStore operations."""

    def test_full_run_lifecycle(self):
        """Test a complete run lifecycle with the store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with LocalStore(name="test_store", path=tmpdir) as store:
                # Create and save a run
                run = Run(compute_name="test_compute", name="test_run")
                store.save_run(run)

                # Start the run
                run.start()
                store.save_run(run)

                # Add events
                run.event("Event 1")
                run.event("Event 2", metadata={"step": 2})
                store.save_run(run)

                # Complete the run
                run.succeed()
                store.save_run(run)

                # Retrieve and verify
                retrieved_run = store.get_run(run.id)

                assert retrieved_run is not None
                assert retrieved_run.status == RunStatus.SUCCEEDED
                assert retrieved_run.started_at is not None
                assert retrieved_run.finished_at is not None
                assert len(retrieved_run.events) == 2

    def test_multiple_stores_with_different_names(self):
        """Test using multiple stores with different names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store1 = LocalStore(name="store1", path=tmpdir)
            store2 = LocalStore(name="store2", path=tmpdir)

            try:
                run1 = Run(compute_name="compute1", name="run1")
                run2 = Run(compute_name="compute2", name="run2")

                store1.save_run(run1)
                store2.save_run(run2)

                # Each store should only see its own runs
                assert store1.get_run(run1.id) is not None
                assert store1.get_run(run2.id) is None

                assert store2.get_run(run2.id) is not None
                assert store2.get_run(run1.id) is None
            finally:
                store1.close()
                store2.close()

    def test_store_persistence_across_connections(self):
        """Test that data persists across different store connections."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "persistent.db"

            # Create store and save run
            with LocalStore(name="test_store", path=db_path) as store:
                run = Run(compute_name="test_compute", name="test_run")
                store.save_run(run)
                run_id = run.id

            # Open new store connection
            with LocalStore(name="test_store", path=db_path) as store:
                retrieved_run = store.get_run(run_id)

                assert retrieved_run is not None
                assert retrieved_run.id == run_id
                assert retrieved_run.compute_name == "test_compute"
                assert retrieved_run.name == "test_run"
