from __future__ import annotations

from bastion.control.access.base.factory import AccessFactory
from bastion.control.access.base.protocol import IAccessLike
from bastion.domain.access.access import AbstractAccessDomain
from bastion.domain.access.platform import AccessPlatform
from bastion.internal.idomainobject import IDomainObject


class AWSAccessDomain(AbstractAccessDomain):
    """
    AWS Access Domain class for managing credentials.

    source: https://docs.aws.amazon.com/boto3/latest/reference/core/session.html

    Attributes:
        name: Name of the access profile.
        platform: AccessPlatform fixed to AWS.
        access_key_id: AWS access key ID.
        access_key_secret: AWS secret access key.
        session_token: AWS session token for temporary credentials.
        profile: AWS CLI profile name.
        region: AWS region name.
        account: AWS account ID.
        tags: Dictionary of tags associated with the access profile.

    """

    platform: AccessPlatform = AccessPlatform.AWS
    access_key_id: str | None = None
    access_key_secret: str | None = None
    session_token: str | None = None
    profile: str | None = None
    region: str | None = None
    account: str | None = None


@AccessFactory.add(AccessPlatform.AWS)
class AWSAccess(
    IDomainObject,
    IAccessLike,
):
    """
    AWS access control wrapper for managing AWS credentials.

    Attributes:
        name: Name of the access profile.
        platform: AccessPlatform fixed to AWS.
        access_key_id: AWS access key ID.
        access_key_secret: AWS secret access key.
        session_token: AWS session token for temporary credentials.
        profile: AWS CLI profile name.
        region: AWS region name.
        account: AWS account ID.
        tags: Tags associated with the access profile.

    """

    _domain_class = AWSAccessDomain

    def __init__(
        self,
        name: str | None = None,
        access_key_id: str | None = None,
        access_key_secret: str | None = None,
        session_token: str | None = None,
        profile: str | None = None,
        region: str | None = None,
        account: str | None = None,
        tags: dict[str, str] = None,
    ):
        super().__init__(
            name=name,
            platform=AccessPlatform.AWS,
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            session_token=session_token,
            profile=profile,
            region=region,
            account=account,
            tags=tags,
        )

    def export(self) -> dict[str, str | None]:
        _key_id = self.access_key_id
        _expr_key_id = None if not _key_id else _key_id[0:4] + "******"
        _secret = self.access_key_secret
        _expr_secret = None if not _secret else _secret[0:4] + "******"
        _token = self.session_token
        _expr_token = None if not _token else _token[0:4] + "******"
        return {
            "name": self.name,
            "platform": self.platform.value,
            "access_key_id": _expr_key_id,
            "access_key_secret": _expr_secret,
            "session_token": _expr_token,
            "profile": self.profile,
            "region": self.region,
            "account": self.account,
            "tags": self.tags,
        }
