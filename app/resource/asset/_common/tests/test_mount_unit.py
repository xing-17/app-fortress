from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.resource.asset._common._mount import DRAMount


def _file_kwargs(**overrides):
    _kwargs = {
        "scheme": "file",
        "pattern": "/data/ds/*",
        "scope": "/data/ds/",
    }
    _kwargs.update(overrides)
    return _kwargs


def _s3_kwargs(**overrides):
    _kwargs = {
        "scheme": "s3",
        "pattern": "s3://bkt/ds/*",
        "scope": "s3://bkt/ds/",
        "endpoint": "oss-cn-hangzhou.aliyuncs.com",
        "region": "cn-hangzhou",
        "url_style": "vhost",
        "key_id": "AKID",
        "secret": "topsecret",
        "session_token": "sts-token",
    }
    _kwargs.update(overrides)
    return _kwargs


class TestDRAMountFile:
    def test_minimal_file_mount_is_valid(self):
        mount = DRAMount(**_file_kwargs())
        assert mount.scheme == "file"
        assert mount.partitions == []
        assert mount.use_ssl is True

    def test_scheme_defaults_to_file(self):
        mount = DRAMount(pattern="/data/ds/*", scope="/data/ds/")
        assert mount.scheme == "file"

    @pytest.mark.parametrize("field", ["endpoint", "region"])
    def test_file_rejects_remote_fields(self, field):
        with pytest.raises(ValidationError):
            DRAMount(**_file_kwargs(**{field: "x"}))

    def test_file_rejects_url_style(self):
        with pytest.raises(ValidationError):
            DRAMount(**_file_kwargs(url_style="vhost"))

    @pytest.mark.parametrize("field", ["key_id", "secret", "session_token"])
    def test_file_rejects_credentials(self, field):
        with pytest.raises(ValidationError):
            DRAMount(**_file_kwargs(**{field: "x"}))


class TestDRAMountS3:
    def test_full_s3_mount_is_valid(self):
        mount = DRAMount(**_s3_kwargs())
        assert mount.scheme == "s3"
        assert mount.endpoint == "oss-cn-hangzhou.aliyuncs.com"
        assert mount.url_style == "vhost"

    @pytest.mark.parametrize("field", ["endpoint", "region", "url_style"])
    def test_s3_requires_remote_fields(self, field):
        with pytest.raises(ValidationError):
            DRAMount(**_s3_kwargs(**{field: None}))

    def test_s3_without_credentials_is_valid(self):
        mount = DRAMount(**_s3_kwargs(key_id=None, secret=None, session_token=None))
        assert mount.key_id is None
        assert mount.secret is None

    def test_key_id_without_secret_is_rejected(self):
        with pytest.raises(ValidationError):
            DRAMount(**_s3_kwargs(secret=None, session_token=None))

    def test_secret_without_key_id_is_rejected(self):
        with pytest.raises(ValidationError):
            DRAMount(**_s3_kwargs(key_id=None, session_token=None))

    def test_session_token_without_key_id_is_rejected(self):
        with pytest.raises(ValidationError):
            DRAMount(**_s3_kwargs(key_id=None, secret=None))

    def test_invalid_url_style_is_rejected(self):
        with pytest.raises(ValidationError):
            DRAMount(**_s3_kwargs(url_style="other"))

    def test_invalid_scheme_is_rejected(self):
        with pytest.raises(ValidationError):
            DRAMount(**_s3_kwargs(scheme="http"))


class TestDRAMountLocation:
    def test_scope_must_end_with_slash(self):
        with pytest.raises(ValidationError):
            DRAMount(**_file_kwargs(scope="/data/ds"))

    @pytest.mark.parametrize("char", ["*", "?", "["])
    def test_scope_rejects_glob_characters(self, char):
        _scope = f"/data/{char}/"
        with pytest.raises(ValidationError):
            DRAMount(**_file_kwargs(scope=_scope, pattern=f"{_scope}*"))

    def test_pattern_must_be_inside_scope(self):
        with pytest.raises(ValidationError):
            DRAMount(**_file_kwargs(pattern="/other/ds/*"))

    def test_sibling_prefix_is_not_inside_scope(self):
        # "/data/ds2/x" shares the text "/data/ds" but not the directory "/data/ds/"
        with pytest.raises(ValidationError):
            DRAMount(**_file_kwargs(pattern="/data/ds2/*"))

    def test_pattern_may_contain_glob_characters(self):
        mount = DRAMount(**_file_kwargs(pattern="/data/ds/year=*/*.parquet"))
        assert mount.pattern == "/data/ds/year=*/*.parquet"


class TestDRAMountModel:
    def test_is_frozen(self):
        mount = DRAMount(**_file_kwargs())
        with pytest.raises(ValidationError):
            mount.pattern = "/data/ds/other"

    def test_extra_fields_are_forbidden(self):
        with pytest.raises(ValidationError):
            DRAMount(**_file_kwargs(unknown="x"))

    def test_partitions_are_kept(self):
        mount = DRAMount(**_file_kwargs(partitions=["year", "month"]))
        assert mount.partitions == ["year", "month"]


class TestDRAMountSecretMasking:
    def test_repr_does_not_contain_secret_values(self):
        _text = repr(DRAMount(**_s3_kwargs()))
        assert "topsecret" not in _text
        assert "sts-token" not in _text

    def test_export_does_not_contain_secret_values(self):
        _text = str(DRAMount(**_s3_kwargs()).export())
        assert "topsecret" not in _text
        assert "sts-token" not in _text

    def test_describe_does_not_contain_secret_values(self):
        _text = DRAMount(**_s3_kwargs()).describe()
        assert "topsecret" not in _text
        assert "sts-token" not in _text

    def test_secret_value_is_still_retrievable(self):
        mount = DRAMount(**_s3_kwargs())
        assert mount.secret.get_secret_value() == "topsecret"
        assert mount.session_token.get_secret_value() == "sts-token"
