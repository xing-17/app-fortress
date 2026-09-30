from __future__ import annotations

import pytest

from app.internal.util.id import IID


class TestIIDGenerateId:
    def test_default_length_is_twelve(self):
        assert len(IID.generate_id()) == 12

    def test_custom_length_is_respected(self):
        assert len(IID.generate_id(length=8)) == 8

    def test_length_longer_than_uuid_returns_full_uuid(self):
        assert len(IID.generate_id(length=100)) == 36

    def test_no_prefix_returns_bare_id(self):
        _id = IID.generate_id(length=8)
        assert not _id.startswith("usr_")

    def test_prefix_is_prepended(self):
        _id = IID.generate_id(length=8, prefix="usr_")
        assert _id.startswith("usr_")
        assert len(_id) == len("usr_") + 8

    def test_empty_string_prefix_is_ignored(self):
        _id = IID.generate_id(length=8, prefix="")
        assert len(_id) == 8

    def test_generated_ids_are_unique(self):
        assert IID.generate_id() != IID.generate_id()


class TestIIDInit:
    def test_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            IID()
