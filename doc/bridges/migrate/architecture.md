# Bridges Migrate 架构设计

## 一、两层架构

Migrate 采用两层架构设计，相比 Core 的三层架构更加扁平：

```
┌─────────────────────────────────────────────┐
│      Service 层 (_service/)                  │
│                                             │
│  MigrateService        - 核心调度服务        │
│  MigrateRequest        - 请求对象            │
│  MigrateRequestState   - 请求状态            │
│  MigrateRegistry       - 注册表管理          │
└─────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────┐
│      Node 层 (node/)                         │
│                                             │
│  MigrateNode           - 执行节点            │
│  MigrateNodeContext    - 节点上下文          │
│  MigrateNodeState      - 节点状态            │
└─────────────────────────────────────────────┘
```

### 职责划分

- **Service 层**：请求生命周期管理、资源解析、任务调度、状态追踪
- **Node 层**：DuckDB 引擎初始化、S3 secret 管理、COPY 语句生成和执行

### 为什么只有两层？

- **1 Request = 1 Node**：每个迁移请求对应单个 MigrateNode，无需策略派生
- **无需展开**：不像 Core 需要按日期/股票代码拆分，迁移任务是原子的
- **简化调度**：无需中间层协调，Service 直接调度 Node

---

## 二、Service 层

### 2.1 MigrateService

核心调度服务，继承 `BaseBridgesService`。

**核心属性**：
- `_registry: MigrateRegistry` - 请求历史注册表
- `_warehouse: BridgesWarehouse` - 资源仓库（获取 Destination）
- `_queue: Queue[MigrateRequest]` - 请求队列
- `_worker: Thread` - 后台工作线程
- `_live: dict[str, MigrateRequestState]` - 运行中的请求状态

**核心方法**：
```python
# 推导执行节点
derive(request: MigrateRequest) -> MigrateNode

# 生成初始状态
plan(request: MigrateRequest) -> MigrateRequestState

# 执行请求
run(request: MigrateRequest) -> MigrateRequestState

# 提交到队列（异步）
submit(request: MigrateRequest) -> str

# 查询状态
lookup(request_id: str) -> dict

# 取消执行
cancel(request_id: str) -> None
```

**执行流程**：
1. 从 warehouse 获取 source 实例（验证存在性）
2. 获取 from_destination 和 to_destination
3. 构建 from_glob（源文件路径）
4. 构建 to_glob（目标文件路径，自动拼接 source.name）
5. 合并 request 和 system 级别的 options/extensions
6. 创建 `MigrateNodeContext`
7. 实例化 `MigrateNode`

### 2.2 MigrateRequest

请求对象，定义数据迁移任务的输入参数。

```python
class MigrateRequest(BaseContext):
    source_name: str                   # 源数据源名称（用于标识和路径构建）
    from_destination: str              # 源 Destination 名称
    from_glob: str                     # 源文件路径 glob（如 s3://bucket/prefix/**/*.parquet）
    to_destination: str                # 目标 Destination 名称
    transform_sql: str | None          # SQL 转换语句（<source> 作为占位符）
    options: list[str]                 # DuckDB COPY TO 选项
    extensions: list[str]              # DuckDB 扩展列表
```

**示例**：
```python
request = MigrateRequest(
    source_name="tushare_stock_daily",
    from_destination="oss_finconnect",
    from_glob="s3://bucket-src/finconnect/landing/tushare_stock_daily/**/*.parquet",
    to_destination="oss_fortress",
    transform_sql="SELECT * EXCLUDE(unused_col) FROM <source> WHERE date >= '2024-01-01'",
    options=["OVERWRITE_OR_IGNORE true"],
    extensions=["httpfs"],
)
```

### 2.3 MigrateRequestState

请求状态，追踪执行进度和结果。

```python
class MigrateRequestState(BaseBridgesState):
    request: MigrateRequest
    node: MigrateNode | None          # 关联的执行节点
    status: MigrateRequestStatus      # PENDING/RUNNING/DONE/FAILED/CANCELED
    error: str | None                 # 错误信息
```

**状态属性**：
- `succeeded: bool` - 是否执行成功
- `finished: bool` - 是否已结束
- `total_rows: int` - 迁移的总行数（来自 node.state.rows）

### 2.4 MigrateRegistry

注册表，持久化请求历史到本地 JSON 文件。

```python
class MigrateRegistry(BaseRegistry):
    def load() -> None                 # 从文件加载
    def upsert(request_id: str, data: dict) -> None  # 更新或插入
    def get(request_id: str) -> dict | None          # 获取单条记录
    def all() -> list[dict]                          # 获取所有记录
```

**持久化路径**：
```
.cache/bridges/registry/migrate.json
```

---

## 三、Node 层

### 3.1 MigrateNode

最小执行单元，负责生成和执行 DuckDB COPY 语句。

**核心属性**：
```python
context: MigrateNodeContext           # 节点上下文
state: MigrateNodeState               # 节点状态
transform_sql: str                    # 转换后的 SQL（<source> 已替换）
script: str                           # 最终的 COPY 语句
_client: duckdb.DuckDBPyConnection    # DuckDB 连接
_cancel_event: threading.Event        # 取消信号
```

**核心方法**：
```python
setup() -> None                       # 初始化 DuckDB 客户端和 S3 secrets
run() -> MigrateNodeState             # 执行迁移任务
cancel() -> None                      # 取消执行
export() -> dict                      # 导出节点信息
```

**执行流程**：
1. `setup()` - 初始化执行环境
   - `_setup_client()` - 创建 DuckDB 连接，加载扩展，设置参数
   - `_setup_from_secret()` - 创建源 bucket 的 S3 secret
   - `_setup_to_secret()` - 创建目标 bucket 的 S3 secret
2. `run()` - 执行 COPY 语句
   - 检查取消状态
   - 执行 `self.script`（DuckDB COPY 语句）
   - 获取写出行数
   - 更新状态为 DONE/FAILED/CANCELED
3. `_client.close()` - 关闭 DuckDB 连接

**DuckDB 配置**：
```python
# 内存限制
SET memory_limit = '8GB';

# 临时目录
SET temp_directory = '/tmp/duckdb';

# 线程数
PRAGMA threads = 4;
```

### 3.2 MigrateNodeContext

节点上下文，封装单次迁移任务的完整配置。

```python
class MigrateNodeContext(BaseContext):
    request_id: str                    # 所属请求 ID
    source_name: str                   # 源数据源名称
    from_destination: BaseDestination  # 源目标实例
    from_glob: str                     # 源文件路径 glob
    to_destination: BaseDestination    # 目标实例
    to_glob: str                       # 目标文件路径 glob
    transform_sql: str | None          # SQL 转换语句
    options: list[str]                 # COPY 选项
    extensions: list[str]              # DuckDB 扩展
```

**自动生成**：
- `id: str` - 自动生成唯一标识（格式：`mignctx_xxxxxxxxxxxx`）
- `identifier: str` - 任务标识符（格式：`{source_name}::{id}`）

### 3.3 MigrateNodeState

节点状态，记录单次执行的结果。

```python
class MigrateNodeState(BaseBridgesState):
    status: MigrateNodeStatus          # PENDING/RUNNING/DONE/FAILED/CANCELED
    started_at: datetime | None        # 开始时间
    finished_at: datetime | None       # 结束时间
    rows: int                          # 迁移的行数
    error: str | None                  # 错误信息
```

**状态转换方法**：
```python
start() -> None                        # 标记开始
finish(rows: int) -> None              # 标记成功完成
fail(error: str) -> None               # 标记失败
cancel() -> None                       # 标记取消（继承）
```

---

## 四、DuckDB 执行引擎

### 4.1 执行模型

Migrate 的核心优势在于使用 DuckDB 作为执行引擎，实现 **数据不经过 Python 内存** 的高性能迁移。

```
┌───────────────────────────────────────────────┐
│  Python 进程                                   │
│                                               │
│  MigrateNode                                  │
│     ↓                                         │
│  DuckDB Engine ┌──────────────────────────┐  │
│     │          │  COPY (SELECT ...)       │  │
│     │          │  TO 's3://...'           │  │
│     │          └──────────────────────────┘  │
│     ↓                                         │
└─────┼─────────────────────────────────────────┘
      │
      ├───→ S3 Read (httpfs extension)
      │     read_parquet('s3://from/**/*.parquet')
      │
      ├───→ In-Engine Transform
      │     SELECT * EXCLUDE(col) WHERE ...
      │
      └───→ S3 Write (httpfs extension)
            TO 's3://to/**/*.parquet'
```

### 4.2 SQL 转换机制

**占位符替换**：
```python
# 用户输入
transform_sql = "SELECT * EXCLUDE(stock_code) FROM <source>"

# 替换后
transform_sql = """
SELECT * EXCLUDE(stock_code) 
FROM read_parquet('s3://bucket/path/**/*.parquet', hive_partitioning = true)
"""
```

**默认转换**（未提供 transform_sql 时）：
```sql
SELECT * FROM read_parquet('s3://from/**/*.parquet', hive_partitioning = true)
```

### 4.3 COPY 语句生成

**最终脚本格式**：
```sql
COPY (
  {transform_sql}
) TO '{to_glob}' (
  FORMAT parquet, 
  COMPRESSION snappy
);
```

**示例**：
```sql
COPY (
  SELECT 
    trade_date, 
    ts_code, 
    open, 
    high, 
    low, 
    close, 
    volume
  FROM read_parquet('s3://src-bucket/finconnect/landing/tushare_stock_daily/**/*.parquet', hive_partitioning = true)
  WHERE trade_date >= '20240101'
) TO 's3://tgt-bucket/fortress/bridges/source/tushare_stock_daily/**/*.parquet' (
  FORMAT parquet,
  COMPRESSION snappy,
  OVERWRITE_OR_IGNORE true
);
```

### 4.4 S3 Secret 管理

**按 Bucket 路由**：
每个 Destination 的 Connection 提供一个 `get_duckdb_secret()` 方法，返回 DuckDB S3 secret：

```python
# 创建 secret
secret: SecretDuckdb = connection.get_duckdb_secret()
secret.create(duckdb_client)

# DuckDB 内部执行
CREATE SECRET {secret_name} (
  TYPE S3,
  KEY_ID '{access_key_id}',
  SECRET '{secret_access_key}',
  REGION '{region}',
  SCOPE 's3://{bucket_name}'
);
```

**同桶迁移 vs 跨桶迁移**：
- **同桶**：只创建一个 secret（from 和 to 共用）
- **跨桶**：创建两个 secret，分别 SCOPE 到不同 bucket

---

## 五、完整执行流程

```
1. 用户提交请求
   ↓
MigrateService.submit(request)
   - 生成 request_id
   - 加入 Queue
   - 后台 Worker 消费
   ↓
2. MigrateService.run(request)
   ↓
derive(request) → MigrateNode
   - resources.get_source(source_name) → 验证存在
   - resources.get_destination(from_destination) → 源目标
   - resources.get_destination(to_destination) → 目标
   - 构建 from_glob（用户提供）
   - 构建 to_glob（自动拼接：{location}/source/{source_name}）
   - 合并 options 和 extensions
   - 创建 MigrateNodeContext → MigrateNode
   ↓
3. MigrateNode.run()
   ↓
setup()
   - _setup_client() → 创建 DuckDB 连接，加载扩展
   - _setup_from_secret() → 创建源 bucket S3 secret
   - _setup_to_secret() → 创建目标 bucket S3 secret
   ↓
4. 执行 COPY 语句
   ↓
_client.execute(script)
   - DuckDB 读取 s3://from/**/*.parquet
   - 在引擎内执行 transform_sql
   - DuckDB 写入 s3://to/**/*.parquet
   - 返回写出行数
   ↓
5. 更新状态
   - state.finish(rows) → DONE
   - 或 state.fail(error) → FAILED
   - 或 state.cancel() → CANCELED
   ↓
6. 持久化和清理
   - 更新 MigrateRegistry（JSON 文件）
   - 从 _live 字典移除请求
   - 关闭 DuckDB 连接
```

---

## 六、关键机制

### 6.1 并发控制

**单级并发**：
- Migrate 不需要多层并发（1 request = 1 node）
- 并发能力依赖 DuckDB 内部并行：
  ```python
  PRAGMA threads = 4;  # 使用 4 个线程读写
  ```

**Service 队列**：
- Service 层通过 Queue + Worker 串行消费请求
- 避免同时打开过多 DuckDB 连接

### 6.2 取消机制

**DuckDB Interrupt**：
```python
def cancel(self) -> None:
    self._cancel_event.set()
    try:
        self._client.interrupt()  # 中断 DuckDB 查询
    except Exception:
        pass
```

**取消时机检查**：
```python
def run(self) -> MigrateNodeState:
    if self._cancel_event.is_set():
        self.state.cancel()
        return self.state
    # ... 执行逻辑
```

### 6.3 错误处理

**异常捕获**：
```python
try:
    result = self._client.execute(self.script).fetchone()
    rows = result[0] if result else 0
    self.state.finish(rows=rows)
except duckdb.InterruptException:
    self.state.cancel()
except Exception as e:
    self.state.fail(str(e))
finally:
    self._client.close()
```

**错误传播**：
- Node 层错误 → 更新 MigrateNodeState.error
- Service 层检查 node.state.succeeded，传播到 MigrateRequestState

### 6.4 状态持久化

**Registry 结构**：
```json
{
  "mig_abc123": {
    "request": {
      "id": "mig_abc123",
      "source_name": "tushare_stock_daily",
      "from_destination": "oss_finconnect",
      "to_destination": "oss_fortress",
      ...
    },
    "status": "DONE",
    "started_at": "2024-06-05T12:00:00",
    "finished_at": "2024-06-05T12:05:00",
    "node": {
      "id": "mignctx_abc123def456",
      "state": {
        "status": "DONE",
        "rows": 1000000
      },
      "script": "COPY (...) TO 's3://...'"
    }
  }
}
```

---

## 七、性能优化

### 7.1 内存优化

**零拷贝架构**：
- 数据不进入 Python 内存
- DuckDB 直接读写 S3
- 适合 TB 级数据迁移

**内存限制**：
```sql
SET memory_limit = '8GB';  -- 限制 DuckDB 内存使用
```

### 7.2 并行读写

**DuckDB 自动并行**：
```python
PRAGMA threads = 4;  # 利用多核并行读写
```

**Glob 并行**：
- `s3://bucket/path/**/*.parquet` 会并行读取多个文件
- DuckDB 自动分片和负载均衡

### 7.3 压缩和格式

**默认选项**：
```python
options = [
    "FORMAT parquet",       # 使用 Parquet 格式
    "COMPRESSION snappy",   # Snappy 压缩（快速）
]
```

**可选压缩**：
- `COMPRESSION gzip` - 更高压缩比
- `COMPRESSION zstd` - 平衡压缩比和速度
- `COMPRESSION snappy` - 最快速度

---

## 八、与 Core 的对比

| 维度 | Core | Migrate |
|------|------|---------|
| **架构层次** | 3 层（Service/Pipeline/PipeNode） | 2 层（Service/Node） |
| **派生机制** | 有（Strategy 展开） | 无（1 request = 1 node） |
| **执行引擎** | Python + Polars | DuckDB SQL |
| **数据流转** | API → Polars → OSS/DB | OSS → DuckDB → OSS |
| **内存占用** | 数据经过 Python | 数据不经过 Python |
| **并发控制** | 两级（Pipeline + PipeNode） | 单级（DuckDB threads） |
| **转换能力** | Python 代码 | SQL |
| **取消方式** | threading.Event | DuckDB interrupt |
| **适用场景** | API 抓取、复杂转换 | OSS 迁移、大规模数据 |
| **典型规模** | 百万行级别 | 亿行级别 |
