from __future__ import annotations

from enum import StrEnum


class ComputeRuntime(StrEnum):
    """
    Enumeration of supported compute runtimes.

    Values:
        LOCAL_PYEP: Local Python entrypoint.
        ALIYUN_FC: Alibaba Cloud Function Compute.
        AWS_LAMBDA: AWS Lambda.

    """

    LOCAL_PYEP = "local_pyep"
    ALIYUN_FC = "aliyun_fc"
    AWS_LAMBDA = "aws_lambda"
