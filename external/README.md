# External Dependencies Boundary

This directory hosts **externally owned components** that are integrated into the 008 review control plane without being absorbed into local business code.

## Hermes-Agent

- Path: `external/hermes-agent/`
- Upstream: `https://github.com/NousResearch/hermes-agent`
- Current mode in this checkout: **git submodule**
- Current pin: `af9caec44fdab7a1b883dede16fe1ce8c2d60fb9`

## Boundary Rules

- `external/hermes-agent/` is an **external kernel / review engine** boundary
- do **not** move upstream Hermes code into `apps/api/src/`
- do **not** rely directly on upstream internal modules from local business code
- do **not** keep long-lived business logic edits inside the submodule working tree

## Patch Policy

If an upstream patch is unavoidable:

- prefer `patches/hermes-agent/`
- or use a documented fork/upgrade workflow
- record rationale, compatibility risk, and rollback path in `docs/architecture/hermes-upstream-contract.md`

## Upgrade Guidance

Standard update flow:

1. `git submodule update --init --recursive`
2. `cd external/hermes-agent`
3. `git fetch origin`
4. `git checkout <new-pinned-commit>`
5. `cd ../..`
6. record the updated gitlink in the parent repository
7. run `make verify-hermes-boundary`

Verification commands:

- `git submodule status -- external/hermes-agent`
- `git ls-files --stage external/hermes-agent`
- `make verify-hermes-boundary`

Detailed contract and governance rules remain in:

- `docs/architecture/hermes-upstream-contract.md`
- `config/hermes_upstream.yaml`
