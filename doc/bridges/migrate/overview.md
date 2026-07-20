# Bridges Migrate 概览

## 模块定位

Migrate 是 Bridges 的数据迁移层，负责对象存储（OSS）之间的数据迁移任务。基于 DuckDB 引擎，实现 S3 直连读写，数据不经过 Python 内存，性能高效。

## 架构分层

### 1. Service 层（_service/）

核心调度服务，负责迁移请求的生命周期管理。

- **MigrateService**：主服务类，继承 BaseBridgesService，实现请求调度和执行
- **MigrateRequest**：请求对象，定义数据迁移任务的输入参数
- **MigrateRequestState**：请求状态，追踪执行进度和结果
- **MigrateRegistry**：注册表，持久化请求历史和状态

### 2. Node 层（node/）

执行节点，负责单次迁移任务的执行。

- **MigrateNode**：最小执行单元，执行 DuckDB COPY 语句完成迁移
- **MigrateNodeContext**：节点上下文，包含源目标、转换 SQL、执行选项
- **MigrateNodeState**：节点状态，记录执行结果和迁移行数

## 执行流程

```
MigrateService.submit(request)
  ↓ derive from_destination/to_destination
  ↓ create MigrateNode
  ↓ 
MigrateService.run(request)
  ↓ 
MigrateNode.run()
  ↓ setup DuckDB client
  ↓ create S3 secrets
  ↓ execute COPY statement
  ↓ 
COPY (
  SELECT * FROM read_parquet('s3://from/**/*.parquet')
) TO 's3://to/**/*.parquet'
```

## 使用示例

```python
from app.bridges.migrate import MigrateService, MigrateRequest

# 创建服务
service = MigrateService()

# 构建请求
request = MigrateRequest(
    source_name="tushare_stock_daily",
    from_destination="oss_finconnect",
    from_glob="s3://bucket-src/finconnect/landing/tushare_stock_daily/**/*.parquet",
    to_destination="oss_fortress",
    transform_sql="SELECT * EXCLUDE(unused_col) FROM <source> WHERE date >= '2024-01-01'",
)

# 提交并执行
request_id = service.submit(request)
state = service.lookup(request_id)

# 同步等待完成
final_state = service.run(request)
print(f"迁移行数: {final_state.total_rows}")
```

## 关键特性

- **两层架构**：Service → Node，结构扁平，职责清晰
- **DuckDB 引擎**：利用 DuckDB 原生 S3 支持，数据不经过 Python 内存
- **SQL 转换**：支持在迁移过程中进行数据转换（列过滤、行过滤、类型转换）
- **取消机制**：支持请求取消，通过 DuckDB interrupt 实现
- **注册表**：持久化请求历史，支持查询和回溯
- **高性能**：纯引擎内执行，适合大规模数据迁移

## 核心组件

- **MigrateService**：服务调度和请求管理
- **MigrateRequest**：请求对象，包含 source_name、from_destination、to_destination、transform_sql
- **MigrateRequestState**：请求状态追踪
- **MigrateNode**：执行节点，生成并执行 DuckDB COPY 语句
- **SecretDuckdb**：DuckDB S3 secret 管理，按 bucket 路由凭证

## 与 Core 的对比

| 特性 | Core | Migrate |
|------|------|---------|
| 用途 | API 数据抓取 | OSS 数据迁移 |
| 架构层次 | 3 层（Service/Pipeline/PipeNode） | 2 层（Service/Node） |
| 执行引擎 | Python + Polars | DuckDB SQL |
| 数据流 | API → Polars → OSS/DB | OSS → DuckDB → OSS |
| 数据经过内存 | ✅ 是 | ❌ 否 |
| 并发策略 | 两级并发（Pipeline + PipeNode） | 单级并发（DuckDB threads） |
| 转换能力 | Python 代码（source.transform） | SQL（transform_sql） |
| 典型场景 | 金融数据抓取 | 数据湖迁移 |
