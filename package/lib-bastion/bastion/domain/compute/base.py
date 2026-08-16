from __future__ import annotations

from enum import StrEnum
from typing import Any, ClassVar

from pydantic import Field

from bastion._internal.model import IBastionModel


class ComputeKind(StrEnum):
    """
    Enumeration of supported compute resource types.

    Attributes:
        LOCAL_PY_FN (str): Local Python function execution type.

    Methods:
        from_any(str | ComputeKind value): Convert string or ComputeKind to ComputeKind enum.

    Example:
        ```python
        kind = ComputeKind.LOCAL_PY_FN
        kind_from_str = ComputeKind.from_any("local_py_fn")
        ```

    """

    LOCAL_PY_FN = "local_py_fn"


class BaseComputeModel(IBastionModel):
    """
    Base model for compute resources that defines common properties.

    Attributes:
        name (str): Name of the compute resource.
        kind (ComputeKind): Kind of the compute resource (e.g., 'local_py_fn').
        tags (dict[str, str]): Tags associated with the compute resource.

    Methods:
        export(): Export the compute model as a dictionary.

    Example:
        ```python
        compute = BaseComputeModel(
            name="my_compute",
            kind=ComputeKind.LOCAL_PY_FN,
            tags={"env": "dev"}
        )
        data = compute.export()
        ```

    """

    _id_enabled: ClassVar[bool] = False
    name: str = Field(
        ...,
        description="Name of the compute resource",
    )
    kind: ComputeKind = Field(
        ...,
        description="Kind of the compute resource, e.g., 'docker', 'local_py_fn', etc.",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Tags associated with the compute resource",
    )

    def export(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind.value,
            "tags": self.tags,
        }
