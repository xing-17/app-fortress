from __future__ import annotations

from zoneinfo import ZoneInfo

import pytest

from app.service.webhost.service import shape

_SYDNEY = ZoneInfo("Australia/Sydney")


class TestLocalTime:
    def test_epoch_in_the_zone(self):
        assert shape.local_text(1_700_000_000, _SYDNEY) == "2023-11-15 09:13:20 AEDT"

    def test_utc_zone(self):
        assert shape.local_text(0, ZoneInfo("UTC")) == "1970-01-01 00:00:00 UTC"

    @pytest.mark.parametrize("value", [None, "x", True])
    def test_not_a_time(self, value):
        assert shape.local_text(value, _SYDNEY) == "-"

    def test_iso_in_the_zone(self):
        assert shape.local_iso_text("2026-01-01T00:00:00+0000", _SYDNEY) == "2026-01-01 11:00:00 AEDT"

    @pytest.mark.parametrize("value", [None, "garbage", "2026-01-01T00:00:00"])
    def test_iso_left_alone_when_not_an_aware_time(self, value):
        assert shape.local_iso_text(value, _SYDNEY) == value


class TestSparkline:
    def test_needs_two_points(self):
        assert shape.sparkline([]) == ""
        assert shape.sparkline([5.0]) == ""

    def test_scales_to_the_box(self):
        assert shape.sparkline([0.0, 100.0], width=10, height=20) == "0.0,20.0 10.0,0.0"

    def test_clamps_out_of_range(self):
        assert shape.sparkline([-5.0, 500.0], width=10, height=20) == "0.0,20.0 10.0,0.0"

    def test_long_series_is_thinned_and_keeps_the_newest(self):
        _values = [float(i % 100) for i in range(1000)]
        _points = shape.sparkline(_values).split(" ")
        assert len(_points) <= 121
        assert _points[-1].startswith("120.0,")


class TestFormats:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [(0, "0 B"), (1023, "1023 B"), (2048, "2.0 KB"), (5 * 1024**3, "5.0 GB"), (None, "-"), ("x", "-")],
    )
    def test_size(self, value, expected):
        assert shape.human_size(value) == expected

    @pytest.mark.parametrize(
        ("value", "expected"),
        [(3.25, "3.2s"), (42, "42s"), (125, "2m 5s"), (7500, "2h 5m"), (None, "-")],
    )
    def test_duration(self, value, expected):
        assert shape.human_duration(value) == expected

    def test_count(self):
        assert shape.human_count(1234567) == "1,234,567"
        assert shape.human_count(None) == "-"
        assert shape.human_count(True) == "-"


class TestFacts:
    def test_keeps_scalars_and_hides_the_known_and_empty(self):
        _info = {
            "name": "src",
            "provider": "fake",
            "country": "None",
            "board": "",
            "vault": "local",
            "datasets": ["a"],
            "meta": {"k": 1},
            "retries": 3,
        }
        assert shape.facts(_info) == [("provider", "fake"), ("vault", "local"), ("retries", "3")]


class TestQualityView:
    def test_no_report(self):
        assert shape.quality_view(None) is None

    def test_empty_dataframe_is_a_problem(self):
        _view = shape.quality_view({"height": 0, "width": 0, "columns": []})
        assert _view["status"] == "bad"
        assert _view["issues"] == ["empty"]
        assert _view["complete"] is None

    def test_clean_report(self):
        _view = shape.quality_view(
            {
                "height": 10,
                "width": 1,
                "complete_rows": 10,
                "columns": [{"name": "a", "type": "INT", "complete_rate": 1.0}],
            }
        )
        assert _view["status"] == "ok"
        assert _view["issues"] == []
        assert _view["complete"] == 100.0
        assert _view["columns"][0]["complete"] == 100.0

    def test_nulls_and_duplicates_warn(self):
        _view = shape.quality_view(
            {
                "height": 10,
                "complete_rows": 8,
                "duplicate_rows": 1,
                "columns": [{"name": "a", "null_count": 2}, {"name": "b", "null_count": 1}],
            }
        )
        assert _view["status"] == "warn"
        assert _view["issues"] == ["2 columns with nulls", "1 duplicate row"]

    def test_flags_of_a_column(self):
        _view = shape.quality_view(
            {"height": 3, "columns": [{"name": "a", "is_all_null": True, "is_constant": True, "null_count": 3}]}
        )
        assert _view["status"] == "bad"
        assert _view["columns"][0]["flags"] == ["all null", "constant"]

    def test_garbage_is_tolerated(self):
        _view = shape.quality_view({"height": "x", "columns": ["nope", None]})
        assert _view["height"] == 0
        assert _view["columns"] == []
