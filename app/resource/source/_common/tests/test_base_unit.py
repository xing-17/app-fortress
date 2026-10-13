from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.internal.constant.sourceprovider import SourceProvider
from app.resource.source._common.tests.fakes.base import FakeDataset
from app.resource.source._common.tests.fakes.ok.alpha import AlphaDataset


class TestGovernedConstruction:
    def test_direct_construction_without_authorization_raises(self, source):
        _ds = source.dataset("alpha")
        with pytest.raises(ValidationError, match="must be constructed via parent resource"):
            AlphaDataset(asset=_ds.asset, database=_ds.database, log_stream=_ds.log_stream)

    def test_authorized_construction_succeeds(self, source):
        _ds = source.dataset("alpha")
        assert isinstance(_ds, AlphaDataset)

    def test_authorized_sentinel_is_not_kept_as_a_field(self, source):
        _ds = source.dataset("alpha")
        assert "_authorized" not in _ds.model_dump()


class TestTaggedResource:
    def test_provider_and_name_are_enforced_into_tags(self, source):
        _ds = source.dataset("alpha")
        assert _ds.tags["provider"] == SourceProvider.TUSHARE
        assert _ds.tags["name"] == "alpha"

    def test_enforced_tags_override_inherited_ones(self, source):
        source.tags["provider"] = "other"
        source.tags["name"] = "other"
        source.tags["env"] = "test"
        _ds = source.dataset("alpha")
        assert _ds.tags["provider"] == SourceProvider.TUSHARE
        assert _ds.tags["name"] == "alpha"
        assert _ds.tags["env"] == "test"


class TestAbstractness:
    def test_base_dataset_class_is_abstract(self):
        assert FakeDataset.__mro__[1].__abstractmethods__ == {"extract", "transform", "write"}
