from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict, Field, SecretStr, model_validator

from app.internal.abstract.domain import IAbstractDomain

_GLOB_CHARS = "*?["


class DRAMount(IAbstractDomain):
    """
    A DRA Mount used to enable the DRA system to access assets

    This class will be used in embeded OLAP such as DuckDB Engine

    Args:
    ----------
        scheme (Literal["file", "s3"]):
            scheme of the mount, either "file" or "s3"
        pattern (str):
            URL type glob pattern, must be inside the scope
        scope (str):
            Allowed prefix, must end with '/' and be inside the scope; also used as the SCOPE of the secret and an entry in allowed_directories
        partitions (list[str]):
            Partition keys, when non-empty the engine reads by hive partition
        endpoint / region / url_style (str | None):
            Required for s3, must be empty for file
        region (str | None):
            S3 region, must be empty for file
        url_style (Literal["vhost", "path"] | None):
            S3 URL style, must be empty for file
        use_ssl (bool):
            Default True
        key_id (str | None):
            S3 key ID, must be empty for file
        secret (SecretStr | None):
            S3 secret, must be empty for file; does not appear in repr and export
        session_token (SecretStr | None):
            S3 session token, must be empty for file


    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    scheme: Literal["file", "s3"] = Field(default="file")
    pattern: str = Field(
        ...,
        description="URL type glob pattern, must be inside the scope",
    )
    scope: str = Field(
        ...,
        description="Allowed prefix, must end with '/' and be inside the scope",
    )
    partitions: list[str] = Field(
        default_factory=list,
        description="Partition keys, when non-empty the engine reads by hive partition",
    )
    endpoint: str | None = Field(
        default=None,
        description="S3 endpoint, required for s3 and must be empty for file",
    )
    region: str | None = Field(
        default=None,
        description="S3 region, required for s3 and must be empty for file",
    )
    url_style: Literal["vhost", "path"] | None = Field(
        default=None,
        description="S3 URL style, required for s3 and must be empty for file",
    )
    use_ssl: bool = Field(
        default=True,
        description="Whether to use SSL for S3, default True",
    )
    key_id: str | None = Field(
        default=None,
        description="S3 key ID, must be empty for file",
    )
    secret: SecretStr | None = Field(
        default=None,
        description="S3 secret, must be empty for file; does not appear in repr and export",
    )
    session_token: SecretStr | None = Field(
        default=None,
        description="S3 session token, must be empty for file",
    )

    @model_validator(mode="after")
    def _validate_location(self) -> DRAMount:
        if not self.scope.endswith("/"):
            raise ValueError("scope must end with '/'")
        if any(c in self.scope for c in _GLOB_CHARS):
            raise ValueError("scope must not contain glob characters")
        if not self.pattern.startswith(self.scope):
            raise ValueError("pattern must be inside scope")
        return self

    @model_validator(mode="after")
    def _validate_scheme(self) -> DRAMount:
        _remote = (self.endpoint, self.region, self.url_style)
        _creds = (self.key_id, self.secret, self.session_token)
        if self.scheme == "s3":
            if any(v is None for v in _remote):
                raise ValueError("s3 requires endpoint, region and url_style")
        elif any(v is not None for v in (*_remote, *_creds)):
            raise ValueError("file takes no endpoint, region, url_style or credentials")
        if (self.key_id is None) != (self.secret is None):
            raise ValueError("key_id and secret must be set together")
        if self.session_token is not None and self.key_id is None:
            raise ValueError("session_token requires key_id")
        return self
