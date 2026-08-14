"""
综合测试：bastion.domain.asset.base

覆盖范围
--------
- TestAssetKind         枚举值正确性；from_any() 类型转换；无效值处理
- TestAssetPlatform     枚举值正确性；from_any() 类型转换；无效值处理
- TestBaseAssetModel    初始化；必填字段验证；可选字段默认值；export() 序列化
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bastion.domain.asset import (
    AssetKind,
    AssetPlatform,
    BaseAssetModel,
)

# ──────────────────────────────────────────────────────────────────────────────
# 测试用具体实现类
# ──────────────────────────────────────────────────────────────────────────────


class DummyAsset(BaseAssetModel):
    """测试用具体 Asset 实现。"""

    def get_location_uri(self) -> str:
        """返回一个虚拟的 URI，用于测试。"""
        return f"dummy://{self.name}"


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_asset():
    """创建测试用 Asset 实例。"""
    return DummyAsset(
        name="test_asset",
        kind=AssetKind.PARQUET,
        platform=AssetPlatform.LOCAL,
    )


# ──────────────────────────────────────────────────────────────────────────────
# TestAssetKind
# ──────────────────────────────────────────────────────────────────────────────


class TestAssetKind:
    """测试 AssetKind 枚举。"""

    def test_enum_values_exist(self):
        """测试所有预定义值存在。"""
        assert AssetKind.PARQUET == "parquet"
        assert AssetKind.CSV == "csv"

    def test_from_any_accepts_string(self):
        """测试 from_any() 接受字符串。"""
        assert AssetKind.from_any("parquet") == AssetKind.PARQUET
        assert AssetKind.from_any("csv") == AssetKind.CSV

    def test_from_any_accepts_enum(self):
        """测试 from_any() 接受枚举值。"""
        assert AssetKind.from_any(AssetKind.PARQUET) == AssetKind.PARQUET

    def test_from_any_invalid_value_raises(self):
        """测试 from_any() 对无效值抛出异常。"""
        with pytest.raises(ValueError, match="Invalid AssetKind value"):
            AssetKind.from_any("json")


# ──────────────────────────────────────────────────────────────────────────────
# TestAssetPlatform
# ──────────────────────────────────────────────────────────────────────────────


class TestAssetPlatform:
    """测试 AssetPlatform 枚举。"""

    def test_enum_values_exist(self):
        """测试所有预定义值存在。"""
        assert AssetPlatform.S3 == "s3"
        assert AssetPlatform.LOCAL == "local"
        assert AssetPlatform.OSS == "oss"

    def test_from_any_accepts_string(self):
        """测试 from_any() 接受字符串。"""
        assert AssetPlatform.from_any("s3") == AssetPlatform.S3
        assert AssetPlatform.from_any("local") == AssetPlatform.LOCAL

    def test_from_any_accepts_enum(self):
        """测试 from_any() 接受枚举值。"""
        assert AssetPlatform.from_any(AssetPlatform.S3) == AssetPlatform.S3

    def test_from_any_invalid_value_raises(self):
        """测试 from_any() 对无效值抛出异常。"""
        with pytest.raises(ValueError, match="Invalid AssetPlatform value"):
            AssetPlatform.from_any("gcs")


# ──────────────────────────────────────────────────────────────────────────────
# TestBaseAssetModel
# ──────────────────────────────────────────────────────────────────────────────


class TestBaseAssetModel:
    """测试 BaseAssetModel 基本功能。"""

    def test_init_with_required_fields(self):
        """测试使用必填字段初始化。"""
        asset = DummyAsset(
            name="test",
            kind=AssetKind.PARQUET,
            platform=AssetPlatform.LOCAL,
        )
        assert asset.name == "test"
        assert asset.kind == AssetKind.PARQUET
        assert asset.platform == AssetPlatform.LOCAL

    def test_init_missing_name_raises(self):
        """测试缺少 name 时抛出异常。"""
        with pytest.raises(ValidationError):
            DummyAsset(
                kind=AssetKind.PARQUET,
                platform=AssetPlatform.LOCAL,
            )

    def test_init_missing_kind_raises(self):
        """测试缺少 kind 时抛出异常。"""
        with pytest.raises(ValidationError):
            DummyAsset(
                name="test",
                platform=AssetPlatform.LOCAL,
            )

    def test_init_missing_platform_raises(self):
        """测试缺少 platform 时抛出异常。"""
        with pytest.raises(ValidationError):
            DummyAsset(
                name="test",
                kind=AssetKind.PARQUET,
            )

    def test_init_description_defaults_to_none(self, sample_asset):
        """测试 description 默认为 None。"""
        assert sample_asset.description is None

    def test_init_owner_defaults_to_none(self, sample_asset):
        """测试 owner 默认为 None。"""
        assert sample_asset.owner is None

    def test_init_metadata_defaults_to_empty_dict(self, sample_asset):
        """测试 metadata 默认为空字典。"""
        assert sample_asset.metadata == {}

    def test_init_tags_defaults_to_empty_dict(self, sample_asset):
        """测试 tags 默认为空字典。"""
        assert sample_asset.tags == {}

    def test_init_with_optional_fields(self):
        """测试设置可选字段。"""
        asset = DummyAsset(
            name="test",
            kind=AssetKind.PARQUET,
            platform=AssetPlatform.S3,
            description="Test description",
            owner="test_owner",
            metadata={"key": "value"},
            tags={"env": "dev"},
        )
        assert asset.description == "Test description"
        assert asset.owner == "test_owner"
        assert asset.metadata == {"key": "value"}
        assert asset.tags == {"env": "dev"}

    def test_id_enabled_is_false(self, sample_asset):
        """测试 _id_enabled 为 False（Asset 使用 name 作为主键）。"""
        # ID 不应该自动生成
        assert sample_asset.id == ""

    def test_from_any_with_dict(self):
        """测试 from_any() 接受字典。"""
        data = {
            "name": "test",
            "kind": "parquet",
            "platform": "s3",
            "description": "Test asset",
            "owner": "test_owner",
            "metadata": {"key": "value"},
            "tags": {"env": "test"},
        }
        asset = DummyAsset.from_any(data)
        assert asset.name == "test"
        assert asset.kind == AssetKind.PARQUET
        assert asset.platform == AssetPlatform.S3
        assert asset.description == "Test asset"
        assert asset.owner == "test_owner"
        assert asset.metadata == {"key": "value"}
        assert asset.tags == {"env": "test"}

    def test_from_any_with_model_instance(self, sample_asset):
        """测试 from_any() 接受模型实例。"""
        result = DummyAsset.from_any(sample_asset)
        assert result is sample_asset

    def test_roundtrip_export_from_any(self):
        """测试 export() 和 from_any() 的往返转换。"""
        original = DummyAsset(
            name="roundtrip_test",
            kind=AssetKind.CSV,
            platform=AssetPlatform.OSS,
            description="Roundtrip test",
            owner="test_owner",
            metadata={"key1": "value1", "key2": 123},
            tags={"env": "dev", "version": "1.0"},
        )
        # Export to dict
        exported = original.export()
        # Recreate from dict
        restored = DummyAsset.from_any(exported)
        # Verify all fields match
        assert restored.name == original.name
        assert restored.kind == original.kind
        assert restored.platform == original.platform
        assert restored.description == original.description
        assert restored.owner == original.owner
        assert restored.metadata == original.metadata
        assert restored.tags == original.tags


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    """测试 export() 序列化。"""

    def test_export_returns_dict(self, sample_asset):
        """测试 export() 返回字典。"""
        result = sample_asset.export()
        assert isinstance(result, dict)

    def test_export_contains_all_keys(self, sample_asset):
        """测试 export() 包含所有字段。"""
        result = sample_asset.export()
        assert "name" in result
        assert "kind" in result
        assert "platform" in result
        assert "description" in result
        assert "owner" in result
        assert "metadata" in result
        assert "tags" in result

    def test_export_kind_is_string_value(self, sample_asset):
        """测试 export() 的 kind 是字符串值。"""
        result = sample_asset.export()
        assert result["kind"] == "parquet"

    def test_export_platform_is_string_value(self, sample_asset):
        """测试 export() 的 platform 是字符串值。"""
        result = sample_asset.export()
        assert result["platform"] == "local"

    def test_export_preserves_optional_fields(self):
        """测试 export() 保留可选字段。"""
        asset = DummyAsset(
            name="test",
            kind=AssetKind.CSV,
            platform=AssetPlatform.S3,
            description="Test",
            owner="owner1",
            metadata={"foo": "bar"},
            tags={"env": "prod"},
        )
        result = asset.export()
        assert result["description"] == "Test"
        assert result["owner"] == "owner1"
        assert result["metadata"] == {"foo": "bar"}
        assert result["tags"] == {"env": "prod"}


# ──────────────────────────────────────────────────────────────────────────────
# TestEdgeCases
# ──────────────────────────────────────────────────────────────────────────────


class TestEdgeCases:
    """测试边界情况。"""

    def test_name_can_contain_special_chars(self):
        """测试 name 可以包含特殊字符。

        TODO: 应该限制允许的字符。
        """
        asset = DummyAsset(
            name="test-asset_123",
            kind=AssetKind.PARQUET,
            platform=AssetPlatform.LOCAL,
        )
        assert asset.name == "test-asset_123"

    def test_metadata_can_be_nested(self):
        """测试 metadata 可以嵌套。"""
        asset = DummyAsset(
            name="test",
            kind=AssetKind.PARQUET,
            platform=AssetPlatform.LOCAL,
            metadata={"level1": {"level2": "value"}},
        )
        assert asset.metadata["level1"]["level2"] == "value"

    def test_tags_values_must_be_strings(self):
        """测试 tags 值必须是字符串。"""
        # Pydantic 应该验证这个
        with pytest.raises(ValidationError):
            DummyAsset(
                name="test",
                kind=AssetKind.PARQUET,
                platform=AssetPlatform.LOCAL,
                tags={"key": 123},  # 应该是字符串
            )
