from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field

from app.internal.abstract.setting import IAbstractTaggedSetting
from app.internal.constant.computeruntime import ComputeRuntime
from app.internal.constant.platform import Platform
from app.internal.util.frn import IFrn
from app.setting._identity import AliyunIdentitySetting


class AbstractComputeSetting(IAbstractTaggedSetting):
    """
    Abstract compute setting

    Attributes:
    ----------
        name (str): Compute name
        runtime (ComputeRuntime): Compute runtime type
        platform (Platform): Compute operating platform
        description (str): Compute description information
        tags (dict[str, str]): Compute tags

    """

    name: str = Field(
        ...,
        description="[Required] Compute name",
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
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="[Optional] Compute tags",
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
        description (str): Compute description information
        tags (dict[str, str]): Compute tags

    """

    # Inherited from AbstractComputeSetting
    # - description: str
    # - tags: dict[str, str]
    entrypoint: str = Field(
        ...,
        description="[Required] Importable function in `package.module:function` form",
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
        timeout_seconds (float): 同步调用的读取超时秒数 (默认600)
        identity (str | None): 调用函数所使用的阿里云 Identity
        platform (Literal[Platform.ALIYUN]): 平台类型，固定为ALIYUN
        runtime (Literal[ComputeRuntime.FC]): 运行时类型，固定为FC
        description (str): 描述信息
        tags (dict[str, str]): 标签

    """

    # Inherited from AbstractComputeSetting
    # - description: str
    # - tags: dict[str, str]
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
        description="[Optional] 同步调用的读取超时秒数",
        gt=0,
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
