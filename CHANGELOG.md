# Changelog

本文件记录仓库层面的重要更新，重点保留对产品定位、正式审查契约、文档治理和交付入口有影响的变更。

> 说明：本次按 2026-03 至 2026-04 的时间窗进行了核查。当前仓库可确认的主线变更集中在 `2026-04-02` 至 `2026-04-08`；若无对应 repo 事实，不为 3 月单独虚构条目。

## 2026-04-12

### Added

- 新增 `template_promotion_policy.py` 实施模板晋升治理，强制执行从 `candidate` 到 `validated` 再到 `promoted_to_seed` 的生命周期检验与归档。
- 新增 `verify_overlay_manifest()` 于 Launcher 内，用于进行针对运行时挂载资产（技能、记忆、配置、提示词）的 Live Overlay 注入前健康度监测及结构化报告。
- 新增 `docs/architecture/hermes-fragment-inventory.md`，系统盘点历史 Hermes-Agent 代码，确认当前系统处于未产生源码依赖污染的“干净壳层”状态。
- 新增 `docs/architecture/hermes-local-kernel-integration.md`，确立 external local kernel 以 Subprocess / Sidecar + Launcher 方式注入的非侵入集成架构，并补充了 PR3 / PR4 相关的架构文档说明。
- 新增 `HermesLocalKernelAdapter` 与 `HermesKernelLauncher` 的本地内核挂载骨架，基于 dry-run 机制支持了隔离环境内的诊断路线。
- 新增 `overlays/hermes-agent/scripts/invoke_kernel.py` 作为 Local Kernel 真实执行时的独立子进程调用垫片（Shim），在物理进程层面与 008 主控面对接原生大模型会话请求。
- 新增 `apps/api/scripts/run_local_hermes_minimal_review.py`，打通最小真实执行链路（Minimal Real Execution），作为一个只供显式触发的封闭验证入口，保证测试端到端安全且不干预默认运行主链。
- 新增对于 `verify_hermes_boundary.py` 边界校验脚本的强化，增强四大关键检查项：防止跨文本的主链泄漏、防止 Support Layer 生成最终裁决语义(`final_grade`等)、校验 Live Overlay 以及检验 Promotion Governance。
- 新增 `apps/api/tests/test_hermes_local_kernel_minimal_execution.py` 专门测试 Local Kernel 执行子进程调用的隔离容错与协议处理（覆盖超时捕获、异常退出）。

### Changed

- 降级 008 原引擎为 Advisory Support Layer（PR3）：限制 `StructuredReviewCapabilityFacade` 和 `FactPacketAdapter`，强制剥离 `final_grade`、`verdict` 等官方裁决字段，确保所有输出携带 `ownership: support_material`，仅由 `HermesReviewAssembler` 执行裁决。
- 升级 `HermesKernelLauncher` 为 Production Main Chain 生产主链引擎，接管 3 级路由（`local_kernel -> external -> llm`），支持凭 `repo_root` 自动解析并传导挂载。
- 增补 `config/hermes_upstream.yaml` 以更新 `expected_runtime` 状态、添加 `overlay` 映射路径和明确 `local_kernel` 执行权限设定声明。
- 更新 `AGENTS.md` 核心声明，补全有关 Local Kernel 作为显式测试选项未进入 `main_dependencies.py` 生产执行主链路的“非默认可用”安全纪律说明。
- 重写 `HermesKernelLauncher` 的 `invoke()` 机制并接入 `subprocess` 模块，使 008 主控面能够安全调度外部 Hermes 进程运行，屏蔽终端原生乱码噪音并只提取确定性 JSON 输出结果。
- 在 `HermesLocalKernelAdapter` 的 `review` 接口内适配挂载管道流，完成从最小 payload 解析转换为 `FactPacket` 实体的降级/可用逻辑。
- 通过 Launcher 把原先在 adapter 内零散维护的 Hermes System Prompt、执行参数拆解归纳至全新 `overlays/hermes-agent/` 文件夹并分层托管。
- 全栈统一 Local Kernel 状态语义的表述同步：在代码 Docstring、边界脚本文案、配置标识与 AGENTS.md 中废弃 `smoke-only` 写法，正式声明为 `minimal real execution available`，仍坚守不耦合主链的 explicit-only 纪律。
- 修复 `invoke_kernel.py` 错误兜底中可能引发 NameError 的 `provider` 未定义引用漏洞；加强 `.gitignore` 以拦截 `*local*.yaml` 等环境重写模板防泄漏。

### Historical Notes

> 补充说明：以下内容同样属于 2026-04-12 的历史补记，不代表当前仓库今天的最新改动顺序；它记录的是本轮对话中已经讨论并随后在仓库中落地的一组 Hermes external-kernel 边界收紧动作。

- 补记 `方案 B` external kernel 收尾：`external/hermes-agent` 已从 planned boundary 真正落地为 git submodule，`.gitmodules`、submodule pointer 与 machine-readable upstream pin 已对齐。
- 补记 submodule 一致性收紧：`config/hermes_upstream.yaml`、`external/README.md`、`docs/architecture/hermes-upstream-contract.md` 与 `scripts/verify_hermes_boundary.py` 已从迁移期口径切换到“必须是真实 submodule”的最终态约束。
- 补记 workflow 入口收口：`make verify-hermes-boundary` 已作为显式边界校验入口存在，后续不应再把 fallback / planned_submodule 视为可接受状态。


## 2026-04-11

> 补充说明：以下内容为 2026-04-12 补写的历史记录，用于补齐 2026-04-11 那一轮 Hermes ownership 小收口；它不是当前仓库在 2026-04-12 的最新代码更新。

### Changed

- 补记一轮围绕 `Hermes 主控 + Hermes 主审 + Hermes 裁决；底座只做支撑` 的小收口：`build_review_task_result()` 进一步转向 decision-first / execution-metadata-first，减少对底座 raw issue/summary 的直接组织依赖，并在结果 metadata 中明确 `result_ownership`、`module_bucketing` 与 `support_material_present`。
- 补记 support-only annotation 收口：底座 issue 在 facade 归一层被显式标注为 `support_material`，并补充 `supportCapabilities / supportModules`，避免 008 支撑材料继续被误读成 final-decision-owned finding。
- 补记 Hermes router finding 的 item-level 模块归属传播：`execution_risk_reviewer` 等 Hermes 主审输出不再只停留在 packet-level `review_modules`，而是把 `module_name / review_modules / template_id / ownership` 下沉到 finding 级别，降低模块分桶对启发式逻辑的依赖。
- 补记一次 3 模块小规模对照验证：`structure_completeness` 当前仍表现为“底座主导，Hermes 重表达”，`legality_compliance` 仍是“混合过渡态”，`execution_continuity` 则已更接近“Hermes 主审 + 底座支撑”。

### Notes

- 这一条 changelog 是历史补记，不代表 2026-04-12 当天的最新开发主线；其作用是把前一轮已经发生的 ownership 收口、模块分桶收口与模块级验证结果补回仓库历史记录。
- 该轮工作的价值不在新增能力，而在把最终结果 ownership 更明确地收回 Hermes 裁决层，并用小规模模块证据验证“主审 / 支撑 / 裁决”分工是否已经开始落地。

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
- 将 special-scheme 第一部分“审查总览表”从仅显示少量映射 issue 的 4 列总览，改为按“结构判定 / 异常摘要 / 补齐建议（简）”表达结构异常的 5 列总览，并同步调整 `test_structured_review.py` 断言口径。
- 完成 `structured-review-form` 的三级选择前端收口：在不改后端契约的前提下保留一级类别、二级 family、三级专项与附加风险模块，并把 capability tree 缺失时的 fallback 收缩为诚实提示。
- 完成一次真实的 weknora 发布闭环：本地变更提交推送后，确认服务器目录 `/root/008-review-control-plane` 不是 git checkout，改用 rsync + `docker compose up -d --build ...` 更新。
- 识别并线上修复 `Dockerfile.api` 的 WeasyPrint / md2pdf native 依赖缺失问题，避免 API 因缺少 `libpangoft2` 等系统库在 import 阶段崩溃，连带拉垮 `/api/tasks/support-scope`。

### Notes

- 这一轮的重点不是再扩大“支持列表”，而是把危大专项方案从通用结构核推进到按工程类型审查的正式内部能力。
- 当前 9 类 pack 的第一阶段仍以章节完整性、参数痕迹、验收链和图纸可视域为主，复杂工程正确性判断仍保留给后续更深层能力演进。
- docs 收口层面，本轮新增的结论不是继续重写正文，而是明确区分“GitHub 页面视图 / Git refs / raw 内容 / 本地文件系统”四种证据层，避免因缓存或旧视图造成错误评审。
- 补充收尾验证事实：special-scheme 总览表已进一步收口为 5 列结构异常总览，`test_structured_review.py` 全量通过（38 passed），且 Weiyanda 样本正式 PDF 已确认走 Chromium / Skia 原生导出链路。
- weknora 已完成一次真实更新与容器重建，但该服务器部署目录当前不是 git checkout；后续仍应按 rsync/compose 事实维护，不应在 changelog 中伪装成标准 git-pull 型部署。

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
