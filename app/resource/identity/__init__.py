from __future__ import annotations

from app.resource.identity._common._factory import IdentityFactory
from app.resource.identity._common._identity import BaseIdentity
from app.resource.identity._common._secret import BaseSecret
from app.resource.identity.aliyun.identity import AliyunIdentity
from app.resource.identity.aliyun.secret import AliyunSecret
from app.resource.identity.local.identity import LocalIdentity
from app.resource.identity.local.secret import LocalSecret

__all__ = [
    "LocalIdentity",
    "AliyunIdentity",
    "BaseIdentity",
    "IdentityFactory",
    "BaseSecret",
    "LocalSecret",
    "AliyunSecret",
]
