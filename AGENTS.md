# hermes-review-agent — Repository AGENTS

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

## Archive Strategy
- Historically deprecated code, outdated scripts, unlinked tests, and obsolete experimentation artifacts MUST be moved to the `archive/` directory instead of being permanently deleted immediately. This ensures a clean active tree while retaining history for manual confirmation.
