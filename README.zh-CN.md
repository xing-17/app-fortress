[English](README.md) | **中文**

# Fortress（伽蓝）

全球数据资产、元数据与算力的统一管理和交互终端。

- 管理数据源（Source）下的数据集（Dataset）：抓取、落盘（Vault/Asset）、元数据与质量（Store）。
- 以 **Node** 的形式对外提供 HTTP 接口，查询数据集、提交运行、执行只读 SQL。
- 在 Node 前面可选挂 **MCP Host**（给 ChatGPT/Codex 等连接）和 **Web Host**（浏览器控制台）。

## 目录结构

```
app/
  cline.py          CLI 入口（fortress 命令）
  entrypoint/       Compute（如阿里云 FC）调用的 handler：run_dataset / run_datasets
  resource/         资源层：identity / vault+asset / store / source(+dataset) / 全局单例
  service/          服务层：machine / node / mcphost / webhost
  setting/          Pydantic 配置模型（system.yaml / services.yaml 的结构）
  internal/         基础设施（日志、工具、数据模型等）
settings/           配置文件目录（system.yaml、services.yaml，已 gitignore）
local/              运行时数据：.auth 密钥、.logs 日志、vault、store、provision（已 gitignore）
docs/               设计文档（auth / cluster / network / node）
```

## Setup

### 1. 环境

需要 Python 3.11 与 conda。

```bash
make env       # 创建/更新 conda 环境 app-fortress
conda activate app-fortress
```

### 2. 安装依赖

```bash
pip install -e ".[dev]"
```

按需安装 extra：

| extra | 内容 |
|---|---|
| `aliyun` | OSS / FC / 阿里云凭证（使用 OSS vault/store 时需要） |
| `tushare` | Tushare 数据源 |
| `rba` | RBA 数据源 |
| `node` | 运行 Node（duckdb、starlette、uvicorn、psutil） |
| `mcphost` | 运行 MCP Host（含 `node`） |
| `webhost` | 运行 Web Host（含 `node`） |
| `dev` | 开发与测试（pytest、ruff、moto 等，含 `tushare`） |

例如运行完整服务：`pip install -e ".[aliyun,rba,mcphost,webhost]"`。

> `make install` 会同时往 conda 环境和当前 shell 的 pip 装非 editable 版本，开发时建议直接用上面的 `pip install -e`。

### 3. 配置

配置目录默认为 `settings/`（可用 `--setting-path` 覆盖）。`system.yaml` 与 `services.yaml` 含密钥/令牌，已被 `.gitignore` 排除，需要自己创建。

**`settings/system.yaml`**（必需）：节点基本信息与资源定义。

```yaml
alias: 伽蓝
node: snt                    # 节点名
version: 0.6.6
timezone: Australia/Sydney

log:
  name: system
  level: DEBUG
  file_path: "./local/.logs/system"

# 凭证（仅使用阿里云 OSS 时需要）
identities:
  - name: my_aliyun
    platform: aliyun
    type: ak
    access_key_id: <ACCESS_KEY_ID>
    access_key_secret: <ACCESS_KEY_SECRET>
    region: cn-shanghai

# 数据源：每个 source 自带 vault（文件）、store（元数据）、log
sources:
  - name: snt_local_abs
    provider: abs            # abs / nswvg / rba / tushare
    timezone: Australia/Sydney
    vault:
      name: snt_local_abs
      filesystem: local      # local 或 oss
      path: ./local/vault/source/abs/
    store:
      name: snt_local_abs
      storesystem: file      # file 或 oss
      path: ./local/store/source/abs/
    log:
      name: snt_local_abs
      level: DEBUG
      file_path: "./local/.logs/source/abs"
```

要点：

- `provider: tushare` 需要 `key`（Tushare token）。
- 使用 OSS 时，vault/store 写 `filesystem: oss` / `storesystem: oss`，并提供 `identity`、`bucket`、`region`、`prefix`、`in_vpc`。
- 顶层还支持 `identities` / `stores` / `vaults` / `computes` 独立声明，供 source 按名称引用。

**`settings/services.yaml`**（可选，只跑 Node 以外的服务或要鉴权时需要）：按服务分块 `machine` / `node` / `mcphost` / `webhost`。

```yaml
node:
  enabled: true
  host: 127.0.0.1
  port: 8800
  auth:
    masterfile: ../local/.auth/node.key   # 相对 settings 目录
    tokens:
      - name: mcphost
        version: 1
        expires: 2027-10-22
        delegate: true
mcphost:
  enabled: true
  port: 8801
  auth: { masterfile: ../local/.auth/mcphost.key, tokens: [...] }
  nodes:
    - name: snt
      endpoint: http://127.0.0.1:8800
      token: <node 签发的令牌>
webhost:
  enabled: true
  port: 8803
  auth: { masterfile: ../local/.auth/webhost.key, tokens: [...] }
  nodes:
    - name: snt
      endpoint: http://127.0.0.1:8800
      token: <node 签发的令牌>
```

### 4. 初始化令牌

令牌由主密钥 + 条目名 + 版本通过 HMAC 推导，服务端不存储（详见 [docs/auth/auth(token).md](docs/auth/auth(token).md)）。

```bash
fortress auth init --service node        # 生成 local/.auth/node.key（已存在则不覆盖）
fortress auth init --service mcphost
fortress auth init --service webhost

fortress auth list --service node        # 查看令牌状态
fortress auth show mcphost --service node   # 取出令牌，填入 mcphost/webhost 的 nodes[].token
```

轮换：条目 `version` +1；吊销：`revoked: true`；全部作废：换主密钥文件。

## 使用

### 启动服务

```bash
make start                 # 等价于 fortress up
```

`fortress up` 会先启动 Node，等端口就绪后启动 MCP Host，并在 `webhost.enabled` 时启动 Web Host；任一进程退出则全部停止。

也可以单独启动：

```bash
fortress node start    [--host H] [--port P] [--setting-path DIR]
fortress mcphost start [--node NAME] [--host H] [--port P] [--log-level info]
fortress webhost start [--host H] [--port P] [--log-level info]
```

### Node HTTP 接口

除 `GET /health` 外都需要 `Authorization: Bearer <token>`。

```bash
TOKEN=$(fortress auth show webhost --service node)

curl localhost:8800/health
curl -H "Authorization: Bearer $TOKEN" localhost:8800/internal/sources
curl -H "Authorization: Bearer $TOKEN" localhost:8800/internal/datasets?source=snt_local_abs

# 提交一次数据集运行（返回 202，随后轮询 runs/{id}）
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"params": {}}' \
  localhost:8800/internal/datasets/snt_local_abs/labour_force_month/runs

# 只读 SQL 查询
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"sql": "SELECT 1"}' localhost:8800/internal/query
```

主要路由：

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查（无需令牌） |
| GET | `/internal/sources[/{source}[/logs]]` | 数据源及日志 |
| GET | `/internal/datasets[?source=]` | 数据集列表 |
| GET | `/internal/datasets/{source}/{dataset}` | 数据集详情 |
| GET | `.../{dataset}/assetfiles｜metadatas｜qualities｜definitions` | 文件、元数据、质量、定义（支持 `since`/`until`） |
| GET/POST | `.../{dataset}/runs`、`.../runs/{id}` | 查询 / 提交运行 |
| GET | `/internal/machine/snapshots[?hours=]` | 机器快照 |
| POST | `/internal/query` | SQL 查询 |

### 直接以代码运行数据集

不经过 Node，直接用 `entrypoint` 里的 handler（也是部署到 FC 等 Compute 时使用的入口）：

```python
from app.entrypoint.run_dataset import handler

handler({
    "source": "snt_local_abs",
    "dataset": "labour_force_month",
    "params": {},
})
# -> {"ok": True, "results": [{"source": ..., "dataset": ..., "assetfiles": [...]}]}
```

批量运行用 `app.entrypoint.run_datasets`，payload 为 `{"items": [{"source", "dataset", "params"}, ...]}`。

### 已有数据源与数据集

| provider | 数据集示例 |
|---|---|
| `abs` | `labour_force_month`、`price_index_cpi_quarter`、`population_erp_quarter` 等 |
| `rba` | `g1_cpi_quarter`、`f6_lending_rates_housing_month` 等（需 `rba` extra） |
| `nswvg` | `psi_week`、`psi_year` |
| `tushare` | `tradedates`、`etf_list`（需 `tushare` extra 和 key） |

完整列表见 `app/resource/source/<provider>/datasets/`。

## 开发

```bash
pytest                 # 默认测试 app/ 下所有 tests
ruff format . && ruff check . --fix   # 或 make lint
make clean             # 清理构建与缓存
```

- 单元测试放在各模块 `tests/` 下，命名 `test_*_unit.py`。
- 新增数据集：在 `app/resource/source/<provider>/datasets/` 下加一个继承该 provider Dataset 基类的类，并设置 `name: ClassVar[str]`。

## 文档

- [docs/summary.md](docs/summary.md)：项目定位
- [docs/auth/](docs/auth/)：令牌与访问控制
- [docs/cluster/architecture.md](docs/cluster/architecture.md)：集群架构
- [docs/network/cloudflare.md](docs/network/cloudflare.md)：Cloudflare 隧道
