from __future__ import annotations

from zoneinfo import ZoneInfo

import pytest

from app.service.webhost.service import machine

from .conftest import HTML

_ZONE = ZoneInfo("UTC")


def _snap(i, **extra):
    return {
        "timestamp": 1_700_000_000.0 + i * 60,
        "cpu_percent": 10.0 + i,
        "mem_percent": 40.0 + i * 0.5,
        "mem_used_mb": 4096,
        "mem_total_mb": 16384,
        "swap_percent": 0.0,
        "disk_percent": 50.0,
        "disk_used_mb": 100_000,
        "disk_total_mb": 200_000,
        **extra,
    }


class TestAxis:
    def test_zero_based_starts_at_zero_and_clears_the_peak(self):
        _lo, _hi = machine.axis([3.0, 12.0], zero=True, limit=100.0, minimum=10.0)
        assert _lo == 0.0
        assert _hi >= 12.0

    def test_fitted_axis_zooms_into_the_range(self):
        _lo, _hi = machine.axis([61.0, 63.0], zero=False, limit=100.0, minimum=4.0)
        assert _lo > 50.0
        assert _hi < 80.0
        assert _lo < 61.0 and _hi > 63.0

    def test_limit_caps_the_top(self):
        assert machine.axis([95.0, 99.0], zero=True, limit=100.0, minimum=10.0)[1] == 100.0

    def test_constant_values_still_give_a_span(self):
        _lo, _hi = machine.axis([5.0, 5.0], zero=False, limit=100.0, minimum=4.0)
        assert _hi > _lo

    def test_no_values(self):
        assert machine.axis([], zero=True, limit=None, minimum=1.0) == (0.0, 1.0)


class TestMachineView:
    def test_none_without_snapshots(self):
        assert machine.machine_view([], _ZONE) is None

    def test_single_snapshot_has_tiles_but_no_charts(self):
        _view = machine.machine_view([_snap(0)], _ZONE)
        assert _view["charts"] == []
        assert {t["label"] for t in _view["tiles"]} >= {"cpu", "memory", "swap", "disk /"}

    def test_cpu_and_memory_are_separate_large_charts(self):
        _view = machine.machine_view([_snap(i) for i in range(5)], _ZONE)
        assert [c["id"] for c in _view["large"]] == ["cpu", "mem"]
        assert all(len(c["series"]) == 1 for c in _view["large"])

    def test_charts_without_data_are_left_out(self):
        _ids = [c["id"] for c in machine.machine_view([_snap(i) for i in range(5)], _ZONE)["charts"]]
        assert "proc_mem" not in _ids
        assert "net" not in _ids
        assert "disk" in _ids

    def test_process_and_network_show_when_reported(self):
        _snaps = [
            _snap(
                i,
                proc_mem_mb=300 + i,
                proc_cpu_percent=5.0,
                proc_workers=8,
                net_sent_mb=100 + i,
                net_recv_mb=200 + 3 * i,
            )
            for i in range(5)
        ]
        _view = machine.machine_view(_snaps, _ZONE)
        _by = {c["id"]: c for c in _view["charts"]}
        assert {"proc_mem", "proc_cpu", "net"} <= set(_by)
        _recv = next(s for s in _by["net"]["series"] if s["label"] == "received")
        assert _recv["values"][0] is None
        assert _recv["values"][1] == pytest.approx(3.0)

    def test_counter_going_back_is_a_gap_not_a_negative_rate(self):
        _snaps = [_snap(i, net_sent_mb=v, net_recv_mb=v) for i, v in enumerate([10, 20, 5, 15])]
        _net = next(c for c in machine.machine_view(_snaps, _ZONE)["charts"] if c["id"] == "net")
        _sent = next(s for s in _net["series"] if s["label"] == "sent")
        assert _sent["values"][2] is None
        assert all(v is None or v >= 0 for v in _sent["values"])

    def test_gap_splits_the_line(self):
        _snaps = [_snap(i) for i in range(6)]
        _snaps[3] = {k: v for k, v in _snaps[3].items() if k != "cpu_percent"}
        _cpu = machine.machine_view(_snaps, _ZONE)["large"][0]["series"][0]
        assert len(_cpu["lines"]) == 2

    def test_data_aligns_with_the_snapshots(self):
        _view = machine.machine_view([_snap(i) for i in range(5)], _ZONE)
        assert len(_view["data"]["t"]) == len(_view["data"]["labels"]) == 5
        assert _view["data"]["t"][0] == 0 and _view["data"]["t"][-1] == 1
        assert len(_view["data"]["charts"]["cpu"]["series"][0]["values"]) == 5

    def test_stats_and_ticks(self):
        _cpu = machine.machine_view([_snap(i) for i in range(5)], _ZONE)["large"][0]
        _s = _cpu["series"][0]
        assert (_s["last"], _s["min"], _s["max"]) == ("14", "10", "14")
        assert len(_cpu["ticks"]) == 5
        assert len(_cpu["times"]) == 5

    def test_info_reports_sampling(self):
        _view = machine.machine_view([_snap(i) for i in range(5)], _ZONE, now=1_700_000_000.0 + 4 * 60 + 30)
        _info = dict(_view["info"])
        assert _info["samples"] == "5"
        assert _info["every"] == "1m 0s"
        assert _info["last sample"] == "30s ago"


class TestMachinePage:
    def test_has_separate_charts(self, signed_in):
        _res = signed_in.get("/n/centre/machine", headers=HTML)
        assert _res.status_code == 200
        assert 'data-chart="cpu"' in _res.text
        assert 'data-chart="mem"' in _res.text
        assert "4.0 GB / 16.0 GB" in _res.text
        assert 'id="machine-data"' in _res.text

    def test_hours_selects_the_window(self, signed_in, fake):
        signed_in.get("/n/centre/machine?hours=12", headers=HTML)
        assert ("list_machine_snapshots", (12,)) in fake.calls

    @pytest.mark.parametrize("hours", ["x", "7", "-1", "0"])
    def test_bad_hours_fall_back_to_the_default(self, signed_in, fake, hours):
        assert signed_in.get(f"/n/centre/machine?hours={hours}", headers=HTML).status_code == 200
        assert ("list_machine_snapshots", (machine.DEFAULT_HOURS,)) in fake.calls

    def test_no_snapshots(self, signed_in, fake):
        fake.snapshots = []
        _res = signed_in.get("/n/centre/machine", headers=HTML)
        assert _res.status_code == 200
        assert "no machine data" in _res.text

    def test_not_running(self, signed_in, fake):
        fake.node_health = {"state": "stopped", "is_running": False}
        assert "not running" in signed_in.get("/n/centre/machine", headers=HTML).text

    def test_unknown_node_is_404(self, signed_in):
        assert signed_in.get("/n/nope/machine", headers=HTML).status_code == 404

    def test_sidebar_marks_machine(self, signed_in):
        assert 'class="item on" href="/n/centre/machine"' in signed_in.get("/n/centre/machine", headers=HTML).text

    def test_requires_login(self, web):
        assert web.get("/n/centre/machine", headers=HTML).status_code in (302, 303, 401)
