from __future__ import annotations

from typing import Any

from bastion.control.compute.base.base import IComputeLike


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
    def load(
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


def _register_defaults() -> None:

    # Register PyEntrypointCompute for the "py_entrypoint" kind
    from bastion.control.compute.pyentrypoint.pyentrypoint import PyEntrypointCompute

    ComputeFactory.register(
        kind="py_entrypoint",
        compute_cls=PyEntrypointCompute,
    )


_register_defaults()
