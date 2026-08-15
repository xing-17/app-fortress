from __future__ import annotations

import json
from typing import Any, ClassVar

from bastion._internal.model import IBastionModel


class IBastionObject:
    _domain_class: ClassVar[type[IBastionModel] | None] = None

    @classmethod
    def _load_domain(
        self,
        value: dict[str, Any],
    ) -> IBastionModel | None:
        if self._domain_class is None:
            return None
        return self._domain_class.from_any(value)

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
        _basic = {
            "__class__": self.__class__.__name__,
            "__module__": self.__class__.__module__,
        }
        _domain = getattr(self, "domain", None)
        if _domain is not None:
            _basic = {**_basic, **_domain.export()}
        return _basic

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
            default=str,
        )
