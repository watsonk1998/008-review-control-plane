# Changelog

本文件记录仓库层面的重要更新，重点保留对产品定位、正式审查契约、文档治理和交付入口有影响的变更。

## 2026-04-08

### Added

- 新增 `matrices.structureCompleteness`，用于承载施组 `L1 结构完整性与形式合规性` 的专用结构矩阵。
- 新增 `structure-completeness-matrix.json` artifact，供结果复核、留档和后续前端复用。
- 新增 `/Users/lucas/repos/review/008-review-control-plane/apps/api/src/review/structure_completeness.py`，将施组结构完整性抽成独立能力层。
- 新增正式报告双载体输出：`reportHtml` 与 `reportPrintCss`，并同步产出 `.html` / `.print.css` 工件，作为正式阅读与打印主路径。

### Changed

- 将施组 `L1` 的“结构完整性与形式合规性”改为仅依据 `《建筑施工组织设计规范》GB/T 50502-2009` 的 12 项矩阵驱动，不再依赖原先粗粒度章节 presence 判定。
- 将中文正式报告中的 `L1` 拆为：
  - `2.1 结构完整性与形式合规性`
  - `2.2 合法合规与法定挂接问题`
- 将结果页的专家阅读路径继续前移：正式报告优先，技术细节与原始结构化结果保持可追溯但不抢占主视图。
- 同步更新 web 类型与测试，使 `construction_org` 的结构完整性矩阵进入 API 结果、artifact、报告与类型定义的同一条闭环。
- 将正式 PDF 导出主路径从 `reportMarkdown + md2pdf` 切换为 `reportHtml + reportPrintCss + Playwright Chromium`，使正式 PDF 与 HTML 预览共享同一套结构化版式。
- 修复异步流水线内误用 Playwright Sync API 导致的静默回退问题，避免官方 `structured-review-report.pdf` 回退到旧 Markdown 样式。
- 将“缺项分析与补齐意见”与 `L2/L3` 详情从单行拼接文本改为结构化 HTML 节点（gap item / issue card / 法规要求列表），提升专家可读性与打印稳定性。

### Notes

- 本次只把 `construction_org` 的结构完整性专属化做实；`hazardous_special_scheme`、`construction_scheme`、`supervision_plan` 仍沿用旧的结构规则入口，后续应继续演进为按文种拆分的结构完整性功能包。
- 这一轮调整的重点不是“把报告写得更像报告”，而是让专家可读性、规范归因、结构化字段、HTML 预览和正式 PDF 共用同一套结构判断来源。
- 已通过实际样本验证新版正式 PDF：`/Users/lucas/repos/review/008-review-control-plane/apps/artifacts/manual-regression-cold-final-13/structured-review-report.pdf`。

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
