"""
Unit tests for bastion.control.store.memory module.
"""

from bastion.control.run.run import RunStatus
from bastion.control.store.memory.memory import MemoryStore, MemoryStoreModel
from bastion.domain.store.base import StoreKind


class TestMemoryStoreModel:
    """Test MemoryStoreModel class."""

    def test_create_default_model(self):
        """Test creating MemoryStoreModel with defaults."""
        model = MemoryStoreModel(name="test_store")
        assert model.name == "test_store"
        assert model.kind == StoreKind.MEMORY


class TestMemoryStoreInitialization:
    """Test MemoryStore initialization and setup."""

    def test_create_store_basic(self):
        """Test creating a basic MemoryStore."""
        store = MemoryStore(name="test_store")
        assert store.name == "test_store"
        assert isinstance(store._bridges, dict)
        assert isinstance(store._runs, dict)
        assert len(store._bridges) == 0
        assert len(store._runs) == 0

    def test_create_store_with_name(self):
        """Test creating store with custom name."""
        store = MemoryStore(name="custom_store")
        assert store.name == "custom_store"

    def test_store_has_empty_dicts_on_init(self):
        """Test that store initializes with empty dictionaries."""
        store = MemoryStore(name="test_store")
        assert store._bridges == {}
        assert store._runs == {}


class TestMemoryStoreBridgeOperations:
    """Test MemoryStore bridge-related methods."""

    def test_save_bridge(self, store_basic, bridge_basic):
        """Test saving a bridge."""
        store_basic.save_bridge(bridge_basic)
        assert store_basic.check_bridge_exists("test_bridge")

    def test_save_bridge_with_bridge_object(self, store_basic, bridge_basic):
        """Test saving a Bridge object."""
        store_basic.save_bridge(bridge_basic)
        retrieved = store_basic.get_bridge("test_bridge")
        assert retrieved is not None
        assert retrieved.name == "test_bridge"

    def test_save_bridge_with_bridge_model(self, store_basic, bridge_basic):
        """Test saving a BridgeModel (domain object)."""
        bridge_model = bridge_basic.domain
        store_basic.save_bridge(bridge_model)
        assert store_basic.check_bridge_exists("test_bridge")

    def test_save_bridge_updates_existing(self, store_basic, bridge_basic):
        """Test that saving a bridge with same name updates it."""
        store_basic.save_bridge(bridge_basic)

        # Modify and save again
        bridge_basic.domain.description = "Updated description"
        store_basic.save_bridge(bridge_basic)

        retrieved = store_basic.get_bridge("test_bridge")
        assert retrieved.description == "Updated description"

    def test_get_bridge_exists(self, store_basic, bridge_basic):
        """Test getting an existing bridge."""
        store_basic.save_bridge(bridge_basic)
        retrieved = store_basic.get_bridge("test_bridge")

        assert retrieved is not None
        assert retrieved.name == "test_bridge"
        assert retrieved.description == "A test bridge"

    def test_get_bridge_not_exists(self, store_basic):
        """Test getting a non-existent bridge returns None."""
        retrieved = store_basic.get_bridge("nonexistent")
        assert retrieved is None

    def test_get_bridge_with_metadata(self, store_basic, bridge_with_metadata):
        """Test getting bridge preserves metadata."""
        store_basic.save_bridge(bridge_with_metadata)
        retrieved = store_basic.get_bridge("bridge_with_meta")

        assert retrieved is not None
        assert retrieved.metadata == {"version": "1.0", "author": "test"}
        assert retrieved.tags == {"env": "test", "team": "data"}

    def test_check_bridge_exists_true(self, store_basic, bridge_basic):
        """Test check_bridge_exists returns True for existing bridge."""
        store_basic.save_bridge(bridge_basic)
        assert store_basic.check_bridge_exists("test_bridge") is True

    def test_check_bridge_exists_false(self, store_basic):
        """Test check_bridge_exists returns False for non-existent bridge."""
        assert store_basic.check_bridge_exists("nonexistent") is False

    def test_list_bridges_empty(self, store_basic):
        """Test list_bridges returns empty list when no bridges exist."""
        bridges = store_basic.list_bridges()
        assert bridges == []
        assert isinstance(bridges, list)

    def test_list_bridges_single(self, store_basic, bridge_basic):
        """Test list_bridges with single bridge."""
        store_basic.save_bridge(bridge_basic)
        bridges = store_basic.list_bridges()

        assert len(bridges) == 1
        assert bridges[0].name == "test_bridge"

    def test_list_bridges_multiple(self, store_basic, multiple_bridges):
        """Test list_bridges with multiple bridges."""
        for bridge in multiple_bridges:
            store_basic.save_bridge(bridge)

        bridges = store_basic.list_bridges()
        assert len(bridges) == 5
        bridge_names = [b.name for b in bridges]
        assert "bridge_0" in bridge_names
        assert "bridge_4" in bridge_names

    def test_list_bridges_with_limit(self, store_basic, multiple_bridges):
        """Test list_bridges with limit parameter."""
        for bridge in multiple_bridges:
            store_basic.save_bridge(bridge)

        bridges = store_basic.list_bridges(limit=3)
        assert len(bridges) == 3

    def test_list_bridges_limit_zero(self, store_basic, multiple_bridges):
        """Test list_bridges with limit of 0."""
        for bridge in multiple_bridges:
            store_basic.save_bridge(bridge)

        bridges = store_basic.list_bridges(limit=0)
        assert len(bridges) == 0

    def test_list_bridges_limit_none(self, store_basic, multiple_bridges):
        """Test list_bridges with limit of None returns all bridges."""
        for bridge in multiple_bridges:
            store_basic.save_bridge(bridge)

        bridges = store_basic.list_bridges(limit=None)
        assert len(bridges) == 5


class TestMemoryStoreRunOperations:
    """Test MemoryStore run-related methods."""

    def test_save_run(self, store_basic, run_basic):
        """Test saving a run."""
        store_basic.save_run(run_basic)
        assert store_basic.check_run_exists(run_basic.id)

    def test_save_run_with_run_object(self, store_basic, run_basic):
        """Test saving a Run object."""
        store_basic.save_run(run_basic)
        retrieved = store_basic.get_run(run_basic.id)
        assert retrieved is not None
        assert retrieved.id == run_basic.id
        assert retrieved.bridge_name == "test_bridge"

    def test_save_run_with_run_model(self, store_basic, run_basic):
        """Test saving a RunModel (domain object)."""
        run_model = run_basic.domain
        store_basic.save_run(run_model)
        assert store_basic.check_run_exists(run_basic.id)

    def test_save_run_updates_existing(self, store_basic, run_basic):
        """Test that saving a run with same ID updates it."""
        store_basic.save_run(run_basic)

        # Modify and save again
        run_basic.start()
        store_basic.save_run(run_basic)

        retrieved = store_basic.get_run(run_basic.id)
        assert retrieved.status == RunStatus.RUNNING
        assert retrieved.started_at is not None

    def test_get_run_exists(self, store_basic, run_basic):
        """Test getting an existing run."""
        store_basic.save_run(run_basic)
        retrieved = store_basic.get_run(run_basic.id)

        assert retrieved is not None
        assert retrieved.id == run_basic.id
        assert retrieved.bridge_name == "test_bridge"
        assert retrieved.name == "test_run"

    def test_get_run_not_exists(self, store_basic):
        """Test getting a non-existent run returns None."""
        retrieved = store_basic.get_run("run-nonexistent123")
        assert retrieved is None

    def test_get_run_with_status(self, store_basic, run_with_status):
        """Test getting run preserves status."""
        store_basic.save_run(run_with_status)
        retrieved = store_basic.get_run(run_with_status.id)

        assert retrieved is not None
        assert retrieved.status == RunStatus.RUNNING
        assert retrieved.started_at is not None

    def test_check_run_exists_true(self, store_basic, run_basic):
        """Test check_run_exists returns True for existing run."""
        store_basic.save_run(run_basic)
        assert store_basic.check_run_exists(run_basic.id) is True

    def test_check_run_exists_false(self, store_basic):
        """Test check_run_exists returns False for non-existent run."""
        assert store_basic.check_run_exists("run-nonexistent123") is False

    def test_list_runs_empty(self, store_basic):
        """Test list_runs returns empty list when no runs exist."""
        runs = store_basic.list_runs()
        assert runs == []
        assert isinstance(runs, list)

    def test_list_runs_single(self, store_basic, run_basic):
        """Test list_runs with single run."""
        store_basic.save_run(run_basic)
        runs = store_basic.list_runs()

        assert len(runs) == 1
        assert runs[0].id == run_basic.id

    def test_list_runs_multiple(self, store_basic, multiple_runs):
        """Test list_runs with multiple runs."""
        for run in multiple_runs:
            store_basic.save_run(run)

        runs = store_basic.list_runs()
        assert len(runs) == 5

    def test_list_runs_ordered_by_created_at(self, store_basic, multiple_runs):
        """Test list_runs returns runs ordered by created_at DESC."""
        for run in multiple_runs:
            store_basic.save_run(run)

        runs = store_basic.list_runs()
        # Should be in descending order (newest first)
        for i in range(len(runs) - 1):
            assert runs[i].created_at >= runs[i + 1].created_at

    def test_list_runs_filter_by_bridge_name(self, store_basic, multiple_runs):
        """Test list_runs filtered by bridge_name."""
        # Create runs for different bridges
        for i, run in enumerate(multiple_runs):
            if i < 3:
                run.domain.bridge_name = "bridge_a"
            else:
                run.domain.bridge_name = "bridge_b"
            store_basic.save_run(run)

        runs_a = store_basic.list_runs(bridge_name="bridge_a")
        runs_b = store_basic.list_runs(bridge_name="bridge_b")

        assert len(runs_a) == 3
        assert len(runs_b) == 2
        assert all(r.bridge_name == "bridge_a" for r in runs_a)
        assert all(r.bridge_name == "bridge_b" for r in runs_b)

    def test_list_runs_with_limit(self, store_basic, multiple_runs):
        """Test list_runs with limit parameter."""
        for run in multiple_runs:
            store_basic.save_run(run)

        runs = store_basic.list_runs(limit=3)
        assert len(runs) == 3

    def test_list_runs_with_bridge_name_and_limit(self, store_basic, multiple_runs):
        """Test list_runs with both bridge_name and limit."""
        for run in multiple_runs:
            store_basic.save_run(run)

        runs = store_basic.list_runs(bridge_name="test_bridge", limit=2)
        assert len(runs) == 2
        assert all(r.bridge_name == "test_bridge" for r in runs)

    def test_list_runs_nonexistent_bridge(self, store_basic, multiple_runs):
        """Test list_runs with non-existent bridge_name returns empty list."""
        for run in multiple_runs:
            store_basic.save_run(run)

        runs = store_basic.list_runs(bridge_name="nonexistent_bridge")
        assert runs == []

    def test_list_runs_limit_none(self, store_basic, multiple_runs):
        """Test list_runs with limit of None returns all runs."""
        for run in multiple_runs:
            store_basic.save_run(run)

        runs = store_basic.list_runs(limit=None)
        assert len(runs) == 5


class TestMemoryStoreExport:
    """Test MemoryStore export functionality."""

    def test_export_empty_store(self, store_basic):
        """Test export with empty store."""
        exported = store_basic.export()

        assert exported["name"] == "test_store"
        assert exported["kind"] == StoreKind.MEMORY
        assert "counts" in exported
        assert exported["counts"]["bridges"] == 0
        assert exported["counts"]["runs"] == 0

    def test_export_with_bridges(self, store_basic, multiple_bridges):
        """Test export with bridges."""
        for bridge in multiple_bridges[:3]:
            store_basic.save_bridge(bridge)

        exported = store_basic.export()
        assert exported["counts"]["bridges"] == 3
        assert exported["counts"]["runs"] == 0

    def test_export_with_runs(self, store_basic, multiple_runs):
        """Test export with runs."""
        for run in multiple_runs[:4]:
            store_basic.save_run(run)

        exported = store_basic.export()
        assert exported["counts"]["bridges"] == 0
        assert exported["counts"]["runs"] == 4

    def test_export_with_bridges_and_runs(self, store_basic, multiple_bridges, multiple_runs):
        """Test export with both bridges and runs."""
        for bridge in multiple_bridges[:2]:
            store_basic.save_bridge(bridge)
        for run in multiple_runs[:3]:
            store_basic.save_run(run)

        exported = store_basic.export()
        assert exported["counts"]["bridges"] == 2
        assert exported["counts"]["runs"] == 3


class TestMemoryStoreDataIsolation:
    """Test MemoryStore data isolation between instances."""

    def test_multiple_stores_are_isolated(self, bridge_basic, run_basic):
        """Test that multiple MemoryStore instances don't share data."""
        store1 = MemoryStore(name="store1")
        store2 = MemoryStore(name="store2")

        # Add data to store1
        store1.save_bridge(bridge_basic)
        store1.save_run(run_basic)

        # Verify store2 is still empty
        assert store2.check_bridge_exists("test_bridge") is False
        assert store2.check_run_exists(run_basic.id) is False
        assert len(store2.list_bridges()) == 0
        assert len(store2.list_runs()) == 0

    def test_store_data_persists_during_lifetime(self, store_basic, bridge_basic):
        """Test that data persists in memory during store lifetime."""
        store_basic.save_bridge(bridge_basic)

        # Multiple retrievals should work
        retrieved1 = store_basic.get_bridge("test_bridge")
        retrieved2 = store_basic.get_bridge("test_bridge")

        assert retrieved1 is not None
        assert retrieved2 is not None
        assert retrieved1.name == retrieved2.name


class TestMemoryStoreInternalState:
    """Test MemoryStore internal state management."""

    def test_internal_bridges_dict(self, store_basic, bridge_basic):
        """Test that bridges are stored in internal dictionary."""
        store_basic.save_bridge(bridge_basic)
        assert "test_bridge" in store_basic._bridges
        assert store_basic._bridges["test_bridge"].name == "test_bridge"

    def test_internal_runs_dict(self, store_basic, run_basic):
        """Test that runs are stored in internal dictionary."""
        store_basic.save_run(run_basic)
        assert run_basic.id in store_basic._runs
        assert store_basic._runs[run_basic.id].id == run_basic.id

    def test_overwriting_bridge_replaces_value(self, store_basic, bridge_basic):
        """Test that saving a bridge with same name replaces the old value."""
        store_basic.save_bridge(bridge_basic)
        original_description = bridge_basic.description

        # Update and save again
        bridge_basic.domain.description = "New description"
        store_basic.save_bridge(bridge_basic)

        # Check internal state
        assert len(store_basic._bridges) == 1
        assert store_basic._bridges["test_bridge"].description == "New description"
        assert store_basic._bridges["test_bridge"].description != original_description

    def test_overwriting_run_replaces_value(self, store_basic, run_basic):
        """Test that saving a run with same ID replaces the old value."""
        store_basic.save_run(run_basic)
        assert store_basic._runs[run_basic.id].status == RunStatus.PENDING

        # Start and save again
        run_basic.start()
        store_basic.save_run(run_basic)

        # Check internal state
        assert len(store_basic._runs) == 1
        assert store_basic._runs[run_basic.id].status == RunStatus.RUNNING


class TestMemoryStoreGetCounts:
    """Test MemoryStore _get_counts method."""

    def test_get_counts_empty(self, store_basic):
        """Test _get_counts with empty store."""
        counts = store_basic._get_counts()
        assert counts["bridges"] == 0
        assert counts["runs"] == 0

    def test_get_counts_with_bridges(self, store_basic, multiple_bridges):
        """Test _get_counts with bridges."""
        for bridge in multiple_bridges:
            store_basic.save_bridge(bridge)

        counts = store_basic._get_counts()
        assert counts["bridges"] == 5
        assert counts["runs"] == 0

    def test_get_counts_with_runs(self, store_basic, multiple_runs):
        """Test _get_counts with runs."""
        for run in multiple_runs:
            store_basic.save_run(run)

        counts = store_basic._get_counts()
        assert counts["bridges"] == 0
        assert counts["runs"] == 5

    def test_get_counts_with_both(self, store_basic, multiple_bridges, multiple_runs):
        """Test _get_counts with both bridges and runs."""
        for bridge in multiple_bridges[:3]:
            store_basic.save_bridge(bridge)
        for run in multiple_runs[:2]:
            store_basic.save_run(run)

        counts = store_basic._get_counts()
        assert counts["bridges"] == 3
        assert counts["runs"] == 2
