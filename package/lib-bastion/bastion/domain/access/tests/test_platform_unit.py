"""Unit tests for AccessPlatform enumeration."""

from __future__ import annotations

from bastion.domain.access.platform import AccessPlatform


class TestAccessPlatform:
    """Test AccessPlatform enumeration."""

    def test_platform_values(self):
        """Test that all platform values are strings."""
        assert AccessPlatform.LOCAL == "local"
        assert AccessPlatform.AWS == "aws"
        assert AccessPlatform.ALIYUN == "aliyun"

    def test_platform_membership(self):
        """Test platform membership checks."""
        assert AccessPlatform.LOCAL in AccessPlatform
        assert AccessPlatform.AWS in AccessPlatform
        assert AccessPlatform.ALIYUN in AccessPlatform

    def test_platform_from_string(self):
        """Test creating platform from string."""
        platform = AccessPlatform("aws")
        assert platform == AccessPlatform.AWS

    def test_roundtrip_string_conversion(self):
        """Test roundtrip: string -> enum -> string."""
        original = "aws"
        platform = AccessPlatform(original)
        result = platform.value

        assert result == original
        assert isinstance(result, str)

    def test_roundtrip_all_platforms(self):
        """Test roundtrip for all platform values."""
        platforms = [AccessPlatform.LOCAL, AccessPlatform.AWS, AccessPlatform.ALIYUN]

        for platform in platforms:
            value = platform.value
            reconstructed = AccessPlatform(value)

            assert reconstructed == platform
            assert reconstructed.value == value

    def test_platform_iteration(self):
        """Test iterating over all platform values."""
        platforms = list(AccessPlatform)

        assert len(platforms) == 3
        assert AccessPlatform.LOCAL in platforms
        assert AccessPlatform.AWS in platforms
        assert AccessPlatform.ALIYUN in platforms

    def test_platform_equality(self):
        """Test platform equality comparisons."""
        assert AccessPlatform.AWS == "aws"
        assert AccessPlatform.AWS == AccessPlatform("aws")
        assert AccessPlatform.AWS != AccessPlatform.LOCAL
        assert AccessPlatform.AWS != "local"
