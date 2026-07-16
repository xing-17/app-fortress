from __future__ import annotations

import json

import duckdb

from app.bridges.migrate.request import BridgesMigrateRequest
from app.bridges.migrate.state import BridgesMigrationState
from app.bridges.resources._warehouse.warehouse import BridgesWarehouse, ModuleBridgesWarehouse
from app.bridges.resources.connections.base.connection import BaseConnection
from app.bridges.resources.destinations.base.destination import BaseDestination
from app.bridges.resources.sources.base import BaseSource
from app.common.plugin import LogPlugin, StopwatchPlugin, TimePlugin
from app.common.setting.bridges import BridgesMigrateSetting


class BridgesMigrationNode(
    LogPlugin,
    TimePlugin,
    StopwatchPlugin,
):
    """
    最小执行单元：执行单次迁移任务（read → transform → write）。

    使用 DuckDB 作为执行引擎，通过 S3 secret 直连 OSS，
    无需将数据经过 Python 内存——全程在 DuckDB 引擎内完成。

    Attributes:
        id: 迁移任务唯一标识符
        state: BridgesMigrationState 对象，追踪执行状态
        from_glob: 源文件路径通配符
        to_glob: 目标文件路径
        transform_sql: DuckDB SQL 变换语句（<source> 已替换为 read_parquet）
        options: DuckDB COPY TO 选项列表
        extensions: DuckDB 扩展列表（如 httpfs）

    Methods:
        plan(): 生成最终的 DuckDB COPY 语句
        run(): 执行迁移任务，返回 BridgesMigrationState
        cancel(): 取消迁移任务
        export(): 导出节点状态为字典
        describe(): 导出节点状态为 JSON 字符串

    Workflow:
        1. 注入 OSS credentials 为 DuckDB S3 secrets（按 bucket 路由）
        2. 将 transform_sql 中的 <source> 占位符替换为 read_parquet(glob_url)
        3. COPY ({sql}) TO 's3://...' (FORMAT parquet, COMPRESSION snappy)
        4. 返回 BridgesMigrationState（写出行数 / 错误信息）

    Note:
        - 同桶迁移只注入一个 secret（mig_src_secret）
        - 跨桶迁移注入两个 secret，分别以 bucket name 为 SCOPE 路由
        - transform_sql 中的 <source> 必须存在，默认为 SELECT * FROM <source>
        - to_glob 支持含 glob 的模式字符串，node 会自动截断至目录部分

    Example:
        >>> node = BridgesMigrationNode(
        ...     setting=migrate_setting,
        ...     request=migrate_request,
        ... )
        >>> state = node.run()
        >>> print(state.rows)  # 写出行数

    """

    def __init__(
        self,
        setting: BridgesMigrateSetting,
        request: BridgesMigrateRequest,
    ) -> None:
        super().__init__()
        self._setting: BridgesMigrateSetting = setting
        self._request: BridgesMigrateRequest = request
        self._resources: BridgesWarehouse = ModuleBridgesWarehouse
        self.state: BridgesMigrationState = BridgesMigrationState(request=request)

        # Base attributes
        self.id: str = request.id
        self._source: BaseSource = self._resolve_source()

        # From and To Destinations
        self._from_dest: BaseDestination = self._resolve_from_destination()
        self._from_dest_conn: BaseConnection = self._from_dest.connection
        self._from_dest_secret: str = None
        self._to_dest: BaseDestination = self._resolve_to_destination()
        self._to_dest_conn: BaseConnection = self._to_dest.connection
        self._to_dest_secret: str = None

        # Migrate attributes
        self.from_glob: str = request.from_glob
        self.to_glob: str = self._resolve_to_glob()
        self.transform_sql: str = self._resolve_transform_sql()
        self.options: list[str] = self._resolve_options()

        # DuckDB client attributes
        self.extensions: list[str] = self._setting.extensions
        self._client: duckdb.DuckDBPyConnection = duckdb.connect(database=":memory:")
        self._set_log_prefix(f"BridgesMigrationNode({self.id})")
        self._setup()

    # ─────────────────────────INTERNAL───────────────────────────────────────────────────

    def _resolve_source(self) -> BaseSource:
        source_name: str = self._request.source_name
        source: BaseSource = self._resources.get_source(source_name)
        return source

    def _resolve_from_destination(self) -> BaseDestination:
        from_dest_name: str = self._request.from_destination
        from_dest: BaseDestination = self._resources.get_destination(from_dest_name)
        if from_dest is None:
            raise ValueError(f"Destination '{from_dest_name}' not found.")
        return from_dest

    def _resolve_to_destination(self) -> BaseDestination:
        to_dest_name: str = self._request.to_destination
        to_dest: BaseDestination = self._resources.get_destination(to_dest_name)
        if to_dest is None:
            raise ValueError(f"Destination '{to_dest_name}' not found.")
        return to_dest

    def _setup_client(self) -> None:
        for ext in self.extensions:
            self._client.execute(f"INSTALL {ext};")
            self._client.execute(f"LOAD {ext};")
        self._client.execute(f"SET memory_limit='{self._setting.memory_limit}';")
        self._client.execute(f"SET temp_directory='{self._setting.temp_directory}';")
        self._client.execute(f"PRAGMA threads={self._setting.max_workers};")
        self.debug("_setup_client(): client setup OK")
        self.debug(f"_setup_client(): memory_limit={self._setting.memory_limit}")
        self.debug(f"_setup_client(): temp_directory={self._setting.temp_directory}")
        self.debug(f"_setup_client(): threads={self._setting.max_workers}")

    def _setup_from_secret(self) -> None:
        secret_name, client = self._from_dest_conn.ingest_to_duckdb(
            self._client,
        )
        self._from_dest_secret: str = secret_name
        self._client: duckdb.DuckDBPyConnection = client
        self._validate_secret(secret_name)
        self.debug(f"_setup_from_secret(): SRC secret '{secret_name}' injected OK.")

    def _setup_to_secret(self) -> None:
        secret_name, client = self._to_dest_conn.ingest_to_duckdb(
            conn=self._client,
        )
        self._to_dest_secret: str = secret_name
        self._client: duckdb.DuckDBPyConnection = client
        self._validate_secret(secret_name)
        self.debug(f"_setup_to_secret(): TGT secret '{secret_name}' injected OK.")

    def _validate_secret(
        self,
        secret_name: str,
    ) -> None:
        query = f"""
            SELECT EXISTS (
                SELECT 1 
                FROM duckdb_secrets() 
                WHERE name = '{secret_name}'
            );
        """
        result = self._client.execute(query).fetchone()
        is_exists = result[0] if result else False
        if not is_exists:
            raise ValueError(f"Secret '{secret_name}' not found in DuckDB.")

    def _resolve_transform_sql(self) -> str:
        if self._request.transform_sql:
            if "<source>" not in self._request.transform_sql:
                raise ValueError("transform_sql must contain the <source> placeholder.")
            else:
                transform_sql = self._request.transform_sql
        else:
            transform_sql = "SELECT * FROM <source>"

        transform_sql = transform_sql.replace(
            "<source>",
            f"read_parquet('{self._request.from_glob}', hive_partitioning = true)",
        )
        return transform_sql

    def _resolve_to_glob(self) -> str:
        uri: str = self._to_dest.get_duckdb_base_uri()
        source_name: str = self._request.source_name
        return f"{uri}/source/{source_name}"

    def _resolve_options(self) -> str:
        if self._request.options:
            return ", ".join(self._request.options)
        else:
            return "FORMAT parquet, COMPRESSION snappy"

    def _setup(self) -> None:
        self._setup_client()
        self._setup_from_secret()
        self._setup_to_secret()
        self.info("setup(): OK")

    # ─────────────────────────EXTERNAL───────────────────────────────────────────────────

    def plan(self) -> str:
        template = f"COPY ({self.transform_sql}) "
        template += f"TO '{self.to_glob}' "
        template += f"({self.options});"
        return template

    def run(self) -> BridgesMigrationState:
        self.tick("run")
        self.state.start()
        try:
            script = self.plan()
            result = self._client.execute(script).fetchone()
            rows = result[0] if result else 0
            duration = self.tock("run")
            self.state.finish(rows)
            self.debug(f"run(): {rows} rows to {self.to_glob} OK.")
            self.debug(f"run(): duration {duration:.2f}s.")
        except Exception as e:
            duration = self.tock("run")
            self.error(f"run(): failed after {duration:.2f}s — {e}")
            self.state.fail(str(e))
        finally:
            self._client.close()
        return self.state

    def cancel(self) -> None:
        self.state.cancel()
        self._client.close()
        self.info(f"cancel(): {self.id} cancelled.")

    def export(self) -> dict[str, str | list[str]]:
        return {
            "id": self.id,
            "request": self._request.export(),
            "state": self.state.export(),
            "from_glob": self.from_glob,
            "to_glob": self.to_glob,
            "transform_sql": self.transform_sql,
            "options": self.options,
        }

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
