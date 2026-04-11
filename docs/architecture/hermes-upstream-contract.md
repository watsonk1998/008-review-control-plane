# Hermes Upstream Contract

## Upstream Source of Truth

- Upstream repository: `https://github.com/NousResearch/hermes-agent.git`
- Tracking branch: `main`
- Current pinned commit: `af9caec44fdab7a1b883dede16fe1ce8c2d60fb9`
- Integration mode in this checkout: `submodule`

Pinning is required so the control plane does not silently drift with upstream internal changes.

## Physical Boundary

- `external/hermes-agent/` is the only approved physical location for upstream Hermes-Agent inside this repository
- upstream Hermes code must not be copied into `apps/api/src/`
- shell-side integration must happen through documented contracts and adapters

## Allowed Integration Surface to Upstream

The control plane may integrate upstream Hermes through these stable shell-facing surfaces:

- `HermesReviewEngine` contract
- `HermesExternalAdapter`
- `HermesLLMAdapter`
- `HermesRouterAdapter`
- Hermes review request / response schema
- template payload contract
- candidate template metadata contract

These are the permitted boundary objects for connecting the shell to the kernel.

## Local Shell Responsibilities

The following remain **local control-plane responsibilities**, not upstream surfaces:

- `HermesController`
- `HermesReviewAssembler`
- module binding policy
- template registry governance
- final result contract

## Forbidden Dependency Surface

Local business logic must not directly depend on unstable upstream internals such as:

- `run_agent.py` conversation-loop internals
- `model_tools.py` tool discovery / execution internals
- `agent/` internal implementation details
- `gateway/` internal implementation details
- upstream `tools/` internal implementation details
- runtime assumptions based on upstream cwd layout
- ad hoc `sys.path` injection into `external/hermes-agent/`

## Upgrade Workflow

1. `git submodule update --init --recursive`
2. review current upstream release notes or target commit
3. `cd external/hermes-agent`
4. `git fetch origin`
5. `git checkout <new-pinned-commit>`
6. `cd ../..`
7. update `config/hermes_upstream.yaml`
8. run `make verify-hermes-boundary`
9. review any contract breakage in request/response shape, routing assumptions, or metadata conventions
10. if breaking changes exist, update shell-side adapters/contracts first, then record the new gitlink in the parent repo

Breaking change handling rule:

- never “follow upstream first and fix later” without recording the compatibility impact

## Patch Policy

- `external/hermes-agent/` must remain pristine by default
- if patching is unavoidable, do not keep undocumented manual edits in the submodule worktree
- patches must be managed through one of:
  - `patches/hermes-agent/0001-*.patch`
  - `patches/hermes-agent/0002-*.patch`
  - a documented fork/upgrade workflow
- every patch record must state:
  - why upstream patching was necessary
  - what shell-side alternative was rejected
  - how to reapply after upgrade
  - how to roll back

## Compatibility Matrix

| control plane | hermes upstream pin | adapter contract | template schema | final packet schema |
|---|---|---|---|---|
| current shell baseline | `af9caec44fdab7a1b883dede16fe1ce8c2d60fb9` | `v1` | `v1` | `v1` |
