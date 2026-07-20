from __future__ import annotations

import json
import threading

import duckdb

from app.bridges.migrate.node.context import MigrateNodeContext
from app.bridges.migrate.node.state import MigrateNodeState
from app.bridges.resources.connections.base.connection import BaseConnection
from app.bridges.resources.destinations.base.destination import BaseDestination
from app.bridges.resources.secret.duckdb import SecretDuckdb
from app.common.core.setting import GlobalSetting
from app.common.plugin import LogPlugin, StopwatchPlugin, TimePlugin
from app.common.setting.bridges import BridgesMigrateSetting


class MigrateNode(
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
        context: MigrateNodeContext 对象，包含迁移任务配置
        state: MigrateNodeState 对象，追踪执行状态
        identifier: 任务标识符(source_name::id)
        request_id: 所属请求 ID
        transform_sql: DuckDB SQL 变换语句（<source> 已替换为 read_parquet）
        options: DuckDB COPY TO 选项列表
        extensions: DuckDB 扩展列表（如 httpfs）
        script: 最终生成的 DuckDB COPY 语句

    Methods:
        plan(): 生成最终的 DuckDB COPY 语句
        run(): 执行迁移任务，返回 MigrateNodeState
        cancel(): 取消迁移任务
        export(): 导出节点状态为字典
        describe(): 导出节点状态为 JSON 字符串

    Workflow:
        1. 注入 OSS credentials 为 DuckDB S3 secrets（按 bucket 路由）
        2. 将 transform_sql 中的 <source> 占位符替换为 read_parquet(glob_url)
        3. COPY ({sql}) TO 's3://...' (FORMAT parquet, COMPRESSION snappy)
        4. 返回 MigrateNodeState（写出行数 / 错误信息）

    Note:
        - 同桶迁移只注入一个 secret（mig_src_secret）
        - 跨桶迁移注入两个 secret，分别以 bucket name 为 SCOPE 路由
        - transform_sql 中的 <source> 必须存在，默认为 SELECT * FROM <source>
        - to_glob 支持含 glob 的模式字符串，node 会自动截断至目录部分

    Example:
        >>> context = MigrateNodeContext(
        ...     request_id="mig_abc123",
        ...     source_name="tushare_stock_capflow",
        ...     from_destination=oss_finconnect_dest,
        ...     from_glob="s3://bucket/path/**/*.parquet",
        ...     to_destination=oss_fortress_dest,
        ...     to_glob="s3://bucket/target/**/*.parquet",
        ... )
        >>> node = MigrateNode(context=context)
        >>> state = node.run()
        >>> print(state.rows)  # 写出行数

    """

    def __init__(
        self,
        context: MigrateNodeContext,
    ) -> None:
        super().__init__()
        self._cancel_event = threading.Event()
        self.context: MigrateNodeContext = context
        self.id: str = context.id
        self.identifier: str = context.identifier
        self.request_id: str = context.request_id
        self._from_dest: BaseDestination = context.from_destination
        self._from_dest_conn: BaseConnection = self._from_dest.connection
        self._from_dest_secret: SecretDuckdb = None
        self._from_dest_secret_name: str = None
        self._from_glob: str = context.from_glob
        self._to_dest: BaseDestination = context.to_destination
        self._to_dest_conn: BaseConnection = self._to_dest.connection
        self._to_dest_secret: SecretDuckdb = None
        self._to_dest_secret_name: str = None
        self._to_glob: str = context.to_glob
        self.transform_sql: str = self._resolve_transform_sql()
        self.options: list[str] = self._resolve_options()
        self.extensions: list[str] = self._resolve_extensions()
        self.script: str = self._resolve_script()
        self._setting: BridgesMigrateSetting = GlobalSetting.bridges.migrate
        self._setting_memory_limit: str = self._setting.memory_limit
        self._setting_temp_directory: str = self._setting.temp_directory
        self._setting_max_workers: int = self._setting.max_workers
        self.state: MigrateNodeState = MigrateNodeState()
        self._client: duckdb.DuckDBPyConnection = None
        self._set_log_prefix(f"MigrateNode({self.identifier})")

    # ─────────────────────────INTERNAL───────────────────────────────────────────────────

    def _resolve_transform_sql(self) -> str:
        if self.context.transform_sql:
            if "<source>" not in self.context.transform_sql:
                raise ValueError("transform_sql must contain '<source>'.")
            else:
                transform_sql = self.context.transform_sql
        else:
            transform_sql = "SELECT * FROM <source>"

        transform_sql = transform_sql.replace(
            "<source>",
            f"read_parquet('{self.context.from_glob}', hive_partitioning = true)",
        )
        return transform_sql

    def _resolve_options(self) -> list[str]:
        if not self.context.options:
            return [
                "FORMAT parquet",
                "COMPRESSION snappy",
            ]
        else:
            return self.context.options

    def _resolve_extensions(self) -> list[str]:
        if not self.context.extensions:
            return ["httpfs"]
        else:
            return self.context.extensions

    def _setup_client(self) -> None:
        self._client = duckdb.connect(
            database=":memory:",
        )
        for ext in self.extensions:
            self._client.execute(f"INSTALL {ext};")
            self._client.execute(f"LOAD {ext};")

        # setup memory limit
        self._client.execute(f"SET memory_limit='{self._setting_memory_limit}';")
        self.debug(f"_setup_client: memory_limit={self._setting_memory_limit}")

        # setup temp directory
        self._client.execute(f"SET temp_directory='{self._setting_temp_directory}';")
        self.debug(f"_setup_client: temp_directory={self._setting_temp_directory}")

        # setup max workers
        self._client.execute(f"PRAGMA threads={self._setting_max_workers};")
        self.debug(f"_setup_client: threads={self._setting_max_workers}")

    def _setup_from_secret(self) -> None:
        secret: SecretDuckdb = self._from_dest_conn.get_duckdb_secret()
        secret.create(self._client)
        secret.check(self._client)
        secret_name: str = secret.name
        self._from_dest_secret_name: str = secret_name
        self._from_dest_secret: SecretDuckdb = secret
        self.debug(f"_setup_from_secret: '{secret_name}' OK.")

    def _setup_to_secret(self) -> None:
        secret: SecretDuckdb = self._to_dest_conn.get_duckdb_secret()
        secret.create(self._client)
        secret.check(self._client)
        secret_name: str = secret.name
        self._to_dest_secret_name: str = secret_name
        self._to_dest_secret: SecretDuckdb = secret
        self.debug(f"_setup_to_secret: '{secret_name}' OK.")

    def _resolve_script(self) -> str:
        _options = ", ".join(self.options)
        script = f"COPY ({self.transform_sql}) "
        script += f"TO '{self._to_glob}' "
        script += f"({_options});"
        return script

    # ─────────────────────────EXTERNAL───────────────────────────────────────────────────

    def setup(self) -> None:
        self._setup_client()
        self._setup_from_secret()
        self._setup_to_secret()
        self.info("setup: OK")

    def run(self) -> MigrateNodeState:
        if self._cancel_event.is_set():
            self.state.cancel()
            self.info("run: cancelled OK.")
            return self.state

        self.setup()
        self.tick("run")
        self.state.start()
        try:
            result = self._client.execute(self.script).fetchone()
            rows = result[0] if result else 0
            duration = self.tock("run")
            self.state.finish(rows=rows)
            self.info("run: OK.")
            self.info(f"run: rows={rows}.")
            self.info(f"run: duration {duration:.2f}s.")
        except duckdb.InterruptException:
            duration = self.tock("run")
            self.state.cancel()
            self.info(f"run: cancelled. duration={duration:.2f}s.")
        except Exception as e:
            duration = self.tock("run")
            self.error(f"run: fail {e}")
            self.info(f"run: duration {duration:.2f}s.")
            self.state.fail(str(e))
        finally:
            self._client.close()
        return self.state

    def cancel(self) -> None:
        self._cancel_event.set()
        try:
            self._client.interrupt()
        except Exception:
            pass  # 连接可能尚未启动或已关闭
        self.info("cancel: OK.")

    def export(self) -> dict[str, str | list[str]]:
        return {
            "context": self.context.export(),
            "state": self.state.export(),
            "script": self.script,
            "extensions": self.extensions,
            "options": self.options,
        }

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
