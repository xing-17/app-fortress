from __future__ import annotations

from importlib import import_module
from types import ModuleType

from app.internal.constant.platform import Platform
from app.resource.identity._common._base import BaseIdentity
from app.setting._identity import UnionIdentitySetting


class IdentityFactory:
    """
    Factory class for creating identity instances based on the platform.

    Attributes:
        _registry (dict[str, str]):
            A mapping of platform names to their corresponding module and class paths.

    Example:
        >>> klass = IdentityFactory.get(Platform.ALIYUN)
        >>> instance = klass(
        ...     name="my_identity",
        ...     platform=Platform.ALIYUN,
        ... )
    """

    # Registry mapping platform name to corresponding module and class paths.
    _registry: dict[str, type[BaseIdentity]] = {
        Platform.ALIYUN: "app.resource.identity.aliyun.aliyun:AliyunIdentity",
        Platform.LOCAL: "app.resource.identity.local.local:LocalIdentity",
    }

    @classmethod
    def get(
        cls,
        platform: Platform | str,
    ) -> type[BaseIdentity] | None:
        _target: str | None = cls._registry.get(platform)
        if not _target:
            raise ValueError(f"'{platform}' identity not found.")

        # Dynamically import the module
        _module_path, _klass_name = _target.split(":")
        _module: ModuleType = import_module(_module_path)
        _klass: type[BaseIdentity] = getattr(_module, _klass_name)

        # Ensure imported class is subclass of BaseIdentity
        if not isinstance(_klass, type):
            raise TypeError(f"Expecting class, got {_klass!r}.")
        if not issubclass(_klass, BaseIdentity):
            raise TypeError(f"Expecting subclass of BaseIdentity, got {_klass!r}.")
        return _klass

    @classmethod
    def load(
        cls,
        setting: UnionIdentitySetting,
    ) -> BaseIdentity:
        klass: type[BaseIdentity] | None = cls.get(setting.platform)
        if not klass:
            raise ValueError(f"Identity class for platform '{setting.platform}' not found.")
        return klass.from_setting(setting)
