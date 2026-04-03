# review_eval

本目录存放 `008-review-control-plane` 的结构化评测样本池（golden pool）。

## 当前状态
当前新增的版本化样本均为 bootstrap 数据，不是最终专家确认 gold truth。

## 目录约定
- 现有 `case_XXX/metadata.json` 目录：legacy evaluator dataset，保持不变
- 新增 `construction_org/<domain>/<case_id>/<version>/`：版本化 bootstrap golden pool

## 版本语义
- `v0.1.0-gemini-seed`：基于 Gemini deepresearch 结果构建的 seed labels
- `v0.2.0-internal-reviewed`：内部人工复核后的版本
- `v1.0.0-expert-golden`：专家确认后的正式 gold 版本

## 非协商原则
1. 不得把 Gemini 结果直接当作专家 truth
2. 必须区分 issue truth 与 visibility truth
3. 必须显式记录 provenance
4. 不得把“未解析附件”直接标成“缺失”

## 当前已初始化 case
- construction_org / electromechanical / cn_baosteel_coldrolling_crane_230235 / v0.1.0-gemini-seed
- construction_org / municipal / cn_puhua_rainwater_storage_pool / v0.1.0-gemini-seed
