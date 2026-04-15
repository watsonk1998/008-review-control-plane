# Layer Governance: Live, Frozen, and Legacy

This document defines the governance state of various code layers within the `hermes-review-agent` repository. To maintain a clean and deterministic review control plane, we distinguish between active expansion surfaces and structural layers retained for compatibility or boundary clarity.

## Current Runtime Path (The Live Path)

The active structured review path remains:

`DeepResearchRuntime -> HermesController -> HermesReviewAssembler`

Within that path, the following components are the primary targets for capability expansion:
- `StructuredReviewExecutor`: The foundation of review capability.
- `StructuredReviewCapabilityFacade`: The module boundary for external callers.
- `HermesReviewAssembler`: The official exit point for synthesized results.

## Frozen Layers

The following categories are **frozen**. They must not accumulate new business capability or ad-hoc logic. When these files are modified, it should only be for refactoring, performance, or bug fixes that don't change the underlying contract.

- **Controller Bridge Contracts**: The interfaces connecting the orchestrator to individual adapters.
- **Packet Bridges**: Data structures used for inner-loop communication.
- **Fallback/Local Hermes Shims**: Local execution shims used when the full upstream kernel is bypassed or in fallback mode.
- **Legacy Serializer Compatibility**: Layers retained to ensure old review packets can still be read or exported.

## Legacy or Internal-only Layers

These layers are retained for internal use or migration reference but should not be treated as independent runtime entrypoints:

- `FinalReportMerger`: Internal helper to the `Assembler`; not to be called directly from the API.
- `reportMarkdown`: An internal raw result field; the external-facing final protocol must use `finalReportMarkdown` or `finalReportPacket`.
- `docs/90-archive/`: Historical compiled documentation and legacy product definitions.

## Migration Principles

1. **Prune aggressively**: Once a legacy path is fully replaced by a new `structured_review` module, move the old logic to `archive/` or delete it if no reference is needed.
2. **Contract First**: Any change to a frozen layer that affects the public contract must be preceded by an update to the system's `ADR` or `AGENTS.md`.
3. **No Shadow Governance**: Do not duplicate basis-selection or rule-mapping logic in fallback shims.
