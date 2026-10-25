from __future__ import annotations

from datetime import datetime, tzinfo
from typing import Any

_MAX_POINTS = 120
_HIDDEN_FACTS = frozenset({"name", "dataset", "source", "description", "datasets", "items", "partitions"})

# Utilities for shaping and formatting data for display in the web console
# Provides:
# - series: Extracts a series of numeric values from a list of snapshots
# - sparkline: Generates SVG polyline points for a sparkline chart
# - human_size: Formats a size in bytes to a human-readable string
# - human_mb: Formats a size in megabytes to a human-readable string
# - human_duration: Formats a duration in seconds to a human-readable string
# - local_text: Formats epoch seconds in the display timezone
# - local_iso_text: Formats an ISO 8601 text (a log event time) in the display timezone
# - brief: Provides a brief representation of a dict or list
# - column_label: Generates a label for a column based on its metadata
# - human_count: Formats a numeric count with commas
# - quality_view: Shapes a quality report for display in the web console


def series(
    snapshots: list[dict[str, Any]],
    key: str,
) -> list[float]:
    _res: list[float] = []
    for _snap in snapshots:
        _value = _snap.get(key)
        if isinstance(_value, (int, float)):
            _res.append(float(_value))
    return _res


def sparkline(
    values: list[float],
    width: int = 120,
    height: int = 28,
    ceiling: float = 100.0,
) -> str:
    """The `points` of an SVG polyline, empty when there is nothing to draw"""
    if len(values) < 2:
        return ""
    if len(values) > _MAX_POINTS:
        _stride: int = -(-len(values) // _MAX_POINTS)
        _kept: list[float] = values[::_stride]

        # The newest reading is always the right end
        if (len(values) - 1) % _stride:
            _kept.append(values[-1])
        values = _kept
    _step: float = width / (len(values) - 1)
    _points: list[str] = []
    for _i, _v in enumerate(values):
        _clamped: float = min(max(_v, 0.0), ceiling)
        _y: float = height - (_clamped / ceiling) * height
        _points.append(f"{_i * _step:.1f},{_y:.1f}")
    return " ".join(_points)


def human_size(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return "-"
    _size: float = float(value)
    for _unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(_size) < 1024 or _unit == "TB":
            if _unit == "B":
                return f"{_size:.0f} {_unit}"
            else:
                return f"{_size:.1f} {_unit}"
        _size /= 1024
    return "-"


def human_mb(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return "-"
    return human_size(float(value) * 1024 * 1024)


def human_duration(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return "-"
    _seconds: int = int(value)
    if _seconds < 60:
        if _seconds < 10:
            return f"{float(value):.1f}s"
        else:
            return f"{_seconds}s"
    _minutes, _s = divmod(_seconds, 60)
    if _minutes < 60:
        return f"{_minutes}m {_s}s"
    _hours, _m = divmod(_minutes, 60)
    return f"{_hours}h {_m}m"


_TIME_FORMAT = "%Y-%m-%d %H:%M:%S %Z"


def local_text(
    value: Any,
    zone: tzinfo,
) -> str:
    """Epoch seconds as text in the display timezone"""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "-"
    try:
        return datetime.fromtimestamp(value, tz=zone).strftime(_TIME_FORMAT)
    except (OverflowError, OSError, ValueError):
        return "-"


def local_iso_text(
    value: Any,
    zone: tzinfo,
) -> Any:
    """ISO 8601 text in the display timezone, anything else is returned as it is"""
    if not isinstance(value, str):
        return value
    try:
        _dt: datetime = datetime.fromisoformat(value)
    except ValueError:
        return value
    if _dt.tzinfo is None:
        return value
    return _dt.astimezone(zone).strftime(_TIME_FORMAT)


def brief(value: Any) -> str:
    """A dict or list on one short line, for tables that do not know the shape"""
    if value is None:
        return "-"
    if isinstance(value, dict):
        _parts: list[str] = [f"{_k}={brief(_v)}" for _k, _v in value.items()]
        return " · ".join(_parts) if _parts else "-"
    if isinstance(value, (list, tuple)):
        return ", ".join(brief(_v) for _v in value) if value else "-"
    return str(value)


def column_label(value: Any) -> str:
    if isinstance(value, dict) and "name" in value:
        _type = value.get("type") or value.get("dtype")
        return f"{value['name']} {_type}" if _type else str(value["name"])
    return brief(value)


def human_count(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "-"
    return f"{int(value):,}"


def _int(value: Any) -> int:
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0


def _pct(rate: Any) -> float | None:
    return float(rate) * 100 if isinstance(rate, (int, float)) and not isinstance(rate, bool) else None


def quality_view(quality: Any) -> dict[str, Any] | None:
    """A stored quality report shaped for the page, None when the assetfile has no metadata"""
    if not isinstance(quality, dict):
        return None

    _height: int = _int(quality.get("height"))
    _duplicates: int = _int(quality.get("duplicate_rows"))
    _complete_rows: int = _int(quality.get("complete_rows"))
    _columns: list[dict[str, Any]] = []
    _all_null: int = 0
    _with_nulls: int = 0
    for _col in quality.get("columns") or []:
        if not isinstance(_col, dict):
            continue
        _nulls: int = _int(_col.get("null_count"))
        if _col.get("is_all_null"):
            _all_null += 1
        elif _nulls:
            _with_nulls += 1
        _flags: list[str] = [
            _label
            for _key, _label in (("is_all_null", "all null"), ("is_constant", "constant"), ("is_unique", "unique"))
            if _col.get(_key)
        ]
        _columns.append(
            {
                "name": str(_col.get("name", "")),
                "type": str(_col.get("type", "")),
                "complete": _pct(_col.get("complete_rate")),
                "null_count": _nulls,
                "unique_count": _int(_col.get("unique_count")),
                "duplicate_count": _int(_col.get("duplicate_count")),
                "flags": _flags,
            }
        )

    _issues: list[str] = []
    if _height == 0:
        _issues.append("empty")
    if _all_null:
        _issues.append(f"{_all_null} all-null column{'s' if _all_null > 1 else ''}")
    if _with_nulls:
        _issues.append(f"{_with_nulls} column{'s' if _with_nulls > 1 else ''} with nulls")
    if _duplicates:
        _issues.append(f"{_duplicates:,} duplicate row{'s' if _duplicates > 1 else ''}")

    _status: str = "ok"
    if _height == 0 or _all_null:
        _status = "bad"
    elif _issues:
        _status = "warn"

    return {
        "status": _status,
        "issues": _issues,
        "height": _height,
        "width": _int(quality.get("width")),
        "complete_rows": _complete_rows,
        "duplicate_rows": _duplicates,
        "complete": _complete_rows / _height * 100 if _height else None,
        "created_at": quality.get("created_at"),
        "columns": _columns,
    }


def facts(info: dict[str, Any]) -> list[tuple[str, str]]:
    """Scalar fields of an info dict as label/value pairs, so a field the node adds shows without a change here"""
    _res: list[tuple[str, str]] = []
    for _key, _value in info.items():
        if _key in _HIDDEN_FACTS or isinstance(_value, (dict, list, tuple)):
            continue
        if _value is None or _value == "" or _value == "None":
            continue
        _res.append((_key, str(_value)))
    return _res


def newest(
    items: list[dict[str, Any]],
    limit: int,
    key: Any,
) -> list[dict[str, Any]]:
    _sorted: list[dict[str, Any]] = sorted(items, key=key, reverse=True)
    return _sorted[:limit]
