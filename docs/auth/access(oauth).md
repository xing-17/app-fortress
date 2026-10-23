# ChatGPT 的 OAuth（Cloudflare Access + access.py）

代码：`app/service/_common/access.py`（`AccessAuth`）、`app/service/_common/http.py`（`BearerAuthMiddleware`）。配置：`AccessSetting`、`AccessUserSetting`。

## 1. 为什么这样设计

- ChatGPT 的连接器只支持 OAuth，不能发自定义 API key 或静态 Bearer。
- 调用由 OpenAI 的服务器发出，入口必须在公网可达。
- 不自建 OAuth 服务器：Cloudflare Access 的 Managed OAuth 充当授权服务器；fortress 只负责验证 Access 签名的身份断言。

## 2. 角色分工

| 角色 | 负责 |
|---|---|
| ChatGPT | OAuth 客户端：动态注册、授权码 + PKCE、持有并刷新令牌 |
| Cloudflare Access（团队域名 `<team>.cloudflareaccess.com`） | 授权服务器（授权、令牌、动态注册端点）、登录（One-time PIN）、Allow 策略、令牌校验 |
| Cloudflare Tunnel（`cloudflared`） | 把 `www.fortressfront.app` 转到本机 `127.0.0.1:8801`，本机主动外连，不开放入站端口 |
| mcphost + `AccessAuth` | 验证 Access 签名的断言，把邮箱映射为调用者名 |
| node | 只信 mcphost 的服务令牌 + 委托，不直接面对 ChatGPT |

Cloudflare 侧配置（控制台里，仓库里没有）：Access 应用为 Self-hosted，域名 `www.fortressfront.app`；策略 Allow，只含白名单邮箱；Managed OAuth 已开启，Allowed redirect URIs 包含 ChatGPT 的回调（`https://chatgpt.com/connector_platform_oauth_redirect`、`https://chatgpt.com/connector/oauth/*`，以控制台实际内容为准）。

## 3. 授权过程（ChatGPT 添加连接器时）

```
ChatGPT                         Cloudflare                      用户
  │ 1. GET /mcp (无凭证)            │
  │ <── 401 + WWW-Authenticate ─────│  指向资源元数据
  │ 2. GET /.well-known/cloudflare-access-protected-resource/mcp
  │ <── authorization_servers = 团队域名
  │ 3. GET 团队域名/.well-known/oauth-authorization-server
  │ <── 授权、令牌、注册端点；支持 authorization_code、refresh_token、PKCE S256
  │ 4. 动态客户端注册（redirect URI 必须在 Allowed redirect URIs 里）
  │ 5. 浏览器跳转到授权端点 ───────────────────────────────────>│ 登录
  │                                  │ <── One-time PIN（邮箱）─│
  │                                  │ 策略判定：邮箱在 Allow 内
  │ <── 回调带授权码 ──────────────────│
  │ 6. 用授权码 + PKCE 换访问令牌与刷新令牌
```

已知故障与对应：

- “Some app settings were rejected”：Access 拒绝了动态注册，因为 Allowed redirect URIs 为空，补上 ChatGPT 回调。
- “Authentication succeeded, action discovery failed”：OAuth 成功但 mcphost 只认 Bearer，工具列表被 401，由 `AccessAuth` 解决。

## 4. 每次调用如何通过（运行时）

1. ChatGPT 带 Cloudflare 签发的访问令牌请求 `https://www.fortressfront.app/mcp`。
2. Cloudflare 校验令牌与策略；通过后把请求经隧道转发，并加上 `Cf-Access-Jwt-Assertion`（一个 JWT，签名密钥是团队发布的公钥）。
3. `BearerAuthMiddleware` 发现 mcphost 配置了 `access` 且请求带断言头：**只按断言判定**，坏断言直接 401，不回退 Bearer。
4. `AccessAuth.verify` 在线程池里执行（取公钥是阻塞调用）。
5. 通过后得到 `Principal(name=<邮箱对应的名字>, description="Cloudflare Access")`，写入 `request.state.principal`。
6. 传输层检查 Host 与 Origin（`public_hosts`）。
7. 调用工具时 mcphost 带 `X-Fortress-Caller: <名字>` 去访问 node。

## 5. `AccessAuth.verify` 的检查清单

| 检查 | 失败的 `reason`（仅日志） |
|---|---|
| 取公钥（`https://<team>/cdn-cgi/access/certs`）失败 | `access keys unavailable`（失败即关闭，不会放行） |
| 签名无效、算法不是 RS256（拒绝 `none`、HS256）、kid 未知、乱码 | `access assertion <异常类名>` |
| 缺少 `exp`、`iat`、`iss`、`aud` 任一项 | `access assertion MissingRequiredClaimError` |
| `iss` 不等于 `https://<team_domain>` | `access assertion InvalidIssuerError` |
| `aud` 不等于应用的 AUD 标签（另一个应用的令牌无法使用） | `access assertion InvalidAudienceError` |
| 已过期（时钟容差 10 秒） | `access assertion ExpiredSignatureError` |
| 没有 `email`（例如 Cloudflare 服务令牌） | `access identity missing` |
| 邮箱（转小写）不在 `users` | `access identity not allowed` |

只记录异常类名，因为异常消息可能引用令牌内容。

公钥缓存：首次使用时取，缓存 1 小时（`KEY_LIFESPAN`），遇到缓存里没有的 kid 会刷新；取公钥超时 5 秒（`FETCH_TIMEOUT`）。

## 6. 配置（`services.yaml` 的 `mcphost`）

```yaml
mcphost:
  public_hosts:
    - www.fortressfront.app           # 隧道转发的 Host，其他 Host 返回 421
  access:
    team_domain: <team>.cloudflareaccess.com   # 必须匹配 *.cloudflareaccess.com
    audience: <AUD 标签>                       # Access 应用的 AUD，至少 16 字符
    users:
      - email: you@example.com                 # 不区分大小写，不能重复
        name: xingxing                         # 日志与 node 上的调用者名
```

- `name` 与令牌名同格式（`^[a-z0-9][a-z0-9-]{0,31}$`）。
- 团队域名与 AUD 是公开标识，不是凭证。
- `access` 只在启动时读取，修改后需要重启 mcphost（不像令牌那样热加载）。
- 未配置 `access` 时，断言头被忽略，只走 Bearer。

## 7. 与 Bearer 的关系

| | Access 断言 | Bearer 令牌 |
|---|---|---|
| 谁用 | ChatGPT（经 Cloudflare） | Codex、VS Code（本机直连） |
| 优先级 | 请求带断言头时唯一生效 | 无断言头时使用 |
| 身份来源 | 邮箱 → `users[].name` | 令牌名 |
| 能否使用 `X-Fortress-Caller` | 不能（`delegation denied`） | 仅 `delegate: true` 的令牌 |
| 是否热加载 | 否 | 是 |

## 8. 使用与验证

添加连接器：ChatGPT 中添加自定义 MCP 连接器，URL 为 `https://www.fortressfront.app/mcp`，认证选 OAuth，用白名单邮箱登录。

确认 Cloudflare 侧：

```bash
curl -i https://www.fortressfront.app/mcp
# 期望 401，响应头带 OAuth 发现信息（说明 Access 在 mcphost 之前）
curl -i https://www.fortressfront.app/.well-known/cloudflare-access-protected-resource/mcp
# 期望 200，protected: true，authorization_servers 指向团队域名
curl -i https://<team>.cloudflareaccess.com/.well-known/oauth-authorization-server
# 期望 200，含授权、令牌、注册端点，支持 authorization_code、refresh_token、S256
```

确认 mcphost 侧：重启 mcphost 后在 ChatGPT 里列数据集、看 schema，日志中应有 `tool start` 与 `tool ok`，调用者名是配置里的名字；被拒绝时出现 `auth rejected` 与原因。

## 9. 生命周期与撤销

- 访问令牌与刷新令牌由 Cloudflare 管理，有效期与会话策略在 Access 控制台里设置，fortress 不存储。
- 撤销一个人：删 Access 策略里的邮箱（Cloudflare 层），并删 `mcphost.access.users` 里的条目后重启（mcphost 层）。两层任何一层拒绝都不通过。
- 换应用或重建 Access 应用：AUD 会变，必须同步 `audience` 并重启，否则全部被 `InvalidAudienceError` 拒绝。
- 本机无法访问团队域名时取不到公钥，公网路径不可用（失败即关闭），本机 Bearer 路径不受影响。

## 10. 尚未完成与风险

| 项目 | 状态 |
|---|---|
| 重启后的 ChatGPT 工具发现的端到端验证 | 未做 |
| Cloudflare WAF：路径限制、限速、OpenAI 出口 IP 白名单 | 未配置 |
| 认证失败的自动封禁与告警 | 只有日志 |
| 数据集白名单、云端凭证只读 | 未做：任何通过认证的人能读节点上所有数据集 |
| `www` 作为 MCP 入口 | 建议改为 `mcp.` 子域名，同步改隧道、Access 应用、`public_hosts`、`audience` |
| 隧道 token 曾以明文出现在 `docs/wall/HOW_TO_SETUP_TUNNEL.md` | 需要轮换，并检查 git 历史 |
