"""
Integration tests for bastion.control.hub module.

These tests validate the three main use cases from the design document:
1. Mode 1 — Hub-driven execution (Fortress ECS scenario)
2. Mode 2 — Compute self-reporting (decentralized) — V2 (placeholder)
3. Mode 3 — Passive inspection (zero compute cooperation) — V2 (placeholder)
"""

import pytest

from bastion.control.asset.local import LocalAsset
from bastion.control.bridge.bridge import Bridge
from bastion.control.compute.pyentrypoint import PyEntrypointCompute
from bastion.control.hub.hub import Hub
from bastion.domain.asset.base import AssetKind, AssetPlatform
from bastion.domain.run import RunStatus


# ============================================================================
# Mode 1 — Hub-Driven Execution (Fortress ECS Scenario)
# ============================================================================


class TestMode1HubDrivenExecution:
    """
    Test Mode 1: Hub-driven execution scenario.
    
    Hub and Compute are co-located, Hub fully manages execution lifecycle.
    Bridge definitions are persisted to Store and don't need to be rebuilt.
    """

    def test_register_and_run_bridge_with_memory_store(
        self,
        hub_memory,
        bridge_simple,
    ):
        """
        Test the basic flow: register a bridge and run it.
        
        This is the minimal closed-loop example from the design doc.
        """
        # Register the bridge
        hub_memory.register(bridge_simple)
        
        # Verify bridge was registered
        stored_bridge = hub_memory.store.get_bridge("test_bridge_simple")
        assert stored_bridge is not None
        assert stored_bridge.name == "test_bridge_simple"
        
        # Run the bridge
        run = hub_memory.run("test_bridge_simple")
        
        # Verify run succeeded
        assert run is not None
        assert run.status == RunStatus.SUCCEEDED
        assert run.bridge_name == "test_bridge_simple"

    def test_register_and_run_with_local_store(
        self,
        hub_local,
        bridge_simple,
    ):
        """
        Test Hub-driven execution with persistent LocalStore.
        
        Validates that bridge definitions persist to database.
        
        NOTE: Due to serialization limitations, we only verify bridge
        persistence here. Actual execution testing is done with MemoryStore.
        """
        # Register the bridge
        hub_local.register(bridge_simple)
        
        # Verify bridge was stored
        stored_bridge = hub_local.store.get_bridge("test_bridge_simple")
        assert stored_bridge is not None
        assert stored_bridge.name == "test_bridge_simple"
        assert stored_bridge.description == "Simple test bridge"
        
        # Verify bridge metadata is preserved
        assert len(stored_bridge.assets) == 1
        assert stored_bridge.assets[0].name == "test_asset"

    def test_stock_daily_update_scenario(
        self,
        hub_memory,
        compute_success,
        local_asset_stock,
    ):
        """
        Test the stock daily update scenario from the design doc.
        
        Simulates:
        ```python
        hub.register(
            Bridge(
                name="update_stock_daily",
                compute=PyEntrypointCompute(...),
                assets=[LocalAsset(...)],
            )
        )
        run = hub.run("update_stock_daily")
        assert run.status == RunStatus.SUCCEEDED
        ```
        """
        # Create and register bridge
        bridge = Bridge(
            name="update_stock_daily",
            compute_domain=compute_success.domain,
            asset_domains=[local_asset_stock.domain],
        )
        hub_memory.register(bridge)
        
        # Run the bridge
        run = hub_memory.run("update_stock_daily")
        
        # Verify success
        assert run.status == RunStatus.SUCCEEDED
        assert run.bridge_name == "update_stock_daily"

    def test_run_with_parameters(
        self,
        hub_memory,
        compute_with_params,
        local_asset_simple,
    ):
        """
        Test running a bridge with parameters.
        """
        # Create bridge with parameterized compute
        bridge = Bridge(
            name="test_with_params",
            compute_domain=compute_with_params.domain,
            asset_domains=[local_asset_simple.domain],
        )
        hub_memory.register(bridge)
        
        # Run with parameters
        run = hub_memory.run(
            "test_with_params",
            params={"input_value": "test", "multiplier": 3}
        )
        
        # Verify success
        assert run.status == RunStatus.SUCCEEDED

    def test_run_failure_handling(
        self,
        hub_memory,
        compute_failure,
        local_asset_simple,
    ):
        """
        Test that Hub properly handles compute failures.
        """
        # Create bridge with failing compute
        bridge = Bridge(
            name="test_failure",
            compute_domain=compute_failure.domain,
            asset_domains=[local_asset_simple.domain],
        )
        hub_memory.register(bridge)
        
        # Run should raise exception
        with pytest.raises(RuntimeError, match="Task failed intentionally"):
            hub_memory.run("test_failure")

    def test_run_nonexistent_bridge_raises_error(self, hub_memory):
        """Test that running a non-existent bridge raises an error."""
        with pytest.raises(ValueError, match="Bridge 'nonexistent' not found"):
            hub_memory.run("nonexistent")

    def test_run_bridge_without_compute_raises_error(
        self,
        hub_memory,
        bridge_no_compute,
    ):
        """
        Test that running a bridge without compute raises an error.
        
        Bridges without compute are for Mode 3 (passive inspection),
        which is not available in V1.
        """
        hub_memory.register(bridge_no_compute)
        
        with pytest.raises(
            ValueError,
            match="Bridge 'bridge_no_compute' has no compute configured"
        ):
            hub_memory.run("bridge_no_compute")


class TestMode1AssetRegistration:
    """Test asset-only registration (syntactic sugar)."""

    def test_register_asset_creates_bridge(
        self,
        hub_memory,
        local_asset_simple,
    ):
        """
        Test that hub.register(asset) is syntactic sugar for creating a bridge.
        
        From design doc:
        hub.register(asset) → Bridge(name=asset.name, assets=[asset])
        """
        # Register asset directly
        hub_memory.register(local_asset_simple)
        
        # Verify a bridge was created with asset name
        stored_bridge = hub_memory.store.get_bridge("test_asset")
        assert stored_bridge is not None
        assert stored_bridge.name == "test_asset"
        assert len(stored_bridge.assets) == 1
        assert stored_bridge.assets[0].name == "test_asset"
        
        # Bridge should have no compute (passive inspection mode)
        assert stored_bridge.compute is None


class TestMode1BridgePersistence:
    """Test bridge registration persistence and updates."""

    def test_register_updates_existing_bridge(
        self,
        hub_memory,
        bridge_simple,
    ):
        """Test that re-registering a bridge updates it."""
        # Register initially
        hub_memory.register(bridge_simple)
        original = hub_memory.store.get_bridge("test_bridge_simple")
        assert original.description == "Simple test bridge"
        
        # Update and re-register
        bridge_simple.domain.description = "Updated description"
        hub_memory.register(bridge_simple)
        
        # Verify update
        updated = hub_memory.store.get_bridge("test_bridge_simple")
        assert updated.description == "Updated description"

    def test_multiple_bridges_can_be_registered(
        self,
        hub_memory,
        compute_success,
        local_asset_simple,
        local_asset_stock,
    ):
        """Test registering multiple bridges."""
        # Create multiple bridges
        bridge1 = Bridge(
            name="bridge_1",
            compute_domain=compute_success.domain,
            asset_domains=[local_asset_simple.domain],
        )
        bridge2 = Bridge(
            name="bridge_2",
            compute_domain=compute_success.domain,
            asset_domains=[local_asset_stock.domain],
        )
        
        # Register both
        hub_memory.register(bridge1)
        hub_memory.register(bridge2)
        
        # Verify both exist
        assert hub_memory.store.check_bridge_exists("bridge_1")
        assert hub_memory.store.check_bridge_exists("bridge_2")
        
        # Run both
        run1 = hub_memory.run("bridge_1")
        run2 = hub_memory.run("bridge_2")
        
        assert run1.status == RunStatus.SUCCEEDED
        assert run2.status == RunStatus.SUCCEEDED


class TestMode1BridgeUnregistration:
    """Test bridge unregistration."""

    def test_unregister_removes_bridge(
        self,
        hub_memory,
        bridge_simple,
    ):
        """Test that unregister removes a bridge from the store."""
        # Register bridge
        hub_memory.register(bridge_simple)
        assert hub_memory.store.check_bridge_exists("test_bridge_simple")
        
        # Unregister bridge
        hub_memory.unregister("test_bridge_simple")
        
        # Verify removal
        assert not hub_memory.store.check_bridge_exists("test_bridge_simple")

    def test_unregister_removes_associated_runs(
        self,
        hub_memory,
        bridge_simple,
    ):
        """Test that unregister removes associated runs."""
        # Register and run bridge
        hub_memory.register(bridge_simple)
        run = hub_memory.run("test_bridge_simple")
        run_id = run.id
        
        # Verify run exists
        assert hub_memory.store.get_run(run_id) is not None
        
        # Unregister bridge
        hub_memory.unregister("test_bridge_simple")
        
        # Verify run was removed
        assert hub_memory.store.get_run(run_id) is None

    def test_unregister_nonexistent_bridge_logs_warning(
        self,
        hub_memory,
    ):
        """Test that unregistering non-existent bridge doesn't raise error."""
        # Should not raise, just log warning
        hub_memory.unregister("nonexistent_bridge")
        
        # Verify still doesn't exist
        assert not hub_memory.store.check_bridge_exists("nonexistent_bridge")


class TestMode1MultipleAssets:
    """Test bridges with multiple assets."""

    def test_bridge_with_multiple_assets(
        self,
        hub_memory,
        compute_success,
        temp_dir,
    ):
        """
        Test that a bridge can update multiple assets.
        
        From design doc:
        - One Compute can update multiple Assets (one-to-many)
        - One Asset can only be updated by one Compute
        """
        # Create multiple assets
        asset1 = LocalAsset(
            name="asset_1",
            kind=AssetKind.PARQUET,
            platform=AssetPlatform.LOCAL,
            path=str(temp_dir / "asset1"),
        )
        asset2 = LocalAsset(
            name="asset_2",
            kind=AssetKind.PARQUET,
            platform=AssetPlatform.LOCAL,
            path=str(temp_dir / "asset2"),
        )
        asset3 = LocalAsset(
            name="asset_3",
            kind=AssetKind.PARQUET,
            platform=AssetPlatform.LOCAL,
            path=str(temp_dir / "asset3"),
        )
        
        # Create bridge with multiple assets
        bridge = Bridge(
            name="multi_asset_bridge",
            compute_domain=compute_success.domain,
            asset_domains=[
                asset1.domain,
                asset2.domain,
                asset3.domain,
            ],
        )
        
        # Register and run
        hub_memory.register(bridge)
        run = hub_memory.run("multi_asset_bridge")
        
        # Verify success
        assert run.status == RunStatus.SUCCEEDED
        
        # Verify bridge has all assets
        stored_bridge = hub_memory.store.get_bridge("multi_asset_bridge")
        assert len(stored_bridge.assets) == 3
        asset_names = [a.name for a in stored_bridge.assets]
        assert "asset_1" in asset_names
        assert "asset_2" in asset_names
        assert "asset_3" in asset_names


# ============================================================================
# Mode 2 — Compute Self-Reporting (Decentralized) — V2
# ============================================================================


class TestMode2ComputeSelfReporting:
    """
    Test Mode 2: Compute self-reporting scenario (V2).
    
    NOTE: This is a V2 feature and depends on cloud storage backends.
    These tests serve as placeholders for future implementation.
    """

    @pytest.mark.skip(reason="Mode 2 is V2 feature, requires DynamoStore/OSSStore")
    def test_compute_self_reporting_placeholder(self):
        """
        Placeholder test for compute self-reporting mode.
        
        In V2, remote compute (Glue/Lambda/FC) will report back to Hub
        via BaseCompute.attach() method with only report() capability.
        """
        pass


# ============================================================================
# Mode 3 — Passive Inspection (Zero Compute Cooperation) — V2
# ============================================================================


class TestMode3PassiveInspection:
    """
    Test Mode 3: Passive inspection scenario (V2).
    
    NOTE: This is a V2 feature and depends on DuckDB httpfs.
    These tests serve as placeholders for future implementation.
    """

    @pytest.mark.skip(reason="Mode 3 is V2 feature, requires DuckDB httpfs + hub.inspect()")
    def test_passive_inspection_placeholder(self):
        """
        Placeholder test for passive inspection mode.
        
        In V2, Hub.inspect(bridge_name) will use DuckDB to directly
        query Asset data locations when Compute=None.
        """
        pass


# ============================================================================
# Hub Lifecycle Tests
# ============================================================================


class TestHubLifecycle:
    """Test Hub initialization and lifecycle management."""

    def test_hub_initialization_with_memory_store(self, memory_store):
        """Test Hub initializes correctly with MemoryStore."""
        hub = Hub(store=memory_store)
        assert hub is not None
        assert hub.store is memory_store

    def test_hub_initialization_with_local_store(self, local_store):
        """Test Hub initializes correctly with LocalStore."""
        hub = Hub(store=local_store)
        assert hub is not None
        assert hub.store is local_store

    def test_hub_store_property(self, hub_memory, memory_store):
        """Test Hub.store property returns the store."""
        assert hub_memory.store is memory_store


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestHubErrorHandling:
    """Test Hub error handling and edge cases."""

    def test_register_invalid_type_raises_error(self, hub_memory):
        """Test that registering invalid type raises TypeError."""
        with pytest.raises(TypeError, match="Expected Bridge or IAssetLike"):
            hub_memory.register("invalid_type")

    def test_run_failure_persists_failed_status(
        self,
        hub_memory,
        compute_failure,
        local_asset_simple,
    ):
        """Test that failed runs are persisted with FAILED status."""
        # Create bridge with failing compute
        bridge = Bridge(
            name="test_failure_persist",
            compute_domain=compute_failure.domain,
            asset_domains=[local_asset_simple.domain],
        )
        hub_memory.register(bridge)
        
        # Run should fail
        with pytest.raises(RuntimeError):
            hub_memory.run("test_failure_persist")
        
        # Find the failed run
        runs = hub_memory.store.list_runs("test_failure_persist")
        assert len(runs) > 0
        
        failed_run = runs[0]
        assert failed_run.status == RunStatus.FAILED
