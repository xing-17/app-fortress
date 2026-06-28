from __future__ import annotations

import json
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, TypeAdapter


class BaseConnectionSetting(BaseModel):
    """
    连接配置基类。

    Attributes:
        type: 连接类型标识，作为区分不同连接配置的字段
        name: 连接标识名，用于日志区分

    """

    type: str = Field(
        ...,
        description="连接类型标识，作为区分不同连接配置的字段",
    )
    name: str = Field(
        ...,
        description="连接标识名，用于日志区分",
    )


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
    url_style: str = "vhost"

    def export(self) -> dict:
        return self.model_dump()

    def describe(self) -> str:
        data = {
            "type": self.type,
            "access_key_id": self.access_key_id[:4] + "***",
            "access_key_secret": self.access_key_secret[:4] + "***",
            "endpoint": self.endpoint,
            "region": self.region,
            "url_style": self.url_style,
            "bucket": self.bucket,
        }
        return json.dumps(
            data,
            indent=4,
            ensure_ascii=False,
        )


ConnectionSetting = Annotated[
    Union[OssConnectionSetting,],
    Field(discriminator="type"),
]

_CONN_ADAPTER = TypeAdapter(ConnectionSetting)


class ConnectionsSetting(BaseModel):
    """
    连接配置集合。

    Attributes:
        connections: 连接配置字典，键为环境名，值为具体的连接

    Examples:
        >>> conns = ConnectionsSetting(raw)
        >>> conn = conns.get("prod")     # → OssConnectionSetting
    """

    connections: dict[str, ConnectionSetting]

    def get(
        self,
        env: str,
    ) -> ConnectionSetting:
        if env not in self.connections:
            raise KeyError(f"Connection not found: {env!r}")
        return self.connections[env]

    def export(self) -> dict:
        result = {}
        for name, conn in self.connections.items():
            result[name] = conn.export()
        return result

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
