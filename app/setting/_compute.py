from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field

from app.internal.abstract.setting import IAbstractTaggedSetting
from app.internal.constant.computeruntime import ComputeRuntime
from app.internal.constant.platform import Platform
from app.internal.util.frn import IFrn
from app.setting._identity import AliyunIdentitySetting, LocalIdentitySetting
from app.setting._log import LogSetting
from app.setting._store import UnionStoreSetting

COMPUTE_NAME_PATTERN: str = r"^[A-Za-z0-9_]+$"


class AbstractComputeSetting(IAbstractTaggedSetting):
    """
    Abstract compute setting

    Attributes:
    ----------
        name (str): Compute name
        runtime (ComputeRuntime): Compute runtime type
        platform (Platform): Compute operating platform
        description (str): Compute description information
        store (UnionStoreSetting | str | None): Store configuration or name or default store
        log (LogSetting | str | None): Log configuration or name or default log stream
        max_run_records (int): Maximum number of run records to keep
        tags (dict[str, str]): Compute tags

    """

    name: str = Field(
        ...,
        description="[Required] Compute name, only letters, digits and underscores",
        pattern=COMPUTE_NAME_PATTERN,
    )
    runtime: ComputeRuntime = Field(
        ...,
        description="[discriminator] Compute runtime",
    )
    platform: Platform = Field(
        ...,
        description="[Required] Compute platform",
    )
    description: str = Field(
        default="",
        description="[Optional] description of the compute",
    )
    store: UnionStoreSetting | str | None = Field(
        default=None,
        description="[Optional] Store configuration or name for the run records of the compute",
    )
    log: LogSetting | str | None = Field(
        default=None,
        description="[Optional] Log configuration or name of the compute",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="[Optional] Compute tags",
    )
    max_run_records: int = Field(
        default=200,
        description="[Optional] Maximum number of run records to keep",
        ge=1,
    )

    @property
    def frn(self) -> str:
        return IFrn.resolve(
            [
                "setting",
                "compute",
                f"platform={self.platform}",
                f"runtime={self.runtime}",
                f"name={self.name}",
            ]
        )

    def _non_override_tags(self) -> dict[str, str]:
        return {
            "platform": self.platform,
            "runtime": self.runtime,
            "name": self.name,
        }


class PyEntrypointComputeSetting(AbstractComputeSetting):
    """
    Local Python entrypoint compute, runs `module:function` in the current or a child process.

    Attributes:
    ----------
        name (str): Compute name
        entrypoint (str): Importable function in `package.module:function` form
        platform (Literal[Platform.LOCAL]): Compute platform, fixed as LOCAL
        runtime (Literal[ComputeRuntime.PYENTRYPOINT]): Compute runtime, fixed as PYENTRYPOINT
        identity (LocalIdentitySetting | str | None): Local identity configuration or name
        description (str): Compute description information
        max_run_records (int): Maximum number of run records to keep
        store (UnionStoreSetting | str | None): Store configuration or name for the run records
        log (LogSetting | str | None): Log configuration or name
        tags (dict[str, str]): Compute tags

    """

    # Inherited from AbstractComputeSetting
    # - description: str
    # - store: UnionStoreSetting | str | None
    # - log: LogSetting | str | None
    # - tags: dict[str, str]
    # - max_run_records: int
    entrypoint: str = Field(
        ...,
        description="[Required] Importable function in `package.module:function` form",
    )
    identity: LocalIdentitySetting | str | None = Field(
        default=None,
        description="[Optional] Local identity configuration or name",
    )
    platform: Literal[Platform.LOCAL] = Platform.LOCAL
    runtime: Literal[ComputeRuntime.PYENTRYPOINT] = ComputeRuntime.PYENTRYPOINT


class FCComputeSetting(AbstractComputeSetting):
    """
    Alibaba Cloud Function Compute (FC 3.0) compute, calls a deployed function through InvokeFunction.

    Attributes:
    ----------
        name (str): Compute name
        function_name (str): FC function name
        region (str): Region of the FC function
        qualifier (str): Function version or alias, defaults to LATEST
        in_vpc (bool): Whether to reach FC from inside the VPC, defaults to False
        timeout_seconds (float): Read timeout of an invocation in seconds, defaults to 600
        max_workers (int): Maximum number of concurrent local invocations of submit, defaults to 8
        identity (AliyunIdentitySetting | str | None): Aliyun identity configuration or name
        platform (Literal[Platform.ALIYUN]): Compute platform, fixed as ALIYUN
        runtime (Literal[ComputeRuntime.FC]): Compute runtime, fixed as FC
        description (str): Compute description information
        max_run_records (int): Maximum number of run records to keep
        store (UnionStoreSetting | str | None): Store configuration or name for the run records
        log (LogSetting | str | None): Log configuration or name
        tags (dict[str, str]): Compute tags

    """

    # Inherited from AbstractComputeSetting
    # - description: str
    # - store: UnionStoreSetting | str | None
    # - log: LogSetting | str | None
    # - tags: dict[str, str]
    # - max_run_records: int
    function_name: str = Field(
        ...,
        description="[Required] FC function name",
    )
    region: str = Field(
        ...,
        description="[Required] Region of the FC function",
    )
    qualifier: str = Field(
        default="LATEST",
        description="[Optional] Function version or alias",
    )
    in_vpc: bool = Field(
        default=False,
        description="[Optional] Whether to reach FC from inside the VPC",
    )
    timeout_seconds: float = Field(
        default=600,
        description="[Optional] Read timeout of an invocation in seconds",
        gt=0,
    )
    max_workers: int = Field(
        default=8,
        description="[Optional] Maximum number of concurrent local invocations of submit",
        ge=1,
    )
    identity: AliyunIdentitySetting | str | None = Field(
        default=None,
        description="[Optional] Aliyun identity configuration or name used to invoke the function",
    )
    platform: Literal[Platform.ALIYUN] = Platform.ALIYUN
    runtime: Literal[ComputeRuntime.FC] = ComputeRuntime.FC


UnionComputeSetting = Annotated[
    Union[
        PyEntrypointComputeSetting,
        FCComputeSetting,
    ],
    Field(discriminator="runtime"),
]
