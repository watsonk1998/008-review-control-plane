---
entity_type: document
doc_type: prd_validation
report_type: validation
time_key: 2026-04-07
canonical_name: 008-review-control-plane-full-prd
created: 2026-04-07
updated: 2026-04-07
engram_topic_key: 008_formal_review_prd
severity_blocker_count: 1
severity_major_count: 2
severity_minor_count: 1
---

> [!NOTE]
> **本文档职责**
> - 负责：
>   - 记录 PRD 相关验证过程、结论与验证发现
> - 不负责：
>   - 不作为产品主定义
>   - 不作为当前 V1 能力边界或验收标准的主真相源
> - 主适用读者：
>   - 产品负责人、评审人员、协作者
> - 冲突处理：
>   - 涉及当前正式定义时，以 product / governance 层主文档为准
> - 文档状态：
>   - 派生产物 / 验证纪要

---

# PRD Validation Report for 008 审查控制面完整 PRD (V0.3)

## 1. Executive Summary
- **Overall**: Needs Improvement (Conditional Pass for Development, but requires schema/state-machine hardening)
- **Top risks**: 
  1. `visibility_gap` 与 `evidence_gap` 在 parser-limited 场景下的判定边界存在轻微重叠和逻辑冲突。
  2. Reviewer 状态机的变更权限（UI 侧是否允许修改 `issueKind`）未在 PRD 中严格锁死，存在破坏证据链追溯的风险。

## 2. Critical Issues (Blockers)

| ID | Category | Issue | Why it matters | Fix |
|---|---|---|---|---|
| BLK-01 | Logical Completeness | 概念重叠：`visibility_gap` vs `evidence_gap` 在 parser-limited 场景下界限不清。PRD 中指出 "parser-limited... 的负向结论才进入 evidence_gap + blocked_by_missing_fact"，但同时又单列了 `visibility_gap` 为需人工复核项。 | 如果一个 PDF 表格无法解析，系统到底应该将其抛出为 `visibility_gap` 还是抛出为 `evidence_gap` + `blocked_by_missing_fact`？如果底层引擎同时抛出，会导致 issue 重复或状态不一致，影响下游 eval gate 的 `attachment_visibility_accuracy` 和 `hard_evidence_accuracy` 的清晰计算。 | 明确互斥与派生关系：在 L0 阶段只判定 `visibility_gap`。在 L1/L2 阶段，如果因为 `visibility_gap` 导致事实缺失，则该特定 Issue 标记为 `blocked_by_visibility`（而非单纯的 missing_fact）。`evidence_gap` 仅保留给：事实提取正常、但文档的确没有提供支持性证据的场景。 |

## 3. Detailed Analysis

### 3.1 AI-Readability
- **优点**：PRD 结构极其严谨，采用了如 `manualReviewNeeded` 为 "唯一的 canonical 布尔语义"，`artifactIndex` 为 "authoritative source"，这种命名和规范极大地提升了系统设计的无二义性和大模型（AI Agent）的可读性。
- **缺点**：缺少对于 `unresolvedFacts` 内部嵌套字段的 JSON Schema 可视化表达。虽然提到了 `sourceExtractor`，`blockingReason` 等，但在多智能体协作时，缺乏静态 Schema 会导致实现偏差。

### 3.2 Industry Standards
- **合理性**：严格限制 V0.3 放弃 OCR 和多模态，以及不做图纸平台化，是非常硬核且负责任的工程决策，完全符合安全与可靠性审查系统的渐进式演进路径。
- **风险**：(Minor) `strictMode` 被标记为保留字段且 `no-op`。为了防止外部 API 消费者（或 Agent）传入 `strictMode=true` 并错误认为系统进行了强合规检查，API 应显式抛出 warning `strictMode is currently a no-op`，而不能仅在文档中声明。

### 3.3 Logical Completeness
- 见 BLK-01。正式结构化主链 `parse → facts → rules → evidence → report` 在逻辑闭环上已经非常成熟，但在异常传播（Exception Propagation）路径上，从 parse 异常如何映射到 evidence gap 需要绝对唯一的路由表。

### 3.4 Edge Cases
- **重大风险 (Major)**：未说明多重并发规则导致的证据冲突如何处理。例如，当 "停机窗口压力" (rule A) 命中，同时 "高风险作业挂接" (rule B) 也命中且基于相同的缺失事实。PRD 需要明确 Candidate issues 的去重合并逻辑（在 L3 LLM 中提及，但需要指出具体的去重 Primary Key 是什么）。

### 3.5 UI/UX Consistency
- **重大风险 (Major)**：PRD 声明 "reviewer cockpit 的 UI 文案会将稳定的 on-wire enum 映射为 reviewer 语义... 但不改变持久化字段"。但是，Reviewer 是否有权限在 UI 层覆盖推翻 `issueKind`（例如把系统判定的 `evidence_gap` 强行改为 `hard_defect`）？如果允许，则底层 SQLite 和 artifact 证据链会被破坏；如果不允许，只能变更 `disposition`，则应该在 PRD 中明确 "UI 严禁发生 IssueKind 状态转移（State Transition），只能追加 Reviewer Disposition"。

## 4. Optimized Spec Proposal

针对 L0 到 L2 异常传播与 `gap` 的区分，重写该部分的约束规范，使用 implementation-ready 的语言：

### 建议增补章节：缺陷类型与阻断原因的互斥状态机 (State Machine for Gap Classification)
> "系统保证所有的负向审查结论必须且只能归属以下三种互斥的终态之一：
> 1. **Visibility Gap (`visibility_gap`)**：根因在 L0（如 PDF 插件未解析、加密、图纸无法提取）。对应事实提取被阻断，下游的规则判定结果强制标记为 `blocked_by_visibility` 并挂起人工复核。
> 2. **Evidence Gap (`evidence_gap`)**：L0 解析成功且可视，但内容中缺乏满足该规则的逻辑闭环（例如：缺少具体责任人，缺少监测机制细节）。对应标记为 `blocked_by_missing_fact`，并阐明 `missingFactKeys`，挂起人工补充依据。
> 3. **Hard Defect (`hard_defect`)**：L0 解析成功且可视，且提取到的事实与法规硬约束明确冲突（例如：规定需双人复核，事实显示单人负责）。直接标记为缺陷。
> 
> UI 层 Reviewer 介入时，**系统冻结原始 `issueKind` 不可被修改**，Reviewer 的裁决仅在 `disposition`（eligible, deferred, rejected）层面进行追加，并伴随 `reviewerNote` 留存，保障事实-证据链不被篡改。"

## 5. Structured Fields
- `[entry_type:: prd_validation]`
- `[time_key:: 2026-04-07]`
- `[severity_blocker_count:: 1]`
- `[severity_major_count:: 2]`
- `[severity_minor_count:: 1]`
- `[source_path:: /Users/lucas/repos/review/008-review-control-plane/docs/90-archive/prd-index.md]`
