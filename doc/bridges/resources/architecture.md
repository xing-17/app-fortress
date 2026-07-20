# Bridges Resources 架构设计

## 一、资源管理架构

Resources 采用工厂模式 + 仓库模式管理所有资源：

```
┌────────────────────────────────────────────┐
│         BridgesWarehouse (仓库)             │
│                                            │
│  统一管理所有资源的加载、实例化和刷新        │
└────────────────────────────────────────────┘
         ↓           ↓           ↓           ↓
┌──────────────┬──────────────┬──────────────┬──────────────┐
│SourceFactory │ProviderFactory│DestinationFactory│ConnectionFactory│
│              │              │              │              │
│ 扫描YAML     │ 注册类型     │ 注册类型     │ 注册类型     │
│ 加载Source   │ 实例化       │ 实例化       │ 实例化       │
└──────────────┴──────────────┴──────────────┴──────────────┘
```

---

## 二、核心资源类型

### 2.1 Source（数据源）

定义数据获取的元信息和执行逻辑。

**BaseSource 核心功能**：
- 从 YAML 配置加载（`from_yaml()`）
- 缓存管理（内存 + 文件）
- 重试机制（tenacity）
- 分页抓取（Paginate）
- 速率限制（Coolant）

**Source 生命周期**：
```python
# 1. 从 YAML 加载
source = BaseSource.from_yaml("items/tushare/daily.yaml")

# 2. 执行数据抓取
data = source.run(provider, params={"trade_date": "20240101"})

# 内部流程：
# - 检查缓存
# - 速率限制（Coolant）
# - 构建参数（build_params）
# - 分页获取（_fetch_all + Paginate）
# - 重试机制（_call_with_retry）
# - 写入缓存
```

**YAML 配置示例**：
```yaml
name: tushare_daily
provider_type: tushare
method: daily
tags:
  region: cn
  asset: stock
  frequency: daily
cache:
  enabled: true
  ttl: 3600
retry:
  max_attempts: 3
  wait_exponential: [1, 10]
paginate:
  enabled: true
  page_size: 5000
```

### 2.2 Provider（数据提供商）

封装 API 调用和会话管理。

**BaseProvider 核心功能**：
- 会话管理（`_create_session()`）
- API 调用（`call(method, **params)`）
- 缓存支持（BridgesCache）
- 随机延迟（Jitter）

**Provider 生命周期**：
```python
# 1. 从配置实例化
provider = BaseProvider(name="tushare_prod")

# 2. 创建会话
session = provider._create_session()

# 3. API 调用
data = provider.call("daily", trade_date="20240101")

# 内部流程：
# - Jitter 随机延迟
# - 检查缓存
# - 调用 session.request()
# - 写入缓存
```

**配置示例（setting.yaml）**：
```yaml
bridges:
  providers:
    tushare_prod:
      name: tushare_prod
      type: tushare
      region: cn
      token: ${TUSHARE_TOKEN}
      jitter_min_seconds: 0.1
      jitter_max_seconds: 0.5
      cache:
        enabled: true
        ttl: 3600
```

### 2.3 Destination（数据目标）

定义数据写出逻辑。

**BaseDestination 核心功能**：
- 数据写出（`write_source()`）
- 质量报告（`write_source_quality()`）
- DLT 集成（`as_dlt_destination()`）

**Destination 生命周期**：
```python
# 1. 从配置实例化（注入 Connection）
dest = BaseDestination(name="oss_prod_tushare", connection=conn)

# 2. 写出数据
dest.write_source(
    data=df,
    table_name="tushare_daily",
    partition_col="trade_date",
    partition_prefix="date",
)

# 3. 写出质量报告
dest.write_source_quality(quality)
```

**配置示例（setting.yaml）**：
```yaml
bridges:
  destinations:
    oss_prod_tushare:
      name: oss_prod_tushare
      type: oss
      connection: oss_prod
      path: s3://bucket/tushare/
```

### 2.4 Connection（连接）

封装底层存储连接。

**BaseConnection 核心功能**：
- 连接池管理
- 生命周期管理（`connect()`, `close()`）
- 健康检查

**Connection 生命周期**：
```python
# 1. 从配置实例化
conn = BaseConnection(name="oss_prod")

# 2. 建立连接
conn.connect()

# 3. 获取客户端
client = conn.get_client()

# 4. 关闭连接
conn.close()
```

---

## 三、工厂模式

所有资源通过工厂模式注册和实例化。

### 3.1 注册机制

```python
# 注册 Provider
@ProviderFactory.register("tushare")
class TushareProvider(BaseProvider):
    def _create_session(self) -> BaseSession:
        return TushareSession(setting=self.setting)
    
    def call(self, method: str, **params) -> Any:
        return self._session.request(method, **params)

# 注册 Destination
@DestinationFactory.register("oss")
class OSSDestination(BaseDestination):
    def write_source(self, data, table_name, ...):
        # 写出逻辑
        ...

# 注册 Connection
@ConnectionFactory.register("oss")
class OSSConnection(BaseConnection):
    def connect(self):
        # 连接逻辑
        ...
```

### 3.2 工厂引导（Bootstrap）

```python
class BridgesWarehouse:
    def load_providers(self) -> dict[str, BaseProvider]:
        return self._provider_factory.bootstrap()
    
    def load_sources(self) -> dict[str, BaseSource]:
        return self._source_factory.bootstrap()
    
    def load_destinations(self) -> dict[str, BaseDestination]:
        return self._destination_factory.bootstrap(self._connections)
    
    def load_connections(self) -> dict[str, BaseConnection]:
        return self._connection_factory.bootstrap()
```

---

## 四、辅助组件

### 4.1 Coolant（速率限制）

控制请求频率，避免触发 API 限流。

```python
class Coolant:
    def __init__(self, min_seconds: float, max_seconds: float):
        self.min_seconds = min_seconds
        self.max_seconds = max_seconds
    
    def wait(self) -> None:
        # 计算距离上次请求的时间间隔
        # 如果不足 min_seconds，则等待
        ...
```

### 4.2 Jitter（随机延迟）

避免请求时间过于集中。

```python
class Jitter:
    def __init__(self, min_seconds: float, max_seconds: float):
        self.min_seconds = min_seconds
        self.max_seconds = max_seconds
    
    def wait(self) -> None:
        time.sleep(random.uniform(self.min_seconds, self.max_seconds))
```

### 4.3 Paginate（分页管理）

自动化翻页逻辑。

```python
class Paginate:
    def __init__(self, page_size: int):
        self.page_size = page_size
    
    def iterate(self, fetch_func, total_count) -> Iterator[pl.DataFrame]:
        # 计算总页数
        # 逐页调用 fetch_func
        # 返回每页数据
        ...
```

### 4.4 Cache（缓存）

多级缓存支持（内存 + 文件）。

```python
class BridgesCache:
    def get(self, key: str) -> Any | None:
        # 先查内存缓存
        # 再查文件缓存
        ...
    
    def set(self, key: str, value: Any, ttl: int) -> None:
        # 写入内存缓存
        # 写入文件缓存
        ...
```

---

## 五、策略派生

Strategy 用于将单个 Source 派生为多个执行上下文。

### 5.1 BaseStrategy

```python
class BaseStrategy:
    def derive(
        self,
        source: BaseSource,
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        # 派生逻辑
        # 返回多个参数字典
        ...
```

### 5.2 策略示例

**DateRangeStrategy**：按日期范围派生
```python
# 输入: {"start_date": "20240101", "end_date": "20240103"}
# 输出: [
#   {"trade_date": "20240101"},
#   {"trade_date": "20240102"},
#   {"trade_date": "20240103"},
# ]
```

**SymbolListStrategy**：按股票列表派生
```python
# 输入: {"symbols": ["000001.SZ", "000002.SZ"]}
# 输出: [
#   {"ts_code": "000001.SZ"},
#   {"ts_code": "000002.SZ"},
# ]
```

---

## 六、数据质量

### 6.1 SourceDataQuality

数据质量对象，记录数据统计信息。

```python
class SourceDataQuality:
    source_name: str
    provider_name: str
    rows: int
    columns: int
    null_counts: dict[str, int]
    duplicate_rows: int
    data_size_bytes: int
    fetch_duration: float
```

### 6.2 质量检查流程

```python
# 1. Source 执行完成后生成质量对象
quality = SourceDataQuality.from_dataframe(
    df=data,
    source_name=source.name,
    provider_name=provider.name,
)

# 2. Destination 写出质量报告
destination.write_source_quality(quality)
```

---

## 七、完整数据流

```
1. BridgesWarehouse 初始化
   ↓
   load_providers() → 实例化所有 Providers
   load_connections() → 实例化所有 Connections
   load_destinations() → 实例化所有 Destinations
   load_sources() → 从 YAML 加载所有 Sources
   ↓

2. CoreService 执行请求
   ↓
   derive_sources() → warehouse.get_sources_by_tags()
   derive_providers() → warehouse.get_provider()
   derive_destinations() → warehouse.get_destination()
   ↓

3. PipelineNode 执行
   ↓
   Strategy.derive() → 派生多个 PipeNodeContext
   ↓

4. PipeNode 执行
   ↓
   Source.run(provider, params)
     ↓
     - Coolant.wait() → 速率限制
     - Cache.get() → 检查缓存
     - build_params() → 构建参数
     - _fetch_all() → 分页获取
       ↓
       - Paginate.iterate()
       - _call_with_retry() → 重试机制
         ↓
         - Jitter.wait() → 随机延迟
         - Provider.call() → API 调用
           ↓
           - Session.request() → 实际请求
     - Cache.set() → 写入缓存
   ↓
   Destination.write_source(data)
     ↓
     - Connection.get_client() → 获取连接
     - 写入数据
   ↓
   Destination.write_source_quality(quality)
     ↓
     - 写入质量报告
```

---

## 八、关键设计原则

### 8.1 配置驱动

所有资源从配置文件加载：
- **Sources**：YAML 文件定义元信息
- **Providers**：setting.yaml 定义连接配置
- **Destinations**：setting.yaml 定义输出配置
- **Connections**：setting.yaml 定义连接配置

### 8.2 工厂模式

所有资源通过工厂模式管理：
- 支持类型注册（`@Factory.register()`）
- 支持批量实例化（`bootstrap()`）
- 支持依赖注入（Connection → Destination）

### 8.3 缓存策略

多级缓存支持：
- **内存缓存**：快速访问，生命周期与进程一致
- **文件缓存**：持久化，支持跨进程共享
- **TTL 控制**：过期自动失效

### 8.4 容错机制

- **重试**：tenacity 指数退避
- **速率限制**：Coolant 控制请求频率
- **随机延迟**：Jitter 避免请求集中
- **分页抓取**：Paginate 自动翻页

### 8.5 扩展性

- **Provider**：通过 `@ProviderFactory.register()` 注册新类型
- **Destination**：通过 `@DestinationFactory.register()` 注册新类型
- **Connection**：通过 `@ConnectionFactory.register()` 注册新类型
- **Strategy**：通过 `@StrategyFactory.register()` 注册新策略
- **Source**：添加 YAML 配置文件即可
2. `run()` - 并发或串行执行所有 SourceNode
3. `finish()` - 收集统计信息，设置最终状态

### 2.5 执行层 (Source Layer)

| 组件 | 职责 |
|------|------|
| `SourceNode` | 最小执行单元，执行原子数据获取任务 |
| `SourceContext` | 执行上下文，包含 request_id、pipeline_id、provider、source、destinations、params |
| `SourceState` | 执行状态追踪（SUCCESS/FAILED/CANCELED） |
| `SourceQuality` | 数据质量报告（行数、列数、空值率、重复率等） |

**执行流程**：
1. `invoke()` - 调用 `source.run(provider, params)` 获取数据
2. `invoke()` - 调用 `source.transform(data)` 转换数据
3. `_write_data()` - 写入所有 Destinations
4. `_write_quality()` - 生成并写入质量报告（可选）

### 2.6 实现层 (Implementation Layer)

| 组件 | 职责 |
|------|------|
| `BaseSource` | 数据源基类，定义数据获取和转换逻辑 |
| `BaseProvider` | 数据提供商基类，封装 API 调用和会话管理 |
| `BaseDestination` | 目标存储基类，定义数据写入接口 |
| `BaseConnection` | 连接基类，管理数据库连接池 |
| `BaseSession` | 会话基类，管理 HTTP/API 会话 |

**辅助组件**：
- `Coolant`：请求速率限制（避免触发 API 限流）
- `Paginate`：分页抓取管理
- `Jitter`：随机延迟（避免请求过于规律）
- `Retry`：重试机制（指数退避）

---

##三、层与组件协作流程

### 3.1 完整执行流程

```
1. 用户提交请求
   ↓
2. BridgesCoreCluster.submit(request)
   - 创建 BridgesCoreRequestState
   - 加入 Queue
   - 返回 request_id
   ↓
3. Worker Thread 消费队列
   - 调用 BridgesCoreCluster.run(request)
   ↓
4. BridgesCoreCluster.derive(request)
   - 解析 sources_by_tags → 筛选 Sources
   - 解析 providers → 获取 Provider 实例
   - 解析 destinations → 获取 Destination 实例
   - 组装参数
   - 创建 PipeContext 列表
   - 创建 PipeNode 列表
   ↓
5. BridgesCoreCluster.run() 并发执行 PipeNodes
   - ThreadPoolExecutor 并发执行（可配置线程数）
   - 每个 PipeNode.run()
   ↓
6. PipeNode.derive()
   - 根据 Source 配置的 Strategy 派生多个 SourceNode
   - 例如：DateRangeStrategy 将 [2024-01-01, 2024-01-31] 拆分为 31 个日期
   ↓
7. PipeNode.run() 并发执行 SourceNodes
   - 根据 Provider 的并发配置决定串行或并发
   - 每个 SourceNode.run()
   ↓
8. SourceNode.run()
   - invoke() - 调用 source.run(provider, params) 获取数据
   - invoke() - 调用 source.transform(data) 转换数据
   - _write_data() - 写入所有 Destinations
   - _write_quality() - 生成质量报告（可选）
   ↓
9. 状态回溯
   - SourceNode 完成 → 更新 SourceState
   - PipeNode 完成 → 收集所有 SourceState → 更新 PipeState
   - BridgesCoreCluster 完成 → 收集所有 PipeState → 更新 BridgesCoreRequestState
   ↓
10. 持久化和清理
    - 更新 BridgesCoreClusterRegistry（JSON 文件）
    - 从 _live 字典移除请求
    - 用户可通过 request_id 查询 Registry
```

### 3.2 关键路径详解

#### 路径 1：请求解析 (derive)

```python
BridgesCoreCluster.derive(request)
├── _derive_sources(request)
│   └── resources.get_sources_by_tags(sources_by_tags)
├── _derive_providers(request, sources)
│   ├── 使用 request.providers 指定的 Provider
│   └── 或根据 source.provider_type 自动匹配
├── _derive_destinations(request)
│   └── resources.get_destination(name) for name in request.destinations
├── _derive_params(request)
│   └── 返回 request.params
└── 创建 PipeContext → PipeNode
```

#### 路径 2：策略派生 (Strategy)

```python
PipeNode.derive()
├── 获取 Strategy: (provider_type, strategy_name)
│   └── strategy = StrategyFactory.create((provider_type, strategy_name))
├── 调用 strategy.run(provider, params)
│   └── 返回 list[dict] - 多组参数
└── 为每组参数创建 SourceContext → SourceNode
```

**常见策略示例**：
- `NullStrategy`：不拆分，直接使用原始参数
- `DateRangeStrategy`：按日期范围拆分
- `DateListStrategy`：按日期列表拆分
- `SymbolStrategy`：按股票代码拆分

#### 路径 3：数据流转 (Data Flow)

```python
SourceNode.run()
├── source.run(provider, params)
│   ├── 检查缓存
│   ├── _fetch_all(provider, params)
│   │   ├── source.build_params(params)
│   │   ├── provider.call(method, **params)
│   │   └── 分页抓取 + 速率限制 + 重试
│   └── 写入缓存
├── source.transform(data)
│   ├── 列重命名、类型转换
│   ├── 时区处理
│   └── 返回 pl.DataFrame
├── destination.write(data, metadata)
│   ├── 写入文件（Parquet/CSV）
│   ├── 写入数据库（Postgres/DuckDB）
│   └── 写入缓存
└── 返回 SourceState
```

### 3.3 并发控制机制

#### 三级并发控制

1. **Cluster 级别**：
   - `max_threads` 控制 PipeNode 并发数
   - 通过 `ThreadPoolExecutor` 实现

2. **Provider 级别**：
   - `max_concurrent` 控制单个 Provider 的并发请求数
   - 决定 SourceNode 是串行还是并发执行

3. **Queue 级别**：
   - `max_queue_size` 限制队列容量
   - 防止内存溢出

#### 取消机制

```python
# 支持三级取消传播
BridgesCoreCluster.cancel(request_id)
└── BridgesCoreRequestState.cancel()
    └── PipeNode.cancel()
        └── SourceNode.cancel()

# 使用 threading.Event 实现
- 在执行前检查 _cancel_event.is_set()
- 如果已取消，跳过执行，状态标记为 CANCELED
```

---

##四、组件使用指南

### 4.1 调度层使用

#### 基本用法

```python
from app.bridges.core.cluster import BridgesCoreCluster
from app.bridges.core.request import BridgesCoreRequest

# 创建集群（单例）
cluster = BridgesCoreCluster()

# 提交异步请求
request = BridgesCoreRequest(
    sources_by_tags={"region": "cn", "type": "stock"},
    destinations=["parquet"],
)
request_id = cluster.submit(request)

# 查询状态
status = cluster.lookup(request_id)
print(status["status"])  # PENDING/RUNNING/DONE/PARTIAL/FAILED

# 取消请求
cluster.cancel(request_id)
```

#### 同步执行

```python
# 直接调用 run（不经过队列）
request = BridgesCoreRequest(...)
state = cluster.run(request)
print(state.export())
```

#### 资源管理

```python
# 刷新资源（重新加载 YAML 配置）
cluster.refresh()

# 重置（清理缓存 + 重新加载）
cluster.reset()

# 导出集群信息
info = cluster.export()
print(info["queue"]["current_size"])
print(info["registry"]["total"])
```

### 4.2 请求层使用

#### 构建请求

```python
from app.bridges.core.request import BridgesCoreRequest

# 指定 Provider
request = BridgesCoreRequest(
    providers={"tushare": "tushare_prod"},  # 使用特定 Provider 实例
    sources_by_tags={"type": "daily"},
    params={"trade_date": "20240101"},
    destinations=["parquet", "postgres"],
)

# 自动匹配 Provider
request = BridgesCoreRequest(
    sources_by_tags={"region": "cn", "type": "stock"},  # 自动根据 provider_type 匹配
    params={"start_date": "2024-01-01", "end_date": "2024-01-31"},
    destinations=["duckdb"],
)

# 导出配置
config = request.export()
json_str = request.describe()
```

### 4.3 资源层使用

#### 访问资源

```python
from app.bridges.resources._warehouse.warehouse import ModuleBridgesWarehouse

resources = ModuleBridgesWarehouse

# 获取 Provider
provider = resources.get_provider("tushare_prod")

# 获取 Source
source = resources.get_source("tushare_daily")

# 按标签筛选 Sources
sources = resources.get_sources_by_tags({"region": "cn", "type": "stock"})

# 获取 Destination
destination = resources.get_destination("parquet")
```

#### 手动调用

```python
# 直接调用 Source
data = source.run(provider, {"trade_date": "20240101"})
print(data.shape)

# 写入 Destination
result = destination.write(data, {"source": "tushare_daily"})
print(result)
```

### 4.4 Pipeline层使用

#### 创建 Pipeline

```python
from app.bridges.pipelines.context import PipeContext
from app.bridges.pipelines.node import PipeNode

# 创建上下文
context = PipeContext(
    request_id="req_123",
    provider=provider,
    source=source,
    destinations=[dest1, dest2],
    params={"trade_date": "20240101"},
)

# 创建并执行节点
node = PipeNode(context)
state = node.run()

# 查看结果
print(state.export())
print(f"成功: {state.success}/{state.total}")
```

#### 策略使用

```python
# 策略在 Source 配置中指定
# items/tushare/my_source.yaml
strategy: by_date  # 按日期拆分

# 策略会自动被 PipeNode.derive() 调用
# 将单个日期范围拆分为多个单日任务
```

### 4.5 执行层使用

#### 创建执行节点

```python
from app.bridges.sources.context import SourceContext
from app.bridges.sources.node import SourceNode

# 创建上下文
context = SourceContext(
    request_id="req_123",
    pipeline_id="pipe_456",
    provider=provider,
    source=source,
    destinations=[destination],
    params={"trade_date": "20240101"},
)

# 创建并执行节点
node = SourceNode(context)
state = node.run()

# 查看质量报告
if node.quality:
    print(f"行数: {node.quality.row_count}")
    print(f"列数: {node.quality.column_count}")
    print(f"空值率: {node.quality.null_rate}")
```

### 4.6 实现层使用

#### 开发自定义 Source

```python
from app.bridges.resources.sources.base.source import BaseSource

class MySource(BaseSource):
    _setting_class = MySourceSetting
    
    def build_params(self, params: dict) -> dict:
        # 组装 API 参数
        return {
            "date": params.get("trade_date"),
            "symbol": params.get("symbol"),
        }
    
    def _fetch_all(self, provider, params):
        # 调用 Provider 获取数据
        return provider.call(self.setting.method, **params)
```

#### 开发自定义 Provider

```python
from app.bridges.resources.providers.base.provider import BaseProvider
from app.bridges.resources.providers.base.factory import ProviderFactory

@ProviderFactory.register("my_provider")
class MyProvider(BaseProvider):
    def _create_session(self):
        return MySession(self.setting)
    
    def call(self, method: str, **kwargs):
        return self.get_session().request(method, **kwargs)
    
    def export(self) -> dict:
        return {"name": self.name, "type": self.type}
```

#### 开发自定义 Destination

```python
from app.bridges.resources.destinations.base.destination import BaseDestination
from app.bridges.resources.destinations.base.factory import DestinationFactory

@DestinationFactory.register("my_destination")
class MyDestination(BaseDestination):
    def write(self, df, metadata: dict) -> dict:
        # 实现写入逻辑
        path = self.setting.path / f"{metadata['source']}.parquet"
        df.write_parquet(path)
        return {"path": str(path), "rows": len(df)}
```

#### 开发自定义 Strategy

```python
from app.bridges.resources.strategies.base.strategies import BaseStrategy
from app.bridges.resources.strategies.base.factory import StrategyFactory

@StrategyFactory.register("my_provider", "by_symbol")
class SymbolStrategy(BaseStrategy):
    def run(self, provider, params: dict) -> list[dict]:
        symbols = params.get("symbols", [])
        return [
            {**params, "symbol": symbol}
            for symbol in symbols
        ]
```

---

## 五、最佳实践

### 5.1 性能优化

1. **合理配置并发**：
   - `bridges.max_threads` 控制 Pipeline 并发数（推荐 2-4）
   - `provider.max_concurrent` 控制单个 Provider 并发数（注意 API 限流）

2. **启用缓存**：
   - Source 级别缓存（`cache.enabled: true`）
   - 设置合理的 TTL（`cache.ttl: 3600`）

3. **使用策略拆分**：
   - 大范围查询使用 DateRangeStrategy 拆分
   - 避免单个请求数据量过大

### 5.2 错误处理

1. **重试配置**：
   - `retry.max_attempts: 3`
   - `retry.wait_seconds: 2`
   - `retry.backoff_factor: 2`

2. **状态检查**：
   - DONE：全部成功
   - PARTIAL：部分成功（可重试失败的部分）
   - FAILED：全部失败

3. **日志追踪**：
   - 每个组件都有 LogPlugin
   - 使用 request_id / pipeline_id / source_id 追踪

### 5.3 资源管理

1. **连接池**：
   - Connection 自动管理连接池
   - 避免频繁创建销毁连接

2. **会话复用**：
   - Provider 内部维护 Session
   - 自动处理 Token 刷新

3. **定期清理**：
   - Registry 会持久化历史记录
   - 定期清理过期记录（`registry.clean()`）

---

## 六、架构优势

1. **分层解耦**：每层职责清晰，便于扩展和测试
2. **工厂模式**：支持插件式注册，易于添加新资源类型
3. **策略模式**：灵活的参数派生机制，支持多种拆分策略
4. **并发控制**：三级并发控制，兼顾性能和稳定性
5. **状态追踪**：完整的状态追踪和持久化，支持断点续传
6. **质量保障**：内置数据质量检查，及时发现数据异常
7. **缓存机制**：多级缓存，减少重复请求
8. **取消机制**：支持任务取消，避免资源浪费
