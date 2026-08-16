"""Unit tests for IBastionObject."""

from __future__ import annotations

import json

from bastion._internal.model import IBastionModel
from bastion._internal.object import IBastionObject


class _ItemModel(IBastionModel):
    __test__ = False
    _id_enabled = False
    name: str
    value: int = 0
    note: str | None = None


class _ItemObject(IBastionObject):
    __test__ = False
    _domain_class = _ItemModel

    def __init__(self, name: str, value: int = 0, note: str | None = None):
        self.domain = _ItemModel(name=name, value=value, note=note)


def test_export_contains_model_fields():
    obj = _ItemObject("example", value=42)
    exported = obj.export()
    assert exported["name"] == "example"
    assert exported["value"] == 42


def test_export_is_pure_data():
    obj = _ItemObject("example")
    exported = obj.export()
    assert "__class__" not in exported
    assert "__module__" not in exported


def test_describe_is_json():
    obj = _ItemObject("example", value=7)
    description = obj.describe()
    data = json.loads(description)
    assert data["name"] == "example"
    assert "\n" in description


def test_getattr_proxies_to_domain():
    obj = _ItemObject("proxy_test", value=99)
    assert obj.name == "proxy_test"
    assert obj.value == 99


def test_roundtrip_via_from_dict():
    obj = _ItemObject("roundtrip", value=5, note="hello")
    data = obj.export()
    restored = _ItemObject.from_dict(data)
    assert restored.name == "roundtrip"
    assert restored.value == 5
    assert restored.note == "hello"


def test_roundtrip_preserves_none():
    obj = _ItemObject("none_test", note=None)
    data = obj.export()
    restored = _ItemObject.from_dict(data)
    assert restored.note is None


def test_from_domain():
    model = _ItemModel(name="direct", value=3)
    obj = _ItemObject.from_domain(model)
    assert obj.name == "direct"
    assert obj.domain is model


def test_from_dict_raises_without_domain_class():
    class _NoDomain(IBastionObject):
        pass

    try:
        _NoDomain.from_dict({"name": "x"})
        assert False, "should have raised"
    except TypeError:
        pass
