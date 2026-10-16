from __future__ import annotations

import importlib
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.internal.constant.computeruntime import ComputeRuntime
from app.internal.constant.computestatus import ComputeStatus
from app.internal.constant.platform import Platform
from app.resource.compute._common._compute import BaseCompute
from app.resource.compute._common._run import ComputeRun
from app.resource.compute.pyentrypoint import compute as compute_module
from app.resource.compute.pyentrypoint import runner
from app.resource.compute.pyentrypoint.compute import PyEntrypointCompute, _Process
from app.resource.store.file.store import FileStore
from app.setting._compute import PyEntrypointComputeSetting
from app.setting._store import FileStoreSetting

_ENTRIES: Path = Path(__file__).parent / "_entries"
_WAIT_SECONDS: float = 60.0


def _make(
    tmp_path: Path,
    entrypoint: str = "fx_entries:echo",
    name: str = "demo",
    **kwargs: Any,
) -> PyEntrypointCompute:
    _store = FileStore(name="s", path=str(tmp_path / "store"))
    return PyEntrypointCompute(name=name, entrypoint=entrypoint, store=_store, **kwargs)


def _wait(compute: PyEntrypointCompute, run: ComputeRun | str) -> ComputeRun:
    _deadline: float = time.monotonic() + _WAIT_SECONDS
    while True:
        _run: ComputeRun = compute.refresh(run)
        if _run.is_finished:
            return _run
        assert time.monotonic() < _deadline, "run did not finish in time"
        time.sleep(0.05)


def _wait_file(path: Path) -> None:
    _deadline: float = time.monotonic() + _WAIT_SECONDS
    while not path.exists():
        assert time.monotonic() < _deadline, f"{path} never appeared"
        time.sleep(0.02)


def _open(path: Path) -> None:
    path.write_text("go", encoding="utf-8")


def _submit_gated(compute: PyEntrypointCompute, tmp_path: Path, name: str = "gate") -> tuple[ComputeRun, Path]:
    _gate: Path = tmp_path / name
    return compute.submit({"gate": str(_gate)}), _gate


def _process_of(compute: PyEntrypointCompute, run: ComputeRun) -> _Process:
    return compute._processes[run.external_id]


class TestConstruction:
    def test_class_variables(self):
        assert PyEntrypointCompute.runtime == ComputeRuntime.PYENTRYPOINT
        assert PyEntrypointCompute.platform == Platform.LOCAL

    def test_is_a_base_compute(self, tmp_path):
        assert isinstance(_make(tmp_path), BaseCompute)

    def test_entrypoint_is_required(self, tmp_path):
        with pytest.raises(ValidationError):
            PyEntrypointCompute(name="demo", store=FileStore(name="s", path=str(tmp_path)))  # type: ignore[call-arg]

    def test_invalid_name_is_rejected(self, tmp_path):
        with pytest.raises(ValidationError):
            _make(tmp_path, name="bad-name")

    def test_frn(self, tmp_path):
        _frn: str = _make(tmp_path, name="local_fetch").frn
        assert "platform=local" in _frn
        assert "runtime=pyentrypoint" in _frn
        assert "name=local_fetch" in _frn

    def test_construction_does_not_import_or_validate_the_entrypoint(self, tmp_path):
        assert _make(tmp_path, entrypoint="no_such_module_xyz:nope").entrypoint == "no_such_module_xyz:nope"

    def test_from_setting_defaults_max_run_records(self, tmp_path):
        _setting = PyEntrypointComputeSetting(
            name="c",
            entrypoint="fx_entries:echo",
            store=FileStoreSetting(name="s", path=str(tmp_path / "store")),
        )
        assert PyEntrypointCompute.from_setting(_setting).max_run_records == 200

    def test_new_instance_has_no_processes(self, tmp_path):
        assert _make(tmp_path)._processes == {}

    def test_instances_do_not_share_process_tables(self, tmp_path):
        _a = _make(tmp_path, name="a")
        _b = _make(tmp_path, name="b")
        assert _a._processes is not _b._processes
        assert _a._lock is not _b._lock

    def test_from_setting(self, tmp_path):
        _setting = PyEntrypointComputeSetting(
            name="from_setting",
            entrypoint="fx_entries:echo",
            description="desc",
            tags={"team": "data"},
            max_run_records=5,
            store=FileStoreSetting(name="s", path=str(tmp_path / "store")),
        )
        _compute = PyEntrypointCompute.from_setting(_setting)
        assert _compute.max_run_records == 5
        assert _compute.name == "from_setting"
        assert _compute.entrypoint == "fx_entries:echo"
        assert _compute.description == "desc"
        assert _compute.tags["team"] == "data"
        assert _compute.execute({"a": 1}).status == ComputeStatus.COMPLETED


class TestExecute:
    def test_success_is_recorded(self, tmp_path):
        _c = _make(tmp_path)
        _run = _c.execute({"a": 1})
        assert _run.status == ComputeStatus.COMPLETED
        assert _run.result == {"echo": {"a": 1}}
        assert _run.payload == {"a": 1}
        assert _c.lookup(_run.id).result == {"echo": {"a": 1}}

    def test_none_payload_is_an_empty_dict(self, tmp_path):
        assert _make(tmp_path).execute().result == {"echo": {}}

    def test_runs_in_the_current_process(self, tmp_path):
        _run = _make(tmp_path, entrypoint="fx_entries:whoami").execute()
        assert _run.result == {"pid": os.getpid()}

    def test_keyword_only_entrypoint(self, tmp_path):
        _run = _make(tmp_path, entrypoint="fx_entries:echo_kwargs").execute({"a": 1})
        assert _run.result == {"echo": {"a": 1}}

    def test_unicode_payload(self, tmp_path):
        assert _make(tmp_path).execute({"k": "中文😀"}).result == {"echo": {"k": "中文😀"}}

    def test_entrypoint_exception_is_recorded_not_raised(self, tmp_path):
        _c = _make(tmp_path, entrypoint="fx_entries:raises")
        _run = _c.execute()
        assert _run.status == ComputeStatus.FAILED
        assert _run.error == "ValueError: bad input"
        assert _c.lookup(_run.id).status == ComputeStatus.FAILED

    def test_entrypoint_exception_raised_on_request(self, tmp_path):
        with pytest.raises(ValueError, match="bad input"):
            _make(tmp_path, entrypoint="fx_entries:raises").execute(raise_on_error=True)

    @pytest.mark.parametrize(
        "entrypoint, error_type",
        [
            ("nocolon", "ValueError"),
            ("no_such_module_xyz:echo", "ModuleNotFoundError"),
            ("fx_entries:missing", "AttributeError"),
            ("fx_entries:not_callable", "TypeError"),
            ("fx_entries:wrong_signature", "TypeError"),
            ("fx_entries:returns_list", "TypeError"),
            ("fx_entries:returns_none", "TypeError"),
            ("fx_entries:returns_set", "ValueError"),
        ],
    )
    def test_bad_entrypoint_or_result_is_recorded_as_failure(self, tmp_path, entrypoint, error_type):
        _run = _make(tmp_path, entrypoint=entrypoint).execute()
        assert _run.status == ComputeStatus.FAILED
        assert _run.error.startswith(f"{error_type}:")

    @pytest.mark.parametrize("payload", [["x"], "x", 1])
    def test_non_dict_payload_is_rejected_before_a_run_is_recorded(self, tmp_path, payload):
        _c = _make(tmp_path)
        with pytest.raises(ValueError):
            _c.execute(payload)
        assert _c.list_runs() == []

    def test_non_serializable_payload_is_rejected_before_a_run_is_recorded(self, tmp_path):
        _c = _make(tmp_path)
        with pytest.raises(ValueError):
            _c.execute({"x": object()})
        assert _c.list_runs() == []

    def test_caller_payload_is_not_mutated_by_the_run(self, tmp_path):
        _payload: dict[str, Any] = {"a": [1]}
        _run = _make(tmp_path).execute(_payload)
        _run.payload["a"].append(2)
        assert _payload == {"a": [1]}


class TestSubmit:
    def test_run_is_started_and_persisted_with_the_pid(self, tmp_path):
        _c = _make(tmp_path, entrypoint="fx_entries:wait_gate")
        _run, _gate = _submit_gated(_c, tmp_path)
        _stored = _c.lookup(_run.id)
        assert _run.status == ComputeStatus.STARTED
        assert _run.external_id.isdigit()
        assert _stored.status == ComputeStatus.STARTED
        assert _stored.external_id == _run.external_id
        _open(_gate)
        _wait(_c, _run)

    def test_runs_to_completion(self, tmp_path):
        _c = _make(tmp_path)
        _run = _c.submit({"a": 1})
        _done = _wait(_c, _run)
        assert _done.status == ComputeStatus.COMPLETED
        assert _done.result == {"echo": {"a": 1}}
        assert _c.lookup(_run.id).result == {"echo": {"a": 1}}
        assert _c.lookup(_run.id).finished_at is not None

    def test_none_payload_is_an_empty_dict(self, tmp_path):
        _c = _make(tmp_path)
        assert _wait(_c, _c.submit()).result == {"echo": {}}

    def test_unicode_payload_and_result(self, tmp_path):
        _c = _make(tmp_path)
        _payload = {"k": "中文😀", "nested": {"a": [1, 2, {"b": None}]}}
        assert _wait(_c, _c.submit(_payload)).result == {"echo": _payload}

    def test_runs_in_a_fresh_interpreter(self, tmp_path):
        _c = _make(tmp_path, entrypoint="fx_entries:pid_info")
        _result = _wait(_c, _c.submit()).result
        assert _result["pid"] != os.getpid()
        assert _result["main_file"].endswith("runner.py")
        assert _result["stdin"] == ""

    def test_child_inherits_parent_import_path_without_the_runner_folder(self, tmp_path):
        _c = _make(tmp_path, entrypoint="fx_entries:pid_info")
        _result = _wait(_c, _c.submit()).result
        assert str(_ENTRIES) in _result["sys_path"]
        assert str(Path(runner.__file__).parent) not in _result["sys_path"]
        assert _result["can_import_runner"] is False

    def test_child_inherits_the_environment(self, tmp_path, monkeypatch):
        monkeypatch.setenv("FX_VAR", "hello")
        _c = _make(tmp_path, entrypoint="fx_entries:read_env")
        assert _wait(_c, _c.submit({"key": "FX_VAR"})).result == {"value": "hello"}

    def test_empty_sys_path_entry_resolves_to_the_current_directory(self, tmp_path, monkeypatch):
        (tmp_path / "fx_cwdmod.py").write_text(
            "import os\n\ndef run(payload):\n    return {'cwd': os.getcwd()}\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "path", ["", *sys.path])
        importlib.invalidate_caches()
        try:
            _c = _make(tmp_path, entrypoint="fx_cwdmod:run")
            _result = _wait(_c, _c.submit()).result
        finally:
            sys.modules.pop("fx_cwdmod", None)
        assert Path(_result["cwd"]).resolve() == tmp_path.resolve()

    def test_large_payload_does_not_block(self, tmp_path):
        _c = _make(tmp_path, entrypoint="fx_entries:big_payload_len")
        _size: int = 5_000_000
        assert _wait(_c, _c.submit({"data": "x" * _size})).result == {"length": _size}

    def test_large_result_does_not_block(self, tmp_path):
        _c = _make(tmp_path, entrypoint="fx_entries:big_result")
        _size: int = 8_000_000
        assert len(_wait(_c, _c.submit({"size": _size})).result["data"]) == _size

    def test_returns_before_the_entrypoint_finishes(self, tmp_path):
        _c = _make(tmp_path, entrypoint="fx_entries:wait_gate")
        _run, _gate = _submit_gated(_c, tmp_path)
        assert not _run.is_finished
        _open(_gate)
        _wait(_c, _run)

    def test_payload_is_not_mutated(self, tmp_path):
        _c = _make(tmp_path)
        _payload: dict[str, Any] = {"a": [1]}
        _wait(_c, _c.submit(_payload))
        assert _payload == {"a": [1]}

    def test_non_dict_payload_is_rejected_before_a_run_is_recorded(self, tmp_path, workdirs):
        _c = _make(tmp_path)
        with pytest.raises(ValueError):
            _c.submit(["x"])  # type: ignore[arg-type]
        assert _c.list_runs() == []
        assert workdirs() == []

    def test_non_serializable_payload_is_rejected_before_a_run_is_recorded(self, tmp_path, workdirs):
        _c = _make(tmp_path)
        with pytest.raises(ValueError):
            _c.submit({"x": object()})
        assert _c.list_runs() == []
        assert workdirs() == []

    @pytest.mark.parametrize(
        "entrypoint, error_type",
        [
            ("nocolon", ValueError),
            ("no_such_module_xyz:echo", ModuleNotFoundError),
            ("fx_entries:missing", AttributeError),
            ("fx_entries:not_callable", TypeError),
            ("fx_entries:wrong_signature", TypeError),
            ("fx_entries:positional_only", TypeError),
        ],
    )
    def test_bad_entrypoint_fails_at_submit_without_spawning(self, tmp_path, workdirs, entrypoint, error_type):
        _c = _make(tmp_path, entrypoint=entrypoint)
        _run = _c.submit()
        assert _run.status == ComputeStatus.FAILED
        assert _run.error.startswith(f"{error_type.__name__}:")
        assert _run.external_id is None
        assert _c.lookup(_run.id).status == ComputeStatus.FAILED
        assert _c._processes == {}
        assert compute_module._live_processes == set()
        assert workdirs() == []
        with pytest.raises(error_type):
            _c.submit(raise_on_error=True)
        assert workdirs() == []

    def test_spawn_failure_is_recorded_and_cleans_up(self, tmp_path, workdirs, monkeypatch):
        def _boom(*args, **kwargs):
            raise OSError("cannot spawn")

        monkeypatch.setattr(subprocess, "Popen", _boom)
        _c = _make(tmp_path)
        _run = _c.submit()
        assert _run.status == ComputeStatus.FAILED
        assert _run.error == "OSError: cannot spawn"
        assert workdirs() == []
        assert _c._processes == {}
        with pytest.raises(OSError):
            _c.submit(raise_on_error=True)
        assert workdirs() == []

    def test_each_submit_is_an_independent_run(self, tmp_path):
        _c = _make(tmp_path)
        _runs = [_c.submit({"n": _n}) for _n in range(3)]
        assert len({_r.id for _r in _runs}) == 3
        assert len({_r.external_id for _r in _runs}) == 3
        for _n, _r in enumerate(_runs):
            assert _wait(_c, _r).result == {"echo": {"n": _n}}
        assert len(_c.list_runs()) == 3


class TestFailureOutcomes:
    def test_entrypoint_exception_carries_the_traceback(self, tmp_path):
        _c = _make(tmp_path, entrypoint="fx_entries:raises")
        _done = _wait(_c, _c.submit())
        assert _done.status == ComputeStatus.FAILED
        assert _done.error.startswith("ValueError: bad input")
        assert "Traceback" in _done.error
        assert _c.lookup(_done.id).status == ComputeStatus.FAILED

    def test_system_exit_is_a_failure(self, tmp_path):
        _c = _make(tmp_path, entrypoint="fx_entries:exit_system")
        _done = _wait(_c, _c.submit())
        assert _done.status == ComputeStatus.FAILED
        assert _done.error.startswith("SystemExit: 3")

    @pytest.mark.parametrize(
        "entrypoint, message",
        [
            ("fx_entries:returns_list", "must return a dict"),
            ("fx_entries:returns_none", "must return a dict"),
            ("fx_entries:returns_set", "JSON serializable"),
        ],
    )
    def test_invalid_result_is_a_failure(self, tmp_path, entrypoint, message):
        _c = _make(tmp_path, entrypoint=entrypoint)
        _done = _wait(_c, _c.submit())
        assert _done.status == ComputeStatus.FAILED
        assert message in _done.error

    def test_hard_exit_reports_the_exit_code_and_stderr(self, tmp_path):
        _c = _make(tmp_path, entrypoint="fx_entries:exit_hard")
        _done = _wait(_c, _c.submit())
        assert _done.status == ComputeStatus.FAILED
        assert _done.error.startswith("Process exited with code 7:")
        assert "fatal: hard exit marker" in _done.error

    def test_killed_child_reports_the_signal(self, tmp_path):
        _c = _make(tmp_path, entrypoint="fx_entries:kill_self")
        _done = _wait(_c, _c.submit())
        assert _done.status == ComputeStatus.FAILED
        assert _done.error.startswith("Process exited with code -9")

    def test_stderr_is_cut_to_its_tail(self, tmp_path):
        _c = _make(tmp_path, entrypoint="fx_entries:exit_hard_noisy")
        _done = _wait(_c, _c.submit({"size": 10_000}))
        _prefix: str = "Process exited with code 9: "
        assert _done.error.startswith(_prefix)
        assert _done.error.endswith("TAIL")
        assert "HEAD" not in _done.error
        assert len(_done.error) == len(_prefix) + compute_module._STDERR_TAIL_CHARS

    def test_a_failed_run_does_not_affect_later_runs(self, tmp_path):
        _c = _make(tmp_path)
        _c.entrypoint = "fx_entries:raises"
        assert _wait(_c, _c.submit()).status == ComputeStatus.FAILED
        _c.entrypoint = "fx_entries:echo"
        assert _wait(_c, _c.submit({"a": 1})).status == ComputeStatus.COMPLETED


class TestRefresh:
    def test_running_process_stays_started(self, tmp_path):
        _c = _make(tmp_path, entrypoint="fx_entries:wait_gate")
        _run, _gate = _submit_gated(_c, tmp_path)
        for _ in range(3):
            assert _c.refresh(_run).status == ComputeStatus.STARTED
            assert _c.refresh(_run.id).status == ComputeStatus.STARTED
        assert _c.lookup(_run.id).status == ComputeStatus.STARTED
        _open(_gate)
        assert _wait(_c, _run).status == ComputeStatus.COMPLETED

    def test_refresh_by_id_and_by_object(self, tmp_path):
        _c = _make(tmp_path)
        _by_id = _wait(_c, _c.submit({"n": 1}).id)
        _by_obj = _wait(_c, _c.submit({"n": 2}))
        assert _by_id.result == {"echo": {"n": 1}}
        assert _by_obj.result == {"echo": {"n": 2}}

    def test_finished_run_is_returned_unchanged(self, tmp_path):
        _c = _make(tmp_path)
        _done = _wait(_c, _c.submit({"a": 1}))
        _again = _c.refresh(_done.id)
        assert _again.status == ComputeStatus.COMPLETED
        assert _again.finished_at == _done.finished_at
        assert _again.result == _done.result

    def test_finishing_removes_the_process_and_its_workdir(self, tmp_path, workdirs):
        _c = _make(tmp_path, entrypoint="fx_entries:wait_gate")
        _run, _gate = _submit_gated(_c, tmp_path)
        assert len(workdirs()) == 1
        assert (workdirs()[0] / "payload.json").exists()
        assert len(compute_module._live_processes) == 1
        _open(_gate)
        _wait(_c, _run)
        assert workdirs() == []
        assert _c._processes == {}
        assert compute_module._live_processes == set()

    def test_failed_run_also_releases_everything(self, tmp_path, workdirs):
        _c = _make(tmp_path, entrypoint="fx_entries:raises")
        _wait(_c, _c.submit())
        assert workdirs() == []
        assert _c._processes == {}
        assert compute_module._live_processes == set()

    def test_unknown_run_id_raises(self, tmp_path):
        with pytest.raises(ValueError, match="not found"):
            _make(tmp_path).refresh("run_missing")

    def test_invalid_run_type_raises(self, tmp_path):
        with pytest.raises(ValueError):
            _make(tmp_path).refresh(123)  # type: ignore[arg-type]

    def test_run_from_another_instance_is_failed_as_not_found(self, tmp_path):
        _a = _make(tmp_path, entrypoint="fx_entries:wait_gate")
        _run, _gate = _submit_gated(_a, tmp_path)
        _b = _make(tmp_path, entrypoint="fx_entries:wait_gate")
        _refreshed = _b.refresh(_run.id)
        assert _refreshed.status == ComputeStatus.FAILED
        assert _refreshed.error == "Process not found"
        assert _b.lookup(_run.id).status == ComputeStatus.FAILED
        _open(_gate)

    def test_run_without_external_id_is_failed_as_not_found(self, tmp_path):
        _c = _make(tmp_path)
        _run = ComputeRun(compute="demo", runtime=ComputeRuntime.PYENTRYPOINT)
        _c._write_run(_run)
        assert _c.refresh(_run.id).error == "Process not found"

    def test_stale_run_object_does_not_overwrite_a_finished_run(self, tmp_path):
        _c = _make(tmp_path, entrypoint="fx_entries:wait_gate")
        _run, _gate = _submit_gated(_c, tmp_path)
        _stale = _c.lookup(_run.id)
        _open(_gate)
        _process_of(_c, _run).process.wait(timeout=_WAIT_SECONDS)
        assert _c.refresh(_run.id).status == ComputeStatus.COMPLETED
        _refreshed = _c.refresh(_stale)
        assert _refreshed.status == ComputeStatus.COMPLETED
        assert _c.lookup(_run.id).status == ComputeStatus.COMPLETED
        assert _c.lookup(_run.id).result == {"gate": "opened", "n": None}


class TestConcurrency:
    def test_concurrent_refresh_of_one_finished_run_is_consistent(self, tmp_path):
        _c = _make(tmp_path, entrypoint="fx_entries:wait_gate")
        _threads: int = 8
        for _round in range(3):
            _run, _gate = _submit_gated(_c, tmp_path, name=f"gate{_round}")
            _open(_gate)
            _process_of(_c, _run).process.wait(timeout=_WAIT_SECONDS)
            _stale = [_c.lookup(_run.id) for _ in range(_threads)]
            _barrier = threading.Barrier(_threads)

            def _refresh(run: ComputeRun) -> ComputeRun:
                _barrier.wait()
                return _c.refresh(run)

            with ThreadPoolExecutor(_threads) as _pool:
                _results = list(_pool.map(_refresh, _stale))
            assert [_r.status for _r in _results] == [ComputeStatus.COMPLETED] * _threads
            assert _c.lookup(_run.id).status == ComputeStatus.COMPLETED
            assert _c.lookup(_run.id).error is None

    def test_concurrent_refresh_by_id_of_one_finished_run_is_consistent(self, tmp_path):
        _c = _make(tmp_path, entrypoint="fx_entries:wait_gate")
        _threads: int = 8
        _run, _gate = _submit_gated(_c, tmp_path)
        _open(_gate)
        _process_of(_c, _run).process.wait(timeout=_WAIT_SECONDS)
        _barrier = threading.Barrier(_threads)

        def _refresh(_: int) -> ComputeRun:
            _barrier.wait()
            return _c.refresh(_run.id)

        with ThreadPoolExecutor(_threads) as _pool:
            _results = list(_pool.map(_refresh, range(_threads)))
        assert all(_r.status == ComputeStatus.COMPLETED for _r in _results)
        assert _c.lookup(_run.id).status == ComputeStatus.COMPLETED

    def test_concurrent_submits(self, tmp_path):
        _c = _make(tmp_path)
        _count: int = 6
        with ThreadPoolExecutor(_count) as _pool:
            _runs = list(_pool.map(lambda _n: _c.submit({"n": _n}), range(_count)))
        assert len({_r.external_id for _r in _runs}) == _count
        assert len({_r.id for _r in _runs}) == _count
        for _n, _r in enumerate(_runs):
            assert _wait(_c, _r).result == {"echo": {"n": _n}}
        assert _c._processes == {}
        assert compute_module._live_processes == set()

    def test_concurrent_waiters_on_distinct_runs(self, tmp_path):
        _c = _make(tmp_path)
        _count: int = 4
        _runs = [_c.submit({"n": _n}) for _n in range(_count)]
        with ThreadPoolExecutor(_count) as _pool:
            _done = list(_pool.map(lambda _r: _wait(_c, _r), _runs))
        assert [_d.result["echo"]["n"] for _d in _done] == list(range(_count))

    def test_two_computes_sharing_a_store_keep_their_own_processes(self, tmp_path):
        _a = _make(tmp_path, name="a")
        _b = _make(tmp_path, name="b")
        _ra = _a.submit({"who": "a"})
        _rb = _b.submit({"who": "b"})
        assert _wait(_a, _ra).result == {"echo": {"who": "a"}}
        assert _wait(_b, _rb).result == {"echo": {"who": "b"}}
        assert [_r.id for _r in _a.list_runs()] == [_ra.id]
        assert [_r.id for _r in _b.list_runs()] == [_rb.id]


class TestTermination:
    def test_terminate_stops_a_running_child_and_releases_it(self, tmp_path, workdirs):
        _c = _make(tmp_path, entrypoint="fx_entries:signal_ready_then_wait")
        _ready: Path = tmp_path / "ready"
        _run = _c.submit({"ready": str(_ready)})
        _wait_file(_ready)
        _proc = _process_of(_c, _run)
        _proc.terminate()
        assert _proc.process.poll() == -15
        assert workdirs() == []
        assert compute_module._live_processes == set()

    def test_refresh_after_terminate_fails_the_run_with_the_exit_code(self, tmp_path):
        _c = _make(tmp_path, entrypoint="fx_entries:signal_ready_then_wait")
        _ready: Path = tmp_path / "ready"
        _run = _c.submit({"ready": str(_ready)})
        _wait_file(_ready)
        _process_of(_c, _run).terminate()
        _done = _c.refresh(_run)
        assert _done.status == ComputeStatus.FAILED
        assert _done.error.startswith("Process exited with code -15")

    def test_a_child_ignoring_sigterm_is_killed(self, tmp_path, monkeypatch, workdirs):
        monkeypatch.setattr(compute_module, "_TERMINATE_TIMEOUT", 0.5)
        _c = _make(tmp_path, entrypoint="fx_entries:ignore_sigterm")
        _ready: Path = tmp_path / "ready"
        _run = _c.submit({"ready": str(_ready)})
        _wait_file(_ready)
        _proc = _process_of(_c, _run)
        _proc.terminate()
        assert _proc.process.poll() == -9
        assert workdirs() == []

    def test_terminate_is_safe_to_repeat(self, tmp_path):
        _c = _make(tmp_path, entrypoint="fx_entries:signal_ready_then_wait")
        _ready: Path = tmp_path / "ready"
        _run = _c.submit({"ready": str(_ready)})
        _wait_file(_ready)
        _proc = _process_of(_c, _run)
        _proc.terminate()
        _proc.terminate()

    def test_exit_hook_terminates_every_live_child_of_every_instance(self, tmp_path, workdirs):
        _procs: list[_Process] = []
        for _name in ("a", "b"):
            _c = _make(tmp_path, entrypoint="fx_entries:signal_ready_then_wait", name=_name)
            _ready: Path = tmp_path / f"ready_{_name}"
            _run = _c.submit({"ready": str(_ready)})
            _wait_file(_ready)
            _procs.append(_process_of(_c, _run))
        assert len(compute_module._live_processes) == 2
        compute_module._terminate_live_processes()
        assert all(_p.process.poll() is not None for _p in _procs)
        assert compute_module._live_processes == set()
        assert workdirs() == []

    def test_exit_hook_with_no_children_is_a_no_op(self):
        compute_module._terminate_live_processes()
        assert compute_module._live_processes == set()


class TestProcess:
    @staticmethod
    def _fake(workdir: Path, returncode: int | None = 0) -> MagicMock:
        _p = MagicMock()
        _p.poll.return_value = returncode
        _p.returncode = returncode
        return _p

    def test_registers_itself_as_live(self, tmp_path):
        _proc = _Process(self._fake(tmp_path), tmp_path)
        assert _proc in compute_module._live_processes

    def test_finish_reads_a_valid_result_and_releases(self, tmp_path):
        (tmp_path / "result.json").write_text('{"ok": true, "result": {"a": 1}}', encoding="utf-8")
        _proc = _Process(self._fake(tmp_path), tmp_path)
        assert _proc.finish() == {"ok": True, "result": {"a": 1}}
        assert not tmp_path.exists()
        assert _proc not in compute_module._live_processes

    def test_finish_returns_a_reported_failure_as_is(self, tmp_path):
        (tmp_path / "result.json").write_text('{"ok": false, "error": "boom"}', encoding="utf-8")
        _proc = _Process(self._fake(tmp_path, returncode=1), tmp_path)
        assert _proc.finish() == {"ok": False, "error": "boom"}

    def test_result_wins_over_a_non_zero_exit_code(self, tmp_path):
        (tmp_path / "result.json").write_text('{"ok": true, "result": {}}', encoding="utf-8")
        (tmp_path / "stderr.log").write_text("noise", encoding="utf-8")
        _proc = _Process(self._fake(tmp_path, returncode=139), tmp_path)
        assert _proc.finish()["ok"] is True

    def test_missing_result_falls_back_to_exit_code_and_stderr(self, tmp_path):
        (tmp_path / "stderr.log").write_text("it broke", encoding="utf-8")
        _proc = _Process(self._fake(tmp_path, returncode=3), tmp_path)
        assert _proc.finish() == {"ok": False, "error": "Process exited with code 3: it broke"}

    @pytest.mark.parametrize("content", [b"{not json", b"", b"\xff\xfe\x00"])
    def test_corrupt_result_falls_back_to_exit_code_and_stderr(self, tmp_path, content):
        (tmp_path / "result.json").write_bytes(content)
        (tmp_path / "stderr.log").write_text("it broke", encoding="utf-8")
        _proc = _Process(self._fake(tmp_path, returncode=2), tmp_path)
        assert _proc.finish() == {"ok": False, "error": "Process exited with code 2: it broke"}

    def test_missing_stderr_is_tolerated_and_still_releases(self, tmp_path):
        _proc = _Process(self._fake(tmp_path, returncode=4), tmp_path)
        assert _proc.finish() == {"ok": False, "error": "Process exited with code 4: "}
        assert not tmp_path.exists()
        assert _proc not in compute_module._live_processes

    def test_missing_workdir_is_tolerated(self, tmp_path):
        _gone: Path = tmp_path / "gone"
        _proc = _Process(self._fake(_gone, returncode=5), _gone)
        assert _proc.finish()["error"].startswith("Process exited with code 5")
        assert _proc not in compute_module._live_processes

    def test_undecodable_stderr_is_replaced(self, tmp_path):
        (tmp_path / "stderr.log").write_bytes(b"ok \xff\xfe end")
        _proc = _Process(self._fake(tmp_path, returncode=1), tmp_path)
        _error: str = _proc.finish()["error"]
        assert _error.startswith("Process exited with code 1: ok ")
        assert _error.endswith(" end")

    def test_long_stderr_keeps_only_the_tail(self, tmp_path):
        (tmp_path / "stderr.log").write_text("a" * 5000 + "END", encoding="utf-8")
        _proc = _Process(self._fake(tmp_path, returncode=1), tmp_path)
        _error: str = _proc.finish()["error"]
        assert _error.endswith("END")
        assert len(_error) == len("Process exited with code 1: ") + compute_module._STDERR_TAIL_CHARS

    def test_terminate_of_a_running_process(self, tmp_path):
        _fake = self._fake(tmp_path, returncode=None)
        _proc = _Process(_fake, tmp_path)
        _proc.terminate()
        _fake.terminate.assert_called_once_with()
        _fake.wait.assert_called_once_with(timeout=compute_module._TERMINATE_TIMEOUT)
        _fake.kill.assert_not_called()
        assert not tmp_path.exists()
        assert _proc not in compute_module._live_processes

    def test_terminate_escalates_to_kill_on_timeout(self, tmp_path):
        _fake = self._fake(tmp_path, returncode=None)
        _fake.wait.side_effect = [subprocess.TimeoutExpired("cmd", 1), None]
        _proc = _Process(_fake, tmp_path)
        _proc.terminate()
        _fake.kill.assert_called_once_with()
        assert _fake.wait.call_count == 2
        assert not tmp_path.exists()

    def test_terminate_of_an_exited_process_only_releases(self, tmp_path):
        _fake = self._fake(tmp_path, returncode=0)
        _proc = _Process(_fake, tmp_path)
        _proc.terminate()
        _fake.terminate.assert_not_called()
        _fake.kill.assert_not_called()
        assert not tmp_path.exists()
        assert _proc not in compute_module._live_processes
