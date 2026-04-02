# GPT Researcher 接入说明

## 接入方式

采用 **direct Python import + 008 环境桥接**。

- 默认源码路径：`/tmp/008-discovery/gpt-researcher`
- adapter：`/Users/lucas/repos/review/008-review-control-plane/apps/api/src/adapters/gpt_researcher_adapter.py`

## 为什么不用单独常驻 HTTP 服务

- 本机已存在源码，direct import 更直接
- 008 只需要能力接入，不需要再维护第二套独立 server 生命周期
- 更容易把 008 的 fixture/doc loader 注入到 GPT Researcher

## 关键适配

1. 从 `century.json` 解析 LLM 与 embedding
2. 把配置注入为 GPT Researcher 期望的环境变量
3. 将本地文档研究改为 **008 自己提取文本，再交给 GPT Researcher 的 report writer**
4. 对成本估算做安全降级，避免 tiktoken 外网下载失败导致主流程中断
5. 对 `ddgs` 依赖做 duckduckgo_search shim，降低本机安装门槛
6. 当 `sourceUrls` 已给定且 `useWeb=false` 时，008 先抓取这些来源正文，再走 **static_source_urls** 模式生成深度研究报告，减少对外部搜索引擎的依赖

## 统一方法

- `health_check()`
- `run_deep_research(...)`
- `run_local_docs_research(...)`

## 本地文档输入方式

008 先用自己的 `DocumentLoader` 读出文本，再把聚合上下文作为 ext_context 交给 GPT Researcher 的 report writer/prompt stack。

## sourceUrls 输入方式

若任务直接给出外部来源 URL：

1. 008 先抓取 URL 正文
2. 归一化为 source context
3. 再调用 GPT Researcher report writer 生成 grounded report

这样可以把 `deep_research` 的成功率从“依赖搜索结果”提升为“依赖给定来源是否可读”。

## 联通验证

- import health 已通过
- 真实文档研究工件：`artifacts/verification/gpt-researcher-connectivity.json`
- source-grounded 深度研究工件：`artifacts/verification/gpt-researcher-deep-research.json`
- 成功 API 任务：`0a76e1d975e2453c8fa263c6aa280412`

## 已知限制

- GPT Researcher 首次运行延迟较高
- `useWeb=true` 时，上游 web retriever 仍依赖外部搜索与抓取稳定性
- 长报告生成对外部 LLM 与网络稳定性更敏感
