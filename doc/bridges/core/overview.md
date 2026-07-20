# Bridges Core 概览

## 模块定位

Core 是 Bridges 的调度执行层，负责请求的编排、任务派发和状态管理。通过三层架构实现数据抓取任务的并发执行和状态追踪。

## 架构分层

### 1. Service 层（_service/）

核心调度服务，负责请求生命周期管理。

- **CoreService**：主服务类，继承 BaseBridgesService，实现请求调度和执行
- **CoreRequest**：请求对象，定义数据获取任务的输入参数
- **CoreRequestState**：请求状态，追踪执行进度和结果
- **CoreRegistry**：注册表，持久化请求历史和状态

### 2. Pipeline 层（pipeline/）

管道节点，负责单个数据源的完整处理流程。

- **PipelineNode**：管道节点，从单个 Source 派生多个 PipeNode 并执行
- **PipelineContext**：管道上下文，包含 Source、Provider、Destinations、Params
- **PipelineState**：管道状态，收集统计信息（成功/失败/取消）

### 3. PipeNode 层（pipenode/）

子节点，负责单次数据获取和写出。

- **PipeNode**：最小执行单元，执行 Source.run() → Destination.write()
- **PipeNodeContext**：节点上下文，包含派生后的具体执行参数
- **PipeNodeState**：节点状态，记录单次执行的结果

## 执行流程

```
CoreService.submit(request)
  ↓ derive sources/providers/destinations
  ↓ create PipelineNodes
  ↓ 
CoreService.run(request)
  ↓ 并发执行
  ↓
PipelineNode.run()
  ↓ derive strategy (生成多个 PipeNodeContext)
  ↓ 顺序或并发执行
  ↓
PipeNode.run()
  ↓ source.run(provider, params)
  ↓ destination.write(data)
```

## 使用示例

```python
from app.bridges.core import CoreService, CoreRequest

# 创建服务
service = CoreService()

# 构建请求
request = CoreRequest(
    providers={"tushare": "tushare_prod"},
    sources_by_tags={"region": "cn", "asset": "stock"},
    params={"trade_date": "20240101"},
    destinations=["oss_prod_tushare"],
)

# 提交并执行
request_id = service.submit(request)
state = service.lookup(request_id)

# 同步等待完成
final_state = service.run(request)
```

## 关键特性

- **三层架构**：Service → Pipeline → PipeNode，职责清晰
- **并发控制**：支持 Pipeline 并发、PipeNode 顺序或并发
- **状态管理**：请求级、管道级、节点级三级状态追踪
- **取消机制**：支持请求取消，通过 threading.Event 传播
- **注册表**：持久化请求历史，支持查询和回溯
        return provider.call(self.setting.method, **params)
```

### 2. 开发新的 Provider

继承 `BaseProvider` 并实现必要方法：

```python
from app.bridges.resources.providers.base.provider import BaseProvider
from app.bridges.resources.providers.base.session import BaseSession

class MyProvider(BaseProvider):
    def _create_session(self) -> BaseSession:
        return MySession(setting=self.setting)
    
    def call(self, method: str, **kwargs):
        # 实现 API 调用逻辑
        return self.get_session().request(method, **kwargs)
    
    def export(self) -> dict:
        return {
            "name": self.name,
            "type": self.type,
            "region": self.region,
        }
```

注册到工厂：

```python
from app.bridges.resources.providers.factory import ProviderFactory

ProviderFactory.register("my_provider")(MyProvider)
```

### 3. 开发新的 Destination

继承 `BaseDestination` 并实现 `write` 方法：

```python
from app.bridges.resources.destinations.base.destination import BaseDestination

class MyDestination(BaseDestination):
    def write(self, df, metadata: dict) -> dict:
        # 实现数据写入逻辑
        path = self.setting.path / f"{metadata['source']}.parquet"
        df.write_parquet(path)
        return {"path": str(path), "rows": len(df)}
```

注册到工厂：

```python
from app.bridges.resources.destinations.factory import DestinationFactory

DestinationFactory.register("my_destination")(MyDestination)
```

### 4. 配置和测试

在 `setting.yaml` 中添加配置：

```yaml
bridges:
  providers:
    my_provider_prod:
      type: my_provider
      api_key: ${MY_API_KEY}
  
  destinations:
    my_destination:
      type: my_destination
      path: /data/output
```

编写测试：

```python
def test_my_source():
    source = MySource.from_yaml("items/my_provider/my_source.yaml")
    provider = MyProvider("my_provider_prod")
    data = source.run(provider, {"trade_date": "20240101"})
    assert data is not None
```

## 核心组件

- **BridgesCoreCluster**：集群管理和请求调度
- **BridgesCoreRequest**：请求对象，包含 sources、providers、params、destinations
- **BridgesCoreRequestState**：请求状态追踪
- **PipeNode**：Pipeline 节点，执行单个 source-provider-destination 流程
- **BridgesWarehouse**：资源注册表和工厂管理
