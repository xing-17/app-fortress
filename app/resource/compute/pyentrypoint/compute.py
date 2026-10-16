from __future__ import annotations

import atexit
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any, ClassVar

from pydantic import Field, PrivateAttr

from app.internal.constant.computeruntime import ComputeRuntime
from app.internal.constant.platform import Platform
from app.resource.compute._common._compute import BaseCompute
from app.resource.compute._common._run import ComputeRun
from app.resource.compute.pyentrypoint import runner
from app.setting._compute import PyEntrypointComputeSetting

_STDERR_TAIL_CHARS: int = 2000
_TERMINATE_TIMEOUT: float = 5.0

# unfinished subprocesses of every instance
# terminated when the parent exits
_live_processes: set[_Process] = set()
_live_lock = threading.Lock()


class _Process:
    """
    A running runner subprocess and the temp files it exchanges data through.

    Args:
    ----------
        process (subprocess.Popen[bytes]):
            The running subprocess.
        workdir (Path):
            The temporary working directory for exchanging data with the subprocess.

    """

    def __init__(
        self,
        process: subprocess.Popen[bytes],
        workdir: Path,
    ) -> None:
        self.process = process
        self.workdir = workdir
        with _live_lock:
            _live_processes.add(self)

    def terminate(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=_TERMINATE_TIMEOUT)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self._release()

    def finish(self) -> dict[str, Any]:
        try:
            try:
                _res_path: Path = self.workdir / "result.json"
                _res: str = _res_path.read_text(encoding="utf-8")
                _outcome: dict[str, Any] = json.loads(_res)
            except (OSError, ValueError):
                try:
                    _stderr_path: Path = self.workdir / "stderr.log"
                    _stderr: str = _stderr_path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    _stderr = ""
                _res_code: int = self.process.returncode
                _stderr_cutoff: str = _stderr[-_STDERR_TAIL_CHARS:]
                _outcome = {
                    "ok": False,
                    "error": f"Process exited with code {_res_code}: {_stderr_cutoff}",
                }
        finally:
            self._release()
        return _outcome

    def _release(self) -> None:
        with _live_lock:
            _live_processes.discard(self)
        shutil.rmtree(self.workdir, ignore_errors=True)


@atexit.register
def _terminate_live_processes() -> None:
    with _live_lock:
        _procs: list[_Process] = list(_live_processes)
    for _proc in _procs:
        _proc.terminate()


class PyEntrypointCompute(BaseCompute):
    """
    Local Python entrypoint compute, calls `package.module:function(payload=...)`

    `execute` calls the entrypoint in the current process,
    `submit` runs it in a fresh Python subprocess (no fork, no re-import of the caller's `__main__`).

    The payload and the result are JSON, the same contract a remote runtime imposes.
    The entrypoint should rebuild its own resources (e.g. a source from the system setting) and return a small dict.
    A submitted run is only tracked by the instance that submitted it, a restart turns it into FAILED on refresh.
    Unfinished subprocesses are terminated when the parent exits.

    Attributes:
    ----------
        runtime (ComputeRuntime):
            Compute runtime, fixed as ComputeRuntime.PYENTRYPOINT
        platform (Platform):
            Compute platform, fixed as Platform.LOCAL
        frn (str):
            Compute FRN (Fortress resource identifier)

    Args:
    ----------
        name (str):
            Compute name
        entrypoint (str):
            Importable function in `package.module:function` form
        description (str):
            Compute description information
        store (BaseStore | AbstractStoreSetting | str | None):
            Store holding the run records
        tags (dict[str, str]):
            Compute tags

    Methods:
    ----------
        from_setting(cls, setting: PyEntrypointComputeSetting) -> PyEntrypointCompute:
            Create a PyEntrypointCompute from a PyEntrypointComputeSetting.
        execute(payload: dict[str, Any] | None = None) -> ComputeRun:
            Run the entrypoint in the current process, record and return the run.
        submit(payload: dict[str, Any] | None = None) -> ComputeRun:
            Run the entrypoint in a subprocess and return the run immediately.
        refresh(run: ComputeRun | str) -> ComputeRun:
            Update the run to COMPLETED or FAILED once the subprocess has exited.

    Example:
    ----------
        >>> compute = PyEntrypointCompute(name="local_fetch", entrypoint="app.entrypoint:run_dataset")
        >>> run = compute.submit({"source": "tushare_prod", "dataset": "tradedates"})
        >>> compute.refresh(run).status

    """

    # Enforced public class variables
    runtime: ClassVar[ComputeRuntime] = ComputeRuntime.PYENTRYPOINT
    platform: ClassVar[Platform] = Platform.LOCAL

    # Enforced instance variables
    # [Inherited] name: str
    # [Inherited] description: str
    # [Inherited] tags: dict[str, str]
    entrypoint: str = Field(
        ...,
        description="[Required] Importable function in `package.module:function` form",
    )

    # Enforced private instance variables
    _processes: dict[str, _Process] = PrivateAttr(default_factory=dict)
    _lock: threading.RLock = PrivateAttr(default_factory=threading.RLock)

    @classmethod
    def from_setting(
        cls,
        setting: PyEntrypointComputeSetting,
    ) -> PyEntrypointCompute:
        return cls(
            name=setting.name,
            entrypoint=setting.entrypoint,
            description=setting.description,
            store=setting.store,
            max_run_records=setting.max_run_records,
            tags=setting.tags,
        )

    def _execute(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return runner.invoke(self.entrypoint, payload)

    def _submit(
        self,
        payload: dict[str, Any],
    ) -> str:
        runner.resolve_entrypoint(self.entrypoint)
        _workdir: Path = Path(tempfile.mkdtemp(prefix="pyentrypoint_"))
        try:
            _payload_path: Path = _workdir / "payload.json"
            _payload_text: str = json.dumps(payload, ensure_ascii=False)
            _payload_path.write_text(
                data=_payload_text,
                encoding="utf-8",
            )
            # the child gets the parent's import path
            # `-P` keeps the runner's own folder off it
            _p_path: str = os.pathsep.join(_p or os.getcwd() for _p in sys.path)
            _env: dict[str, str] = {
                **os.environ,
                "PYTHONPATH": _p_path,
            }
            _stderr_path: Path = _workdir / "stderr.log"
            _result_path: Path = _workdir / "result.json"
            with _stderr_path.open("wb") as _stderr:
                _popen: subprocess.Popen[bytes] = subprocess.Popen(
                    [
                        sys.executable,
                        "-P",
                        runner.__file__,
                        self.entrypoint,
                        str(_payload_path),
                        str(_result_path),
                    ],
                    stdin=subprocess.DEVNULL,
                    stderr=_stderr,
                    env=_env,
                )
        except BaseException:
            shutil.rmtree(_workdir, ignore_errors=True)
            raise

        _external_id: str = str(_popen.pid)
        with self._lock:
            self._processes[_external_id] = _Process(
                process=_popen,
                workdir=_workdir,
            )
        return _external_id

    def _get_process(
        self,
        run: ComputeRun,
    ) -> _Process | None:
        _external_id: str | None = run.external_id
        with self._lock:
            return self._processes.get(_external_id)

    def refresh(
        self,
        run: ComputeRun | str,
    ) -> ComputeRun:
        # poll and record under one lock
        # so concurrent refreshes cannot record conflicting outcomes
        with self._lock:
            return super().refresh(run)

    def _poll(
        self,
        run: ComputeRun,
    ) -> ComputeRun:
        _proc: _Process | None = self._get_process(run)
        if _proc is None:
            # a stale run object may already have been finished by an earlier refresh
            _stored: ComputeRun | None = self.lookup(run.id)
            if _stored is not None and _stored.is_finished:
                return _stored
            # no entry means this instance never spawned it, or it was lost across a restart
            run.fail(error="Process not found")
            return run

        if _proc.process.poll() is None:
            # process is still running
            # so the run is considered started
            return run

        # process has exited
        with self._lock:
            self._processes.pop(run.external_id, None)

        _outcome: dict[str, Any] = _proc.finish()
        if _outcome.get("ok"):
            run.complete(result=_outcome.get("result"))
        else:
            run.fail(error=_outcome.get("error"))
        return run
