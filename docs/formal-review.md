# structured_review 正式审查说明

## 入口参数

`structured_review` 支持以下显式参数：

- `documentType`
- `disciplineTags`
- `strictMode`
- `policyPackIds`

其中：

- `documentType` 缺省时允许后端推断，但最终生效值必须写回 `resolvedProfile.documentType`
- `disciplineTags` 缺省时允许由事实抽取补齐
- `strictMode` 默认 `true`
- `policyPackIds` 为空表示自动选 pack；显式传入时会在基础 pack 之外补齐

## 结果结构

P0 的稳定结果字段：

- `summary`
- `resolvedProfile`
- `issues`
- `matrices`
- `artifactIndex`
- `reportMarkdown`
- `unresolvedFacts`

其中 `artifactIndex` 是前端下载工件的唯一可信入口，避免 UI 直接依赖本地绝对路径。

## 当前正式支持的文档类型

- `construction_org`
- `hazardous_special_scheme`

以下类型暂时只提供 pack 骨架与 registry 覆盖，不作为 P1 主支持对象：

- `construction_scheme`
- `supervision_plan`
- `review_support_material`

## 当前 pack registry

### base packs

- `construction_org.base`
- `hazardous_special_scheme.base`
- `construction_scheme.base`
- `supervision_plan.base`
- `review_support_material.base`

### scenario packs

- `lifting_operations.base`
- `temporary_power.base`
- `hot_work.base`
- `gas_area_ops.base`
- `special_equipment.base`
- `working_at_height.base`

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

- `GET /api/tasks/{taskId}/artifacts`
- `GET /api/tasks/{taskId}/artifacts/{artifactName}`

典型工件包括：

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

- CI 稳定子集：12 cases
- legacy 完整评测池：20 cases
- additive versioned bootstrap cases：`construction_org` 2 个、`hazardous_special_scheme` 1 个

主命令：

```bash
make eval-review
make eval-review-ablations
make eval-review-cross-pack
make eval-review-cross-model
```
