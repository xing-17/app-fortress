from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from bastion._internal.object import IBastionObject
from bastion.domain.quality.base import BaseQualityModel

QualityModel = BaseQualityModel


@runtime_checkable
class IQualityLike(Protocol):
    # IBastionObject attributes
    domain: BaseQualityModel

    # quality attributes
    id: str
    run_id: str
    kind: str | None
    passed: bool | None
    description: str | None
    metrics: dict[str, Any]
    created_at: str | None

    # additional attributes for integrity
    logic_name: str | None
    sha256: str

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> IQualityLike: ...

    @classmethod
    def from_domain(
        cls,
        domain: QualityModel,
    ) -> IQualityLike: ...

    def export(self) -> dict[str, Any]: ...

    def describe(self) -> str: ...


class Quality(
    IBastionObject,
    IQualityLike,
):
    _domain_class = QualityModel

    def __init__(
        self,
        run_id: str,
        id: str | None = None,
        kind: str | None = None,
        passed: bool | None = None,
        description: str | None = None,
        created_at: datetime | str | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            run_id=run_id,
            id=id,
            kind=kind,
            passed=passed,
            description=description,
            created_at=created_at,
            metrics=metrics,
        )
