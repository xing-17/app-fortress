"""Entrypoints for the pyentrypoint tests, stdlib only so a child process imports it fast."""

from __future__ import annotations

import os
import signal
import sys
import time
from importlib import import_module
from typing import Any

not_callable = 42


def echo(payload: dict[str, Any]) -> dict[str, Any]:
    return {"echo": payload}


def echo_kwargs(**kwargs: Any) -> dict[str, Any]:
    return {"echo": kwargs["payload"]}


def with_default(payload: dict[str, Any], extra: int = 1) -> dict[str, Any]:
    return {"extra": extra, "payload": payload}


def whoami(payload: dict[str, Any]) -> dict[str, Any]:
    return {"pid": os.getpid()}


def pid_info(payload: dict[str, Any]) -> dict[str, Any]:
    _main = sys.modules["__main__"]
    return {
        "pid": os.getpid(),
        "main_file": getattr(_main, "__file__", None),
        "stdin": sys.stdin.read(),
        "sys_path": list(sys.path),
        "can_import_runner": _can_import("runner"),
    }


def read_env(payload: dict[str, Any]) -> dict[str, Any]:
    return {"value": os.environ.get(payload["key"])}


def raises(payload: dict[str, Any]) -> dict[str, Any]:
    raise ValueError("bad input")


def returns_list(payload: dict[str, Any]) -> list[int]:
    return [1, 2, 3]


def returns_none(payload: dict[str, Any]) -> None:
    return None


def returns_set(payload: dict[str, Any]) -> dict[str, Any]:
    return {"x": {1, 2}}


def big_result(payload: dict[str, Any]) -> dict[str, Any]:
    return {"data": "x" * payload["size"]}


def big_payload_len(payload: dict[str, Any]) -> dict[str, Any]:
    return {"length": len(payload["data"])}


def exit_system(payload: dict[str, Any]) -> dict[str, Any]:
    sys.exit(3)


def exit_hard(payload: dict[str, Any]) -> dict[str, Any]:
    sys.stderr.write("fatal: hard exit marker\n")
    sys.stderr.flush()
    os._exit(7)


def exit_hard_noisy(payload: dict[str, Any]) -> dict[str, Any]:
    sys.stderr.write("HEAD" + "e" * payload["size"] + "TAIL")
    sys.stderr.flush()
    os._exit(9)


def kill_self(payload: dict[str, Any]) -> dict[str, Any]:
    os.kill(os.getpid(), signal.SIGKILL)
    return {}


def wait_gate(payload: dict[str, Any]) -> dict[str, Any]:
    """Block until the gate file exists, so a test decides when the run may finish."""
    _gate: str = payload["gate"]
    _deadline: float = time.monotonic() + 60
    while not os.path.exists(_gate):
        if time.monotonic() > _deadline:
            raise TimeoutError("gate never opened")
        time.sleep(0.02)
    return {"gate": "opened", "n": payload.get("n")}


def ignore_sigterm(payload: dict[str, Any]) -> dict[str, Any]:
    """Ignore SIGTERM and signal readiness, only SIGKILL can stop it."""
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    with open(payload["ready"], "w", encoding="utf-8") as _f:
        _f.write("ready")
    time.sleep(60)
    return {}


def signal_ready_then_wait(payload: dict[str, Any]) -> dict[str, Any]:
    with open(payload["ready"], "w", encoding="utf-8") as _f:
        _f.write("ready")
    time.sleep(60)
    return {}


def _can_import(name: str) -> bool:
    try:
        import_module(name)
    except ImportError:
        return False
    return True


def positional_only(payload: dict[str, Any], /) -> dict[str, Any]:
    return {}


def wrong_signature(x: int) -> dict[str, Any]:
    return {}


def needs_extra(payload: dict[str, Any], extra: int) -> dict[str, Any]:
    return {}
