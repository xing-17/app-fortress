from __future__ import annotations

import json
from abc import abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from app.bridges.resources.sources.base.setting import BaseSourceSetting
from app.common.plugin import (
    LogPlugin,
    StopwatchPlugin,
    TimePlugin,
)

if TYPE_CHECKING:
    pass


class BaseSource(
    LogPlugin,
    TimePlugin,
    StopwatchPlugin,
):
    """
    数据源基类。

    定义从 YAML 配置加载的数据源的基础结构。
    子类须实现 build_params 方法，用于将运行时参数组装成 API 调用参数。

    Attributes:
        _setting_class: 子类声明，对应的 Setting 类，供 from_yaml 使用
        setting:        数据源配置对象（BaseSourceSetting 子类）
        name:           数据源名称，来自 setting.name

    Methods:
        from_yaml(path):        类方法，从 YAML 文件加载 setting 并构建实例
        build_params(**kwargs): 抽象方法，组装 API 调用参数
        export():               导出数据源配置为字典

    Example:
        >>> class MySource(BaseSource):
        ...     _setting_class = MySourceSetting
        ...     def build_params(self, **kwargs): ...
        >>> source = MySource.from_yaml("items/my.yaml")

    """

    _setting_class: ClassVar[type[BaseSourceSetting]] = BaseSourceSetting

    @classmethod
    def from_yaml(
        cls,
        path: str | Path,
    ) -> "BaseSource":
        setting = cls._setting_class.from_yaml(path)
        return cls(setting=setting)

    def __init__(
        self,
        setting: BaseSourceSetting,
    ) -> None:
        self.setting = setting
        self.name = setting.name
        self.provider_type = setting.provider_type
        self.tags = setting.tags

    @abstractmethod
    def build_params(
        self,
        **kwargs,
    ) -> dict:
        raise NotImplementedError

    def export(self) -> dict:
        return {
            "name": self.setting.name,
            "setting": self.setting.export(),
            "provider_type": self.setting.provider_type,
            "tags": self.setting.tags,
        }

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
