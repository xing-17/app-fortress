"""
综合测试：destinations.base.factory

覆盖范围
--------
- TestRegister    register() 写入注册表，重复注册抛 ValueError，返回原类
- TestCreate      create() 返回正确类型，未知 conn type 抛 KeyError
- TestBootstrap   bootstrap() 按 bridges.destinations 批量创建所有实例
"""

from __future__ import annotations

from typing import Any

import pytest

from app.bridges.connections.base.connection import BaseConnection
from app.bridges.destinations.base.destination import BaseDestination
from app.bridges.destinations.base.factory import DestinationFactory
from app.common.core.setting import GlobalSetting
from app.common.setting.bridges import BridgesDestinationSetting
from app.common.setting.connections import OssConnectionSetting

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

_DEST_SETTING = BridgesDestinationSetting(
    name="alpha_dest",
    connection="alpha_conn",
    base_prefix="test/data",
    format="parquet",
)

_CONN_SETTING = OssConnectionSetting(
    name="alpha_conn",
    type="oss",
    access_key_id="ak",
    access_key_secret="sk",
    endpoint="ep.com",
    region="cn",
    bucket="bkt",
)


class _AlphaConnection(BaseConnection):
    def _create_connection(self) -> str:
        return "alpha-handle"

    def ping(self) -> bool:
        return True


class _AlphaDestination(BaseDestination):
    def _resolve_setting(self, name: str) -> BridgesDestinationSetting:
        return _DEST_SETTING

    def write(self, df: Any, table_name: str, partition_col: str, partition_prefix: str) -> None:
        pass

    def export(self) -> dict:
        return {"name": self.name}


def _make_alpha_conn() -> _AlphaConnection:
    return _AlphaConnection(setting=_CONN_SETTING)


# ──────────────────────────────────────────────────────────────────────────────
# TestRegister
# ──────────────────────────────────────────────────────────────────────────────


class TestRegister:
    def test_register_stores_class_in_registry(self, monkeypatch):
        monkeypatch.setattr(DestinationFactory, "_registry", {})
        DestinationFactory.register("alpha")(_AlphaDestination)
        assert "alpha" in DestinationFactory._registry

    def test_register_maps_key_to_correct_class(self, monkeypatch):
        monkeypatch.setattr(DestinationFactory, "_registry", {})
        DestinationFactory.register("alpha")(_AlphaDestination)
        assert DestinationFactory._registry["alpha"] is _AlphaDestination

    def test_register_returns_class_unchanged(self, monkeypatch):
        monkeypatch.setattr(DestinationFactory, "_registry", {})
        result = DestinationFactory.register("alpha")(_AlphaDestination)
        assert result is _AlphaDestination

    def test_register_duplicate_raises_value_error(self, monkeypatch):
        monkeypatch.setattr(DestinationFactory, "_registry", {})
        DestinationFactory.register("alpha")(_AlphaDestination)
        with pytest.raises(ValueError, match="already registered"):
            DestinationFactory.register("alpha")(_AlphaDestination)

    def test_register_multiple_types(self, monkeypatch):
        monkeypatch.setattr(DestinationFactory, "_registry", {})
        DestinationFactory.register("alpha")(_AlphaDestination)
        DestinationFactory.register("beta")(_AlphaDestination)
        assert "alpha" in DestinationFactory._registry
        assert "beta" in DestinationFactory._registry


# ──────────────────────────────────────────────────────────────────────────────
# TestCreate
# ──────────────────────────────────────────────────────────────────────────────


class TestCreate:
    def test_create_returns_correct_type(self, monkeypatch):
        monkeypatch.setattr(DestinationFactory, "_registry", {"oss": _AlphaDestination})
        result = DestinationFactory.create("alpha_dest", conn=_make_alpha_conn())
        assert isinstance(result, _AlphaDestination)

    def test_create_returns_base_destination_instance(self, monkeypatch):
        monkeypatch.setattr(DestinationFactory, "_registry", {"oss": _AlphaDestination})
        result = DestinationFactory.create("alpha_dest", conn=_make_alpha_conn())
        assert isinstance(result, BaseDestination)

    def test_create_returns_new_instance_each_call(self, monkeypatch):
        monkeypatch.setattr(DestinationFactory, "_registry", {"oss": _AlphaDestination})
        conn = _make_alpha_conn()
        a = DestinationFactory.create("alpha_dest", conn=conn)
        b = DestinationFactory.create("alpha_dest", conn=conn)
        assert a is not b

    def test_create_unknown_conn_type_raises_key_error(self, monkeypatch):
        monkeypatch.setattr(DestinationFactory, "_registry", {})
        with pytest.raises(KeyError, match="Unknown destination type"):
            DestinationFactory.create("alpha_dest", conn=_make_alpha_conn())


# ──────────────────────────────────────────────────────────────────────────────
# TestBootstrap
# ──────────────────────────────────────────────────────────────────────────────


class TestBootstrap:
    def _patch(self, monkeypatch) -> None:
        monkeypatch.setattr(DestinationFactory, "_registry", {"oss": _AlphaDestination})
        monkeypatch.setattr(GlobalSetting.bridges, "destinations", [_DEST_SETTING])

    def test_bootstrap_returns_dict(self, monkeypatch):
        self._patch(monkeypatch)
        result = DestinationFactory.bootstrap({"alpha_conn": _make_alpha_conn()})
        assert isinstance(result, dict)

    def test_bootstrap_keys_match_destination_names(self, monkeypatch):
        self._patch(monkeypatch)
        result = DestinationFactory.bootstrap({"alpha_conn": _make_alpha_conn()})
        assert set(result.keys()) == {"alpha_dest"}

    def test_bootstrap_values_are_base_destination_instances(self, monkeypatch):
        self._patch(monkeypatch)
        result = DestinationFactory.bootstrap({"alpha_conn": _make_alpha_conn()})
        assert isinstance(result["alpha_dest"], BaseDestination)

    def test_bootstrap_empty_destinations_returns_empty_dict(self, monkeypatch):
        monkeypatch.setattr(GlobalSetting.bridges, "destinations", [])
        assert DestinationFactory.bootstrap({}) == {}

    def test_bootstrap_missing_connection_raises_key_error(self, monkeypatch):
        self._patch(monkeypatch)
        with pytest.raises(KeyError, match="alpha_conn"):
            DestinationFactory.bootstrap({})  # no connections injected

    def test_bootstrap_connection_is_passed_to_destination(self, monkeypatch):
        self._patch(monkeypatch)
        conn = _make_alpha_conn()
        result = DestinationFactory.bootstrap({"alpha_conn": conn})
        assert result["alpha_dest"].connection is conn
