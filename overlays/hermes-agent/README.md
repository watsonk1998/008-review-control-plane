# Hermes-Agent Overlays

## What Are Overlays?

Overlays are **shell-side configuration assets** that will be injected into the Hermes local kernel at launch time by `HermesKernelLauncher`. They allow the 008 control plane to customize the upstream kernel's behavior without modifying the upstream source code inside `external/hermes-agent/`.

## Critical Distinction

| Layer | Location | Ownership |
|---|---|---|
| Upstream kernel source | `external/hermes-agent/` | NousResearch (pinned, read-only) |
| Shell-side overlays | `overlays/hermes-agent/` | 008 control plane (this repo) |
| Shell-side adapters | `apps/api/src/adapters/` | 008 control plane (this repo) |

**Overlays are NOT upstream kernel code.** They are business-specific configuration and assets that the launcher mounts into the kernel's execution context.

## Directory Structure

```
overlays/hermes-agent/
├── README.md           ← this file
├── skills/             ← custom tool/skill definitions for the kernel
├── memory/             ← knowledge/memory configuration for the kernel
├── config/             ← kernel launch configuration overrides
└── prompts/            ← custom system prompts and role instructions
```

## What Belongs Here

- ✅ Skill definitions (tool registration YAML/JSON for review-specific capabilities)
- ✅ Memory / knowledge retrieval configuration
- ✅ Kernel launch config overrides (e.g., model routing, timeout tuning)
- ✅ Custom system prompts / role prompts for review scenarios
- ✅ Environment variable templates for the kernel subprocess

## What Does NOT Belong Here

- ❌ Controller logic (`HermesController` stays in `apps/api/src/review/`)
- ❌ Assembler logic (`HermesReviewAssembler` stays in shell)
- ❌ Module binding policy
- ❌ Review contracts (`ReviewBrief`, `FactPacket`)
- ❌ Adapter implementations
- ❌ Any code that directly modifies the upstream kernel
- ❌ Business main-chain logic

## How Overlays Are Used

1. `HermesKernelLauncher` resolves the overlay root path at startup.
2. During kernel subprocess launch, overlay directories are injected via environment variables or CLI arguments.
3. The kernel reads these overlays to customize its tool set, prompts, and configuration.

**Current status**: The launcher supports `dry_run` and `smoke` modes that verify overlay resolution. Full overlay injection into a live kernel subprocess is not yet implemented.

## Relationship to Other Assets

- `config/hermes_upstream.yaml` — declares `overlay_root` pointing to this directory
- `apps/api/src/adapters/hermes_kernel_launcher.py` — resolves and validates this directory
- `apps/api/scripts/run_local_hermes_smoke.py` — exercises overlay resolution in smoke path
