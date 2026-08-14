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

    @classmethod
    def from_any(
        cls,
        value: str | ComputeKind,
    ) -> ComputeKind:
        """
        Convert a string or ComputeKind instance to a ComputeKind enum value.
        """
        if isinstance(value, cls):
            return value
        try:
            return cls(value)
        except ValueError:
            raise ValueError(f"Invalid ComputeKind value: {value}")


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

    @classmethod
    def from_any(
        cls,
        value: dict | BaseComputeModel,
    ) -> BaseComputeModel:
        if isinstance(value, BaseComputeModel):
            return value
        try:
            _attrs = {
                "name": value.get("name"),
                "kind": ComputeKind.from_any(value.get("kind")),
                "tags": value.get("tags", {}),
            }
            _attrs = {k: v for k, v in _attrs.items() if v is not None}
            return cls(**_attrs)
        except Exception as e:
            raise ValueError(f"Cannot create {cls.__name__}: {e}") from e

    def export(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind.value,
            "tags": self.tags,
        }
