from __future__ import annotations

from pathlib import Path

import pytest

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.resource._global.identities import GlobalIdentities
from app.resource.identity.aliyun.aliyun import AliyunIdentity
from app.resource.identity.local.local import LocalIdentity
from app.resource.store.file.store import FileStore
from app.setting._store import FileStoreSetting


@pytest.fixture(autouse=True)
def _reset_global_identities():
    # GlobalIdentities holds process-wide singleton state; isolate tests from each other.
    GlobalIdentities.reset()
    yield
    GlobalIdentities.reset()


class TestFileStoreInit:
    def test_default_identity_is_local_identity_default(self, tmp_path):
        store = FileStore(name="my_store", path=str(tmp_path))
        assert store.identity.name == LocalIdentity.default().name

    def test_storesystem_and_platform_are_fixed(self, tmp_path):
        store = FileStore(name="my_store", path=str(tmp_path))
        assert store.storesystem == StoreSystem.FILE
        assert store.platform == Platform.LOCAL


class TestFileStoreDerivePath:
    def test_string_path_is_resolved_to_path_and_created(self, tmp_path):
        _target = tmp_path / "new_store_dir"
        store = FileStore(name="my_store", path=str(_target))
        assert isinstance(store.path, Path)
        assert store.path == _target
        assert _target.is_dir()

    def test_existing_directory_string_path_is_kept(self, tmp_path):
        store = FileStore(name="my_store", path=str(tmp_path))
        assert store.path == tmp_path

    def test_string_path_pointing_to_file_raises_value_error(self, tmp_path):
        _file = tmp_path / "a_file.txt"
        _file.write_text("content")
        with pytest.raises(ValueError):
            FileStore(name="my_store", path=str(_file))


class TestFileStoreFromSetting:
    def test_from_setting_copies_name_path_tags(self, tmp_path):
        setting = FileStoreSetting(
            name="my_store",
            path=str(tmp_path),
            tags={"env": "test"},
        )
        store = FileStore.from_setting(setting)
        assert store.name == "my_store"
        assert store.path == tmp_path
        assert store.tags["env"] == "test"

    def test_from_setting_uses_default_identity_when_not_specified(self, tmp_path):
        setting = FileStoreSetting(name="my_store", path=str(tmp_path))
        store = FileStore.from_setting(setting)
        assert store.identity.name == LocalIdentity.default().name

    def test_from_setting_resolves_named_identity(self, tmp_path):
        _identity = LocalIdentity(name="registered_local_identity")
        GlobalIdentities.identities = {"registered_local_identity": _identity}
        setting = FileStoreSetting(
            name="my_store",
            path=str(tmp_path),
            identity="registered_local_identity",
        )
        store = FileStore.from_setting(setting)
        assert store.identity is _identity

    def test_from_setting_raises_value_error_on_platform_mismatch(self, tmp_path):
        _aliyun_identity = AliyunIdentity(name="an_aliyun_identity")
        GlobalIdentities.identities = {"an_aliyun_identity": _aliyun_identity}
        setting = FileStoreSetting(
            name="my_store",
            path=str(tmp_path),
            identity="an_aliyun_identity",
        )
        with pytest.raises(ValueError):
            FileStore.from_setting(setting)


class TestFileStoreWriteAndReadBytes:
    def test_write_bytes_creates_file_under_path(self, tmp_path):
        store = FileStore(name="my_store", path=str(tmp_path))
        store.write_bytes("a.txt", b"hello")
        assert (tmp_path / "a.txt").read_bytes() == b"hello"

    def test_write_bytes_creates_missing_parent_directories(self, tmp_path):
        store = FileStore(name="my_store", path=str(tmp_path))
        store.write_bytes("nested/deeper/a.txt", b"hello")
        assert (tmp_path / "nested" / "deeper" / "a.txt").read_bytes() == b"hello"

    def test_read_bytes_returns_written_content(self, tmp_path):
        store = FileStore(name="my_store", path=str(tmp_path))
        store.write_bytes("a.txt", b"payload")
        assert store.read_bytes("a.txt") == b"payload"

    def test_read_bytes_missing_key_raises_file_not_found_error(self, tmp_path):
        store = FileStore(name="my_store", path=str(tmp_path))
        with pytest.raises(FileNotFoundError):
            store.read_bytes("missing.txt")


class TestFileStoreFrn:
    def test_frn_returns_expected_identifier(self, tmp_path):
        store = FileStore(name="my_store", path=str(tmp_path))
        assert store.frn == f"store:platform={Platform.LOCAL}:storesystem={StoreSystem.FILE}:name=my_store"
