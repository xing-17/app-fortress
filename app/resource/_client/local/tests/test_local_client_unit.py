from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pytest

from app.resource._client.local.client import LocalObjectClient


def _set_mtime(path: Path, timestamp: float) -> None:
    os.utime(path, (timestamp, timestamp))


class TestWriteBytes:
    def test_writes_content_to_new_file(self, tmp_path):
        _target = tmp_path / "a.txt"
        LocalObjectClient.write_bytes(_target, b"hello")
        assert _target.read_bytes() == b"hello"

    def test_creates_missing_parent_directories(self, tmp_path):
        _target = tmp_path / "nested" / "deeper" / "a.txt"
        LocalObjectClient.write_bytes(_target, b"hello")
        assert _target.exists()

    def test_overwrites_existing_file(self, tmp_path):
        _target = tmp_path / "a.txt"
        _target.write_bytes(b"old")
        LocalObjectClient.write_bytes(_target, b"new")
        assert _target.read_bytes() == b"new"

    def test_writes_empty_bytes(self, tmp_path):
        _target = tmp_path / "a.txt"
        LocalObjectClient.write_bytes(_target, b"")
        assert _target.read_bytes() == b""

    def test_existing_parent_directory_is_not_disturbed(self, tmp_path):
        _target = tmp_path / "a.txt"
        LocalObjectClient.write_bytes(_target, b"hello")
        assert tmp_path.is_dir()


class TestReadBytes:
    def test_reads_back_written_content(self, tmp_path):
        _target = tmp_path / "a.txt"
        _target.write_bytes(b"payload")
        assert LocalObjectClient.read_bytes(_target) == b"payload"

    def test_missing_file_raises_file_not_found_error(self, tmp_path):
        _target = tmp_path / "missing.txt"
        with pytest.raises(FileNotFoundError):
            LocalObjectClient.read_bytes(_target)

    def test_directory_raises_is_a_directory_error(self, tmp_path):
        with pytest.raises(IsADirectoryError):
            LocalObjectClient.read_bytes(tmp_path)


class TestGetObject:
    def test_returns_path_key_as_path_instance(self, tmp_path):
        _target = tmp_path / "a.txt"
        _target.write_bytes(b"payload")
        _meta = LocalObjectClient.get_object(_target)
        assert isinstance(_meta["path"], Path)
        assert _meta["path"] == _target

    def test_stat_dict_reports_actual_file_size(self, tmp_path):
        _target = tmp_path / "a.txt"
        _target.write_bytes(b"payload")
        _meta = LocalObjectClient.get_object(_target)
        assert _meta["stat"]["st_size"] == len(b"payload")

    def test_stat_dict_contains_expected_keys(self, tmp_path):
        _target = tmp_path / "a.txt"
        _target.write_bytes(b"payload")
        _meta = LocalObjectClient.get_object(_target)
        assert set(_meta["stat"].keys()) == {
            "st_mode",
            "st_ino",
            "st_dev",
            "st_nlink",
            "st_uid",
            "st_gid",
            "st_size",
            "st_atime",
            "st_mtime",
            "st_ctime",
        }

    def test_missing_file_raises_file_not_found_error(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            LocalObjectClient.get_object(tmp_path / "missing.txt")

    def test_directory_is_accepted_without_error(self, tmp_path):
        # Docstring claims "single file" but get_object has no is_file() guard;
        # calling it on a directory silently succeeds instead of raising.
        _meta = LocalObjectClient.get_object(tmp_path)
        assert _meta["path"] == tmp_path


class TestListObjectsBasics:
    def test_missing_directory_returns_empty_list(self, tmp_path):
        assert LocalObjectClient.list_objects(tmp_path / "missing") == []

    def test_file_path_instead_of_directory_returns_empty_list(self, tmp_path):
        _target = tmp_path / "a.txt"
        _target.write_bytes(b"x")
        assert LocalObjectClient.list_objects(_target) == []

    def test_empty_directory_returns_empty_list(self, tmp_path):
        assert LocalObjectClient.list_objects(tmp_path) == []

    def test_lists_files_at_top_level(self, tmp_path):
        (tmp_path / "a.txt").write_bytes(b"a")
        (tmp_path / "b.txt").write_bytes(b"b")
        _result = LocalObjectClient.list_objects(tmp_path)
        assert {m["path"] for m in _result} == {tmp_path / "a.txt", tmp_path / "b.txt"}

    def test_recurses_into_nested_directories(self, tmp_path):
        _nested = tmp_path / "sub"
        _nested.mkdir()
        (_nested / "c.txt").write_bytes(b"c")
        _result = LocalObjectClient.list_objects(tmp_path)
        assert _nested / "c.txt" in {m["path"] for m in _result}

    def test_directories_themselves_are_excluded_from_results(self, tmp_path):
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "c.txt").write_bytes(b"c")
        _result = LocalObjectClient.list_objects(tmp_path)
        assert all(p["path"].is_file() for p in _result)
        assert (tmp_path / "sub") not in {m["path"] for m in _result}

    def test_results_are_sorted_by_path(self, tmp_path):
        (tmp_path / "b.txt").write_bytes(b"b")
        (tmp_path / "a.txt").write_bytes(b"a")
        (tmp_path / "c.txt").write_bytes(b"c")
        _paths = [m["path"] for m in LocalObjectClient.list_objects(tmp_path)]
        assert _paths == sorted(_paths)

    def test_each_entry_matches_get_object_shape(self, tmp_path):
        (tmp_path / "a.txt").write_bytes(b"a")
        _result = LocalObjectClient.list_objects(tmp_path)
        assert _result[0].keys() == {"path", "stat"}


class TestListObjectsSinceUntilFilters:
    def _make_files_with_mtimes(self, tmp_path) -> dict[str, Path]:
        _old = tmp_path / "old.txt"
        _mid = tmp_path / "mid.txt"
        _new = tmp_path / "new.txt"
        for _p in (_old, _mid, _new):
            _p.write_bytes(b"x")
        _set_mtime(_old, 1_000_000)
        _set_mtime(_mid, 2_000_000)
        _set_mtime(_new, 3_000_000)
        return {"old": _old, "mid": _mid, "new": _new}

    def test_since_as_float_excludes_older_files(self, tmp_path):
        _files = self._make_files_with_mtimes(tmp_path)
        _result = LocalObjectClient.list_objects(tmp_path, since=1_500_000)
        assert {m["path"] for m in _result} == {_files["mid"], _files["new"]}

    def test_since_as_datetime_is_converted_to_timestamp(self, tmp_path):
        _files = self._make_files_with_mtimes(tmp_path)
        _since = datetime.fromtimestamp(1_500_000)
        _result = LocalObjectClient.list_objects(tmp_path, since=_since)
        assert {m["path"] for m in _result} == {_files["mid"], _files["new"]}

    def test_until_as_float_excludes_newer_files(self, tmp_path):
        _files = self._make_files_with_mtimes(tmp_path)
        _result = LocalObjectClient.list_objects(tmp_path, until=2_500_000)
        assert {m["path"] for m in _result} == {_files["old"], _files["mid"]}

    def test_until_as_datetime_is_converted_to_timestamp(self, tmp_path):
        _files = self._make_files_with_mtimes(tmp_path)
        _until = datetime.fromtimestamp(2_500_000)
        _result = LocalObjectClient.list_objects(tmp_path, until=_until)
        assert {m["path"] for m in _result} == {_files["old"], _files["mid"]}

    def test_since_and_until_combined_selects_middle_range(self, tmp_path):
        _files = self._make_files_with_mtimes(tmp_path)
        _result = LocalObjectClient.list_objects(
            tmp_path,
            since=1_500_000,
            until=2_500_000,
        )
        assert {m["path"] for m in _result} == {_files["mid"]}

    def test_since_boundary_is_inclusive(self, tmp_path):
        _files = self._make_files_with_mtimes(tmp_path)
        _result = LocalObjectClient.list_objects(tmp_path, since=2_000_000)
        assert _files["mid"] in {m["path"] for m in _result}

    def test_until_boundary_is_inclusive(self, tmp_path):
        _files = self._make_files_with_mtimes(tmp_path)
        _result = LocalObjectClient.list_objects(tmp_path, until=2_000_000)
        assert _files["mid"] in {m["path"] for m in _result}


class TestListObjectsRecursive:
    def _make_nested_files(self, tmp_path) -> None:
        (tmp_path / "top.txt").write_bytes(b"top")
        _nested = tmp_path / "sub"
        _nested.mkdir()
        (_nested / "nested.txt").write_bytes(b"nested")

    def test_recursive_true_includes_nested_files(self, tmp_path):
        self._make_nested_files(tmp_path)
        _result = LocalObjectClient.list_objects(tmp_path, recursive=True)
        assert {m["path"] for m in _result} == {
            tmp_path / "top.txt",
            tmp_path / "sub" / "nested.txt",
        }

    def test_recursive_false_excludes_nested_files(self, tmp_path):
        self._make_nested_files(tmp_path)
        _result = LocalObjectClient.list_objects(tmp_path, recursive=False)
        assert {m["path"] for m in _result} == {tmp_path / "top.txt"}

    def test_recursive_defaults_to_true(self, tmp_path):
        self._make_nested_files(tmp_path)
        _result = LocalObjectClient.list_objects(tmp_path)
        assert tmp_path / "sub" / "nested.txt" in {m["path"] for m in _result}


class TestListFolders:
    def test_missing_directory_returns_empty_list(self, tmp_path):
        assert LocalObjectClient.list_folders(tmp_path / "missing") == []

    def test_file_path_instead_of_directory_returns_empty_list(self, tmp_path):
        _target = tmp_path / "a.txt"
        _target.write_bytes(b"x")
        assert LocalObjectClient.list_folders(_target) == []

    def test_empty_directory_returns_empty_list(self, tmp_path):
        assert LocalObjectClient.list_folders(tmp_path) == []

    def test_lists_top_level_folders(self, tmp_path):
        (tmp_path / "sub1").mkdir()
        (tmp_path / "sub2").mkdir()
        _result = LocalObjectClient.list_folders(tmp_path)
        assert {m["path"] for m in _result} == {tmp_path / "sub1", tmp_path / "sub2"}

    def test_files_are_excluded_from_results(self, tmp_path):
        (tmp_path / "sub").mkdir()
        (tmp_path / "a.txt").write_bytes(b"a")
        _result = LocalObjectClient.list_folders(tmp_path)
        assert all(p["path"].is_dir() for p in _result)
        assert (tmp_path / "a.txt") not in {m["path"] for m in _result}

    def test_results_are_sorted_by_path(self, tmp_path):
        (tmp_path / "b").mkdir()
        (tmp_path / "a").mkdir()
        (tmp_path / "c").mkdir()
        _paths = [m["path"] for m in LocalObjectClient.list_folders(tmp_path)]
        assert _paths == sorted(_paths)

    def test_recursive_true_includes_nested_folders(self, tmp_path):
        _nested = tmp_path / "sub" / "deeper"
        _nested.mkdir(parents=True)
        _result = LocalObjectClient.list_folders(tmp_path, recursive=True)
        assert {m["path"] for m in _result} == {tmp_path / "sub", _nested}

    def test_recursive_false_excludes_nested_folders(self, tmp_path):
        _nested = tmp_path / "sub" / "deeper"
        _nested.mkdir(parents=True)
        _result = LocalObjectClient.list_folders(tmp_path, recursive=False)
        assert {m["path"] for m in _result} == {tmp_path / "sub"}

    def test_recursive_defaults_to_true(self, tmp_path):
        _nested = tmp_path / "sub" / "deeper"
        _nested.mkdir(parents=True)
        _result = LocalObjectClient.list_folders(tmp_path)
        assert _nested in {m["path"] for m in _result}

    def test_each_entry_matches_get_object_shape(self, tmp_path):
        (tmp_path / "sub").mkdir()
        _result = LocalObjectClient.list_folders(tmp_path)
        assert _result[0].keys() == {"path", "stat"}
