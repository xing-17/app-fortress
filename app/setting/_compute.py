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
    阿里云函数计算(FC 3.0)计算资源，通过 InvokeFunction 调用已部署的函数。

    Attributes:
    ----------
        name (str): 计算资源名称
        function_name (str): FC 函数名称
        region (str): FC 函数所在区域
        qualifier (str): 函数版本或别名 (默认LATEST)
        in_vpc (bool): 是否在VPC内访问FC (默认False)
        timeout_seconds (float): 调用的读取超时秒数 (默认600)
        max_workers (int): submit 的本地最大并发调用数 (默认8)
        identity (AliyunIdentitySetting | str | None): 调用函数所使用的阿里云 Identity
        platform (Literal[Platform.ALIYUN]): 平台类型，固定为ALIYUN
        runtime (Literal[ComputeRuntime.FC]): 运行时类型，固定为FC
        description (str): 描述信息
        max_run_records (int | None): 最大保留的运行记录数 (可选)
        store (UnionStoreSetting | str | None): 记录运行结果的Store配置或名称
        tags (dict[str, str]): 标签

    """

    # Inherited from AbstractComputeSetting
    # - description: str
    # - store: UnionStoreSetting | str | None
    # - log: LogSetting | str | None
    # - tags: dict[str, str]
    # - max_run_records: int
    function_name: str = Field(
        ...,
        description="[Required] FC 函数名称",
    )
    region: str = Field(
        ...,
        description="[Required] FC 函数所在区域",
    )
    qualifier: str = Field(
        default="LATEST",
        description="[Optional] 函数版本或别名",
    )
    in_vpc: bool = Field(
        default=False,
        description="[Optional] 是否在VPC内访问FC",
    )
    timeout_seconds: float = Field(
        default=600,
        description="[Optional] 调用的读取超时秒数",
        gt=0,
    )
    max_workers: int = Field(
        default=8,
        description="[Optional] submit 的本地最大并发调用数",
        ge=1,
    )
    identity: AliyunIdentitySetting | str | None = Field(
        default=None,
        description="[Optional] 阿里云身份用于调用函数",
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
