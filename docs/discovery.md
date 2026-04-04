# 资产勘查与接入方式确认

勘查时间：2026-04-02

## 1. 007 项目技术栈、目录结构与可复用点

勘查目录：历史 `007-deepresearch` 本地仓库

### 1.1 事实

- 007 不是一个干净的前后端 monorepo，而是 **Python 主导** 的混合项目：
  - `agent/`：Autogenesis / DeepResearchAgent 风格的 Python 运行时源码与依赖
  - `run_review.py`、`review_config.py`：审查器主执行脚本与配置
  - `webapp/`：轻量 Web 层（配套 `requirements-web.txt`，偏 Flask）
  - `fixtures/`：施组与监理规划样本
  - `policy_packs/`、`tests/`、`results/`
- `agent/requirements.txt` 显示其为 **Python + LangChain + LangGraph + 多检索器** 的重型 agent runtime。

### 1.2 可复用点

- fixture 目录组织方式
- 已整理的施组 / 监理规划样本
- 007 中关于审查场景的资料域划分经验
- DeepResearchAgent 风格的 planner / runtime 思路

### 1.3 放弃点

- 不继续在 007 上重度改造
- 不把 007 的审查器主脚本直接搬到 008 里作为主流程
- 不把 007 的 Python agent runtime 整仓嵌入 008

## 2. DeepResearchAgent 本地接入形态

### 2.1 勘查结果

- 007 内存在 `agent/` 源码树，可视为 DeepResearchAgent / Autogenesis 风格本地实现
- 未发现一个可直接复用、稳定暴露给 008 的本地 HTTP 服务
- 可行方式：
  1. 直接源码 import（耦合过重）
  2. 独立服务调用（本机现成服务不足）
  3. 子进程 CLI（维护成本偏高）
  4. **在 008 内构建兼容其角色定位的 orchestrator/control plane**

### 2.2 最终采用

采用 **008 内部兼容实现**：

- `apps/api/src/orchestrator/planner.py`
- `apps/api/src/orchestrator/router.py`
- `apps/api/src/orchestrator/deepresearch_runtime.py`

原因：

- 能保证 008 的定位仍是 control plane / orchestration layer
- 避免 007 审查器业务逻辑反向污染 008
- 便于后续增加更多能力路由策略与任务状态机

## 3. DeepTutor 本地接入形态

### 3.1 勘查结果

勘查副本：`/tmp/008-discovery/DeepTutor`

发现：

- 官方路由存在真实接口：
  - `GET /api/v1/system/status`
  - `WebSocket /api/v1/chat`
- 但完整官方应用依赖较重，涉及 RAG / docling / llama-index 等更大栈

### 3.2 方案比较

- 直接跑全量官方服务：最完整，但本机接入重、启动成本高
- 仅复用源码中的 ChatAgent：可保留真实聊天能力，减少未用依赖

### 3.3 最终采用

采用 **轻量 bridge**：

- 文件：`scripts/run_deeptutor_bridge.py`
- 复用 DeepTutor 的真实 `ChatAgent + SessionManager`
- 对未用重模块做 monkeypatch
- 对 008 暴露与官方一致的 health/chat 接口

原因：

- 保留“真实 DeepTutor 能力服务”属性
- 又能满足 008 的快速联通与验证要求

## 4. GPT Researcher 本地接入形态

### 4.1 勘查结果

勘查副本：`/tmp/008-discovery/gpt-researcher`

发现：

- 存在 FastAPI server 入口，但仍需要完整依赖栈
- 直接 Python package import 可行：`gpt_researcher.GPTResearcher`
- 支持 `deep` 与本地文档研究
- 其默认 Local / embedding 流程在本机兼容性不稳定，因此更稳妥的接法是：**008 自己提取文档文本，再交给 GPT Researcher 的 report writer/prompt stack**

### 4.2 最终采用

采用 **direct Python import + 008 侧环境桥接**：

- adapter：`apps/api/src/adapters/gpt_researcher_adapter.py`
- LLM / embedding 配置由 008 解析 century.json 后写入其运行环境
- 本地文档研究改用 **008 DocumentLoader 提取文本 + GPT Researcher report writer**，避免强依赖其 DOC_PATH / embedding 压缩链路

原因：

- 真实调用 GPT Researcher 本体
- 不需要再单独维护一个常驻服务
- 更利于把 008 的 fixture 与 doc loader 接到其研究链路上

## 5. century.json 与 gbcs-fast.json 结构勘查

### 5.1 LLM 配置

路径：部署侧提供的 `century.json` / 等价 LLM 配置文件

实际可用 profile：

- `dashscope`
- `dashscope_embedding`
- `sealos_aiproxy`

已使用字段：

- `base_url`
- `api_key`
- `models.chat[]`
- `provider`

008 解析策略：

- 环境变量覆盖优先
- 文件回退次之
- 默认 chat profile = `dashscope`
- 默认 embedding profile = `dashscope_embedding`

### 5.2 FastGPT 配置

路径：部署侧提供的 `gbcs-fast.json` / 等价 FastGPT 配置文件

已使用字段：

- `gbcs-fast.base_url`
- `gbcs-fast.api_key`
- `headers.Authorization`（用于 search key 回退推断）

注意：

- 该 `base_url` 已经是 `.../api`
- Mode A 实际应拼接为 `.../api/core/dataset/searchTest`
- 不应再次额外 append `/api`

## 6. FastGPT dataset / collection 标识来源

### 6.1 datasetId

当前 008 默认 dataset registry 来源于本机已有实现经验（沿用 006 的 registry）：

- `gb_national = 69842ce095a6ce02e8055b98`
- `building_municipal = 6984435295a6ce02e80696a1`
- `petrochemical = 698444f395a6ce02e806baeb`
- `laws_regulations = 69ac6551c5c0bdd8e039b120`

### 6.2 collectionId

- 未在固定配置中硬编码
- 通过任务请求体高级项或环境变量注入
- 因此 Mode B 作为 **策略可选能力**，不是默认必经路径

## 7. fixture 复制策略

已从 007 复制最小可验证样本到：

- `fixtures/construction`
- `fixtures/supervision`

当前 manifest：`fixtures/manifest.json`

已覆盖：

- 11 份施组法规/标准 markdown
- 1 份施工组织设计 docx
- 3 份监理规划/规范 docx
- 1 份历史审查结果 markdown

## 8. 结论

008 的最终接入选择如下：

- **DeepResearchAgent**：008 内兼容 orchestrator/control plane
- **DeepTutor**：轻量 bridge，复用真实 ChatAgent
- **GPT Researcher**：direct import + env bridge + 本地文档上下文注入
- **FastGPT**：统一 adapter，优先 chunks retrieval
- **LLM**：服务端统一配置解析层，从 century.json/环境变量读取
