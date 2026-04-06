# review_eval

本目录存放 `008-review-control-plane` 的结构化评测样本池（golden pool）。

## 当前状态
当前新增的版本化样本均为 bootstrap 数据，不是最终专家确认 gold truth。

## 目录约定
- 现有 `case_XXX/metadata.json` 目录：legacy evaluator dataset，保持不变
- 新增 `<doc_type>/<domain>/<case_id>/<version>/`：版本化 bootstrap golden pool

## 版本语义
- `v0.1.0-gemini-seed`：基于 Gemini deepresearch 结果构建的 seed labels
- `v0.1.0-bootstrap-seed`：从既有 legacy / fixture 样本转换出的最小 versioned seed
- `v0.1.0-ci-stage-gate`：进入 official versioned stage gate 的运行时对齐样本
- `v0.2.0-internal-reviewed`：内部人工复核后的版本
- `v1.0.0-expert-golden`：专家确认后的正式 gold 版本

## truth layering / promotion discipline

- `seed` 只能作为研究输入与候选标签来源，不能直接视为 reviewed truth
- `internal-reviewed preparation` 是 reviewer / artifact / eval 之间的承接层，不等于 `v0.2.0-internal-reviewed`
- runtime review-preparation 现在必须显式区分 promotion disposition：`eligible / deferred / rejected`
- summary 层必须同步暴露 `issueBlockingReasons / attachmentBlockingReasons`，asset 层必须为每条记录输出 `promotionBlockingReasons`
- promotion 必须至少区分：
  - issue truth
  - visibility truth
  - evidence truth
  - enhancement-only observations
- visible-scope 内已闭合的负向事实可以进入 issue truth；parser-limited 导致的章节/事实缺口只能保留为 explainable `evidence_gap`
- 若 case 仍存在 `parser_limited_pdf_requires_manual_review`、`attachment_unparsed`、`referenced_only` 等 blocking 语义，只能进入 reviewed-preparation，不得直接宣称完成 reviewed promotion
- provenance 必须能回指 seed / reviewer decision / artifacts；不得把最新一次 eval snapshot 当作长期 truth
- attachment 侧若 reviewer 仍确认 visibility gap 成立，应落入 `rejected` disposition，并在 summary 中进入 `rejectedAttachmentIds`
- runtime 侧的 `GET /api/tasks/{taskId}/review-preparation` 只负责导出 reviewed-preparation 候选资产；是否写入 `fixtures/review_eval/**` 仍需人工筛选与复核
- provenance tier 只能通过精确 case identity 命中版本化 metadata；source-path-only runtime task 必须保持 `runtime_only`
- reviewer confirm 不能把 `visibility_gap / evidence_gap / blocked_* / manualReviewNeeded / evidenceMissing` issue 直接提升为 promotable truth；这些 blocker 必须在 summary/asset 中可回放
- runtime provenance 的 `sourceTier` 当前固定映射：
  - `v0.1.0-gemini-seed -> seed`
  - `v0.1.0-bootstrap-seed -> bootstrap_seed`
  - `v0.1.0-ci-stage-gate -> ci_stage_gate`
  - `v0.2.0-internal-reviewed -> internal_reviewed`
  - `v1.0.0-expert-golden -> expert_golden`
  - 未命中版本化 metadata -> `runtime_only`

## 非协商原则
1. 不得把 Gemini 结果直接当作专家 truth
2. 必须区分 issue truth 与 visibility truth
3. 必须显式记录 provenance
4. 不得把“未解析附件”直接标成“缺失”
5. internal-reviewed preparation 只是准备层，不得冒充 internal-reviewed

## 当前已初始化 case
- construction_org / electromechanical / cn_baosteel_coldrolling_crane_230235 / v0.1.0-gemini-seed
- construction_org / municipal / cn_puhua_rainwater_storage_pool / v0.1.0-gemini-seed
- hazardous_special_scheme / lifting / cn_hazardous_special_scheme_md_missing_core_001 / v0.1.0-bootstrap-seed
- construction_scheme / general / cn_construction_scheme_attachment_gap_001 / v0.1.0-bootstrap-seed
- supervision_plan / general / cn_supervision_plan_monitoring_gap_001 / v0.1.0-bootstrap-seed
- review_support_material / context / cn_review_support_material_context_only_001 / v0.1.0-bootstrap-seed
- construction_org / industrial / cn_construction_org_gas_area_ops_001 / v0.1.0-bootstrap-seed

## 当前评测池概览

- legacy CI 稳定子集：12 cases
- 全量评测池：30 cases
- versioned cases：10 cases
- official CI stage-gate versioned cases：3 cases
- 新增的 4 个 bootstrap-seed versioned cases 当前只进入 experimental diagnostics，不自动提升 skeleton documentType 为 official gate
