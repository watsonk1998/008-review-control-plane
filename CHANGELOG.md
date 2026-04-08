# Changelog

本文件记录仓库层面的重要更新，重点保留对产品定位、正式审查契约、文档治理和交付入口有影响的变更。

## 2026-04-07

### Added

- 新增 `docs/PRD-INDEX.md`，作为 `docs/` 的统一入口页。
- 在索引页中明确现有拆分式文档体系的 5 组职责：
  - 产品总纲：`docs/product-strategy.md`
  - 核心能力需求 / 功能规格：`docs/formal-review.md`
  - 架构与实现约束：`docs/architecture.md`
  - 验收与评测门槛：`docs/testing.md`
  - 边界 / 限制 / 运行支撑：`docs/known-limitations.md`、`docs/runbook.md`、`docs/integration/*.md`

### Changed

- 更新 `README.md` 的“关键文档”区，新增：
  - `docs/PRD-INDEX.md`
  - `docs/product-strategy.md`
  - `docs/known-limitations.md`
- 将项目文档的表达从“单文件 PRD 缺失”纠正为“已有拆分式 PRD 文档包，但此前缺统一导航与主真相源声明”。

### Notes

- 本次更新不重写既有产品文档正文，不引入新的产品结论，只对现有文档进行导航层编排与真相源声明。
- 后续若新增产品级文档，应同步更新 `docs/PRD-INDEX.md`，避免再次出现入口分散、口径冲突或阅读路径不清的问题。
