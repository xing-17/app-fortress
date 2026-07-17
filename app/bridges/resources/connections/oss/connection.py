from __future__ import annotations

import oss2

from app.bridges.resources.connections.base.connection import BaseConnection
from app.bridges.resources.connections.base.factory import ConnectionFactory
from app.bridges.resources.secret.duckdb import SecretDuckdb
from app.common.setting.connections import OssConnectionSetting


@ConnectionFactory.register("oss")
class OSSConnection(BaseConnection):
    """
    阿里云 OSS 连接管理。

    封装 oss2.Bucket 实例的创建。由 ConnectionFactory 注册，
    实例由 BridgesCluster 持有并注入各 Destination。

    Attributes:
        bucket_name: OSS Bucket 名称
        endpoint:    OSS Endpoint 地址

    Example:
        >>> conn = OSSConnection(setting=oss_setting)
        >>> bucket = conn.get_connection()  # → oss2.Bucket
        >>> conn.ping()  # True

    """

    def __init__(
        self,
        setting: OssConnectionSetting,
    ) -> None:
        super().__init__(setting=setting)
        self.region: str = setting.region
        self.bucket_name: str = setting.bucket
        self.endpoint: str = setting.endpoint
        self._set_log_prefix(f"OSSConnection({self.name})")

    def _create_connection(self) -> oss2.Bucket:
        auth = oss2.Auth(
            access_key_id=self.setting.access_key_id,
            access_key_secret=self.setting.access_key_secret,
        )
        return oss2.Bucket(
            auth=auth,
            endpoint=self.setting.endpoint,
            bucket_name=self.setting.bucket,
            connect_timeout=120,
        )

    def ping(self) -> bool:
        try:
            self.tick("ping")

            self.get_connection().get_bucket_info()
            self.info("ping: OK.")

            seconds = self.tock("ping")
            self.debug(f"ping: duration {seconds:.3f}s.")
            return True
        except Exception as e:
            self.warning(f"ping: fail {e}")
            return False

    def get_duckdb_secret(self) -> SecretDuckdb:
        name = f"_oss_conn_secret_{self.name}"
        secret = SecretDuckdb.from_params(
            type="s3",
            name=name,
            params={
                "KEY_ID": self.setting.access_key_id,
                "SECRET": self.setting.access_key_secret,
                "REGION": self.setting.region,
                "ENDPOINT": self.setting.endpoint,
                "URL_STYLE": self.setting.url_style,
                "USE_SSL": str(self.setting.use_ssl).lower(),
            },
            scope=f"s3://{self.bucket_name}",
        )
        return secret

    def export(self) -> dict:
        result = super().export()
        result["bucket"] = self.bucket_name
        result["endpoint"] = self.endpoint
        return result
