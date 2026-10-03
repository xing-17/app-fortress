from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.internal.util.path import IPath
from app.resource._client.local.client import LocalObjectClient
from app.resource._global.identities import GlobalIdentities
from app.resource.identity._common._base import BaseIdentity
from app.resource.identity.local import LocalIdentity
from app.resource.store._common._table import BaseTable


class FileStoreTable(BaseTable):
    """
    File store table backed by a single JSON file directly under its parent database's path.

    Only constructible via `FileStoreDatabase.table(name)`.

    Args:
        name (str): Table name, single path segment
        path (Path): Table file path, derived from the parent database path and name
        identity (LocalIdentity): Local identity associated with the table
        storesystem (Literal[StoreSystem.FILE]): Store system type, fixed as FILE
        platform (Literal[Platform.LOCAL]): Store platform type, fixed as LOCAL
        tags (dict[str, str]): Table tags

    Methods:
        write(key: str, data: Any, strict: bool = False) -> None:
            Upsert data for key into the table's flat {key: data} JSON content.
        read(key: str, strict: bool = False) -> Any:
            Read data for key, or None if missing.
        delete(key: str, strict: bool = False) -> None:
            Delete a key's value; raises KeyError if missing and strict is True.

    """

    storesystem: Literal[StoreSystem.FILE] = StoreSystem.FILE
    platform: Literal[Platform.LOCAL] = Platform.LOCAL
    path: Path = Field(
        ...,
        description="[NoOps] Table file path, derived from the parent database path and name",
    )
    identity: LocalIdentity = Field(
        ...,
        description="[NoOps] Local identity associated with the table",
    )

    @model_validator(mode="after")
    def _derive_path(self) -> "FileStoreTable":
        _p = IPath.resolve(value=self.path)
        if _p.exists() and not _p.is_file():
            raise ValueError(f"Path {_p} exists and must be a file")
        object.__setattr__(self, "path", _p)
        return self

    @model_validator(mode="after")
    def _derive_identity(self) -> "FileStoreTable":
        _identity: BaseIdentity = GlobalIdentities.resolve(
            value=self.identity,
            default=LocalIdentity.default(),
            platform=Platform.LOCAL,
        )
        object.__setattr__(self, "identity", _identity)
        return self

    def write(
        self,
        key: str,
        data: Any,
        strict: bool = False,
    ) -> None:
        _content = self._load_content(strict=strict)
        _content[key] = data
        try:
            _stringfied: str = json.dumps(_content, ensure_ascii=False)
            _bytes: bytes = _stringfied.encode("utf-8")
            LocalObjectClient.write_bytes(self.path, _bytes)
        except Exception as e:
            self._handle_io_error(exception=e, strict=strict)

    def read(
        self,
        key: str,
        strict: bool = False,
    ) -> Any:
        _content = self._load_content(strict=strict)
        return _content.get(key)

    def delete(
        self,
        key: str,
        strict: bool = False,
    ) -> None:
        _content = self._load_content(strict=strict)
        if key in _content:
            try:
                del _content[key]
                _stringfied: str = json.dumps(_content, ensure_ascii=False)
                _bytes: bytes = _stringfied.encode("utf-8")
                LocalObjectClient.write_bytes(self.path, _bytes)
            except Exception as e:
                self._handle_io_error(exception=e, strict=strict)
        else:
            _error: KeyError = KeyError(f"Key {key} does not exist")
            self._handle_io_error(exception=_error, strict=strict)

    def _load_content(
        self,
        strict: bool = False,
    ) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            _bytes: bytes = LocalObjectClient.read_bytes(self.path)
            return json.loads(_bytes)
        except Exception as e:
            self._handle_io_error(exception=e, strict=strict)
            return {}

    def export(self) -> dict[str, Any]:
        _result: dict = super().export()
        _result["identity"] = self.identity.name
        return _result
