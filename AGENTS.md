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
