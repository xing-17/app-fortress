from __future__ import annotations

import math
import statistics
import time
from datetime import datetime, tzinfo
from typing import Any

from app.service.webhost.service import shape

# Windows the machine page offers, the node keeps `retention_hours` (12) of snapshots
HOURS = (1, 3, 6, 12)
DEFAULT_HOURS = 6

_WIDTH = 1000
_HEIGHT = 240
_TICKS = 4
_FIT_PAD = 0.25
_LONG_WINDOW_SECONDS = 20 * 3600

# id, title, size, unit, zero based, upper limit, smallest span, lines of (label, class, source)
# source is ("raw", key) for a gauge or ("rate", key) for a counter since boot read as a rate
_CHARTS: tuple[tuple[Any, ...], ...] = (
    (
        "cpu",
        "CPU",
        "large",
        "%",
        True,
        100.0,
        10.0,
        (("machine", "s0", ("raw", "cpu_percent")),),
    ),
    (
        "mem",
        "Memory",
        "large",
        "%",
        False,
        100.0,
        4.0,
        (("machine", "s0", ("raw", "mem_percent")),),
    ),
    (
        "proc_cpu",
        "Process CPU",
        "small",
        "% of a core",
        True,
        None,
        10.0,
        (("process", "s0", ("raw", "proc_cpu_percent")),),
    ),
    (
        "proc_mem",
        "Process memory",
        "small",
        "MB",
        True,
        None,
        16.0,
        (("process", "s0", ("raw", "proc_mem_mb")),),
    ),
    (
        "net",
        "Network",
        "small",
        "MB/min",
        True,
        None,
        1.0,
        (("received", "s0", ("rate", "net_recv_mb")), ("sent", "s1", ("rate", "net_sent_mb"))),
    ),
    (
        "disk",
        "Disk",
        "small",
        "%",
        False,
        100.0,
        4.0,
        (("root", "s0", ("raw", "disk_percent")),),
    ),
)


def _number(snapshot: dict[str, Any], key: str) -> float | None:
    _value = snapshot.get(key)
    if isinstance(_value, bool) or not isinstance(_value, (int, float)):
        return None
    return float(_value)


def _gauge(snapshots: list[dict[str, Any]], key: str) -> list[float | None]:
    return [_number(_s, key) for _s in snapshots]


def _rate(snapshots: list[dict[str, Any]], key: str) -> list[float | None]:
    """Per minute change of a counter, None where it is unknown or went back (a reboot)"""
    _res: list[float | None] = [None]
    for _prev, _cur in zip(snapshots, snapshots[1:]):
        _a, _b = _number(_prev, key), _number(_cur, key)
        _span: float = float(_cur["timestamp"]) - float(_prev["timestamp"])
        if _a is None or _b is None or _b < _a or _span <= 0:
            _res.append(None)
        else:
            _res.append((_b - _a) / _span * 60)
    return _res


def _nice_step(raw: float) -> float:
    if raw <= 0:
        return 1.0
    _base: float = 10 ** math.floor(math.log10(raw))
    for _m in (1, 2, 2.5, 5, 10):
        if raw <= _m * _base:
            return _m * _base
    return 10 * _base


def axis(
    values: list[float],
    zero: bool,
    limit: float | None,
    minimum: float,
) -> tuple[float, float]:
    """
    The lower and upper end of a chart

    A zero based axis shows the level, a fitted one zooms into the range the values moved in so a
    slow change is not drawn as a flat line.
    """
    if not values:
        return 0.0, limit if limit is not None else minimum
    _lo, _hi = min(values), max(values)
    if zero:
        _lo, _hi = 0.0, max(_hi * 1.1, minimum)
    else:
        _pad: float = max(_hi - _lo, minimum) * _FIT_PAD
        _lo, _hi = max(_lo - _pad, 0.0), _hi + _pad
    _step: float = _nice_step((_hi - _lo) / _TICKS)
    _lo = 0.0 if zero else math.floor(_lo / _step) * _step
    _hi = math.ceil(_hi / _step) * _step
    if limit is not None:
        _hi = min(_hi, limit)
    if _hi <= _lo:
        _hi = _lo + _step
    return _lo, _hi


def _text(value: float | None) -> str:
    if value is None:
        return "-"
    if abs(value) >= 100:
        return f"{value:.0f}"
    if abs(value) >= 10:
        return f"{value:.1f}".rstrip("0").rstrip(".")
    return f"{value:.2f}".rstrip("0").rstrip(".") or "0"


def _paths(
    fractions: list[float],
    values: list[float | None],
    lo: float,
    hi: float,
) -> tuple[list[str], list[str]]:
    """SVG points of the line and of the area under it, one entry per unbroken run of readings"""
    _runs: list[list[tuple[float, float]]] = []
    _run: list[tuple[float, float]] = []
    for _f, _v in zip(fractions, values):
        if _v is None:
            if _run:
                _runs.append(_run)
                _run = []
            continue
        _y: float = _HEIGHT - (min(max(_v, lo), hi) - lo) / (hi - lo) * _HEIGHT
        _run.append((_f * _WIDTH, _y))
    if _run:
        _runs.append(_run)

    _lines: list[str] = []
    _areas: list[str] = []
    for _r in _runs:
        if len(_r) < 2:
            continue
        _pts: str = " ".join(f"{_x:.1f},{_y:.1f}" for _x, _y in _r)
        _lines.append(_pts)
        _areas.append(f"{_pts} {_r[-1][0]:.1f},{_HEIGHT} {_r[0][0]:.1f},{_HEIGHT}")
    return _lines, _areas


def _time_ticks(first: float, last: float, zone: tzinfo) -> list[dict[str, Any]]:
    _fmt: str = "%m-%d %H:%M" if last - first >= _LONG_WINDOW_SECONDS else "%H:%M"
    _res: list[dict[str, Any]] = []
    for _i in range(_TICKS + 1):
        _f: float = _i / _TICKS
        _res.append(
            {
                "text": datetime.fromtimestamp(first + (last - first) * _f, tz=zone).strftime(_fmt),
                "left": _f * 100,
            }
        )
    return _res


def _chart(
    spec: tuple[Any, ...],
    snapshots: list[dict[str, Any]],
    fractions: list[float],
    times: list[dict[str, Any]],
) -> dict[str, Any] | None:
    _id, _title, _size, _unit, _zero, _limit, _minimum, _lines = spec
    _columns: list[tuple[str, str, list[float | None]]] = []
    for _label, _cls, (_mode, _key) in _lines:
        _values = _rate(snapshots, _key) if _mode == "rate" else _gauge(snapshots, _key)
        if any(_v is not None for _v in _values):
            _columns.append((_label, _cls, _values))
    if not _columns:
        return None

    _all: list[float] = [_v for _, _, _vs in _columns for _v in _vs if _v is not None]
    _lo, _hi = axis(_all, _zero, _limit, _minimum)

    _drawn: list[dict[str, Any]] = []
    for _label, _cls, _values in _columns:
        _data: list[float] = [_v for _v in _values if _v is not None]
        _lines_pts, _areas = _paths(fractions, _values, _lo, _hi)
        _drawn.append(
            {
                "label": _label,
                "cls": _cls,
                "lines": _lines_pts,
                "areas": _areas,
                "last": _text(_data[-1]),
                "min": _text(min(_data)),
                "avg": _text(statistics.fmean(_data)),
                "max": _text(max(_data)),
                "values": [None if _v is None else round(_v, 2) for _v in _values],
            }
        )

    _ticks: list[dict[str, Any]] = []
    for _i in range(_TICKS + 1):
        _share: float = _i / _TICKS
        _ticks.append(
            {"text": _text(_lo + (_hi - _lo) * _share), "top": (1 - _share) * 100, "y": (1 - _share) * _HEIGHT}
        )
    return {
        "id": _id,
        "title": _title,
        "size": _size,
        "unit": _unit,
        "series": _drawn,
        "ticks": _ticks,
        "times": times,
    }


def _tiles(last: dict[str, Any], cpu: list[float | None]) -> list[dict[str, Any]]:
    _cpu_data: list[float] = [_v for _v in cpu if _v is not None]
    _tiles: list[dict[str, Any]] = []

    def _add(label: str, value: str, detail: str = "", pct: float | None = None) -> None:
        _tiles.append({"label": label, "value": value, "detail": detail, "pct": pct})

    _cpu_now = _number(last, "cpu_percent")
    if _cpu_now is not None:
        _detail: str = f"avg {_text(statistics.fmean(_cpu_data))}% · peak {_text(max(_cpu_data))}%" if _cpu_data else ""
        _add("cpu", f"{_cpu_now:.0f}%", _detail, _cpu_now)

    _mem = _number(last, "mem_percent")
    if _mem is not None:
        _add(
            "memory",
            f"{_mem:.0f}%",
            f"{shape.human_mb(last.get('mem_used_mb'))} / {shape.human_mb(last.get('mem_total_mb'))}",
            _mem,
        )

    _swap = _number(last, "swap_percent")
    if _swap is not None:
        _add("swap", f"{_swap:.0f}%", "", _swap)

    _disk = _number(last, "disk_percent")
    if _disk is not None:
        _add(
            "disk /",
            f"{_disk:.0f}%",
            f"{shape.human_mb(last.get('disk_used_mb'))} / {shape.human_mb(last.get('disk_total_mb'))}",
            _disk,
        )

    _proc_mem = _number(last, "proc_mem_mb")
    if _proc_mem is not None:
        _share = _number(last, "proc_mem_percent")
        _add(
            "process memory",
            shape.human_mb(_proc_mem),
            f"{_text(_share)}% of the machine" if _share is not None else "",
        )

    _proc_cpu = _number(last, "proc_cpu_percent")
    if _proc_cpu is not None:
        _add("process cpu", f"{_text(_proc_cpu)}%", "100% is one full core")

    _threads = _number(last, "proc_workers")
    if _threads is not None:
        _add("threads", f"{_threads:.0f}")

    _sent, _recv = _number(last, "net_sent_mb"), _number(last, "net_recv_mb")
    if _sent is not None and _recv is not None:
        _add("network since boot", f"{shape.human_mb(_recv)} in", f"{shape.human_mb(_sent)} out")
    return _tiles


def machine_view(
    snapshots: list[dict[str, Any]],
    zone: tzinfo,
    now: float | None = None,
) -> dict[str, Any] | None:
    """Machine snapshots shaped for the page, None when there is nothing to show"""
    _snaps: list[dict[str, Any]] = [_s for _s in snapshots if _number(_s, "timestamp") is not None]
    if not _snaps:
        return None
    _stamps: list[float] = [float(_s["timestamp"]) for _s in _snaps]
    _first, _last_at = _stamps[0], _stamps[-1]
    _span: float = _last_at - _first
    _fractions: list[float] = [(_t - _first) / _span if _span > 0 else 0.0 for _t in _stamps]
    _times: list[dict[str, Any]] = _time_ticks(_first, _last_at, zone)

    _charts: list[dict[str, Any]] = []
    if len(_snaps) >= 2:
        for _spec in _CHARTS:
            _c = _chart(_spec, _snaps, _fractions, _times)
            if _c is not None:
                _charts.append(_c)

    _gaps: list[float] = [_b - _a for _a, _b in zip(_stamps, _stamps[1:])]
    _now: float = time.time() if now is None else now
    _data: dict[str, Any] = {
        "t": [round(_f, 5) for _f in _fractions],
        "labels": [shape.local_text(_t, zone) for _t in _stamps],
        "charts": {
            _c["id"]: {
                "unit": _c["unit"],
                "series": [{k: s[k] for k in ("label", "cls", "values")} for s in _c["series"]],
            }
            for _c in _charts
        },
    }
    return {
        "tiles": _tiles(_snaps[-1], _gauge(_snaps, "cpu_percent")),
        "charts": _charts,
        "large": [_c for _c in _charts if _c["size"] == "large"],
        "small": [_c for _c in _charts if _c["size"] != "large"],
        "data": _data,
        "info": [
            ("samples", str(len(_snaps))),
            ("every", shape.human_duration(statistics.median(_gaps)) if _gaps else "-"),
            ("window", shape.human_duration(_span)),
            ("last sample", f"{shape.human_duration(max(_now - _last_at, 0))} ago"),
        ],
    }
