"""Unit tests for access base factory."""

from __future__ import annotations

import pytest

from bastion.control.access.base.factory import AccessFactory
from bastion.domain.access.platform import AccessPlatform


class TestAccessFactory:
    """Test AccessFactory registration and loading."""

    def test_register_and_load_from_dict(self):
        """Test registering access platform and loading from dict."""
        AccessFactory._registry.clear()

        @AccessFactory.add("test_platform")
        class TestAccess:
            @classmethod
            def from_dict(cls, data):
                return cls()

            @classmethod
            def from_domain(cls, domain):
                return cls()

        assert "test_platform" in AccessFactory._registry
        assert AccessFactory._registry["test_platform"] is TestAccess

    def test_register_duplicate_platform_raises(self):
        """Test duplicate platform registration raises ValueError."""
        AccessFactory._registry.clear()

        @AccessFactory.add("test_platform")
        class FirstAccess:
            pass

        with pytest.raises(ValueError, match="already registered"):

            @AccessFactory.add("test_platform")
            class SecondAccess:
                pass

    def test_load_from_dict(self):
        """Test loading access from dictionary."""
        from bastion.control.access.local import LocalAccess

        AccessFactory._registry.clear()
        AccessFactory.add(AccessPlatform.LOCAL)(LocalAccess)

        data = {
            "name": "test_access",
            "platform": AccessPlatform.LOCAL,
            "tags": {"env": "test"},
        }

        access = AccessFactory.load(data)
        assert isinstance(access, LocalAccess)
        assert access.name == "test_access"
        assert access.platform == AccessPlatform.LOCAL

    def test_load_from_domain_model(self):
        """Test loading access from domain model."""
        from bastion.control.access.local import LocalAccess, LocalAccessDomain

        AccessFactory._registry.clear()
        AccessFactory.add(AccessPlatform.LOCAL)(LocalAccess)

        domain = LocalAccessDomain(
            name="test_access",
            tags={"env": "test"},
        )

        access = AccessFactory.load(domain)
        assert isinstance(access, LocalAccess)
        assert access.name == "test_access"
        assert access.tags == {"env": "test"}

    def test_load_missing_platform_from_dict_raises(self):
        """Test loading without platform field from dict raises ValueError."""
        AccessFactory._registry.clear()

        with pytest.raises(ValueError, match="missing required field"):
            AccessFactory.load({"name": "test"})

    def test_load_unregistered_platform_raises(self):
        """Test loading unregistered platform raises ValueError."""
        AccessFactory._registry.clear()

        data = {
            "name": "test_access",
            "platform": "nonexistent_platform",
        }

        with pytest.raises(ValueError, match="No access registered"):
            AccessFactory.load(data)

    def test_register_decorator_returns_class(self):
        """Test add decorator returns the original class."""
        AccessFactory._registry.clear()

        @AccessFactory.add("test_platform")
        class TestAccess:
            pass

        assert TestAccess is not None
        assert TestAccess.__name__ == "TestAccess"
