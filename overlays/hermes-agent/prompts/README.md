# Hermes Prompts — Overlay

Custom system prompts and role instructions for the local Hermes kernel.

## Status

- Bootstrap / sample only
- One sample prompt extracted from the LLM adapter for reference

## Contents

- `hermes_review_system_prompt.md` — the Hermes review system prompt,
  currently hardcoded in `apps/api/src/adapters/hermes_llm_adapter.py`.
  This copy serves as a reference for the future overlay-based prompt
  injection path. The original file in the adapter is NOT removed.

## Future Usage

The `HermesKernelLauncher` will make prompts from this directory available
to the kernel subprocess, replacing hardcoded prompts in adapter code.
