"""Unit tests for access domain models."""

from __future__ import annotations

from bastion.domain.access.access import AbstractAccessDomain
from bastion.domain.access.platform import AccessPlatform


class ConcreteAccessDomain(AbstractAccessDomain):
    """Concrete implementation of AbstractAccessDomain for testing."""

    platform: AccessPlatform = AccessPlatform.LOCAL


class TestAbstractAccessDomain:
    """Test AbstractAccessDomain base class."""

    def test_create_domain(self):
        """Test creating an access domain."""
        domain = ConcreteAccessDomain(
            name="test_access",
            platform=AccessPlatform.LOCAL,
        )

        assert domain.name == "test_access"
        assert domain.platform == AccessPlatform.LOCAL
        assert domain.tags == {}

    def test_domain_with_default_values(self):
        """Test creating domain with default values."""
        domain = ConcreteAccessDomain()

        assert domain.name == "default"
        assert domain.platform == AccessPlatform.LOCAL
        assert domain.tags == {}

    def test_domain_with_tags(self):
        """Test creating domain with tags."""
        domain = ConcreteAccessDomain(
            name="test",
            tags={"env": "prod", "team": "data"},
        )

        assert domain.tags == {"env": "prod", "team": "data"}

    def test_domain_platform_assignment(self):
        """Test that platform can be assigned."""
        domain = ConcreteAccessDomain(
            name="test",
            platform=AccessPlatform.AWS,
        )

        assert domain.platform == AccessPlatform.AWS

    def test_export_to_dict(self):
        """Test exporting domain to dictionary."""
        domain = ConcreteAccessDomain(
            name="test_export",
            platform=AccessPlatform.LOCAL,
            tags={"env": "dev"},
        )

        exported = domain.export()

        assert exported["name"] == "test_export"
        assert exported["platform"] == "local"
        assert exported["tags"] == {"env": "dev"}

    def test_roundtrip_from_dict(self):
        """Test roundtrip: dict -> domain -> export."""
        data = {
            "name": "test_access",
            "platform": "local",
            "tags": {"env": "test", "version": "1.0"},
        }

        domain = ConcreteAccessDomain.from_dict(data)
        exported = domain.export()

        assert domain.name == "test_access"
        assert domain.platform == AccessPlatform.LOCAL
        assert domain.tags == {"env": "test", "version": "1.0"}
        assert exported["name"] == "test_access"
        assert exported["platform"] == "local"
        assert exported["tags"] == {"env": "test", "version": "1.0"}

    def test_roundtrip_with_clone(self):
        """Test roundtrip: domain -> clone -> export."""
        original = ConcreteAccessDomain(
            name="original",
            platform=AccessPlatform.AWS,
            tags={"env": "prod"},
        )

        cloned = original.clone(name="cloned", tags={"env": "dev"})

        assert cloned.name == "cloned"
        assert cloned.platform == AccessPlatform.AWS
        assert cloned.tags == {"env": "dev"}
        assert original.name == "original"
        assert original.tags == {"env": "prod"}

    def test_describe(self):
        """Test describe method returns string representation."""
        domain = ConcreteAccessDomain(
            name="test_describe",
            platform=AccessPlatform.LOCAL,
        )

        description = domain.describe()

        assert isinstance(description, str)
        assert len(description) > 0
        assert "test_describe" in description

    def test_id_disabled_by_default(self):
        """Test that ID generation is disabled for access domains."""
        domain = ConcreteAccessDomain(name="test")

        # Access domains should not have auto-generated IDs
        assert domain._id_enabled is False

    def test_tags_default_factory(self):
        """Test that tags use default factory for empty dict."""
        domain1 = ConcreteAccessDomain(name="test1")
        domain2 = ConcreteAccessDomain(name="test2")

        domain1.tags["key"] = "value1"

        assert domain2.tags == {}
        assert domain1.tags == {"key": "value1"}
