"""
Bastion — Lightweight Python library for managing data pipeline ecosystems.

This library provides metadata-only management of data assets, pipelines,
and execution tracking across different compute platforms (local, AWS, Aliyun).

Quick Start:
    >>> from bastion import LocalAsset, LocalPyFnCompute, MemoryStore, Run
    >>>
    >>> # Create an asset
    >>> asset = LocalAsset(name="my_data", kind="parquet", path="./data")
    >>>
    >>> # Create a compute function
    >>> def my_task():
    >>>     print("Processing data...")
    >>>
    >>> compute = LocalPyFnCompute(name="my_compute", fn=my_task)
    >>>
    >>> # Create a run and execute
    >>> run = Run(bridge_name="my_bridge")
    >>> store = MemoryStore(name="my_store")
    >>> compute.execute(run=run, store=store)

"""

# Version
__version__ = "0.0.1"

# Core domain models (for advanced usage)
# Internal utilities (for library developers)
from bastion._internal import (
    IBastionClock,
    IBastionLog,
    IBastionModel,
)

# Control layer - Main user-facing classes
from bastion.control import (
    LocalAsset,
    LocalAssetModel,
    LocalPyFnCompute,
    LocalPyFnComputeModel,
    Run,
)
from bastion.domain import (
    AssetKind,
    AssetPlatform,
    BaseAssetModel,
    BaseBridgeModel,
    BaseComputeModel,
    BaseEventModel,
    BaseQualityModel,
    BaseRunModel,
    BaseStoreModel,
    ComputeKind,
    RunStatus,
)

# Infrastructure layer
from bastion.infra import (
    IStoreLike,
    MemoryStore,
)

__all__ = [
    # Version
    "__version__",
    # Domain enums and status
    "AssetKind",
    "AssetPlatform",
    "ComputeKind",
    "RunStatus",
    # Main user-facing classes
    "LocalAsset",
    "LocalPyFnCompute",
    "Run",
    "MemoryStore",
    # Store interface
    "IStoreLike",
    # Domain models (advanced)
    "BaseAssetModel",
    "BaseBridgeModel",
    "BaseComputeModel",
    "BaseEventModel",
    "BaseQualityModel",
    "BaseRunModel",
    "BaseStoreModel",
    # Control models
    "LocalAssetModel",
    "LocalPyFnComputeModel",
    # Internal utilities
    "IBastionClock",
    "IBastionLog",
    "IBastionModel",
]
