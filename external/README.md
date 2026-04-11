# External Dependencies Boundary

This directory hosts **externally owned components** that are integrated into the 008 review control plane without being absorbed into local business code.

## Hermes-Agent

- Path: `external/hermes-agent/`
- Upstream: `https://github.com/NousResearch/hermes-agent.git`
- Intended mode: **git submodule**
- Current mode in this checkout: **planned_submodule**
- Current pin: `af9caec44fdab7a1b883dede16fe1ce8c2d60fb9`

## Boundary Rules

- `external/hermes-agent/` is an **external kernel / review engine** boundary
- do **not** move upstream Hermes code into `apps/api/src/`
- do **not** rely directly on upstream internal modules from local business code
- do **not** keep long-lived manual edits inside the submodule working tree

## Patch Policy

If an upstream patch is unavoidable:

- prefer `patches/hermes-agent/`
- or use a documented fork/upgrade workflow
- record rationale, compatibility risk, and rollback path in `docs/architecture/hermes-upstream-contract.md`

## Upgrade Guidance

Use the upgrade workflow defined in:

- `docs/architecture/hermes-upstream-contract.md`
- `config/hermes_upstream.yaml`
