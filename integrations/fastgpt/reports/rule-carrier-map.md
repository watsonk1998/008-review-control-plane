# FastGPT 审查规则承载地图

生成日期：2026-04-26

## 维护边界

当前 FastGPT 迁移形态是 `workflow+workflow-tools`：

- 主工作流只负责输入归一化、文件 URL 显式传递、6 个工作流工具编排、正式/降级出口。
- 规则、依据、模板、模块绑定主要在工作流工具内承载。
- repo 仍是再生成来源；平台侧是同事日常维护入口。平台改动后必须导出 workflow JSON 回存，避免平台和 repo 漂移。

## 链路地图

| 层 | 节点/工具 | 承载内容 | 维护方式 | 平台侧可维护性 |
|---|---|---|---|---|
| 主工作流 | `normalizeInput` | `documentType`、`enabledModules`、`strictMode`、用户文件 URL 数组归一化 | code node | 低：只允许调变量默认值，不建议改编排 |
| 主工作流 | `callReviewConfigWft` | 调用 `hermes_review_config_wft`，解析文档类型注册表与方案类型配置 | pluginModule | 中：配置工具内维护，主工作流只维护工具 ID 绑定 |
| 主工作流 | `callReviewContextWft` | 调用 `hermes_review_context_wft`，传入文件 URL 与归一化变量 | pluginModule | 低：只维护工具 ID 绑定 |
| 主工作流 | `callAiReviewWft` | 调用 AI 主审工具 | pluginModule | 低：只维护工具 ID 绑定 |
| 主工作流 | `callDeterministicWft` | 调用确定性审查工具 | pluginModule | 低：只维护工具 ID 绑定 |
| 主工作流 | `callSupportWft` | 调用 008 支撑层工具 | pluginModule | 低：只维护工具 ID 绑定 |
| 主工作流 | `callFinalAssemblerWft` | 调用最终组装工具 | pluginModule | 低：只维护工具 ID 绑定 |
| 主工作流 | `formalReply` / `degradedReply` | 正式报告或 fail-closed 降级结果出口 | answerNode | 中：可维护展示文本，但不得改变正式/降级语义 |

## 工作流工具承载

| 工作流工具 | 主要节点 | 承载内容 | 类型 |
|---|---|---|---|
| `hermes_review_config_wft` | `resolveReviewConfig` | `document_type_registry`、`scheme_config__{documentType}`、reviewerConfigs、riskFocus、modelPolicy、outputContract | code 常量 + 平台配置入口 |
| `hermes_review_context_wft` | `readTargetFiles` | FastGPT 文档解析节点，读取 `targetFileUrls` | 文件读取 |
| `hermes_review_context_wft` | `buildReviewContext` | `GOVERNANCE_SNAPSHOT`、`DATASET_MANIFEST`、`basisRegistry`、`packRegistry`、`templateManifest`、profile 解析、候选规则生成 | code 常量 + governance 快照 |
| `hermes_ai_review_wft` | `prepareAiReview` | 按 `enabledModules`、`documentType`、配置工具 reviewerConfigs 和模板 `supported_document_types` 选择 reviewer，并生成模块分组 prompt | code 常量 + config + template manifest |
| `hermes_ai_review_wft` | `runStructureReview` / `runParameterReview` / `runLegalityReview` / `runExecutionReview` / `runEvidenceReview` | 按模块分组执行 reviewer prompt 与结构化 JSON 主审要求 | prompt |
| `hermes_ai_review_wft` | `normalizeAiReview` | 归一化 AI 输出，对缺失 reviewer 做 degrade | code 常量 |
| `hermes_deterministic_review_wft` | `runDeterministicReview` | 规范现行有效性、可视域缺口、计算审查兜底等确定性 finding | deterministic code |
| `hermes_support_008_wft` | `buildSupport008` | 008 支撑层线索、证据索引、supportPacket | code |
| `hermes_final_assembler_wft` | `assembleFinalDecision` | fail-closed、模块门禁、最终评级、正式/降级报告组装 | deterministic code |

## 文档类型规则入口

| documentType | 方案类型 | 主要 profile / pack 来源 | 关键 reviewer/规则入口 | 主要维护点 |
|---|---|---|---|---|
| `distribution_network_special_scheme` | 停电施工方案 | `profileMapping`、`basisRegistry`、`packRegistry`、`rulePackRegistry` | 停电链路、结构完整性、参数一致性、规范/证据核验 | 平台侧维护 reviewer prompt、风险关注点、启用模块；repo 侧维护 governance 快照 |
| `construction_org` | 施工组织设计 | `profileMapping`、`basisRegistry`、`packRegistry`、`rulePackRegistry` | 施工组织结构、内容一致性、技术方案、证据/规范核验 | 平台侧维护 reviewer prompt、模块启用、工程类型关注点；repo 侧维护依据映射 |

## 平台维护建议

### 当前平台维护入口

同事日常只改以下位置：

1. `hermes_review_config_wft/resolveReviewConfig` 内的 `document_type_registry`、`scheme_config__{documentType}`、reviewer prompt、风险关注点、规则包引用、modelPolicy 和 outputContract。
2. 主工作流变量默认值：`documentType`、`enabledModules`、`strictMode`。
3. 必要时调整 `focusRequirements`，但不得绕过 `hermes_review_config_wft -> hermes_review_context_wft` 的 profile/basis 解析。

禁止在主工作流里直接新增 `documentType -> basis file path` 或把大段规范原文塞进 prompt。依据选择必须走配置工具、governance 快照、profile 与 pack。

repo 仍保留生成器和治理资产；每次平台变更后导出 JSON 回存并跑 `npm test` 与真实方案验收脚本。

## 验收门禁

真实方案验收必须满足：

- key identity probe 命中 `normalizeInput -> callReviewConfigWft -> callReviewContextWft -> callAiReviewWft -> callFinalAssemblerWft -> formalReply/degradedReply`。
- 文件 URL 可由外网访问，响应 `200`，`Content-Type` 为 DOCX。
- `detail=true` 响应的 `responseData` 无节点错误。
- 最终输出为中文非空，并收口到正式报告或降级报告。
- 报告包含风险点、依据/证据边界、整改建议或人工复核要求。
