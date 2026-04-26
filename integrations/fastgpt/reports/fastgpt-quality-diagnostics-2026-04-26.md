# FastGPT 审查质量诊断报告

- 生成时间：2026-04-26T12:53:30.355Z
- 原始 flowResponses/getResData JSON 不写入 repo；本报告仅保存脱敏摘要。
- 若 evidenceLevel 为 `summary-only`，说明输入缺少完整后台流日志，token、耗时、reviewer 分包和 traceability 只能标记为证据不足。
- 本轮已用用户临时提供的 FastGPT key 对 `https://xtaiqa.jg-pm.com/api/v1/chat/completions` 做 `detail=true` 身份探测：命中 Hermes 主工作流节点链（`normalizeInput -> callReviewContextWft -> callAiReviewWft -> callFinalAssemblerWft`）。由于仍缺主应用 AppId，本轮未调用后台 `getHistories/getResData` 导出完整 flowResponses。

## 总览

| 输入 | evidenceLevel | nodes | nodeErrors | selectedReviewers | reviewerPackets | finalLength | traceability |
|---|---:|---:|---:|---:|---:|---:|---:|
| real-docx-power-outage-summary-2026-04-26.json | summary-only | 9 | 0 | 0 | 0 | 260 | 0 |
| real-docx-construction-org-summary-2026-04-26.json | summary-only | 9 | 0 | 0 | 0 | 260 | 0 |

## real-docx-power-outage-summary-2026-04-26.json

### 节点耗时 / 模型 / Token

- 数据不足：输入中未发现节点耗时、模型或 token 字段。

### Reviewer 分包

- 数据不足：输入中未发现 reviewerPackets/packets。

### 模块有效结论

| module | reviewerCount | degradedCount | findings | effectiveByFinding |
|---|---:|---:|---:|---:|
| structure_completeness | 0 | 0 | 0 | NO |
| parameter_consistency | 0 | 0 | 0 | NO |
| legality_compliance | 0 | 0 | 0 | NO |
| execution_continuity | 0 | 0 | 0 | NO |
| evidence_validation | 0 | 0 | 0 | NO |

### 最终输出

- 字符数：260
- traceability 条目数：0

```text

# 配网停电施工专项方案正式审查报告

本次审查已由专业主审组件裁决完成，总体评级结论为：**需要修改**。

## 重点风险
- 计算书与验算依据缺失
- 附件及图纸解析受限，请结合原件复核

## 关键问题
- [medium] 计算书与验算依据缺失：文档中虽包含风险评估公式及风险值计算过程（如制作电缆中间头风险值60，户内终端头安装作业风险值50），但未提供具体的电气参数选型计算、电缆截面热稳定校验或机械强度验算等关键计算书。根
```

## real-docx-construction-org-summary-2026-04-26.json

### 节点耗时 / 模型 / Token

- 数据不足：输入中未发现节点耗时、模型或 token 字段。

### Reviewer 分包

- 数据不足：输入中未发现 reviewerPackets/packets。

### 模块有效结论

| module | reviewerCount | degradedCount | findings | effectiveByFinding |
|---|---:|---:|---:|---:|
| structure_completeness | 0 | 0 | 0 | NO |
| parameter_consistency | 0 | 0 | 0 | NO |
| legality_compliance | 0 | 0 | 0 | NO |
| execution_continuity | 0 | 0 | 0 | NO |
| evidence_validation | 0 | 0 | 0 | NO |

### 最终输出

- 字符数：260
- traceability 条目数：0

```text

# 施工组织设计正式审查报告

本次审查已由专业主审组件裁决完成，总体评级结论为：**需要修改**。

## 重点风险
- 计算书与验算依据缺失
- 附件及图纸解析受限，请结合原件复核
- 编制依据现行有效性核验

## 关键问题
- [medium] 计算书与验算依据缺失：文档中虽包含汽车吊选型计算过程，但缺乏完整的专项方案计算书（如临时用电负荷计算、起重吊装稳定性详细验算等）及支撑性附件。文档解析提示正文多处引用附件或附图，当前仅
```
