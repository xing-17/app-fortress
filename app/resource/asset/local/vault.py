from __future__ import annotations

from pathlib import Path
from typing import ClassVar, Literal

from pydantic import Field, model_validator

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.internal.util.path import IPath
from app.resource._global.identities import GlobalIdentities
from app.resource.asset._common._vault import BaseVault
from app.resource.asset.local.asset import LocalAsset
from app.resource.identity._common._identity import BaseIdentity
from app.resource.identity.local import LocalIdentity
from app.setting._identity import AbstractIdentitySetting
from app.setting._vault import LocalVaultSetting
from app.internal.util.frn import IFrn


class LocalVault(BaseVault):
    """
    Local vault contains a collection of local assets and associated assetfiles.

    Args:
        name (str | None): Local vault name
        path (str | Path): Local vault path
        identity (LocalIdentity | AbstractIdentitySetting | str | None): Local vault identity
        filesystem (Literal[AssetFilesystem.LOCAL]): Asset filesystem type, fixed as LOCAL
        platform (Literal[Platform.LOCAL]): Asset platform type, fixed as LOCAL
        description (str): Local vault description information
        tags (dict[str, str]): Local vault tags

    Methods:
        from_setting(cls, setting: LocalVaultSetting) -> LocalVault:
            Create a LocalVault instance from a LocalVaultSetting object.
        asset(rel: str, filekind=None, partitions=None) -> LocalAsset:
            Create a LocalAsset scoped to a path relative to the vault, rejecting paths that escape it.

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
    path: str | Path | None = Field(
        default=None,
        description="[Required] Local vault path, default ./vault",
    )
    identity: LocalIdentity | AbstractIdentitySetting | str | None = Field(
        default=None,
        description="[Optional] Local vault identity",
    )
    filesystem: Literal[AssetFilesystem.LOCAL] = AssetFilesystem.LOCAL
    platform: Literal[Platform.LOCAL] = Platform.LOCAL

    # Class-level attributes
    default_path: ClassVar[str] = "./vault"

    @model_validator(mode="after")
    def _derive_path(self) -> "LocalVault":
        _path: Path = IPath.resolve(
            value=self.path,
            default=Path(self.default_path),
            ensure=True,
        )
        if not _path.is_dir():
            raise ValueError(f"Path {self.path} must be a directory")
        object.__setattr__(self, "path", _path)
        return self

    @model_validator(mode="after")
    def _derive_identity(self) -> "LocalVault":
        _identity: BaseIdentity = GlobalIdentities.resolve(
            value=self.identity,
            default=LocalIdentity.default(),
            platform=Platform.LOCAL,
        )
        object.__setattr__(self, "identity", _identity)
        return self

    @classmethod
    def from_setting(
        cls,
        setting: LocalVaultSetting,
    ) -> LocalVault:
        return cls(
            name=setting.name,
            path=setting.path,
            identity=setting.identity,
            description=setting.description,
            tags=setting.tags,
        )

    @property
    def uri(self) -> str:
        return f"file://{self.path}"

    @property
    def frn(self) -> str:
        return IFrn.resolve(
            [
                "vault",
                f"platform={self.platform}",
                f"path={self.path}",
            ]
        )

    def asset(
        self,
        rel: str,
        filekind: AssetFileKind | None = None,
        partitions: list[str] | None = None,
    ) -> LocalAsset:
        # asset object has to be the subdirectory of the vault path
        _resolved = (self.path / rel).expanduser().resolve()
        if not _resolved.is_relative_to(self.path):
            raise ValueError(f"Rel '{rel}' escapes vault {self.path}")

        # create and return the LocalAsset instance
        return LocalAsset(
            path=_resolved,
            filekind=filekind,
            partitions=partitions,
            identity=self.identity,
            tags=self.tags,
        )
