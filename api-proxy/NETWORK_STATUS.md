# Windows 反代网络修复记录

## 当前配置：2026-09-22 15:27 已恢复直连

用户已停用 Clash。检查确认 `7890` 无监听、Mihomo 核心及 TUN 未运行，
但 CLIProxyAPI 仍残留此前的 `proxy-url: "http://127.0.0.1:7890"`。
15:25:58 已移除这一配置；15:25:59 反代热加载成功。
进程的上游 TCP 连接已确认直达 `104.18.32.47:443`。

Sol、Luna、Astra 分别通过一次 Chat Completions 和一次 Responses 实测，
共六次均返回 HTTP 200、`OK`，且返回模型名称与请求一致，耗时 2.069–6.652 秒。
这些结果证明检查时直连可用，后续稳定性仍取决于实际网络和上游服务。

当前使用 `http://127.0.0.1:8317/v1`；反代及其守护任务均不再要求 Clash 运行。
后面的 Clash 配置说明仅为历史记录，当前配置以本节为准。
脱敏证据：`%USERPROFILE%\.cli-proxy-api\direct-network-check-2026-09-22.json`。

## 2026-09-21 21:45 Astra 认证复查

`gpt-6-astra` 当前可用。21:43 初次调用已成功，随后三轮共六次测试
（Chat Completions、Responses 各三次）全部返回 HTTP 200 和 `OK`，
耗时 2.880–4.516 秒，返回模型均为 `gpt-6-astra`。
现有认证启用且尚未过期；本次复查直接使用现有认证，没有重置认证或重新登录。

日志中 20:58:24 的 Astra 上游请求返回 HTML 403。所安装版本的
[普通 403 处理逻辑](https://github.com/router-for-me/CLIProxyAPI/blob/v7.3.8/sdk/cliproxy/auth/conductor_cooldown.go#L854)
会设置约 30 分钟的模型冷却；`auth_unavailable` 可以附带缓存的上游错误。
此前现象与该机制吻合，首次复查时已经恢复可用。

这不代表所有上游错误都已消失：21:43:48 的 Sol 请求另有 `server_is_overloaded`
502，随后一次 503 引用了该过载错误。应区分模型冷却、上游过载和登录失效。
完整实验恢复仍需继续验证。

当时用户确认使用 Clash，保留了 `http://127.0.0.1:7890` 出站配置；该配置已于
2026-09-22 移除，见上方当前配置。
详细脱敏证据：`%USERPROFILE%\.cli-proxy-api\astra-auth-check-2026-09-21.json`。

## 2026-09-21 20:49 出站配置调整及当时验证

检查时间：2026-09-21 20:51:53，Asia/Shanghai。

2026-09-21 20:49:18，已在本机 `%USERPROFILE%\.cli-proxy-api\config.yaml`
增加以下配置，并确认 CLIProxyAPI 热加载成功：

```yaml
proxy-url: "http://127.0.0.1:7890"
```

本机 Clash 已开启；修改前 Sol、Luna 的短请求也已恢复成功。此次修改将反代的
出站连接显式交给 Clash 的 HTTP 代理端口。已从 CLIProxyAPI 进程的 TCP 连接
确认它连接到了 `127.0.0.1:7890`，减少对系统 TUN 和本地 DNS 状态的依赖。

实验继续使用 `http://127.0.0.1:8317/v1`，模型名称为 `gpt-5.6-sol`、
`gpt-5.6-luna`。本次验证使用现有账号和模型，尚无已验证可用的独立备用 API。

每个模型分别执行三次 Chat Completions、三次 Responses，均要求返回 `OK`：

| 模型 | 成功次数 | 耗时范围 |
| --- | --- | --- |
| gpt-5.6-sol | 6 / 6 | 4.583–9.624 秒 |
| gpt-5.6-luna | 6 / 6 | 2.236–3.339 秒 |

修改后至上述检查时间，服务日志记录 19 次请求完成，全部 HTTP 200；
没有新增 `upstream execution failed` 或 `TLS handshake` 错误。
这些结果覆盖短请求和约 2 分 35 秒的观察窗口，完整扑克任务恢复及长时间稳定性
仍需由实验运行验证。

当时这条线路需要 Clash/Mihomo 持续运行并提供 `7890` 端口。检查时 Clash 的登录
自启关闭；Windows 重启后需要先启动 Clash。现有 `CLIProxyAPI-Watchdog`
只负责反代进程和本地 API 的存活，`/v1/models` 成功本身不能证明上游可用。

脱敏证据保存在 `%USERPROFILE%\.cli-proxy-api\network-repair-2026-09-21.json`，
包含逐次模型测试、配置热加载、出站连接和日志汇总。
修改前配置备份为同目录的 `config.before-explicit-proxy-20260921T204918.yaml.bak`；
该备份含本地 API 凭据，应留在本机。
