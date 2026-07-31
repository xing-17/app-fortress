from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field

from app.common.setting.base import BaseSetting

# ---------------------------------------------------------------
# Fortress Portal Configuration
# ---------------------------------------------------------------


# ---------- Service Configuration ----------
class ServiceSetting(BaseSetting):
    """
    Fortress 服务配置。

    定义远程主机上服务的部署路径和 Makefile 控制命令。
    可在 portal.yml 的 instances.<name>.service 段中覆盖默认值。

    Attributes:
        path: 远程部署目录
        start_cmd: 启动命令（make start → docker/build + docker/start）
        stop_cmd: 停止命令（make end → docker/end）
        restart_cmd: 重启命令（make restart → docker/end + docker/start）
        timeout: 远程命令超时秒数

    """

    path: str = "/root/workspace/app-fortress"
    start_cmd: str = "make start"
    stop_cmd: str = "make end"
    restart_cmd: str = "make restart"
    timeout: int = 300


# ---------- Instance Configuration ----------
class BaseInstanceSetting(BaseSetting):
    """
    实例配置。

    Attributes:
        type: str 实例类型标识，作为区分不同实例配置的字段
        name: str 实例标识名，用于日志区分
        settings: dict 实例特定的配置项

    Examples:
        >>> config = BaseInstanceSetting(
        ...     type="aliyun_ecs",
        ...     name="app-fortress",
        ...     ...
        ... )
        >>> print(config.describe())
        >>> ...

    """

    type: str
    name: str
    key: str
    host: str
    port: int
    timeout: int = 6
    service: ServiceSetting = Field(default_factory=ServiceSetting)

    def export(self) -> dict:
        result = super().export()
        result["key"] = "***" + self.key[-4:]
        return result


class EcsInstanceSetting(BaseInstanceSetting):
    """
    阿里云 ECS 实例配置。

    Attributes:
        type: str 实例类型标识，固定为 "ecs"
        name: str 实例标识名，用于日志区分
        region: str 实例所在的地域ID
        port: int 实例SSH服务监听的端口，默认为22
        access_key_id: str 阿里云Access Key ID
        access_key_secret: str 阿里云Access Key Secret

    """

    type: Literal["ecs"] = "ecs"
    region: str
    access_key_id: str
    access_key_secret: str

    def export(self) -> dict:
        result = super().export()
        result["access_key_id"] = "***" + self.access_key_id[-4:]
        result["access_key_secret"] = "***" + self.access_key_secret[-4:]
        return result


class LocalInstanceSetting(BaseInstanceSetting):
    """
    本地实例配置。

    代表运行 app-fortress 的本机，无需云凭证。

    Attributes:
        type: str 实例类型标识，固定为 "local"
        host: str 本机地址，默认为 "localhost"
        port: int 用于 ping 检测的本地端口，默认为 22
        key: str 本地实例无需密钥，默认为空字符串

    """

    type: Literal["local"] = "local"
    host: str = "localhost"
    port: int = 22
    key: str = ""


InstanceSetting = Annotated[
    Union[EcsInstanceSetting, LocalInstanceSetting],
    Field(discriminator="type"),
]


# -------------- Portal Setting --------------------------
class PortalSetting(BaseSetting):
    host: str = "0.0.0.0"
    port: int = 7964
    version: str = "1.0.0"
    key: str = ""
    instances: dict[str, InstanceSetting] = {}

    def get_instance(
        self,
        name: str,
    ) -> InstanceSetting | None:
        return self.instances.get(name)

    def list_instances(self) -> list[InstanceSetting]:
        return list(self.instances.values())

    def export(self) -> dict:
        result = super().export()
        result["instances"] = {}
        for name, instance in self.instances.items():
            result["instances"][name] = instance.export()
        return result
