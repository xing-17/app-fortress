from __future__ import annotations

from enum import StrEnum


class ComputeRuntime(StrEnum):
    """
    Enumeration of supported compute runtimes

    Values:
    ----------
        PYENTRYPOINT: Local Python entrypoint, executed in the current or a child process
        FC: Aliyun Function Compute function

    """

    PYENTRYPOINT = "pyentrypoint"
    FC = "fc"
