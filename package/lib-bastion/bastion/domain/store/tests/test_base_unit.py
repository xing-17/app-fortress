"""
Unit tests for bastion.domain.store.base module.
"""

from bastion.domain.store.base import BaseStoreModel, StoreKind


class TestStoreKind:
    """Test StoreKind enumeration."""

    def test_store_kind_values(self):
        """Test StoreKind has correct memory value."""
        assert StoreKind.MEMORY == "memory"


class TestBaseStoreModel:
    """Test BaseStoreModel class."""

    def test_create_base_store_model(self):
        """Test creating a basic store model."""
        store = BaseStoreModel(
            name="test_store",
            kind=StoreKind.MEMORY,
        )
        assert store.name == "test_store"
        assert store.kind == StoreKind.MEMORY

    def test_id_disabled(self):
        """Test that BaseStoreModel does not auto-generate ID."""
        store = BaseStoreModel(
            name="test_store",
            kind=StoreKind.MEMORY,
        )
        # ID should be empty string since _id_enabled is False
        assert store.id == ""

    def test_identifier_property(self):
        """Test identifier property combines kind and name."""
        store = BaseStoreModel(
            name="test_store",
            kind=StoreKind.MEMORY,
        )
        assert store.identifier == "memory:test_store"

    def test_identifier_format(self):
        """Test identifier format is kind:name."""
        store = BaseStoreModel(
            name="my_data_store",
            kind=StoreKind.MEMORY,
        )
        identifier = store.identifier

        assert ":" in identifier
        parts = identifier.split(":")
        assert len(parts) == 2
        assert parts[0] == "memory"
        assert parts[1] == "my_data_store"

    def test_create_with_string_kind(self):
        """Test creating store with string kind value."""
        store = BaseStoreModel(
            name="test_store",
            kind="memory",  # String instead of enum
        )
        assert store.kind == StoreKind.MEMORY

    def test_multiple_stores_have_different_identifiers(self):
        """Test that different stores have unique identifiers."""
        store1 = BaseStoreModel(name="store1", kind=StoreKind.MEMORY)
        store2 = BaseStoreModel(name="store2", kind=StoreKind.MEMORY)

        assert store1.identifier != store2.identifier
        assert store1.identifier == "memory:store1"
        assert store2.identifier == "memory:store2"

    def test_store_kind_in_identifier(self):
        """Test identifier starts with store kind."""
        store = BaseStoreModel(
            name="test_store",
            kind=StoreKind.MEMORY,
        )
        assert store.identifier.startswith("memory:")

    def test_store_name_in_identifier(self):
        """Test identifier ends with store name."""
        store = BaseStoreModel(
            name="test_store",
            kind=StoreKind.MEMORY,
        )
        assert store.identifier.endswith(":test_store")

    def test_from_any_with_dict(self):
        """Test from_any creates model from dictionary."""
        data = {
            "name": "test_store",
            "kind": "memory",
        }
        store = BaseStoreModel.from_any(data)
        assert store.name == "test_store"
        assert store.kind == StoreKind.MEMORY

    def test_from_any_with_model_instance(self):
        """Test from_any returns same instance when given model."""
        original = BaseStoreModel(
            name="test_store",
            kind=StoreKind.MEMORY,
        )
        result = BaseStoreModel.from_any(original)
        assert result is original

    def test_roundtrip_export_from_any(self):
        """Test export and from_any roundtrip conversion."""
        original = BaseStoreModel(
            name="roundtrip_store",
            kind=StoreKind.MEMORY,
        )
        # Export to dict
        exported = original.export()
        # Recreate from dict
        restored = BaseStoreModel.from_any(exported)
        # Verify all fields match
        assert restored.name == original.name
        assert restored.kind == original.kind
        assert restored.identifier == original.identifier
