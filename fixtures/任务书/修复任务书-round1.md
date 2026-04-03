# 008-review-control-plane 结构化施组审查能力改造任务书（Codex 执行版）

> 材料绑定：本任务书绑定于`/Users/lucas/repos/review/008-review-control-plane` ，以及三份输入材料：原始施组、Gemini 深度审查结果、008 当前审查结果。仓库 README 已将 008 明确定位为 **review control plane**，而不是把能力重心放在“审查器本体”。  
> 代码审阅范围：本轮重点核查了 `apps/api/src/services/document_loader.py`、`apps/api/src/orchestrator/{planner.py,router.py,deepresearch_runtime.py}`、`apps/api/src/adapters/{llm_gateway.py,gpt_researcher_adapter.py,fastgpt_adapter.py}`、`apps/api/src/domain/models.py`、`apps/api/src/routes/tasks.py`、`apps/api/src/repositories/sqlite_store.py`，以及前端的 `apps/web/src/types/control-plane.ts`、`apps/web/src/components/{home-dashboard.tsx,task-detail.tsx}`、`apps/web/src/app/{page.tsx,tasks/[taskId]/page.tsx}`。未逐文件展开整个 `apps/web/src` 与所有 supporting files，因此前端部分以任务入口、详情页和类型定义为主，不假装看过全部组件实现。

## 事实标签约定

* **已确认事实**：直接来自仓库代码、仓库文档、原始施组、Gemini 结果、008 结果。
* **合理推断**：基于已确认事实做出的工程判断，用于解释为什么要这样改。
* **建议新增设计**：本任务书给 Codex 和工程团队的实施方案，不把它写成既成事实。

---

## A. 执行摘要（Executive Summary）

**已确认事实**：008 当前是一个多能力编排底座。README、架构文档与 planner 边界说明都把它定义为统一任务入口、能力路由、运行时总控，而不是最终正式审查器；`review_assist` 链路也被测试文档定义为“辅助审查”，并要求输出里明确写出“这是辅助审查结果，不等于正式审查结论”。运行时实现上，`review_assist` 把 FastGPT 检索结果、DeepTutor 解释、GPT Researcher 本地研究和文档前 4000 字预览打成一个被截断的综合输入，再交给 LLM 生成总结。

**已确认事实**：这套链路能抓住一些显性缺陷，但原始施组本身包含大量更适合“正式结构化审查”的信号，例如重复的“防火安全”章节、50t 汽车吊与 2.86t 起吊计算、7 天停机窗口、附件 1/2、煤气区域、37 人资源配置；Gemini 结果已经把这些信号提升为 L1/L2/L3 分层审查、程序合规判断、规范适用与工程推理，而 008 当前结果明确承认它只基于“文档目录、前部预览及分块审查笔记”。  

**建议新增设计**：本任务书不把 008 推倒重来，而是要求在现有 control plane 架构上增量引入一条 **`structured_review` 正式审查路径**，并明确与现有 `review_assist` 双轨共存：
`review_assist` 保留为快速辅助总结；
`structured_review` 新增为正式结构化审查。
正式审查必须建立在六层流水线之上：**文档解析层 → 事实抽取层 → 规则命中层 → 证据归档层 → LLM 解释层 → 报告组装层**。P0 不做“换模型”或“加长 prompt”，而是优先交付：`DocumentParseResult`、`ExtractedFacts`、最小规则核、`visibility_gap` 机制、最小 `FinalIssue[]` 输出和可回归评测。P1 再补 policy packs、evidence packs、report builder、evaluation harness；P2 才进入更复杂的工程推理增强和多模态扩展。

---

## B. 背景与问题定义

### B1. 输入层

**已确认事实**：`DocumentLoader` 目前对 `.docx` 主要使用 `docx2txt.process()`，失败后回退到 `python-docx` 段落拼接；对 PDF 则是 `pdfplumber` 纯文本提取。它返回的是单一字符串，不保留 heading 层级、表格结构、图片/图纸占位、附件状态、页眉页脚清洗结果。

**已确认事实**：原始施组并不是“纯段落文本”文档，而是明显依赖目录、图示、表格、附件与章节结构的工程文件。目录里直接出现重复的“第五节 防火安全 / 第七节 防火安全”，正文包含 50t 汽车吊和 2.86t 起吊计算、7 天停机窗口、附件 1/2；008 当前审查结果也写明其审查范围仅基于“文档目录、前部预览及分块审查笔记”。 

**问题定义**：当前输入层把“工程文档对象”降维成“截断后的纯文本字符串”，这会直接造成四类后果：

1. 章节级证据难定位；
2. 表格与附件状态丢失；
3. `系统没读到` 和 `文档没有` 混淆；
4. 规则引擎缺少可消费的结构化字段。
   这不是模型强弱问题，而是输入对象定义错误。

### B2. 检索层

**已确认事实**：`router.py` 目前按 query 关键词选默认数据集：出现“条例/法律/法规”走 `laws_regulations`，出现“监理/施工组织/施组/市政/建筑”走 `building_municipal`；`task_type == "review_assist"` 时也直接默认到 `building_municipal`。能力链方面，`review_assist` 固定为 `fast -> deeptutor -> (fixture 时 gpt_researcher) -> llm_gateway`。

**已确认事实**：FastGPT 检索默认参数虽是 `limit=5000`、`searchMode='mixedRecall'`、`usingReRank=True`，但 `llm_gateway.summarize_chunks()` 只拼前 8 个 chunks；`deepresearch_runtime._run_review_assist()` 最终综合输入也只取 `chunks[:8]`，且 user payload 被截到 15000 字符。

**问题定义**：当前“召回很多”并不等于“参与正式判断很多”。系统缺的不是再多一个检索器，而是 **rule-aware evidence retrieval**：先抽事实、再命规则、再为规则补证据，而不是先堆 chunks 再期待 LLM 自行归纳出正式审查结论。

### B3. 审查方法层

**已确认事实**：`deepresearch_runtime._run_review_assist()` 目前的顺序是：FastGPT 取 chunks → 可选 DeepTutor 解释 → 可选 GPT Researcher 本地报告 → LLM 生成“辅助审查要点”和“非正式审查结论”；返回结果里还显式写入 `notice = "这是辅助审查结果，不等于正式审查结论。"`。

**已确认事实**：Gemini 结果已经显式采用 L1/L2/L3 三层结构，不仅指出显性缺陷，还把同一份施组中的起重吊装、煤气区域、停送电、7 天窗口与 37 人资源配置等信息串成程序合规、规范适用和工程可操作性问题。  

**问题定义**：008 当前不是“坏掉的 formal reviewer”，而是“还没做成 formal reviewer”。它缺少三件 formal review 的基础设施：

* 结构化事实抽取；
* 规则命中与分层；
* 证据归档与 issue schema。
  所以它更像“审查辅助总结器”，不是“正式审查器”。

### B4. 架构层

**已确认事实**：README 直接写明 008 “不再把能力重心放在审查器本体”，而是 review control plane；架构文档把 DeepResearchRuntime 定义为 planner/router/coordinator，LLM Gateway 只是“轻量整理、摘要、最终辅助输出层”；并把“正式 review pack registry、规则执行器、结构化 issue schema、审查报告导出”放在“可扩展方向”。

**合理推断**：这意味着当前缺陷不是“链路没打通”，而是“领域子系统尚未落地”。所以本任务书必须采用 **增量演进**：保留 control plane，新增 formal review 子域，而不是重写整个系统。

### B5. 数据模型层

**已确认事实**：`apps/api/src/domain/models.py` 的 `TaskType` 目前只有 `knowledge_qa`、`deep_research`、`document_research`、`review_assist`；不存在 `structured_review`，也没有 `ReviewLayer`、`EvidenceSpan`、`RuleHit`、`FinalIssue` 等结构化审查对象。前端 `apps/web/src/types/control-plane.ts` 也保持同样的四种 task type。

**问题定义**：没有 issue schema，就没有稳定输出；没有 evidence schema，就没有可解释性；没有 visibility schema，就无法区分 `missing` 与 `visibility_gap`；没有 review enums，就很难做评测、回归、人工复核。

### B6. 测试评测层

**已确认事实**：`docs/testing.md` 目前验证重点是链路能跑通、工件能落盘、审查辅助输出包含固定短语；例如“测试 4：审查辅助”要求输出包含“辅助审查要点”和“这是辅助审查结果，不等于正式审查结论”。README 仍把 `make test / make smoke / make verify-connectivity` 作为主命令。

**问题定义**：现在的“测试通过”不代表“审查质量达标”。正式审查能力必须有独立评测集、模块级消融、跨模型对照、跨 pack 对照，以及至少 10 项质量指标。

---

## C. 现状盘点（As-Is）

### C1. 关键文件现状矩阵

| 文件                                                  | 当前职责                                                                  | 当前限制                                                                              | 为什么更像总结器而不是审查器                                                            | 依据             |
| --------------------------------------------------- | --------------------------------------------------------------------- | --------------------------------------------------------------------------------- | ------------------------------------------------------------------------- | -------------- |
| `README.md`                                         | 定义项目定位、能力列表、命令入口                                                      | 定位明确偏 control plane，而非 formal reviewer                                            | 从产品目标上就没有把“正式审查结论”当主目标                                                    |   |
| `docs/architecture.md`                              | 定义前端/API/orchestrator/adapter 分层                                      | 把 LLM Gateway 定义为“轻量整理、摘要、最终辅助输出层”，formal review pack registry 仍在未来方向             | 架构文档自己承认 formal review 还没落地                                               |   |
| `docs/known-limitations.md`                         | 说明能力边界                                                                | DeepTutor 更适合知识问答/解释型能力，不是完整平台镜像                                                  | 对正式审查来说，当前依赖能力天然更偏解释/辅助                                                   |  |
| `docs/testing.md`                                   | 当前测试目标说明                                                              | 审查辅助测试只校验链路与固定短语，不校验问题召回、严重度、依据准确率                                                | 测试目标决定团队不会朝 formal review 优化                                              |   |
| `apps/api/src/services/document_loader.py`          | 提供 `extract_text()`                                                   | 纯文本抽取；无 heading/table/attachment/image/visibility 结构                              | 没有结构化输入，后续只能做基于文本碎片的归纳                                                    |   |
| `apps/api/src/orchestrator/planner.py`              | 生成 plan、能力链与 boundary                                                 | boundary 明确写 `deepresearchagent` 不是 final domain reviewer                         | planner 自己就把系统边界定在“协调”而非“裁决”                                              | (`apps/api/src/orchestrator/planner.py`) |
| `apps/api/src/orchestrator/router.py`               | 根据 query / task type 选数据集与 capability chain                           | 默认按关键词和 task type 做粗粒度路由；`review_assist` 直接走 `building_municipal`                 | 缺少 doc type / discipline / policy pack 级别的正式审查路由                          |   |
| `apps/api/src/orchestrator/deepresearch_runtime.py` | 执行 `knowledge_qa / deep_research / document_research / review_assist` | `review_assist` 只看前 4000 字 preview、前 8 个 chunks，综合输入截到 15000 字符；结果显式标注为辅助审查       | 这是典型的“碎片综合总结”链路，而不是结构化 formal review pipeline                             |   |
| `apps/api/src/adapters/llm_gateway.py`              | 通用 chat；`summarize_chunks()` 做最后整理                                    | `summarize_chunks()` 只拼 `chunks[:8]`，system prompt 是“谨慎的工程知识整理助手”                 | 它被设计成谨慎摘要器，不是规则裁判器                                                        | (`apps/api/src/adapters/llm_gateway.py`) |
| `apps/api/src/adapters/gpt_researcher_adapter.py`   | 深度研究与本地文档研究                                                           | 本地文档上下文直接 `text[:24000]`，按字符串拼接到 `ext_context`                                    | 它能研究文本，但不是 section-aware / rule-aware 正式审查器                               | (`apps/api/src/adapters/gpt_researcher_adapter.py`) |
| `apps/api/src/adapters/fastgpt_adapter.py`          | 提供 chunk 检索                                                           | 虽支持 `mixedRecall` 和 rerank，但本身只返回 chunk 检索结果                                      | 没有 rule-centric clause resolution，无法独立承担审查判断                              |   |
| `apps/api/src/domain/models.py`                     | Task/API 基础模型                                                         | 只有 4 种 task type，无 issue/evidence/review enums                                    | 没有结构化审查对象，无法稳定表达 formal review 结果                                         |   |
| `apps/api/src/routes/tasks.py`                      | 创建/查询任务 API                                                           | 直接接受 `CreateTaskRequest` 并返回 `TaskRecord`；当前不承载 formal review 参数                  | TaskType、result shape 一旦扩展，这里是 API 兼容入口                                   | (`apps/api/src/routes/tasks.py`) |
| `apps/api/src/repositories/sqlite_store.py`         | 任务与事件落库                                                               | `task_type` 是文本列，`plan_json/result_json/error_json` 是 JSON 文本                     | 好处是可增量扩展 `structured_review`；坏处是没有专门 review 索引                            | (`apps/api/src/repositories/sqlite_store.py`) |
| `apps/web/src/types/control-plane.ts`               | 前端类型定义                                                                | `TaskType` 仍只有四类，CreateTaskRequest/TaskRecord 也没有 structured review 类型与 issue DTO | 前端无法创建和类型化展示 formal review 结果                                             | (`apps/web/src/types/control-plane.ts`) |
| `apps/web/src/components/home-dashboard.tsx`        | 首页任务创建表单                                                              | `TASK_OPTIONS` 只有 4 类，`review_assist` 文案明确写“辅助审查，不直接给正式审查结论”                      | UI 目前只支持“辅助审查”心智，不支持 formal review 表单                                     | (`apps/web/src/components/home-dashboard.tsx`) |
| `apps/web/src/components/task-detail.tsx`           | 任务详情渲染                                                                | 只假设 `task.result.finalAnswer` 是字符串，`sources/artifacts` 是普通数组                      | structured review 需要 issues、matrices、visibility、manual review flags 的专门展示 | (`apps/web/src/components/task-detail.tsx`) |

### C2. 结合三份材料后的现状结论

**已确认事实**：原始施组里有足够多的 formal review 信号；Gemini 结果证明这些信号可以被升格为 L1/L2/L3 分层审查；008 当前结果则明确承认自己只基于预览和 chunk notes。因此，当前差距不是“这个案例太难”，而是“008 现状还没有 formal review 这一条产品化路径”。  

---

## D. 目标状态（To-Be）

### D1. 目标架构的文字版描述

**建议新增设计**：目标不是“让 008 更像 Gemini”，而是让 Codex 在现有 control plane 之上，落地一条正式、可解释、可评测、可回归的 `structured_review` 路径。

目标架构如下：

1. **任务入口保留不变**
   继续使用现有 Web UI、FastAPI、SQLite store、artifact 落盘、DeepResearchRuntime、planner/router/adapters 基础设施。

2. **双轨制显式成立**

   * `review_assist`：保留，继续做快速辅助总结。
   * `structured_review`：新增，承担正式结构化审查。

3. **runtime 只做编排，不做领域裁判**
   `DeepResearchRuntime` 负责识别 task type、调度 review 子域执行器、落盘中间工件、回写任务结果。
   正式审查的领域判断迁移到 `apps/api/src/review/` 子域。

4. **formal review 由六层流水线驱动**
   `DocumentParseResult -> ExtractedFacts -> RuleHit[] -> IssueCandidate[] -> FinalIssue[] -> Report/Matrices`

5. **输出不再只有 Markdown 字符串**
   `structured_review` 必须同时输出：

   * 正式审查 Markdown 报告
   * `FinalIssue[]` 结构化 JSON
   * 章节结构图
   * 危大识别矩阵
   * 规则命中矩阵
   * 冲突矩阵
   * 附件可视域矩阵
   * 供人工复核的 evidence span 索引

### D2. 保留 / 新增 / 重构

| 类别 | 内容                                                                                                                                      |
| -- | --------------------------------------------------------------------------------------------------------------------------------------- |
| 保留 | `planner/router/runtime` 基础编排、FastGPT/DeepTutor/GPT Researcher/LLM adapters、SQLite task store、artifacts 机制、现有 `review_assist` API 和前端入口 |
| 新增 | `structured_review` task type、`review/` 子域、policy packs、evidence packs、fact extraction、rule engine、issue schema、evaluation harness      |
| 重构 | `document_loader.py` 输入对象、`router.py` 路由逻辑、`deepresearch_runtime.py` 正式审查分支、`llm_gateway.py` 职责边界、前端 result 展示类型                        |

---

## E. 设计原则与非目标（Principles / Non-goals）

1. **不推翻 control plane**
   不重写现有 orchestrator，不废弃 adapters，不重建新的任务平台。

2. **保留 `review_assist`，新增 `structured_review`**
   不再让 `review_assist` 承担 formal review 期待。

3. **正式审查不是一个大 prompt**
   必须拆成：解析、抽取、命规、证据、解释、组装。

4. **P0 不做换模型**
   不把“更强模型”“更长上下文”“更长 prompt”当首要任务。

5. **确定性逻辑优先**
   L0/L1 尽量使用确定性逻辑；LLM 只进入 L3 和文案整理。

6. **不把系统没看见当成文档没有**
   必须显式区分：
   `missing` / `visibility_gap` / `attachment_unparsed` / `evidence_missing` / `manual_review_needed`。

7. **不为单案例打补丁**
   不得硬编码“煤气区域 = 缺空气呼吸器”“汽车吊 = 必然缺承载力”“防火安全重复 = 专项正则”之类 case-specific patch。

8. **建议性增强不得伪装成强制性缺陷**
   必须区分“必须 / 应当 / 建议”。

9. **先做最小可用 formal review 内核，再谈多模态平台**
   P0 不上来搞庞大的扫描 OCR / 图像理解平台。

10. **评测先于文风**
    本次改造目标不是复刻 Gemini 行文风格，而是建立可评测、可回归的正式审查底座。

---

## F. 目标架构设计

### F1. 为什么必须新增 `review/` 子域

**建议新增设计**：正式审查逻辑不能继续堆在 `deepresearch_runtime.py`。原因有三：

* runtime 负责调度，不适合承载领域规则、证据分层和报告生成。
* `review_assist` 必须保留，formal review 必须与其物理隔离，避免回归风险。
* 结构化审查会持续增长 pack、schema、rules、evaluation，如果继续堆在 orchestrator/adapters，会把 control plane 变成领域大杂烩。

### F2. 建议目录结构

```text
apps/api/src/review/
  __init__.py
  schema.py
  pipeline.py
  parser/
    docx_parser.py
    normalizer.py
    attachment_indexer.py
  extractors/
    project_facts.py
    hazard_facts.py
    schedule_resource_facts.py
  rules/
    engine.py
    packs/
      construction_org/
      construction_scheme/
      hazardous_work/
      supervision/
  evidence/
    clause_store.py
    evidence_builder.py
  report/
    issue_builder.py
    report_builder.py
    matrices.py
  evaluation/
    dataset.py
    metrics.py
    harness.py
```

### F3. 模块职责、输入输出与边界

| 目录/文件                    | 角色                     | 输入                                          | 输出                                  | 与现有层的边界                                 |
| ------------------------ | ---------------------- | ------------------------------------------- | ----------------------------------- | --------------------------------------- |
| `review/schema.py`       | 正式审查内部 schema          | task metadata、parse/facts/rules/evidence 状态 | Pydantic models                     | 不替代 `domain/models.py`，只承载 review 子域细对象 |
| `review/pipeline.py`     | structured review 执行入口 | `TaskRecord`、fixture/source doc、router 结果   | `StructuredReviewResult`            | 由 `deepresearch_runtime.py` 调用          |
| `review/parser/*`        | 文档解析与可视域管理             | 文件路径                                        | `DocumentParseResult`               | 替代“纯文本即输入对象”的做法                         |
| `review/extractors/*`    | 事实抽取                   | `DocumentParseResult`、pack/extractor 配置     | `ExtractedFacts`                    | 对上游无感知，对下游只暴露结构化事实                      |
| `review/rules/engine.py` | 规则匹配                   | `ExtractedFacts`、`PolicyPack[]`             | `RuleHit[]`                         | 不直接调用 LLM                               |
| `review/rules/packs/*`   | 规则与 pack 注册            | manifest / rule defs                        | pack 列表、rule defs                   | 由 router/pipeline 选择                    |
| `review/evidence/*`      | 依据归档与条文匹配              | `RuleHit[]`、`EvidencePack[]`、可选 chunk 检索    | `IssueCandidate[]`、`EvidenceSpan[]` | 可以复用 FastGPTAdapter，但不把它当裁判             |
| `review/report/*`        | issue 归并与报告构建          | `IssueCandidate[]`、`FinalIssue[]`、matrices  | Markdown/JSON/artifacts             | 负责最终 formal review 输出                   |
| `review/evaluation/*`    | 评测集、指标、harness         | golden dataset、系统输出                         | 指标结果、回归报告                           | 独立于线上 runtime，可在 CI 跑                   |

### F4. 与现有 `orchestrator / adapters / domain` 的边界

* **Orchestrator**：只负责 task plan、task routing、capability scheduling、artifact 落盘、event 记录。
* **Review 子域**：负责正式审查领域逻辑。
* **Adapters**：保留为外部能力接入层；Formal review 只能把它们当工具，不把它们当裁判。
* **Domain**：保留共享 task/request/response 模型与跨层 enum/DTO。
* **Web**：只消费 `TaskRecord.result` 的结构化 schema，不承担审查判断。

---

## G. 领域模型与数据结构设计

### G1. 放置原则

* `apps/api/src/domain/models.py`：放 **共享 enum、API-facing DTO、TaskType 扩展**。
* `apps/api/src/review/schema.py`：放 **formal review 内部模型与中间产物**。
* `apps/web/src/types/control-plane.ts`：同步前端可消费的类型子集。

### G2. 核心对象设计表

| 对象                     | 为什么需要                                  | 关键字段                                                                                                                                                 | 建议文件                                                 | 类型               |
| ---------------------- | -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- | ---------------- |
| `StructuredReviewTask` | 把 `TaskRecord` 转成 formal review 专用执行对象 | `taskId`, `documentType`, `disciplineTags`, `policyPackIds`, `strictMode`, `sourceDocument`, `reviewProfile`                                         | `review/schema.py`                                   | runtime artifact |
| `PolicyPack`           | 把“文档类型/专业场景/规则集”装载成可复用单元               | `id`, `version`, `docTypes`, `disciplineTags`, `ruleIds`, `evidencePackIds`, `extractorIds`, `defaultEnabled`                                        | `review/schema.py`                                   | domain config    |
| `EvidencePack`         | 把法规依据和适用条件结构化                          | `id`, `version`, `clauses[]`, `forceLevel`, `applicability`, `severityMapping`                                                                       | `review/schema.py`                                   | domain config    |
| `DocumentParseResult`  | 让输入从纯字符串升级为结构化文档对象                     | `documentId`, `blocks`, `sections`, `tables`, `figures`, `attachments`, `normalizedText`, `visibilityReport`                                         | `review/schema.py`                                   | runtime artifact |
| `AttachmentVisibility` | 区分“缺失”和“未解析”                           | `parsed`, `attachment_unparsed`, `referenced_only`, `missing`, `unknown`                                                                             | `domain/models.py`                                   | shared enum      |
| `ExtractedFacts`       | 让规则引擎吃结构化事实                            | `projectFacts`, `hazardFacts`, `scheduleFacts`, `resourceFacts`, `attachmentFacts`, `emergencyFacts`, `factEvidence`                                 | `review/schema.py`                                   | runtime artifact |
| `RuleHit`              | 记录规则命中与命中类型                            | `ruleId`, `packId`, `matchType`, `status`, `factRefs`, `evidenceRefs`, `layerHint`, `severityHint`                                                   | `review/schema.py` + base enum in `domain/models.py` | runtime artifact |
| `IssueCandidate`       | 把多个 rule hit 归并为待输出问题                  | `candidateId`, `title`, `ruleHits`, `findingType`, `docEvidence`, `policyEvidence`, `manualReviewNeeded`                                             | `review/schema.py`                                   | runtime artifact |
| `FinalIssue`           | 正式输出的稳定问题对象                            | `issueId`, `title`, `layer`, `severity`, `findingType`, `docEvidence`, `policyEvidence`, `recommendation`, `confidence`, `whetherManualReviewNeeded` | `review/schema.py`                                   | report DTO       |
| `EvidenceSpan`         | 让证据可定位、可复核                             | `sourceType`, `sourceId`, `locator`, `excerpt`, `visibility`, `confidence`                                                                           | `domain/models.py` / `review/schema.py`              | shared DTO       |
| `ReviewLayer`          | 支持 L1/L2/L3 分层                         | `L1`, `L2`, `L3`                                                                                                                                     | `domain/models.py`                                   | shared enum      |
| `FindingType`          | 区分硬证据、工程推断、可视域缺口、建议增强                  | `hard_evidence`, `engineering_inference`, `visibility_gap`, `suggestion_enhancement`                                                                 | `domain/models.py`                                   | shared enum      |
| `ConfidenceLevel`      | 支持结果校准与人工复核                            | `low`, `medium`, `high`                                                                                                                              | `domain/models.py`                                   | shared enum      |
| `ReviewIssue`          | 供 API/UI 通用消费的轻量 issue DTO             | `id`, `title`, `layer`, `severity`, `findingType`, `summary`, `manualReviewNeeded`                                                                   | `domain/models.py`                                   | API DTO          |

### G3. 字段级设计建议

#### 1. `AttachmentVisibility`

```python
class AttachmentVisibility(str, Enum):
    parsed = "parsed"
    attachment_unparsed = "attachment_unparsed"
    referenced_only = "referenced_only"
    missing = "missing"
    unknown = "unknown"
```

#### 2. `ReviewLayer / FindingType / ConfidenceLevel`

```python
class ReviewLayer(str, Enum):
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"

class FindingType(str, Enum):
    hard_evidence = "hard_evidence"
    engineering_inference = "engineering_inference"
    visibility_gap = "visibility_gap"
    suggestion_enhancement = "suggestion_enhancement"

class ConfidenceLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
```

#### 3. `EvidenceSpan`

```python
class EvidenceSpan(BaseModel):
    sourceType: Literal["document", "policy", "artifact"]
    sourceId: str
    locator: dict[str, Any]  # page, sectionId, blockId, lineRange, tableCell, attachmentId
    excerpt: str
    visibility: AttachmentVisibility | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.medium
```

#### 4. `StructuredReviewTask`

```python
class StructuredReviewTask(BaseModel):
    taskId: str
    requestId: str
    documentType: Literal[
        "construction_org",
        "construction_scheme",
        "hazardous_special_scheme",
        "supervision_plan",
        "review_support_material",
    ]
    disciplineTags: list[str]
    policyPackIds: list[str] = []
    strictMode: bool = True
    sourceDocumentPath: str
    sourceFixtureId: str | None = None
    useAssistArtifacts: bool = False
```

#### 5. `DocumentParseResult`

```python
class DocumentParseResult(BaseModel):
    documentId: str
    filePath: str
    fileType: str
    sections: list[dict[str, Any]]          # heading tree
    blocks: list[dict[str, Any]]            # paragraph / list / figure placeholder
    tables: list[dict[str, Any]]
    attachments: list[dict[str, Any]]       # title, ref, visibility, parseState
    figures: list[dict[str, Any]]
    normalizedText: str
    preview: str
    visibilityReport: dict[str, Any]
```

#### 6. `ExtractedFacts`

```python
class ExtractedFacts(BaseModel):
    projectFacts: dict[str, Any]
    hazardFacts: dict[str, Any]
    scheduleFacts: dict[str, Any]
    resourceFacts: dict[str, Any]
    attachmentFacts: dict[str, Any]
    emergencyFacts: dict[str, Any]
    factEvidence: dict[str, list[EvidenceSpan]]
    unresolvedFacts: list[str] = []
```

#### 7. `RuleHit / IssueCandidate / FinalIssue`

```python
class RuleHit(BaseModel):
    ruleId: str
    packId: str
    matchType: Literal["direct_hit", "inferred_risk", "visibility_gap"]
    status: Literal["hit", "pass", "not_applicable", "manual_review_needed"]
    layerHint: ReviewLayer
    severityHint: str
    factRefs: list[str]
    evidenceRefs: list[str]
    rationale: str | None = None

class IssueCandidate(BaseModel):
    candidateId: str
    title: str
    ruleHits: list[RuleHit]
    layerHint: ReviewLayer
    severityHint: str
    findingType: FindingType
    docEvidence: list[EvidenceSpan]
    policyEvidence: list[EvidenceSpan]
    evidenceMissing: bool = False
    manualReviewNeeded: bool = False
    manualReviewReason: str | None = None

class FinalIssue(BaseModel):
    issueId: str
    title: str
    layer: ReviewLayer
    severity: Literal["high", "medium", "low", "info"]
    findingType: FindingType
    summary: str
    docEvidence: list[EvidenceSpan]
    policyEvidence: list[EvidenceSpan]
    recommendation: list[str]
    confidence: ConfidenceLevel
    whetherManualReviewNeeded: bool = False
```

### G4. 为什么这些对象必须先于 prompt

没有 `EvidenceSpan`，就无法做“问题—证据—依据—建议”闭环。
没有 `AttachmentVisibility`，就会继续把“附件未解析”误判成“附件缺失”。
没有 `RuleHit`/`IssueCandidate`/`FinalIssue`，LLM 只能生成长文本，无法做评测、回归和人工复核。
没有 `structured_review` task type，前后端都无法对 formal review 做独立演进。

---

## H. 正式审查流水线设计

### H1. 可视域检查（Visibility Check）

**输入**：原始文件路径、`DocumentParseResult` 初始对象。
**输出**：`visibilityReport`、`AttachmentVisibility[]`、`attachment-visibility-matrix`。
**确定性逻辑**：

* 识别 heading/tree/table/figure/attachment placeholder；
* 识别“附件1/附件2”等引用；
* 区分已解析、存在但未解析、仅引用未找到、完全缺失；
* 生成 `manual_review_needed` 标记。
  **禁止交给 LLM 的判断**：
* “附件存在/不存在”；
* “图纸是否已解析”；
* “系统没读到是否等于文档没有”。

**P0 行动要求**：

* 先把 `visibility_gap` 机制做出来；
* 对于原始施组中的附件 1/2，P0 允许输出 `attachment_unparsed` 或 `referenced_only + manual_review_needed`，但不允许直接输出“缺失”作为硬缺陷。

### H2. 事实抽取（Fact Extraction）

**输入**：`DocumentParseResult`、router 选出的 extractor 列表。
**输出**：`ExtractedFacts`。
**确定性逻辑优先**：

* section-aware 抽取：从“工程概况 / 施工部署 / 进度管理 / 资源计划 / 安全管理 / 应急预案 / 附件”分区抽取；
* table-aware 抽取：表格中的起重量、工期、劳动力、机具数量、附件索引、危险源表；
* 规则敏感字段优先：
  `crane_type`, `lifting_weight`, `gas_area`, `hot_work`, `temporary_power`, `special_equipment_scope`, `shutdown_window_days`, `labor_count`, `emergency_plan_titles`, `attachment_refs`, `special_scheme_plan_status`。
  **允许交给 LLM 的判断**：
* 仅限受控 schema 抽取的模糊字段，且必须输出 evidence spans；
* 不允许 LLM 直接产出最终缺陷结论。

### H3. 规则命中（Rule Matching）

**输入**：`ExtractedFacts`、`PolicyPack[]`。
**输出**：`RuleHit[]`。
**必须由确定性逻辑完成**：

* 危大识别初筛；
* 专项方案计划是否缺失；
* 章节重复/目录冲突；
* 附件可视域状态；
* 特种作业人员要求是否出现；
* 工期/资源基础冲突初筛。
  **规则类型**：
* 强制性规则：必须类；
* 建议性规则：应当/建议类；
* 可视域规则：`visibility_gap`。
  **禁止交给 LLM 的判断**：
* L1 命中；
* rule pass/hit/not_applicable；
* clause applicability 的基础判定。

### H4. 证据分层（Evidence Layering）

**输入**：`RuleHit[]`、`EvidencePack[]`、可选法规 chunk 检索结果。
**输出**：`IssueCandidate[]`。
**分层要求**：

* 文档证据：原施组文本、表格、附件引用；
* 规范证据：条文、指南、适用条件、强制/建议级别；
* 工程推断：仅当事实已充分且规则允许进入 L3；
* 待补充证据：`evidence_missing`。
  **确定性逻辑优先**：
* clause lookup；
* applicability mapping；
* evidence assembly；
* `manual_review_needed` 触发条件。
  **可选外部能力**：
* 可复用 FastGPT 做条文补检索；
* 但 evidence builder 必须以 `ruleId / clauseId` 为中心，不以“泛 query 检索”替代命规。

### H5. LLM 解释（LLM Explanation）

**输入**：`IssueCandidate[]`。
**输出**：经解释、归并、去重后的 `FinalIssue[]`。
**LLM 允许做的事**：

* 把多个候选问题合并成工程语言可读的问题标题；
* 为 L3 工程推断补足整改编排；
* 把 recommendation 写成现场可执行动作；
* 控制表述清晰度。
  **LLM 禁止做的事**：
* 自主判定 L1 命中；
* 发明不存在的文档证据；
* 发明不存在的法规条文；
* 把 `visibility_gap` 伪装成 `hard_evidence`。
  **hallucination 控制**：
* 输入只给 `IssueCandidate[]` 与 `EvidenceSpan[]` 的 ID 和 excerpt；
* 输出必须走 JSON schema；
* 若 evidence 不足，只能返回 `manual_review_needed = true`。

### H6. 报告组装（Report Builder）

**输入**：`FinalIssue[]`、matrices、summary stats。
**输出**：

* `structured-review-report.md`
* `structured-review-result.json`
* 中间矩阵 artifacts
* API `task.result`
  **必须是模板化/确定性输出**：
* 总体结论；
* L1/L2/L3 分层问题；
* 问题清单；
* 矩阵；
* 人工复核提示。
  **人工复核支持**：
* 每条 issue 可回溯到 `docEvidence` / `policyEvidence`；
* `manual_review_needed` 必须高亮。

### H7. L0 / L1 / L2 / L3 与六层流水线的映射关系

| 层级           | 主要对应流水线       | 说明                       |
| ------------ | ------------- | ------------------------ |
| L0 可视域检查     | 文档解析层 + 可视域报告 | 判断“读到了什么、没读到什么、哪里需要人工复核” |
| L1 硬证据与强约束规则 | 事实抽取层 + 规则命中层 | 以确定性规则为主，尽量不依赖 LLM       |
| L2 条文适用与规范差距 | 证据归档层         | 形成“事实—条文—缺口”链条           |
| L3 工程推理与整改编排 | LLM 解释层       | 只在事实与规则已成型后进入            |
| 输出层          | 报告组装层         | 把 L0-L3 统一成可复核产物         |

---

## I. Policy Pack / Rule Pack 设计

### I1. 为什么必须 pack 化

1. **防过拟合**：把规则绑定到 pack，而不是绑到某个案例关键词。
2. **可组合**：同一份施组可能同时命中机电安装、起重吊装、煤气区域、临时用电、动火、特种设备多个场景。
3. **可评测**：可以做跨 pack 对照和消融。
4. **可运维**：法规更新时只更新 evidence pack 或局部 scenario pack。

### I2. 三层抽象

#### 1. 文档类型 pack

* `construction_org`
* `construction_scheme`
* `hazardous_special_scheme`
* `supervision`
* `review_support_material`

#### 2. 专业场景 pack

* `electromech_installation`
* `civil`
* `steel_structure`
* `temporary_power`
* `lifting_operations`
* `hot_work`
* `gas_area_ops`
* `special_equipment`
* `supervision_process`

#### 3. 法规依据 pack

* `gbt_50502_construction_org`
* `dangerous_subproject_guidelines`
* `jgj_59_safety_check`
* `temporary_power_safety`
* `fire_safety_on_site`
* `special_equipment_regulations`

### I3. pack 组合示例

> 以下示例是抽象示例，不是为当前冷轧厂样本硬编码。

```text
structured_review(
  documentType="construction_org",
  disciplineTags=["electromechanical", "lifting", "gas_area", "temporary_power", "hot_work", "special_equipment"]
)
=> load:
  - construction_org.base
  - electromech_installation.base
  - lifting_operations.base
  - gas_area_ops.base
  - temporary_power.base
  - hot_work.base
  - special_equipment.base
  - evidence packs mapped by selected rules
```

### I4. P0 与 P1 的实现方式

* **P0**：pack 先用 Python/Pydantic manifest，实现简单、便于 Codex 直接改代码。
* **P1**：当 pack 数量上来后，再考虑 `yaml/json` registry 和 authoring 机制。
* **禁止**：P0 就做复杂 DSL / 可视化配置平台。

---

## J. 文件级改造清单（文件级改造矩阵）

> 下表“当前文件”基于 Section C 的 As-Is；这里重点给 Codex 明确“改什么、加什么、如何验收”。

| 优先级 | 模块                   | 当前文件                                                   | 新增文件                                                                                                                                        | 修改目的                                          | 具体改动点                                                                                                                                                                                                                                                                | 依赖关系                                  | 风险                                          | 验收标准                                                                          |
| --- | -------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- | ------------------------------------------- | ----------------------------------------------------------------------------- |
| P0  | Task/API schema      | `apps/api/src/domain/models.py`                        | `apps/api/src/review/schema.py`                                                                                                             | 引入 `structured_review` 与正式审查 shared enums/DTO | 给 `TaskType` 新增 `structured_review`；新增 `ReviewLayer`、`FindingType`、`AttachmentVisibility`、`ConfidenceLevel`、`EvidenceSpan`、`ReviewIssue`；`review/schema.py` 增加 `StructuredReviewTask`、`DocumentParseResult`、`ExtractedFacts`、`RuleHit`、`IssueCandidate`、`FinalIssue` | 无                                     | 影响前后端类型兼容                                   | `pytest` 通过；`CreateTaskRequest(taskType="structured_review")` 可序列化；前端 TS 类型同步 |
| P0  | Task route           | `apps/api/src/routes/tasks.py`                         | —                                                                                                                                           | 让 API 接受新 task type                           | 保持路由不变，继续使用 `CreateTaskRequest`；若有 request validation error 文案，新增 structured_review 说明                                                                                                                                                                               | `domain/models.py`                    | 低                                           | POST `/api/tasks` 可创建 `structured_review` 任务                                  |
| P0  | Task store           | `apps/api/src/repositories/sqlite_store.py`            | —                                                                                                                                           | 确保新 task type 和新 result JSON 能落库              | 不改表结构；补充 task_type enum 回归测试；确认 `result_json` 可存复杂 structured review 结果                                                                                                                                                                                              | `domain/models.py`                    | 低                                           | 不做 DB migration 也能创建/更新/读取 `structured_review` 任务                             |
| P0  | 文档解析                 | `apps/api/src/services/document_loader.py`             | `apps/api/src/review/parser/docx_parser.py`, `apps/api/src/review/parser/normalizer.py`, `apps/api/src/review/parser/attachment_indexer.py` | 把输入从纯文本升级为 `DocumentParseResult`              | 保留 `extract_text()` 兼容老链路；新增 `parse_document()`；docx parser 输出 headings/tables/attachments/figures；normalizer 做页眉页脚/重复段落清洗；attachment indexer 标注 `parsed/attachment_unparsed/referenced_only/missing`                                                                | `review/schema.py`                    | 会影响现有 `document_research` / `review_assist` | 老的 `extract_text()` 行为回归通过；样本文档 parse 后能提取 heading tree、附件索引、重复章节             |
| P0  | structured review 入口 | —                                                      | `apps/api/src/review/pipeline.py`                                                                                                           | 建立 formal review 执行入口                         | 实现 `StructuredReviewExecutor.run(task, fixture)`；内部串 parse/extract/rules/evidence/llm/report；返回 `task.result` 结构                                                                                                                                                     | `review/*`, `deepresearch_runtime.py` | 新链路初期错误定位成本高                                | 可单独跑通 executor 单元测试；返回结构包含 `issues/matrices/reportMarkdown`                   |
| P0  | 路由选择                 | `apps/api/src/orchestrator/router.py`                  | `apps/api/src/review/rules/packs/__init__.py`                                                                                               | 从 query/dataset 路由升级为 pack 路由                 | 为 `structured_review` 增加 pack selection：基于 `documentType + disciplineTags + fixture metadata + extracted hints` 选 pack；`review_assist` 逻辑不变                                                                                                                          | `review/schema.py`                    | pack 选择错误会放大误报/漏报                           | 单测：给定 docType/tags 能稳定选中预期 packs；`review_assist` 回归不变                         |
| P0  | 计划生成                 | `apps/api/src/orchestrator/planner.py`                 | —                                                                                                                                           | 让 plan 能表达正式审查阶段                              | 对 `structured_review` 生成多阶段 execution plan：`parse -> extract -> rules -> evidence -> explain -> report`；boundary 仍保留 runtime 非 final reviewer 的定位，但 formal review 子域为 domain reviewer                                                                                | `router.py`                           | 低                                           | `plan.capabilityChain` 或 equivalent stages 正确生成                               |
| P0  | runtime 编排           | `apps/api/src/orchestrator/deepresearch_runtime.py`    | —                                                                                                                                           | 把正式审查从 runtime 中拆出去                           | 新增 `_run_structured_review()`；调用 `StructuredReviewExecutor`；保留 `_run_review_assist()` 原行为；禁止 formal review 再走 `chunks[:8] + 15000 截断 JSON`                                                                                                                           | `review/pipeline.py`                  | 回归风险最大                                      | `review_assist` 回归不坏；`structured_review` 生成结构化结果与 artifacts                   |
| P0  | LLM 角色收缩             | `apps/api/src/adapters/llm_gateway.py`                 | —                                                                                                                                           | 让 LLM 从“主裁判”降级为“解释/归并/润色”                     | 保留 `chat()` 和 `summarize_chunks()` 供 legacy 使用；新增 `explain_issue_candidates()`、`merge_issue_candidates()`、`render_recommendations()`；输出必须 schema 化                                                                                                                   | `review/schema.py`                    | 如果误用旧方法会继续摘要化                               | formal review 不再调用 `summarize_chunks()`；LLM 输出校验通过                            |
| P0  | 规则引擎                 | —                                                      | `apps/api/src/review/rules/engine.py`, `apps/api/src/review/rules/packs/construction_org/*`                                                 | 交付最小规则核                                       | 先覆盖：施组结构完整性、危大识别、重大隐患初筛、附件可视域、应急预案针对性、工期/资源基础冲突                                                                                                                                                                                                                      | `ExtractedFacts`, `PolicyPack`        | 规则定义不稳                                      | 最小 pack 能在样本文档上输出稳定 `RuleHit[]`                                               |
| P0  | 事实抽取                 | —                                                      | `apps/api/src/review/extractors/project_facts.py`, `hazard_facts.py`, `schedule_resource_facts.py`                                          | 输出 formal review 最小 facts                     | project/hazard/schedule/resource/attachment/emergency 六类 facts；支持 section-aware/table-aware 抽取；必要时有限 LLM fallback                                                                                                                                                    | `DocumentParseResult`                 | facts 质量直接决定命规质量                            | 样本能抽到：50t/2.86t/7天/37人/附件1-2/重复章节/预案标题                                        |
| P0  | 证据归档                 | —                                                      | `apps/api/src/review/evidence/clause_store.py`, `evidence_builder.py`                                                                       | 建立“事实—条文—缺口”链                                 | 用 pack 的 `ruleId -> clauseId` 映射优先；必要时调用 FastGPT 补充 clause excerpt；输出 `IssueCandidate[]`                                                                                                                                                                             | `RuleHit[]`, `fastgpt_adapter.py`     | 条文映射维护成本                                    | 每个 candidate 都有 `docEvidence + policyEvidence` 或明确 `evidence_missing`         |
| P0  | 报告与矩阵                | —                                                      | `apps/api/src/review/report/issue_builder.py`, `report_builder.py`, `matrices.py`                                                           | 输出 formal review 结果和 4 类中间产物                  | 生成：Markdown 报告、`FinalIssue[]`、章节结构图、危大识别矩阵、规则命中矩阵、冲突矩阵、附件可视域矩阵                                                                                                                                                                                                       | `IssueCandidate[]`                    | 输出格式不稳定                                     | `task.result` 可被前端消费；artifacts 全部落盘                                           |
| P0  | FastGPT 复用           | `apps/api/src/adapters/fastgpt_adapter.py`             | —                                                                                                                                           | 把 FastGPT 从“答案来源”降级为“证据补检索工具”                 | 保留现有 search 接口；补充标准化 chunk metadata（chunkId/sourceLabel/score/datasetId）；为 evidence builder 提供稳定返回结构                                                                                                                                                                 | `review/evidence/*`                   | 低                                           | evidence builder 能拿到稳定 chunk meta                                             |
| P1  | GPT Researcher 复用    | `apps/api/src/adapters/gpt_researcher_adapter.py`      | —                                                                                                                                           | 使其成为“目标问题分段研究器”而非前缀文本研究器                      | 新增 `run_targeted_local_research(query, sections[])` 或等价方法；由 parse result 选 section graph，再构造 ext_context；保留旧 `run_local_docs_research()`                                                                                                                             | `DocumentParseResult`                 | 复杂度提升                                       | formal review 可选地按问题粒度调用研究器，而不是整文前 24000 字                                    |
| P1  | 评测框架                 | —                                                      | `apps/api/src/review/evaluation/dataset.py`, `metrics.py`, `harness.py`                                                                     | 建立可回归评测体系                                     | 定义 golden case schema、metrics、thresholds、ablation runner、cross-model runner、cross-pack runner                                                                                                                                                                        | `review/schema.py`                    | 需要标注投入                                      | `make eval-review` 能输出指标与失败 case 清单                                           |
| P1  | 文档更新                 | `README.md`, `docs/architecture.md`, `docs/testing.md` | `docs/formal-review.md`（可选）                                                                                                                 | 同步架构、测试和使用方式                                  | README 增加 structured_review；architecture 补双轨图；testing 重写质量验证目标；补 formal review 运行说明                                                                                                                                                                                  | backend stable                        | 文档滞后                                        | 文档与代码一致；新命令/新结果结构说明完整                                                         |
| P1  | Web 类型               | `apps/web/src/types/control-plane.ts`                  | —                                                                                                                                           | 前端理解新 task/result schema                      | 新增 `TaskType="structured_review"`；新增 `StructuredReviewResult`、`FinalIssue`、`ReviewMatrix` 类型                                                                                                                                                                         | backend schema                        | 低                                           | TS 编译通过；类型无 `any` 漏洞                                                          |
| P1  | Web API              | `apps/web/src/lib/api.ts`                              | —                                                                                                                                           | 前端能发起和读取 structured review                    | 为 create/get task 保持兼容；如果需要下载 artifacts，增加 API helper                                                                                                                                                                                                                | `routes/tasks.py`                     | 低                                           | 前端可成功发起 structured review 并渲染                                                 |
| P1  | Web 首页               | `apps/web/src/components/home-dashboard.tsx`           | `apps/web/src/components/structured-review-form.tsx`（建议）                                                                                    | 增加 structured review 表单与 pack/profile 选择      | 在 `TASK_OPTIONS` 增加 `structured_review`；增加 documentType / disciplineTags / strictMode 输入；保留 review_assist 文案                                                                                                                                                         | web types/api                         | 中                                           | 首页可创建 structured review，不影响原四类任务                                              |
| P1  | Web 详情页              | `apps/web/src/components/task-detail.tsx`              | `apps/web/src/components/structured-review-summary.tsx`, `issue-list.tsx`, `review-matrices.tsx`（建议）                                        | 将 result 从字符串视图升级为 issue/matrix 视图            | 保留原始 JSON 调试区；增加 FinalIssue 列表、矩阵卡片、manual review badge；若任务不是 structured_review，则走旧渲染                                                                                                                                                                                | web types/api                         | 中                                           | structured review 结果可视化；旧任务详情不回归                                              |
| P2  | 多模态增强                | `document_loader.py` / `review/parser/*`               | `review/parser/image_figure_parser.py`（可选）                                                                                                  | 解析图纸/示意图/进度网络图                                | 仅在 P2 考虑，对扫描件/图像型附件做增强，不进入 P0                                                                                                                                                                                                                                        | parser stable                         | 高                                           | 至少对附件图/进度网络图给出可视域增强，不破坏 P0                                                    |

---

## K. 分阶段实施路线图（P0 / P1 / P2）

### K1. P0：最小可用结构化审查内核

**目标**
在不破坏 `review_assist` 的前提下，交付第一条可运行、可解释、可回归的 `structured_review` 路径。

**具体任务**

1. `TaskType` 新增 `structured_review`，前后端类型打通。
2. `document_loader.py` 保留 legacy `extract_text()`，新增 `parse_document()` 返回 `DocumentParseResult`。
3. 建立 `review/` 子域和 `StructuredReviewExecutor`。
4. 实现最小 facts 抽取。
5. 实现最小规则核。
6. 实现 `visibility_gap / attachment_unparsed / evidence_missing / manual_review_needed` 机制。
7. 输出最小 `FinalIssue[]` + Markdown + 4 类矩阵。

**输出产物**

* `structured_review` task type
* `DocumentParseResult`
* `ExtractedFacts`
* 最小 `PolicyPack` / `RuleHit` / `FinalIssue`
* `structured-review-report.md`
* `structured-review-result.json`

**风险**

* parser 回归影响旧链路
* rules 过少导致“看起来不如 Gemini”
* formal review 与 review_assist 职责混淆

**依赖**

* backend types
* parser 子域
* runtime branch

**验收标准**

* `review_assist` 结果 shape 和 notice 不变
* `structured_review` 可创建、执行、落盘
* 样本文档中至少能正确区分 `missing` 与 `visibility_gap`
* 可输出结构化 `FinalIssue[]`
* 有单元测试和至少 1 个 golden case

### K2. P1：规则体系、报告体系、评测体系

**目标**
把最小可用内核升级成可维护的 formal review 底座。

**具体任务**

1. 引入 pack registry 与 evidence packs。
2. 实现 L1/L2/L3 分层审查流程。
3. 补 report builder 和矩阵 builder。
4. 建立 golden dataset 和 evaluation harness。
5. 前端结构化展示 results/issues/matrices。
6. 重写 `docs/testing.md` 与 README/architecture 文档。

**输出产物**

* `review/rules/packs/*`
* `review/evidence/*`
* `review/report/*`
* `review/evaluation/*`
* web structured review UI
* 文档与命令更新

**风险**

* pack 设计过重
* 评测标注量不足
* clause mapping 初期不稳

**依赖**

* P0 stable schema
* parser/facts/rules 稳定

**验收标准**

* 至少支持 1 类施组正式审查 + 1 类一般施工方案或危大专项方案试点
* `make eval-review` 可运行
* 有跨 pack、跨模型、模块消融结果
* Web 可视化 structured review 结果

### K3. P2：工程推理增强与多模态扩展

**目标**
把 formal review 从“结构化合规审查”提升为“工程逻辑增强审查”。

**具体任务**

1. 资源-工序冲突分析、风险升级、交叉作业冲突分析。
2. 图纸/图片附件可视域增强。
3. 人工复核闭环、误报库、标注回流。
4. pack registry / 规则 authoring / 证据维护平台化。

**输出产物**

* 工程推理增强模块
* 多模态 parser 增强
* 人工复核工作流
* 平台化运营能力

**风险**

* 多模态成本高
* 工程推断更容易过度推断
* 规则 authoring 复杂化

**依赖**

* P1 评测体系稳定
* `manual_review_needed` 闭环存在

**验收标准**

* 新增能力有单独评测项
* 过度推断率被显式度量
* 多模态能力不会把 `attachment_unparsed` 误改成“硬缺陷”

---

## L. 给 Codex 的执行拆分（PR / Commit 级别）

### PR1：新增 domain schema 与 task type

**改哪些文件**

* `apps/api/src/domain/models.py`
* `apps/api/src/routes/tasks.py`
* `apps/web/src/types/control-plane.ts`
* `apps/web/src/components/home-dashboard.tsx`

**不改哪些文件**

* `deepresearch_runtime.py`
* `document_loader.py`
* 所有 review 子域新逻辑

**为什么先做**

* 这是最小、最安全的跨端契约准备；
* 没有 `structured_review` task type，其它 PR 都无法串起来。

**回滚边界**

* 回滚到四种 TaskType；
* 前后端不影响旧任务。

---

### PR2：重构 document parse pipeline

**改哪些文件**

* `apps/api/src/services/document_loader.py`
* `apps/api/src/review/schema.py`
* `apps/api/src/review/parser/docx_parser.py`
* `apps/api/src/review/parser/normalizer.py`
* `apps/api/src/review/parser/attachment_indexer.py`
* 新增 parser 单测 fixtures

**不改哪些文件**

* `review_assist` runtime 逻辑
* LLM 相关 adapter

**为什么这个顺序安全**

* parser 是 formal review 的基础，但可以通过保留 `extract_text()` 来避免回归旧链路。

**回滚边界**

* 删掉 `parse_document()` 和 review/parser，新链路失效但 legacy 仍在。

---

### PR3：引入 fact extraction

**改哪些文件**

* `apps/api/src/review/extractors/project_facts.py`
* `hazard_facts.py`
* `schedule_resource_facts.py`
* `review/schema.py`

**不改哪些文件**

* `router.py`
* `llm_gateway.py`

**为什么这个顺序安全**

* facts 是 rules 的前置；在没有 rules 时也能单独验证抽取质量。

**回滚边界**

* structured review 仍可停在 parse 层，旧链路无影响。

---

### PR4：引入 minimal rule engine

**改哪些文件**

* `apps/api/src/review/rules/engine.py`
* `apps/api/src/review/rules/packs/construction_org/*`
* `apps/api/src/review/evidence/clause_store.py`
* `apps/api/src/review/evidence/evidence_builder.py`

**不改哪些文件**

* Web UI
* `gpt_researcher_adapter.py`

**为什么这个顺序安全**

* 先交付 deterministic L1/L2 内核，再接 LLM。
* 便于先做模块级评测。

**回滚边界**

* 保留 facts 抽取成果，暂时不输出 formal issues。

---

### PR5：runtime 接入 structured_review + report builder

**改哪些文件**

* `apps/api/src/orchestrator/router.py`
* `apps/api/src/orchestrator/planner.py`
* `apps/api/src/orchestrator/deepresearch_runtime.py`
* `apps/api/src/review/pipeline.py`
* `apps/api/src/review/report/{issue_builder.py,report_builder.py,matrices.py}`
* `apps/api/src/adapters/llm_gateway.py`
* `apps/api/src/adapters/fastgpt_adapter.py`

**不改哪些文件**

* 旧 `review_assist` 行为与输出 shape

**为什么这个顺序安全**

* backend 结构已具备，此时接 runtime 风险可控；
* report builder 先于前端 UI，便于用 raw JSON 调试。

**回滚边界**

* runtime 去掉 `_run_structured_review()` 分支即可恢复旧系统。

---

### PR6：测试与评测框架

**改哪些文件**

* `apps/api/src/review/evaluation/*`
* `docs/testing.md`
* `README.md`
* `docs/architecture.md`
* `Makefile`
* `fixtures/review_eval/*`

**不改哪些文件**

* Web UI
* 复杂多模态能力

**为什么这个顺序安全**

* 在 UI 改造前先把质量门槛固定下来，防止“页面好看但结果不可评”。

**回滚边界**

* 删除 eval 命令与 fixtures，不影响主运行链。

---

### PR7：兼容层与前端展示

**改哪些文件**

* `apps/web/src/lib/api.ts`
* `apps/web/src/components/home-dashboard.tsx`
* `apps/web/src/components/task-detail.tsx`
* 新增 `structured-review-summary.tsx`
* 新增 `issue-list.tsx`
* 新增 `review-matrices.tsx`
* `apps/web/src/app/page.tsx`
* `apps/web/src/app/tasks/[taskId]/page.tsx`

**不改哪些文件**

* parser/rules core logic

**为什么最后做**

* 先稳定后端 schema 和 artifacts，再渲染 UI，避免前端反复返工。

**回滚边界**

* 前端回退到 raw JSON 渲染，不影响 backend 正式审查能力。

---

## M. 测试、评测与回归方案

### M1. 现有命令如何延续

保留：

* `make test`
* `make smoke`
* `make verify-connectivity`

新增建议：

* `make test-review-unit`
* `make test-review-integration`
* `make smoke-structured-review`
* `make eval-review`
* `make eval-review-ablations`
* `make eval-review-cross-model`
* `make eval-review-cross-pack`

### M2. 测试分层

#### 1. 单元测试

覆盖：

* parser 输出结构是否稳定；
* attachment visibility 是否正确；
* extractor 是否能抽到关键字段；
* rule engine 是否命中/跳过正确；
* evidence builder 是否能生成 `docEvidence/policyEvidence/manualReviewNeeded`；
* report builder 是否稳定产出 schema。

#### 2. 集成测试

覆盖：

* `routes/tasks.py` 创建 `structured_review`；
* `deepresearch_runtime.py` 调到 `review/pipeline.py`；
* `sqlite_store.py` 能存取新结果；
* `llm_gateway.py` formal review 新接口输出合法 JSON。

#### 3. 端到端测试

覆盖：

* 首页创建 `structured_review`；
* 详情页展示 issue 列表与矩阵；
* 旧 `review_assist` 创建与详情页不回归。

#### 4. 评测集

覆盖 golden dataset 与指标计算。

#### 5. 回归基线

* review_assist 基线：保持 notice、结果 shape、旧工件落盘；
* structured_review 基线：首批 golden cases 的指标门槛。

#### 6. 模块级消融

必须支持关闭单个模块评测：

* `--disable-parser-normalizer`
* `--disable-visibility-check`
* `--disable-rule-engine`
* `--disable-llm-explanation`
* `--disable-report-builder`
* `--pack=...`
* `--model=...`

### M3. 标准化评测样本池建设要求

**最低建设要求**
P1 前必须建立一个最小可用 golden pool，覆盖下列文档/专业类型，不允许任何一项缺失：

| 维度            | 最低覆盖要求     |
| ------------- | ---------- |
| 施工组织设计        | ≥ 2 个 case |
| 一般施工方案        | ≥ 2 个 case |
| 危大专项方案        | ≥ 2 个 case |
| 监理规划 / 审查辅助材料 | ≥ 2 个 case |
| 机电安装类         | ≥ 2 个 case |
| 土建类           | ≥ 2 个 case |
| 钢结构类          | ≥ 2 个 case |
| 临电类           | ≥ 2 个 case |
| 起重吊装类         | ≥ 2 个 case |

**实施建议**

* P0：先建 5~10 个 mini golden cases。
* P1：扩展到至少 20~30 个标准 cases。
* case metadata 必须包含：`docType`, `disciplineTags`, `expectedPacks`, `groundTruthIssues`, `visibilityLabels`, `manualReviewCases`。

### M4. 指标定义

| 指标       | 含义                                         | 计算建议                                    |
| -------- | ------------------------------------------ | --------------------------------------- |
| 问题召回率    | 是否找到标注问题                                   | `matched_issues / ground_truth_issues`  |
| 重大问题命中率  | 是否命中 L1 / 重大事故隐患                           | `matched_L1 / ground_truth_L1`          |
| 危大识别命中率  | 是否识别危大工程、是否要求专项方案                          | case-level accuracy                     |
| 依据引用准确率  | 条文是否适用、引用是否正确                              | `valid_policy_refs / total_policy_refs` |
| 硬证据准确率   | 直接可证问题的误报 / 漏报                             | precision / recall for `hard_evidence`  |
| 工程推断率    | 有多少推断被人工认可为合理                              | `accepted_inferred / total_inferred`    |
| 过度推断率    | 有多少推断被判越界                                  | `rejected_inferred / total_inferred`    |
| 严重度校准准确性 | L1/L2/L3 或 severity 是否合理                   | exact / adjacent match                  |
| 建议可执行性   | 建议是否可落地                                    | 人工 rubric 1-5                           |
| 可解释性评分   | 问题—证据—依据—建议链是否完整                           | rubric 1-5                              |
| 附件可视域正确率 | 是否正确区分 missing / unparsed / visibility gap | label accuracy                          |

### M5. 评测方法

1. **端到端评测**
   对完整 structured_review 输出做 case-level 评分。

2. **模块级消融**
   关闭 parser / rule engine / LLM / report builder，量化每层贡献。

3. **跨模型对照**
   固定 facts/rules，只替换 explanation model，避免把所有差距都归因给模型。

4. **跨 pack 对照**
   同一 case 上关闭/开启 pack，验证 pack 化是否有效。

### M6. golden dataset 目录建议

```text
fixtures/review_eval/
  construction_org/
    electromech/
      case_001/
        source.docx
        metadata.json
        ground_truth_issues.json
        ground_truth_visibility.json
  construction_scheme/
  hazardous_special_scheme/
  supervision/
```

### M7. 初始阈值建议（写入 `evaluation/thresholds.yaml`）

> 这是建议阈值，最终由团队拍板。

* 重大问题命中率 ≥ 0.80
* 危大识别命中率 ≥ 0.85
* 依据引用准确率 ≥ 0.85
* 附件可视域正确率 ≥ 0.90
* 过度推断率 ≤ 0.15
* review_assist 回归失败数 = 0

---

## N. 报告输出格式设计

### N1. `structured_review` 目标输出结构

```json
{
  "summary": {
    "overallConclusion": "修改后重新报审",
    "documentType": "construction_org",
    "selectedPacks": ["construction_org.base", "lifting_operations.base"],
    "manualReviewNeeded": true
  },
  "issues": [
    {
      "issueId": "ISSUE-001",
      "title": "危大工程专项方案计划缺失",
      "layer": "L1",
      "severity": "high",
      "findingType": "hard_evidence",
      "docEvidence": [],
      "policyEvidence": [],
      "recommendation": [],
      "confidence": "high",
      "whetherManualReviewNeeded": false
    }
  ],
  "matrices": {
    "hazardIdentification": {},
    "ruleHits": {},
    "conflicts": {},
    "attachmentVisibility": {},
    "sectionStructure": {}
  },
  "artifacts": [
    "artifacts/tasks/.../structured-review-report.md",
    "artifacts/tasks/.../rule-hit-matrix.json"
  ]
}
```

### N2. 正式审查 Markdown 报告结构

1. 总体结论
2. 可视域与人工复核提示
3. L1 问题
4. L2 问题
5. L3 问题
6. 危大识别矩阵
7. 规则命中矩阵
8. 冲突矩阵
9. 附件可视域矩阵
10. 章节结构图
11. 证据索引与人工复核说明

### N3. 每条问题必须包含的字段

* 问题标题
* `layer`
* `severity`
* `finding_type`
* `doc_evidence`
* `policy_evidence`
* `recommendation`
* `confidence`
* `whether_manual_review_needed`

### N4. 4 类专门 artifact builder

| Artifact | 生成模块                                          | 价值                                  |
| -------- | --------------------------------------------- | ----------------------------------- |
| 章节结构图    | `review/report/matrices.py` + parser 输出       | 帮人工快速看文档结构异常、重复章节、附件挂接位置            |
| 危大识别矩阵   | `review/report/matrices.py` + rule hits       | 把事实、规则、结论、专项方案需求对齐，利于 L1 回归         |
| 规则命中矩阵   | `review/report/matrices.py` + engine 输出       | 可直接做回归 diff，定位是 parser 退化还是 rule 退化 |
| 冲突矩阵     | `review/report/matrices.py` + extracted facts | 显式表达工期-资源、危险源-措施、附件-审查项冲突           |

**为什么必须做这四类**

* 它们显著提升可解释性；
* 它们天然适合做机器 diff 和回归测试；
* 它们降低人工复核成本；
* 它们能把 formal review 从“长文报告”升级成“可审计产物”。

---

## O. 风险、边界与开放问题

### O1. 现在就能定的

1. 双轨制必须成立，`review_assist` 不得删除。
2. P0 必须先做 parser/facts/rules/evidence，不做模型替换优先级。
3. `visibility_gap` 机制必须先于“附件缺失”结论。
4. formal review 输出必须结构化，不能只是一篇 Markdown。

### O2. 需要工程试做后再定的

1. facts 抽取中 LLM fallback 的比例和边界。
2. rule pack 的粒度：是按大类场景还是按更细 discipline 拆。
3. evidence pack 的 clause 粒度与维护成本。
4. `gpt_researcher_adapter` 在 formal review 中是常用模块还是可选增强模块。
5. 初始评测阈值的合理区间。

### O3. 必须人工拍板的

1. 规范/依据库的长期维护责任归属。
2. 是否在 P1 引入扫描件/图纸多模态解析。
3. 是否建设 rule authoring 机制与审核流程。
4. golden dataset 的标注规范与人工验收标准。
5. formal review 结果是否作为业务“准入门槛”而非仅供辅助。

---

## P. 明确的 Definition of Done

以下条件全部满足，才视为本次改造完成：

1. `structured_review` 能被创建、调度、执行、查询。
2. 现有 `review_assist` 不回归损坏，notice 与结果 shape 保持兼容。
3. 至少支持一类 **施工组织设计** 的正式结构化审查。
4. 能区分 `missing` 与 `visibility_gap`，并支持 `attachment_unparsed`。
5. 能输出结构化 `FinalIssue[]`。
6. 能输出正式报告 Markdown 与至少 4 类中间矩阵 artifacts。
7. 有最小 golden dataset 与 `make eval-review` 命令。
8. `docs/testing.md`、`docs/architecture.md`、`README.md` 已同步更新。
9. 前端可创建并查看 `structured_review` 任务。
10. 每条 formal issue 都能追溯到 `docEvidence` 和 `policyEvidence`。
11. 不依赖“模仿 Gemini 文风”也能稳定输出正式审查结果。
12. 至少一轮模块级消融和跨 pack 对照已跑通并有记录。
13. P0/P1 中禁止项没有被采用：未出现 case-specific hardcode、未出现“没读到附件=缺附件”的错误逻辑。

---

## Q. 附录：接口草图 / 伪代码 / 数据流草图

### Q1. `structured_review` 请求草图

```json
{
  "taskType": "structured_review",
  "capabilityMode": "auto",
  "query": "对该施工组织设计执行正式结构化审查",
  "fixtureId": "230235-冷轧厂2030单元三台行车电气系统改造-施工组织设计.docx",
  "useWeb": false,
  "debug": true,
  "sourceUrls": [],
  "documentType": "construction_org",
  "disciplineTags": ["electromechanical", "lifting", "gas_area", "temporary_power", "hot_work", "special_equipment"],
  "strictMode": true
}
```

### Q2. runtime 编排伪代码

```python
# apps/api/src/orchestrator/deepresearch_runtime.py

async def run_task(task: TaskRecord):
    plan = planner.build_plan(task, has_fixture=bool(task.fixtureId))

    if task.taskType == "review_assist":
        return await self._run_review_assist(task, plan, fixture)

    if task.taskType == "structured_review":
        return await self._run_structured_review(task, plan, fixture)

    ...
```

```python
# apps/api/src/review/pipeline.py

class StructuredReviewExecutor:
    async def run(self, task: StructuredReviewTask, fixture: FixtureRecord | None) -> dict[str, Any]:
        parse_result = self.parser.parse_document(task.sourceDocumentPath)
        visibility = self.parser.build_visibility_report(parse_result)

        packs = self.pack_registry.select(task.documentType, task.disciplineTags, parse_result)
        facts = self.extractors.extract(parse_result, packs)

        rule_hits = self.rule_engine.run(facts, packs, visibility)
        candidates = self.evidence_builder.build(rule_hits, facts, parse_result, packs)

        final_issues = self.llm_gateway.explain_issue_candidates(candidates)
        matrices = self.report_builder.build_matrices(parse_result, facts, rule_hits, final_issues)
        report = self.report_builder.render(final_issues, matrices, visibility)

        return {
            "summary": report.summary,
            "issues": [issue.model_dump() for issue in final_issues],
            "matrices": matrices,
            "reportMarkdown": report.markdown,
            "artifacts": report.artifacts,
        }
```

### Q3. pack manifest 草图

```python
class PolicyPack(BaseModel):
    id: str
    version: str
    docTypes: list[str]
    disciplineTags: list[str]
    extractorIds: list[str]
    ruleIds: list[str]
    evidencePackIds: list[str]
    defaultEnabled: bool = True
```

### Q4. evaluation case metadata 草图

```json
{
  "caseId": "construction_org_electromech_001",
  "docType": "construction_org",
  "disciplineTags": ["electromechanical", "lifting"],
  "expectedPacks": ["construction_org.base", "lifting_operations.base"],
  "groundTruthIssues": "ground_truth_issues.json",
  "groundTruthVisibility": "ground_truth_visibility.json",
  "notes": "manual_review required on attachment visibility"
}
```

### Q5. 不要做什么（防过拟合清单）

1. 看到“煤气区域”就固定报缺空气呼吸器。
2. 看到“汽车吊”就固定报地基承载力验算缺失。
3. 看到“防火安全”重复就加一个只服务本案例的正则补丁。
4. 只把报告改写成 L1/L2/L3 文风。
5. 只换更大模型。
6. 只加更长 prompt。
7. 只增大上下文长度。
8. 把“系统没读到附件”直接写成“文档缺附件”。
9. 为单一行业场景做专门 patch，而不是抽象成 scenario pack。
10. 把建议性工程优化伪装成强制性缺陷。

---

**一句话交付指令**：Codex 应按 “先建 `structured_review` 契约与 parser，再建 facts/rules/evidence，再接 runtime/report/evaluation，最后补 UI” 的顺序增量改造 008，目标是把它升级成一套 **可扩展、可解释、可评测、可回归的结构化施组审查底座**，而不是另一个只会写长文的总结器。

