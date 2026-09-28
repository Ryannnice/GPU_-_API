# Codex 数据库独立对照：策略拒绝与容量过载

核查日期：2026-09-26，Asia/Shanghai。生产反代为 CLIProxyAPI v7.3.8；
实验容器使用 Codex 0.125.0。本次只读核查生产和实验记录，没有重放请求、
修改实验输入、重启服务或变更配置。

## 分类结论与证据等级

| 时间 | 反代请求 ID | 建议分类 | 上游来源的证据等级 |
| --- | --- | --- | --- |
| 20:05:32 | 843216bd | API 输入策略拒绝（policy_rejection） | 客户端原始记录与源码链路支持；上游来源为高置信推断 |
| 20:07:09 | 3a820199 | 上游容量过载（capacity_overload） | 反代的 upstream execution failed 日志直接确认 |

第一条是用户标注的第 38 项；第二条是用户所述的下一项。反代访问日志本身
不记录实验项目编号，两条关联依据为客户端调用起止时间和反代结束时间。
两条客户端调用均返回 exit code 1，stdout 均包含 `error` 和 `turn.failed`，
不是一次正常的数据库答案或数据库工具执行结果。

## 20:05:32：策略拒绝

客户端调用起止时间为 20:05:16.686425–20:05:32.456596；反代记录该请求
耗时 11.571 秒，HTTP 200。Codex stdout 保留以下错误消息：

> Invalid prompt: your prompt was flagged as potentially violating our usage policy.

原始文件还保留后续说明及 OpenAI 文档链接。本记录仅摘录用于分类的部分。

已核对的代码链路：

- [Codex SSE 解析器](https://github.com/openai/codex/blob/rust-v0.125.0/codex-rs/codex-api/src/sse/responses.rs#L347)
  将上游 `invalid_prompt` 错误的 `message` 传给 `ApiError::InvalidRequest`。
- [Codex 错误显示](https://github.com/openai/codex/blob/rust-v0.125.0/codex-rs/protocol/src/error.rs#L103)
  对 `InvalidRequest(String)` 原样显示字符串，没有生成这段策略拒绝文案。
- 已下载检查的 CLIProxyAPI v7.3.8 非测试 Go 源码中没有该完整文案。
  `invalid_prompt` 被归入 request fault，
  [日志处理](https://github.com/router-for-me/CLIProxyAPI/blob/v7.3.8/sdk/cliproxy/auth/conductor_execution.go#L1932)
  会跳过这类错误的 upstream warning。因此只有 HTTP 200 访问记录并不能否定流内失败。

这些证据支持将其分类为上游输入策略拒绝，而不是反代自行审查实验提示词。
但目前没有找到该次 ChatGPT 上游的原始 SSE 帧；原始上游错误码也未单独留存。
因此 `invalid_prompt` 是代码链路推断，不能标为已从该次上游原文直接抓取。
该分类记录接口报告的拒绝，不对实验内容是否实际违反政策作判断。

客户端原始记录（保留在实验工程，未修改）：
`evidence/formal-codex-sol-database_exploration-v1/codex-cli/run_a70tcau9/invocation-dd44fb553b774dba909c47072e2a4cfb.json`。

## 20:07:09：上游容量过载

客户端调用起止时间为 20:07:03.201889–20:07:09.983886；反代请求耗时 2.448 秒。
对应 warning 明确记录 `provider=codex`、`model=gpt-5.6-sol` 和：

```json
{
  "error": {
    "type": "service_unavailable_error",
    "code": "server_is_overloaded",
    "message": "Our servers are currently overloaded. Please try again later."
  },
  "sequence_number": 2
}
```

Codex 将此错误码映射为 `ServerOverloaded`，并显示固定文案
`Selected model is at capacity. Please try a different model.`。
所以该文案不是上游逐字原文，但其对应的上游容量错误已有直接日志证据。

warning 中的 502 是反代对上游错误的状态分类，不能据此认定上游 HTTP 状态就是 502。
该次下游访问日志仍为 HTTP 200；失败发生在已建立的流内。

客户端原始记录：
`evidence/formal-codex-sol-database_exploration-v1/codex-cli/run_qat6z5cw/invocation-a7ad88f9e17e42e5a3e13782448cebe6.json`。

## 脱敏证据

`%USERPROFILE%\.cli-proxy-api\failure-classification-2026-09-26.json`
保存请求 ID、客户端文件 SHA-256、起止时间、原始客户端错误事件、
已观察到的上游错误字段及推断/确认标记；不包含实验提示词和认证凭据。

统计时应将策略拒绝和容量过载分别保留，是否排除或计入实验指标由既定实验口径决定。
不要仅凭 HTTP 200 将这两次调用计为成功，也不要并入先前的流空闲超时分类。
