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
from bastion.control.asset import (
    s3,  # noqa: F401 - 副作用导入，触发装饰器
)
from bastion.control.asset.s3 import (
    S3Asset,
    S3AssetModel,
    S3AssetRef,
)
from bastion.control.asset import (
    oss,  # noqa: F401 - 副作用导入，触发装饰器
)
from bastion.control.asset.oss import (
    OSSAsset,
    OSSAssetModel,
    OSSAssetRef,
)

__all__ = [
    "LocalAsset",
    "LocalAssetModel",
    "LocalAssetRef",
    "S3Asset",
    "S3AssetModel",
    "S3AssetRef",
    "OSSAsset",
    "OSSAssetModel",
    "OSSAssetRef",
]
