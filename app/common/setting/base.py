from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from pydantic import BaseModel, computed_field

if TYPE_CHECKING:
    pass


class BaseSetting(BaseModel):
    """
    配置基类。

    Attributes:
        category: 配置类别，默认为类名

    Methods:
        from_yaml: 从 YAML 文件加载配置
        export: 导出配置为字典
        describe: 返回配置的 JSON 字符串描述

    Examples:
        >>> config = SomeSetting.from_yaml("setting/some.yml")
        >>> print(config.describe())
        >>> ...

    """

    @computed_field
    @property
    def category(self) -> str:
        return self.__class__.__name__

    @classmethod
    def from_yaml(
        cls,
        path: str | Path,
    ) -> "BaseSetting":
        resolved = Path(path).expanduser().resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"YAML not found: {resolved}")

        try:
            with resolved.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse YAML: {resolved}\n{e}") from e

        if not data:
            warnings.warn(f"YAML is empty or invalid: {resolved}", UserWarning)

        return cls(**data)

    def export(self) -> dict:
        return self.model_dump()

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
