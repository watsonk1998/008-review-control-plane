# Latest Eval Summary

## 执行环境
- 生成时间：2026-04-05T00:51:14+08:00
- 仓库：`/Users/lucas/repos/review/008-review-control-plane`
- 分支：`main`
- commit：`ac8019195d5e333732bfb3d81daedad43cc6688e`
- git dirty：yes
- 是否使用了本地修改：是
- 本地修改列表：["?? scripts/build_research_pack.py"]
- LLM 模式：`configured`
- 关键命令：`make eval-review` / `make eval-review-ablations` / `make eval-review-cross-pack` / `make eval-review-cross-model`

## 四个命令执行结果

### eval-review
- 状态：成功（exit 0）
- 日志：`/Users/lucas/repos/review/008-review-control-plane/artifacts/research-pack/logs/eval-review.log`
- JSON：`/Users/lucas/repos/review/008-review-control-plane/artifacts/research-pack/eval/eval-review.json`
- legacy baseline：通过
- official versioned stage gate：通过
- facts_accuracy：1.0000
- rule_hit_accuracy：1.0000
- hazard_identification_accuracy：1.0000
- attachment_visibility_accuracy：0.5833
- manual_review_flag_accuracy：0.9722
- 主结果 passed：True
- legacy 失败项：无
- stage gate 失败项：无

### eval-review-ablations
- 状态：成功（exit 0）
- 日志：`/Users/lucas/repos/review/008-review-control-plane/artifacts/research-pack/logs/eval-review-ablations.log`
- JSON：`/Users/lucas/repos/review/008-review-control-plane/artifacts/research-pack/eval/eval-review-ablations.json`
- 变体：baseline, disable_llm_explanation, disable_normalizer, disable_rule_engine, disable_visibility_check
- baseline facts_accuracy：0.9318
- baseline rule_hit_accuracy：0.9273

### eval-review-cross-pack
- 状态：成功（exit 0）
- 日志：`/Users/lucas/repos/review/008-review-control-plane/artifacts/research-pack/logs/eval-review-cross-pack.log`
- JSON：`/Users/lucas/repos/review/008-review-control-plane/artifacts/research-pack/eval/eval-review-cross-pack.json`
- auto pack_selection_accuracy：1.0000
- expected_packs_forced pack_selection_accuracy：1.0000

### eval-review-cross-model
- 状态：成功（exit 0）
- 日志：`/Users/lucas/repos/review/008-review-control-plane/artifacts/research-pack/logs/eval-review-cross-model.log`
- JSON：`/Users/lucas/repos/review/008-review-control-plane/artifacts/research-pack/eval/eval-review-cross-model.json`
- deterministic facts_accuracy：0.9318
- fallback facts_accuracy：0.9318

## 主评测摘要
- legacy baseline 是否通过：是
- official versioned stage gate 是否通过：是
- 主评测总开关 passed：True
- facts_accuracy：1.0000
- rule_hit_accuracy：1.0000
- hazard_identification_accuracy：1.0000
- attachment_visibility_accuracy：0.5833
- manual_review_flag_accuracy：0.9722
- versioned stage aggregate：{"issue_recall": 1.0, "l1_hit_rate": 1.0, "high_severity_issue_recall": 1.0, "pack_selection_accuracy": 1.0, "policy_ref_accuracy": 1.0, "attachment_visibility_accuracy": 1.0, "severity_accuracy": 1.0, "manual_review_flag_accuracy": 1.0, "hard_evidence_accuracy": 1.0, "facts_accuracy": 1.0, "rule_hit_accuracy": 1.0, "hazard_identification_accuracy": 1.0, "suggestion_defect_separation": 1.0, "remediation_bucket_consistency": 1.0}

## Layered Metrics
### L0
- attachment_visibility_accuracy: 0.5833
- manual_review_flag_accuracy: 0.9722
### L1
- issue_recall: 0.7542
- l1_hit_rate: 0.8889
- high_severity_issue_recall: 1.0000
- hard_evidence_accuracy: 0.6945
- severity_accuracy: 0.7542
### L2
- facts_accuracy: 1.0000
- rule_hit_accuracy: 1.0000
- policy_ref_accuracy: 0.7542
- hazard_identification_accuracy: 1.0000
### L3
- suggestion_defect_separation: 0.7542
- remediation_bucket_consistency: 1.0000
- diagnosticOnly: true
### CrossCutting
- pack_selection_accuracy: 1.0000

## 异常与风险
- 四个 eval 命令均成功返回。
- PDF 解释边界： parseMode=pdf_text_only, parserLimited=True, 仅代表可视域受限，不代表文档或附件缺失。
