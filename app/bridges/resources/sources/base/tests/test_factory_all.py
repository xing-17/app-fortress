"""
综合测试：app.bridges.sources.source.base.factory

覆盖范围
--------
- TestRegister    register() 写入注册表，重复注册抛 ValueError，返回原类
- TestFromYaml    from_yaml() 路由到正确子类，错误情况抛对应异常
- TestBootstrap   bootstrap() 按 source_paths 批量发现，异常文件只警告不中断
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest
import yaml

from app.bridges.resources.sources.base.factory import SourceFactory
from app.bridges.resources.sources.base.setting import (
    BaseSourceSetting,
)
from app.bridges.resources.sources.base.source import BaseSource
from app.common.core.setting import CoreSetting

# ──────────────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────────────


class _MockSource(BaseSource):
    _setting_class = BaseSourceSetting

    def build_params(self, **kwargs) -> dict:
        return kwargs


_VALID_YAML_CONTENT = {
    "name": "test_source",
    "provider_type": "mock",
    "method": "daily",
    "strategy": "by_date",
    "partition": {"prefix": "date", "column": "trade_date"},
}


# ──────────────────────────────────────────────────────────────────────────────
# TestRegister
# ──────────────────────────────────────────────────────────────────────────────


class TestRegister:
    def test_register_stores_class_in_registry(self, monkeypatch):
        monkeypatch.setattr(SourceFactory, "_registry", {})
        SourceFactory.register("mock")(_MockSource)
        assert "mock" in SourceFactory._registry

    def test_register_maps_key_to_correct_class(self, monkeypatch):
        monkeypatch.setattr(SourceFactory, "_registry", {})
        SourceFactory.register("mock")(_MockSource)
        assert SourceFactory._registry["mock"] is _MockSource

    def test_register_returns_class_unchanged(self, monkeypatch):
        monkeypatch.setattr(SourceFactory, "_registry", {})
        result = SourceFactory.register("mock")(_MockSource)
        assert result is _MockSource

    def test_register_duplicate_raises_value_error(self, monkeypatch):
        monkeypatch.setattr(SourceFactory, "_registry", {})
        SourceFactory.register("mock")(_MockSource)
        with pytest.raises(ValueError, match="already registered"):
            SourceFactory.register("mock")(_MockSource)

    def test_register_multiple_different_types(self, monkeypatch):
        monkeypatch.setattr(SourceFactory, "_registry", {})
        SourceFactory.register("mock")(_MockSource)
        SourceFactory.register("other")(_MockSource)
        assert "mock" in SourceFactory._registry
        assert "other" in SourceFactory._registry


# ──────────────────────────────────────────────────────────────────────────────
# TestFromYaml
# ──────────────────────────────────────────────────────────────────────────────


class TestFromYaml:
    def test_from_yaml_routes_to_correct_class(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(SourceFactory, "_registry", {"mock": _MockSource})
        p = tmp_path / "s.yaml"
        p.write_text(yaml.dump(_VALID_YAML_CONTENT), encoding="utf-8")
        source = SourceFactory.from_yaml(p)
        assert isinstance(source, _MockSource)

    def test_from_yaml_sets_correct_name(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(SourceFactory, "_registry", {"mock": _MockSource})
        p = tmp_path / "s.yaml"
        p.write_text(yaml.dump(_VALID_YAML_CONTENT), encoding="utf-8")
        source = SourceFactory.from_yaml(p)
        assert source.name == "test_source"

    def test_from_yaml_missing_file_raises_filenotfounderror(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            SourceFactory.from_yaml(tmp_path / "missing.yaml")

    def test_from_yaml_empty_file_raises_value_error(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(SourceFactory, "_registry", {"mock": _MockSource})
        p = tmp_path / "empty.yaml"
        p.write_text("", encoding="utf-8")
        with pytest.raises(ValueError, match="empty"):
            SourceFactory.from_yaml(p)

    def test_from_yaml_missing_provider_type_raises_value_error(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(SourceFactory, "_registry", {"mock": _MockSource})
        content = {k: v for k, v in _VALID_YAML_CONTENT.items() if k != "provider_type"}
        p = tmp_path / "notype.yaml"
        p.write_text(yaml.dump(content), encoding="utf-8")
        with pytest.raises(ValueError, match="provider_type"):
            SourceFactory.from_yaml(p)

    def test_from_yaml_unknown_provider_type_raises_key_error(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(SourceFactory, "_registry", {})
        p = tmp_path / "s.yaml"
        p.write_text(yaml.dump(_VALID_YAML_CONTENT), encoding="utf-8")
        with pytest.raises(KeyError, match="mock"):
            SourceFactory.from_yaml(p)

    def test_from_yaml_delegates_to_source_class(self, tmp_path: Path, monkeypatch):
        """验证 factory 调用的是 klass.from_yaml，而非直接解析 _setting_class"""
        called_with = []

        class _TrackSource(_MockSource):
            @classmethod
            def from_yaml(cls, path):
                called_with.append(path)
                return super().from_yaml(path)

        monkeypatch.setattr(SourceFactory, "_registry", {"mock": _TrackSource})
        p = tmp_path / "s.yaml"
        p.write_text(yaml.dump(_VALID_YAML_CONTENT), encoding="utf-8")
        SourceFactory.from_yaml(p)
        assert len(called_with) == 1
        assert called_with[0] == p


# ──────────────────────────────────────────────────────────────────────────────
# TestBootstrap
# ──────────────────────────────────────────────────────────────────────────────


class TestBootstrap:
    def _write_yaml(self, directory: Path, name: str, provider_type: str = "mock") -> Path:
        content = {
            "name": name,
            "provider_type": provider_type,
            "method": "daily",
            "strategy": "by_date",
            "partition": {"prefix": "date", "column": "trade_date"},
        }
        p = directory / f"{name}.yaml"
        p.write_text(yaml.dump(content), encoding="utf-8")
        return p

    def test_bootstrap_discovers_all_yaml_in_paths(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(SourceFactory, "_registry", {"mock": _MockSource})
        items = tmp_path / "items"
        items.mkdir()
        self._write_yaml(items, "source_a")
        self._write_yaml(items, "source_b")

        monkeypatch.setattr(CoreSetting, "_default_root_dir", tmp_path)
        monkeypatch.setattr("app.common.core.setting.GlobalSetting.bridges.source_paths", ["items"])

        result = SourceFactory.bootstrap()
        assert "source_a" in result
        assert "source_b" in result

    def test_bootstrap_returns_correct_instances(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(SourceFactory, "_registry", {"mock": _MockSource})
        items = tmp_path / "items"
        items.mkdir()
        self._write_yaml(items, "source_x")

        monkeypatch.setattr(CoreSetting, "_default_root_dir", tmp_path)
        monkeypatch.setattr("app.common.core.setting.GlobalSetting.bridges.source_paths", ["items"])

        result = SourceFactory.bootstrap()
        assert isinstance(result["source_x"], _MockSource)

    def test_bootstrap_invalid_directory_emits_warning(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(SourceFactory, "_registry", {"mock": _MockSource})
        monkeypatch.setattr(CoreSetting, "_default_root_dir", tmp_path)
        monkeypatch.setattr(
            "app.common.core.setting.GlobalSetting.bridges.source_paths",
            ["nonexistent_dir"],
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = SourceFactory.bootstrap()
        assert result == {}
        assert any(issubclass(x.category, UserWarning) for x in w)

    def test_bootstrap_bad_yaml_emits_warning_not_raises(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(SourceFactory, "_registry", {"mock": _MockSource})
        items = tmp_path / "items"
        items.mkdir()
        (items / "bad.yaml").write_text("", encoding="utf-8")  # 空文件

        monkeypatch.setattr(CoreSetting, "_default_root_dir", tmp_path)
        monkeypatch.setattr("app.common.core.setting.GlobalSetting.bridges.source_paths", ["items"])

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = SourceFactory.bootstrap()
        assert result == {}
        assert any(issubclass(x.category, UserWarning) for x in w)

    def test_bootstrap_duplicate_name_skips_second_emits_warning(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(SourceFactory, "_registry", {"mock": _MockSource})
        dir_a = tmp_path / "items_a"
        dir_b = tmp_path / "items_b"
        dir_a.mkdir()
        dir_b.mkdir()
        self._write_yaml(dir_a, "dup_source")
        self._write_yaml(dir_b, "dup_source")

        monkeypatch.setattr(CoreSetting, "_default_root_dir", tmp_path)
        monkeypatch.setattr(
            "app.common.core.setting.GlobalSetting.bridges.source_paths",
            ["items_a", "items_b"],
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = SourceFactory.bootstrap()

        assert len(result) == 1
        assert any("already exists" in str(x.message) for x in w)

    def test_bootstrap_returns_empty_dict_when_no_paths(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(SourceFactory, "_registry", {"mock": _MockSource})
        monkeypatch.setattr(CoreSetting, "_default_root_dir", tmp_path)
        monkeypatch.setattr("app.common.core.setting.GlobalSetting.bridges.source_paths", [])

        result = SourceFactory.bootstrap()
        assert result == {}
