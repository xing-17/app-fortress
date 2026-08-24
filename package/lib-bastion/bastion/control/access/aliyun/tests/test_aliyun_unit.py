"""Unit tests for Aliyun access."""

from __future__ import annotations

from bastion.control.access.aliyun import AliyunAccess, AliyunAccessDomain
from bastion.control.access.base.protocol import IAccessLike
from bastion.domain.access.platform import AccessPlatform


class TestAliyunAccessDomain:
    """Test AliyunAccessDomain domain model."""

    def test_create_domain(self):
        """Test creating an AliyunAccessDomain."""
        domain = AliyunAccessDomain(
            name="test_aliyun",
            access_key_id="LTAI4GBcXXXXXXXXXXXX",
            access_key_secret="xxxxxxxxxxxxxxxxxxxxx",
        )

        assert domain.name == "test_aliyun"
        assert domain.platform == AccessPlatform.ALIYUN
        assert domain.access_key_id == "LTAI4GBcXXXXXXXXXXXX"

    def test_domain_platform_is_aliyun(self):
        """Test that domain platform is ALIYUN."""
        domain = AliyunAccessDomain(
            name="test",
            access_key_id="test_key",
        )

        assert domain.platform == AccessPlatform.ALIYUN

    def test_domain_with_security_token(self):
        """Test creating domain with security token."""
        domain = AliyunAccessDomain(
            name="test",
            access_key_id="key",
            access_key_secret="secret",
            security_token="token",
        )

        assert domain.security_token == "token"

    def test_domain_with_timeouts(self):
        """Test creating domain with timeout settings."""
        domain = AliyunAccessDomain(
            name="test",
            access_key_id="key",
            timeout=30,
            connect_timeout=10,
        )

        assert domain.timeout == 30
        assert domain.connect_timeout == 10

    def test_domain_with_tags(self):
        """Test creating domain with tags."""
        domain = AliyunAccessDomain(
            name="test",
            access_key_id="key",
            tags={"env": "prod", "team": "data"},
        )

        assert domain.tags == {"env": "prod", "team": "data"}


class TestAliyunAccess:
    """Test AliyunAccess control class."""

    def test_create_access(self):
        """Test creating an AliyunAccess instance."""
        access = AliyunAccess(
            name="test_aliyun",
            access_key_id="LTAI4GBcXXXXXXXXXXXX",
            access_key_secret="xxxxxxxxxxxxxxxxxxxxx",
        )

        assert access.name == "test_aliyun"
        assert access.platform == AccessPlatform.ALIYUN
        assert access.access_key_id == "LTAI4GBcXXXXXXXXXXXX"

    def test_access_implements_protocol(self):
        """Test that AliyunAccess implements IAccessLike protocol."""
        access = AliyunAccess(name="test", access_key_id="key")

        assert isinstance(access, IAccessLike)

    def test_export_masks_credentials(self):
        """Test that export masks sensitive credentials."""
        access = AliyunAccess(
            name="test",
            access_key_id="LTAI4GBcXXXXXXXXXXXX",
            access_key_secret="xxxxxxxxxxxxxxxxxxxxx",
            security_token="CAISXXXXXXXXXXXXToken",
        )

        exported = access.export()

        assert exported["access_key_id"] == "LTAI******"
        assert exported["access_key_secret"] == "xxxx******"
        assert exported["security_token"] == "CAIS******"
        assert exported["name"] == "test"
        assert exported["platform"] == "aliyun"

    def test_export_handles_none_credentials(self):
        """Test that export handles None credentials."""
        access = AliyunAccess(
            name="test",
            timeout=30,
        )

        exported = access.export()

        assert exported["access_key_id"] is None
        assert exported["access_key_secret"] is None
        assert exported["security_token"] is None
        assert exported["timeout"] == 30

    def test_export_with_timeouts(self):
        """Test export includes timeout settings."""
        access = AliyunAccess(
            name="test",
            access_key_id="key",
            timeout=60,
            connect_timeout=15,
        )

        exported = access.export()

        assert exported["timeout"] == 60
        assert exported["connect_timeout"] == 15

    def test_roundtrip_from_dict(self):
        """Test roundtrip: dict -> access -> export."""
        data = {
            "name": "test_aliyun",
            "platform": "aliyun",
            "access_key_id": "LTAI4GBcXXXXXXXXXXXX",
            "access_key_secret": "xxxxxxxxxxxxxxxxxxxxx",
            "timeout": 30,
            "tags": {"env": "test"},
        }

        access = AliyunAccess.from_dict(data)
        exported = access.export()

        assert access.name == "test_aliyun"
        assert access.platform == AccessPlatform.ALIYUN
        assert exported["name"] == "test_aliyun"
        assert exported["timeout"] == 30
        assert exported["tags"] == {"env": "test"}

    def test_roundtrip_from_domain(self):
        """Test roundtrip: domain -> access -> domain."""
        domain = AliyunAccessDomain(
            name="test_aliyun",
            access_key_id="LTAI4GBcXXXXXXXXXXXX",
            access_key_secret="xxxxxxxxxxxxxxxxxxxxx",
            timeout=45,
            connect_timeout=10,
            tags={"env": "prod"},
        )

        access = AliyunAccess.from_domain(domain)

        assert access.name == "test_aliyun"
        assert access.access_key_id == "LTAI4GBcXXXXXXXXXXXX"
        assert access.timeout == 45
        assert access.connect_timeout == 10
        assert access.tags == {"env": "prod"}

    def test_describe(self):
        """Test describe method returns string representation."""
        access = AliyunAccess(
            name="prod_access",
            access_key_id="LTAI4GBcXXXXXXXXXXXX",
            timeout=30,
        )

        description = access.describe()

        assert isinstance(description, str)
        assert len(description) > 0
