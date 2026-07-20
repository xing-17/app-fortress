# Bridges Resources 概览

## 模块定位

Resources 是 Bridges 的资源管理层，提供数据源、提供商、目标地、连接等核心资源的统一管理和工厂实例化。

## 核心组件

### 1. Warehouse（_warehouse/）

资源仓库，统一管理所有资源的加载和刷新。

- **BridgesWarehouse**：资源仓库主类，管理四大工厂和资源实例
  - `load_providers()`: 加载所有 Provider 实例
  - `load_connections()`: 加载所有 Connection 实例
  - `load_destinations()`: 加载所有 Destination 实例
  - `load_sources()`: 加载所有 Source 实例
  - `refresh()`: 刷新所有资源和缓存

### 2. Sources（sources/）

数据源，定义数据获取的元信息和执行逻辑。

- **BaseSource**：数据源基类
  - 从 YAML 配置加载（`from_yaml()`）
  - 缓存管理（内存缓存 + 文件缓存）
  - 重试机制（tenacity）
  - 分页抓取（Paginate）
  - 速率限制（Coolant）
- **SourceFactory**：数据源工厂，扫描并实例化所有数据源

### 3. Providers（providers/）

数据提供商，封装 API 调用和会话管理。

- **BaseProvider**：提供商基类
  - 会话管理（`_create_session()`）
  - API 调用（`call(method, **params)`）
  - 缓存支持（BridgesCache）
  - 随机延迟（Jitter）
- **BaseSession**：会话基类，管理 API 客户端生命周期
- **ProviderFactory**：提供商工厂，根据配置实例化 Provider

### 4. Destinations（destinations/）

数据目标，定义数据写出逻辑。

- **BaseDestination**：目标基类
  - 数据写出（`write_source()`）
  - 质量报告（`write_source_quality()`）
  - DLT 集成（`as_dlt_destination()`）
- **DestinationFactory**：目标工厂，根据配置实例化 Destination

### 5. Connections（connections/）

连接管理，封装底层存储连接。

- **BaseConnection**：连接基类，管理数据库、对象存储等连接
- **ConnectionFactory**：连接工厂，实例化并共享连接对象

### 6. Strategies（strategies/）

执行策略，定义数据源派生逻辑。

- **BaseStrategy**：策略基类，将单个 Source 派生为多个执行上下文
  - 按时间范围派生（日期列表）
  - 按分区派生（股票列表）
  - 自定义派生逻辑
- **StrategyFactory**：策略工厂

### 7. Cache（cache/）

缓存管理，提供多级缓存支持。

- **BridgesCache**：缓存类，支持内存和文件缓存
- **ModuleBridgesCache**：模块级缓存单例

### 8. Quality（quality/）

数据质量检查和报告。

- **SourceDataQuality**：数据源质量对象，记录数据统计信息

### 9. Accessory（accessory/）

辅助工具，提供通用功能。

- **Coolant**：速率限制，控制请求频率
- **Paginate**：分页管理，自动化翻页逻辑
- **Jitter**：随机延迟，避免请求时间过于集中

### 10. Secret（secret/）

密钥管理，处理敏感信息。

## 工厂模式

所有资源通过工厂模式管理：

```python
# 注册 Provider
@ProviderFactory.register("tushare")
class TushareProvider(BaseProvider):
    ...

# 注册 Destination
@DestinationFactory.register("oss")
class OSSDestination(BaseDestination):
    ...

# 注册 Connection
@ConnectionFactory.register("oss")
class OSSConnection(BaseConnection):
    ...
```

## 使用示例

### 通过 Warehouse 访问

```python
from app.bridges.resources import BridgesWarehouse

warehouse = BridgesWarehouse()

# 获取 Provider
provider = warehouse.get_provider("tushare_prod")

# 获取 Source
source = warehouse.get_source("tushare_daily")

# 获取 Destination
dest = warehouse.get_destination("oss_prod_tushare")

# 执行数据抓取
data = source.run(provider, params={"trade_date": "20240101"})
```

### 直接使用资源

```python
from app.bridges.resources.sources.base.source import BaseSource
from app.bridges.resources.providers.base.provider import BaseProvider

# 加载 Source
source = BaseSource.from_yaml("items/tushare/daily.yaml")

# 创建 Provider
provider = BaseProvider(name="tushare_prod")

# 执行抓取
data = source.run(provider, params={"trade_date": "20240101"})
```

## 关键特性

- **统一管理**：Warehouse 统一加载和刷新所有资源
- **工厂模式**：通过注册机制实现扩展
- **配置驱动**：从 YAML 和 setting.yaml 加载配置
- **缓存支持**：多级缓存（内存 + 文件）
- **重试机制**：自动重试失败请求
- **速率限制**：Coolant + Jitter 控制请求频率
- **分页支持**：自动化翻页逻辑
- **质量检查**：数据质量统计和报告
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
