from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.resource._client.oss.client import OSSClient
from app.resource._global.identities import GlobalIdentities
from app.resource.asset.oss.asset import OSSAsset
from app.resource.asset.oss.assetfile import OSSAssetfile
from app.resource.identity.aliyun.identity import AliyunIdentity
from app.resource.identity.aliyun.identitysecret import AliyunIdentitySecret
from app.resource.identity.local.identity import LocalIdentity
from app.service.node.dra.mount import DRAMount


@pytest.fixture(autouse=True)
def _reset_global_identities():
    # GlobalIdentities holds process-wide singleton state; isolate tests from each other.
    GlobalIdentities.reset()
    yield
    GlobalIdentities.reset()


def _fake_client(objects: list[dict] | None = None) -> MagicMock:
    _client = MagicMock()
    _client.list_objects.return_value = objects or []
    return _client


class TestOSSAssetInit:
    def test_missing_bucket_raises_validation_error(self, monkeypatch):
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client())
        with pytest.raises(ValidationError):
            OSSAsset(region="cn-hangzhou", _authorized=True)

    def test_missing_region_raises_validation_error(self, monkeypatch):
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client())
        with pytest.raises(ValidationError):
            OSSAsset(bucket="my-bucket", _authorized=True)

    def test_missing_authorized_raises_value_error(self):
        with pytest.raises(ValueError):
            OSSAsset(bucket="my-bucket", region="cn-hangzhou")

    def test_filesystem_and_platform_are_fixed(self):
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", _authorized=True)
        assert asset.filesystem == AssetFilesystem.OSS
        assert asset.platform == Platform.ALIYUN

    def test_default_identity_is_aliyun_identity_default(self):
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", _authorized=True)
        assert asset.identity.name == AliyunIdentity.default().name

    def test_default_filekind_is_object(self):
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", _authorized=True)
        assert asset.filekind == AssetFileKind.OBJECT

    def test_default_partitions_is_empty_list(self):
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", _authorized=True)
        assert asset.partitions == []

    def test_default_prefix_is_empty_string(self):
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", _authorized=True)
        assert asset.prefix == ""


class TestOSSAssetDerivePrefix:
    def test_trailing_slashes_are_stripped(self):
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", prefix="my/prefix/", _authorized=True)
        assert asset.prefix == "my/prefix"


class TestOSSAssetDeriveIdentity:
    def test_resolves_named_identity(self):
        _identity = AliyunIdentity(name="registered_aliyun_identity")
        GlobalIdentities.identities = {"registered_aliyun_identity": _identity}
        asset = OSSAsset(
            bucket="my-bucket",
            region="cn-hangzhou",
            identity="registered_aliyun_identity",
            _authorized=True,
        )
        assert asset.identity is _identity

    def test_platform_mismatch_raises_value_error(self):
        _local_identity = LocalIdentity(name="a_local_identity")
        GlobalIdentities.identities = {"a_local_identity": _local_identity}
        with pytest.raises(ValueError):
            OSSAsset(bucket="my-bucket", region="cn-hangzhou", identity="a_local_identity", _authorized=True)


class TestOSSAssetUriFrnAndName:
    def test_uri_returns_oss_scheme_with_bucket_and_prefix(self):
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", prefix="prices", _authorized=True)
        assert asset.uri == "oss://my-bucket/prices"

    def test_frn_includes_platform_bucket_and_prefix(self):
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", prefix="prices", _authorized=True)
        assert asset.frn == f"asset:platform={Platform.ALIYUN}:bucket=my-bucket:prefix=prices"

    def test_name_returns_last_prefix_segment(self):
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", prefix="a/b/prices", _authorized=True)
        assert asset.name == "prices"


class TestOSSAssetFullPattern:
    def test_without_partitions_has_no_partition_segment(self):
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", prefix="prices", _authorized=True)
        assert asset.full_pattern == "*prices/*"

    def test_with_partitions_includes_partition_segment(self):
        asset = OSSAsset(
            bucket="my-bucket",
            region="cn-hangzhou",
            prefix="prices",
            partitions=["year", "month"],
            _authorized=True,
        )
        assert asset.full_pattern == "*prices/year=*/month=*/*"

    def test_with_filekind_restricts_object_segment(self):
        asset = OSSAsset(
            bucket="my-bucket",
            region="cn-hangzhou",
            prefix="prices",
            filekind=AssetFileKind.PARQUET,
            _authorized=True,
        )
        assert asset.full_pattern == "*prices/*.parquet"


class TestOSSAssetGetDraMount:
    @pytest.fixture(autouse=True)
    def _fake_secret(self, monkeypatch):
        monkeypatch.setattr(
            AliyunIdentity,
            "as_secret",
            lambda self: AliyunIdentitySecret(
                access_key_id="AKID",
                access_key_secret="topsecret",
                security_token="sts-token",
            ),
        )

    def test_is_an_s3_mount_with_vhost_style(self):
        mount = OSSAsset(bucket="my-bucket", region="cn-hangzhou", prefix="prices", _authorized=True).get_dra_mount()
        assert isinstance(mount, DRAMount)
        assert mount.scheme == "s3"
        assert mount.url_style == "vhost"
        assert mount.region == "cn-hangzhou"

    def test_scope_and_pattern_use_s3_scheme_not_oss(self):
        mount = OSSAsset(bucket="my-bucket", region="cn-hangzhou", prefix="prices", _authorized=True).get_dra_mount()
        assert mount.scope == "s3://my-bucket/prices/"
        assert mount.pattern == "s3://my-bucket/prices/*"

    def test_empty_prefix_scopes_the_whole_bucket(self):
        mount = OSSAsset(bucket="my-bucket", region="cn-hangzhou", _authorized=True).get_dra_mount()
        assert mount.scope == "s3://my-bucket/"
        assert mount.pattern == "s3://my-bucket/*"

    def test_partitions_and_filekind_shape_the_pattern(self):
        asset = OSSAsset(
            bucket="my-bucket",
            region="cn-hangzhou",
            prefix="prices",
            partitions=["year", "month"],
            filekind=AssetFileKind.PARQUET,
            _authorized=True,
        )
        mount = asset.get_dra_mount()
        assert mount.pattern == "s3://my-bucket/prices/year=*/month=*/*.parquet"
        assert mount.partitions == ["year", "month"]

    def test_public_endpoint_when_not_in_vpc(self):
        mount = OSSAsset(bucket="my-bucket", region="cn-hangzhou", _authorized=True).get_dra_mount()
        assert mount.endpoint == "oss-cn-hangzhou.aliyuncs.com"

    def test_internal_endpoint_when_in_vpc(self):
        mount = OSSAsset(bucket="my-bucket", region="cn-hangzhou", in_vpc=True, _authorized=True).get_dra_mount()
        assert mount.endpoint == "oss-cn-hangzhou-internal.aliyuncs.com"

    def test_credentials_come_from_identity_secret(self):
        mount = OSSAsset(bucket="my-bucket", region="cn-hangzhou", _authorized=True).get_dra_mount()
        assert mount.key_id == "AKID"
        assert mount.secret.get_secret_value() == "topsecret"
        assert mount.session_token.get_secret_value() == "sts-token"

    def test_long_lived_key_has_no_session_token(self, monkeypatch):
        monkeypatch.setattr(
            AliyunIdentity,
            "as_secret",
            lambda self: AliyunIdentitySecret(access_key_id="AKID", access_key_secret="topsecret"),
        )
        mount = OSSAsset(bucket="my-bucket", region="cn-hangzhou", _authorized=True).get_dra_mount()
        assert mount.session_token is None

    def test_secret_is_fetched_on_every_call(self, monkeypatch):
        _calls = []

        def _as_secret(self):
            _calls.append(1)
            return AliyunIdentitySecret(access_key_id=f"AKID{len(_calls)}", access_key_secret="s")

        monkeypatch.setattr(AliyunIdentity, "as_secret", _as_secret)
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", _authorized=True)
        assert asset.get_dra_mount().key_id == "AKID1"
        assert asset.get_dra_mount().key_id == "AKID2"

    def test_mount_does_not_expose_secret_in_describe(self):
        mount = OSSAsset(bucket="my-bucket", region="cn-hangzhou", _authorized=True).get_dra_mount()
        assert "topsecret" not in mount.describe()
        assert "sts-token" not in mount.describe()

    def test_does_not_create_an_oss_client(self, monkeypatch):
        def _boom(**kwargs):
            raise AssertionError("get_dra_mount must not build an OSS client")

        monkeypatch.setattr(OSSClient, "get_client", _boom)
        OSSAsset(bucket="my-bucket", region="cn-hangzhou", _authorized=True).get_dra_mount()


class TestOSSAssetListObjects:
    def test_empty_bucket_returns_empty_list(self, monkeypatch):
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client())
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", prefix="prices", _authorized=True)
        assert asset.list_objects() == []

    def test_builds_assetfile_for_each_object(self, monkeypatch):
        _objects = [
            {"key": "prices/a.csv", "size": 3, "last_modified": 100.0, "etag": "e1"},
            {"key": "prices/b.csv", "size": 4, "last_modified": 200.0, "etag": "e2"},
        ]
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client(_objects))
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", prefix="prices", _authorized=True)
        _files = asset.list_objects()
        assert len(_files) == 2
        assert all(isinstance(f, OSSAssetfile) for f in _files)
        assert {f.name for f in _files} == {"a.csv", "b.csv"}

    def test_assetfile_inherits_asset_identity_and_tags(self, monkeypatch):
        _objects = [{"key": "prices/a.csv", "size": 1, "last_modified": 100.0}]
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client(_objects))
        asset = OSSAsset(
            bucket="my-bucket",
            region="cn-hangzhou",
            prefix="prices",
            tags={"env": "prod"},
            _authorized=True,
        )
        _file = asset.list_objects()[0]
        assert _file.identity is asset.identity
        assert _file.tags["env"] == "prod"

    def test_assetfile_size_and_modified_at_come_from_metadata(self, monkeypatch):
        _objects = [{"key": "prices/a.csv", "size": 5, "last_modified": 123.0}]
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client(_objects))
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", prefix="prices", _authorized=True)
        _file = asset.list_objects()[0]
        assert _file.size == 5
        assert _file.modified_at == 123.0

    def test_metadata_excludes_none_values(self, monkeypatch):
        _objects = [{"key": "prices/a.csv", "size": 1, "last_modified": 100.0, "etag": None}]
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client(_objects))
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", prefix="prices", _authorized=True)
        _file = asset.list_objects()[0]
        assert all(v is not None for v in _file.metadata.values())

    def test_forwards_prefix_pattern_since_until_recursive_to_client(self, monkeypatch):
        _client = _fake_client()
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _client)
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", prefix="prices", _authorized=True)
        asset.list_objects(pattern="*.csv", since=1.0, until=2.0, recursive=False)
        _client.list_objects.assert_called_once_with(
            prefix="prices/",
            pattern="*.csv",
            since=1.0,
            until=2.0,
            recursive=False,
        )

    def test_empty_prefix_lists_from_bucket_root(self, monkeypatch):
        _client = _fake_client()
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _client)
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", _authorized=True)
        asset.list_objects()
        assert _client.list_objects.call_args.kwargs["prefix"] == ""

    def test_partitions_are_derived_relative_to_asset_prefix(self, monkeypatch):
        _objects = [{"key": "vault/prices/year=2024/month=01/a.csv", "size": 1, "last_modified": 100.0}]
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client(_objects))
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", prefix="vault/prices", _authorized=True)
        assert asset.list_objects()[0].partitions == {"year": "2024", "month": "01"}

    def test_partition_like_segments_above_prefix_are_ignored(self, monkeypatch):
        _objects = [{"key": "env=prod/prices/year=2024/a.csv", "size": 1, "last_modified": 100.0}]
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client(_objects))
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", prefix="env=prod/prices", _authorized=True)
        assert asset.list_objects()[0].partitions == {"year": "2024"}

    def test_object_directly_under_prefix_has_no_partitions(self, monkeypatch):
        _objects = [{"key": "prices/a.csv", "size": 1, "last_modified": 100.0}]
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client(_objects))
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", prefix="prices", _authorized=True)
        assert asset.list_objects()[0].partitions == {}


class TestOSSAssetListAssetfiles:
    def test_uses_full_pattern_and_matches_files(self, monkeypatch):
        _client = _fake_client([{"key": "prices/a.csv", "size": 1, "last_modified": 100.0}])
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _client)
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", prefix="prices", _authorized=True)
        _files = asset.list_assetfiles()
        assert len(_files) == 1
        assert _files[0].name == "a.csv"
        _client.list_objects.assert_called_once_with(
            prefix="prices/",
            pattern=asset.full_pattern,
            since=None,
            until=None,
            recursive=True,
        )


class TestOSSAssetAssetfile:
    def test_creates_assetfile_without_partitions(self, monkeypatch):
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client())
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", prefix="prices", _authorized=True)
        _assetfile = asset.assetfile("data.csv")
        assert isinstance(_assetfile, OSSAssetfile)
        assert _assetfile.key == "prices/data.csv"

    def test_creates_assetfile_with_partitions(self, monkeypatch):
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client())
        asset = OSSAsset(
            bucket="my-bucket",
            region="cn-hangzhou",
            prefix="prices",
            partitions=["year", "month"],
            _authorized=True,
        )
        _assetfile = asset.assetfile("data.csv", partitions={"year": "2024", "month": "01"})
        assert _assetfile.key == "prices/year=2024/month=01/data.csv"
        assert _assetfile.partitions == {"year": "2024", "month": "01"}

    def test_mismatched_partition_keys_raise_value_error(self, monkeypatch):
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client())
        asset = OSSAsset(
            bucket="my-bucket", region="cn-hangzhou", prefix="prices", partitions=["year"], _authorized=True
        )
        with pytest.raises(ValueError):
            asset.assetfile("data.csv", partitions={"month": "01"})

    def test_missing_required_partitions_raise_value_error(self, monkeypatch):
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client())
        asset = OSSAsset(
            bucket="my-bucket", region="cn-hangzhou", prefix="prices", partitions=["year"], _authorized=True
        )
        with pytest.raises(ValueError):
            asset.assetfile("data.csv")

    def test_assetfile_inherits_asset_identity_and_tags(self, monkeypatch):
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client())
        asset = OSSAsset(
            bucket="my-bucket", region="cn-hangzhou", prefix="prices", tags={"env": "prod"}, _authorized=True
        )
        _assetfile = asset.assetfile("data.csv")
        assert _assetfile.identity is asset.identity
        assert _assetfile.tags["env"] == "prod"

    def test_filekind_mismatch_raises_value_error(self, monkeypatch):
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client())
        asset = OSSAsset(
            bucket="my-bucket", region="cn-hangzhou", prefix="prices", filekind=AssetFileKind.PARQUET, _authorized=True
        )
        with pytest.raises(ValueError):
            asset.assetfile("data.csv")

    def test_filekind_match_succeeds(self, monkeypatch):
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client())
        asset = OSSAsset(
            bucket="my-bucket", region="cn-hangzhou", prefix="prices", filekind=AssetFileKind.PARQUET, _authorized=True
        )
        _assetfile = asset.assetfile("data.parquet")
        assert _assetfile.filekind == AssetFileKind.PARQUET
