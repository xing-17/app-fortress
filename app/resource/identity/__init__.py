from __future__ import annotations

from app.resource.identity._common._factory import IdentityFactory
from app.resource.identity._common._identity import BaseIdentity
from app.resource.identity._common._identitysecret import BaseIdentitySecret
from app.resource.identity.aliyun.identity import AliyunIdentity
from app.resource.identity.aliyun.identitysecret import AliyunIdentitySecret
from app.resource.identity.local.identity import LocalIdentity
from app.resource.identity.local.identitysecret import LocalIdentitySecret

__all__ = [
    "LocalIdentity",
    "AliyunIdentity",
    "BaseIdentity",
    "IdentityFactory",
    "BaseIdentitySecret",
    "LocalIdentitySecret",
    "AliyunIdentitySecret",
]
