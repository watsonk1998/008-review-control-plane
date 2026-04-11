# Hermes Kernel Config — Overlay

Kernel launch configuration overrides for the local Hermes agent.

## Status

- Bootstrap / sample only
- No configuration is actively loaded by the kernel yet

## Future Usage

The `HermesKernelLauncher` will inject these configuration overrides
when spawning the kernel subprocess. Typical overrides include:
- LLM provider routing (which model endpoint to use)
- Timeout and resource limits
- Tool registration policies
- Logging and tracing configuration
