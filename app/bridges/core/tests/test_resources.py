"""
综合测试：app.bridges.core.resources

覆盖范围
--------
- TestResourcesBasic     基本实例化、加载
- TestProvidersAccess    Provider 访问方法
- TestDestinationsAccess Destination 访问方法
- TestSourcesAccess      Source 访问方法
- TestExport             export() 和 describe() 方法

注意：这些测试依赖于实际的资源配置。
如果资源配置为空，某些测试可能失败。
"""

from __future__ import annotations

import json

from app.bridges.core.resources import BridgesResources, ModuleBridgesResources

# ──────────────────────────────────────────────────────────────────────────────
# TestResourcesBasic
# ──────────────────────────────────────────────────────────────────────────────


class TestResourcesBasic:
    def test_create_resources_instance(self):
        """测试创建 BridgesResources 实例。"""
        resources = BridgesResources()
        assert resources is not None
        assert hasattr(resources, "setting")
        assert hasattr(resources, "cache")

    def test_resources_has_factories(self):
        """测试 resources 包含工厂实例。"""
        resources = BridgesResources()
        assert hasattr(resources, "_provider_factory")
        assert hasattr(resources, "_connection_factory")
        assert hasattr(resources, "_destination_factory")
        assert hasattr(resources, "_source_factory")

    def test_resources_has_collections(self):
        """测试 resources 包含资源集合。"""
        resources = BridgesResources()
        assert isinstance(resources._providers, dict)
        assert isinstance(resources._connections, dict)
        assert isinstance(resources._destinations, dict)
        assert isinstance(resources._sources, dict)

    def test_module_singleton_exists(self):
        """测试全局单例存在。"""
        assert ModuleBridgesResources is not None
        assert isinstance(ModuleBridgesResources, BridgesResources)


# ──────────────────────────────────────────────────────────────────────────────
# TestProvidersAccess
# ──────────────────────────────────────────────────────────────────────────────


class TestProvidersAccess:
    def test_get_provider_raises_on_missing(self):
        """测试 get_provider() 在找不到时抛出异常。"""
        resources = BridgesResources()
        try:
            resources.get_provider("nonexistent_provider")
            assert False, "应该抛出 ValueError"
        except ValueError as e:
            assert "not found" in str(e)

    def test_get_first_provider_by_type_raises_on_missing(self):
        """测试 get_first_provider_by_type() 在找不到时抛出异常。"""
        resources = BridgesResources()
        try:
            resources.get_first_provider_by_type("nonexistent_type")
            assert False, "应该抛出 ValueError"
        except ValueError as e:
            assert "No provider found" in str(e)


# ──────────────────────────────────────────────────────────────────────────────
# TestDestinationsAccess
# ──────────────────────────────────────────────────────────────────────────────


class TestDestinationsAccess:
    def test_get_destination_raises_on_missing(self):
        """测试 get_destination() 在找不到时抛出异常。"""
        resources = BridgesResources()
        try:
            resources.get_destination("nonexistent_destination")
            assert False, "应该抛出 ValueError"
        except ValueError as e:
            assert "not found" in str(e)

    def test_list_destinations_returns_list(self):
        """测试 list_destinations() 返回列表。"""
        resources = BridgesResources()
        destinations = resources.list_destinations()
        assert isinstance(destinations, list)


# ──────────────────────────────────────────────────────────────────────────────
# TestSourcesAccess
# ──────────────────────────────────────────────────────────────────────────────


class TestSourcesAccess:
    def test_get_sources_raises_on_missing(self):
        """测试 get_sources() 在找不到时抛出异常。"""
        resources = BridgesResources()
        try:
            resources.get_sources("nonexistent_source")
            assert False, "应该抛出 ValueError"
        except ValueError as e:
            assert "not found" in str(e)

    def test_get_sources_by_tags_returns_list(self):
        """测试 get_sources_by_tags() 返回列表。"""
        resources = BridgesResources()
        # 使用不存在的标签应该返回空列表
        sources = resources.get_sources_by_tags({"nonexistent": "tag"})
        assert isinstance(sources, list)

    def test_get_sources_by_tags_filters_correctly(self):
        """测试 get_sources_by_tags() 正确过滤。"""
        resources = BridgesResources()
        # 如果有配置的 sources，这个测试会更有意义
        # 这里只验证返回类型
        sources = resources.get_sources_by_tags({})
        assert isinstance(sources, list)


# ──────────────────────────────────────────────────────────────────────────────
# TestRefresh
# ──────────────────────────────────────────────────────────────────────────────


class TestRefresh:
    def test_refresh_method_exists(self):
        """测试 refresh() 方法存在。"""
        resources = BridgesResources()
        assert hasattr(resources, "refresh")
        assert callable(resources.refresh)

    def test_refresh_method_runs(self):
        """测试 refresh() 方法可以运行。"""
        resources = BridgesResources()
        # 应该不抛出异常
        resources.refresh()


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_returns_dict(self):
        """测试 export() 返回字典。"""
        resources = BridgesResources()
        result = resources.export()
        assert isinstance(result, dict)

    def test_export_contains_all_sections(self):
        """测试导出包含所有部分。"""
        resources = BridgesResources()
        result = resources.export()
        assert "providers" in result
        assert "connections" in result
        assert "destinations" in result
        assert "sources" in result

    def test_export_sections_are_dicts(self):
        """测试导出的各部分都是字典。"""
        resources = BridgesResources()
        result = resources.export()
        assert isinstance(result["providers"], dict)
        assert isinstance(result["connections"], dict)
        assert isinstance(result["destinations"], dict)
        assert isinstance(result["sources"], dict)

    def test_describe_returns_json_string(self):
        """测试 describe() 返回 JSON 字符串。"""
        resources = BridgesResources()
        result = resources.describe()
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_describe_contains_same_data_as_export(self):
        """测试 describe() 包含与 export() 相同的数据。"""
        resources = BridgesResources()
        exported = resources.export()
        described = json.loads(resources.describe())
        assert exported == described
