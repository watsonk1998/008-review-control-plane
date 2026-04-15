# Harness Engineering Principles

This document defines the overarching design philosophy for the `008-review-control-plane` to govern its external review kernel (`external/hermes-agent`).

## 1. System of Record

The repository is the **system of record** for all review policies, standard mappings, and compliance rules. 
Agent capabilities must be documented in structured formats (YAML, Markdown) that act as a verifiable source of truth, 
rather than relying merely on natural language prompts attached to individual agents.

- **Legibility**: The relationships between review types, standard specifications, and extraction rules must be cleanly human-readable.
- **Traceability**: All external laws, standards, and company-specific documents must be registered in the central knowledge base with explicit validity status.

## 2. Kernel Preservation

The core review engine (`external/hermes-agent`) acts exclusively as an external kernel.
- **No Direct Modification**: The kernel is treated as immutable by the business layer. Do not put business logic into the external kernel.
- **Harness Overrides**: The execution environment orchestrates the kernel using "Overlays" (prompts, skill configurations, limited configurations).
- **Execution Confinement**: The kernel must never dictate its own inputs or unilaterally alter the public schema of its output.

## 3. The Governed Review Pipeline (Official Main Chain)

All formal review tasks MUST follow this single, strict pipeline. Bypassing any step is forbidden.

1. **TaskCompiler**: Translates a broad user intent into a strict `ReviewBrief`. Pure compilation; no basis selection logic.
2. **ProfileResolver**: Determines the document classification (e.g., Level 1/2/3 schemes). Translates parameters into a `ResolvedReviewProfile`.
3. **BasisPackResolver**: Assembles the exact required rule packs, compliance documents, and basis sets directly derived from the Profile.
4. **SupportPacketBuilder**: Structures extracted facts, validates initial checks, and wraps visibility gaps into a normalized `SupportPacket`. Must NOT generate a formal final verdict.
5. **Hermes Main Review**: Hermes acts as the sole synthesizer and main reviewer. It consumes the built context but does not independently query the filesystem for arbitrary standards.
6. **FinalReportAssembler**: The sole authority for producing the formal review report output.

## 4. Hard Constraints

- **No Prompt Engineering as Architecture**: Architectural routing choices cannot be driven purely by "smarter prompts". They must be driven by constrained execution tracks.
- **Fail Closed**: If `hermes_review_packets` is empty, Hermes controller is degraded, or the backend is unavailable, the system MUST NOT masquerade support layer outputs as formal reports. It must fail-closed and return only pre-checks or support information.
- **Adapter Limitations**: LLM Adapters cannot decide basis files internally (e.g., via `if documentType == X`) or load raw markdown specs using simplistic prompts.
- **Frontend Selection Is a Harness Contract**: If the frozen frontend contract specifies selected review modules, that selection must propagate through execution, aggregation, rendering, and export. "后台全跑、前台隐藏未选模块" is a contract violation, not a cosmetic issue.
- **Rendered Output Is the Metric Source of Truth**: User-visible counters and cards must be derived from the final rendered finding set or another governed machine contract. Never parse human-readable executive-summary prose back into machine metrics.
- **Same-Layer Evidence Before Generic Fallback**: When presentation layers still contain recoverable chapter anchors in governed summaries or recommendations, use them before emitting generic fallback text such as “未定位到稳定章节，请结合原文复核。”.
