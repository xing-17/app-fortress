"""

Local Python async function Compute implementation with multiprocessing.

"""

from bastion.control.compute.pyasyncentrypoint.pyasyncentrypoint import (
    PyAsyncEntrypointCompute,
    PyAsyncEntrypointModel,
    run_in_async,
)

__all__ = [
    "PyAsyncEntrypointModel",
    "PyAsyncEntrypointCompute",
    "run_in_async",
]
