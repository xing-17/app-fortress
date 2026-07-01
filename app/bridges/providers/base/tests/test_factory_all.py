"""
综合测试：app.bridges.providers.base.factory

覆盖范围
--------
- TestRegister   register() 写入注册表，重复注册抛 ValueError，返回原类
- TestCreate     create() 返回正确实例，每次返回新对象，未知类型抛 KeyError
- TestBootstrap  bootstrap() 根据 GlobalSetting.bridges.providers 批量创建 provider
"""

from __future__ import annotations

from typing import Any

import pytest

from app.bridges.providers.base.factory import ProviderFactory
from app.bridges.providers.base.provider import BaseProvider
from app.bridges.providers.base.session import BaseSession
from app.common.core.setting import GlobalSetting
from app.common.setting.bridges import BaseProviderSetting

# ──────────────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────────────


_ALPHA_SETTING = BaseProviderSetting(name="alpha", type="alpha")


class _AlphaSession(BaseSession):
    def _create_session(self) -> str:
        return "alpha-handle"


class _AlphaProvider(BaseProvider):
    @property
    def setting(self) -> BaseProviderSetting:
        return _ALPHA_SETTING

    def _create_session(self) -> _AlphaSession:
        return _AlphaSession(name=self.name, type=self.type, region=self.region)

    def call(self, method: str, *args: Any, **kwargs: Any) -> Any:
        return None

    def export(self) -> dict[str, Any]:
        return {}


# ──────────────────────────────────────────────────────────────────────────────
# TestRegister
# ──────────────────────────────────────────────────────────────────────────────


class TestRegister:
    def test_register_stores_class_in_registry(self, monkeypatch):
        monkeypatch.setattr(ProviderFactory, "_registry", {})
        ProviderFactory.register("alpha")(_AlphaProvider)
        assert "alpha" in ProviderFactory._registry

    def test_register_maps_key_to_correct_class(self, monkeypatch):
        monkeypatch.setattr(ProviderFactory, "_registry", {})
        ProviderFactory.register("alpha")(_AlphaProvider)
        assert ProviderFactory._registry["alpha"] is _AlphaProvider

    def test_register_returns_class_unchanged(self, monkeypatch):
        monkeypatch.setattr(ProviderFactory, "_registry", {})
        result = ProviderFactory.register("alpha")(_AlphaProvider)
        assert result is _AlphaProvider

    def test_register_duplicate_raises_value_error(self, monkeypatch):
        monkeypatch.setattr(ProviderFactory, "_registry", {})
        ProviderFactory.register("alpha")(_AlphaProvider)
        with pytest.raises(ValueError, match="already registered"):
            ProviderFactory.register("alpha")(_AlphaProvider)

    def test_register_multiple_different_types(self, monkeypatch):
        monkeypatch.setattr(ProviderFactory, "_registry", {})
        ProviderFactory.register("alpha")(_AlphaProvider)
        ProviderFactory.register("beta")(_AlphaProvider)
        assert "alpha" in ProviderFactory._registry
        assert "beta" in ProviderFactory._registry


# ──────────────────────────────────────────────────────────────────────────────
# TestCreate
# ──────────────────────────────────────────────────────────────────────────────


class TestCreate:
    def test_create_returns_correct_type(self, monkeypatch):
        monkeypatch.setattr(ProviderFactory, "_registry", {"alpha": _AlphaProvider})
        result = ProviderFactory.create("alpha")
        assert isinstance(result, _AlphaProvider)

    def test_create_returns_base_provider_instance(self, monkeypatch):
        monkeypatch.setattr(ProviderFactory, "_registry", {"alpha": _AlphaProvider})
        result = ProviderFactory.create("alpha")
        assert isinstance(result, BaseProvider)

    def test_create_returns_new_instance_each_call(self, monkeypatch):
        monkeypatch.setattr(ProviderFactory, "_registry", {"alpha": _AlphaProvider})
        a = ProviderFactory.create("alpha")
        b = ProviderFactory.create("alpha")
        assert a is not b

    def test_create_unknown_type_raises_key_error(self, monkeypatch):
        monkeypatch.setattr(ProviderFactory, "_registry", {})
        with pytest.raises(KeyError):
            ProviderFactory.create("nonexistent")


# ──────────────────────────────────────────────────────────────────────────────
# TestBootstrap
# ──────────────────────────────────────────────────────────────────────────────


class TestBootstrap:
    def test_bootstrap_returns_dict(self, monkeypatch):
        monkeypatch.setattr(ProviderFactory, "_registry", {"alpha": _AlphaProvider})
        monkeypatch.setattr(GlobalSetting.bridges, "providers", {"alpha": None})
        result = ProviderFactory.bootstrap()
        assert isinstance(result, dict)

    def test_bootstrap_keys_match_setting_providers(self, monkeypatch):
        monkeypatch.setattr(ProviderFactory, "_registry", {"alpha": _AlphaProvider})
        monkeypatch.setattr(GlobalSetting.bridges, "providers", {"alpha": None})
        result = ProviderFactory.bootstrap()
        assert set(result.keys()) == {"alpha"}

    def test_bootstrap_values_are_provider_instances(self, monkeypatch):
        monkeypatch.setattr(ProviderFactory, "_registry", {"alpha": _AlphaProvider})
        monkeypatch.setattr(GlobalSetting.bridges, "providers", {"alpha": None})
        result = ProviderFactory.bootstrap()
        assert isinstance(result["alpha"], BaseProvider)

    def test_bootstrap_providers_not_connected(self, monkeypatch):
        monkeypatch.setattr(ProviderFactory, "_registry", {"alpha": _AlphaProvider})
        monkeypatch.setattr(GlobalSetting.bridges, "providers", {"alpha": None})
        result = ProviderFactory.bootstrap()
        assert not result["alpha"]._session.is_ready()
