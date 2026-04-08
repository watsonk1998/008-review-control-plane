# Changelog

本文件记录仓库层面的重要更新，重点保留对产品定位、正式审查契约、文档治理和交付入口有影响的变更。

> 说明：本次按 2026-03 至 2026-04 的时间窗进行了核查。当前仓库可确认的主线变更集中在 `2026-04-02` 至 `2026-04-08`；若无对应 repo 事实，不为 3 月单独虚构条目。

## 2026-04-09

### Added

- 新增危大专项方案 9 类工程类型的 internal-ready type packs：`foundation_pit / formwork_support / lifting_installation_removal / scaffold / demolition / underground_excavation / curtain_wall_installation / manual_bored_pile / steel_structure_installation`。
- 新增对应的 type-specific rule hits、evidence clauses、issue/report 文案与 targeted regression tests，使 9 类危大工程不再只停留在 pack registry 层。

### Changed

- 将 `hazardous_special_scheme` 路径下的起重吊装能力从旧 `lifting_operations.base` 收口到新的 `lifting_installation_removal.base`，并在 profile resolver 中同时归一 `disciplineTags` 与 `requestedPolicyPackIds`。
- 保持 `construction_org` 与 `construction_scheme` 继续使用旧 `lifting_operations.base`，明确危大路径与非危大路径的兼容边界。
- 将脚手架、拆除、暗挖、建筑幕墙安装、人工挖孔桩等新增类型 pack 统一纳入 visibility-first 语义：图纸、禁用条件和复杂验算主题优先进入人工复核，而不是直接下硬结论。
- 补做 `docs/` 分层迁移的 GitHub 可见面对齐核验：确认本地工作树、`origin/main` 树和 GitHub raw 内容一致，`docs/` 根目录当前只保留 `README.md`、4 个 legacy stub 与分层目录，不再把旧页面观察误判为“迁移只完成一半”。
- 将根 `README.md` 收口为 English-first 仓库入口页，并重建 `CHANGELOG.md` 对 2026-04-02 至 2026-04-08 主线演进的连续记录，使 docs 入口、仓库首页与变更记录三者口径重新对齐。

### Notes

- 这一轮的重点不是再扩大“支持列表”，而是把危大专项方案从通用结构核推进到按工程类型审查的正式内部能力。
- 当前 9 类 pack 的第一阶段仍以章节完整性、参数痕迹、验收链和图纸可视域为主，复杂工程正确性判断仍保留给后续更深层能力演进。
- docs 收口层面，本轮新增的结论不是继续重写正文，而是明确区分“GitHub 页面视图 / Git refs / raw 内容 / 本地文件系统”四种证据层，避免因缓存或旧视图造成错误评审。
- 补充收尾验证事实：special-scheme 总览表已收口为 4 列，`test_structured_review.py` 全量通过（38 passed），且 Weiyanda 样本正式 PDF 已确认走 Chromium / Skia 原生导出链路；weknora 发布目前仍停留在方案准备层，尚未写成“已上线”事实。

## 2026-04-08

### Added

- 新增分层化 `docs/` 信息架构，形成 `00-product / 10-governance / 20-design / 30-quality / 40-operations / 50-research / 90-archive` 的主目录结构。
- 新增 `docs/README.md` 作为文档总入口、阅读顺序说明与真相源分工表。
- 新增 `matrices.structureCompleteness` 与 `structure-completeness-matrix.json`，用于承载并落盘结构完整性矩阵。
- 新增 `apps/api/src/review/structure_completeness.py`，将结构完整性抽成可复用能力层。
- 新增正式报告双载体输出：`reportHtml` 与 `reportPrintCss`，并同步产出 `.html` / `.print.css` 工件，作为正式阅读与打印主路径。

### Changed

- 将 `README.md` 收口为 English-first 入口页，不再在根目录重复承载 detailed formal-review 契约与治理细节，统一导流到 `docs/README.md`。
- 将 `docs/integration/` 归并为 design layer 材料，并在主文档中加入职责声明，降低跨层口径漂移。
- 将专项方案结构完整性 ownership 从单点实现扩展到 foundation pit、formwork support、steel structure installation 等第三级 pack；`hazardous_special_scheme.base` 继续承载通用专项方案要求。
- 规范化 pack metadata 与 support-scope hierarchy，为 `PolicyPack` 补齐 `label / role / familyKey / tier` 等产品可见元数据，统一 capability tree 与 support-scope 输出口径。
- 完成 distribution network special scheme 的 pack hierarchy 与 review messaging 收口，使危大/专项/场景 pack 的支持边界表达更一致。
- 将 special-scheme 报告中的结构完整性展示重组为“专项补充要求 + 通用要求”的分组表格，提升专家复核顺序与阅读密度。
- 将正式 PDF 打印样式继续收敛为 white document-style visual system，统一字体、页间距、分组文本块与表格样式，改善正式文档观感与打印稳定性。

### Notes

- 这一轮的重点不是扩范围，而是同时收口文档入口、支持边界、结构完整性 ownership 与正式报告阅读路径。
- 根 `README.md` 与 `docs/README.md` 的角色被显式拆开：前者负责仓库首页，后者负责文档导航与 source-of-truth routing。
- 结构完整性能力仍在继续从“单文种特化”向“按文种/场景归属”演进，后续仍可继续扩展到更多 doc type。
- 补记当前产品边界事实：`hazardous_special_scheme` 仍是专项方案 official 主类型，`construction_scheme` 仍为 experimental；“非危大专项施工方案”当前没有独立 documentType / base pack，且路由层对“专项施工方案”默认偏向危大专项方案路径。

## 2026-04-07

### Added

- 新增 `structured_review` 正式 PDF artifact 输出链路，使正式报告不再停留在 Markdown 导出阶段。
- 新增 `L1` 结构完整性矩阵结果与报告呈现，用于支撑 `construction_org` 的正式结构审查表达。
- 新增 DeepTutor bridge 集成，打通 review control plane 与外部能力服务的一个稳定接入点。
- 新增更完整的 task detail / structured review form / recent tasks / review decision panel 前端基础流，形成面向审查工作的最小可用工作台。

### Changed

- 将 structured review 正式报告整体改写为更适合中文专家阅读的结构化样式，弱化工程化原始字段直出，强化正式阅读路径。
- 将 `construction_org` 的 `L1` 从粗粒度结构存在性判断改为规范驱动的结构完整性与形式合规性表达。
- 将结果页的主阅读路径前移到正式报告，同时保留 artifact、原始结果与 reviewer decision 的可追溯入口。
- 收敛 task detail 与 form 的中文产品文案，使“创建任务—查看结果—做复核”的主路径更贴近审查场景而非通用调试台。

### Notes

- 这一轮的核心不是新增更多审查结论，而是把已有工程化结果改造成更适合专家阅读、打印和复核的正式交付面。
- `construction_org` 在这一日获得了最完整的一条“矩阵—报告—artifact—前端展示”闭环。

## 2026-04-06

### Added

- 新增 V0.3 governance spine 的关键实现，包括 reviewer decision、testing gates 与更明确的 formal-review 治理对象。
- 新增自动化 formal structural review baseline 运行方式，使评测可按既定基线自动回放。
- 新增更严格的 L0 visibility parity 与 evidence closure 约束，用于约束结果层和 artifact 层的一致性。

### Changed

- 强化 structured review 的 evidence closure，使结果中的 issue、visibility、artifact 与 evidence gap 不再松散耦合。
- 将 reviewer decision 从附属信息提升为正式治理链路的一部分，支持任务级与结果级复核闭环。
- 将 testing / evaluation 的角色从“跑通即可”提升为 formal-review spine 的硬门槛之一。

### Notes

- 这一轮开始，008 的主线不再只是“能产出结构化结果”，而是开始具备较明确的治理骨架。
- baseline、gate 与 visibility parity 的引入，本质上是在给 `structured_review` 加上可验证约束，而不是继续扩大表面功能数。

## 2026-04-05

### Added

- 新增 review preparation assets 与对应输出路径，为 internal-reviewed preparation 承接提供独立工件。
- 新增 replay diagnostics 与 review preparation / replay evaluation flow 文档，支撑按 case 回放与问题诊断。
- 新增 `product-strategy.md`，作为 008 产品定位、阶段目标与路线判断的主文档之一。
- 新增 research pack generation 相关文档与产出说明，明确真实结构化结果如何导出为研究型样本包。

### Changed

- 强化 preflight 与 evidence traceability，使 unresolved facts、visibility 约束、blocking reasons 与 evidence provenance 的链路更明确。
- 将 formal-review spine 的实施设计进一步从“任务书式描述”落到证据链闭环、治理对象与运行路径上。
- 将 review preparation 与 replay 从临时调试动作收口为正式运行/验证路径的一部分。

### Notes

- 这一轮的重点是把“结果之后怎么办”补齐：除了生成 structured review，还要能准备复核、回放 case、诊断差距。
- `product-strategy.md` 的加入，使产品身份、路线与实施层文档开始分层。

## 2026-04-04

### Added

- 新增 canonical visibility contract 与 direct eval artifacts，使可视域约束直接进入结果与评测产物。
- 新增 reviewer decision flow，支持从结果查看走向最小复核闭环。
- 新增多类 experimental review packs，为危大专项方案等场景提供更细分的 pack 覆盖。
- 新增 reviewer-oriented task detail 改进，提升对审查人而非开发者的结果查看可用性。

### Changed

- 将 visibility 从辅助说明收口为 canonical contract，减少“报告说一套、artifact 说一套”的口径分裂。
- 收紧 canonical review flow，使 experimental pack、eval artifact 与 structured review 主链的关系更明确。
- 对 promotion criteria 与 review visibility contracts 进行对齐，开始把 readiness / official / experimental 的治理边界写进运行结果与支持范围。

### Notes

- 这一天的主线是“把结果契约变成统一契约”，不是继续加更多零散输出字段。
- experimental pack 在这里被引入，但它们的角色是扩展诊断和能力准备，不等于 official support。

## 2026-04-03

### Added

- 新增 `structured_review` pipeline 与 evaluation support，形成正式结构化审查主链的第一版可运行骨架。
- 新增 uploaded source document support，使任务不再局限于内置 fixture，可接受上传文档引用。
- 新增 typed review evidence models，为事实、证据、issue 与报告之间建立更稳定的数据桥梁。
- 新增 review workbench 的 heartbeat 与 live task streaming，形成更像 control plane 的任务面板体验。
- 新增 source-grounded GPT Researcher fallback 与 evidence 路径，改善研究类能力的来源可追溯性。

### Changed

- 将项目从通用任务面升级为带有正式结构化审查子域的 control plane，而非只提供研究/问答类能力。
- 将 fixture evaluation semantics 与 review docs 对齐，使 structured review 的结果、样本与测试口径开始同步。
- 将 `structured_review` 从概念能力推进为“能跑、能评测、能展示”的主链雏形。

### Notes

- 这是 008 从基础 runtime 向 formal-review 主线迈出的关键一天。
- 此时主链已出现，但 governance、visibility 与 reviewer gate 仍在后续几天继续补硬。

## 2026-04-02

### Added

- 新增 review control plane monorepo 初始骨架，确立 `apps/api`、`apps/web` 与配套脚本/测试的基本工程布局。
- 新增 API / Web 最小实现与 supporting tests，为后续任务创建、状态查看与能力扩展提供基础底座。

### Changed

- 将项目从空仓状态推进为可继续承载 research、review 与 orchestration 能力的工程起点。
- 为后续 `structured_review`、前端工作台和文档体系演进建立统一仓库边界。

### Notes

- 这是当前 4 月主线的工程起点。
- 3 月时间窗已核查；当前仓库中未确认到需单独写入 changelog 的 3 月 repo 级条目，因此本文件从 2026-04-02 开始连续记录。
