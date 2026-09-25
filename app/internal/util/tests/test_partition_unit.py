from __future__ import annotations

from app.internal.util.partition import IPartition


class TestIPartitionResolve:
    def test_resolve_parses_key_value_segments(self):
        assert IPartition.resolve(["year=2024", "month=01"]) == {
            "year": "2024",
            "month": "01",
        }

    def test_resolve_strips_whitespace(self):
        assert IPartition.resolve([" year = 2024 "]) == {"year": "2024"}

    def test_resolve_skips_segments_without_equals(self):
        assert IPartition.resolve(["year=2024", "no_equals_here"]) == {
            "year": "2024",
        }

    def test_resolve_skips_segments_with_empty_key_or_value(self):
        assert IPartition.resolve(["=2024", "year=", "  =  "]) == {}

    def test_resolve_empty_list_returns_empty_dict(self):
        assert IPartition.resolve([]) == {}

    def test_resolve_splits_on_first_equals_only(self):
        assert IPartition.resolve(["expr=a=b=c"]) == {"expr": "a=b=c"}


class TestIPartitionToString:
    def test_to_string_joins_with_default_connector(self):
        assert IPartition.to_string({"year": "2024", "month": "01"}) == "year=2024/month=01"

    def test_to_string_joins_with_custom_connector(self):
        assert IPartition.to_string({"year": "2024", "month": "01"}, connector=",") == "year=2024,month=01"

    def test_to_string_empty_dict_returns_empty_string(self):
        assert IPartition.to_string({}) == ""

    def test_to_string_falls_back_to_slash_when_connector_empty(self):
        assert IPartition.to_string({"year": "2024"}, connector="") == "year=2024"
