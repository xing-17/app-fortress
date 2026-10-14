from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.setting import (
    AliyunIdentitySetting,
    FileStoreSetting,
    LocalIdentitySetting,
    OSSStoreSetting,
    UnionStoreSetting,
)


class TestUnionStoreSetting:
    def test_dispatches_on_storesystem(self):
        _adapter = TypeAdapter(UnionStoreSetting)
        assert isinstance(_adapter.validate_python({"name": "s", "storesystem": "file"}), FileStoreSetting)
        _oss = _adapter.validate_python({"name": "s", "storesystem": "oss", "bucket": "b", "region": "r"})
        assert isinstance(_oss, OSSStoreSetting)

    def test_unknown_storesystem_is_rejected(self):
        with pytest.raises(ValidationError):
            TypeAdapter(UnionStoreSetting).validate_python({"name": "s", "storesystem": "unknown"})

    def test_missing_storesystem_is_rejected(self):
        with pytest.raises(ValidationError):
            TypeAdapter(UnionStoreSetting).validate_python({"name": "s"})


class TestFileStoreSetting:
    def test_defaults(self):
        _s = FileStoreSetting(name="s")
        assert _s.storesystem == StoreSystem.FILE
        assert _s.platform == Platform.LOCAL
        assert _s.path is None
        assert _s.identity is None

    def test_name_is_required(self):
        with pytest.raises(ValidationError):
            FileStoreSetting()

    def test_discriminators_are_fixed(self):
        with pytest.raises(ValidationError):
            FileStoreSetting(name="s", storesystem="oss")
        with pytest.raises(ValidationError):
            FileStoreSetting(name="s", platform="aliyun")

    def test_identity_accepts_name(self):
        assert FileStoreSetting(name="s", identity="id").identity == "id"

    def test_identity_accepts_nested_setting(self):
        _s = FileStoreSetting(name="s", identity={"name": "id", "platform": "local"})
        assert isinstance(_s.identity, LocalIdentitySetting)

    def test_identity_accepts_none(self):
        assert FileStoreSetting(name="s", identity=None).identity is None

    def test_identity_rejects_other_platform(self):
        with pytest.raises(ValidationError):
            FileStoreSetting(name="s", identity={"name": "id", "platform": "aliyun"})
        with pytest.raises(ValidationError):
            FileStoreSetting(name="s", identity=AliyunIdentitySetting(name="id"))

    def test_frn(self):
        assert FileStoreSetting(name="s").frn == "setting:store:platform=local:storesystem=file:name=s"

    def test_user_tags_cannot_override_reserved_tags(self):
        _s = FileStoreSetting(name="s", tags={"name": "fake", "storesystem": "fake", "env": "prod"})
        assert _s.tags["name"] == "s"
        assert _s.tags["storesystem"] == "file"
        assert _s.tags["platform"] == "local"
        assert _s.tags["env"] == "prod"


class TestOSSStoreSetting:
    def test_defaults(self):
        _s = OSSStoreSetting(name="s", bucket="b", region="r")
        assert _s.storesystem == StoreSystem.OSS
        assert _s.platform == Platform.ALIYUN
        assert _s.prefix is None
        assert _s.in_vpc is False
        assert _s.identity is None

    def test_requires_bucket_and_region(self):
        with pytest.raises(ValidationError):
            OSSStoreSetting(name="s")
        with pytest.raises(ValidationError):
            OSSStoreSetting(name="s", bucket="b")
        with pytest.raises(ValidationError):
            OSSStoreSetting(name="s", region="r")

    def test_discriminators_are_fixed(self):
        with pytest.raises(ValidationError):
            OSSStoreSetting(name="s", bucket="b", region="r", storesystem="file")
        with pytest.raises(ValidationError):
            OSSStoreSetting(name="s", bucket="b", region="r", platform="local")

    def test_identity_accepts_name(self):
        assert OSSStoreSetting(name="s", bucket="b", region="r", identity="id").identity == "id"

    def test_identity_accepts_nested_setting(self):
        _s = OSSStoreSetting(
            name="s",
            bucket="b",
            region="r",
            identity={"name": "id", "platform": "aliyun", "type": "ak"},
        )
        assert isinstance(_s.identity, AliyunIdentitySetting)

    def test_identity_rejects_other_platform(self):
        with pytest.raises(ValidationError):
            OSSStoreSetting(name="s", bucket="b", region="r", identity={"name": "id", "platform": "local"})
        with pytest.raises(ValidationError):
            OSSStoreSetting(name="s", bucket="b", region="r", identity=LocalIdentitySetting(name="id"))

    def test_frn(self):
        _s = OSSStoreSetting(name="s", bucket="b", region="r")
        assert _s.frn == "setting:store:platform=aliyun:storesystem=oss:name=s"

    def test_user_tags_cannot_override_reserved_tags(self):
        _s = OSSStoreSetting(name="s", bucket="b", region="r", tags={"platform": "fake", "env": "prod"})
        assert _s.tags["platform"] == "aliyun"
        assert _s.tags["env"] == "prod"
