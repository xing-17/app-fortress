"""Unit tests for access base protocol."""

from __future__ import annotations

from bastion.control.access.base.protocol import IAccessLike
from bastion.domain.access.platform import AccessPlatform


class TestIAccessLike:
    """Test IAccessLike protocol."""

    def test_protocol_runtime_checkable(self):
        """Test that IAccessLike is runtime checkable."""

        class ConcreteAccess:
            name: str = "test"
            platform: AccessPlatform = AccessPlatform.LOCAL
            tags: dict[str, str] = {}

            @classmethod
            def from_dict(cls, data):
                return cls()

            @classmethod
            def from_domain(cls, domain):
                return cls()

            def export(self):
                return {}

            def describe(self):
                return "test access"

        instance = ConcreteAccess()
        assert isinstance(instance, IAccessLike)

    def test_protocol_missing_method_fails_check(self):
        """Test that missing protocol methods fail instance check."""

        class IncompleteAccess:
            name: str = "test"
            platform: AccessPlatform = AccessPlatform.LOCAL
            tags: dict[str, str] = {}
            # Missing from_dict, from_domain, export, describe

        instance = IncompleteAccess()
        assert not isinstance(instance, IAccessLike)

    def test_protocol_has_required_attributes(self):
        """Test that protocol requires name, platform, and tags."""
        from bastion.control.access.local import LocalAccess

        access = LocalAccess(name="test", tags={"env": "test"})

        assert hasattr(access, "name")
        assert hasattr(access, "platform")
        assert hasattr(access, "tags")

    def test_protocol_has_required_methods(self):
        """Test that protocol requires from_dict, from_domain, export, describe."""
        from bastion.control.access.local import LocalAccess

        assert hasattr(LocalAccess, "from_dict")
        assert hasattr(LocalAccess, "from_domain")
        assert hasattr(LocalAccess, "export")
        assert hasattr(LocalAccess, "describe")
