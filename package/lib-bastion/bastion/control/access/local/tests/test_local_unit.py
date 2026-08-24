"""Unit tests for Local access."""

from __future__ import annotations

from bastion.control.access.base.protocol import IAccessLike
from bastion.control.access.local import LocalAccess, LocalAccessDomain
from bastion.domain.access.platform import AccessPlatform


class TestLocalAccessDomain:
    """Test LocalAccessDomain domain model."""

    def test_create_domain(self):
        """Test creating a LocalAccessDomain."""
        domain = LocalAccessDomain(
            name="test_local",
            tags={"env": "test"},
        )

        assert domain.name == "test_local"
        assert domain.platform == AccessPlatform.LOCAL
        assert domain.tags == {"env": "test"}

    def test_domain_platform_is_local(self):
        """Test that domain platform is LOCAL."""
        domain = LocalAccessDomain(name="test")

        assert domain.platform == AccessPlatform.LOCAL

    def test_domain_minimal(self):
        """Test creating domain with minimal fields."""
        domain = LocalAccessDomain(name="minimal")

        assert domain.name == "minimal"
        assert domain.platform == AccessPlatform.LOCAL

    def test_domain_with_tags(self):
        """Test creating domain with tags."""
        domain = LocalAccessDomain(
            name="test",
            tags={"env": "dev", "owner": "team"},
        )

        assert domain.tags == {"env": "dev", "owner": "team"}


class TestLocalAccess:
    """Test LocalAccess control class."""

    def test_create_access(self):
        """Test creating a LocalAccess instance."""
        access = LocalAccess(
            name="test_local",
            tags={"env": "test"},
        )

        assert access.name == "test_local"
        assert access.platform == AccessPlatform.LOCAL
        assert access.tags == {"env": "test"}

    def test_access_implements_protocol(self):
        """Test that LocalAccess implements IAccessLike protocol."""
        access = LocalAccess(name="test")

        assert isinstance(access, IAccessLike)

    def test_create_minimal(self):
        """Test creating with minimal parameters."""
        access = LocalAccess(name="minimal")

        assert access.name == "minimal"
        assert access.platform == AccessPlatform.LOCAL

    def test_export(self):
        """Test export method."""
        access = LocalAccess(
            name="test",
            tags={"env": "test", "team": "data"},
        )

        exported = access.export()

        assert exported["name"] == "test"
        assert exported["platform"] == "local"
        assert exported["tags"] == {"env": "test", "team": "data"}

    def test_export_no_tags(self):
        """Test export with no tags."""
        access = LocalAccess(name="test")

        exported = access.export()

        assert exported["name"] == "test"
        assert exported["platform"] == "local"
        # tags defaults to empty dict when not provided
        assert exported["tags"] == {} or exported["tags"] is None

    def test_roundtrip_from_dict(self):
        """Test roundtrip: dict -> access -> export."""
        data = {
            "name": "test_local",
            "platform": "local",
            "tags": {"env": "test"},
        }

        access = LocalAccess.from_dict(data)
        exported = access.export()

        assert access.name == "test_local"
        assert access.platform == AccessPlatform.LOCAL
        assert exported["name"] == "test_local"
        assert exported["tags"] == {"env": "test"}

    def test_roundtrip_from_domain(self):
        """Test roundtrip: domain -> access -> domain."""
        domain = LocalAccessDomain(
            name="test_local",
            tags={"env": "prod"},
        )

        access = LocalAccess.from_domain(domain)

        assert access.name == "test_local"
        assert access.platform == AccessPlatform.LOCAL
        assert access.tags == {"env": "prod"}

    def test_describe(self):
        """Test describe method returns string representation."""
        access = LocalAccess(
            name="local_access",
            tags={"env": "dev"},
        )

        description = access.describe()

        assert isinstance(description, str)
        assert len(description) > 0
