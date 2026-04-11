# 008 Review Control Plane — Repository AGENTS

## Repository Mission

This repository is the **008 review control plane / shell**.

Its job is to integrate, govern, and expose a stable review system around Hermes-driven review execution without absorbing the Hermes upstream kernel into local business code.

`external/hermes-agent/` is the designated **external kernel / review engine** boundary for upstream `NousResearch/hermes-agent`.

## System Boundary

At the product level, **Hermes** is responsible for main review control, main review judgment, and final review decision-making.

Within this repository boundary:

- **upstream Hermes-Agent** is integrated as an **external kernel / review engine**
- the **control-plane shell** remains responsible for:
  - `HermesController`
  - `HermesReviewAssembler`
  - template registry policy
  - module binding policy
  - governance
  - public contract stability

This repository must not treat upstream Hermes internals as ordinary local business modules.

## Kernel Safety Rules

- `external/hermes-agent/` is external kernel territory and must remain **pristine by default**
- direct business changes inside `external/hermes-agent/` are **forbidden by default**
- allowed exceptions are limited to:
  - documented upstream upgrade
  - explicit patch overlay managed through `patches/hermes-agent/`
  - documented fork/upgrade workflow with written rationale
- long-lived manual edits inside the submodule working tree are not allowed
- business logic in `apps/api/src/` must not directly depend on unstable upstream internal implementation details

## Allowed Extension Surfaces

New local behavior should extend these shell-side areas first:

- `apps/api/src/adapters/`
- `apps/api/src/review/`
- `apps/api/src/review/rules/`
- `apps/api/src/review/evidence/`
- `apps/api/src/review/plugins/`

Preferred shell responsibilities include:

- adapter contracts
- controller orchestration
- assembler output shaping
- template governance
- rule/evidence/plugin orchestration
- citation and validity support

## Public Contract Freeze

- there must be only one official public final result path
- runtime/candidate/experimental material must not automatically mutate the official final result schema
- raw/debug payloads must not enter the official public contract by default
- controller and assembler remain the guarded public contract path

## Evolution Governance

- runtime templates and candidate templates are allowed
- they do **not** become official automatically
- promotion requires documented validation and explicit promotion flow
- the same principle applies to rule packs, evidence sources, validity checkers, and plugins

## Plugin-first Rule

When adding domain-specific capability, prefer shell-side plugin/pack mechanisms instead of kernel modification.

This applies especially to:

- laws and regulations
- standards and specifications
- validity checking
- citation enrichment
- company policy libraries
- external connectors for rules or evidence sources

These capabilities belong to the control-plane shell, not to the Hermes upstream kernel.

## Upstream Pinning

- all Hermes upstream work must be based on a **pinned upstream version**
- using “latest main” as an implicit dependency target is forbidden
- the machine-readable source of truth is `config/hermes_upstream.yaml`
- upgrade and patch policy are defined in `docs/architecture/hermes-upstream-contract.md`
