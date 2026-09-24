from __future__ import annotations


class IAbstractUtility:
    def __init__(
        self,
        **kwargs,
    ):
        raise TypeError("IAbstractUtility is not intended to be initialized")
