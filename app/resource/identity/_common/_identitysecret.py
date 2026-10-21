from __future__ import annotations

from abc import ABC
from typing import ClassVar

from pydantic import ConfigDict

from app.internal.abstract.domain import IAbstractDomain
from app.internal.constant.platform import Platform


class BaseIdentitySecret(
    IAbstractDomain,
    ABC,
):
    """
    Base class for secrets, a short-lived snapshot produced by an identity for downstream use

    Values are held as `SecretStr`, so repr, export and describe never show them.
    Do not use `sha256()` as a fingerprint, the masked export makes different secrets collide.

    Attributes:
    ----------
        platform (Platform):
            Platform type, declared by the subclass

    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Enforced public class variables
    platform: ClassVar[Platform]
