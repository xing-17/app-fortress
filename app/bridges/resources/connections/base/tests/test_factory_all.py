"""
综合测试：resources.connections.base.factory

覆盖范围
--------
- TestRegister   register() 写入注册表，重复注册抛 ValueError，返回原类
- TestCreate     create() 返回正确类型，每次返回新实例，未知类型抛 KeyError
- TestBootstrap  bootstrap() 按 resources.connections.yml 批量创建所有实例
"""

import pytest

from app.bridges.resources.connections.base.connection import BaseConnection
from app.bridges.resources.connections.base.factory import ConnectionFactory
from app.bridges.resources.secret.duckdb import SecretDuckdb
from app.common.core.setting import GlobalSetting
from app.common.setting.connections import OssConnectionSetting

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

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

    def get_duckdb_secret(self) -> SecretDuckdb | None:
        return None


# ──────────────────────────────────────────────────────────────────────────────
# TestRegister
# ──────────────────────────────────────────────────────────────────────────────


class TestRegister:
    def test_register_stores_class_in_registry(self, monkeypatch):
        monkeypatch.setattr(ConnectionFactory, "_registry", {})
        ConnectionFactory.register("alpha")(_AlphaConnection)
        assert "alpha" in ConnectionFactory._registry

    def test_register_maps_key_to_correct_class(self, monkeypatch):
        monkeypatch.setattr(ConnectionFactory, "_registry", {})
        ConnectionFactory.register("alpha")(_AlphaConnection)
        assert ConnectionFactory._registry["alpha"] is _AlphaConnection

    def test_register_returns_class_unchanged(self, monkeypatch):
        monkeypatch.setattr(ConnectionFactory, "_registry", {})
        result = ConnectionFactory.register("alpha")(_AlphaConnection)
        assert result is _AlphaConnection

    def test_register_duplicate_raises_value_error(self, monkeypatch):
        monkeypatch.setattr(ConnectionFactory, "_registry", {})
        ConnectionFactory.register("alpha")(_AlphaConnection)
        with pytest.raises(ValueError, match="already registered"):
            ConnectionFactory.register("alpha")(_AlphaConnection)

    def test_register_multiple_types(self, monkeypatch):
        monkeypatch.setattr(ConnectionFactory, "_registry", {})
        ConnectionFactory.register("alpha")(_AlphaConnection)
        ConnectionFactory.register("beta")(_AlphaConnection)
        assert "alpha" in ConnectionFactory._registry
        assert "beta" in ConnectionFactory._registry


# ──────────────────────────────────────────────────────────────────────────────
# TestCreate
# ──────────────────────────────────────────────────────────────────────────────


class TestCreate:
    def _patch(self, monkeypatch) -> None:
        monkeypatch.setattr(ConnectionFactory, "_registry", {"oss": _AlphaConnection})
        monkeypatch.setattr(GlobalSetting.connections, "connections", {"alpha_conn": _CONN_SETTING})

    def test_create_returns_correct_type(self, monkeypatch):
        self._patch(monkeypatch)
        assert isinstance(ConnectionFactory.create("alpha_conn"), _AlphaConnection)

    def test_create_returns_base_connection_instance(self, monkeypatch):
        self._patch(monkeypatch)
        assert isinstance(ConnectionFactory.create("alpha_conn"), BaseConnection)

    def test_create_returns_new_instance_each_call(self, monkeypatch):
        self._patch(monkeypatch)
        assert ConnectionFactory.create("alpha_conn") is not ConnectionFactory.create("alpha_conn")

    def test_create_unknown_type_raises_key_error(self, monkeypatch):
        monkeypatch.setattr(ConnectionFactory, "_registry", {})
        monkeypatch.setattr(GlobalSetting.connections, "connections", {"alpha_conn": _CONN_SETTING})
        with pytest.raises(KeyError, match="Unknown connection type"):
            ConnectionFactory.create("alpha_conn")

    def test_create_unknown_name_raises(self, monkeypatch):
        monkeypatch.setattr(ConnectionFactory, "_registry", {"oss": _AlphaConnection})
        monkeypatch.setattr(GlobalSetting.connections, "connections", {})
        with pytest.raises(Exception):
            ConnectionFactory.create("nonexistent")


# ──────────────────────────────────────────────────────────────────────────────
# TestBootstrap
# ──────────────────────────────────────────────────────────────────────────────


class TestBootstrap:
    def _patch(self, monkeypatch) -> None:
        monkeypatch.setattr(ConnectionFactory, "_registry", {"oss": _AlphaConnection})
        monkeypatch.setattr(GlobalSetting.connections, "connections", {"alpha_conn": _CONN_SETTING})

    def test_bootstrap_returns_dict(self, monkeypatch):
        self._patch(monkeypatch)
        assert isinstance(ConnectionFactory.bootstrap(), dict)

    def test_bootstrap_keys_match_connections(self, monkeypatch):
        self._patch(monkeypatch)
        assert set(ConnectionFactory.bootstrap().keys()) == {"alpha_conn"}

    def test_bootstrap_values_are_base_connection_instances(self, monkeypatch):
        self._patch(monkeypatch)
        result = ConnectionFactory.bootstrap()
        assert isinstance(result["alpha_conn"], BaseConnection)

    def test_bootstrap_empty_connections_returns_empty_dict(self, monkeypatch):
        monkeypatch.setattr(GlobalSetting.connections, "connections", {})
        assert ConnectionFactory.bootstrap() == {}

    def test_bootstrap_multiple_connections(self, monkeypatch):
        conn2 = OssConnectionSetting(
            name="beta_conn",
            type="oss",
            access_key_id="ak2",
            access_key_secret="sk2",
            endpoint="ep2.com",
            region="cn",
            bucket="bkt2",
        )
        monkeypatch.setattr(ConnectionFactory, "_registry", {"oss": _AlphaConnection})
        monkeypatch.setattr(
            GlobalSetting.connections,
            "connections",
            {"alpha_conn": _CONN_SETTING, "beta_conn": conn2},
        )
        result = ConnectionFactory.bootstrap()
        assert set(result.keys()) == {"alpha_conn", "beta_conn"}

    def test_bootstrap_each_connection_is_independent_instance(self, monkeypatch):
        conn2 = OssConnectionSetting(
            name="beta_conn",
            type="oss",
            access_key_id="ak2",
            access_key_secret="sk2",
            endpoint="ep2.com",
            region="cn",
            bucket="bkt2",
        )
        monkeypatch.setattr(ConnectionFactory, "_registry", {"oss": _AlphaConnection})
        monkeypatch.setattr(
            GlobalSetting.connections,
            "connections",
            {"alpha_conn": _CONN_SETTING, "beta_conn": conn2},
        )
        result = ConnectionFactory.bootstrap()
        assert result["alpha_conn"] is not result["beta_conn"]
