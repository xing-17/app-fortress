from __future__ import annotations

from abc import ABC
from typing import Any

from pydantic import ConfigDict, Field

from app.internal.abstract.domain import IAbstractTaggedDomain
from app.internal.logstream.stream import LogStream
from app.internal.util.id import IID


def generate_id(
    length: int = 12,
    prefix: str | None = None,
) -> str:
    return IID.generate_id(length=length, prefix=prefix)


class BaseAccessory(
    IAbstractTaggedDomain,
    ABC,
):
    """
    Base class for accessory resources.

    Args:
        id (str): Unique identifier of the accessory, auto-generated if not provided
        logstream (LogStream | None): Log stream associated with the accessory
        tags (dict[str, str]): Tags associated with the accessory

    Methods:
        info/debug/warning/error/critical(msg, metadata=None, metrics=None, tags=None) -> None:
            Emit a log record to the bound logstream, prefixed with the accessory's kind and id.
        export() -> dict[str, Any]:
            Export the accessory as a dict, including the logstream name if bound.

    """

    # LogStream is a plain logging.Logger subclass, not a pydantic type.
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(
        default_factory=lambda: generate_id(length=12),
        description="The unique identifier of the accessory.",
    )
    logstream: LogStream | None = Field(
        default=None,
        description="The log stream associated with the accessory.",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="The tags associated with the accessory.",
    )

    @property
    def kind(self) -> str:
        return self.cls_name

    @property
    def frn(self) -> str:
        return f"{self.kind}:id={self.id}"

    def _resolve_msg(
        self,
        msg: object,
    ) -> str:
        return f"{self.kind}({self.id}): {msg}"

    def info(
        self,
        msg: object,
        metadata: dict[str, Any] | None = None,
        metrics: dict[str, str | int | float] | None = None,
        tags: dict[str, str] | None = None,
    ) -> None:
        if self.logstream:
            return self.logstream.info(
                msg=self._resolve_msg(msg),
                metadata=metadata,
                metrics=metrics,
                tags=tags,
            )

    def error(
        self,
        msg: object,
        metadata: dict[str, Any] | None = None,
        metrics: dict[str, str | int | float] | None = None,
        tags: dict[str, str] | None = None,
    ) -> None:
        if self.logstream:
            return self.logstream.error(
                msg=self._resolve_msg(msg),
                metadata=metadata,
                metrics=metrics,
                tags=tags,
            )

    def debug(
        self,
        msg: object,
        metadata: dict[str, Any] | None = None,
        metrics: dict[str, str | int | float] | None = None,
        tags: dict[str, str] | None = None,
    ) -> None:
        if self.logstream:
            return self.logstream.debug(
                msg=self._resolve_msg(msg),
                metadata=metadata,
                metrics=metrics,
                tags=tags,
            )

    def warning(
        self,
        msg: object,
        metadata: dict[str, Any] | None = None,
        metrics: dict[str, str | int | float] | None = None,
        tags: dict[str, str] | None = None,
    ) -> None:
        if self.logstream:
            return self.logstream.warning(
                msg=self._resolve_msg(msg),
                metadata=metadata,
                metrics=metrics,
                tags=tags,
            )

    def critical(
        self,
        msg: object,
        metadata: dict[str, Any] | None = None,
        metrics: dict[str, str | int | float] | None = None,
        tags: dict[str, str] | None = None,
    ) -> None:
        if self.logstream:
            return self.logstream.critical(
                msg=self._resolve_msg(msg),
                metadata=metadata,
                metrics=metrics,
                tags=tags,
            )

    def export(self) -> dict[str, Any]:
        _res: dict[str, Any] = self.model_dump(
            mode="json",
            round_trip=True,
            exclude={"logstream"},
        )
        if self.logstream:
            _res["logstream"] = self.logstream.name
        else:
            _res["logstream"] = None
        return _res
