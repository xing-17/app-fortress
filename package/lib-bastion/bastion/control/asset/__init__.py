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
    ILocalAdaptorLike,
    LocalAdaptor,
)
from bastion.control.asset import (
    s3,  # noqa: F401 - 副作用导入，触发装饰器
)
from bastion.control.asset.s3 import (
    S3Asset,
    S3AssetModel,
    S3AssetRef,
    IS3AdaptorLike,
    S3Adaptor,
)
from bastion.control.asset import (
    oss,  # noqa: F401 - 副作用导入，触发装饰器
)
from bastion.control.asset.oss import (
    OSSAsset,
    OSSAssetModel,
    OSSAssetRef,
    IOSSAdaptorLike,
    OSSAdaptor,
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
