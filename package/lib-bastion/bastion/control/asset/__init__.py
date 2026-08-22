"""

Asset control layer implementations.

"""

from bastion.control.asset import (
    local,  # noqa: F401 - 副作用导入，触发装饰器
    oss,  # noqa: F401 - 副作用导入，触发装饰器
    s3,  # noqa: F401 - 副作用导入，触发装饰器
)
from bastion.control.asset.local import (
    ILocalAdaptorLike,
    LocalAdaptor,
    LocalAsset,
    LocalAssetModel,
    LocalAssetRef,
)
from bastion.control.asset.oss import (
    IOSSAdaptorLike,
    OSSAdaptor,
    OSSAsset,
    OSSAssetModel,
    OSSAssetRef,
)
from bastion.control.asset.s3 import (
    IS3AdaptorLike,
    S3Adaptor,
    S3Asset,
    S3AssetModel,
    S3AssetRef,
)

__all__ = [
    "LocalAsset",
    "LocalAssetModel",
    "LocalAssetRef",
    "ILocalAdaptorLike",
    "LocalAdaptor",
    "S3Asset",
    "S3AssetModel",
    "S3AssetRef",
    "IS3AdaptorLike",
    "S3Adaptor",
    "OSSAsset",
    "OSSAssetModel",
    "OSSAssetRef",
    "IOSSAdaptorLike",
    "OSSAdaptor",
]
