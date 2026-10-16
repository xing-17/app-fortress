from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.internal.constant.computeruntime import ComputeRuntime
from app.internal.constant.platform import Platform
from app.resource.compute._common._compute import BaseCompute
from app.resource.compute._common._factory import ComputeFactory


class _Dummy(BaseCompute):
    runtime = ComputeRuntime.PYENTRYPOINT
    platform = Platform.LOCAL

    @classmethod
    def from_setting(cls, setting):
        return ("loaded", setting.name)

    def _execute(self, payload):
        return {}

    def _submit(self, payload):
        return ""

    def _poll(self, run):
        return run


class _NotCompute:
    pass


_THIS = __name__


@pytest.fixture
def _registry(monkeypatch):
    _reg: dict = {}
    monkeypatch.setattr(ComputeFactory, "_registry", _reg)
    return _reg


class TestComputeFactoryGet:
    @pytest.mark.parametrize(
        "runtime",
        [ComputeRuntime.PYENTRYPOINT, ComputeRuntime.FC],
    )
    def test_builtin_runtimes_resolve_to_compute_subclasses(self, runtime):
        _klass = ComputeFactory.get(runtime)
        assert issubclass(_klass, BaseCompute)
        assert _klass.runtime == runtime

    def test_string_runtime_is_accepted(self):
        assert ComputeFactory.get("pyentrypoint") is ComputeFactory.get(ComputeRuntime.PYENTRYPOINT)

    def test_unregistered_runtime_raises_value_error(self):
        with pytest.raises(ValueError):
            ComputeFactory.get("unknown")

    def test_registered_class_is_returned(self, _registry):
        _registry[ComputeRuntime.PYENTRYPOINT] = f"{_THIS}:_Dummy"
        assert ComputeFactory.get(ComputeRuntime.PYENTRYPOINT) is _Dummy

    def test_non_class_target_raises_type_error(self, _registry):
        _registry[ComputeRuntime.PYENTRYPOINT] = f"{_THIS}:_THIS"
        with pytest.raises(TypeError):
            ComputeFactory.get(ComputeRuntime.PYENTRYPOINT)

    def test_non_compute_class_raises_type_error(self, _registry):
        _registry[ComputeRuntime.PYENTRYPOINT] = f"{_THIS}:_NotCompute"
        with pytest.raises(TypeError):
            ComputeFactory.get(ComputeRuntime.PYENTRYPOINT)


class TestComputeFactoryLoad:
    def test_load_delegates_to_from_setting(self, _registry):
        _registry[ComputeRuntime.PYENTRYPOINT] = f"{_THIS}:_Dummy"
        _setting = SimpleNamespace(runtime=ComputeRuntime.PYENTRYPOINT, name="demo")
        assert ComputeFactory.load(_setting) == ("loaded", "demo")  # type: ignore[arg-type]

    def test_load_unregistered_runtime_raises_value_error(self, _registry):
        _setting = SimpleNamespace(runtime=ComputeRuntime.FC, name="demo")
        with pytest.raises(ValueError):
            ComputeFactory.load(_setting)  # type: ignore[arg-type]
