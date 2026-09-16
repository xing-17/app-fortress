from __future__ import annotations

from app.resource.identity._common._base import BaseIdentity
from app.resource.identity.aliyun.aliyun import AliyunIdentity
from app.resource.identity.local.local import LocalIdentity

__all__ = [
    "LocalIdentity",
    "AliyunIdentity",
    "BaseIdentity",
]
