# hermes-review-agent

hermes-review-agent is a review control plane for engineering document review.
Its current primary track is `structured_review`: a formal-review pipeline that turns review inputs into **structured, reviewable draft outputs** rather than final signed conclusions.

> For the full documentation map and source-of-truth guide, start from [`docs/README.md`](docs/README.md).

## Current Focus

The repository is currently centered on:

- HermesController-first `structured_review` as the runtime live path
- hermes-review-agent `StructuredReviewExecutor` as the structured review capability foundation
- reviewable structured issues, evidence, and visibility-aware outputs
- governance-aware capability evolution (`official` / `ready` / `experimental`)

Legacy note: the former post-hoc dual-review path has been removed from the active runtime and survives only as a historical migration reference; it is not part of the current live path.

This repository does **not** position the current system as a fully automatic final review-signing engine.

## Current Live Path / Frozen Layers / Internal-only Layers

### Current live path

The active structured review path is:

`DeepResearchRuntime -> HermesController -> HermesReviewAssembler`

Within that path:

- `StructuredReviewExecutor` is the hermes-review-agent capability foundation
- `StructuredReviewCapabilityFacade` is the module boundary exposed to Hermes-side callers
- `HermesReviewAssembler` is the only official final output entrypoint

### Frozen layers

The following categories are frozen and must not accumulate new business capability:

- controller bridge contracts and packet bridges
- fallback/local Hermes shims
- legacy serializer compatibility and other compat-only layers

When these files remain in the repository, they are retained for migration, compatibility, or boundary clarity — not as active expansion surfaces.

### Legacy or internal-only layers

- `FinalReportMerger` is an assembler-internal helper, not an independent runtime entrypoint
- `reportMarkdown` remains an internal hermes-review-agent result field; external final protocol uses `finalReportMarkdown / finalReportPacket`
- historical compiled docs under `docs/90-archive/` are retained for reference, not as day-to-day source of truth

## Repository Guide

### Key areas

- `apps/` — application code
- `fixtures/` — review fixtures and sample inputs
- `docs/` — product, governance, design, quality, operations, and research docs
- `scripts/` — project scripts and utilities
- `artifacts/` — generated outputs and evaluation artifacts

### Documentation entrypoints

- Product and V1 definition:
  - [`docs/00-product/`](docs/00-product/)
- Governance and formal-review boundaries:
  - [`docs/10-governance/`](docs/10-governance/)
- Design and implementation:
  - [`docs/20-design/`](docs/20-design/)
- Quality, testing, and known limitations:
  - [`docs/30-quality/`](docs/30-quality/)
- Full docs map and source-of-truth guide:
  - [`docs/README.md`](docs/README.md)

For detailed governance, capability boundaries, acceptance rules, and implementation planning, use:

- [`docs/10-governance/formal-review.md`](docs/10-governance/formal-review.md)
- [`docs/10-governance/008-v1-capability-boundary.md`](docs/10-governance/008-v1-capability-boundary.md)
- [`docs/10-governance/008-v1-acceptance-spec.md`](docs/10-governance/008-v1-acceptance-spec.md)
- [`docs/20-design/008-v1-implementation-skeleton.md`](docs/20-design/008-v1-implementation-skeleton.md)
- [`docs/20-design/008-v1-pr1-pr8-workplan.md`](docs/20-design/008-v1-pr1-pr8-workplan.md)

## Quick Start

### Bootstrap

```bash
make bootstrap
```

### Run the local stack

```bash
make dev
```

### Run tests

```bash
make test
```

### Run review evaluation

```bash
make eval-review
```

## What the System Currently Produces

At a high level, the main `structured_review` path aims to produce:

- structured review issues
- evidence-aware review artifacts
- visibility and parser-limitation disclosure
- unresolved facts and manual-review cues
- reviewable markdown and report outputs

The detailed result contract, review semantics, and governance rules are maintained in the governance and design docs listed above rather than duplicated in this root README.

## Current Documentation Model

Docs are organized in layers:

- `00-product` — what the product is
- `10-governance` — what is officially supported and where the boundaries are
- `20-design` — how the system is designed and implemented
- `30-quality` — testing, limitations, and validation
- `40-operations` — runbooks and maintenance
- `50-research` — background research
- `90-archive` — historical indexes and compiled artifacts

For reading order, ownership, and source-of-truth mapping, use [`docs/README.md`](docs/README.md).

## Notes

- Some capabilities may exist in code or experimental packs without being official product commitments.
- Historical compiled docs and legacy indexes are retained under `docs/90-archive/`, but they are not the day-to-day source of truth.
- When in doubt about documentation ownership, follow the source-of-truth table in [`docs/README.md`](docs/README.md).

## Development Status

This repository is actively evolving around:

- structured review contracts
- evidence and visibility-aware review behavior
- evaluation and governance alignment
- implementation staging toward V1 formal-review goals

For implementation planning and staged delivery context, see:

- [`docs/20-design/008-v1-implementation-skeleton.md`](docs/20-design/008-v1-implementation-skeleton.md)
- [`docs/20-design/008-v1-pr1-pr8-workplan.md`](docs/20-design/008-v1-pr1-pr8-workplan.md)
- [`DELIVERY_REPORT.md`](DELIVERY_REPORT.md)
