# Bridges 概览

## Bridges 是什么

Bridges 是一个数据桥接框架，用于统一管理多源数据的获取、处理和输出。它通过标准化的接口连接不同的数据提供商（如 Tushare、Wind 等），将数据转换后输出到指定目标（数据库、文件、缓存等）。

核心特性：
- 多数据源统一管理
- 异步并发执行
- 自动重试和缓存
- 请求队列和状态追踪
- 灵活的标签筛选机制

## 体系定位

Bridges 位于 app-fortress 的数据层核心，承担以下职责：

- **资源管理层**：统一管理 Sources（数据源）、Providers（提供商）、Destinations（目标地）
- **调度执行层**：通过 BridgesCoreCluster 调度请求，支持并发和队列化处理
- **数据流转层**：从数据获取到输出的完整 Pipeline，包含数据转换、缓存、重试等机制

## 使用方式

### 基本用法

```python
from app.bridges.core.cluster import BridgesCoreCluster
from app.bridges.core.request import BridgesCoreRequest

# 创建集群
cluster = BridgesCoreCluster()

# 构建请求
request = BridgesCoreRequest(
    providers={"tushare": "tushare_prod"},
    sources_by_tags={"region": "cn", "type": "stock"},
    params={"trade_date": "20240101"},
    destinations=["parquet", "duckdb"],
)

# 提交请求（异步执行）
request_id = cluster.submit(request)

# 查询状态
status = cluster.lookup(request_id)

# 取消请求
cluster.cancel(request_id)
```

### 配置文件

在 `setting.yaml` 中配置 providers 和 destinations：

```yaml
bridges:
  providers:
    tushare_prod:
      type: tushare
      token: ${TUSHARE_TOKEN}
  
  destinations:
    parquet:
      type: parquet
      path: /data/output
```

## 开发新的 Bridge

### 1. 开发新的 Source

在 `app/bridges/resources/sources/items/` 创建配置文件：

```yaml
# items/my_provider/my_source.yaml
name: my_source
provider_type: my_provider
method: get_data
tags:
  region: cn
  type: stock
cache:
  enabled: true
  ttl: 3600
retry:
  max_attempts: 3
```

创建 Source 类（如需自定义逻辑）：

```python
from app.bridges.resources.sources.base.source import BaseSource

class MySource(BaseSource):
    def build_params(self, params: dict) -> dict:
        # 构建 API 参数
        return {"date": params.get("trade_date")}
    
    def _fetch_all(self, provider, params):
        # 调用 provider 获取数据
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
