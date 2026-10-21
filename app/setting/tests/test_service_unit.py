from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.internal.constant.servicekind import ServiceKind
from app.setting.service import (
    MachineServiceSetting,
    McpHostServiceSetting,
    NodeEndpointSetting,
    NodeServiceSetting,
    ServicesSetting,
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
