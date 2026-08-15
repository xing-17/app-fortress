from __future__ import annotations

from typing import Any

from bastion._internal.object import IBastionObject
from bastion.domain.quality.base import BaseQualityModel

QualityModel = BaseQualityModel


class Quality(IBastionObject):
    """
    Wrapper for quality metrics metadata associated with a run.

    Attributes:
        domain (QualityModel): The underlying quality domain model.

    Methods:
        from_any(data: Quality | dict[str, str | dict]) -> Quality: Create Quality from dict or Quality instance.
        id: Get the quality check ID.
        run_id: Get the run ID associated with this quality check.
        _sha256_key: Get the SHA256 hash key for uniqueness.
        export() -> dict[str, Any]: Export quality data as a dictionary.

    Example:
        ```python
        quality = Quality(run_id="run-123", passed=True, description="Data validation")
        exported = quality.export()
        ```
    """

    @classmethod
    def from_any(cls, data: Quality | dict[str, str | dict]) -> Quality:
        if isinstance(data, Quality):
            return data
        try:
            return cls(
                id=data.get("id", None),
                run_id=data["run_id"],
                created_at=data.get("created_at", None),
                kind=data.get("kind", "base"),
                passed=data.get("passed", True),
                description=data.get("description", None),
                metrics=data.get("metrics", None),
            )
        except Exception as e:
            raise ValueError(f"Invalid data for Quality: {data}") from e

    def __init__(
        self,
        run_id: str,
        id: str | None = None,
        created_at: str | None = None,
        kind: str = "base",
        passed: bool = True,
        description: str | None = None,
        metrics: dict | None = None,
    ):
        super().__init__()
        self.domain: QualityModel = QualityModel.from_any(
            {
                "id": id,
                "run_id": run_id,
                "kind": kind,
                "passed": passed,
                "created_at": created_at,
                "description": description,
                "metrics": metrics,
            }
        )

    @property
    def id(self) -> str:
        return self.domain.id

    @property
    def run_id(self) -> str:
        return self.domain.run_id

    @property
    def _sha256_key(self) -> str:
        return self.domain._sha256_key

    def export(self) -> dict[str, Any]:
        return {
            **self.domain.export(),
        }
