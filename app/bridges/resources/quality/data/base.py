from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

import polars as pl


class BaseDataQuality(ABC):
    """
    质量报告基类。

    提供数据质量报告的基本结构和方法，子类可根据具体需求扩展。

    Attributes:
        source_name (str): 数据源名称
        source_context_id (str): 数据源上下文 ID
        extra (dict[str, Any]): 额外信息，如执行状态、时间戳

    Methods:
        report(): 生成 pl.DataFrame 格式的质量报告。
        export(): 导出为字典格式，包含所有质量信息。
        describe(): 返回质量报告的 JSON 字符串表示。

    """

    @abstractmethod
    def get_category(self) -> str:
        """
        获取质量报告的类别。

        Returns:
            str: 质量报告的类别
        """
        raise NotImplementedError("Subclasses must implement the get_category method.")

    @abstractmethod
    def get_identifier(self) -> str:
        """
        获取数据源的唯一标识符。

        Returns:
            str: 数据源的唯一标识符

        """
        raise NotImplementedError("Subclasses must implement the get_identifier method.")

    @abstractmethod
    def report(self) -> pl.DataFrame:
        """
        生成 Polars DataFrame 格式的质量报告。

        每列生成一行，包含所有质量指标。

        Returns:
            pl.DataFrame: 数据质量报告
        """
        raise NotImplementedError("Subclasses must implement the report method.")

    @abstractmethod
    def export(self) -> dict[str, Any]:
        """
        导出为字典格式，包含所有质量信息。

        Returns:
            dict[str, Any]: 数据质量报告的字典表示
        """
        raise NotImplementedError("Subclasses must implement the export method.")

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
