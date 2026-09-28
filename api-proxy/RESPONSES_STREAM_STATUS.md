# Responses 流停滞排查：2026-09-26

截至本次检查，尚无在本机验证能解决此次长任务停滞的反代修复。
生产实例仍为 CLIProxyAPI v7.3.8，端口 8317；本次没有重启、升级或修改其配置，
也没有修改实验工程或停止容器。

## 已核对的请求

| 用户报告的开始时间 | 反代记录的结束时间 | 耗时 | 请求 ID | HTTP 状态 |
| --- | --- | --- | --- | --- |
| 18:20:40 | 18:30:39 | 9 分 59 秒 | e6ad6143 | 200 |
| 18:30:41 | 18:45:43 | 15 分 2 秒 | 4f1afd15 | 200 |

时间为 2026-09-26，Asia/Shanghai。开始时间由反代结束时间减去耗时得到，
与用户报告一致。HTTP 200 只能说明流的响应头已发送，不能证明收到终止事件。
这两个请求在当前反代日志中只有访问记录，没有原始 SSE 事件序列，无法据此区分
上游未发送终止事件、传输停滞或客户端消费问题。

此前的健康检查使用短的非流式请求，不能覆盖此类长时间流停滞。

## 当前版本与已发布修复

检查时官方最新版本为 [v7.3.18](https://github.com/router-for-me/CLIProxyAPI/releases/tag/v7.3.18)。
已下载并比对 v7.3.8 与 v7.3.18 的 Codex HTTP 执行器、Responses handler 和配置样例。

- v7.3.8 已处理 `response.completed`、`response.incomplete` 和 `response.done`，
  并在正常终止事件后退出读取循环。不能仅凭缺少完成事件就断言缺少旧的终止兼容补丁。
  参见 [v7.3.8 Codex 流实现](https://github.com/router-for-me/CLIProxyAPI/blob/v7.3.8/internal/runtime/executor/codex_executor_stream.go#L403)。
- v7.3.11 包含 [Responses 私有及遥测事件过滤修复](https://github.com/router-for-me/CLIProxyAPI/commit/dd013f9e2993ccb840ce9da74308dfe30ecce15c)。
  它改善下游事件兼容性，但没有证据证明此次停滞由这些事件引起。
- v7.3.17 包含 [Codex routing hint 修复](https://github.com/router-for-me/CLIProxyAPI/pull/6090)。
  作者明确没有声称该请求头改善延迟；不能据此承诺解决卡流。
- v7.3.18 的相应 HTTP 流读取循环仍使用阻塞的 `scanner.Scan()`，这次版本差异
  没有引入独立的流空闲读取计时器。升级尚不能作为本问题已经解决的证据。

配置边界也需区分：`streaming.keepalive-seconds` 发送心跳；
`streaming.bootstrap-retries` 用于首字节发送之前的重试；
`codex.stream-bootstrap-timeout` 限制初始缓冲阶段，并只在新帧到达时检查时间，
不会中止上游连接。它们均不能直接保证收到 reasoning 后停滞的流最终结束。
参见 [配置样例](https://github.com/router-for-me/CLIProxyAPI/blob/v7.3.18/config.example.yaml#L330)。

## 本次流式验证

19:39 使用现有生产端口执行三次独立的合成短请求，没有执行返回的工具调用：

| Sol 测试 | 终止标志 | 收到 EOF | 耗时 |
| --- | --- | --- | --- |
| Responses 短文本 | response.completed | 是 | 2.086 秒 |
| Responses 函数调用 | response.completed | 是 | 2.834 秒 |
| Chat Completions 短文本 | [DONE] | 是 | 1.661 秒 |

这证明当时短流能完整结束，不代表已复现或修复长实验任务。
脱敏的逐事件类型与时间戳保存在
`%USERPROFILE%\.cli-proxy-api\stream-check-2026-09-26-193924.json`。

## 实验侧超时边界及后续处理

只读检查发现实验扩展已配置
`model_providers.clbench_proxy.stream_idle_timeout_ms=90000`，即 90 秒流空闲超时；
原有重试次数及外层 300 秒调用截止时间保留。
该 provider 设置与 [OpenAI Docs 的配置项](https://learn.chatgpt.com/docs/config-file/config-advanced#azure-provider-and-per-provider-tuning) 一致。
配置文件存在不等于所有已启动的进程都采用了新值。

日志栈中的 300 秒错误来自外层 `subprocess.run(..., timeout=...)` 执行
`docker exec`，不应与 Codex 的 SSE 空闲超时混为一谈。现有执行函数中没有
显式终止容器内该次 Codex 进程的处理；需要验证外层超时后的取消是否传递到了
容器及上游。反代耗时超过 300 秒说明这个边界值得检查，但不是孤儿进程的证明。
本次容器进程快照未发现运行超过 300 秒的 Codex 进程。

建议继续观察已加的 90 秒空闲重连，并核验实际生效值、总重试预算和取消传播。
如做反代升级对照，应在独立端口使用同一失败输入，并只记录 SSE 事件类型、时间戳、
终止事件与取消时间；通过此类对照之后才能判定升级是否解决正式任务。
不要为让客户端结束而合成 `response.completed`，这会把不完整响应或工具参数误记为成功。
