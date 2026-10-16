from __future__ import annotations

import inspect
import json
import os
import sys
import traceback
from importlib import import_module
from typing import Any, Callable


def ensure_serializable(value: Any) -> Any:
    """
    Ensure the value is JSON serializable by performing a round trip.
    """
    try:
        _content: str = json.dumps(value)
        return json.loads(_content)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Value must be JSON serializable: {e}") from e


def resolve_entrypoint(entrypoint: str) -> Callable[..., Any]:
    """
    Resolve the entrypoint string to a callable and validate its signature.
    """
    _module, _sep, _name = entrypoint.partition(":")
    if not (_module and _sep and _name):
        raise ValueError(f"Entrypoint '{entrypoint}' must be `package.module:function`")
    _func: Any = getattr(import_module(_module), _name)
    if not callable(_func):
        raise TypeError(f"Entrypoint '{entrypoint}' is not callable")
    try:
        inspect.signature(_func).bind(payload={})
    except TypeError as e:
        raise TypeError(f"Entrypoint '{entrypoint}' must accept `payload`: {e}") from e
    return _func


def invoke(
    entrypoint: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Invoke the entrypoint with the payload and return its JSON serializable result."""
    _callable: Callable[..., Any] = resolve_entrypoint(entrypoint)
    _result: Any = _callable(payload=payload)
    if not isinstance(_result, dict):
        _type_name: str = type(_result).__name__
        raise TypeError(f"Entrypoint '{entrypoint}' must return a dict, got {_type_name}")
    return ensure_serializable(_result)


def main(argv: list[str]) -> int:
    """Subprocess entry: run `<entrypoint> <payload_path> <result_path>` and write the outcome JSON."""
    _ep, _payload_path, _res_path = argv
    try:
        with open(_payload_path, encoding="utf-8") as _f:
            _payload: dict[str, Any] = json.load(_f)

        _outcome: dict[str, Any] = {
            "ok": True,
            "result": invoke(_ep, _payload),
        }
    except BaseException as e:
        _msg: str = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        _outcome = {
            "ok": False,
            "error": _msg,
        }

    # write then rename so the parent never reads a partial file
    _tmp_path: str = f"{_res_path}.tmp"
    with open(_tmp_path, "w", encoding="utf-8") as _f:
        json.dump(_outcome, _f, ensure_ascii=False)

    os.replace(_tmp_path, _res_path)
    return 0 if _outcome["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
