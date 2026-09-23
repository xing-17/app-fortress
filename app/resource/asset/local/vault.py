from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.internal.util.path import IPath
from app.resource._global.identities import GlobalIdentities
from app.resource.asset._common._vault import BaseVault
from app.resource.identity.local import LocalIdentity
from app.setting._vault import LocalVaultSetting


class LocalVault(BaseVault):
    """
    Local vault contains a collection of local assets and associated assetfile.

    Args:
        name (str | None): Local vault name
        path (str | Path): Local vault path
        identity (LocalIdentity): Local vault identity
        filesystem (Literal[AssetFilesystem.LOCAL]): Asset filesystem type, fixed as LOCAL
        platform (Literal[Platform.LOCAL]): Asset platform type, fixed as LOCAL
        description (str): Local vault description information
        tags (dict[str, str]): Local vault tags

    Methods:
        from_setting(cls, setting: LocalVaultSetting) -> LocalVault:
            Create a LocalVault instance from a LocalVaultSetting object.

    Example:
        >>> from app.resource.asset.local.vault import LocalVault
        >>> from app.setting._vault import LocalVaultSetting
        >>> setting = LocalVaultSetting(name="my_vault", path="/tmp/my_vault")
        >>> vault = LocalVault.from_setting(setting)
        >>> vault.name
        'my_vault'

    """

    # Inherited from BaseVault
    # - name: str | None
    # - description: str
    # - tags: dict[str, str]
    path: str | Path = Field(
        ...,
        description="[Required] Local vault path",
    )
    identity: LocalIdentity = Field(
        default_factory=LocalIdentity.default,
        description="[Optional] Local vault identity",
    )
    filesystem: Literal[AssetFilesystem.LOCAL] = AssetFilesystem.LOCAL
    platform: Literal[Platform.LOCAL] = Platform.LOCAL

    @model_validator(mode="after")
    def _derive_path(self) -> "LocalVault":
        _path: Path = IPath.resolve(self.path)
        if not _path.exists():
            _path.mkdir(parents=True, exist_ok=True)
        if not _path.is_dir():
            raise ValueError(f"Path {self.path} must be a directory")
        object.__setattr__(self, "path", _path)
        return self

    @classmethod
    def from_setting(
        cls,
        setting: LocalVaultSetting,
    ) -> LocalVault:
        return cls(
            name=setting.name,
            path=setting.path,
            identity=GlobalIdentities.resolve(
                value=getattr(setting, "identity", None),
                platform=Platform.LOCAL,
                default=LocalIdentity.default(),
            ),
            description=setting.description,
            tags=setting.tags,
        )

    @property
    def uri(self) -> str:
        return f"file://{self.path}"

    @property
    def frn(self) -> str:
        return f"vault:{self.platform}:{self.path}"
