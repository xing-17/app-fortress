"""
Unit tests for bastion.control.store.local module.
"""

from pathlib import Path

import duckdb
import pytest

from bastion.control.run.run import RunStatus
from bastion.control.store.local.local import LocalStore, LocalStoreModel
from bastion.domain.store.base import StoreKind


class TestLocalStoreModel:
    """Test LocalStoreModel class."""

    def test_create_default_model(self):
        """Test creating LocalStoreModel with defaults."""
        model = LocalStoreModel(name="test_store")
        assert model.name == "test_store"
        assert model.kind == StoreKind.LOCAL
        assert model.path == "./data/store.duckdb"
        assert model.table_bridges == "_bridges"
        assert model.table_runs == "_runs"

    def test_create_model_with_custom_values(self):
        """Test creating LocalStoreModel with custom values."""
        model = LocalStoreModel(
            name="custom_store",
            path="/tmp/custom.duckdb",
            table_bridges="my_bridges",
            table_runs="my_runs",
        )
        assert model.name == "custom_store"
        assert model.path == "/tmp/custom.duckdb"
        assert model.table_bridges == "my_bridges"
        assert model.table_runs == "my_runs"


class TestLocalStoreInitialization:
    """Test LocalStore initialization and setup."""

    def test_create_store_basic(self, temp_db_path):
        """Test creating a basic LocalStore."""
        store = LocalStore(
            name="test_store",
            path=temp_db_path,
        )
        assert store.name == "test_store"
        assert store.table_bridges == "_bridges"
        assert store.table_runs == "_runs"
        assert temp_db_path.exists()
        store.close()

    def test_create_store_with_custom_tables(self, temp_db_path):
        """Test creating store with custom table names."""
        store = LocalStore(
            name="test_store",
            path=temp_db_path,
            table_bridges="custom_bridges",
            table_runs="custom_runs",
        )
        assert store.table_bridges == "custom_bridges"
        assert store.table_runs == "custom_runs"
        store.close()

    def test_create_store_with_path_string(self, tmp_path):
        """Test creating store with path as string."""
        db_path = str(tmp_path / "test.duckdb")
        store = LocalStore(
            name="test_store",
            path=db_path,
        )
        assert Path(db_path).exists()
        store.close()

    def test_create_store_with_path_object(self, temp_db_path):
        """Test creating store with path as Path object."""
        store = LocalStore(
            name="test_store",
            path=temp_db_path,
        )
        assert temp_db_path.exists()
        store.close()

    def test_create_store_creates_parent_directories(self, tmp_path):
        """Test that store creates parent directories if they don't exist."""
        nested_path = tmp_path / "nested" / "dirs" / "store.duckdb"
        store = LocalStore(
            name="test_store",
            path=nested_path,
        )
        assert nested_path.exists()
        assert nested_path.parent.exists()
        store.close()

    def test_create_store_with_tilde_path(self, tmp_path):
        """Test creating store with tilde in path."""
        # Mock a path with tilde (actual expansion will happen)
        store = LocalStore(
            name="test_store",
            path="~/test_store.duckdb",
        )
        # Just verify it doesn't crash
        store.close()

    def test_invalid_table_name_raises_error(self, temp_db_path):
        """Test that invalid table names raise ValueError."""
        with pytest.raises(ValueError, match="Table names must be valid SQL identifiers"):
            LocalStore(
                name="test_store",
                path=temp_db_path,
                table_bridges="invalid-name",
            )

    def test_invalid_table_name_with_special_chars(self, temp_db_path):
        """Test that table names with special characters raise ValueError."""
        with pytest.raises(ValueError, match="Table names must be valid SQL identifiers"):
            LocalStore(
                name="test_store",
                path=temp_db_path,
                table_runs="invalid name",
            )

    def test_tables_created_on_init(self, store_basic):
        """Test that tables are created on initialization."""
        # Query to check if tables exist
        tables = store_basic._conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
        ).fetchall()
        table_names = [t[0] for t in tables]

        assert "_bridges" in table_names
        assert "_runs" in table_names

    def test_index_created_on_init(self, store_basic):
        """Test that index is created on initialization."""
        indexes = store_basic._conn.execute("SELECT index_name FROM duckdb_indexes()").fetchall()
        index_names = [idx[0] for idx in indexes]

        assert "idx_runs_bridge" in index_names


class TestLocalStoreContextManager:
    """Test LocalStore context manager behavior."""

    def test_context_manager_enter_exit(self, temp_db_path):
        """Test using LocalStore as context manager."""
        with LocalStore(name="test_store", path=temp_db_path) as store:
            assert store.name == "test_store"
            assert store._conn is not None

        # Connection should be closed after exit
        with pytest.raises(duckdb.ConnectionException):
            store._conn.execute("SELECT 1")

    def test_context_manager_with_operations(self, temp_db_path, bridge_basic):
        """Test context manager with actual operations."""
        with LocalStore(name="test_store", path=temp_db_path) as store:
            store.save_bridge(bridge_basic)
            assert store.check_bridge_exists("test_bridge")


class TestLocalStoreBridgeOperations:
    """Test LocalStore bridge-related methods."""

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


class TestLocalStoreRunOperations:
    """Test LocalStore run-related methods."""

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


class TestLocalStoreExport:
    """Test LocalStore export functionality."""

    def test_export_empty_store(self, store_basic):
        """Test export with empty store."""
        exported = store_basic.export()

        assert exported["name"] == "test_store"
        assert exported["kind"] == StoreKind.LOCAL
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


class TestLocalStoreCloseConnection:
    """Test LocalStore connection management."""

    def test_close_method(self, temp_db_path):
        """Test close() method closes connection."""
        store = LocalStore(name="test_store", path=temp_db_path)
        store.close()

        with pytest.raises(duckdb.ConnectionException):
            store._conn.execute("SELECT 1")

    def test_operations_after_close_raise_error(self, store_basic, bridge_basic):
        """Test that operations after close raise appropriate errors."""
        store_basic.close()

        with pytest.raises(duckdb.ConnectionException):
            store_basic.save_bridge(bridge_basic)


class TestLocalStoreCustomTables:
    """Test LocalStore with custom table names."""

    def test_custom_table_names_in_sql(self, store_custom_tables):
        """Test that custom table names are used in SQL."""
        # Check that custom tables exist
        tables = store_custom_tables._conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
        ).fetchall()
        table_names = [t[0] for t in tables]

        assert "custom_bridges" in table_names
        assert "custom_runs" in table_names

    def test_operations_with_custom_tables(self, store_custom_tables, bridge_basic, run_basic):
        """Test that operations work with custom table names."""
        store_custom_tables.save_bridge(bridge_basic)
        store_custom_tables.save_run(run_basic)

        assert store_custom_tables.check_bridge_exists("test_bridge")
        assert store_custom_tables.check_run_exists(run_basic.id)

        bridges = store_custom_tables.list_bridges()
        runs = store_custom_tables.list_runs()

        assert len(bridges) == 1
        assert len(runs) == 1
