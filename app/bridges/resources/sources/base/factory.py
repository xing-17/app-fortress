from __future__ import annotations

import warnings
from pathlib import Path

import yaml

from app.bridges.resources.sources.base.source import BaseSource
from app.common.core.setting import GlobalSetting


class SourceFactory:
    """
    Source 注册工厂。

    按 provider_type 注册 Source 子类，并依据 bridges.yml 的
    source_paths 扫描所有 YAML 文件完成批量发现。

    Methods:
        register(provider_type): 装饰器，将 Source 子类注册到注册表
        from_yaml(path):         从单个 YAML 文件构建 Source 实例
        bootstrap():             扫描 source_paths，返回 {name: source}

    Example:
        >>> @SourceFactory.register("tushare")
        ... class TushareSource(BaseSource): ...
        >>> sources = SourceFactory.bootstrap()

    """

    _registry: dict[str, type[BaseSource]] = {}  # provider_type → class

    @classmethod
    def register(
        cls,
        provider_type: str,
    ):
        def decorator(klass: type[BaseSource]):
            if provider_type in cls._registry:
                raise ValueError(f"Source provider_type '{provider_type}' already registered.")
            cls._registry[provider_type] = klass
            return klass

        return decorator

    @classmethod
    def from_yaml(
        cls,
        path: str | Path,
    ) -> BaseSource:
        resolved = Path(path).expanduser().resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"Source YAML not found: {resolved}")

        try:
            raw = yaml.safe_load(resolved.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse YAML: {resolved}\n{e}") from e

        if not raw:
            raise ValueError(f"Source YAML is empty: {resolved}")

        provider_type = raw.get("provider_type")
        if not provider_type:
            raise ValueError(f"Missing 'provider_type' field in YAML: {resolved}")

        klass = cls._registry.get(provider_type)
        if klass is None:
            raise KeyError(f"Unknown provider_type '{provider_type}'.")

        return klass.from_yaml(resolved)

    @classmethod
    def bootstrap(cls) -> dict[str, BaseSource]:
        root = GlobalSetting._default_root_dir
        source_paths: list[str] = GlobalSetting.bridges.source_paths
        result: dict[str, BaseSource] = {}
        for rel_path in source_paths:
            directory = (root / rel_path).resolve()
            if not directory.is_dir():
                warnings.warn(
                    f"{directory} is not directory",
                    UserWarning,
                )
                continue

            for yaml_file in sorted(directory.glob("*.yaml")):
                try:
                    source = cls.from_yaml(yaml_file)
                except Exception as e:
                    warnings.warn(
                        f"Failed to load source from {yaml_file}: {e}",
                        UserWarning,
                    )
                    continue

                if source.name in result:
                    warnings.warn(
                        f"Source '{source.name}' already exists, skipping.",
                        UserWarning,
                    )
                    continue
                result[source.name] = source
        return result
