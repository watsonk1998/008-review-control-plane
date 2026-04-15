# Review Governance

## Scope

This document governs controlled evolution of:

- templates
- rule packs
- evidence sources
- validity checkers
- plugins

The goal is to allow runtime experimentation without destabilizing the official public review contract.

## Template Types

- `official template`
- `runtime template`
- `candidate template`
- `experimental template`

## Required Governance Metadata

The following metadata fields have fixed intent:

- `runtime_only`: may be used at runtime but is not part of the official seeded contract
- `experimental`: allowed for exploration, not a production commitment
- `not_official`: explicitly excluded from official registry status
- `requires_promotion_validation`: cannot become official without formal validation
- `generated`: machine-generated artifact that requires governance review

## Template Governance

- runtime/candidate/experimental templates may exist
- they must still run through controller + registry + assembler governance
- they must not bypass the official final contract path
- they must not silently redefine official output semantics

## Rule Pack Governance

- rule packs must declare ownership, applicability, and status
- candidate or experimental packs must not silently become official defaults
- pack promotion requires validation of scope, source quality, and false-positive risk

## Evidence Source Governance

- evidence sources must declare source-of-truth assumptions and freshness rules
- unofficial or experimental sources must be isolated from automatic official assertions
- degraded or stale evidence must remain visible as degraded metadata, not hidden

## Validity Checker Governance

- validity checkers must declare what they validate and what they cannot validate
- checker outputs must be advisory metadata until promoted into official support behavior
- validity logic must not bypass evidence or assembler governance

## Promotion Workflow

Promotion to official status requires:

1. explicit candidate/runtime/experimental identification
2. promotion validation against contract expectations
3. review of public contract impact
4. explicit registry promotion
5. documented approval and version update where needed

## Public Contract Safety

- runtime/candidate/template/pack/plugin/source changes must not automatically change the public final result schema
- runtime material must not bypass `HermesController`
- runtime material must not bypass `HermesReviewAssembler`
- official result shaping remains controller + assembler governed

## Debug / Raw Isolation

- raw/debug/experimental output must not enter the official protocol by default
- debug-only material should be visible only through debug/dev paths
- official outputs should remain schema-stable even when debug payloads evolve

## Governance Responsibilities

- `controller`: orchestrates execution under governed boundaries
- `registry`: decides what is discoverable, selectable, and official
- `assembler`: owns final official output shaping
- `plugin/rule/evidence` layers: provide governed support inputs, not autonomous public contract changes

## Deprecation Policy

- deprecations must be explicit
- previously official artifacts should not disappear silently
- when replacing a template/pack/plugin/source, record the replacement path and transition rule
