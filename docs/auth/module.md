# service/_common 与 auth 体系总览

代码位置：`app/service/_common`。所有 fortress 服务（node、mcphost、webhost）共用的基础件。

| 文件 | 内容 |
|---|---|
| `_service.py` | `BaseService`：服务生命周期状态机与日志 |
| `auth.py` | `TokenAuth`、`Principal`、`AuthError`：静态 Bearer 令牌（派生式，不存储） |
| `access.py` | `AccessAuth`：验证 Cloudflare Access 签发的身份断言（ChatGPT 的 OAuth 路径） |
| `http.py` | `BearerAuthMiddleware`、`JsonResponse`：ASGI 认证中间件与统一 JSON 响应 |

相关文档：

- [auth(token).md](auth(token).md)：Bearer 令牌如何工作
- [access(oauth).md](access(oauth).md)：ChatGPT 的 OAuth 如何工作

配置模型在 `app/setting/service.py`：`TokenSetting`、`AuthSetting`、`AccessUserSetting`、`AccessSetting`。配置文件是 `settings/services.yaml`。

## 1. 两条认证路径

fortress 有两种调用者，对应两种凭证：

| 调用者 | 能力 | 凭证 | 入口 |
|---|---|---|---|
| 本机客户端（Codex、VS Code） | 能发自定义 `Authorization` 头 | 静态 Bearer 令牌（由主密钥派生） | `http://127.0.0.1:8801/mcp`，不经 Cloudflare |
| ChatGPT（网页与手机） | 只支持 OAuth，不能发静态 Bearer | Cloudflare Access 的 OAuth，mcphost 验证 Access 签名的身份断言 | `https://www.fortressfront.app/mcp` |

ChatGPT 的连接器是账号级配置，请求由 OpenAI 的服务器发出，所以入口必须能从公网到达；公网只暴露 mcphost，node 始终只监听 `127.0.0.1`。

## 2. 整体架构与信任链

```
ChatGPT ──HTTPS──> Cloudflare Access (OAuth 授权服务器 + 策略)
                        │  通过后附加 Cf-Access-Jwt-Assertion
                        ▼  (cloudflared 隧道，主动外连)
Codex / VS Code ─────> mcphost 127.0.0.1:8801
                        │  BearerAuthMiddleware：断言 或 Bearer
                        │  Host / Origin 检查 (public_hosts)
                        ▼  服务令牌 + X-Fortress-Caller: <调用者名>
                       node 127.0.0.1:8800
                        │  BearerAuthMiddleware：Bearer + 委托
                        ▼
                       数据（每个调用者独立会话与审计）
```

三层各验各的，不互相信任：

1. Cloudflare：谁能走到 mcphost（OAuth 登录 + Allow 策略，只放行指定邮箱）。
2. mcphost：再验一次身份。断言必须签名有效、`iss`、`aud` 正确、邮箱在白名单；或者 Bearer 令牌有效。
3. node：只认 mcphost 的服务令牌（`delegate: true`），调用者名通过 `X-Fortress-Caller` 传入。

最终 node 看到的调用者名形如 `mcphost:xingxing`（ChatGPT 用户）或 `mcphost:codex`（本机 Codex 令牌）。

## 3. 请求的认证顺序（`BearerAuthMiddleware`）

```
请求进来
 ├─ lifespan 或 public_paths（node 的 /health）→ 直接放行
 ├─ 配置了 access 且带 Cf-Access-Jwt-Assertion
 │     → 只按断言判定，失败直接 401，不回退 Bearer
 └─ 否则 → 要求 Authorization: Bearer <令牌>
 然后：
 ├─ 无 X-Fortress-Caller → 主体即验证出的 Principal
 └─ 有 X-Fortress-Caller
       ├─ 主体 delegate=false（含所有 Access 身份）→ 拒绝 "delegation denied"
       ├─ 名字不符合 ^[a-z0-9][a-z0-9-]{0,31}$ → 拒绝 "malformed caller"
       └─ 通过 → Principal(name="<令牌名>:<调用者>")，且不继承 delegate
通过后 principal 写入 request.state.principal
```

失败响应永远是同一个：

```
401 {"error": "unauthorized"}
WWW-Authenticate: Bearer
```

真正的原因（`missing`、`malformed`、`mismatch`、`revoked`、`expired`、`delegation denied`、`access assertion <异常类名>`、`access identity not allowed` 等）只写入日志 `auth rejected`（带 `reason`、`path`、`client`），不返回给调用者。

mcphost 的 `public_paths` 为空，所有路径都需要认证；node 只有 `/health` 公开。

## 4. 生命周期

### 4.1 首次部署

```bash
# 每个服务一把主密钥（node 一把，mcphost 一把），权限 600，已存在则不覆盖
fortress auth init                    # node：local/.auth/node.key
fortress auth init --service mcphost  # mcphost：local/.auth/mcphost.key
```

主密钥至少 32 字符，POSIX 下必须是 `chmod 600`，否则服务拒绝启动。

### 4.2 签发

在 `settings/services.yaml` 里加条目，令牌本身不存储，由主密钥和条目名、版本推导：

```yaml
node:
  auth:
    masterfile: ../local/.auth/node.key
    tokens:
      - name: mcphost          # node 上给 mcphost 用的服务令牌
        version: 1
        expires: 2027-10-22    # 最后有效日（UTC）
        delegate: true         # 可以替别人（调用者）发请求
mcphost:
  auth:
    masterfile: ../local/.auth/mcphost.key
    tokens:
      - { name: codex, description: Codex connector, version: 1, expires: 2027-10-22 }
```

取出令牌并分发：

```bash
fortress auth show mcphost                   # node 上的 mcphost 令牌
fortress auth show codex --service mcphost   # 给 Codex 的用户令牌
```

node 的 `mcphost` 令牌填进 `mcphost.nodes[].token`（这一项改完需要重启 mcphost）。

### 4.3 运行与热加载

- node 与 mcphost 启动时用 `TokenAuth(reload=…, watch=[services.yaml])`。主密钥文件或 `services.yaml` 变化后（最多每 1 秒检查一次），`auth` 部分自动重载，**吊销、轮换、新增令牌无需重启**。
- 重载失败（YAML 写错、密钥文件有问题）会保留旧状态并记录 `auth reload failed, rollback to previous state`：写错不会锁死所有人，但也不会吊销任何东西，改完要看日志确认 `auth reloaded`。
- 不会热加载（需要重启）：`mcphost.access`（团队域名、AUD、白名单邮箱）、`public_hosts`、`nodes[].token`、监听地址与端口。

### 4.4 轮换、吊销、过期

| 操作 | 做法 | 效果 |
|---|---|---|
| 轮换单个令牌 | 把该条目 `version` 加 1，再 `fortress auth show` 取新令牌 | 旧令牌立即失效 |
| 吊销 | `revoked: true`，或删除条目 | 立即失效 |
| 过期 | `expires: <日期>`，当天仍有效，次日起失效 | 自动失效 |
| 更换主密钥 | 换掉 `*.key` 文件 | 该服务下所有令牌全部失效，需要重新分发（node 主密钥更换后，mcphost 里的 `nodes[].token` 也要更新并重启） |
| 删除 ChatGPT 访问 | 在 Cloudflare Access 策略里删除邮箱；同时删 `mcphost.access.users` 中的条目并重启 | 两层都拒绝 |

`fortress auth list [--service mcphost]` 查看各条目的状态（`active`、`revoked`、`expired`）与过期日。

### 4.5 一次完整请求（ChatGPT）

1. ChatGPT 通过 Cloudflare 完成 OAuth（见 [access(oauth).md](access(oauth).md)），带着 Cloudflare 签发的访问令牌请求 `/mcp`。
2. Cloudflare 校验通过后把签名过的身份断言放进 `Cf-Access-Jwt-Assertion`，经隧道转给 mcphost。
3. `BearerAuthMiddleware` 在线程池里用 `AccessAuth.verify` 验证断言，邮箱映射为名字 `xingxing`，`Principal(name="xingxing")`。
4. MCP 传输层检查 Host 与 Origin 是否在 `public_hosts` 内，否则 421 或 403。
5. 工具调用时，mcphost 用自己的 node 服务令牌，并带 `X-Fortress-Caller: xingxing` 请求 node。
6. node 的中间件验证服务令牌与委托，主体变为 `mcphost:xingxing`，查询在该调用者独立的会话里执行并留下审计。

## 5. 使用速查

### 5.1 本机客户端

```bash
TOKEN=$(fortress auth show codex --service mcphost)
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8801/mcp
```

在 Codex、VS Code 的 MCP 配置里，URL 为 `http://127.0.0.1:8801/mcp`，请求头为 `Authorization: Bearer <令牌>`。

### 5.2 ChatGPT

在 ChatGPT 添加自定义 MCP 连接器，URL 填 `https://www.fortressfront.app/mcp`，认证方式选 OAuth，按提示用白名单邮箱登录（One-time PIN）。

### 5.3 启动

```bash
fortress node start      # 先启动 node，监听 127.0.0.1:8800
fortress mcphost start   # 启动 mcphost，启动时会检查 node 是否在线、令牌是否有效
```

### 5.4 在代码里使用

```python
from pathlib import Path
from app.service._common import TokenAuth
from app.service._common.http import BearerAuthMiddleware

# 首次：创建主密钥（已存在返回 None）
TokenAuth.generate_master_file(setting, base_dir=Path("settings"))

auth = TokenAuth(
    setting,                                    # AuthSetting
    base_dir=Path("settings"),                  # masterfile 相对路径的基准
    reload=load_auth_setting,                   # 可选，开启热加载
    watch=[Path("settings/services.yaml")],
)
token = auth.token("codex")        # 派生令牌（只有 active 条目可以）
principal = auth.verify(token)     # 返回 Principal，失败抛 AuthError

app = BearerAuthMiddleware(asgi_app, auth=auth, log=log)

# 带 Cloudflare Access 时：
# from app.service._common.access import AccessAuth
# app = BearerAuthMiddleware(asgi_app, auth=auth, log=log, access=AccessAuth(setting.access))
```

mcphost 里 `McpHostService` 在 `setting.access` 存在时自动构造 `AccessAuth`；`asgi_app()` 在没有 `auth` 时直接抛错（不允许无认证服务数据）。

## 6. 排错

| 现象 | 可能原因 | 查看 |
|---|---|---|
| 公网 401 且响应里有 OAuth 发现信息 | 请求在 Cloudflare 就被拦了：未登录或策略不通过 | Cloudflare Access 日志 |
| 公网 401 `{"error":"unauthorized"}` | mcphost 拒绝：断言无效、邮箱不在白名单、或令牌错误 | mcphost 日志 `auth rejected` 的 `reason` |
| 421 或 403 | Host 或 Origin 不在 `public_hosts` | 检查 `public_hosts` 与隧道的 Public Hostname |
| mcphost 启动报 "node rejected the token" | `mcphost.nodes[].token` 与 node 当前令牌不匹配（主密钥、版本、过期、吊销变过） | `fortress auth show mcphost` 取新值 |
| 改了 `services.yaml` 没生效 | 重载失败，保留旧状态 | 日志 `auth reload failed` |
| 启动报 masterfile 权限错误 | 不是 600 | `chmod 600 local/.auth/*.key` |
| 断言验证报 `access keys unavailable` | 本机取不到 Cloudflare 公钥（失败即关闭，请求被拒） | 本机网络、团队域名 |

## 7. 安全要点

- 令牌不存储：泄露的只有主密钥文件和 `services.yaml` 里的 `nodes[].token`，两者都不应进版本控制。
- 令牌比较用 `hmac.compare_digest`，且遍历所有条目不提前返回，没有计时差异。
- 断言只接受 RS256，拒绝 `none` 与 HS256；`exp`、`iat`、`iss`、`aud` 缺一不可。
- Access 身份与服务令牌不能互相冒充：Access 身份不能用 `X-Fortress-Caller`，被委托的主体不再继承 `delegate`。
- 断言存在时不回退 Bearer，避免用弱路径绕过强路径。
