from __future__ import annotations

from abc import ABC
from enum import StrEnum
from typing import ClassVar

from pydantic import Field

from bastion._internal.model import IBastionModel


class ComputeKind(StrEnum):
    """
    Enumeration of supported compute resource types.

    Attributes:
        PY_ENTRYPOINT (str): Local Python function execution type.

    Methods:
        from_any(str | ComputeKind value): Convert string or ComputeKind to ComputeKind enum.

    Example:
        ```python
        kind = ComputeKind.PY_ENTRYPOINT
        kind_from_str = ComputeKind.from_any("py_entrypoint")
        ```

    """

    PY_ENTRYPOINT = "py_entrypoint"


class BaseComputeModel(
    IBastionModel,
    ABC,
):
    """
    Base model for compute resources defining execution environments and their properties.

    Attributes:
        name (str): Name of the compute resource.
        kind (ComputeKind): Kind of the compute resource (e.g., local_py_entrypoint).
        tags (dict[str, str]): Tags associated with the compute resource.
        logic_name (str): Logical identifier combining bridge_name and optional name.
        sha256 (str): SHA256 hash of the run's canonical representation.

    Methods:
        from_any(value): Convert dict or instance to compute model (inherited).
        export(): Export the compute model as a dictionary.
        describe(): Export compute as JSON string (inherited).
        clone(**updates): Create a deep copy with updates (inherited).

    Example:
        ```python
        compute = BaseComputeModel(
            name="my_compute",
            kind=ComputeKind.PY_ENTRYPOINT,
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
        description="Kind of the compute resource, e.g., 'docker', 'py_entrypoint', etc.",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Tags associated with the compute resource",
    )
