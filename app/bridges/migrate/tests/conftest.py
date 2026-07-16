"""
pytest 配置文件 for migrate 测试。

Mock 掉可能引起问题的模块级初始化。
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ──────────────────────────────────────────────────────────────────────────────
# Mock ModuleBridgesCache 和 ModuleBridgesWarehouse
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session", autouse=True)
def mock_bridges_resources():
    """
    Mock 掉 BridgesCache 和 BridgesWarehouse 的模块级初始化。

    这样可以避免在导入时连接真实的数据库文件。
    """
    # Mock BridgesCache
    with patch("app.bridges.resources.cache.cache.BridgesCache.load") as mock_cache_load:
        mock_cache = MagicMock()
        mock_cache_load.return_value = mock_cache

        # Mock BridgesWarehouse
        with patch("app.bridges.resources._warehouse.warehouse.BridgesWarehouse"):
            mock_warehouse_instance = MagicMock()

            yield {
                "cache": mock_cache,
                "warehouse": mock_warehouse_instance,
            }
