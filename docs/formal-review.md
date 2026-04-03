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
- `resolvedProfile`
- `issues`
- `matrices`
- `artifactIndex`
- `reportMarkdown`
- `unresolvedFacts`

其中：

- `artifactIndex` 与 `GET /api/tasks/{taskId}/artifacts` 共享同一套官方 catalog
- parse 结果内部使用 typed `visibility`、`parseMode`、`parserLimited`
- `summary.visibilitySummary` 负责总览；`matrices.attachmentVisibility` 负责结构化明细

## 当前正式支持的文档类型

- `construction_org`
- `hazardous_special_scheme`

以下类型暂时只提供 pack 骨架与 registry 覆盖，不作为 P1 主支持对象：

- `construction_scheme`
- `supervision_plan`
- `review_support_material`

## 当前 pack registry

### base packs

- `construction_org.base`（ready）
- `hazardous_special_scheme.base`（ready）
- `construction_scheme.base`（placeholder）
- `supervision_plan.base`（placeholder）
- `review_support_material.base`（placeholder）

### scenario packs

- `lifting_operations.base`（placeholder）
- `temporary_power.base`（placeholder）
- `hot_work.base`（placeholder）
- `gas_area_ops.base`（placeholder）
- `special_equipment.base`（placeholder）
- `working_at_height.base`（placeholder）

支持范围事实源：

- `GET /api/tasks/support-scope`
- 前端表单与结果页均消费该接口，而不是各写一套支持范围文案

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

典型工件包括：

- `structured-review-parse.json`
- `structured-review-facts.json`
- `structured-review-rule-hits.json`
- `structured-review-candidates.json`
- `structured-review-result.json`
- `structured-review-report.md`
- `hazard-identification-matrix.json`
- `rule-hit-matrix.json`
- `conflict-matrix.json`
- `attachment-visibility-matrix.json`
- `section-structure-matrix.json`

## manual review 语义

- `manualReviewNeeded` 是唯一 canonical 布尔语义
- `whetherManualReviewNeeded` 仅保留兼容 alias
- `FinalIssue` 会保留 `evidenceMissing` 与 `manualReviewReason`
- `summary.visibilitySummary` 会统一输出附件计数、状态计数、reason counts、重复章节与 parse warnings

以下情况必须保留人工复核标记：

- `visibility_gap`
- `attachment_unparsed`
- `referenced_only`
- evidence 不足以形成硬缺陷时

系统不得把“没读到附件”直接写成“附件缺失”。

## 评测数据集

`fixtures/review_eval/` 当前包含：

- legacy CI 稳定子集：12 cases
- 数据集总量：26 cases
- versioned cases：6 cases
- 其中 versioned official stage-gate cases：3 cases

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
