# Hermes Memory Configuration — Overlay

Memory and knowledge retrieval configuration for the local Hermes kernel.

## Status

- Bootstrap / sample only
- No memory configuration is actively loaded by the kernel yet

## Future Usage

The `HermesKernelLauncher` will pass this directory to the kernel subprocess,
allowing it to configure knowledge retrieval, context window management,
and session memory behavior.
