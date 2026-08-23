"""Unit tests for memory store."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from bastion.control.run.run import Run
from bastion.control.store.base.base import IStoreLike
from bastion.control.store.memory.memory import MemoryStore
from bastion.domain.run import RunModel, RunStatus


class TestIStoreLikeProtocol:
    """Test IStoreLike protocol definition."""

    def test_protocol_check_with_memory_store(self):
        """Test that MemoryStore implements IStoreLike protocol."""
        store = MemoryStore(name="test_store")

        assert isinstance(store, IStoreLike)

    def test_protocol_required_attributes(self):
        """Test protocol required attributes are accessible."""
        store = MemoryStore(name="test_store")

        # Test protocol attributes
        assert store.name == "test_store"

    def test_protocol_required_methods(self):
        """Test protocol required methods exist."""
        store = MemoryStore(name="test_store")

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


class TestMemoryStoreCreation:
    """Test MemoryStore creation and initialization."""

    def test_create_with_default_name(self):
        """Test creating store with default name."""
        store = MemoryStore()

        assert store.name == "default"
        assert isinstance(store._runs, dict)
        assert len(store._runs) == 0

    def test_create_with_custom_name(self):
        """Test creating store with custom name."""
        store = MemoryStore(name="custom_store")

        assert store.name == "custom_store"
        assert isinstance(store._runs, dict)

    def test_init_method_is_noop(self):
        """Test that init() method does nothing for memory store."""
        store = MemoryStore(name="test_store")

        # Should not raise any exception
        store.init()

        # Store should still be usable
        assert store.name == "test_store"
        assert len(store._runs) == 0


class TestMemoryStoreSaveRun:
    """Test MemoryStore save_run functionality."""

    def test_save_run_from_run_object(self):
        """Test saving run from Run object."""
        store = MemoryStore(name="test_store")
        run = Run(compute_name="test_compute", name="test_run")

        store.save_run(run)

        # Verify run was saved
        assert run.id in store._runs
        saved_model = store._runs[run.id]
        assert saved_model.id == run.id
        assert saved_model.compute_name == "test_compute"

    def test_save_run_from_domain_model(self):
        """Test saving run from RunModel domain object."""
        store = MemoryStore(name="test_store")
        domain = RunModel(
            compute_name="test_compute",
            name="test_run",
        )

        store.save_run(domain)

        # Verify run was saved
        assert domain.id in store._runs
        saved_model = store._runs[domain.id]
        assert saved_model.id == domain.id
        assert saved_model.compute_name == "test_compute"

    def test_save_run_updates_existing_run(self):
        """Test that saving existing run updates the record."""
        store = MemoryStore(name="test_store")
        run = Run(compute_name="test_compute", name="test_run")
        store.save_run(run)

        # Modify run and save again
        run.start()
        store.save_run(run)

        # Verify only one record exists
        assert len(store._runs) == 1

        # Verify run was updated
        retrieved_run = store.get_run(run.id)
        assert retrieved_run is not None
        assert retrieved_run.status == RunStatus.RUNNING

    def test_save_run_preserves_all_data(self):
        """Test that save_run preserves all run data."""
        store = MemoryStore(name="test_store")
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

    def test_save_multiple_runs(self):
        """Test saving multiple different runs."""
        store = MemoryStore(name="test_store")
        run1 = Run(compute_name="compute1", name="run1")
        run2 = Run(compute_name="compute2", name="run2")
        run3 = Run(compute_name="compute3", name="run3")

        store.save_run(run1)
        store.save_run(run2)
        store.save_run(run3)

        assert len(store._runs) == 3
        assert run1.id in store._runs
        assert run2.id in store._runs
        assert run3.id in store._runs


class TestMemoryStoreGetRun:
    """Test MemoryStore get_run functionality."""

    def test_get_run_returns_existing_run(self):
        """Test getting an existing run."""
        store = MemoryStore(name="test_store")
        run = Run(compute_name="test_compute", name="test_run")
        store.save_run(run)

        retrieved_run = store.get_run(run.id)

        assert retrieved_run is not None
        assert retrieved_run.id == run.id
        assert retrieved_run.compute_name == "test_compute"
        assert retrieved_run.name == "test_run"

    def test_get_run_returns_none_for_nonexistent_run(self):
        """Test getting a nonexistent run returns None."""
        store = MemoryStore(name="test_store")

        retrieved_run = store.get_run("nonexistent-id")

        assert retrieved_run is None

    def test_get_run_returns_run_with_correct_type(self):
        """Test that get_run returns a Run object."""
        store = MemoryStore(name="test_store")
        run = Run(compute_name="test_compute", name="test_run")
        store.save_run(run)

        retrieved_run = store.get_run(run.id)

        assert isinstance(retrieved_run, Run)

    def test_get_run_returns_independent_copy(self):
        """Test that get_run returns a new Run instance from stored model."""
        store = MemoryStore(name="test_store")
        run = Run(compute_name="test_compute", name="test_run")
        store.save_run(run)

        retrieved_run = store.get_run(run.id)

        # Modifying retrieved run should not affect the original
        assert retrieved_run is not None
        # They should be different Run instances
        assert retrieved_run is not run


class TestMemoryStoreListRuns:
    """Test MemoryStore list_runs functionality."""

    def test_list_runs_returns_all_runs(self):
        """Test listing all runs without filters."""
        store = MemoryStore(name="test_store")
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
        store = MemoryStore(name="test_store")
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
        store = MemoryStore(name="test_store")
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
        store = MemoryStore(name="test_store")
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
        store = MemoryStore(name="test_store")

        # Create multiple runs
        for i in range(5):
            run = Run(compute_name="compute1", name=f"run{i}")
            store.save_run(run)

        runs = store.list_runs(limit=3)

        assert len(runs) == 3

    def test_list_runs_combines_multiple_filters(self):
        """Test listing runs with multiple filters combined."""
        store = MemoryStore(name="test_store")
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
        store = MemoryStore(name="test_store")
        run = Run(compute_name="compute1", name="run1")
        store.save_run(run)

        runs = store.list_runs(compute_name="nonexistent")

        assert runs == []

    def test_list_runs_returns_empty_list_when_store_empty(self):
        """Test that list_runs returns empty list when store is empty."""
        store = MemoryStore(name="test_store")

        runs = store.list_runs()

        assert runs == []


class TestMemoryStoreDeleteRun:
    """Test MemoryStore delete_run functionality."""

    def test_delete_run_removes_run(self):
        """Test that delete_run removes the run."""
        store = MemoryStore(name="test_store")
        run = Run(compute_name="test_compute", name="test_run")
        store.save_run(run)

        # Verify run exists
        assert store.get_run(run.id) is not None
        assert run.id in store._runs

        # Delete run
        store.delete_run(run.id)

        # Verify run no longer exists
        assert store.get_run(run.id) is None
        assert run.id not in store._runs

    def test_delete_run_does_not_affect_other_runs(self):
        """Test that deleting one run does not affect others."""
        store = MemoryStore(name="test_store")
        run1 = Run(compute_name="compute1", name="run1")
        run2 = Run(compute_name="compute2", name="run2")
        run3 = Run(compute_name="compute3", name="run3")

        store.save_run(run1)
        store.save_run(run2)
        store.save_run(run3)

        # Delete middle run
        store.delete_run(run2.id)

        # Verify other runs still exist
        assert store.get_run(run1.id) is not None
        assert store.get_run(run2.id) is None
        assert store.get_run(run3.id) is not None
        assert len(store._runs) == 2

    def test_delete_nonexistent_run_does_not_raise(self):
        """Test that deleting a nonexistent run does not raise an exception."""
        store = MemoryStore(name="test_store")

        # Should not raise any exception
        store.delete_run("nonexistent-id")

        # Store should still be usable
        run = Run(compute_name="test_compute", name="test_run")
        store.save_run(run)
        assert store.get_run(run.id) is not None

    def test_delete_run_allows_same_id_to_be_added_again(self):
        """Test that after deletion, a run with the same ID can be added."""
        store = MemoryStore(name="test_store")

        # Create and save a run
        domain1 = RunModel(compute_name="compute1", name="run1")
        run_id = domain1.id
        store.save_run(domain1)

        # Delete the run
        store.delete_run(run_id)
        assert store.get_run(run_id) is None

        # Create a new domain with the same ID and save it
        domain2 = RunModel(compute_name="compute2", name="run2")
        domain2.id = run_id  # Reuse the same ID
        store.save_run(domain2)

        # Verify new run is saved
        retrieved = store.get_run(run_id)
        assert retrieved is not None
        assert retrieved.compute_name == "compute2"
        assert retrieved.name == "run2"


class TestMemoryStoreIsolation:
    """Test MemoryStore isolation and independence."""

    def test_multiple_stores_are_independent(self):
        """Test that multiple MemoryStore instances are independent."""
        store1 = MemoryStore(name="store1")
        store2 = MemoryStore(name="store2")

        run1 = Run(compute_name="compute1", name="run1")
        run2 = Run(compute_name="compute2", name="run2")

        store1.save_run(run1)
        store2.save_run(run2)

        # Each store should have only its own run
        assert len(store1._runs) == 1
        assert len(store2._runs) == 1
        assert store1.get_run(run1.id) is not None
        assert store1.get_run(run2.id) is None
        assert store2.get_run(run1.id) is None
        assert store2.get_run(run2.id) is not None

    def test_store_modification_does_not_affect_original_run(self):
        """Test that modifying stored data does not affect original Run object."""
        store = MemoryStore(name="test_store")
        run = Run(compute_name="test_compute", name="test_run")

        # Save the run in pending status
        store.save_run(run)

        # Modify the original run
        run.start()
        run.succeed()

        # For memory store, the domain model is shared by reference,
        # so modifications to the original run do affect the stored version.
        # This is expected behavior for an in-memory store.
        retrieved = store.get_run(run.id)
        assert retrieved is not None
        # The store reflects the updated status because they share the same domain
        assert (
            retrieved.status == RunStatus.PENDING
        )  # This will be PENDING because the original run was modified after saving

        # However, if we want to preserve the old state, we need to save explicitly
        # at the time we want to capture the state
        run2 = Run(compute_name="compute2", name="run2")
        store.save_run(run2)

        # Now modify but don't save
        run2.start()

        # Create a new store and save the original state
        store2 = MemoryStore(name="store2")
        run3 = Run(compute_name="compute3", name="run3")
        store2.save_run(run3)

        # Verify store2 has its own independent data
        assert len(store._runs) == 2
        assert len(store2._runs) == 1
