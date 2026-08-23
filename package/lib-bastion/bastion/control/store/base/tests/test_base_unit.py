"""Unit tests for store base module."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from bastion.control.store.base.base import IStoreLike
from bastion.control.store.memory.memory import MemoryStore


class TestIStoreLikeProtocol:
    """Test IStoreLike protocol definition."""

    def test_protocol_required_attributes_exist(self):
        """Test that store implementations have required protocol attributes."""
        store = MemoryStore(name="test_store")

        # Verify protocol attributes exist
        assert hasattr(store, "name")

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

    def test_protocol_context_manager_methods(self):
        """Test protocol context manager methods exist."""
        store = MemoryStore(name="test_store")

        # Test context manager protocol
        assert hasattr(store, "__enter__")
        assert hasattr(store, "__exit__")
        assert callable(store.__enter__)
        assert callable(store.__exit__)


class TestIStoreLikeRuntimeCheckable:
    """Test IStoreLike runtime_checkable behavior."""

    def test_memory_store_is_storelike(self):
        """Test that MemoryStore is recognized as IStoreLike."""
        store = MemoryStore(name="test_store")

        # Test runtime protocol check
        assert isinstance(store, IStoreLike)

    def test_storelike_protocol_check_requires_name(self):
        """Test that protocol check requires name attribute."""

        class MinimalStore:
            """Minimal store implementation without name."""

            def __enter__(self) -> Any:
                return self

            def __exit__(self, *args: Any) -> None:
                pass

            def init(self) -> None:
                pass

            def save_run(self, run: Any) -> None:
                pass

            def get_run(self, run_id: str) -> Any:
                return None

            def list_runs(self, **kwargs: Any) -> list[Any]:
                return []

            def delete_run(self, run_id: str) -> None:
                pass

        minimal = MinimalStore()

        # Should fail protocol check without name attribute
        assert not isinstance(minimal, IStoreLike)

    def test_storelike_protocol_check_with_all_attributes(self):
        """Test that protocol check passes with all required attributes."""

        class CompleteStore:
            """Complete store implementation."""

            def __init__(self) -> None:
                self.name = "complete_store"

            def __enter__(self) -> Any:
                return self

            def __exit__(self, *args: Any) -> None:
                pass

            def init(self) -> None:
                pass

            def save_run(self, run: Any) -> None:
                pass

            def get_run(self, run_id: str) -> Any:
                return None

            def list_runs(
                self,
                compute_name: str | None = None,
                since: datetime | None = None,
                until: datetime | None = None,
                limit: int | None = None,
            ) -> list[Any]:
                return []

            def delete_run(self, run_id: str) -> None:
                pass

        complete = CompleteStore()

        # Should pass protocol check
        assert isinstance(complete, IStoreLike)


class TestIStoreLikeContextManager:
    """Test IStoreLike context manager protocol."""

    def test_context_manager_returns_self(self):
        """Test that __enter__ returns the store itself."""
        store = MemoryStore(name="test_store")

        with store as ctx:
            assert ctx is store
            assert isinstance(ctx, IStoreLike)

    def test_context_manager_usage(self):
        """Test using store as context manager."""
        store = MemoryStore(name="test_store")

        # Test basic context manager usage
        with store as ctx:
            assert ctx.name == "test_store"
            # Store should be usable within context
            ctx.init()
