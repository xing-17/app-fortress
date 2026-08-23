from __future__ import annotations

from typing import Any, Callable

from bastion.control.compute.base.base import IComputeLike
from bastion.domain.compute import BaseComputeModel


class ComputeFactory:
    _registry: dict[str, type[IComputeLike]] = {}

    @classmethod
    def register(
        cls,
        kind: str,
    ) -> Callable[[type[IComputeLike]], type[IComputeLike]]:
        def decorator(klass: type[IComputeLike]):
            if kind in cls._registry:
                raise ValueError(f"'{kind}' compute already registered.")
            cls._registry[kind] = klass
            return klass

        return decorator

    @classmethod
    def load(
        cls,
        data: dict[str, Any] | BaseComputeModel,
    ) -> IComputeLike:
        if isinstance(data, BaseComputeModel):
            kind = getattr(data, "kind", None)
        else:
            kind = data.get("kind", None)

        if not kind:
            raise ValueError("Compute data missing required field: 'kind'")

        # Look up the registered class for the kind
        klass: type[IComputeLike] | None = cls._registry.get(kind)
        if klass is None:
            raise ValueError(f"No compute class registered for kind: '{kind}'")

        # Determine whether to load from dict or domain model
        if isinstance(data, BaseComputeModel):
            return klass.from_domain(data)
        else:
            return klass.from_dict(data)
