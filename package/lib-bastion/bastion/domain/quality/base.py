from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

from pydantic import Field, field_validator

from bastion._internal.clock import IBastionClock
from bastion._internal.model import IBastionModel


class BaseQualityModel(IBastionModel):
    """
    Base quality model for recording quality metrics and validation results from run executions.

    Attributes:
        id (str): Unique identifier with 'qual' prefix (inherited from IBastionModel).
        run_id (str): ID of the run associated with the quality metrics.
        kind (str): Kind of the model, defaults to 'base'.
        passed (bool): Indicates whether the quality check passed.
        description (str | None): Optional description of the quality metrics.
        created_at (datetime): Datetime when the quality metrics were created.
        metrics (dict[str, Any]): Dictionary of quality metrics.
        logic_name (str): Logical identifier combining bridge_name and optional name.
        sha256 (str): SHA256 hash of the run's canonical representation.

    Methods:
        from_any(value): Convert dict or instance to quality model (inherited).
        export(): Export the quality model as a dictionary with serialized fields.
        describe(): Export quality as JSON string (inherited).
        clone(**updates): Create a deep copy with updates (inherited).

    Example:
        ```python
        quality = BaseQualityModel(
            run_id="run-123abc",
            passed=True,
            description="Data validation checks",
            metrics={"row_count": 1000, "null_rate": 0.02}
        )
        exported = quality.export()
        ```
    """

    _id_enabled: ClassVar[bool] = True
    _id_prefix: ClassVar[str] = "qual"
    _id_length: ClassVar[int] = 20

    run_id: str = Field(
        ...,
        description="ID of the run associated with the quality metrics.",
    )
    kind: str = Field(
        default="base",
        description="Kind of the model, defaults to 'base'.",
    )
    passed: bool | None = Field(
        default=None,
        description="Indicates whether the quality check passed, defaults to None.",
    )
    description: str | None = Field(
        default=None,
        description="Optional description of the quality metrics.",
    )
    created_at: datetime = Field(
        default_factory=IBastionClock.current,
        description="Datetime when the quality metrics were created.",
    )
    metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="Dictionary of quality metrics.",
    )

    @field_validator("created_at", mode="before")
    @classmethod
    def _coerce_required_datetime(cls, v: Any) -> Any:
        if v is None:
            return IBastionClock.current()
        if isinstance(v, str):
            return IBastionClock.from_iso(v)
        return v
