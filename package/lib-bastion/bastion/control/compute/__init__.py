"""

Compute control layer implementations.

"""

from bastion.control.compute import (
    pyasyncentrypoint,  # noqa: F401 - 副作用导入，触发装饰器
    pyentrypoint,  # noqa: F401 - 副作用导入，触发装饰器
)
from bastion.control.compute.base.base import (
    IComputeLike,
)
from bastion.control.compute.base.factory import (
    ComputeFactory,
)
from bastion.control.compute.pyasyncentrypoint.pyasyncentrypoint import (
    PyAsyncEntrypointCompute,
    PyAsyncEntrypointModel,
    run_in_async,
)
from bastion.control.compute.pyentrypoint import (
    PyEntrypointCompute,
    PyEntrypointModel,
)

__all__ = [
    "IComputeLike",
    "ComputeFactory",
    "PyEntrypointCompute",
    "PyEntrypointModel",
    "PyAsyncEntrypointCompute",
    "PyAsyncEntrypointModel",
    "run_in_async",
]
