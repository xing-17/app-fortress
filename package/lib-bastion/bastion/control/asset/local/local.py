from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import Field, computed_field

from bastion._internal.object import IBastionObject
from bastion.control.asset.base.base import IAssetLike
from bastion.domain.platform import Platform
from bastion.control.asset.base.factory import AssetFactory
from bastion.domain.asset import BaseAssetModel
from bastion.domain.assetref import BaseAssetRefModel

logger = logging.getLogger(__name__)


class LocalAssetRef(BaseAssetRefModel):
    """
    Represents a single file on the local filesystem.

    This is a reference to an actual file with its metadata and partition information.

    Attributes:
        uri: Absolute file path (e.g., "/home/user/data/year=2024/sales.parquet")
        name: Filename with extension (e.g., "sales.parquet")
        stem: Filename without extension (e.g., "sales")
        size: File size in bytes (None if file doesn't exist)
        modified_at: File last modified timestamp (None if unavailable)
        partitions: Partition values from path (e.g., {"year": "2024"})
        
    """
    @computed_field
    @property
    def name(self) -> str:
        return Path(self.uri).name
    
    @computed_field
    @property
    def stem(self) -> str:
        return Path(self.uri).stem

class LocalAssetModel(BaseAssetModel):
    """
    Domain model for local filesystem assets.

    This model stores the core information about a local asset without any behavior.

    Attributes:
        name: Asset identifier
        path: Base directory path where files are stored
        kind: File format (parquet, csv, json, etc.)
        partitions: List of partition column names (e.g., ["year", "month"])
        refs: List of file references found during inspection
        description: Human-readable description
        owner: Owner identifier
        metadata: Custom key-value pairs
        tags: Classification tags

    """
    platform: Platform = Platform.LOCAL
    path: str = Field(
        ...,
        description="Path of the local asset in the filesystem",
    )


@AssetFactory.register("local")
class LocalAsset(
    IBastionObject,
    IAssetLike,
):
    """
    Manages a local filesystem asset and its files.

    Use this class to work with data stored on the local filesystem. It can discover
    files, build glob patterns, and manage partitioned data.

    Attributes:
        domain: The underlying domain model with core data
        name: Asset identifier
        kind: File format (parquet, csv, json, etc.)
        platform: Always Platform.LOCAL for local assets
        path: Base directory path where files are stored
        partitions: List of partition column names (e.g., ["year", "month"])
        refs: List of discovered file references
        description: Human-readable description
        owner: Owner identifier
        metadata: Custom key-value pairs
        tags: Classification tags

    Methods:
        inspect() -> list[LocalAssetRef]:
            Scans the filesystem and returns all matching files as references.
            Updates the asset's refs list.
            
        _resolve_path() -> Path:
            Converts the path to an absolute Path object (expands ~ and resolves ..)
            
        _resolve_glob_pattern() -> str:
            Creates a glob pattern based on partitions and file kind.
            Example: "year=*/month=*/*.parquet"
            
        _resolve_partition(path: Path) -> dict[str, str]:
            Extracts partition values from a file path.
            Example: "/data/year=2024/month=01/file.parquet" -> {"year": "2024", "month": "01"}

    Example:
        ```python
        # Create an asset for partitioned parquet files
        asset = LocalAsset(
            name="sales_data",
            kind=AssetKind.PARQUET,
            platform=Platform.LOCAL,
            path="~/data/sales",
            partitions=["year", "month"],
        )

        # Scan the filesystem to find all matching files
        refs = asset.inspect()
        print(f"Found {len(refs)} files")
        
        # Each ref has file details
        for ref in refs:
            print(f"{ref.name}: {ref.size} bytes, partitions: {ref.partitions}")
        ```
    """

    _domain_class: type[LocalAssetModel] = LocalAssetModel

    def _resolve_path(self) -> Path:
        """Convert the asset path to an absolute Path object with ~ and .. resolved."""
        return Path(self.path).expanduser().resolve()

    def _resolve_glob_pattern(self) -> str:
        """Build a glob pattern based on partitions and file kind (e.g., 'year=*/month=*/*.parquet')."""
        _self_parts = self.domain.partitions or []
        _self_kind = self.domain.kind.value
        parts = []
        if _self_parts:
            parts.extend([f"{p}=*" for p in _self_parts])
        parts.append(f"*{_self_kind}")
        return str(Path(*parts))

    def _resolve_partition(
        self,
        path: Path,
    ) -> dict[str, str]:
        """Extract partition values from a file path (e.g., 'year=2024/month=01' -> {'year': '2024', 'month': '01'})."""
        if not self.domain.partitions:
            return {}
        result: dict[str, str] = {}
        relative = path.relative_to(self._resolve_path())
        for part in relative.parts:
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            if key in self.domain.partitions:
                result[key] = value
        return result

    def inspect(
        self,
        **kwargs: Any,
    ) -> list[LocalAssetRef]:
        """
        Scan the filesystem and discover all files belonging to this asset.
        
        This method searches the asset's path for files matching the glob pattern,
        extracts partition values, collects file metadata, and stores references.

        Returns:
            List of file references with metadata (path, size, timestamps, partitions).
            Also updates self.domain.refs with the discovered files.
        
        """
        _root: Path = self._resolve_path()
        _pattern: str = self._resolve_glob_pattern()
        refs: list[LocalAssetRef] = []

        # Check if the path exists
        if not _root.exists():
            logger.warning(f"Path does not exist: {_root}")
        # Check if the path is a file
        elif _root.is_file():
            logger.warning(f"Path is not a directory: {_root}")
        else:
            # Use rglob to find all files matching the pattern
            for file in _root.rglob(_pattern):
                _stat = file.stat()
                _uri: str = str(file.expanduser().resolve())
                _parts: dict[str, str] = self._resolve_partition(file)
                _size: int = _stat.st_size
                _updated_at: datetime = datetime.fromtimestamp(
                    timestamp=_stat.st_mtime,
                    tz=UTC,
                )
                _ref = LocalAssetRef(
                    uri=_uri,
                    partitions=_parts,
                    size=_size,
                    modified_at=_updated_at,
                )
                refs.append(_ref)

        # Store the refs in the instance for later use
        logger.info(f"Found {len(refs)} files in  {_pattern}")
        self.domain.refs = refs
        return refs
