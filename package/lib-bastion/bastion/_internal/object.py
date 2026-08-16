from __future__ import annotations

import json
from typing import Any, ClassVar, Self

from bastion._internal.model import IBastionModel


class IBastionObject:
    _domain_class: ClassVar[type[IBastionModel] | None] = None

    @classmethod
    def from_dict(
        cls,
        data: dict[str, str | dict],
    ) -> Self:
        if cls._domain_class is None:
            raise TypeError(f"{cls.__name__} has no _domain_class")

        domain = cls._load_domain(data)
        return cls.from_domain(domain)

    @classmethod
    def from_domain(
        cls,
        domain: IBastionModel,
    ) -> Self:
        obj = cls.__new__(cls)
        object.__init__(obj)
        obj.domain = domain
        return obj

    @classmethod
    def _load_domain(
        cls,
        value: dict[str, Any],
    ) -> IBastionModel | None:
        if cls._domain_class is None:
            return None
        return cls._domain_class.from_any(value)

    def __getattr__(
        self,
        name: str,
    ) -> Any:
        domain = self.__dict__.get("domain")
        if domain is not None:
            return getattr(domain, name)
        _cls_name = self.__class__.__name__
        raise AttributeError(f"'{_cls_name}' object has no attribute '{name}'")

    def export(self) -> dict:
        return self.domain.model_dump(mode="json") 

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
            default=str,
        )
