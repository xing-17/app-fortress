from __future__ import annotations

from importlib import import_module
from types import ModuleType

from app.internal.constant.assetfilesystem import AssetFilesystem
from app.resource.asset._common._vault import BaseVault
from app.setting._vault import UnionVaultSetting


class VaultFactory:
    """
    Factory class for asset vault instances by filesystem type.

    Attributes:
        _registry (dict[AssetFilesystem, str]):
            A mapping of filesystem types to their corresponding module and class paths.

    Example:
        >>> klass = VaultFactory.get(AssetFilesystem.LOCAL)
        >>> instance = klass(
        ...     name="my_vault",
        ...     filesystem=AssetFilesystem.LOCAL,
        ... )

    """

    # Registry mapping filesystem types to their corresponding module and class paths.
    _registry: dict[AssetFilesystem, str] = {
        AssetFilesystem.LOCAL: "app.resource.asset.local.vault:LocalVault",
        AssetFilesystem.OSS: "app.resource.asset.oss.vault:OSSVault",
    }

    @classmethod
    def get(
        cls,
        filesystem: AssetFilesystem,
    ) -> type[BaseVault]:
        _target: str | None = cls._registry.get(filesystem)
        if not _target:
            raise ValueError(f"No store registered for filesystem {filesystem}")

        # Dynamically import the module and callable class
        _module_path, _klass_name = _target.split(":")
        _module: ModuleType = import_module(_module_path)
        _klass: type[BaseVault] = getattr(_module, _klass_name)

        # Ensure imported class is a subclass of BaseVault
        if not isinstance(_klass, type):
            raise TypeError(f"Expecting class, got {_klass!r}.")
        if not issubclass(_klass, BaseVault):
            raise TypeError(f"Expecting subclass of BaseVault, got {_klass!r}.")
        return _klass

    @classmethod
    def load(
        cls,
        setting: UnionVaultSetting,
    ) -> BaseVault:
        _klass: type[BaseVault] = cls.get(setting.filesystem)
        if not _klass:
            raise ValueError(f"Vault class '{setting.filesystem}' not found")
        return _klass.from_setting(setting)
