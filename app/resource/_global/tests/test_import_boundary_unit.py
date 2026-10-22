from __future__ import annotations

import subprocess
import sys


def _loaded_after_import(statement: str, modules: list[str]) -> list[str]:
    _code = f"import sys; {statement}; print([m for m in {modules!r} if m in sys.modules])"
    _out = subprocess.run([sys.executable, "-c", _code], capture_output=True, text=True, check=True)
    return eval(_out.stdout.strip())


class TestResourceImportBoundary:
    def test_import_resource_does_not_load_engine_or_service(self):
        _loaded = _loaded_after_import(
            "import app.resource, app.setting",
            ["duckdb", "mcp", "uvicorn", "app.service"],
        )
        assert _loaded == []
