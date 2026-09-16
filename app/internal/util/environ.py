from __future__ import annotations

import os

from app.internal.abstract.utility import IAbstractUtility


class IEnviron(IAbstractUtility):
    """
    Utility class for interacting with env vars.

    Methods:
        get_variable(name: str | None, default: str | None = None) -> str | None
            Retrieves the value of an environment variable, returning the default if not set.
        set_variable(name: str, value: str) -> None
            Sets the value of an environment variable.

    """

    @staticmethod
    def get_variable(
        name: str | None,
        default: str | None = None,
    ) -> str | None:
        # No variable name to look up (e.g. optional osenv_* setting unset) -> just use the default
        if name is None:
            return default
        return os.getenv(name, default)

    @staticmethod
    def set_variable(
        name: str,
        value: str,
    ) -> None:
        os.environ[name] = value
