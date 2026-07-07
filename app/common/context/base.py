from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, computed_field, model_validator

from app.common.plugin import TimePlugin

if TYPE_CHECKING:
    pass


class BaseContext(
    BaseModel,
    TimePlugin,
):
    """
    上下文基类。

    提供上下文数据的标准化结构，自动记录创建时间。
    继承自 Pydantic BaseModel 和 TimePlugin，支持数据验证和时间处理。

    Attributes:
        category[str]: 上下文类别，自动计算为类名（computed field）
        created_at[datetime]: 上下文创建时间，自动设置为当前时间（timezone-aware）

    Methods:
        from_any: 从 JSON 字符串或字典创建上下文实例
        export: 导出上下文为字典
        describe: 返回上下文的 JSON 字符串描述

    Examples:
        >>> class TaskContext(BaseContext):
        ...     task_id: str
        ...     status: str
        >>>
        >>> # 从字典创建
        >>> ctx = TaskContext.from_any({"task_id": "T001", "status": "pending"})
        >>> print(ctx.category)
        'TaskContext'
        >>>
        >>> # 从 JSON 字符串创建
        >>> json_str = '{"task_id": "T002", "status": "running"}'
        >>> ctx = TaskContext.from_any(json_str)
        >>>
        >>> # 自动设置创建时间
        >>> assert ctx.created_at is not None
        >>>
        >>> # 导出和描述
        >>> print(ctx.describe())
        >>> ...

    """

    created_at: datetime | None = Field(default=None, frozen=True)

    @model_validator(mode="after")
    def set_created_at(self) -> BaseContext:
        if self.created_at is None:
            object.__setattr__(
                self,
                "created_at",
                self._get_current_datetime(),
            )
        return self

    @computed_field
    @property
    def category(self) -> str:
        return self.__class__.__name__

    @classmethod
    def from_any(
        cls,
        data: str | dict[str, Any],
    ) -> "BaseContext":
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse JSON: {e}") from e
        if not isinstance(data, dict):
            raise ValueError(f"Invalid type for context: {type(data)}")
        return cls(**data)

    def export(self) -> dict[str, Any]:
        result = self.model_dump()
        result["category"] = self.category
        result["created_at"] = self.created_at.isoformat()
        return result

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
