# hermesStructuredReview legacy toolset reference

本目录是上一版 FastGPT system Toolset 迁移方案的参考实现，当前不再作为正式交付路径。

当前正式交付路径已迁为：

- 主工作流：`/Users/lucas/repos/review/hermes-review-agent/artifacts/fastgpt/hermes-main-review.workflow.json`
- 工作流工具：`/Users/lucas/repos/review/hermes-review-agent/artifacts/fastgpt/workflow-tools/*.template.json`

保留本目录的原因：

- 本地 Vitest 仍使用这些 TS helper 做审查逻辑回归样例。
- 其中的解析、确定性审查和组装逻辑是工作流工具代码节点实现的参考素材。

不得把本目录重新包装为本次迁移的 `.pkg` 交付物；如确需系统插件，应另开明确的 fallback 设计。
