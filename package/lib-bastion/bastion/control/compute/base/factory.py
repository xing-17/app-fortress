from __future__ import annotations

from typing import Any

from bastion.control.compute.base.base import IComputeLike
from bastion.domain.compute.base import BaseComputeModel


class ComputeFactory:
    _registry: dict[str, type[IComputeLike]] = {}

    @classmethod
    def register(
        cls,
        kind: str,
        compute_cls: type[IComputeLike],
    ) -> None:
        cls._registry[kind] = compute_cls

    @classmethod
    def load_from_dict(
        cls,
        data: dict[str, Any],
    ) -> IComputeLike:
        kind = data.get("kind")
        if kind is None:
            raise ValueError("Compute data missing required field: 'kind'")

        compute_cls = cls._registry.get(kind)
        if compute_cls is None:
            raise ValueError(f"No compute class registered for kind: '{kind}'")

        return compute_cls.from_dict(data)

    @classmethod
    def load_from_domain(
        cls,
        domain: Any,
    ) -> IComputeLike:
        kind = getattr(domain, "kind", None)
        if kind is None:
            raise ValueError("Domain object missing required attribute: 'kind'")

        compute_cls = cls._registry.get(kind)
        if compute_cls is None:
            raise ValueError(f"No compute class registered for kind: '{kind}'")

        return compute_cls.from_domain(domain)

    @classmethod
    def resolve(
        cls,
        value: IComputeLike | dict[str, Any] | None,
    ) -> IComputeLike | None:
        if value is None:
            return None
        elif isinstance(value, IComputeLike):
            return value
        elif isinstance(value, BaseComputeModel):
            return cls.load_from_domain(value)
        elif isinstance(value, dict):
            return cls.load_from_dict(value)
        else:
            raise ValueError(f"Invalid compute type: {type(value)}")


def _register_defaults() -> None:

    # Register PyEntrypointCompute for the "py_entrypoint" kind
    from bastion.control.compute.pyentrypoint.pyentrypoint import PyEntrypointCompute

    ComputeFactory.register(
        kind="py_entrypoint",
        compute_cls=PyEntrypointCompute,
    )


_register_defaults()
