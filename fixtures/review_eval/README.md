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
- `v0.2.0-internal-reviewed`：内部人工复核后的版本
- `v1.0.0-expert-golden`：专家确认后的正式 gold 版本

## truth layering / promotion discipline

- `seed` 只能作为研究输入与候选标签来源，不能直接视为 reviewed truth
- `internal-reviewed preparation` 是 reviewer / artifact / eval 之间的承接层，不等于 `v0.2.0-internal-reviewed`
- promotion 必须至少区分：
  - issue truth
  - visibility truth
  - evidence truth
  - enhancement-only observations
- 若 case 仍存在 `parser_limited_pdf_requires_manual_review`、`attachment_unparsed`、`referenced_only` 等 blocking 语义，只能进入 reviewed-preparation，不得直接宣称完成 reviewed promotion
- provenance 必须能回指 seed / reviewer decision / artifacts；不得把最新一次 eval snapshot 当作长期 truth

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
