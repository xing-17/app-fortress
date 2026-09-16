from __future__ import annotations

from pathlib import Path

import pytest

from app.internal.util.path import IPath


class TestIPathResolve:
    def test_resolve_relative_path_returns_absolute_path(self):
        result = IPath.resolve("some/relative/path")
        assert result.is_absolute()

    def test_resolve_expands_user_home(self):
        result = IPath.resolve("~/some_file")
        assert result == Path.home() / "some_file"

    def test_resolve_accepts_path_instance(self):
        result = IPath.resolve(Path("some/relative/path"))
        assert result == Path("some/relative/path").expanduser().resolve()

    def test_resolve_empty_string_without_default_raises_value_error(self):
        with pytest.raises(ValueError):
            IPath.resolve("")

    def test_resolve_none_without_default_raises_value_error(self):
        with pytest.raises(ValueError):
            IPath.resolve(None)  # type: ignore[arg-type]

    def test_resolve_empty_value_uses_default(self, tmp_path):
        result = IPath.resolve("", default=tmp_path)
        assert result == tmp_path.expanduser().resolve()

    def test_resolve_existing_path_with_validate_returns_path(self, tmp_path):
        result = IPath.resolve(tmp_path, validate=True)
        assert result == tmp_path.expanduser().resolve()

    def test_resolve_missing_path_with_validate_raises_value_error(self, tmp_path):
        missing = tmp_path / "missing"
        with pytest.raises(ValueError):
            IPath.resolve(missing, validate=True)

    def test_resolve_missing_path_without_validate_does_not_raise(self, tmp_path):
        missing = tmp_path / "missing"
        result = IPath.resolve(missing)
        assert result == missing.expanduser().resolve()


class TestIPathValidateExists:
    def test_validate_exists_returns_resolved_path(self, tmp_path):
        result = IPath.validate_exists(tmp_path)
        assert result == tmp_path.expanduser().resolve()

    def test_validate_exists_missing_path_raises_value_error(self, tmp_path):
        missing = tmp_path / "missing"
        with pytest.raises(ValueError):
            IPath.validate_exists(missing)

    def test_validate_exists_accepts_string_input(self, tmp_path):
        result = IPath.validate_exists(str(tmp_path))
        assert result == tmp_path.expanduser().resolve()
