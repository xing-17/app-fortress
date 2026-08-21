"""

Asset control layer implementations.

"""

from bastion.control.asset import (
    local,  # noqa: F401 - 副作用导入，触发装饰器
)
from bastion.control.asset.local import (
    LocalAsset,
    LocalAssetModel,
    LocalAssetRef,
)

__all__ = [
    "LocalAsset",
    "LocalAssetModel",
    "LocalAssetRef",
]
