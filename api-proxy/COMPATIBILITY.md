# CLBench / Mem0 接口排查记录

验证日期：2026-09-19。本机运行 CLIProxyAPI **v7.3.8**，地址为
`http://127.0.0.1:8317/v1`。此次排查没有改动正在运行的反代、Windows
自启动任务或实验工程的源代码、配置。

用户已选择：暂用 CPU BGE，明确标注嵌入设置变更。实验工程已迁移至
`C:\Desktop\Research_Agentic\CLBench_Reproduction`。

## 实测结果

| 检查 | 结果 | 实验端含义 |
| --- | --- | --- |
| `/chat/completions` | HTTP 200 | 可继续使用现有对话模型 |
| `/responses` 请求 `store: true` | HTTP 200，但返回 `store: false` | 不具备所请求的服务端保存行为 |
| 下一轮只传 `previous_response_id` | HTTP 200，回答 `UNKNOWN` | 不能依赖该 ID 延续上下文 |
| 下一轮显式传原输入、完整 `output`、新输入 | 正确返回随机测试码 | 显式回传历史的路径通过了两轮记忆对照 |
| `GET /responses/{id}` | HTTP 404 | 无法通过此接口取回历史响应 |
| 本机 `/embeddings` | HTTP 404 | 当前反代没有实现这个路由 |
| 直连官方 `text-embedding-3-small`，1536 维 | HTTP 429，`insufficient_quota` / `credit_balance_exhausted` | 本次测试使用的环境凭证没有可用额度，尚未取得原模型向量 |
| Mem0 原提取配置 + BGE | LiteLLM 拒绝采样参数，最终得到 0 条记忆 | 需要先合入下面的采样参数补丁 |
| Mem0 修复配置 + BGE | 1 次真实提取模型调用，生成 2 条记忆并检索回 2 条 | 最小提取、存储与检索链路通过 |

这些是接口与适配器检查，不是正式基准实验结果。

## Mem0 开跑前需要的修复

隔离冒烟测试发现，Mem0 默认的 `top_p=0.1` 被当前 LiteLLM 的
`openai/gpt-5.6-sol` 适配路径拒绝；去掉它之后，`temperature=0.0` 也被拒绝。
Mem0 捕获提取错误后返回空结果，所以仅看 `Memory.add()` 没有抛异常，
不足以认定记忆提取成功。

[采样参数补丁](patches/clbench-mem0-sampling.patch) 仅对提取模型
`gpt-5.6-sol` / `openai/gpt-5.6-sol` 将 `temperature` 和 `top_p` 设为 `None`，
其它模型沿用原配置。它保持 Mem0 的记忆提取、更新和检索实现。
该补丁已经通过应用检查，但尚未改写实验工程，由实验负责人统一合并。

```powershell
git -C C:/Desktop/Research_Agentic/CLBench_Reproduction/upstream apply --check C:/Desktop/GPU_-_API/api-proxy/patches/clbench-mem0-sampling.patch
git -C C:/Desktop/Research_Agentic/CLBench_Reproduction/upstream apply C:/Desktop/GPU_-_API/api-proxy/patches/clbench-mem0-sampling.patch
```

真实 Mem0 验证使用独立临时 Qdrant 和 SQLite 存储、虚构用户信息，以及实验
工程现有的 `support/sitecustomize.py` 模型注册与脱敏记录逻辑。原配置失败；
修复配置在 8.5 秒内提取 2 条记忆，搜索正确返回了每月预测、CSV 格式偏好。
结果保存在 `C:\Users\renyv\.cli-proxy-api\mem0-flow-probe-patched.json`，
其中记录了证据目录与所用 support 文件的 SHA-256。

该烟测没有覆盖完整任务或所有记忆更新分支。当前环境未安装 spaCy NLP
组件，Mem0 发出了对应加载失败提示；本次检索检查仍然通过。正式实验应
记录这个依赖状态，并单独运行自己的任务预检。

## 原因与 ICL 接入

这不是 Windows 或 CPU 的限制。该版本的
[非流式执行器](https://github.com/router-for-me/CLIProxyAPI/blob/v7.3.8/internal/runtime/executor/codex_executor_execute.go#L60)
和
[流式执行器](https://github.com/router-for-me/CLIProxyAPI/blob/v7.3.8/internal/runtime/executor/codex_executor_stream.go#L63)
都主动移除 `previous_response_id`；
[请求转换器](https://github.com/router-for-me/CLIProxyAPI/blob/v7.3.8/internal/translator/codex/openai/responses/codex_openai-responses_request.go#L22)
强制 `store: false`。
[路由表](https://github.com/router-for-me/CLIProxyAPI/blob/v7.3.8/internal/api/server_routes.go)
没有 `/v1/embeddings`。

ICL 当前使用 `provider_mode: "litellm_chat"`，显式维护完整可见历史，可以
继续做该路径的预检；这与原生 Responses 的隐藏推理状态路径应分别记录。
如果使用 Responses 的无状态模式，应按
[OpenAI 的上下文管理说明](https://developers.openai.com/api/docs/guides/conversation-state)
显式回传需要保留的输入和完整输出项，包括工具调用、工具结果及返回的
推理项。保留输出中的 `phase` 等字段，每轮重新提供当前 `instructions`，
并按实验原定规则执行上下文预算和 run / instance 隔离。

### 另一个已定位的实验端问题

在检查时的 `src/systems/utils/provider_adapters.py` 中，
`_capture_openai_response()` 在无状态模式下也会保存 response ID，而
`_openai_input_messages()` 仅据 ID 是否存在决定是否只发送新增消息。
因此，仅把 `openai_store` 改成 `false` 仍会丢掉前轮可见历史。

[独立补丁](patches/clbench-stateless-history.patch) 把判断改为同时要求
`self.openai_store` 为真，才使用增量消息。补丁没有应用到实验工程，便于
实验负责人在迁移后的目录统一合并。当前 `litellm_chat` 分支不经过这段代码。

这个补丁只解决无状态模式的可见历史截断问题，不代表已经实现完整原生
服务端状态或验证了全部工具调用链。

在迁移后的 `upstream` 目录可先检查、再应用：

```powershell
git apply --check C:/Desktop/GPU_-_API/api-proxy/patches/clbench-stateless-history.patch
git apply C:/Desktop/GPU_-_API/api-proxy/patches/clbench-stateless-history.patch
```

## 已选择的 CPU BGE 路线

已使用实验工程安装的 **Mem0 自带 FastEmbedEmbedding** 做真实推理，并在
独立的内存 Qdrant 集合验证检索。检查通过：384 维、所有数值有限、仅使用
`CPUExecutionProvider`、同一文本的重复结果稳定、相关记忆排在无关文本之前。

本次模型与依赖指纹：

- 配置模型：`BAAI/bge-small-en-v1.5`，384 维。
- FastEmbed 对应制品：`qdrant/bge-small-en-v1.5-onnx-q`，量化 ONNX。
- 制品 revision：`52398278842ec682c6f32300af41344b1c0b0bb2`。
- `model_optimized.onnx` SHA-256：`51f1bd0addd6e859e42c2c8021a5e5461385bb676a649f4b269aa445449f2431`。
- `mem0ai=2.0.0`、`fastembed=0.7.4`、`onnxruntime=1.30.0`、`qdrant-client=1.17.1`。
- 已下载缓存：`C:\Users\renyv\.cli-proxy-api\embedding-cache`。

可以复用这个已校验的缓存。实验负责人需让 `run_job.py` 中的
`FASTEMBED_CACHE_PATH` 指向该目录；检查时该脚本会覆盖同名环境变量，
因此仅在外层 shell 设置变量不足以改变它。

[BGE 模型卡](https://huggingface.co/BAAI/bge-small-en-v1.5) 与本机 FastEmbed
模型定义表明这是英语嵌入模型，输入预算为 512 tokens。应记录实际长文本
截断行为；它与原 OpenAI 嵌入模型的输入处理和向量空间均不等价。

供实验设置说明使用：

> Mem0 保留 SDK 的记忆提取、更新与检索流程。由于当前反代不提供 embeddings
> 路由，且本次官方上游凭证请求返回额度不足，嵌入后端暂替换为
> BAAI/bge-small-en-v1.5 的 FastEmbed 量化 ONNX CPU 实现，输出 384 维。
> 原设置为 text-embedding-3-small、1536 维。此结果属于修改了嵌入设置的复现，
> 不作为原嵌入设置的严格复现结果。

## 将来恢复 Mem0 原嵌入设置

需要一个实际能够调用 `text-embedding-3-small` 的上游及可用额度。
当前 ChatGPT/Codex 登录接入的本机路由并不提供这个模型的 embeddings 接口。
修复额度后，可以让 Mem0 的嵌入请求单独直连官方 API，任务回答和记忆提取
继续走现有本机反代，无需更换这两部分的模型。

检查时的 `run_job.py` 会把 `OPENAI_API_KEY` 和 OpenAI base URL 覆盖成本机
反代的值。因此，嵌入必须使用单独的凭证变量，并在 Mem0 配置中显式覆盖
base URL；只把模型名改回去仍然会打到本机 404 路由。

建议实验负责人在 `_create_mem0()` 的配置构造处使用以下嵌入配置，并给
实验子进程传入 `MEM0_EMBEDDING_API_KEY`。不要把密钥字面值写入实验 JSON。

```python
"embedder": {
    "provider": "openai",
    "config": {
        "model": "text-embedding-3-small",
        "embedding_dims": 1536,
        "openai_base_url": "https://api.openai.com/v1",
        "api_key": os.environ["MEM0_EMBEDDING_API_KEY"],
    },
},
```

同时将实验参数恢复为 `embedding_provider="openai"`、
`embedding_model="text-embedding-3-small"`、`embedding_dims=1536`，让 Qdrant
的 `embedding_model_dims` 也为 1536，并在正式实验前创建新的向量存储。
切换时不可继续使用 BGE 生成的旧向量。

这条线路成功之前，`BAAI/bge-small-en-v1.5` / FastEmbed / ONNX CPU / 384 维
只能作为明确标注的替代设置；它不构成原嵌入模型的严格复现。

## 可重复检查

在本仓库根目录检查本机反代：

```powershell
python api-proxy/probe_capabilities.py --report "$env:USERPROFILE/.cli-proxy-api/capability-probe.json"
```

检查官方嵌入上游。默认从当前进程的 `OPENAI_API_KEY` 读取凭证；也可以
指定单独的环境变量或本机密钥文件。只有 HTTP 200、模型名正确、返回一个
1536 维有限数值向量时才返回退出码 0。

```powershell
python api-proxy/check_embeddings.py --key-env MEM0_EMBEDDING_API_KEY --report "$env:USERPROFILE/.cli-proxy-api/official-embedding-probe.json"
```

重跑隔离的真实 Mem0 提取与检索烟测（默认使用已修复的采样配置；加
`--unpatched-sampling` 可对照原问题）：

```powershell
& 'C:/Desktop/Research_Agentic/CLBench_Reproduction/upstream/.venv/Scripts/python.exe' C:/Desktop/GPU_-_API/api-proxy/check_mem0_flow.py --support-dir C:/Desktop/Research_Agentic/CLBench_Reproduction/support
```

在实验的虚拟环境重跑 CPU 嵌入与检索检查：

```powershell
& 'C:/Desktop/Research_Agentic/CLBench_Reproduction/upstream/.venv/Scripts/python.exe' C:/Desktop/GPU_-_API/api-proxy/check_bge_cpu.py --report "$env:USERPROFILE/.cli-proxy-api/bge-cpu-probe.json"
```

使用实验工程的虚拟环境，在内存中验证历史补丁（不会改写工程）：

```powershell
& '<迁移后的 upstream>/.venv/Scripts/python.exe' C:/Desktop/GPU_-_API/api-proxy/verify_clbench_history.py --upstream '<迁移后的 upstream>'
```

已验证的范围包括：原问题可复现、补丁保留完整可见历史、无状态请求不发送
`previous_response_id`、当前 instructions 会重发、有状态增量行为保持、
reset 清除前一 run 的状态。正式实验前仍应运行实验工程自己的回归检查。

另外，请单独记录请求参数兼容性：上述 Codex 请求转换器会删除
`temperature`、`top_p`、`max_output_tokens` 和 `max_completion_tokens`。
这些参数不能仅凭客户端已设置就认定上游实际执行了它们。ICL 配置里的
`max_tokens` 是本地上下文截断预算，应与这些输出限制参数区分。
