from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from app.internal.constant.aliyunidentitytype import AliyunIdentityType
from app.internal.constant.platform import Platform
from app.setting import (
    AliyunIdentitySetting,
    LocalIdentitySetting,
    UnionIdentitySetting,
)


class TestUnionIdentitySetting:
    def test_dispatches_on_platform(self):
        _adapter = TypeAdapter(UnionIdentitySetting)
        assert isinstance(_adapter.validate_python({"name": "a", "platform": "local"}), LocalIdentitySetting)
        assert isinstance(_adapter.validate_python({"name": "a", "platform": "aliyun"}), AliyunIdentitySetting)

    def test_unknown_platform_is_rejected(self):
        with pytest.raises(ValidationError):
            TypeAdapter(UnionIdentitySetting).validate_python({"name": "a", "platform": "unknown"})

    def test_missing_platform_is_rejected(self):
        with pytest.raises(ValidationError):
            TypeAdapter(UnionIdentitySetting).validate_python({"name": "a"})


class TestLocalIdentitySetting:
    def test_name_is_required(self):
        with pytest.raises(ValidationError):
            LocalIdentitySetting()

    def test_platform_is_fixed(self):
        assert LocalIdentitySetting(name="x").platform == Platform.LOCAL
        with pytest.raises(ValidationError):
            LocalIdentitySetting(name="x", platform="aliyun")

    def test_frn(self):
        assert LocalIdentitySetting(name="x").frn == "setting:identity:platform=local:name=x"

    def test_user_tags_cannot_override_reserved_tags(self):
        _s = LocalIdentitySetting(name="x", tags={"name": "fake", "platform": "fake", "env": "prod"})
        assert _s.tags["name"] == "x"
        assert _s.tags["platform"] == "local"
        assert _s.tags["env"] == "prod"


class TestAliyunIdentitySetting:
    def test_defaults(self):
        _s = AliyunIdentitySetting(name="x")
        assert _s.platform == Platform.ALIYUN
        assert _s.type == AliyunIdentityType.CHAIN
        assert _s.access_key_id is None
        assert _s.access_key_secret is None
        assert _s.region is None

    def test_credentials_and_osenv_fields(self):
        _s = AliyunIdentitySetting(
            name="x",
            type="ak",
            access_key_id="id",
            osenv_access_key_secret="SECRET_ENV",
            osenv_region="REGION_ENV",
        )
        assert _s.type == AliyunIdentityType.AK
        assert _s.access_key_id == "id"
        assert _s.osenv_access_key_secret == "SECRET_ENV"
        assert _s.osenv_region == "REGION_ENV"

    def test_invalid_type_is_rejected(self):
        with pytest.raises(ValidationError):
            AliyunIdentitySetting(name="x", type="bogus")

    def test_platform_is_fixed(self):
        with pytest.raises(ValidationError):
            AliyunIdentitySetting(name="x", platform="local")

    def test_frn(self):
        assert AliyunIdentitySetting(name="x").frn == "setting:identity:platform=aliyun:name=x"

    def test_none_for_defaulted_field_falls_back_to_default(self):
        assert AliyunIdentitySetting(name="x", type=None).type == AliyunIdentityType.CHAIN

    def test_export_round_trip(self):
        _s = AliyunIdentitySetting(name="x", type="ak", access_key_id="id")
        assert AliyunIdentitySetting(**_s.export()).export() == _s.export()
