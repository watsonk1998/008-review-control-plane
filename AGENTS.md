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
