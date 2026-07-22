from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field

from app.common.setting.base import BaseSetting

# ---------------------------------------------------------------
# Fortress Portal Configuration
# ---------------------------------------------------------------


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


InstanceSetting = Annotated[
    Union[EcsInstanceSetting,],
    Field(discriminator="type"),
]


# -------------- Portal Setting --------------------------
class PortalSetting(BaseSetting):
    host: str = "0.0.0.0"
    port: int = 7964
    version: str = "1.0.0"
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
