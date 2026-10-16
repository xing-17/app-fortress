from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from app.internal.constant.computeruntime import ComputeRuntime
from app.internal.constant.platform import Platform
from app.setting import (
    AliyunIdentitySetting,
    FCComputeSetting,
    LocalIdentitySetting,
    PyEntrypointComputeSetting,
    UnionComputeSetting,
)


class TestUnionComputeSetting:
    def test_dispatches_on_runtime(self):
        _adapter = TypeAdapter(UnionComputeSetting)
        _py = _adapter.validate_python({"name": "c", "runtime": "pyentrypoint", "entrypoint": "a.b:f"})
        assert isinstance(_py, PyEntrypointComputeSetting)
        _fc = _adapter.validate_python({"name": "c", "runtime": "fc", "function_name": "fn", "region": "cn-hangzhou"})
        assert isinstance(_fc, FCComputeSetting)

    def test_unknown_runtime_is_rejected(self):
        with pytest.raises(ValidationError):
            TypeAdapter(UnionComputeSetting).validate_python({"name": "c", "runtime": "unknown"})

    def test_missing_runtime_is_rejected(self):
        with pytest.raises(ValidationError):
            TypeAdapter(UnionComputeSetting).validate_python({"name": "c", "entrypoint": "a.b:f"})


class TestPyEntrypointComputeSetting:
    def test_defaults(self):
        _s = PyEntrypointComputeSetting(name="c", entrypoint="a.b:f")
        assert _s.runtime == ComputeRuntime.PYENTRYPOINT
        assert _s.platform == Platform.LOCAL
        assert _s.description == ""
        assert _s.tags["name"] == "c"

    def test_max_run_records_defaults_and_must_be_positive(self):
        assert PyEntrypointComputeSetting(name="c", entrypoint="a.b:f").max_run_records == 200
        assert PyEntrypointComputeSetting(name="c", entrypoint="a.b:f", max_run_records=3).max_run_records == 3
        with pytest.raises(ValidationError):
            PyEntrypointComputeSetting(name="c", entrypoint="a.b:f", max_run_records=0)

    def test_requires_name_and_entrypoint(self):
        with pytest.raises(ValidationError):
            PyEntrypointComputeSetting(name="c")
        with pytest.raises(ValidationError):
            PyEntrypointComputeSetting(entrypoint="a.b:f")

    def test_discriminators_are_fixed(self):
        with pytest.raises(ValidationError):
            PyEntrypointComputeSetting(name="c", entrypoint="a.b:f", runtime="fc")
        with pytest.raises(ValidationError):
            PyEntrypointComputeSetting(name="c", entrypoint="a.b:f", platform="aliyun")

    def test_frn(self):
        _s = PyEntrypointComputeSetting(name="c", entrypoint="a.b:f")
        assert _s.frn == "setting:compute:platform=local:runtime=pyentrypoint:name=c"


class TestFCComputeSetting:
    def test_defaults(self):
        _s = FCComputeSetting(name="c", function_name="fn", region="cn-hangzhou")
        assert _s.runtime == ComputeRuntime.FC
        assert _s.platform == Platform.ALIYUN
        assert _s.qualifier == "LATEST"
        assert _s.max_workers == 8
        assert _s.in_vpc is False
        assert _s.timeout_seconds == 600
        assert _s.identity is None

    def test_requires_function_name_and_region(self):
        with pytest.raises(ValidationError):
            FCComputeSetting(name="c", region="cn-hangzhou")
        with pytest.raises(ValidationError):
            FCComputeSetting(name="c", function_name="fn")

    def test_timeout_must_be_positive(self):
        with pytest.raises(ValidationError):
            FCComputeSetting(name="c", function_name="fn", region="r", timeout_seconds=0)

    def test_discriminators_are_fixed(self):
        with pytest.raises(ValidationError):
            FCComputeSetting(name="c", function_name="fn", region="r", runtime="pyentrypoint")
        with pytest.raises(ValidationError):
            FCComputeSetting(name="c", function_name="fn", region="r", platform="local")

    def test_identity_accepts_name(self):
        _s = FCComputeSetting(name="c", function_name="fn", region="r", identity="id")
        assert _s.identity == "id"

    def test_identity_accepts_nested_setting(self):
        _s = FCComputeSetting(
            name="c",
            function_name="fn",
            region="r",
            identity={"name": "id", "platform": "aliyun"},
        )
        assert isinstance(_s.identity, AliyunIdentitySetting)

    def test_identity_rejects_other_platform(self):
        with pytest.raises(ValidationError):
            FCComputeSetting(name="c", function_name="fn", region="r", identity=LocalIdentitySetting(name="id"))
