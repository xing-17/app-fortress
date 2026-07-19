from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field

from app.common.setting.base import BaseSetting


class BaseConnectionSetting(BaseSetting):
    type: str = Field(..., description="连接类型标识，作为区分不同连接配置的字段")
    name: str = Field(..., description="连接标识名，用于日志区分")


class OssConnectionSetting(BaseConnectionSetting):
    """
    阿里云 OSS 连接配置。

    支持同时为 Python 客户端（oss2）和 dbt-duckdb httpfs 提供配置。

    Attributes:
        type:              连接类型标识，固定为 "oss"
        cache:             本地缓存目录
        access_key_id:     OSS Access Key ID
        access_key_secret: OSS Access Key Secret
        endpoint:          OSS Endpoint（外网/内网）
        region:            OSS Region
        url_style:         URL 风格，vhost 或 path
        bucket:            目标 Bucket 名称
        use_ssl:           是否使用 HTTPS 协议

    Examples:
        >>> conn = OssConnectionSetting(
        ...     type="oss",
        ...     access_key_id="xxx",
        ...     access_key_secret="yyy",
        ...     endpoint="oss-cn-shanghai.aliyuncs.com",
        ...     region="cn-shanghai",
        ...     bucket="my-bucket",
        ... )
        >>> conn.describe()
        >>> ...

    """

    type: Literal["oss"] = "oss"
    name: str | None = None
    access_key_id: str
    access_key_secret: str
    endpoint: str
    region: str
    bucket: str
    url_style: str | None = "vhost"
    use_ssl: bool | None = True

    def export(self) -> dict:
        result = super().export()
        result["access_key_id"] = self.access_key_id[:4] + "***"
        result["access_key_secret"] = self.access_key_secret[:4] + "***"
        return result


ConnectionSetting = Annotated[
    Union[OssConnectionSetting,],
    Field(discriminator="type"),
]


class ConnectionsSetting(BaseSetting):
    """
    连接配置集合。

    Attributes:
        connections: 连接配置字典，键为连接名，值为具体的连接

    Methods:
        get: 根据连接名获取对应的连接配置

    Examples:
        >>> conns = ConnectionsSetting(raw)
        >>> conn = conns.get("prod")     # → OssConnectionSetting
        >>> print(conn.describe())

    """

    connections: dict[str, ConnectionSetting]

    def get(
        self,
        name: str,
    ) -> ConnectionSetting:
        if name not in self.connections:
            raise KeyError(f"Connection not found: {name!r}")
        return self.connections[name]

    def export(self) -> dict:
        result = {}
        for name, conn in self.connections.items():
            result[name] = conn.export()
        return result
