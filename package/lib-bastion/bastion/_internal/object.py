from __future__ import annotations

import json
from typing import Any, ClassVar, Self

from bastion._internal.model import IBastionModel


class IBastionObject:
    """
    Base wrapper class for domain models with attribute delegation.

    Attributes:
        _domain_class (ClassVar[type[IBastionModel] | None]): The domain model class to wrap.
        domain (IBastionModel): The underlying domain model instance.

    Methods:
        from_dict(dict data): Create instance from dictionary data.
        from_domain(IBastionModel domain): Create instance from domain model.
        export(): Export the underlying domain model to a dictionary.
        describe(): Return a JSON string representation of the domain model.

    Example:
        ```python
        from bastion._internal.object import IBastionObject
        from bastion._internal.model import IBastionModel

        class MyDomain(IBastionModel):
            name: str
            value: int

        class MyObject(IBastionObject):
            _domain_class = MyDomain

        # Create from dict
        obj = MyObject.from_dict({"name": "test", "value": 42})
        print(obj.name)  # Accesses obj.domain.name via __getattr__

        # Create from domain
        domain = MyDomain(name="example", value=100)
        obj2 = MyObject.from_domain(domain)

        # Export and describe
        data = obj.export()
        json_str = obj.describe()
        ```
    """

    _domain_class: ClassVar[type[IBastionModel] | None] = None

    def __init__(
        self, 
        **kwargs,
    ) -> None:
        if kwargs:
            if self._domain_class is None:
                raise TypeError(f"{self.__class__.__name__} has no _domain_class")
            self.domain = self._domain_class(**kwargs)

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
