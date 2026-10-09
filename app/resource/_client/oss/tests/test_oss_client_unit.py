from __future__ import annotations

import io
import threading
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from alibabacloud_credentials.models import CredentialModel
from alibabacloud_oss_v2.exceptions import OperationError, ServiceError
from alibabacloud_oss_v2.models import (
    CommonPrefix,
    GetObjectResult,
    HeadObjectResult,
    ListObjectsV2Result,
    ObjectProperties,
    Owner,
    PutObjectResult,
)

from app.resource._client.oss import client as oss_client_module
from app.resource._client.oss.client import OSSClient
from app.resource.identity.aliyun.identity import AliyunIdentity


def _make_identity(name: str = "my-identity") -> AliyunIdentity:
    return AliyunIdentity(name=name)


def _make_page(
    *,
    contents: list[ObjectProperties] | None = None,
    common_prefixes: list[CommonPrefix] | None = None,
) -> ListObjectsV2Result:
    return ListObjectsV2Result(contents=contents, common_prefixes=common_prefixes)


def _not_found_error(name: str) -> OperationError:
    _service_error = ServiceError(
        status_code=404,
        code="NoSuchKey",
        request_id="id-1234",
        message="The specified key does not exist.",
        ec=None,
        timestamp=None,
        request_target=None,
    )
    return OperationError(name=name, error=_service_error)


def _other_service_error(name: str, code: str = "AccessDenied") -> OperationError:
    _service_error = ServiceError(
        status_code=403,
        code=code,
        request_id="id-5678",
        message="Access denied.",
        ec=None,
        timestamp=None,
        request_target=None,
    )
    return OperationError(name=name, error=_service_error)


@pytest.fixture(autouse=True)
def _reset_client_cache():
    # OSSClient._cache holds process-wide singleton state; isolate tests from each other.
    OSSClient.reset()
    yield
    OSSClient.reset()


class TestOSSClientInit:
    def test_stores_bucket_region_identity(self):
        identity = _make_identity()
        client = OSSClient(bucket="my-bucket", region="cn-hangzhou", identity=identity)
        assert client.bucket == "my-bucket"
        assert client.region == "cn-hangzhou"
        assert client.identity is identity

    def test_default_in_vpc_is_false(self):
        client = OSSClient(bucket="my-bucket", region="cn-hangzhou", identity=_make_identity())
        assert client.in_vpc is False

    def test_public_endpoint_when_not_in_vpc(self):
        client = OSSClient(bucket="my-bucket", region="cn-hangzhou", identity=_make_identity(), in_vpc=False)
        assert client.endpoint == "oss-cn-hangzhou.aliyuncs.com"

    def test_internal_endpoint_when_in_vpc(self):
        client = OSSClient(bucket="my-bucket", region="cn-hangzhou", identity=_make_identity(), in_vpc=True)
        assert client.endpoint == "oss-cn-hangzhou-internal.aliyuncs.com"

    def test_lazy_client_is_none_until_accessed(self):
        client = OSSClient(bucket="my-bucket", region="cn-hangzhou", identity=_make_identity())
        assert client._client is None


class TestOSSClientGetClient:
    def test_returns_new_instance_on_cache_miss(self):
        identity = _make_identity()
        result = OSSClient.get_client(bucket="my-bucket", region="cn-hangzhou", identity=identity)
        assert isinstance(result, OSSClient)
        assert result.bucket == "my-bucket"

    def test_returns_same_instance_on_cache_hit(self):
        identity = _make_identity()
        first = OSSClient.get_client(bucket="my-bucket", region="cn-hangzhou", identity=identity)
        second = OSSClient.get_client(bucket="my-bucket", region="cn-hangzhou", identity=identity)
        assert first is second

    def test_different_bucket_yields_different_instance(self):
        identity = _make_identity()
        first = OSSClient.get_client(bucket="bucket-a", region="cn-hangzhou", identity=identity)
        second = OSSClient.get_client(bucket="bucket-b", region="cn-hangzhou", identity=identity)
        assert first is not second

    def test_different_identity_yields_different_instance(self):
        first = OSSClient.get_client(bucket="my-bucket", region="cn-hangzhou", identity=_make_identity("identity-a"))
        second = OSSClient.get_client(bucket="my-bucket", region="cn-hangzhou", identity=_make_identity("identity-b"))
        assert first is not second

    def test_different_in_vpc_yields_different_instance(self):
        identity = _make_identity()
        public = OSSClient.get_client(bucket="my-bucket", region="cn-hangzhou", identity=identity, in_vpc=False)
        internal = OSSClient.get_client(bucket="my-bucket", region="cn-hangzhou", identity=identity, in_vpc=True)
        assert public is not internal
        assert public.endpoint == "oss-cn-hangzhou.aliyuncs.com"
        assert internal.endpoint == "oss-cn-hangzhou-internal.aliyuncs.com"

    def test_in_vpc_is_passed_through_to_new_instance(self):
        result = OSSClient.get_client(bucket="my-bucket", region="cn-hangzhou", identity=_make_identity(), in_vpc=True)
        assert result.in_vpc is True
        assert result.endpoint == "oss-cn-hangzhou-internal.aliyuncs.com"

    def test_cache_hit_moves_entry_to_most_recently_used(self):
        identity = _make_identity()
        first = OSSClient.get_client(bucket="bucket-a", region="cn-hangzhou", identity=identity)
        OSSClient.get_client(bucket="bucket-b", region="cn-hangzhou", identity=identity)
        # Touch "bucket-a" again so it is no longer the least-recently-used entry.
        OSSClient.get_client(bucket="bucket-a", region="cn-hangzhou", identity=identity)
        assert list(OSSClient._cache.values())[-1] is first

    def test_evicts_least_recently_used_entry_beyond_max_size(self):
        identity = _make_identity()
        OSSClient._cache_max_size = 2
        first = OSSClient.get_client(bucket="bucket-a", region="cn-hangzhou", identity=identity)
        OSSClient.get_client(bucket="bucket-b", region="cn-hangzhou", identity=identity)
        OSSClient.get_client(bucket="bucket-c", region="cn-hangzhou", identity=identity)
        assert len(OSSClient._cache) == 2
        assert first not in OSSClient._cache.values()

    def test_reset_clears_cache(self):
        OSSClient.get_client(bucket="my-bucket", region="cn-hangzhou", identity=_make_identity())
        OSSClient.reset()
        assert len(OSSClient._cache) == 0

    def test_is_thread_safe_for_concurrent_cache_misses(self):
        identity = _make_identity()
        _results: list[OSSClient] = []
        _lock = threading.Lock()

        def _get():
            _result = OSSClient.get_client(bucket="my-bucket", region="cn-hangzhou", identity=identity)
            with _lock:
                _results.append(_result)

        _threads = [threading.Thread(target=_get) for _ in range(8)]
        for _t in _threads:
            _t.start()
        for _t in _threads:
            _t.join()

        assert len(_results) == 8
        assert all(_r is _results[0] for _r in _results)


class TestOSSClientClientProperty:
    def test_builds_client_once_and_caches_it(self, monkeypatch):
        _mock_client_cls = MagicMock()
        monkeypatch.setattr(oss_client_module, "OSSTeaClient", _mock_client_cls)
        monkeypatch.setattr(
            AliyunIdentity,
            "get_credential",
            MagicMock(return_value=CredentialModel(access_key_id="AKIDEXAMPLE", access_key_secret="secretvalue")),
        )
        client = OSSClient(bucket="my-bucket", region="cn-hangzhou", identity=_make_identity())

        first = client.client
        second = client.client

        assert first is second
        _mock_client_cls.assert_called_once()

    def test_config_region_and_endpoint_are_set(self, monkeypatch):
        _captured_cfg = {}

        def _fake_oss_tea_client(cfg):
            _captured_cfg["cfg"] = cfg
            return MagicMock()

        monkeypatch.setattr(oss_client_module, "OSSTeaClient", _fake_oss_tea_client)
        monkeypatch.setattr(
            AliyunIdentity,
            "get_credential",
            MagicMock(return_value=CredentialModel(access_key_id="AKIDEXAMPLE", access_key_secret="secretvalue")),
        )
        client = OSSClient(bucket="my-bucket", region="cn-hangzhou", identity=_make_identity(), in_vpc=True)

        _ = client.client

        assert _captured_cfg["cfg"].region == "cn-hangzhou"
        assert _captured_cfg["cfg"].endpoint == "oss-cn-hangzhou-internal.aliyuncs.com"

    def test_credentials_provider_fetches_fresh_credential_on_every_call(self, monkeypatch):
        # This is the fix for expired STS/RAM-role tokens: credentials must be
        # re-resolved per request instead of snapshotted once at client construction.
        _captured_cfg = {}

        def _fake_oss_tea_client(cfg):
            _captured_cfg["cfg"] = cfg
            return MagicMock()

        monkeypatch.setattr(oss_client_module, "OSSTeaClient", _fake_oss_tea_client)
        _get_credential = MagicMock(
            side_effect=[
                CredentialModel(access_key_id="AK-1", access_key_secret="SK-1", security_token="TOKEN-1"),
                CredentialModel(access_key_id="AK-2", access_key_secret="SK-2", security_token="TOKEN-2"),
            ]
        )
        monkeypatch.setattr(AliyunIdentity, "get_credential", _get_credential)
        client = OSSClient(bucket="my-bucket", region="cn-hangzhou", identity=_make_identity())

        _ = client.client
        _provider = _captured_cfg["cfg"].credentials_provider
        _first = _provider.get_credentials()
        _second = _provider.get_credentials()

        assert _get_credential.call_count == 2
        assert _first.access_key_id == "AK-1"
        assert _first.security_token == "TOKEN-1"
        assert _second.access_key_id == "AK-2"
        assert _second.security_token == "TOKEN-2"

    def test_is_thread_safe_double_checked_locking(self, monkeypatch):
        monkeypatch.setattr(oss_client_module, "OSSTeaClient", MagicMock(side_effect=lambda cfg: MagicMock()))
        monkeypatch.setattr(
            AliyunIdentity,
            "get_credential",
            MagicMock(return_value=CredentialModel(access_key_id="AKIDEXAMPLE", access_key_secret="secretvalue")),
        )
        client = OSSClient(bucket="my-bucket", region="cn-hangzhou", identity=_make_identity())
        _results: list[object] = []
        _lock = threading.Lock()

        def _access():
            _result = client.client
            with _lock:
                _results.append(_result)

        _threads = [threading.Thread(target=_access) for _ in range(8)]
        for _t in _threads:
            _t.start()
        for _t in _threads:
            _t.join()

        assert all(_r is _results[0] for _r in _results)


class TestOSSClientWriteBytes:
    def test_calls_put_object_with_bucket_key_and_body(self):
        client = OSSClient(bucket="my-bucket", region="cn-hangzhou", identity=_make_identity())
        _mock_client = MagicMock(put_object=MagicMock(return_value=PutObjectResult()))
        client._client = _mock_client

        client.write_bytes("path/to/object.bin", b"hello world")

        _mock_client.put_object.assert_called_once()
        _request = _mock_client.put_object.call_args.args[0]
        assert _request.bucket == "my-bucket"
        assert _request.key == "path/to/object.bin"
        assert _request.body.read() == b"hello world"


class TestOSSClientReadBytes:
    def test_returns_bytes_from_response_body(self):
        client = OSSClient(bucket="my-bucket", region="cn-hangzhou", identity=_make_identity())
        _response = GetObjectResult(body=io.BytesIO(b"file contents"))
        client._client = MagicMock(get_object=MagicMock(return_value=_response))

        result = client.read_bytes("path/to/object.bin")

        assert result == b"file contents"

    def test_missing_key_raises_file_not_found_error(self):
        client = OSSClient(bucket="my-bucket", region="cn-hangzhou", identity=_make_identity())
        client._client = MagicMock(get_object=MagicMock(side_effect=_not_found_error("GetObject")))

        with pytest.raises(FileNotFoundError):
            client.read_bytes("missing-key")

    def test_other_service_errors_propagate_unchanged(self):
        client = OSSClient(bucket="my-bucket", region="cn-hangzhou", identity=_make_identity())
        _error = _other_service_error("GetObject")
        client._client = MagicMock(get_object=MagicMock(side_effect=_error))

        with pytest.raises(OperationError) as _exc_info:
            client.read_bytes("forbidden-key")
        assert _exc_info.value is _error


class TestOSSClientGetObject:
    def test_returns_expected_metadata_fields(self):
        client = OSSClient(bucket="my-bucket", region="cn-hangzhou", identity=_make_identity())
        _lmdt = datetime(2026, 1, 1, tzinfo=timezone.utc)
        _response = HeadObjectResult(
            etag="etag-value",
            last_modified=_lmdt,
            content_length=1234,
            storage_class="Standard",
        )
        client._client = MagicMock(head_object=MagicMock(return_value=_response))

        result = client.get_object("path/to/object.bin")

        assert result == {
            "bucket": "my-bucket",
            "key": "path/to/object.bin",
            "etag": "etag-value",
            "last_modified": _lmdt.timestamp(),
            "size": 1234,
            "storage_class": "Standard",
        }

    def test_does_not_raise_attribute_error_for_missing_owner(self):
        # Regression test: HeadObjectResult has no `owner` attribute at all
        # (unlike ListObjectsV2's ObjectProperties), accessing it used to raise AttributeError.
        client = OSSClient(bucket="my-bucket", region="cn-hangzhou", identity=_make_identity())
        client._client = MagicMock(head_object=MagicMock(return_value=HeadObjectResult()))

        result = client.get_object("path/to/object.bin")

        assert "owner" not in result

    def test_none_last_modified_is_kept_as_none(self):
        client = OSSClient(bucket="my-bucket", region="cn-hangzhou", identity=_make_identity())
        client._client = MagicMock(head_object=MagicMock(return_value=HeadObjectResult(last_modified=None)))

        result = client.get_object("path/to/object.bin")

        assert result["last_modified"] is None

    def test_missing_key_raises_file_not_found_error(self):
        client = OSSClient(bucket="my-bucket", region="cn-hangzhou", identity=_make_identity())
        client._client = MagicMock(head_object=MagicMock(side_effect=_not_found_error("HeadObject")))

        with pytest.raises(FileNotFoundError):
            client.get_object("missing-key")

    def test_other_service_errors_propagate_unchanged(self):
        client = OSSClient(bucket="my-bucket", region="cn-hangzhou", identity=_make_identity())
        _error = _other_service_error("HeadObject")
        client._client = MagicMock(head_object=MagicMock(side_effect=_error))

        with pytest.raises(OperationError) as _exc_info:
            client.get_object("forbidden-key")
        assert _exc_info.value is _error


class TestOSSClientListObjects:
    def _client_with_pages(self, *pages: ListObjectsV2Result) -> OSSClient:
        client = OSSClient(bucket="my-bucket", region="cn-hangzhou", identity=_make_identity())
        _paginator = MagicMock(iter_page=MagicMock(return_value=iter(pages)))
        client._client = MagicMock(list_objects_v2_paginator=MagicMock(return_value=_paginator))
        return client

    def test_returns_empty_list_when_no_contents(self):
        client = self._client_with_pages(_make_page(contents=[]))
        assert client.list_objects() == []

    def test_returns_objects_from_single_page(self):
        _owner = Owner(id="1234", display_name="alice")
        _lmdt = datetime(2026, 1, 1, tzinfo=timezone.utc)
        client = self._client_with_pages(
            _make_page(
                contents=[
                    ObjectProperties(
                        key="a.txt",
                        etag="etag-a",
                        last_modified=_lmdt,
                        size=10,
                        storage_class="Standard",
                    )
                ]
            )
        )

        result = client.list_objects()

        assert result == [
            {
                "bucket": "my-bucket",
                "key": "a.txt",
                "etag": "etag-a",
                "last_modified": _lmdt.timestamp(),
                "size": 10,
                "storage_class": "Standard",
            }
        ]

    def test_aggregates_objects_across_multiple_pages(self):
        client = self._client_with_pages(
            _make_page(contents=[ObjectProperties(key="a.txt")]),
            _make_page(contents=[ObjectProperties(key="b.txt")]),
        )

        result = client.list_objects()

        assert [_o["key"] for _o in result] == ["a.txt", "b.txt"]

    def test_results_are_sorted_by_key(self):
        client = self._client_with_pages(
            _make_page(contents=[ObjectProperties(key="c.txt"), ObjectProperties(key="a.txt")]),
            _make_page(contents=[ObjectProperties(key="b.txt")]),
        )

        result = client.list_objects()

        assert [_o["key"] for _o in result] == ["a.txt", "b.txt", "c.txt"]

    def test_pattern_filters_keys(self):
        client = self._client_with_pages(
            _make_page(contents=[ObjectProperties(key="a.txt"), ObjectProperties(key="b.csv")])
        )

        result = client.list_objects(pattern="*.txt")

        assert [_o["key"] for _o in result] == ["a.txt"]

    def test_since_filters_out_older_objects(self):
        _old = datetime(2020, 1, 1, tzinfo=timezone.utc)
        _new = datetime(2026, 1, 1, tzinfo=timezone.utc)
        client = self._client_with_pages(
            _make_page(
                contents=[
                    ObjectProperties(key="old.txt", last_modified=_old),
                    ObjectProperties(key="new.txt", last_modified=_new),
                ]
            )
        )

        result = client.list_objects(since=datetime(2023, 1, 1, tzinfo=timezone.utc))

        assert [_o["key"] for _o in result] == ["new.txt"]

    def test_since_accepts_float_timestamp(self):
        _old = datetime(2020, 1, 1, tzinfo=timezone.utc)
        _new = datetime(2026, 1, 1, tzinfo=timezone.utc)
        client = self._client_with_pages(
            _make_page(
                contents=[
                    ObjectProperties(key="old.txt", last_modified=_old),
                    ObjectProperties(key="new.txt", last_modified=_new),
                ]
            )
        )

        result = client.list_objects(since=datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())

        assert [_o["key"] for _o in result] == ["new.txt"]

    def test_until_filters_out_newer_objects(self):
        _old = datetime(2020, 1, 1, tzinfo=timezone.utc)
        _new = datetime(2026, 1, 1, tzinfo=timezone.utc)
        client = self._client_with_pages(
            _make_page(
                contents=[
                    ObjectProperties(key="old.txt", last_modified=_old),
                    ObjectProperties(key="new.txt", last_modified=_new),
                ]
            )
        )

        result = client.list_objects(until=datetime(2023, 1, 1, tzinfo=timezone.utc))

        assert [_o["key"] for _o in result] == ["old.txt"]

    def test_missing_last_modified_is_not_filtered_out(self):
        client = self._client_with_pages(_make_page(contents=[ObjectProperties(key="a.txt", last_modified=None)]))

        result = client.list_objects(since=datetime(2020, 1, 1, tzinfo=timezone.utc))

        assert [_o["key"] for _o in result] == ["a.txt"]
        assert result[0]["last_modified"] is None

    def test_recursive_true_uses_no_delimiter(self):
        client = self._client_with_pages(_make_page(contents=[]))
        client.list_objects(recursive=True)
        _paginator = client._client.list_objects_v2_paginator.return_value
        _request = _paginator.iter_page.call_args.kwargs["request"]
        assert _request.delimiter is None

    def test_recursive_false_uses_slash_delimiter(self):
        client = self._client_with_pages(_make_page(contents=[]))
        client.list_objects(recursive=False)
        _paginator = client._client.list_objects_v2_paginator.return_value
        _request = _paginator.iter_page.call_args.kwargs["request"]
        assert _request.delimiter == "/"

    def test_requests_fetch_owner(self):
        client = self._client_with_pages(_make_page(contents=[]))
        client.list_objects()
        _paginator = client._client.list_objects_v2_paginator.return_value
        _request = _paginator.iter_page.call_args.kwargs["request"]
        assert _request.fetch_owner is True

    def test_prefix_is_passed_through_to_request(self):
        client = self._client_with_pages(_make_page(contents=[]))
        client.list_objects(prefix="my/prefix")
        _paginator = client._client.list_objects_v2_paginator.return_value
        _request = _paginator.iter_page.call_args.kwargs["request"]
        assert _request.prefix == "my/prefix"
        assert _request.bucket == "my-bucket"


class TestOSSClientListFolders:
    def _client_with_pages_by_prefix(self, pages_by_prefix: dict[str, list[ListObjectsV2Result]]) -> OSSClient:
        client = OSSClient(bucket="my-bucket", region="cn-hangzhou", identity=_make_identity())
        _captured_requests: list = []

        def _list_objects_v2_paginator():
            _mock_paginator = MagicMock()

            def _iter_page(request):
                _captured_requests.append(request)
                return iter(pages_by_prefix.get(request.prefix, []))

            _mock_paginator.iter_page.side_effect = _iter_page
            return _mock_paginator

        client._client = MagicMock(list_objects_v2_paginator=MagicMock(side_effect=_list_objects_v2_paginator))
        client._captured_requests = _captured_requests
        return client

    def test_returns_empty_list_when_no_common_prefixes(self):
        client = self._client_with_pages_by_prefix({"": [_make_page(common_prefixes=[])]})
        assert client.list_folders() == []

    def test_returns_top_level_folders(self):
        client = self._client_with_pages_by_prefix(
            {
                "": [_make_page(common_prefixes=[CommonPrefix(prefix="a/"), CommonPrefix(prefix="b/")])],
                "a/": [_make_page(common_prefixes=[])],
                "b/": [_make_page(common_prefixes=[])],
            }
        )

        result = client.list_folders()

        assert [_f["prefix"] for _f in result] == ["a/", "b/"]
        assert all(_f["bucket"] == "my-bucket" for _f in result)

    def test_recursive_true_descends_into_subfolders(self):
        client = self._client_with_pages_by_prefix(
            {
                "": [_make_page(common_prefixes=[CommonPrefix(prefix="a/")])],
                "a/": [_make_page(common_prefixes=[CommonPrefix(prefix="a/b/")])],
                "a/b/": [_make_page(common_prefixes=[])],
            }
        )

        result = client.list_folders(recursive=True)

        assert [_f["prefix"] for _f in result] == ["a/", "a/b/"]

    def test_recursive_false_only_lists_top_level(self):
        client = self._client_with_pages_by_prefix(
            {
                "": [_make_page(common_prefixes=[CommonPrefix(prefix="a/")])],
            }
        )

        result = client.list_folders(recursive=False)

        assert [_f["prefix"] for _f in result] == ["a/"]
        # Non-recursive must not have queried anything below the top level.
        assert len(client._captured_requests) == 1

    def test_pattern_filters_returned_folders_but_still_recurses(self):
        client = self._client_with_pages_by_prefix(
            {
                "": [_make_page(common_prefixes=[CommonPrefix(prefix="a/"), CommonPrefix(prefix="keep/")])],
                "a/": [_make_page(common_prefixes=[CommonPrefix(prefix="a/keep/")])],
                "keep/": [_make_page(common_prefixes=[])],
                "a/keep/": [_make_page(common_prefixes=[])],
            }
        )

        result = client.list_folders(pattern="*keep/")

        assert sorted(_f["prefix"] for _f in result) == ["a/keep/", "keep/"]

    def test_results_are_sorted_by_prefix(self):
        client = self._client_with_pages_by_prefix(
            {
                "": [_make_page(common_prefixes=[CommonPrefix(prefix="b/"), CommonPrefix(prefix="a/")])],
                "b/": [_make_page(common_prefixes=[])],
                "a/": [_make_page(common_prefixes=[])],
            }
        )

        result = client.list_folders()

        assert [_f["prefix"] for _f in result] == ["a/", "b/"]

    def test_uses_slash_delimiter(self):
        client = self._client_with_pages_by_prefix({"": [_make_page(common_prefixes=[])]})
        client.list_folders()
        assert all(_r.delimiter == "/" for _r in client._captured_requests)

    def test_bucket_is_passed_through_to_request(self):
        client = self._client_with_pages_by_prefix({"": [_make_page(common_prefixes=[])]})
        client.list_folders()
        assert all(_r.bucket == "my-bucket" for _r in client._captured_requests)

    def test_visits_prefixes_in_breadth_first_order(self):
        client = self._client_with_pages_by_prefix(
            {
                "": [_make_page(common_prefixes=[CommonPrefix(prefix="a/"), CommonPrefix(prefix="b/")])],
                "a/": [_make_page(common_prefixes=[CommonPrefix(prefix="a/x/")])],
                "b/": [_make_page(common_prefixes=[])],
                "a/x/": [_make_page(common_prefixes=[])],
            }
        )

        client.list_folders()

        # BFS: both top-level prefixes must be visited before descending into "a/x/".
        _visited = [_r.prefix for _r in client._captured_requests]
        assert _visited.index("a/") < _visited.index("a/x/")
        assert _visited.index("b/") < _visited.index("a/x/")
