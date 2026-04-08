# 008 审查控制面（Review Control Plane）— 完整 PRD

> 📋 文档状态：V0.3 产品需求文档（完整版）
> 📅 更新时间：2026-04-07
> 👥 适用对象：产品、研发、架构、测试、项目管理

---

## 一、产品定位与一句话定义

**产品名称：** `008-review-control-plane`

**一句话定义：** 008 当前是一个以 **review control plane** 为总控壳、在 **official scope** 内承载 `structured_review` 正式结构化审查主链的系统。

**V0.3 一句话目标：** V0.3 不是扩范围版本，而是收边界、硬内核、补证据、强评测的版本。目标是在 official scope 内，把 structured_review 做成：可审前置、可视域诚实、证据可追溯、规则可命中、结果可复核、评测可闭环的 formal-review spine。

---

## 二、当前阶段的产品定位

当前产品的最准确说法，不是"大而全的工程 AI 平台"，也不是"单一对话式审查模型"，而是一个 **review control plane**：

- **前端**：统一任务入口与链路展示
- **后端**：任务 API、状态存储与 artifacts
- **运行时**：能力路由与编排
- **审查子域**：`structured_review` 正式结构化审查，主链已定义为 `parse → facts → rules → evidence → report`

### 它当前不是什么

- 不是万能工程 AI
- 不是全自动替代人工签发系统
- 不是"更像 Gemini 的写作器"
- 不是当前阶段就去做平台级 OCR、多模态、图纸平台或多文档联合审查的大系统

### 双轨能力区分

| 能力轨道 | 定位 | 说明 |
|---|---|---|
| `review_assist` | 快速辅助总结 | 解决"先看一眼、先归纳一下"，明确不是正式审查结论 |
| `structured_review` | 正式结构化审查 | V0.3 产品主线，输出稳定 schema、矩阵和报告工件 |

### 产品结构图

```
008-review-control-plane
|
|-- review_assist                          ← 快速辅助 / 总结 / 预览（非正式审查）
|
+-- structured_review                      ← 正式结构化审查主链
    |
    |   +----------- formal-review spine -----------+
    |   |                                           |
    |-- parse ........... 文档解析 + parseMode/Warnings
    |-- facts ........... 事实抽取 + unresolvedFacts
    |-- rules ........... 规则/条文适用 + applicabilityState
    |-- evidence ........ 证据链闭合 + evidence gap
    |-- report .......... 报告 + artifacts + artifactIndex
    |   |                                           |
    |   +-------------------------------------------+
    |
    |-- reviewer gate ... 人工复核分流（manualReviewNeeded）
    +-- eval gate ....... 版本化评测拦截（versioned cases + layered metrics）

支撑层：前端界面 / runtime 编排 / 外部能力适配器
未来层：OCR / 多模态 / 图纸平台化 / 多文档联合 / ontology / graph-first / workflow 产品化
```
## 三、V0.3 为什么要"收边界、硬内核、补证据、强评测"

V0.3 的中心定义：**收边界、硬内核、补证据、强评测**。这不是口号，而是对当前仓库最短板的直接响应。

### 当前最重要的问题

当前最重要的问题，不在平台壳不够大，也不在报告文案不够像专家，而在：

1. **L0 可视域与 parser 诚实性** — 系统是否诚实表达"看到了什么、没看到什么"
2. **L1/L2 规则与证据闭环** — 规则命中是否可追溯、证据链是否可验证
3. **reviewer gate 与 eval gate 的硬度** — 人工复核与评测拦截是否已制度化

最新阶段性评测虽然显示 official stage gate 已通过，但同时给出：
- `attachment_visibility_accuracy` 仅 **0.5833**
- `hard_evidence_accuracy` 仅 **0.6945**
- L3 的 `suggestion_defect_separation` 仍只是 diagnostic 维度

这恰恰说明 **"能跑通"不等于"内核已硬"**。

### 为什么不扩范围

- 当前 official `documentType` 仅有 `construction_org` 与 `hazardous_special_scheme`
- 其余 ready base pack 仍处于 experimental，需经过治理晋升门禁才能成为 official
- 贸然扩范围只会在尚未做硬的主链上叠加不稳定性

### 为什么主攻 L0 + L2

| 层级 | 状态 | V0.3 定位 |
|---|---|---|
| **L0** 可视域 | parser warnings / manual review 语义尚未完全前置成独立 gate | **主攻** |
| **L1** 规则命中 | 已有规则命中与问题对象骨架 | 巩固 |
| **L2** 证据闭环 | clause applicability / evidence gap closure 未稳定闭环 | **主攻** |
| **L3** 工程推理 | 可增强但不应成为主战场 | 诊断性增强 |

---

## 四、V0.3 目标与非目标

### 4.1 V0.3 目标

1. **在 official scope 内收口** — 只围绕 `construction_org` 与 `hazardous_special_scheme` 展开
2. **formal-review spine 做到"像一条正式主链"**：
   - 审查前先判断可不可审
   - 用 `visibility` 诚实表达看到了什么和没看到什么
   - 把 facts、rules、policy refs、issues、artifacts 串成可追溯证据链
   - 把 `unresolvedFacts` 与 `applicabilityState` 纳入判断
   - 在结果层支持人工复核
   - 在评测层支持 versioned replay 与 stage gate
3. **reviewer / eval / artifacts 是正式主线的一部分**，不是配角

### 4.2 V0.3 非目标

| 不做的事 | 原因 |
|---|---|
| 全文档类型覆盖 | official 只有 2 个 doc type，其余需通过治理晋升 |
| OCR / 多模态 / 图纸平台化 | PDF 正式边界仍为 `pdf_text_only + parserLimited=True` |
| 多文档联合审查 | 当前仍是最小单文件输入路径 |
| ontology / graph-first 重构 | 当前主问题不是"图谱不够漂亮"而是"证据闭环不够硬" |
| 企业级大 workflow 壳 | 最短板不在队列编排，而在 formal-review spine 本身 |
## 五、产品演进主线（V0.0 → V0.3）

| 版本 | 定位 | 关键成就 |
|---|---|---|
| **V0.0** | 审查相关原型输出 | 有 issue、rule-hit、matrix 雏形，证明了路可走 |
| **V0.2** | 代际性升级 | `visibility` 成为 canonical object；`manualReviewNeeded` 成为 canonical 语义；issues、matrices、artifactIndex 正式化；pack readiness 纳入治理 |
| **V0.3** | 收边界、硬内核 | 在 official scope 内把主链做硬：L0 可视域诚实 + L2 证据闭环 + gate 制度化 |

**演进主线**：从"审查相关原型输出" → "带稳定 contract 的 early structured reviewer" → "official scope 内可信、可复核、可评测的 formal-review spine"

---

## 六、核心能力地图

产品的核心能力围绕 formal-review spine 组织，中心不是"更多模型能力"，而是"更可靠的 formal-review contract"。

### 能力分层

| 层级 | 名称 | 职责 | V0.3 定位 |
|---|---|---|---|
| 1 | **文档可视域层** | 回答"系统看到了什么、没看到什么" | 正式主线前置条件 |
| 2 | **事实抽取层** | 把输入文档转为可用于规则判断的 facts | 正式主线骨架 |
| 3 | **规则/条文适用层** | 对接 policy packs、clause applicability | 正式主线核心中段 |
| 4 | **证据与 unresolved facts 层** | 串接可追溯证据链 | **V0.3 必须补硬** |
| 5 | **报告与 artifact 层** | 组织成 reviewer 可读、eval 可回放的外显载体 | 正式主线输出层 |
| 6 | **reviewer gate 层** | 分流"系统可判"与"需人工复核" | 正式主线（当前偏弱） |
| 7 | **eval gate 层** | versioned cases + layered metrics 约束 | 正式主线治理闭环 |

### 层级归属

- **正式主线**：文档可视域 → 事实抽取 → 规则适用 → 证据 → 报告 → reviewer gate → eval gate
- **支撑层**：前端界面、runtime 编排、外部能力适配器
- **未来层**：OCR、多模态、图纸平台化、多文档联合审查、ontology / graph-first、企业级 workflow
## 七、正式审查能力规格（structured_review）

### 7.1 入口参数

| 参数 | 说明 |
|---|---|
| `fixtureId` / `sourceDocumentRef` | 二选一，服务端统一归一化为 `sourceDocumentRef` |
| `documentType` | 缺省时允许后端推断，最终写回 `resolvedProfile.documentType` |
| `disciplineTags` | 缺省时允许由事实抽取补齐 |
| `strictMode` | 默认 `true`，当前状态 `reserved / no-op` |
| `policyPackIds` | 为空表示自动选 pack；显式传入时只执行 `ready` packs |

### 7.2 P0 稳定结果字段

- `summary` — 审查摘要
- `visibility` — top-level canonical visibility 对象（携带 `parseMode / parseWarnings / manualReviewReason / preflight`）
- `resolvedProfile` — 实际生效的审查配置
- `issues` — 问题列表（含 `issueKind / applicabilityState / missingFactKeys / blockingReasons`）
- `matrices` — 结构化矩阵（附件可视域 / 规则命中 / 冲突 / 章节结构）
- `artifactIndex` — 工件索引（authoritative source）
- `reportMarkdown` — 面向审查专家的中文正式报告
- `unresolvedFacts` — 未解析事实（含 `sourceExtractor / blockingReason / visibilityLimited`）

### 7.3 当前正式支持的文档类型

| 文档类型 | 状态 | 说明 |
|---|---|---|
| `construction_org` | ✅ **official** | 施工组织设计 |
| `hazardous_special_scheme` | ✅ **official** | 危大专项方案 |
| `construction_scheme` | 🧪 experimental | 已有 ready base pack |
| `supervision_plan` | 🧪 experimental | 已有 ready base pack |
| `review_support_material` | 🧪 experimental | 已有 ready base pack |

### 7.4 Pack Registry

**Base Packs：**

| Pack | 状态 |
|---|---|
| `construction_org.base` | ✅ ready |
| `hazardous_special_scheme.base` | ✅ ready |
| `construction_scheme.base` | ✅ ready (experimental) |
| `supervision_plan.base` | ✅ ready (experimental) |
| `review_support_material.base` | ✅ ready (experimental) |

**Scenario Packs：**

| Pack | 状态 | 适用范围 |
|---|---|---|
| `lifting_operations.base` | ✅ ready | construction_scheme 可用 |
| `temporary_power.base` | ✅ ready | construction_scheme 可用 |
| `hot_work.base` | ✅ ready | construction_scheme 可用 |
| `gas_area_ops.base` | ✅ ready | 仅 construction_org / hazardous_special_scheme |
| `special_equipment.base` | 📋 placeholder | — |
| `working_at_height.base` | 📋 placeholder | — |

> ⚠️ **治理原则**：`ready pack ≠ official documentType`。Pack 晋升治理条件：tests / versioned cases / policy evidence / rule coverage 全部达标。

### 7.5 Issue 语义

- `issueKind`：`hard_defect` / `visibility_gap` / `evidence_gap` / `enhancement`
- `applicabilityState`：标记规则适用状态
- `evidenceMissing=true` 必须具备显式 explainability
- visible-scope 内已闭合的负向事实 → `hard_defect + applies`
- parser-limited 或 fact-unresolved 的负向结论 → `evidence_gap + blocked_by_missing_fact`

### 7.6 Manual Review 语义

- `manualReviewNeeded` 是唯一 canonical 布尔语义
- 以下场景必须保留人工复核标记：
  - `parser_limited_pdf_requires_manual_review`
  - `visibility_gap`
  - `attachment_unparsed` / `referenced_only`
  - evidence 不足以形成硬缺陷时
- **系统不得把"没读到附件"直接写成"附件缺失"**

### 7.7 Artifact API

| 接口 | 说明 |
|---|---|
| `POST /api/uploads/documents` | 文档上传 |
| `GET /api/tasks/support-scope` | 支持范围查询（含 promotionCriteria） |
| `GET /api/tasks/{taskId}/artifacts` | 工件列表 |
| `GET /api/tasks/{taskId}/artifacts/{artifactName}` | 工件下载 |
| `PUT /api/tasks/{taskId}/reviewer-decision` | 人工复核决策更新 |
| `GET /api/tasks/{taskId}/review-preparation` | 审查准备摘要 |

### 7.8 L1 / L2 / L3 语义分层

| 层级 | 范围 | LLM 角色 |
|---|---|---|
| **L1** | 硬证据 / 可视域 / 强约束规则 | LLM 不负责命中判断 |
| **L2** | 条文适用 + 依据链完整性 | LLM 不负责基础判定 |
| **L3** | 工程推理 / 整改编排 | LLM 只负责 issue title 清洗、recommendation 生成、候选去重合并 |

**LLM 绝对禁区**：不得生成不存在的文档/法规证据。
## 八、系统架构

### 8.1 为什么是 Control Plane

008 的职责不是承载某个具体审查 pack，而是：
- 统一接收任务
- 做任务规划与能力路由
- 编排 DeepTutor / GPT Researcher / FastGPT / 本地 LLM
- 保存任务状态、步骤、工件
- 向前端暴露统一、可观察的运行时接口
- 为正式审查能力提供可扩展的 review domain pipeline

### 8.2 系统分层

```
┌──────────────────────────────────────────────────────────┐
│  1. 前端层（apps/web）                                     │
│     展示 / 创建任务 / SSE 实时流 / 结果渲染 / reviewer cockpit │
├──────────────────────────────────────────────────────────┤
│  2. API 层（apps/api/src/routes）                          │
│     任务 CRUD / upload / support-scope / artifact / reviewer │
├──────────────────────────────────────────────────────────┤
│  3. Orchestrator 层                                       │
│     planner → router → runtime 调度 structured_review     │
├──────────────────────────────────────────────────────────┤
│  4. Review 子域（apps/api/src/review）                     │
│     parser → facts → pack registry → rule engine →        │
│     evidence builder → report builder → eval harness      │
├──────────────────────────────────────────────────────────┤
│  5. Adapter 层（apps/api/src/adapters）                    │
│     deeptutor / gpt_researcher / fastgpt / llm_gateway    │
├──────────────────────────────────────────────────────────┤
│  6. Config 层 + 7. State/Artifacts 层                     │
│     配置注入 / SQLite / artifacts / uploads / fixtures     │
└──────────────────────────────────────────────────────────┘
```

### 8.3 核心任务流

```
Web UI → FastAPI Tasks API → DeepResearchRuntime
                                    │
                        ┌───────────┼───────────┐
                        ▼           ▼           ▼
                    Planner      Router     Review Pipeline
                                    │           │
                        ┌───────┬───┴───┬───┐   ├── Parser
                        ▼       ▼       ▼   ▼   ├── Extractors
                    FastGPT DeepTutor GPT-R LLM  ├── Pack Registry
                                                ├── Rule Engine
                        ▼       ▼       ▼   ▼   ├── Evidence Builder
                        └───────┴───────┴───┘   └── Report Builder
                                    │
                                    ▼
                            SQLite + Artifacts → Web UI
```

### 8.4 各能力角色

| 能力 | 角色 |
|---|---|
| DeepResearchAgent / Runtime | planner, router, coordinator |
| FastGPT | 底层知识切片检索层 |
| DeepTutor | 知识问答 / 规范解释层 |
| GPT Researcher | 研究报告 / 多来源归纳 / 本地文档研究层 |
| LLM Gateway | 轻量整理、摘要、正式审查解释层（非主裁判） |
| Review Pipeline | formal review 的领域执行器 |

### 8.5 当前 Formal Review 最小规则核

- 施工组织设计核心章节完整性
- 一般施工方案核心章节完整性
- 监理规划核心章节与监测监控安排完整性
- 审查支持材料"仅为补充、不能替代正式方案正文"提示
- 重复章节标题识别
- 附件可视域缺口标记
- 高风险作业专项方案挂接检查
- 应急预案针对性检查
- 停机窗口 / 人力 / 高风险工序并行压力提示
- 危大专项方案核心章节完整性
- 危大专项方案验算依据检查
- 危大专项方案措施-监测闭环检查
- 煤气区域作业控制与应急链路检查
## 九、核心流程图解

### 9.1 正式审查主链流水线

```
输入（Input）            正式审查主链（Formal-Review Spine）            输出 / 治理
────────── ┌────────────────────────────────────────────────────────┐ ──────────────
           │                                                        │
PDF/Fixture│  ┌───────┐     ┌───────┐     ┌───────┐                 │  ┌────────────┐
──────────►│  │ 解析  │────►│ 事实  │────►│ 规则  │                 │─►│ 工件索引   │
           │  │(Parse)│     │(Facts)│     │(Rules)│                 │  │(Artifacts) │
           │  └───┬───┘     └───┬───┘     └───┬───┘                 │  └─────┬──────┘
           │      │             │             │                     │        │
           │      ▼             ▼             ▼                     │        ▼
           │   可视域       未决事实       适用状态                   │  ┌────────────┐
           │ (visibility) (unresolved  (applicability               │  │ 审查报告   │
           │  parseMode     Facts)         State)                   │  │ (Report)   │
           │      │             │             │                     │  └─────┬──────┘
           │      ▼             ▼             ▼                     │        │
           │  ┌─────────┐   ┌────────────┐┌─────────┐              │        │
           │  │ 前置检查 │   │ 证据构建   ││ 问题种类 │              │        │
           │  │(L0 Gate)│   │ (Evidence) ││(Issues) │              │        │
           │  └────┬────┘   └─────┬──────┘└────┬────┘              │        │
           │       │              │            │                    │        │
           │       ▼              ▼            ▼                    │        ▼
           │  ┌──────────────────────────────────────┐              │  ┌────────────┐
           │  │        复核门禁（Reviewer Gate）       │              │  │ 人工裁决   │
           │  │ 需人工复核（manualReviewNeeded）→ 分流 │              │  │ (Decision) │
           │  └─────────────┬────────────────────────┘              │  └────────────┘
           │                │                                       │
           └────────────────┼───────────────────────────────────────┘
                            ▼
                 ┌───────────────────────┐
                 │   评测门禁（Eval Gate） │
                 │ 版本化用例（versioned） │
                 │ 分层指标（layered）     │
                 │ 阶段阻断（stage gate）  │
                 └───────────────────────┘
```

### 9.2 人类专家 × 系统 协作地图

```
┌──────────────────────────────────────────────────────────────────────┐
│                   人类专家 × 系统 协作地图（Collaboration Map）         │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  系统自动完成                 人工必须介入                 系统不得越权   │
│  ──────────                 ──────────                 ──────────     │
│                                                                      │
│  [解析 Parse]─────────►┌─ 可视域盲区（Visibility）─┐                   │
│  [事实 Facts]          │  · PDF 附件不可读        │◄── 人工确认        │
│  [规则 Rules]          │  · 图纸无法提取          │  "确实缺失"         │
│                        └───────────────────────┘ vs "解析器读不到"     │
│                                                                      │
│  [问题 Issue]─────────►┌─ 复核门禁（Reviewer Gate）┐                   │
│  [证据 Evidence]       │  · 可视域缺口            │◄── 人工裁决         │
│  [矩阵 Matrices]       │  · 证据缺口              │  同意/驳回/补充      │
│                        └───────────────────────┘                      │
│                                                                      │
│  [评测 Eval]──────────►┌─ 样本治理（Eval Gov.）────┐                   │
│  [指标 Metrics]        │  · 双样本人工复核裁决      │◄── 人工标注         │
│  [回放 Replay]         │  · 版本化测试用例晋升      │  专家级真相(gold)    │
│                        └───────────────────────┘                      │
│                                                                      │
│  ▼ 绝对禁区：模型不得自行签发正式结论 / 不得把"读不到"伪装成"事实缺失" ▼  │
└──────────────────────────────────────────────────────────────────────┘
```

### 9.3 Pack / DocType 治理晋升流程

```
占位符（placeholder）──► 就绪（ready）──► 实验性（experimental）──► 正式（official）
     │                    │                  │                      │
     ▼                    ▼                  ▼                      ▼
仅有骨架/模板            有可执行规则       进入评测但不进入        通过完整门禁
不参与正式审查          可被系统选中       阶段阻断（stage gate）   成为正式支持对象

晋升门禁要求：
┌─────────────────────────────────────────────────────────────────────┐
│  测试（tests）               ✓ 功能测试矩阵全面覆盖                   │
│  版本用例（versioned cases） ✓ 拥有专属、稳定的版本化黄金标准用例      │
│  政策证据（policy evidence） ✓ 条文引用准确、无虚构，结果可追溯        │
│  规则覆盖（rule coverage）   ✓ 规则实际命中率与识别率达标              │
└─────────────────────────────────────────────────────────────────────┘
```
## 十、验收与评测门槛

### 10.1 评测数据集

| 类别 | 数量 | 说明 |
|---|---|---|
| legacy CI 稳定子集 | 12 cases | 回归地板 |
| 本地完整评测池 | 30 cases | 含所有类型 |
| versioned cases | 10 cases | 含 3 个 official CI stage-gate |
| experimental versioned | 4 cases | 只进入 diagnostics |

### 10.2 Legacy 主门禁（回归地板）

| 指标 | 阈值 |
|---|---|
| issue_recall | ≥ 0.75 |
| l1_hit_rate | ≥ 0.85 |
| pack_selection_accuracy | ≥ 0.95 |
| policy_ref_accuracy | ≥ 0.75 |
| attachment_visibility_accuracy | ≥ 0.55 |
| severity_accuracy | ≥ 0.75 |
| manual_review_flag_accuracy | ≥ 0.95 |

### 10.3 Official Versioned Stage Gate（主质量门槛）

| 指标 | 阈值 |
|---|---|
| facts_accuracy | ≥ 0.90 |
| rule_hit_accuracy | ≥ 0.85 |
| hazard_identification_accuracy | ≥ 0.90 |
| attachment_visibility_accuracy | ≥ 0.90 |
| manual_review_flag_accuracy | ≥ 0.80 |

### 10.4 分层指标（Layered Metrics）

| 层级 | 覆盖范围 | 角色 |
|---|---|---|
| **L0** | visibility / parser / manual review + preflight_gate_consistency | blocking |
| **L1** | hard evidence / severity / recall | blocking |
| **L2** | facts / rule hits / policy refs + evidence_traceability | blocking |
| **L3** | remediation bucket / suggestion-defect separation | diagnostic-only |
| **CrossCutting** | pack selection + review_preparation_provenance_consistency | diagnostic |

### 10.5 回归命令

```
make test                          # 全量测试
make test-review-unit              # review 单元测试
make test-review-integration       # review 集成测试
make eval-review                   # legacy + versioned stage gate
make eval-review-ablations         # 消融实验
make eval-review-cross-pack        # 跨 pack 对比
make eval-review-cross-model       # 跨模型对比
make eval-review-replay            # 版本化回放
make smoke                         # 冒烟测试
make verify-connectivity           # 连通性验证
```

---

## 十一、已知限制

1. **DeepTutor 当前是 bridge 形态** — 复用 ChatAgent，未启动完整 RAG/KB 栈
2. **GPT Researcher 依赖较重** — 首次运行延迟高，web research 受外部搜索质量影响
3. **FastGPT Mode B 依赖 collectionId** — 无 collectionId 时优先走 Mode A
4. **SSE 断流时回退轮询** — 前端从实时流自动降级到 polling
5. **审查辅助不是正式审查结论** — `review_assist` 是 control plane 级辅助整合
6. **仅支持最小单文件输入** — 不支持多文档批处理、外部对象存储、多模态 OCR
7. **P0 正式支持范围有限** — 仅 `construction_org` 与 `hazardous_special_scheme`
8. **PDF 仍是 text-only 降级路径** — 表格/图示/附件可能落入 `unknown / attachment_unparsed`
9. **strictMode 仍是保留字段** — 当前 `reserved / no-op`，避免过度承诺
## 十二、外部参考项目与借鉴边界

| 项目 | 可借鉴 | V0.3 适用性 | 明确不借 | 借过头会偏向 |
|---|---|---|---|---|
| **OpenContracts** | 证据对象模型 / annotation / provenance | 当前可用：强化 evidence traceability | 整体协作壳、annotation-first 工作方式 | 文档标注与语料管理平台 |
| **AEC-Bench** | 评测任务设计 / scope taxonomy / replay | 当前可用：让 eval 更像可诊断基准 | multimodal benchmark 壳、agent sandbox | benchmark 平台 |
| **claude-legal-skill** | pre-review checklist / 审查前置纪律 | 当前可用：加强 reviewer gate | 法律 redline、法律文书输出壳 | 文档审阅 copilot |
| **AEC3PO** | schema discipline / 术语关系命名 | 中长期储备：命名一致性准备 | ontology-first 重构路线 | 知识工程项目 |
| **AWS RAPID** | 人在回路工作流 / 队列编排 | 长期参考：当前短板不在壳层 | 企业工作流产品化整套实现 | 工作流 SaaS |

---

## 十三、中期与长期路线图

```
时间层        主要目标                                          进入前提
────────────────────────────────────────────────────────────────────────────────
当前 V0.3     收边界 · 硬内核 · 补证据 · 强评测                  ← 当前主线
              |-- official scope 内 formal-review spine 做硬
              |-- 主攻 L0（可视域 / parser 诚实）+ L2（证据闭环）
              +-- reviewer gate + eval gate 成为正式制度
────────────────────────────────────────────────────────────────────────────────
中期          扩边界 · 补承接 · 强治理                          V0.3 主链足够硬
              |-- 更多 ready packs 通过治理晋升为 official
              |-- 补 internal-reviewed / gold 承接层
              +-- 加强 reviewer workflow / adjudication
────────────────────────────────────────────────────────────────────────────────
中远期        扩输入 · 扩文档                                    中期治理成熟
              |-- OCR / 多模态 / 图纸平台化
              +-- 多文档联合审查
────────────────────────────────────────────────────────────────────────────────
长期          扩模型 · 扩平台                                    中远期能力稳定
              |-- ontology / graph-first
              |-- 完整 workflow / 产品化
              +-- 审查控制平台级能力
────────────────────────────────────────────────────────────────────────────────
```

**关键原则**：每一层路线的进入必须以上一层主链"足够硬"为前提，不允许以"技术上做得到"替代"产品上接得住"。

---

## 十四、治理原则

1. **Anti-overfit 是长期治理原则** — 不追样本追分、不追文风追像、不追指标追高
2. **分层治理必须长期保留** — official / experimental / diagnostics / internal-reviewed / gold
3. **扩范围必须在主线足够硬之后** — 先做硬 official scope 内的 formal-review spine
4. **四层文档关系长期维护** — 研究 → 边界 → 裁决 → 实施，实施层不反写上层

---

## 十五、V0.3 成功判据

### 什么叫成功

| 判据 | 说明 |
|---|---|
| 可审前置成立 | L0 visibility / parser warnings / manual review 已前置成独立 gate |
| 可视域诚实可验证 | `attachment_visibility_accuracy` 系统性提升，来自 contract 硬度而非样本特判 |
| 证据可追溯 | facts → rules → policy refs → issues → evidence 可在 artifacts 中完整回溯 |
| 规则可命中 | `applicabilityState`、clause applicability 在 official scope 内可被 versioned cases 稳定复现 |
| 结果可复核 | reviewer gate 能显式分流"系统可判"与"需人工复核" |
| 评测可闭环 | eval gate 通过 versioned cases + layered metrics 实现 stage gate 拦截 |

### 什么不算成功

- 报告文风更像专家但证据链未变硬
- 某次样本得分更高但来自 wording 优化而非 contract 加固
- 多了更多 experimental 方向但 official scope 主链硬度未提升
- diagnostics 层指标提升被误解为 official readiness 提升

---

> 📝 **文档来源**：本 PRD 整合了 `docs/product-strategy.md`、`docs/formal-review.md`、`docs/architecture.md`、`docs/testing.md`、`docs/known-limitations.md` 的完整内容。
> 
> 📌 **维护原则**：主真相源为上述独立文档，本飞书文档为面向团队沟通的完整合并版。
