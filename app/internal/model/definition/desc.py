from __future__ import annotations

from pydantic import Field

from app.internal.abstract.domain import IAbstractDomain


class ColumnDesc(IAbstractDomain):
    """
    Static documentation of one dataset column, declared by the dataset class as ColumnDesc

    It is not stored with the data and not part of the definition fingerprint,
    so it can change at any time and applies to every partition already written.

    Args:
    ---------
        description (str):
            What the column means, default is ""
        unit (str):
            Unit of the values, default is ""

    """

    model_config = IAbstractDomain.model_config | {"frozen": True}

    name: str = Field(
        ...,
        description="Name of the column.",
    )
    description: str = Field(
        default="",
        description="What the column means.",
    )
    unit: str = Field(
        default="",
        description="Unit of the values.",
    )
