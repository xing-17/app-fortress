"""
综合测试：bastion.domain.assetkind

覆盖范围
--------
- TestAssetKind         枚举值正确性
"""

from __future__ import annotations

from bastion.domain.assetkind import AssetKind

# ──────────────────────────────────────────────────────────────────────────────
# TestAssetKind
# ──────────────────────────────────────────────────────────────────────────────


class TestAssetKind:
    """测试 AssetKind 枚举。"""

    def test_enum_values_exist(self):
        """测试所有预定义值存在。"""
        assert AssetKind.PARQUET == "parquet"
        assert AssetKind.CSV == "csv"
        assert AssetKind.ANY == "any"
