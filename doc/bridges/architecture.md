# Bridges 架构设计

## 一、总体架构层次

Bridges 采用六层架构设计，从上到下依次为：

```
┌─────────────────────────────────────────────┐
│          调度层 (Cluster Layer)              │  集群管理、队列调度、并发控制
├─────────────────────────────────────────────┤
│          请求层 (Request Layer)              │  请求封装、状态追踪
├─────────────────────────────────────────────┤
│          资源层 (Resource Layer)             │  资源管理、工厂模式、生命周期
├─────────────────────────────────────────────┤
│          Pipeline层 (Pipe Layer)             │  Pipeline 编排、策略派生
├─────────────────────────────────────────────┤
│          执行层 (Source Layer)               │  原子任务执行、数据质量检查
├─────────────────────────────────────────────┤
│          实现层 (Implementation Layer)       │  具体资源实现（Source/Provider/Destination）
└─────────────────────────────────────────────┘
```

### 职责划分

- **调度层**：负责请求队列管理、并发控制、任务分发
- **请求层**：封装用户请求，追踪执行状态
- **资源层**：统一管理所有资源（Sources、Providers、Destinations、Connections）
- **Pipeline层**：将请求解析为多个 Pipeline 节点，通过策略派生细粒度任务
- **执行层**：执行原子数据获取任务，包含数据转换和质量检查
- **实现层**：各类资源的具体实现（如 TushareProvider、PostgresDestination 等）

---

## 二、各层关键组件

### 2.1 调度层 (Cluster Layer)

| 组件 | 职责 |
|------|------|
| `BridgesCoreCluster` | 集群入口，管理请求生命周期 |
| `BridgesCoreClusterRegistry` | 持久化请求执行历史（JSON 文件） |
| `Queue[BridgesCoreRequest]` | 请求队列，支持最大容量限制 |
| `Worker Thread` | 后台线程，串行消费队列 |

**核心方法**：
- `submit(request) -> request_id`：提交请求到队列，返回请求 ID
- `run(request) -> state`：执行请求的完整流程
- `lookup(request_id) -> dict`：查询请求状态
- `cancel(request_id)`：取消请求执行
- `derive(request) -> list[PipeNode]`：解析请求，派生 Pipeline 节点

### 2.2 请求层 (Request Layer)

| 组件 | 职责 |
|------|------|
| `BridgesCoreRequest` | 请求对象，包含 sources、providers、params、destinations |
| `BridgesCoreRequestState` | 请求状态追踪，包含统计信息（成功/失败/部分成功） |
| `BridgesCoreRequestStatus` | 状态枚举（PENDING/RUNNING/DONE/PARTIAL/FAILED/CANCELED） |

**BridgesCoreRequest 结构**：
```python
{
    "id": "req_abc123",
    "providers": {"tushare": "tushare_prod"},
    "sources_by_tags": {"region": "cn", "type": "stock"},
    "params": {"start_date": "2024-01-01"},
    "destinations": ["parquet", "postgres"]
}
```

### 2.3 资源层 (Resource Layer)

| 组件 | 职责 |
|------|------|
| `BridgesWarehouse` | 资源容器，管理所有资源实例 |
| `ProviderFactory` | Provider 工厂，支持类型注册和实例化 |
| `SourceFactory` | Source 工厂，从 YAML 文件加载 |
| `DestinationFactory` | Destination 工厂，支持类型注册和实例化 |
| `ConnectionFactory` | Connection 工厂，管理数据库连接 |
| `BridgesCache` | 全局缓存管理，支持多种缓存策略 |

**资源访问方法**：
- `get_provider(name) -> BaseProvider`
- `get_source(name) -> BaseSource`
- `get_destination(name) -> BaseDestination`
- `get_sources_by_tags(tags) -> list[BaseSource]`
- `load()` / `refresh()`：加载或刷新所有资源

### 2.4 Pipeline层 (Pipe Layer)

| 组件 | 职责 |
|------|------|
| `PipeNode` | Pipeline 节点，管理单个 Source-Provider-Destinations 组合 |
| `PipeContext` | Pipeline 上下文，封装 Provider、Source、Destinations、Params |
| `PipeState` | Pipeline 状态追踪（PENDING/RUNNING/DONE/PARTIAL/FAILED） |
| `BaseStrategy` | 策略基类，将参数派生为多个子参数（如按日期分区） |
| `StrategyFactory` | 策略工厂，按 (provider_type, strategy_name) 注册 |

**执行流程**：
1. `derive()` - 根据 Source 配置的 Strategy 派生多个 SourceNode
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
