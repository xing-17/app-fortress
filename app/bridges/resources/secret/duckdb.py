from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict

import duckdb


@dataclass
class SecretDuckdbConfig:
    """
    DuckDB Secret 配置数据类

    Attributes:
        type: Secret 类型（如 's3', 'azure', 'gcs'）
        name: Secret 唯一标识名称
        params: Secret 参数字典（参数名会自动转换为大写）
        scope: 可选的 Secret 作用域（如 's3://bucket-name'）
    """

    type: str
    name: str
    params: Dict[str, Any]
    scope: str | None = None


class SecretDuckdb:
    """
    DuckDB Secret 封装

    例如传入 {"key_id": "xxx"} 会生成 SQL: KEY_ID 'xxx'

    Attributes:
        config: Secret 配置对象
        name: Secret 名称（快捷访问）

    Methods:
        from_params(type, name, params, scope): 工厂方法，从参数直接创建实例
        to_sql(): 导出为 CREATE SECRET SQL 语句
        create(conn): 在 DuckDB 连接中创建 secret
        drop(conn): 从 DuckDB 连接中删除 secret
        check(conn): 检查 secret 是否存在
        list_all(conn): 列出所有 secret
        export(): 导出为字典
        describe(): 导出为 JSON 字符串

    Example:
        >>> secret = SecretDuckdb.from_params(
        ...     type="s3",
        ...     name="oss_prod",
        ...     params={"key_id": "xxx", "secret": "xxx"},
        ...     scope="s3://my-bucket"
        ... )
        >>>
        ... print(secret.to_sql())
    """

    @classmethod
    def from_params(
        cls,
        type: str,
        name: str,
        params: Dict[str, Any],
        scope: str | None = None,
    ) -> "SecretDuckdb":
        """
        工厂方法：从参数直接创建 SecretDuckdb 实例

        Args:
            type: Secret 类型（如 's3', 'azure', 'gcs'）
            name: Secret 唯一标识名称
            params: Secret 参数字典（参数名会自动转换为大写）
            scope: 可选的 Secret 作用域（如 's3://bucket-name'）

        Returns:
            SecretDuckdb: 新创建的实例
        """
        config = SecretDuckdbConfig(
            type=type,
            name=name,
            params=params,
            scope=scope,
        )
        return cls(config)

    def __init__(
        self,
        config: SecretDuckdbConfig,
    ):
        self.config = config
        self.name = config.name

    def to_sql(self) -> str:
        context_lines = []
        context_lines.append(f"TYPE {self.config.type}")
        context_lines.append("PROVIDER config")
        for key, value in self.config.params.items():
            key_upper = key.upper()
            context_lines.append(f"{key_upper} '{value}'")
        if self.config.scope:
            context_lines.append(f"SCOPE '{self.config.scope}'")
        context = ",\n\t".join(context_lines)
        statement = f"""CREATE OR REPLACE SECRET {self.name} (\n {context} \n);"""
        return statement

    def create(
        self,
        conn: duckdb.DuckDBPyConnection,
    ) -> None:
        statement = self.to_sql()
        conn.execute(statement)

    def drop(
        self,
        conn: duckdb.DuckDBPyConnection,
    ) -> None:
        statement = f"DROP SECRET IF EXISTS {self.name};"
        conn.execute(statement)

    def check(
        self,
        conn: duckdb.DuckDBPyConnection,
    ) -> bool:
        statement = "SELECT name FROM duckdb_secrets() WHERE name = ?;"
        result = conn.execute(statement, [self.name]).fetchall()
        return len(result) > 0

    @staticmethod
    def list_all(
        conn: duckdb.DuckDBPyConnection,
    ) -> list[str]:
        """
        列出 DuckDB 中所有 secret 的名称

        Args:
            conn: DuckDB 连接对象

        Returns:
            list[str]: 所有 secret 的名称列表

        """
        statement = "SELECT name FROM duckdb_secrets();"
        result = conn.execute(statement).fetchall()
        return [row[0] for row in result]

    def export(self) -> dict[str, Any]:
        return {
            "type": self.config.type,
            "name": self.config.name,
            "scope": self.config.scope,
        }

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
