from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

import duckdb

from app.internal.model.dra import DRAMount, DRARejectedError

_IDENT = re.compile(r"^[a-z_][a-z0-9_]{0,62}\Z")
_GLOB_CHARS = "*?["
_BAD_PATH_CHARS = re.compile(r"[\x00-\x1f'\"\\]")

# Schemas the engine owns
# a source of the same name would shadow or collide with them.
RESERVED_SCHEMAS = frozenset({"main", "temp", "system", "information_schema", "pg_catalog"})


class DRAGuard:
    @staticmethod
    def check_statement(
        conn: duckdb.DuckDBPyConnection,
        sql: str,
    ) -> None:
        # Empty statement check
        if not isinstance(sql, str) or not sql.strip():
            _expl: str = "empty statement"
            raise DRARejectedError(_expl)

        # Extract statements using DuckDB parser
        try:
            _stmts = conn.extract_statements(sql)
        except duckdb.Error as e:
            raise DRARejectedError(f"cannot parse statement: {e}") from e

        # Ensure exactly one statement is present and it is a SELECT statement
        if len(_stmts) != 1:
            raise DRARejectedError(f"exactly one statement is allowed, got {len(_stmts)}")

        # Get the type of the statement
        _type = _stmts[0].type
        if _type != duckdb.StatementType.SELECT:
            raise DRARejectedError(f"{_type.name} statement is not supported, use SELECT")

    @staticmethod
    def check_identifier(
        value: str,
        what: str,
    ) -> str:
        if not isinstance(value, str) or not _IDENT.match(value):
            raise DRARejectedError(f"invalid {what} {value!r}, expected [a-z_][a-z0-9_]* (max 63)")
        return value

    @staticmethod
    def split_dataset_name(name: str) -> tuple[str, str]:
        if isinstance(name, str):
            _parts = name.split(".")
        else:
            _parts = []

        # Ensure the dataset name has exactly two parts separated by a dot
        if len(_parts) != 2:
            raise DRARejectedError(f"dataset name must be '<source>.<dataset>', got {name!r}")

        # Extract source and dataset parts
        _source = DRAGuard.check_identifier(_parts[0], "source name")
        _dataset = DRAGuard.check_identifier(_parts[1], "dataset name")
        if _source in RESERVED_SCHEMAS:
            raise DRARejectedError(f"source name {_source!r} is reserved")
        return _source, _dataset

    @staticmethod
    def check_mount(mount: DRAMount) -> tuple[str, str]:
        """
        Re-validate a mount on the DRA side, the input is not trusted

        """
        # Ensure the mount has a valid scheme
        if mount.scheme not in ("file", "s3"):
            raise DRARejectedError(f"scheme {mount.scheme!r} is not supported yet")

        # Validate partition keys and mount paths
        for _key in mount.partitions:
            DRAGuard.check_identifier(_key, "partition key")

        if mount.scheme == "s3":
            return DRAGuard._check_s3_mount(mount)

        for _value in (mount.scope, mount.pattern):
            if _BAD_PATH_CHARS.search(_value):
                # Found invalid characters in the mount path
                raise DRARejectedError("invalid characters in mount")
            if not Path(_value).is_absolute():
                # Ensure the mount path is absolute
                raise DRARejectedError("mount paths must be absolute")
            if ".." in PurePosixPath(_value).parts:
                # Prevent directory traversal in mount paths
                raise DRARejectedError("'..' is not allowed in mount paths")

        _scope = Path(mount.scope).resolve()
        _fixed: list[str] = []
        _rest: list[str] = []
        for _part in Path(mount.pattern).parts:
            if _rest or any(c in _part for c in _GLOB_CHARS):
                _rest.append(_part)
            else:
                _fixed.append(_part)

        # Determine the fixed prefix and the rest of the pattern parts
        _prefix = Path(*_fixed).resolve()
        if not _prefix.is_relative_to(_scope):
            raise DRARejectedError("pattern is outside the scope")
        return str(_scope), str(_prefix.joinpath(*_rest))

    @staticmethod
    def _check_s3_mount(mount: DRAMount) -> tuple[str, str]:
        for _value in (mount.scope, mount.pattern):
            if _BAD_PATH_CHARS.search(_value):
                raise DRARejectedError("invalid characters in mount")
            if not _value.startswith("s3://") or len(_value) <= len("s3://"):
                raise DRARejectedError("s3 mount paths must start with 's3://'")
            if ".." in _value.split("/"):
                raise DRARejectedError("'..' is not allowed in mount paths")
        if "/" not in mount.scope[len("s3://") :].rstrip("/") and mount.scope.count("/") < 3:
            raise DRARejectedError("s3 scope must name a bucket")
        return mount.scope, mount.pattern

    @staticmethod
    def stringify_sql(value: str) -> str:
        _string = value.replace("'", "''")
        return "'" + _string + "'"
