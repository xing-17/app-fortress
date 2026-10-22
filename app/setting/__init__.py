from __future__ import annotations

from ._compute import (
    FCComputeSetting,
    PyEntrypointComputeSetting,
    UnionComputeSetting,
)
from ._identity import (
    AliyunIdentitySetting,
    LocalIdentitySetting,
    UnionIdentitySetting,
)
from ._log import LogSetting
from ._source import (
    ABSSourceSetting,
    NSWVGSourceSetting,
    TushareSourceSetting,
    UnionSourceSetting,
)
from ._store import (
    FileStoreSetting,
    OSSStoreSetting,
    UnionStoreSetting,
)
from ._vault import (
    LocalVaultSetting,
    OSSVaultSetting,
    UnionVaultSetting,
)
from .service import (
    AbstractHostServiceSetting,
    AbstractServiceSetting,
    AuthSetting,
    DRASetting,
    MachineServiceSetting,
    McpHostServiceSetting,
    NodeEndpointSetting,
    NodeServiceSetting,
    ServicesSetting,
    TokenSetting,
    WebHostServiceSetting,
)
from .system import (
    SystemLogSetting,
    SystemSetting,
)

__all__ = [
    "FCComputeSetting",
    "PyEntrypointComputeSetting",
    "UnionComputeSetting",
    "AliyunIdentitySetting",
    "LocalIdentitySetting",
    "UnionIdentitySetting",
    "LogSetting",
    "ABSSourceSetting",
    "NSWVGSourceSetting",
    "TushareSourceSetting",
    "UnionSourceSetting",
    "OSSStoreSetting",
    "FileStoreSetting",
    "UnionStoreSetting",
    "LocalVaultSetting",
    "OSSVaultSetting",
    "UnionVaultSetting",
    "AbstractHostServiceSetting",
    "AbstractServiceSetting",
    "AuthSetting",
    "DRASetting",
    "MachineServiceSetting",
    "NodeEndpointSetting",
    "NodeServiceSetting",
    "McpHostServiceSetting",
    "WebHostServiceSetting",
    "ServicesSetting",
    "TokenSetting",
    "SystemLogSetting",
    "SystemSetting",
]
