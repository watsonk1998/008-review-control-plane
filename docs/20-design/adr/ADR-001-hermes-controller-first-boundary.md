# ADR-001 — HermesController-first boundary

## Status
Accepted

## Context

The runtime live path for `structured_review` is already controller-first:

`DeepResearchRuntime -> HermesController -> HermesReviewAssembler`

`StructuredReviewExecutor` remains the 008 capability foundation, but it is no longer the runtime-facing orchestrator. Hermes-side callers should cross into 008 only through `StructuredReviewCapabilityFacade`.

The repository still contains bridge, compat, fallback, and helper layers that are needed for migration or internal implementation, but they must not become new feature surfaces.

## Decision

1. `HermesController` remains the runtime controller for structured review.
2. `StructuredReviewExecutor` remains the 008 capability foundation.
3. `StructuredReviewCapabilityFacade` is the supported module boundary from Hermes-side code into 008 capabilities.
4. `HermesReviewAssembler` is the only official final output entrypoint.
5. `FinalReportMerger` is retained only as an assembler-internal helper and does not own the external final-output contract.
6. Bridge / compat / fallback layers are frozen and must not accumulate new business capability.

## Freeze boundaries

Frozen categories include:

- controller bridge contracts
- 008-to-controller packet bridges
- fallback/local Hermes shims
- compat-only serializers and similar migration helpers

These layers may receive bug fixes, migration support, or removal work, but not new product capability.

## Consequences

- Documentation, code comments, and tests should describe one live path and one final output entrypoint.
- Controller/runtime code must not bypass the facade to depend directly on executor internals.
- Internal 008 result fields such as `reportMarkdown` may continue to exist, but external final protocol is owned by the assembler and exposed through `finalReportMarkdown / finalReportPacket`.
- The shrink sequence is fixed: freeze and rename boundaries first, consolidate output semantics second, harden the facade boundary third.
