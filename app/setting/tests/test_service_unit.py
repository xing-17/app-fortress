from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from app.internal.constant.servicekind import ServiceKind
from app.setting.service import (
    AuthSetting,
    DRASetting,
    MachineServiceSetting,
    McpHostServiceSetting,
    NodeEndpointSetting,
    NodeServiceSetting,
    ServicesSetting,
    TokenSetting,
    WebHostServiceSetting,
)


class TestServiceDefaults:
    def test_kinds_are_fixed(self):
        assert MachineServiceSetting().kind == ServiceKind.MACHINE
        assert NodeServiceSetting().kind == ServiceKind.NODE
        assert McpHostServiceSetting().kind == ServiceKind.MCPHOST
        assert WebHostServiceSetting().kind == ServiceKind.WEBHOST

    def test_default_ports(self):
        assert NodeServiceSetting().port == 8800
        assert McpHostServiceSetting().port == 8801
        assert WebHostServiceSetting().port == 8802

    def test_default_log_derived_from_kind(self):
        _log = NodeServiceSetting().log
        assert _log.name == "node"
        assert _log.tags["service"] == "node"

    def test_kind_tag_is_not_overridable(self):
        assert NodeServiceSetting(tags={"kind": "x"}).tags["kind"] == ServiceKind.NODE

    @pytest.mark.parametrize("port", [0, 65536])
    def test_invalid_port_raises(self, port):
        with pytest.raises(ValidationError):
            NodeServiceSetting(port=port)

    def test_wrong_kind_raises(self):
        with pytest.raises(ValidationError):
            NodeServiceSetting(kind="mcphost")


class TestMachineSetting:
    def test_defaults_are_a_snapshot_a_minute_for_twelve_hours(self):
        _setting = MachineServiceSetting()
        assert _setting.interval_seconds == 60
        assert _setting.retention_hours == 12.0
        assert _setting.max_snapshots == 720

    def test_max_snapshots_follows_the_two_settings(self):
        _setting = MachineServiceSetting(interval_seconds=30, retention_hours=2)
        assert _setting.max_snapshots == 240

    def test_max_snapshots_rounds_up(self):
        assert MachineServiceSetting(interval_seconds=60, retention_hours=0.02).max_snapshots == 2

    @pytest.mark.parametrize("field, value", [("interval_seconds", 0), ("retention_hours", 0), ("retention_hours", -1)])
    def test_invalid_values_raise(self, field, value):
        with pytest.raises(ValidationError):
            MachineServiceSetting(**{field: value})

    def test_too_many_snapshots_raise(self):
        with pytest.raises(ValidationError, match="exceed"):
            MachineServiceSetting(interval_seconds=1, retention_hours=100)

    def test_loaded_through_services_setting(self):
        _services = ServicesSetting.model_validate({"machine": {"interval_seconds": 120, "retention_hours": 24}})
        assert _services.machine.max_snapshots == 720


class TestHostNodes:
    @pytest.mark.parametrize("cls", [McpHostServiceSetting, WebHostServiceSetting])
    def test_default_nodes_is_single_local_node(self, cls):
        _nodes = cls().nodes
        assert [(n.name, n.endpoint) for n in _nodes] == [("centre", "http://127.0.0.1:8800")]

    @pytest.mark.parametrize("cls", [McpHostServiceSetting, WebHostServiceSetting])
    def test_multiple_nodes(self, cls):
        _setting = cls(
            nodes=[
                {"name": "snt", "endpoint": "http://127.0.0.1:8800"},
                {"name": "centre", "endpoint": "https://centre.example.com"},
            ]
        )
        assert [n.name for n in _setting.nodes] == ["snt", "centre"]
        assert isinstance(_setting.nodes[0], NodeEndpointSetting)

    @pytest.mark.parametrize("cls", [McpHostServiceSetting, WebHostServiceSetting])
    def test_duplicate_node_names_raise(self, cls):
        with pytest.raises(ValidationError, match="duplicate"):
            cls(
                nodes=[
                    {"name": "snt", "endpoint": "http://a"},
                    {"name": "snt", "endpoint": "http://b"},
                ]
            )

    @pytest.mark.parametrize("cls", [McpHostServiceSetting, WebHostServiceSetting])
    def test_empty_nodes_raise(self, cls):
        with pytest.raises(ValidationError):
            cls(nodes=[])

    def test_node_requires_name_and_endpoint(self):
        with pytest.raises(ValidationError):
            NodeEndpointSetting(name="snt")
        with pytest.raises(ValidationError):
            NodeEndpointSetting(endpoint="http://a")

    def test_node_empty_strings_raise(self):
        with pytest.raises(ValidationError):
            NodeEndpointSetting(name="", endpoint="http://a")
        with pytest.raises(ValidationError):
            NodeEndpointSetting(name="snt", endpoint="")

    def test_node_service_has_no_nodes(self):
        assert not hasattr(NodeServiceSetting(), "nodes")


class TestDRASetting:
    def test_defaults(self):
        _s = NodeServiceSetting().dra
        assert (_s.timeout_seconds, _s.max_rows, _s.max_result_mb, _s.memory_limit_mb, _s.threads) == (
            30,
            10_000,
            128,
            1024,
            4,
        )

    def test_override_from_dict(self):
        _s = ServicesSetting.from_dict({"node": {"dra": {"timeout_seconds": 5, "max_result_mb": 16}}})
        assert _s.node.dra.timeout_seconds == 5
        assert _s.node.dra.max_result_mb == 16
        assert _s.node.dra.max_rows == 10_000

    @pytest.mark.parametrize(
        "field, value",
        [("timeout_seconds", 0), ("max_rows", 0), ("max_result_mb", 0), ("memory_limit_mb", 8), ("threads", 0)],
    )
    def test_invalid_limits_raise(self, field, value):
        with pytest.raises(ValidationError):
            DRASetting(**{field: value})


class TestAuthSetting:
    def test_defaults(self):
        _a = NodeServiceSetting().auth
        assert _a.masterfile == "../local/.auth/password.key"
        assert _a.tokens == []

    def test_from_yaml(self, tmp_path):
        _path = tmp_path / "services.yaml"
        _path.write_text(
            "node:\n  auth:\n    masterfile: ../k\n    tokens:\n"
            "      - name: chatgpt\n        version: 2\n        expires: 2027-10-22\n",
            encoding="utf-8",
        )
        _a = ServicesSetting.from_yaml(_path).node.auth
        assert _a.masterfile == "../k"
        assert (_a.tokens[0].name, _a.tokens[0].version) == ("chatgpt", 2)
        assert _a.tokens[0].expires == date(2027, 10, 22)
        assert _a.tokens[0].revoked is False

    def test_token_defaults(self):
        _t = TokenSetting(name="a")
        assert (_t.description, _t.version, _t.expires, _t.revoked) == ("", 1, None, False)

    @pytest.mark.parametrize("name", ["", "A", "a_b", "-a", "a b", "a.b", "a" * 33, "a\n"])
    def test_invalid_token_name_raises(self, name):
        with pytest.raises(ValidationError):
            TokenSetting(name=name)

    def test_invalid_version_raises(self):
        with pytest.raises(ValidationError):
            TokenSetting(name="a", version=0)

    def test_duplicate_token_names_raise(self):
        with pytest.raises(ValidationError, match="duplicate"):
            AuthSetting(tokens=[{"name": "a"}, {"name": "a", "version": 2}])

    def test_export_roundtrip(self):
        _s = ServicesSetting.from_dict(
            {"node": {"auth": {"tokens": [{"name": "a", "expires": "2027-10-22", "revoked": True}]}}}
        )
        assert ServicesSetting.from_dict(_s.export()) == _s


class TestPublicHosts:
    def test_default_is_empty(self):
        assert McpHostServiceSetting().public_hosts == []

    def test_from_yaml(self, tmp_path):
        _path = tmp_path / "services.yaml"
        _path.write_text(
            "mcphost:\n  public_hosts:\n    - WWW.Example.com\n    - mcp.example.com:8443\n", encoding="utf-8"
        )
        assert ServicesSetting.from_yaml(_path).mcphost.public_hosts == ["www.example.com", "mcp.example.com:8443"]

    def test_duplicates_are_dropped(self):
        assert McpHostServiceSetting(public_hosts=["a.com", "A.com"]).public_hosts == ["a.com"]

    @pytest.mark.parametrize(
        "host",
        [
            "",
            "*",
            "*.example.com",
            "https://a.com",
            "a.com/mcp",
            "a.com:",
            "a.com:123456",
            "a b.com",
            "a.com\nb.com",
            "-a.com",
        ],
    )
    def test_invalid_host_raises(self, host):
        with pytest.raises(ValidationError, match="public_hosts"):
            McpHostServiceSetting(public_hosts=[host])


class TestNodeEndpointToken:
    def test_token_defaults_to_none(self):
        assert NodeEndpointSetting(name="snt", endpoint="http://a").token is None

    def test_token_from_yaml(self, tmp_path):
        _path = tmp_path / "services.yaml"
        _path.write_text(
            "mcphost:\n  nodes:\n    - name: snt\n      endpoint: http://127.0.0.1:8800\n      token: abc123\n",
            encoding="utf-8",
        )
        _node = ServicesSetting.from_yaml(_path).mcphost.nodes[0]
        assert _node.token.get_secret_value() == "abc123"

    def test_token_is_hidden(self):
        _s = McpHostServiceSetting(nodes=[{"name": "snt", "endpoint": "http://a", "token": "abc123"}])
        assert "abc123" not in repr(_s)
        assert "abc123" not in _s.describe()
        assert "abc123" not in str(_s.export())


class TestServicesSetting:
    def test_defaults(self):
        _s = ServicesSetting()
        assert _s.node.port == 8800
        assert _s.mcphost.nodes[0].endpoint == "http://127.0.0.1:8800"
        assert _s.webhost.nodes[0].endpoint == "http://127.0.0.1:8800"

    def test_from_dict_partial(self):
        _s = ServicesSetting.from_dict({"webhost": {"enabled": False}})
        assert _s.webhost.enabled is False
        assert _s.mcphost.enabled is True

    def test_from_yaml_with_nodes(self, tmp_path):
        _path = tmp_path / "services.yaml"
        _path.write_text(
            "mcphost:\n  nodes:\n    - name: snt\n      endpoint: http://127.0.0.1:8800\n",
            encoding="utf-8",
        )
        _s = ServicesSetting.from_yaml(_path)
        assert _s.mcphost.nodes[0].name == "snt"

    def test_export_roundtrip(self):
        _s = ServicesSetting()
        assert ServicesSetting.from_dict(_s.export()) == _s
