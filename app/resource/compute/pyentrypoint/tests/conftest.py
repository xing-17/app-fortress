from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.resource._global.identities import GlobalIdentities
from app.resource.compute.pyentrypoint import compute as compute_module

_ENTRIES: Path = Path(__file__).parent / "_entries"


@pytest.fixture(scope="session", autouse=True)
def _entries_on_path():
    # fixture entrypoints live outside `app` so a child process imports them without loading the app
    _mp = pytest.MonkeyPatch()
    _mp.syspath_prepend(str(_ENTRIES))
    yield
    _mp.undo()


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path_factory):
    GlobalIdentities.reset()
    _tmp: Path = tmp_path_factory.mktemp("tmpdir")
    monkeypatch.setattr(tempfile, "tempdir", str(_tmp))
    yield
    # no test may leave a running child behind
    for _proc in list(compute_module._live_processes):
        _proc.terminate()
    GlobalIdentities.reset()


@pytest.fixture
def workdirs():
    """Currently existing run working directories."""

    def _list() -> list[Path]:
        return sorted(Path(tempfile.gettempdir()).glob("pyentrypoint_*"))

    return _list
