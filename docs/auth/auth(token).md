# Bearer 令牌（auth.py）

代码：`app/service/_common/auth.py`、`app/service/_common/http.py`。配置：`AuthSetting`、`TokenSetting`（`app/setting/service.py`）。

## 1. 核心思想：令牌是推导出来的，不是存起来的

```
token = hex( HMAC-SHA256( masterkey, "fortress-token-v1:<name>:<version>" ) )   # 64 个十六进制字符
```

- `masterkey`：一个服务一份的主密钥文件内容（至少 32 字符）。
- `name`、`version`：配置里的条目名与版本。
- 服务端什么都不存。验证时对每个条目重新计算，与请求带来的令牌做常量时间比较。

由此得到：

| 需求 | 做法 |
|---|---|
| 签发 | 配置里加条目，`fortress auth show <name>` 取出 |
| 轮换 | 条目 `version` 加 1，旧令牌立即失效 |
| 吊销 | `revoked: true` 或删除条目 |
| 过期 | `expires`（最后有效日，UTC，当天仍有效） |
| 全部作废 | 换主密钥 |

## 2. 数据结构

| 名称 | 作用 |
|---|---|
| `TokenSetting` | 一个条目：`name`（`^[a-z0-9][a-z0-9-]{0,31}$`）、`description`、`version`（默认 1，至少 1）、`expires`、`revoked`、`delegate` |
| `AuthSetting` | `masterfile`（相对路径以 settings 目录为基准）与 `tokens`；条目名必须唯一 |
| `TokenAuth` | `token(name)`、`verify(raw)`、`state(name)`、`generate_master_file(...)` |
| `Principal` | 不可变的调用者身份：`name`、`description`、`delegate` |
| `AuthError` | 拒绝时抛出，消息永远是 `invalid token`，真实原因在 `.reason` |
| `TokenAuthState` | 不可变快照（配置、主密钥、条目、文件戳），热加载时整体替换 |
| `BearerAuthMiddleware` | ASGI 中间件，见第 5 节 |

## 3. 验证过程（`TokenAuth.verify`）

1. 不是字符串或长度不是 64 → `malformed`。
2. 取当前状态（必要时先热加载）。
3. 对每个条目计算 HMAC，用 `hmac.compare_digest` 比较；遍历全部条目，不提前返回。
4. 没有命中 → `mismatch`。
5. 命中但条目 `revoked` → `revoked`；今天（UTC）晚于 `expires` → `expired`。
6. 通过 → `Principal(name, description, delegate)`。

`token(name)` 只对 `active` 的条目返回令牌；未知条目抛 `ValueError("unknown token ...")`，吊销或过期的条目抛 `ValueError("token ... is revoked/expired")`。

## 4. 主密钥文件

- 创建：`TokenAuth.generate_master_file(setting, base_dir)`，内容为 `secrets.token_hex(32)`（64 字符），用 `O_EXCL` 与 `0o600` 创建，已存在返回 `None`，不覆盖。
- 读取：文件必须存在；POSIX 下组或其他人有任何权限就拒绝（`chmod 600`）；去掉首尾空白后少于 32 字符拒绝。错误信息不含密钥内容。

## 5. HTTP 中间件（`BearerAuthMiddleware`）

读取 `Authorization: Bearer <令牌>`（scheme 不区分大小写），交给 `TokenAuth.verify`，通过后把 `Principal` 放入 `request.state.principal`。

- 缺少头 → `missing`；scheme 不是 bearer → `malformed`。
- `/health` 默认公开（`public_paths`）；mcphost 传空集合，全部需要认证。
- 拒绝一律返回 `401 {"error":"unauthorized"}` 与 `WWW-Authenticate: Bearer`，原因只进日志 `auth rejected`。

### 委托（`delegate`）

host 服务（mcphost、webhost）已经认证了真正的调用者，但 node 需要知道“是谁在查”，用于独立会话和审计。

- 带 `delegate: true` 的令牌可以发 `X-Fortress-Caller: <名字>`。
- 名字必须符合 `^[a-z0-9][a-z0-9-]{0,31}$`，否则 `malformed caller`。
- 结果主体是 `Principal(name="<令牌名>:<名字>")`，**不继承 `delegate`**。
- 没有 `delegate` 的令牌发这个头 → `delegation denied`。

例：mcphost 用 node 上的 `mcphost` 令牌，代表 `xingxing` 查询，node 看到的调用者是 `mcphost:xingxing`。

## 6. 热加载

```python
TokenAuth(setting, base_dir=..., reload=<返回新 AuthSetting 的函数>, watch=[services.yaml])
```

- 主密钥文件与 `watch` 的文件会被 stat（`mtime_ns` 与大小）；最多每 `reload_interval`（默认 1 秒）检查一次，`0` 表示每次调用都检查。
- 有变化时调用 `reload()` 并重读主密钥，整体替换状态；成功记录 `auth reloaded`（带令牌数）。
- 失败（YAML 写错、密钥文件问题）保留旧状态，记录 `auth reload failed, rollback to previous state`，并记下新的文件戳，所以只有文件再次变化才会重试。
- 同一时间只有一个线程做重载，其他线程直接使用手头的状态。
- 注意：写错配置不会锁死所有人，但也不会吊销任何东西，改完要看日志。

CLI 启动时（`app/cline.py` 的 `_build_auth`）只把 `services.yaml` 里 `auth` 这一块接上热加载，其余配置（`nodes[].token`、`public_hosts`、`access`、端口）需要重启。

## 7. 令牌的两个方向

```
mcphost 用户令牌（mcphost.auth）          node 服务令牌（node.auth）
   谁在调用 mcphost                          mcphost 或 webhost 凭什么访问 node
   例：codex、chatgpt                        例：mcphost（delegate: true）、webhost
   主密钥：mcphost.key                       主密钥：node.key
   fortress auth show <name> --service mcphost   fortress auth show <name>
```

node 的 `mcphost` 令牌需要手工填进 `mcphost.nodes[].token`（`SecretStr`，repr 与导出不显示）。mcphost 启动时会调用一次 node 的 `list_sources` 来证明令牌有效（`/health` 不要令牌，不能证明）。

## 8. 命令与用法

```bash
fortress auth init [--service node|mcphost]            # 创建主密钥，已存在则退出码 1
fortress auth list [--service node|mcphost]            # 各条目的 state、expires、description
fortress auth show <name> [--service node|mcphost]     # 打印令牌，非 active 时报错、退出码 1
```

`--setting-path` 可指定 settings 目录。`--service` 默认 `node`。

调用示例：

```bash
TOKEN=$(fortress auth show codex --service mcphost)
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8801/mcp
```

## 9. 令牌状态与时间线

```
签发 (条目存在, version=N)
   │  active：verify 通过
   ├── version → N+1 ───────────────> 旧令牌 mismatch（新令牌 active）
   ├── revoked: true / 删除条目 ──────> revoked 或 mismatch
   └── 当天之后 (UTC 日期 > expires) ──> expired
```

## 10. 注意事项

- `expires` 为空表示永不过期，建议总是设置并定期轮换。
- 日志与错误信息里不会出现令牌或主密钥；排错看 `AuthError.reason`（只在日志里）。
- 主密钥、`services.yaml`（含 `nodes[].token`）不要提交到 git。
