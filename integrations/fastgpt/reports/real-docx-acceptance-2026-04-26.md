# FastGPT 真实方案验收结果

- 验收时间：2026-04-26T12:04:03.573Z
- Chat URL：https://xtaiqa.jg-pm.com/api/v1/chat/completions
- Key 指纹：openapi-...r8dHNp
- 原始响应目录：`/tmp/hermes-fastgpt-real-acceptance-20260426`

## 结论

| 案例 | documentType | 出口 | 是否通过 | contentLength | nodeErrors |
|---|---|---:|---:|---:|---:|
| 停电施工方案-威彦达 | `distribution_network_special_scheme` | formal | PASS | 424 | 0 |
| 施工组织设计-冷轧厂2030单元三台行车电气系统改造 | `construction_org` | formal | PASS | 425 | 0 |

## 节点链

### 停电施工方案-威彦达

- workflowStart / workflowStart / 流程开始 / error=null
- normalizeInput / code / 归一化输入 / error=null
- callReviewContextWft / pluginModule / 调用 hermes_review_context_wft / error=null
- callAiReviewWft / pluginModule / 调用 hermes_ai_review_wft / error=null
- callDeterministicWft / pluginModule / 调用 hermes_deterministic_review_wft / error=null
- callSupportWft / pluginModule / 调用 hermes_support_008_wft / error=null
- callFinalAssemblerWft / pluginModule / 调用 hermes_final_assembler_wft / error=null
- routeFinalReply / ifElseNode / 判断是否降级 / error=null
- formalReply / answerNode / 正式报告输出 / error=null

检查项：
- chineseNonEmpty: PASS
- formalOrDegradedReply: PASS
- responseDataNoNodeErrors: PASS
- businessSignals: PASS
- riskSignals: PASS
- evidenceBoundarySignals: PASS
- remediationOrManualReviewSignals: PASS

正文预览：

```text

# 配网停电施工专项方案正式审查报告

本次审查已由专业主审组件裁决完成，总体评级结论为：**需要修改**。

## 重点风险
- 计算书与验算依据缺失
- 附件及图纸解析受限，请结合原件复核

## 关键问题
- [medium] 计算书与验算依据缺失：文档中虽包含风险评估公式及风险值计算过程（如制作电缆中间头风险值60，户内终端头安装作业风险值50），但未提供具体的电气参数选型计算、电缆截面热稳定校验或机械强度验算等关键计算书。根据审查规则，未看到详细计算书时不得臆造错误，判定为证据不足。
- [medium
```

### 施工组织设计-冷轧厂2030单元三台行车电气系统改造

- workflowStart / workflowStart / 流程开始 / error=null
- normalizeInput / code / 归一化输入 / error=null
- callReviewContextWft / pluginModule / 调用 hermes_review_context_wft / error=null
- callAiReviewWft / pluginModule / 调用 hermes_ai_review_wft / error=null
- callDeterministicWft / pluginModule / 调用 hermes_deterministic_review_wft / error=null
- callSupportWft / pluginModule / 调用 hermes_support_008_wft / error=null
- callFinalAssemblerWft / pluginModule / 调用 hermes_final_assembler_wft / error=null
- routeFinalReply / ifElseNode / 判断是否降级 / error=null
- formalReply / answerNode / 正式报告输出 / error=null

检查项：
- chineseNonEmpty: PASS
- formalOrDegradedReply: PASS
- responseDataNoNodeErrors: PASS
- businessSignals: PASS
- riskSignals: PASS
- evidenceBoundarySignals: PASS
- remediationOrManualReviewSignals: PASS

正文预览：

```text

# 施工组织设计正式审查报告

本次审查已由专业主审组件裁决完成，总体评级结论为：**需要修改**。

## 重点风险
- 计算书与验算依据缺失
- 附件及图纸解析受限，请结合原件复核
- 编制依据现行有效性核验

## 关键问题
- [medium] 计算书与验算依据缺失：文档中虽包含汽车吊选型计算过程，但缺乏完整的专项方案计算书（如临时用电负荷计算、起重吊装稳定性详细验算等）及支撑性附件。文档解析提示正文多处引用附件或附图，当前仅获得正文文本，无法验证计算参数的原始来源及完整性。
- [medium] 附件及
```

