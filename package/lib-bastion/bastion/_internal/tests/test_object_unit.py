"""Unit tests for IBastionObject."""

from __future__ import annotations

import json

from bastion._internal.object import IBastionObject


class TestObject(IBastionObject):
    """Test object for testing."""

    __test__ = False

    def __init__(self, name: str):
        self.name = name


def test_export():
    """Test exporting object metadata."""
    obj = TestObject("example")
    exported = obj.export()
    assert isinstance(exported, dict)
    assert exported["__class__"] == "TestObject"
    assert "__module__" in exported


def test_describe():
    """Test JSON string representation."""
    obj = TestObject("example")
    description = obj.describe()
    assert isinstance(description, str)
    data = json.loads(description)
    assert data["__class__"] == "TestObject"
    assert "__module__" in data


def test_describe_formatting():
    """Test that describe returns formatted JSON."""
    obj = TestObject("example")
    description = obj.describe()
    # Check for indentation (formatted JSON)
    assert "\n" in description
    assert "    " in description


def test_inheritance():
    """Test that IBastionObject can be inherited."""

    class CustomObject(IBastionObject):
        def __init__(self, value: int):
            self.value = value

    obj = CustomObject(42)
    exported = obj.export()
    assert exported["__class__"] == "CustomObject"
