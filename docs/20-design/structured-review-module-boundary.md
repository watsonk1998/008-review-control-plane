# Structured Review Module Boundary

## Purpose

`StructuredReviewCapabilityFacade` is the supported module boundary between Hermes-side orchestration code and 008 structured-review capabilities.

It exists to let `HermesController` and `HermesModuleRegistry` use 008 capabilities without depending directly on `StructuredReviewExecutor` internals.

## Public methods

The facade exposes five public capability methods:

- `parse_visibility(...)`
- `fact_extract(...)`
- `profile_and_packs(...)`
- `rule_and_evidence(...)`
- `primary_review(...)`

These methods are the only supported Hermes-side entrypoints into 008 capabilities.

## Input contract

Each method receives:

- `workspace`: mutable runtime cache for intermediate objects owned by the facade/module flow
- `context`: normalized task/runtime context including source document path, task identity, review profile hints, artifact writers, and `FactPacketAdapter`

The caller may pass the same `workspace` through multiple calls so the facade can reuse cached parse/fact/profile state.

## Output contract

The facade returns normalized JSON-ready payloads, not executor-native objects.

### Incremental capability outputs

- `parse_visibility`: `module_id`, normalized `visibility`, serialized `parse_result`, `manual_review_needed`
- `fact_extract`: `module_id`, serialized `facts`
- `profile_and_packs`: `module_id`, serialized `resolved_profile`, serialized `packs`, `executable_pack_ids`
- `rule_and_evidence`: `module_id`, serialized `rule_hits`, serialized `candidates`

### Primary review output

`primary_review(...)` returns:

- `module_id`
- `normalized_result`: stable, controller-consumable structured-review result view
- `packet`: serialized `FactPacket` for primary packet flow

The `normalized_result` is the facade-owned compatibility surface for controller/assembler consumption. It may preserve current keys such as `summary`, `visibility`, `issues`, `artifactIndex`, `reportMarkdown`, `reportHtml`, `reportPrintCss`, `resolvedProfile`, `matrices`, and `unresolvedFacts`, but the controller must treat this object as a facade contract rather than as executor-native structure.

## Degradation and error contract

- Incremental methods may raise if the underlying capability fails before producing a valid intermediate state.
- `primary_review(...)` preserves executor behavior and returns the normalized result only after the executor successfully completes.
- Supplemental-review orchestration and final-output assembly are explicitly out of scope for this boundary.

## Forbidden dependencies

Hermes-side callers must not:

- call `document_loader.parse_document` directly
- call executor private helpers such as `_extract_facts` or `_build_task`
- call `rule_engine.run` or `evidence_builder.build` directly
- call `executor.run(...)` outside the facade
- treat executor-native dict keys as a public contract independent of the facade

## Ownership split

- `StructuredReviewExecutor`: internal 008 implementation and report generation
- `StructuredReviewCapabilityFacade`: normalized module boundary into 008 capabilities
- `HermesController`: template selection and orchestration
- `HermesReviewAssembler`: external final result protocol
