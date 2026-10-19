import pytest


@pytest.fixture(autouse=True)
def _isolate_cwd(tmp_path, monkeypatch):
    # Relative default paths (./.local, ./.logs) must never land in the project tree
    monkeypatch.chdir(tmp_path)
