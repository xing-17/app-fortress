# Bridges Core 架构设计

## 一、三层架构

Core 采用三层架构设计：

```
┌─────────────────────────────────────────────┐
│      Service 层 (_service/)                  │
│                                             │
│  CoreService        - 核心调度服务          │
│  CoreRequest        - 请求对象              │
│  CoreRequestState   - 请求状态              │
│  CoreRegistry       - 注册表管理            │
└─────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────┐
│      Pipeline 层 (pipeline/)                 │
│                                             │
│  PipelineNode       - 管道节点              │
│  PipelineContext    - 管道上下文            │
│  PipelineState      - 管道状态              │
└─────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────┐
│      PipeNode 层 (pipenode/)                 │
│                                             │
│  PipeNode           - 执行节点              │
│  PipeNodeContext    - 节点上下文            │
│  PipeNodeState      - 节点状态              │
└─────────────────────────────────────────────┘
```

### 职责划分

- **Service 层**：请求生命周期管理、资源解析、任务调度、状态追踪
- **Pipeline 层**：单个数据源的完整处理流程、策略派生、并发控制
- **PipeNode 层**：最小执行单元、数据获取和写出

---

## 二、Service 层

### 2.1 CoreService

核心调度服务，继承 `BaseBridgesService`。

**核心属性**：
- `_registry: CoreRegistry` - 请求历史注册表
- `_warehouse: BridgesWarehouse` - 资源仓库
- `_queue: Queue[CoreRequest]` - 请求队列
- `_worker: Thread` - 后台工作线程

**核心方法**：
```python
# 推导执行计划
derive(request: CoreRequest) -> list[PipelineNode]

# 生成初始状态
plan(request: CoreRequest) -> CoreRequestState

# 执行请求
run(request: CoreRequest) -> CoreRequestState

# 提交到队列（异步）
submit(request: CoreRequest) -> str

# 查询状态
lookup(request_id: str) -> dict

# 取消执行
cancel(request_id: str) -> None
```

**执行流程**：
1. `_derive_sources()` - 根据 tags 筛选 Source
2. `_derive_providers()` - 为每个 Source 匹配 Provider
3. `_derive_destinations()` - 解析 Destination 列表
4. `_derive_params()` - 构建参数字典
5. 为每个 Source-Provider 组合创建 `PipelineNode`
6. 并发执行所有 `PipelineNode`

### 2.2 CoreRequest

请求对象，定义数据抓取任务的输入参数。

```python
class CoreRequest(BaseContext):
    providers: dict[str, str]          # {"tushare": "tushare_prod"}
    sources_by_tags: dict[str, str]    # {"region": "cn", "asset": "stock"}
    params: dict[str, str]             # {"trade_date": "20240101"}
    destinations: list[str]            # ["oss_prod_tushare"]
```

### 2.3 CoreRequestState

请求状态，追踪执行进度和结果。

```python
class CoreRequestState(BaseRequestState):
    request: CoreRequest
    status: CoreRequestStatus          # PENDING/RUNNING/DONE/...
    pipeline_states: list[PipelineState]
    succeeded: int
    failed: int
    canceled: int
```

### 2.4 CoreRegistry

注册表，持久化请求历史到本地文件。

```python
class CoreRegistry:
    def put(request_id: str, state: dict) -> None
    def get(request_id: str) -> dict | None
    def list() -> list[dict]
```

---

## 三、Pipeline 层

### 3.1 PipelineNode

管道节点，负责单个数据源的完整处理流程。

**核心属性**：
```python
context: PipelineContext               # 包含 Source, Provider, Destinations, Params
state: PipelineState                   # 状态追踪
_cancel_event: threading.Event         # 取消信号
```

**核心方法**:
```python
start() -> None                        # 标记开始
derive() -> list[PipeNodeContext]      # 策略派生
run() -> PipelineState                 # 执行所有节点
finish() -> None                       # 收集统计
cancel() -> None                       # 取消执行
```

**执行流程**：
1. `start()` - 设置状态为 RUNNING
2. `derive()` - 通过 Strategy 派生多个 PipeNodeContext
3. `run()` - 根据 Provider 的并发配置执行节点
4. `finish()` - 统计成功/失败/取消数量，设置最终状态

### 3.2 PipelineContext

管道上下文，封装执行所需的所有资源和参数。

```python
class PipelineContext(BaseContext):
    request_id: str                    # 请求 ID
    source: BaseSource                 # 数据源
    provider: BaseProvider             # 提供商
    destinations: list[BaseDestination] # 目标列表
    params: dict[str, Any]             # 参数字典
```

### 3.3 PipelineState

管道状态，追踪单个 Pipeline 的执行结果。

```python
class PipelineState:
    context: PipelineContext
    status: PipelineStatus             # PENDING/RUNNING/DONE/...
    pipenode_states: list[PipeNodeState]
    succeeded: int
    failed: int
    canceled: int
```

---

## 四、PipeNode 层

### 4.1 PipeNode

最小执行单元，负责单次数据获取和写出。

**核心属性**：
```python
context: PipeNodeContext               # 节点上下文
state: PipeNodeState                   # 节点状态
_cancel_event: threading.Event         # 取消信号
```

**核心方法**：
```python
start() -> None                        # 标记开始
run() -> PipeNodeState                 # 执行数据抓取和写出
finish() -> None                       # 完成收尾
cancel() -> None                       # 取消执行
```

**执行流程**：
1. 调用 `source.run(provider, params)` 获取数据
2. 遍历 destinations，调用 `destination.write_source(data, ...)`
3. 生成数据质量报告，调用 `destination.write_source_quality(quality)`
4. 更新状态为 DONE/FAILED

### 4.2 PipeNodeContext

节点上下文，包含派生后的具体执行参数。

```python
class PipeNodeContext(BaseContext):
    pipeline_id: str                   # 所属 Pipeline ID
    request_id: str                    # 所属 Request ID
    source: BaseSource
    provider: BaseProvider
    destinations: list[BaseDestination]
    params: dict[str, Any]             # 派生后的具体参数
```

### 4.3 PipeNodeState

节点状态，记录单次执行的结果。

```python
class PipeNodeState:
    context: PipeNodeContext
    status: PipeNodeStatus             # PENDING/RUNNING/DONE/FAILED/CANCELED
    error: Exception | None
    data_quality: SourceDataQuality | None
```

---

## 五、完整执行流程

```
1. 用户提交请求
   ↓
CoreService.submit(request)
   - 生成 request_id
   - 加入 Queue
   - 后台 Worker 消费
   ↓
2. CoreService.run(request)
   ↓
derive(request) → list[PipelineNode]
   - _derive_sources(request) → 根据 tags 筛选 Sources
   - _derive_providers(request, sources) → 匹配 Providers
   - _derive_destinations(request) → 解析 Destinations
   - _derive_params(request) → 构建参数
   - 为每个 Source-Provider 创建 PipelineNode
   ↓
3. 并发执行 PipelineNodes (ThreadPoolExecutor)
   ↓
PipelineNode.run()
   - start() → 标记开始
   - derive() → 策略派生 PipeNodeContexts
   - 并发或顺序执行 PipeNodes
   - finish() → 收集统计
   ↓
4. PipeNode.run()
   - start() → 标记开始
   - source.run(provider, params) → 获取数据
   - destination.write_source(data) → 写出数据
   - destination.write_source_quality(quality) → 写出质量
   - finish() → 完成
   ↓
5. 返回 CoreRequestState
   - 聚合所有 PipelineState
   - 统计成功/失败/取消数量
   - 更新注册表
```

---

## 六、关键机制

### 6.1 并发控制

- **Service 层**：使用 ThreadPoolExecutor 并发执行多个 PipelineNode
- **Pipeline 层**：根据 Provider 配置决定是否并发执行 PipeNode
  - `provider.concurrent = true` → 并发执行
  - `provider.concurrent = false` → 顺序执行

### 6.2 取消机制

- 使用 `threading.Event` 实现取消信号传播
- 取消从 Service 层传播到 Pipeline 层，再到 PipeNode 层
- 未开始的节点直接标记为 CANCELED

### 6.3 状态管理

三级状态追踪：
1. **CoreRequestState** - 请求级状态，聚合所有 Pipeline
2. **PipelineState** - 管道级状态，聚合所有 PipeNode
3. **PipeNodeState** - 节点级状态，单次执行结果

### 6.4 策略派生

通过 Strategy 将单个 Pipeline 派生为多个 PipeNode：
- **DateRangeStrategy**：按日期范围派生
- **SymbolListStrategy**：按股票列表派生
- **CustomStrategy**：自定义派生逻辑

### 6.5 注册表持久化

CoreRegistry 将请求状态持久化到本地 JSON 文件：
- 支持断点恢复
- 支持历史查询
- 支持状态回溯
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
