# hermes-review-agent — Repository AGENTS

## Contract posture
This file remains a **thick local execution contract** because it defines upstream-vs-shell boundaries, the official review pipeline, fail-closed report ownership, and basis-governance constraints.

For the high-level roadmap, shell topology, and governing manifesto, see the [Root README](README.md). If background architecture prose grows further, move explanatory material into `docs/20-design/` and keep only boundary, pipeline, result, and safety rules here.

## Repository Mission

This repository is the **hermes-review-agent control plane / shell**.

Its job is to integrate, govern, and expose a stable review system around Hermes-driven review execution without absorbing the Hermes upstream kernel into local business code.

`external/hermes-agent/` is the designated **external kernel / review engine** boundary for upstream `NousResearch/hermes-agent`.

## System Boundary (Upstream vs Shell)

At the product level, **Hermes** is responsible for main review control, main review judgment, and final review decision-making.

Within this repository boundary:
- **upstream Hermes-Agent (`external/hermes-agent/`)** is the untouched upstream execution kernel.
- **control-plane shell** remains responsible for:
  - `HermesController`
  - `HermesReviewAssembler`
  - template registry policy
  - module binding policy
  - governance
  - public contract stability

**Boundary hard rules**:
- `external/hermes-agent` MUST NOT contain project-specific business logic, basis selection, profile mapping, or formal result contract generation.
- Do not move, rename, copy, or fork the upstream kernel's code for local business logic.
- Do not copy shell orchestrator code into the upstream kernel.

## Governed Review Pipeline (The ONLY Official Main Chain)

All formal review tasks MUST follow this strict orchestration pipeline:

1. **TaskCompiler**: Translates broad inputs into a strict `ReviewBrief`. Does NOT perform basis selection.
2. **ProfileResolver**: Parses profiles and determines system classification. Must NOT be bypassed by adapters.
3. **BasisPackResolver**: Assembles packs, rule packs, and basis sets strictly according to the `profile_id`.
4. **SupportPacketBuilder**: Prepares facts, evidence, rule hits, and visibility gaps into a normalized `SupportPacket`. Must NOT generate formal verdicts.
5. **Hermes Main Review**: Consumes the `ReviewBrief`, `SupportPacket`, and resolved bases to execute main judgment/synthesis. Does NOT independently fetch raw specification files.
6. **FinalReportAssembler**: The **ONLY** official exit point for formal review results. Assembles and outputs the formally structured final report.

## Basis Governance

The formal basis for any review (laws, standards, enterprise rules) is strictly governed by the repository system of record.
- **Truth Source**: Basis files MUST come from `knowledge/review_basis/`.
- **Registry**: Registries and mappings MUST be defined in `config/review_basis/`.
- **Prohibited Behavior**: 
  - Adapters are FORBIDDEN from reading basis files directly or making basis choices.
  - Adapters MUST NOT use `fixtures/` as a formal basis repository.
  - Hardcoded mappings like `documentType -> basis file path` or large prompt injections of raw specifications are strictly prohibited.
  - **Dynamic Mapping Constraint**: Review basis assignment (especially for tier-3 scheme additions) MUST be handled via dynamic `applicability_tags` mapping in `basis_registry.yaml`. Developers MUST NOT directly modify Python code or hardcode `basis_ids` arrays in `pack_registry.yaml` every time a new standard is introduced. Data binding must remain isolated in the configuration layer.

## Frontend Governance Harness

- The frontend MUST NOT become a shadow governance layer.
- Classification trees, basis lists, pack/rule-pack visibility, module states, progress states, and export options MUST be projected from backend frozen contracts or governed payloads.
- Frontend hardcoded taxonomy/basis/rule mappings are forbidden except for narrow, schema-aligned fallback rendering when the backend contract is unavailable.
- If a product requirement cannot be expressed by the current backend contract, extend the backend contract first and then update the frontend projection.
- Harness principle: keep a **single source of truth** for governance data; do not duplicate review governance in the web shell.

## Result Protocol & Final Report Ownership

- **Final Report Ownership**: The formal review report can ONLY be output by the shell-side `FinalReportAssembler`.
- **Support-Layer Prohibition**: `support_result_hermes_review_agent` and pre-check findings are strictly supporting evidence/pointers. They MUST NEVER be presented as the main body of the formal review report if Hermes fails.
- **Fail-Closed Policy**: If `hermes_review_packets` is empty, Hermes controller is degraded, the backend is unavailable, or Hermes main review did not complete successfully:
  - The system MUST fail-closed.
  - NO formal review report shall be emitted.
  - Only non-formal outcomes (e.g., "Pre-check result", "Support layer result", "Main review aborted") may be returned.

## User-Visible Language & Tone Constraint

All user-visible content in reports, interfaces, and statuses MUST be presented in **Chinese**.
- This includes frontend copys, generated markdown reports, state descriptions, and error notifications.
- The tone must be natural, professional, restrained, and human-friendly.
- **CRITICAL RESTRICTION**: Language "polishing" MUST NEVER alter:
  - Factual review findings
  - Identified risk severity levels
  - Evidence and text citations
  - Regulatory article references
  - Statuses like `degraded`, `visibility gap`, or `manual review needed`.

## Kernel Safety Rules

- `external/hermes-agent/` must remain **pristine by default**.
- direct business changes inside `external/hermes-agent/` are **forbidden by default**.
- allowed exceptions: documented upstream upgrade or explicit patch overlay via `patches/hermes-agent/`.

## Upstream Pinning

- all Hermes upstream work must be based on a **pinned upstream version**.
- the machine-readable source of truth is `config/hermes_upstream.yaml`.
- upgrade and patch policy are defined in `docs/architecture/hermes-upstream-contract.md`.

## Deployment SOP

- Any deployment to the server MUST strictly follow the instructions and architectural caveats outlined in `hermes-agent-deployment-sop.md`.
- Be aware of the **Dual-Cache Layer** structure in `Dockerfile.api`. Even though runtime volumes exist for Python hot-reloading, explicitly executing `--build` (e.g., `docker compose up -d --build api`) is the heavily-cached best practice for guaranteeing dependency consistency.
- Ensure production environment files (like `.env`) are excluded from any automated `rsync` synchronizations to prevent catastrophic credential loss.

**`hermes-agent-deployment-sop.md` is explicitly listed in `.gitignore` (line 85) and MUST NEVER be committed or pushed to GitHub.**
- AI Agents are FORBIDDEN from running: `git add hermes-agent-deployment-sop.md`, `git add -f hermes-agent-deployment-sop.md`, or any `git add -A` that includes this file.
- This file contains server topology, port mappings, and operational secrets — it is a **local-only private document**.
- When merging feature branches into `main`, always use `--no-ff`. Never use `--ff-only` (diverged branches will cause `fatal: Not possible to fast-forward`).
- Dependabot **High** CVE alerts must be fixed and deployed within the current session — do not defer to the next session.

## Archive Strategy
- Historically deprecated code, outdated scripts, unlinked tests, and obsolete experimentation artifacts MUST be moved to the `archive/` directory instead of being permanently deleted immediately. This ensures a clean active tree while retaining history for manual confirmation.


## Project Corrections Addendum (2026-04-15)

- Task detail simulated progress is a **detail-view experience contract**, not a task-age replay. It must start from 0% when the detail page is entered, then advance at 1% per 4 seconds, cap at 90% while non-terminal, and only switch to 100% on terminal completion.
- The formal report `审查依据文件` list must cover the **actually enabled formal bases** for the current review, including selected pack sources, while hiding both `监理工程师对停电施工方案的审核规则及要点` and `《危险性较大的分部分项工程专项施工方案编制指南》（建办质〔2021〕48号）` from that visible list.
- `编制依据现行有效性核验` is defined strictly as verification of the reviewed document's own `编制依据/编制说明` section. Built-in review bases are out of scope and must never be shown as the object being verified.
- When prior docs/tests mention the old `3 秒 1%` progress rule or built-in-basis validity checks, the 2026-04-15 rule above supersedes them.

## Project Corrections Addendum (2026-04-15, PM batch)

> Source: UI/Reliability repair session — assembler module gate + frontend callout removal.

- **首屏状态卡片禁止展示 warning callout**：`manualReviewNeeded` 和 `parserLimited` 的警示信息只能出现在正式报告正文，任务详情页首屏状态卡片禁止渲染"需要人工复核"与"预检与文档解析说明"两块 callout。

- **assembler 模块级门禁是必须的**：`hermes_ok=True`（全局非全部降级）不代表正式报告可以安全输出。若 `enabled_modules` 中某模块的所有**实际被选中运行**的 reviewer 均 degraded，则该模块无法产出有意义结论，必须 fail-closed（返回降级 markdown，`final_packet=None`），不得输出占位为"本模块未发现需要单独提示的问题"的正式报告。

- **模块降级判断必须看"实际运行"reviewer**：`_check_critical_module_blocks` 必须仅考察 `agent_results` 中出现的 reviewer_id（实际被选中运行的），不得用 `binding.hermes_templates` 声明的全部模板集合做 `all()` 判断——未被选中的 reviewer 不参与判断，否则会错误地认为该 reviewer"正常"从而不阻断。

- **`degradedReason` 禁止为空字符串**：任何降级路径都必须写入非空的 `degradedReason`；若 `packet.error=""` 则回退到 `"{agent_id} 审查组件降级，未返回有效结果"`。

- **测试中 `ReviewBrief.review_object_type` 的类型约束**：该字段类型为 `ReviewDocumentType`（文档类型枚举，如 `distribution_network_special_scheme`），不得使用审查结论等级（如 `conditional_pass`），否则 Pydantic 直接抛 ValidationError。

- **`assembler.py` 历史遗漏导入**：`ReviewPacketMetrics` 在 `_merge_hermes_review_outcomes` 中已被使用但原先未导入，属潜在 `NameError`；已在本批次修复。补导入时，务必同步检查同文件其他已使用但未显式导入的类型。

- **测试执行环境**：`hermes-review-agent/apps/api` 项目使用本地虚拟环境，测试命令必须用 `.venv/bin/pytest`，不得假设系统 PATH 中有 `pytest`。

## Project Corrections Addendum (2026-04-15, report output & normative validity)

> Source: User-reported issues — executive summary stats sentence + over-aggressive normative validity judgment.

- **正式报告 executive summary 禁止包含统计句**：`_decide_executive_summary()` 只允许输出"本次审查已由专业主审组件裁决完成，总体评级结论为：**X**。"这一句主结论。禁止拼接模块覆盖数、问题总数、风险分布等统计文案。此类信息由 view model 的 `executiveSummaryView.metrics` 独立计算展示，不得从 prose summary 中反向解析。

- **裸标准号不得直接判定为"现行有效"**：若被审方案《编制依据》中引用的标准号缺少年份后缀（如 `GB/T 6995` 而非 `GB/T 6995.1-2008`），且联网结果无法唯一映射到单个具体现行标准，则状态必须为 `unknown`（待人工核验）。仅凭搜索摘要出现"现行/有效/实施"等正向关键词不得判定 `current`。

- **家族标准 / 多分册标准不可自动收敛**：若输入无分册号（如 `GB/T 6995`）但搜索结果指向某个分册（如 `GB/T 6995.1-2008`），不算唯一映射，必须判定 `unknown`。

- **联网精确唯一命中条件**：只有同时满足以下三项，才允许将裸标准号判定为 `current` 并标注 `resolvedTitle`：(1) 搜索结果标题含精确标准编号（含年份）；(2) 基础编号与输入完全一致；(3) 输入无分册号时，搜索结果也不得是分册。

- **view model 必须承载规范化结果**：`NormativeValidityCheckView` 必须包含 `resolvedTitle`（精确命中时的规范化标题）和 `note`（unknown 时的人工核验原因，或 current+resolved 时的确认说明）。表格主标题优先展示 resolvedTitle（若存在且不同于原始标题）。

- **`_parse_executive_summary()` 防御性过滤**：即使遗留数据仍含"本次结果共覆盖…形成…项审查问题…"类统计句，view model 解析时也必须过滤，不得渗透到前端 narrative。当先前文档或代码中关于 executive summary 的口径与本条冲突时，以本条为准。


## Project Corrections Addendum (2026-04-15, normative scope + calculation reviewer + prose dedup)

> Source: Engineering hardening session — scope narrowing, note column fix, calculation sub-agent, verdict dedup.

- **`编制依据现行有效性核验` 范围严格限定为标准规范**：核验对象只能是带标准编号的规范性文件（国标 GB/GB/T、行标 DL/DL/T/NB、地标 DB/DBJ、带标准号企业标准 Q/CSG/Q/GDW 等）。法律法规、行政条例、部门规章、企业内部管理制度文件、通知、规定、办法等**明确排除**，不得进入核验集合。实现：`_is_standard_normative()` 门禁方法在两个文档抽取入口统一过滤。

- **`_is_standard_normative()` 判断优先顺序不可颠倒**：(1) 先检查标准编号——有编号直接 return True，不走排除关键词路径（防止带编号的企业标准被误伤）；(2) 再检查排除关键词；(3) 再检查法律形态（以"X法》"结尾）；(4) 默认保守通过。任何修改不得将编号检查后移。

- **`_heuristic_result()` 禁止对条例/法规词条判 current**：此类词条应在 `_is_standard_normative()` 入口已被过滤，不应流入 heuristic。历史代码中对"条例"的保守 current 映射已移除，禁止恢复。

- **note 文案列位合同**：`编制依据现行有效性核验` 表格中，note 必须出现在**核验状态列**（以 structured-report__muted 样式追加在 statusLabel 之后），不得出现在**规范名称列** `<td>` 内。修改渲染方法时必须遵守此列位合同。

- **`_render_executive_summary()` fallback 条件**：仅在 verdict 不存在时才允许 fallback 渲染 raw_text。有 verdict badge 时不得再追加 `<p>` 渲染 raw_text（否则 verdict 信息重复展示）。本条与旧代码口径冲突时以本条为准。

- **calculation_review_reviewer 保守约束**：该模板负责计算式/验算/参数/公式审查，归属 evidence_validation。未见计算书/验算过程时，**禁止臆造计算错误**，只能输出"证据不足，需人工补充复核"类保守表达。

- **测试文件内嵌中文书名号陷阱（HG-16）**：Python 字符串内嵌 `》` 时若外层引号同向会触发 SyntaxError: unterminated string literal。写入后必须执行语法验证：`python -c "import ast; ast.parse(open('file.py').read())"`，不得假设工具写入一定正确。

## Project Corrections Addendum (2026-04-15, evidence_validation execution plan + calc fallback)

> Source: User-reported evidence_validation module completely missing in reports — reviewer never selected + calculation reviewer invisible.

- **前端默认启用模块必须包含全部 5 个模块（HG-18）**：`review-acceptance-page.tsx` 的 `enabledModules` 初始值必须与 `create-task-form.tsx` 保持一致，即同时包含 `structure_completeness`、`parameter_consistency`、`legality_compliance`、`execution_continuity`、`evidence_validation`。遗漏任何模块会导致对应 reviewer 不进入 `enabledAgents`，进而被 `template_registry.select_templates()` 的 `continue` 分支跳过。

- **`template_registry.select_templates()` 的 enabled 过滤是硬门禁**：当 `enabledAgents` 非空时，不在列表中的 template **一律 `continue`**（L66-71），不会被 `default_enabled`、`document_type_match` 或 `focus_keywords` 救回。因此任何新增 reviewer 必须确保其 template_id 被 `module_template_ids()` 正确返回。

- **calculation_review_reviewer 必须有确定性 fallback（HG-17）**：当 `hermes_router` 返回 0 个 findings 时，`agent_runner` 必须自动注入一条 `severity=info` 的保守型 finding（`H-CALC-FALLBACK-001`），文案为"未见计算书或验算过程，需人工补充复核"。这确保"计算核验"功能在前端始终可见，不会出现"模板存在但功能不存在"的用户体验。

- **`_TEMPLATE_HARD_MODULE` 双层硬归属是必须的（HG-15 强化）**：`agent_runner._annotate_finding_ownership` 和 `final_report_view_model._resolve_module` 必须**同时维护** `_TEMPLATE_HARD_MODULE` 映射。两者缺一不可：runner 侧保证写入时正确，view_model 侧保证读取时不被 category/keyword fallback 覆盖。

- **`power_outage_operation_chain_reviewer` 禁止声明 `evidence_validation`（HG-19）**：该 reviewer 的 `metadata.review_modules` 只允许包含 `execution_continuity`。将其绑定到 `evidence_validation` 会导致停电链路 finding 混入证据验证模块，与 normative_validity_reviewer / calculation_review_reviewer 的输出混淆。

- **`_build_normative_validity()` 必须用原始 findings 构建表格（HG-20）**：传入 `deduped_findings` 会导致表格被 dedup 吞掉（ID/title 冲突时丢失含 `normativeValidityChecks` 的 finding）。必须传入 `findings`（pre-dedup）以保证表格数据不丢失。

- **模板 JSON 文件禁止包含中文弯引号（HG-21）**：`templates/*.json` 中的字符串值禁止使用中文弯引号（`\u201c` `\u201d` `\u2018` `\u2019`），必须使用书名号（`《》`）或直接去掉。中文弯引号会被 JSON 解析器视为字符串终止符，导致 `model_validate_json` 报 `expected , or }` 错误。`template_registry.load_templates()` 会静默跳过加载失败的模板（只打 warning），这是**静默失败反模式**——模板从未加载 → 从未被选中 → reviewer 从未执行 → 功能完全不可见。

- **模板 JSON 创建/修改后必须执行验证门禁（HG-22）**：任何对 `templates/*.json` 的创建或修改操作完成后，必须立即执行以下验证：`python -c "import json; json.load(open('path/to/template.json'))"` 以及 `python -c "from src.review.hermes.template_models import AgentTemplate; AgentTemplate.model_validate_json(open('path').read())"`。两项均通过后方可提交。

- **前端及正式报告禁止出现 Emoji 表情符号（HG-23）**：所有用户可见内容——包括正式报告 HTML/PDF、前端页面、状态提示、模块标题——禁止使用任何 Emoji（Unicode Emoji 序列、Emoji_Presentation 字符）。如需视觉标识，使用 SVG 图标或纯 CSS 实现。此规则覆盖 `apps/web/`、`_FINAL_REPORT_CSS`、`FinalReportRenderer` 和所有 view model 输出。

## Project Corrections Addendum (2026-04-16, 施组接入 + Agent 拆分 + 技术债务清理)

> Source: 施工组织设计文档类型全量接入、内容一致性/技术方案 reviewer 粒度拆分、早期集成项目代码清理（commit 91f87fa）。

### 施工组织设计（construction_org）接入规则

- **新增文档类型必须走四层流程**：L1 分类（前端 taxonomy）→ basis_registry.yaml → pack_registry.yaml → Hermes template JSON → module_bindings.py。缺任何一层都会导致 reviewer 不被选中或依据文件不加载，属于静默失败（无报错，功能不可见）。

- **施组专属审查依据文件的 truth source 是 `knowledge/review_basis/`**：禁止直接从 `fixtures/` 读取作为正式审查依据；`fixtures/` 仅用于开发调试。迁移新标准时必须同步更新 `basis_registry.yaml` 条目。

- **`supported_document_types` 是 reviewer 隔离的唯一机制**：施组专属 reviewer 必须设置 `supported_document_types: ["construction_org"]`，否则该 reviewer 会对所有文档类型生效，污染配网/危大方案审查结果。通用 reviewer 设置 `supported_document_types: []`（空数组）表示适用所有类型。

### Agent 粒度拆分规则

- **单 reviewer 禁止同时挂载 `parameter_consistency` 和 `execution_continuity` 两个模块**：参数矛盾与执行逻辑断点是不同职责，混在一个 reviewer 会导致 prompt 语义模糊、findings 归模块随机。

- **`execution_risk_reviewer` 的职责已收窄为 `execution_continuity` 单模块**：其历史遗留的 `parameter_consistency` 职责已迁移至 `parameter_consistency_reviewer`（2026-04-16）。修改该文件时不得重新添加 `parameter_consistency` 声明。

- **`module_bindings.py` 是 module → templates 的唯一映射层**：新建或拆分 reviewer 时，必须同步更新 `REVIEW_MODULE_BINDINGS` 中对应模块的 `hermes_templates` 列表，否则该 reviewer 永远不被任何模块选中。

### JSON 模板写入硬门禁（HG-24，升级 HG-21/22）

- **工具写入 JSON 不可信原则（HG-24）**：`multi_replace_file_content`/`replace_file_content` 对多字节中文字符的写入结果不可信，可能静默写入非 ASCII 替换字符（如「葶」代替「紧」）或中文弯引号（`\u201c\u201d`）。写入后必须**逐文件单独验证**，不能批量验证掩盖报错顺序：`python -c "import json; json.load(open('path.json'))" && echo OK || echo FAIL`。若验证失败，使用 `write_to_file（Overwrite: true）` 完整重写，不要再次用 patch 工具。

- **HG-21 补充**：除 `\u201c\u201d`（中文弯双引号）外，`\u2018\u2019`（弯单引号）亦在禁止范围内，一律改用书名号（`《》`）或删除。

### 技术债务清理规则

- **DeepResearchRuntime 唯一支持的 task type 是 `structured_review`**：`knowledge_qa`、`deep_research`、`document_research`、`review_assist` 四个 task type 的执行路径已从 `deepresearch_runtime.py` 删除（2026-04-16，commit `91f87fa`）。引入新 task type 时必须在该文件显式添加分支，不得假设历史方法仍存在。

- **FastGPT 向量知识库适配器保留**：`adapters/fastgpt_adapter.py` 和 `config/fastgpt.py` 具备独立扩展价值（向量知识库对接）。禁止在下次技术债务清理中删除这两个文件。

- **已删除的 adapter 清单（禁止重新引入）**：`adapters/deeptutor_adapter.py`（DeepTutor WebSocket 客户端）、`adapters/gpt_researcher_adapter.py`（GPT Researcher HTTP 客户端）、`orchestrator/planner.py`（DeepResearchAgent capability chain 规划器）。

- **根目录只存放配置文件和项目说明**：一次性 migration 脚本、调试脚本、工具脚本和截图禁止放在根目录，必须归档到 `archive/` 或移入 `scripts/`。

## Project Corrections Addendum (2026-04-16, UI performance & extraction noise)

> Source: Resolving Weknora frontend crashes, progress bar logic, markdown table extraction noise, and English key leakage.

- **全局 CSS 禁止使用强制重排属性（HG-25）**：`break-inside: avoid` 和 `page-break-inside: avoid` 绝对禁止出现在全局（屏幕）CSS 中。它们只能被包裹在 `@media print { ... }` 块内。在几十张卡片的长列表中，这些属性会在滚动时引发 `O(n)` 的强制重排，导致浏览器白屏卡死。
- **任务进度条必须以真实创建时间为基准**：前端 `task-detail.tsx` 的进度计时起点必须用 `task.createdAt`。禁止使用 `Date.now()`（页面打开时间），否则中途导航进入的长期运行任务会导致进度回退到 1%（时间差重置）。
- **`progressPercent` 必须采信后端真实 stage 估值**：最终渲染的进度百分比必须 `Math.max(simulatedPercent, realPercent)`。当后端明确上报已完成多轮 agent 审查（`realPercent > 60%`）时，绝不允许被单纯基于时间推演的低进度（`simulatedPercent`）所覆盖。
- **Markdown 表格提取免疫（HG-26）**：针对 PDF 等格式的识别缺陷（会把表格渲染为带竖线的 markdown 行），在 `_split_reference_candidates` 提取规范依据时增加硬提取门禁：任何首字符为 `|` 或单句含 `>=2` 个 `|` 的片段，直接按噪音抛弃。禁止使用简单的符号 split 导致整块表格被识别为一个标准名称。
- **内部状态键必须做展现层隔离（HG-27）**：像 `title_detected_without_attachment_body` 等内部引擎状态 key，绝对禁止通过 `finding.summary` 渗透至最终正式审查报告中展示给用户。此类变量应始终在到达视图模型（View Model）前经 `_INTERNAL_DESCRIPTION_KEY_LABELS` 之类的字典实行收口翻译。

## Project Corrections Addendum (2026-04-16, 下午批次 — UI 体验回归修复)

> Source: 用户截图报告 5 个生产回归——进度条瞬跳卡死、PDF 页面割裂空白、编制依据识别不全、网页滚动卡顿白屏、鼠标滚轮触发浏览器回退。

### 进度条 stage floor 合同（修订，与上方旧规则冲突时以本条为准）

**进度条设计最终合同**：
- 时间驱动（`estimateSimulatedProgress`，1%/6s，上限 90%）为**唯一主驱动**。
- stage 信号通过 `estimateStageFloor()` 只提供**下界保证（floor）**，不是跳跃目标值。
- `effectivePercent = Math.max(simulatedPercent, stageFloor)`。
- **`stageFloor` 值域上限约束（任何修改必须遵守，违反即回退）**：
  - `agent_running`（无 totalAgents）：`≤ 25%`
  - `agent_running`（有数据）：`25 + completedRatio * 50`，范围 `[25%, 75%]`
  - `report`：`≤ 88%`；`finalize`：`≤ 95%`
- 上方 HG-25 addendum 中"`progressPercent` 必须采信后端真实 stage 估值"的表述与本条冲突，以本条为准：stage 值只是 floor，**不是最终决定者**。

### CSS 打印样式禁止事项

- **`page: wide` 禁止在报告 CSS 中使用**（`@media print` 内亦禁止）：切换页面尺寸（portrait→landscape）需要从新页开始，即使包在 print block 内也会在元素前产生强制分页，导致报告空白页。宽表格应 `overflow-x: auto` 在屏幕水平滚动，PDF 自然断页。
- **`content-visibility: auto` 禁止在报告 section 上使用**：快速滚动时未渲染 section 出现白屏占位块，副作用大于性能收益。
- **`transition: box-shadow` 禁止用于长列表 issue-card**：hover 过渡在大量 card 时触发持续 composite 重绘，是滚动卡顿的主要 CSS 原因。

### 横向滚动容器 overscroll 合同（HG-28）

任何使用 `overflow-x: auto/scroll` 的报告/详情页容器，**必须**同时声明 `overscroll-behavior-x: contain`。
- 不声明时 Mac trackpad/鼠标横向滚到边界后事件"穿透"给浏览器触发历史导航（后退）。
- 受此约束：`.structured-report-host`（`theme.css`）、`.structured-report__table-wrap`（`final_report_view_model.py`）。
- 新增任何横向滚动容器时，`overscroll-behavior-x: contain` 为**必须项**。

### 标准代号提取 regex 覆盖合同（更新 normative_validity.py 维护规则）

`_NORMATIVE_CODE_PATTERN` 覆盖的前缀集合（变更 normative_validity.py 时必须确认完整）：
`GB / GB/T / GBJ / DL/T / DL / NB/T / NB / AQ / DB / DBJ / DGJ / JGJ / YD/T / SL / GA / CECS / TSG / HG / CJJ / SH/T / YB / JB / CJ / YS / SY / HJ / TB / LB / MZ / Q/CSG / Q/GDW / Q/SH / Q/BGJ`

pipe-row 提取改为 cell-by-cell（最终版，上方旧 HG-26 的"按噪音抛弃"已被此方案取代）：
1. 按 `|` 分割为单元格；2. 过滤表头标签；3. 保留含标准代号或 `《` 的 cell；4. 禁止 `findall(code)` 只提取裸代号。

