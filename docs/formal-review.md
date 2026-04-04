# structured_review 正式审查说明

## 入口参数

`structured_review` 支持以下显式参数：

- `fixtureId` / `sourceDocumentRef`（二选一）
- `documentType`
- `disciplineTags`
- `strictMode`
- `policyPackIds`

其中：

- `fixtureId` 与 `sourceDocumentRef` 会在服务端统一归一化为 `sourceDocumentRef`
- `documentType` 缺省时允许后端推断，但最终生效值必须写回 `resolvedProfile.documentType`
- `disciplineTags` 缺省时允许由事实抽取补齐
- `strictMode` 默认 `true`，但当前状态是 `reserved / no-op`
- `policyPackIds` 为空表示自动选 pack；显式传入时只会执行 `ready` packs

## 结果结构

P0 的稳定结果字段：

- `summary`
- `visibility`
- `resolvedProfile`
- `issues`
- `matrices`
- `artifactIndex`
- `reportMarkdown`
- `unresolvedFacts`

其中：

- `artifactIndex` 与 `GET /api/tasks/{taskId}/artifacts` 共享同一套官方 catalog；对新任务即使为空也视为 authoritative source
- parse 结果内部使用 typed `visibility`、`parseMode`、`parserLimited`
- `result.visibility` 是 top-level canonical visibility 对象，并直接携带 `parseWarnings`
- `summary.visibilitySummary` 仅负责总览；`matrices.attachmentVisibility` 负责结构化明细
- issue 会显式给出 `issueKind`（`hard_defect / visibility_gap / evidence_gap / enhancement`）与 `applicabilityState`
- task-detail 结果页优先以结构化 reviewer 视图呈现 `attachmentVisibility / ruleHits / conflicts / sectionStructure`，raw JSON 仅作为折叠调试信息

## 当前正式支持的文档类型

- `construction_org`
- `hazardous_special_scheme`

以下类型当前已有可执行 `ready` base packs，但 documentType 当前仅处于 experimental 范围，不作为 official gate 主支持对象：

- `construction_scheme`
- `supervision_plan`
- `review_support_material`

## 当前 pack registry

### base packs

- `construction_org.base`（ready）
- `hazardous_special_scheme.base`（ready）
- `construction_scheme.base`（ready，experimental）
- `supervision_plan.base`（ready，experimental）
- `review_support_material.base`（ready，experimental）

### scenario packs

- `lifting_operations.base`（ready）
- `temporary_power.base`（ready）
- `hot_work.base`（ready）
- `gas_area_ops.base`（ready）
- `special_equipment.base`（placeholder）
- `working_at_height.base`（placeholder）

适用边界补充：

- `lifting_operations.base` / `temporary_power.base` / `hot_work.base` 现可对 `construction_scheme` 生效
- `gas_area_ops.base` 当前仅对 `construction_org` 与 `hazardous_special_scheme` 生效
- `supervision_plan` 与 `review_support_material` 本轮仍保持 base-only

support-scope 唯一事实源：

- `GET /api/tasks/support-scope`
- 前端表单与结果页均消费该接口，而不是各写一套支持范围文案

其中：

- documentType readiness：`official | experimental | skeleton`
- pack readiness：`ready | placeholder`
- `ready pack ≠ official documentType`

## L1 / L2 / L3 语义

- **L1**：硬证据 / 可视域 / 强约束规则
- **L2**：条文适用 + 依据链完整性
- **L3**：工程推理 / 整改编排

LLM 在 P1 中只负责：

- issue title 清洗
- recommendation 生成
- 候选 issue 去重合并

LLM 不负责：

- L1 命中判断
- 条文适用基础判定
- 生成不存在的文档/法规证据

## artifact API

- `POST /api/uploads/documents`
- `GET /api/tasks/support-scope`
- `GET /api/tasks/{taskId}/artifacts`
- `GET /api/tasks/{taskId}/artifacts/{artifactName}`
- `PUT /api/tasks/{taskId}/reviewer-decision`

典型工件包括：

- `structured-review-parse.json`
- `structured-review-l0-visibility.json`
- `structured-review-facts.json`
- `structured-review-rule-hits.json`
- `structured-review-candidates.json`
- `structured-review-result.json`
- `structured-review-report-buckets.json`
- `structured-review-report.md`
- `hazard-identification-matrix.json`
- `rule-hit-matrix.json`
- `conflict-matrix.json`
- `attachment-visibility-matrix.json`
- `section-structure-matrix.json`

## manual review 语义

- `manualReviewNeeded` 是唯一 canonical 布尔语义
- `whetherManualReviewNeeded` 仅保留给 legacy task replay 的只读兼容层
- `FinalIssue` 会保留 `evidenceMissing` 与 `manualReviewReason`
- `FinalIssue.issueKind` 与 `FinalIssue.applicabilityState` 是 reviewer / report / eval 共享的最小派生语义
- `result.visibility` 是唯一 canonical visibility contract
- `summary.visibilitySummary` 会统一输出附件计数、状态计数、reason counts、重复章节与 parse warnings，但不再反向生成 canonical visibility
- reviewer decision 以单个 task-scoped JSON 保存：`taskState + note + issues[] + attachments[] + updatedAt`
- `disable_visibility_check` 仅保留给 eval / ablation 内部路径

PDF 仍保持 `pdf_text_only + parserLimited=True` 的受限路径；本轮只新增轻量结构提示，不引入 OCR / 多模态：

- `pdf_appendix_title_candidates:<n>`
- `pdf_table_caption_candidates:<n>`
- `pdf_figure_caption_candidates:<n>`

这些 warning 只表达“可视域受限 / 结构提示”，不能被解释为“正文或附件缺失”。

以下情况必须保留人工复核标记：

- `visibility_gap`
- `attachment_unparsed`
- `referenced_only`
- evidence 不足以形成硬缺陷时

系统不得把“没读到附件”直接写成“附件缺失”。

## 评测数据集

`fixtures/review_eval/` 当前包含：

- legacy CI 稳定子集：12 cases
- 数据集总量：30 cases
- versioned cases：10 cases
- 其中 versioned official stage-gate cases：3 cases
- 其余新增 versioned cases 为 experimental diagnostics，不进入 blocking official gate

当前 `make eval-review` 同时要求：

- legacy 主门禁通过
- official versioned stage gate 通过：
  - `facts_accuracy >= 0.90`
  - `rule_hit_accuracy >= 0.85`
  - `hazard_identification_accuracy >= 0.90`
  - `attachment_visibility_accuracy >= 0.90`
  - `manual_review_flag_accuracy >= 0.80`

主命令：

```bash
make eval-review
make eval-review-ablations
make eval-review-cross-pack
make eval-review-cross-model
```

评测输出会额外提供 `layeredMetrics`：

- `L0`：visibility / parser / manual review
- `L1`：hard evidence / severity / recall
- `L2`：facts / rule hits / policy refs
- `L3`：remediation bucket consistency / suggestion-defect separation（当前为 diagnostic-only）
- `CrossCutting`：pack selection
