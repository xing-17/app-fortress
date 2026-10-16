from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from app.resource.compute.pyentrypoint import runner


def _run_main(tmp_path: Path, entrypoint: str, payload: Any = None, raw_payload: str | None = None):
    _payload_path: Path = tmp_path / "payload.json"
    _result_path: Path = tmp_path / "result.json"
    if raw_payload is not None:
        _payload_path.write_text(raw_payload, encoding="utf-8")
    elif payload is not None:
        _payload_path.write_text(json.dumps(payload), encoding="utf-8")
    _code: int = runner.main([entrypoint, str(_payload_path), str(_result_path)])
    _outcome: dict[str, Any] = json.loads(_result_path.read_text(encoding="utf-8"))
    return _code, _outcome


class TestEnsureSerializable:
    def test_plain_value_round_trips(self):
        assert runner.ensure_serializable({"a": [1, 2.5, "x", None, True]}) == {"a": [1, 2.5, "x", None, True]}

    def test_tuple_becomes_list(self):
        assert runner.ensure_serializable({"a": (1, 2)}) == {"a": [1, 2]}

    def test_non_string_keys_become_strings(self):
        assert runner.ensure_serializable({1: "a"}) == {"1": "a"}

    def test_returns_a_copy(self):
        _src: dict[str, Any] = {"a": [1]}
        _out: dict[str, Any] = runner.ensure_serializable(_src)
        _out["a"].append(2)
        assert _src == {"a": [1]}

    @pytest.mark.parametrize("value", [{1, 2}, object(), b"bytes", lambda: 1])
    def test_non_serializable_raises_value_error(self, value):
        with pytest.raises(ValueError, match="JSON serializable"):
            runner.ensure_serializable({"x": value})

    def test_circular_reference_raises_value_error(self):
        _loop: dict[str, Any] = {}
        _loop["self"] = _loop
        with pytest.raises(ValueError, match="JSON serializable"):
            runner.ensure_serializable(_loop)

    def test_unicode_survives(self):
        assert runner.ensure_serializable({"k": "中文😀"}) == {"k": "中文😀"}


class TestResolveEntrypoint:
    @pytest.mark.parametrize("entrypoint", ["", "fx_entries", "fx_entries:", ":echo", ":", "fx_entries.echo"])
    def test_malformed_entrypoint_raises_value_error(self, entrypoint):
        with pytest.raises(ValueError, match="package.module:function"):
            runner.resolve_entrypoint(entrypoint)

    def test_resolves_function(self):
        _func = runner.resolve_entrypoint("fx_entries:echo")
        assert _func(payload={"a": 1}) == {"echo": {"a": 1}}

    def test_missing_module_raises_module_not_found(self):
        with pytest.raises(ModuleNotFoundError):
            runner.resolve_entrypoint("no_such_module_xyz:echo")

    def test_missing_attribute_raises_attribute_error(self):
        with pytest.raises(AttributeError):
            runner.resolve_entrypoint("fx_entries:no_such_function")

    def test_extra_colon_is_part_of_the_name(self):
        with pytest.raises(AttributeError):
            runner.resolve_entrypoint("fx_entries:echo:more")

    def test_non_callable_raises_type_error(self):
        with pytest.raises(TypeError, match="not callable"):
            runner.resolve_entrypoint("fx_entries:not_callable")

    @pytest.mark.parametrize("name", ["echo_kwargs", "with_default"])
    def test_accepts_payload_keyword(self, name):
        assert callable(runner.resolve_entrypoint(f"fx_entries:{name}"))

    @pytest.mark.parametrize("name", ["positional_only", "wrong_signature", "needs_extra"])
    def test_signature_without_payload_raises_type_error(self, name):
        with pytest.raises(TypeError, match="must accept `payload`"):
            runner.resolve_entrypoint(f"fx_entries:{name}")


class TestInvoke:
    def test_passes_payload_by_keyword(self):
        assert runner.invoke("fx_entries:echo", {"a": 1}) == {"echo": {"a": 1}}

    def test_result_is_json_round_tripped(self):
        assert runner.invoke("fx_entries:with_default", {"a": 1}) == {"extra": 1, "payload": {"a": 1}}

    @pytest.mark.parametrize("name, type_name", [("returns_list", "list"), ("returns_none", "NoneType")])
    def test_non_dict_result_raises_type_error(self, name, type_name):
        with pytest.raises(TypeError, match=f"must return a dict, got {type_name}"):
            runner.invoke(f"fx_entries:{name}", {})

    def test_non_serializable_result_raises_value_error(self):
        with pytest.raises(ValueError, match="JSON serializable"):
            runner.invoke("fx_entries:returns_set", {})

    def test_entrypoint_exception_propagates(self):
        with pytest.raises(ValueError, match="bad input"):
            runner.invoke("fx_entries:raises", {})

    def test_invalid_entrypoint_propagates(self):
        with pytest.raises(ValueError, match="package.module:function"):
            runner.invoke("nocolon", {})


class TestMain:
    def test_success_writes_result_and_returns_zero(self, tmp_path):
        _code, _outcome = _run_main(tmp_path, "fx_entries:echo", {"a": 1})
        assert _code == 0
        assert _outcome == {"ok": True, "result": {"echo": {"a": 1}}}

    def test_entrypoint_exception_is_reported_with_traceback(self, tmp_path):
        _code, _outcome = _run_main(tmp_path, "fx_entries:raises", {})
        assert _code == 1
        assert _outcome["ok"] is False
        assert _outcome["error"].startswith("ValueError: bad input")
        assert "Traceback" in _outcome["error"]

    def test_system_exit_is_reported_as_failure(self, tmp_path):
        _code, _outcome = _run_main(tmp_path, "fx_entries:exit_system", {})
        assert _code == 1
        assert _outcome["error"].startswith("SystemExit: 3")

    def test_keyboard_interrupt_is_reported_as_failure(self, tmp_path, monkeypatch):
        def _interrupt(entrypoint, payload):
            raise KeyboardInterrupt()

        monkeypatch.setattr(runner, "invoke", _interrupt)
        _code, _outcome = _run_main(tmp_path, "fx_entries:echo", {})
        assert _code == 1
        assert _outcome["error"].startswith("KeyboardInterrupt")

    def test_non_dict_result_is_reported(self, tmp_path):
        _code, _outcome = _run_main(tmp_path, "fx_entries:returns_list", {})
        assert _code == 1
        assert "must return a dict" in _outcome["error"]

    def test_non_serializable_result_is_reported(self, tmp_path):
        _code, _outcome = _run_main(tmp_path, "fx_entries:returns_set", {})
        assert _code == 1
        assert "JSON serializable" in _outcome["error"]

    def test_bad_entrypoint_is_reported(self, tmp_path):
        _code, _outcome = _run_main(tmp_path, "no_such_module_xyz:echo", {})
        assert _code == 1
        assert "ModuleNotFoundError" in _outcome["error"]

    def test_missing_payload_file_is_reported(self, tmp_path):
        _code, _outcome = _run_main(tmp_path, "fx_entries:echo")
        assert _code == 1
        assert "FileNotFoundError" in _outcome["error"]

    def test_invalid_payload_json_is_reported(self, tmp_path):
        _code, _outcome = _run_main(tmp_path, "fx_entries:echo", raw_payload="{not json")
        assert _code == 1
        assert "JSONDecodeError" in _outcome["error"]

    def test_unicode_is_written_unescaped(self, tmp_path):
        _run_main(tmp_path, "fx_entries:echo", {"k": "中文"})
        assert "中文" in (tmp_path / "result.json").read_text(encoding="utf-8")

    def test_no_temp_file_is_left_behind(self, tmp_path):
        _run_main(tmp_path, "fx_entries:echo", {})
        assert sorted(_p.name for _p in tmp_path.iterdir()) == ["payload.json", "result.json"]

    def test_existing_result_file_is_replaced(self, tmp_path):
        (tmp_path / "result.json").write_text("stale", encoding="utf-8")
        _code, _outcome = _run_main(tmp_path, "fx_entries:echo", {})
        assert _code == 0
        assert _outcome["ok"] is True

    def test_unwritable_result_path_raises(self, tmp_path):
        (tmp_path / "payload.json").write_text("{}", encoding="utf-8")
        _missing: Path = tmp_path / "missing_dir" / "result.json"
        with pytest.raises(OSError):
            runner.main(["fx_entries:echo", str(tmp_path / "payload.json"), str(_missing)])

    @pytest.mark.parametrize("argv", [[], ["a"], ["a", "b"], ["a", "b", "c", "d"]])
    def test_wrong_argument_count_raises_value_error(self, argv):
        with pytest.raises(ValueError):
            runner.main(argv)


class TestScriptEntry:
    """Run `runner.py` as a script the way the parent does."""

    @staticmethod
    def _spawn(tmp_path: Path, entrypoint: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        (tmp_path / "payload.json").write_text(json.dumps(payload), encoding="utf-8")
        _proc = subprocess.run(
            [
                sys.executable,
                "-P",
                runner.__file__,
                entrypoint,
                str(tmp_path / "payload.json"),
                str(tmp_path / "result.json"),
            ],
            env={"PYTHONPATH": str(Path(__file__).parent / "_entries")},
            capture_output=True,
            timeout=60,
            check=False,
        )
        _outcome = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
        return _proc.returncode, _outcome

    def test_exit_code_zero_on_success(self, tmp_path):
        _code, _outcome = self._spawn(tmp_path, "fx_entries:echo", {"a": 1})
        assert _code == 0
        assert _outcome["result"] == {"echo": {"a": 1}}

    def test_exit_code_one_on_failure(self, tmp_path):
        _code, _outcome = self._spawn(tmp_path, "fx_entries:raises", {})
        assert _code == 1
        assert _outcome["ok"] is False

    def test_wrong_arguments_exit_non_zero(self, tmp_path):
        _proc = subprocess.run(
            [sys.executable, "-P", runner.__file__],
            capture_output=True,
            timeout=60,
            check=False,
        )
        assert _proc.returncode != 0
