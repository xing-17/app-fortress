from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.setting import (
    AliyunIdentitySetting,
    LocalIdentitySetting,
    LocalVaultSetting,
    OSSVaultSetting,
    UnionVaultSetting,
)


class TestUnionVaultSetting:
    def test_dispatches_on_filesystem(self):
        _adapter = TypeAdapter(UnionVaultSetting)
        assert isinstance(
            _adapter.validate_python({"name": "v", "filesystem": "local", "path": "./v"}), LocalVaultSetting
        )
        _oss = _adapter.validate_python({"name": "v", "filesystem": "oss", "bucket": "b", "region": "r"})
        assert isinstance(_oss, OSSVaultSetting)

    def test_unknown_filesystem_is_rejected(self):
        with pytest.raises(ValidationError):
            TypeAdapter(UnionVaultSetting).validate_python({"name": "v", "filesystem": "unknown"})

    def test_missing_filesystem_is_rejected(self):
        with pytest.raises(ValidationError):
            TypeAdapter(UnionVaultSetting).validate_python({"name": "v", "path": "./v"})


class TestLocalVaultSetting:
    def test_defaults(self):
        _s = LocalVaultSetting(name="v", path="./v")
        assert _s.filesystem == AssetFilesystem.LOCAL
        assert _s.platform == Platform.LOCAL
        assert _s.identity is None
        assert _s.description == ""
        assert _s.tags["name"] == "v"

    def test_requires_name_and_path(self):
        with pytest.raises(ValidationError):
            LocalVaultSetting(name="v")
        with pytest.raises(ValidationError):
            LocalVaultSetting(path="./v")

    def test_discriminators_are_fixed(self):
        with pytest.raises(ValidationError):
            LocalVaultSetting(name="v", path="./v", filesystem="oss")
        with pytest.raises(ValidationError):
            LocalVaultSetting(name="v", path="./v", platform="aliyun")

    def test_identity_accepts_name(self):
        assert LocalVaultSetting(name="v", path="./v", identity="id").identity == "id"

    def test_identity_accepts_nested_setting(self):
        _s = LocalVaultSetting(name="v", path="./v", identity={"name": "id", "platform": "local"})
        assert isinstance(_s.identity, LocalIdentitySetting)

    def test_identity_accepts_none(self):
        assert LocalVaultSetting(name="v", path="./v", identity=None).identity is None

    def test_identity_rejects_other_platform(self):
        with pytest.raises(ValidationError):
            LocalVaultSetting(name="v", path="./v", identity={"name": "id", "platform": "aliyun"})
        with pytest.raises(ValidationError):
            LocalVaultSetting(name="v", path="./v", identity=AliyunIdentitySetting(name="id"))

    def test_frn(self):
        _s = LocalVaultSetting(name="v", path="./v")
        assert _s.frn == "setting:vault:platform=local:filesystem=local:name=v"

    def test_user_tags_cannot_override_reserved_tags(self):
        _s = LocalVaultSetting(name="v", path="./v", tags={"name": "fake", "filesystem": "fake", "env": "prod"})
        assert _s.tags["name"] == "v"
        assert _s.tags["filesystem"] == "local"
        assert _s.tags["platform"] == "local"
        assert _s.tags["env"] == "prod"


class TestOSSVaultSetting:
    def test_defaults(self):
        _s = OSSVaultSetting(name="v", bucket="b", region="r")
        assert _s.filesystem == AssetFilesystem.OSS
        assert _s.platform == Platform.ALIYUN
        assert _s.prefix == ""
        assert _s.in_vpc is False
        assert _s.identity is None

    def test_requires_bucket_and_region(self):
        with pytest.raises(ValidationError):
            OSSVaultSetting(name="v")
        with pytest.raises(ValidationError):
            OSSVaultSetting(name="v", bucket="b")
        with pytest.raises(ValidationError):
            OSSVaultSetting(name="v", region="r")

    def test_discriminators_are_fixed(self):
        with pytest.raises(ValidationError):
            OSSVaultSetting(name="v", bucket="b", region="r", filesystem="local")
        with pytest.raises(ValidationError):
            OSSVaultSetting(name="v", bucket="b", region="r", platform="local")

    def test_identity_accepts_name(self):
        assert OSSVaultSetting(name="v", bucket="b", region="r", identity="id").identity == "id"

    def test_identity_accepts_nested_setting(self):
        _s = OSSVaultSetting(
            name="v",
            bucket="b",
            region="r",
            identity={"name": "id", "platform": "aliyun"},
        )
        assert isinstance(_s.identity, AliyunIdentitySetting)

    def test_identity_rejects_other_platform(self):
        with pytest.raises(ValidationError):
            OSSVaultSetting(name="v", bucket="b", region="r", identity={"name": "id", "platform": "local"})
        with pytest.raises(ValidationError):
            OSSVaultSetting(name="v", bucket="b", region="r", identity=LocalIdentitySetting(name="id"))

    def test_frn(self):
        _s = OSSVaultSetting(name="v", bucket="b", region="r")
        assert _s.frn == "setting:vault:platform=aliyun:filesystem=oss:name=v"

    def test_user_tags_cannot_override_reserved_tags(self):
        _s = OSSVaultSetting(name="v", bucket="b", region="r", tags={"platform": "fake", "env": "prod"})
        assert _s.tags["platform"] == "aliyun"
        assert _s.tags["env"] == "prod"
