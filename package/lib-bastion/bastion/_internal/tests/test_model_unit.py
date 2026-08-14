"""Unit tests for IBastionModel."""

from __future__ import annotations

from bastion._internal.model import IBastionModel


class TestModel(IBastionModel):
    """Test model with custom prefix."""

    __test__ = False
    _id_prefix = "test"
    name: str = "default"


class TestModelNoPrefix(IBastionModel):
    """Test model without prefix."""

    __test__ = False
    _id_prefix = ""
    value: int = 0


def test_auto_id_generation():
    """Test that ID is auto-generated on initialization."""
    model = TestModel(name="example")
    assert model.id
    assert model.id.startswith("test-")
    assert len(model.id.split("-")[1]) == 12


def test_auto_id_generation_no_prefix():
    """Test ID generation without prefix."""
    model = TestModelNoPrefix(value=42)
    assert model.id
    assert "-" not in model.id
    assert len(model.id) == 12


def test_custom_id():
    """Test providing a custom ID."""
    custom_id = "custom-123"
    model = TestModel(id=custom_id, name="example")
    assert model.id == custom_id


def test_from_json():
    """Test creating model from JSON dictionary."""
    data = {"id": "test-abc123", "name": "from_json"}
    model = TestModel.from_json(data)
    assert model.id == "test-abc123"
    assert model.name == "from_json"


def test_export():
    """Test exporting model to dictionary."""
    model = TestModel(name="export_test")
    exported = model.export()
    assert isinstance(exported, dict)
    assert "id" in exported
    assert "name" in exported
    assert exported["name"] == "export_test"


def test_describe():
    """Test JSON string representation."""
    model = TestModel(name="describe_test")
    description = model.describe()
    assert isinstance(description, str)
    assert "describe_test" in description
    assert "id" in description


def test_logic_name():
    """Test logic name property."""
    model = TestModel(id="test-123", name="logic")
    logic_name = model._logic_name
    assert logic_name == "TestModel(test-123)"


def test_extra_fields_ignored():
    """Test that extra fields are ignored."""
    data = {"name": "test", "extra_field": "ignored"}
    model = TestModel.from_json(data)
    assert model.name == "test"
    assert not hasattr(model, "extra_field")


def test_validate_assignment():
    """Test that assignment validation works."""
    model = TestModel(name="initial")
    model.name = "updated"
    assert model.name == "updated"
