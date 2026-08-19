"""
综合测试：bastion.domain.assetitem

覆盖范围
--------
-- TestAssetItem 
"""

from __future__ import annotations

from bastion.domain.assetitem import BaseAssetItemModel

# ──────────────────────────────────────────────────────────────────────────────
# TestAssetItem
# ──────────────────────────────────────────────────────────────────────────────


class TestAssetItem:
    """测试 AssetItem 类。"""

    def test_create_asset_item(self):
        """测试创建 AssetItem 实例。"""
        asset_item = BaseAssetItemModel(
            name="example_asset",
            platform="local",
        )
        assert asset_item.name == "example_asset"
        assert asset_item.platform == "local"
        

    def test_asset_item_default_values(self):
        """测试 AssetItem 的默认值。"""
        asset_item = BaseAssetItemModel(
            name="example_asset",
            platform="local",
        )
        assert asset_item.partitions == {}
        assert asset_item.owner is None
        assert asset_item.metadata == {}
        assert asset_item.tags == {}
        
    def test_asset_item_export(self):
        """测试 AssetItem 的导出功能。"""
        asset_item = BaseAssetItemModel(
            name="example_asset",
            platform="local",
            partitions={"year": "2023", "month": "06"},
            owner="user123",
            metadata={"description": "Sample asset"},
            tags={"env": "test"},
        )
        exported = asset_item.export()
        assert exported["name"] == "example_asset"
        assert exported["platform"] == "local"
        assert exported["partitions"] == {"year": "2023", "month": "06"}
        assert exported["owner"] == "user123"
        assert exported["metadata"] == {"description": "Sample asset"}
        assert exported["tags"] == {"env": "test"}
        
