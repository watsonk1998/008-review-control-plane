# Hermes Review Skills — Overlay

Skills placed here will be injected into the local Hermes kernel
as custom tool registrations at launch time.

## Status

- Bootstrap / sample only
- No skills are actively loaded by the kernel yet

## Future Usage

The `HermesKernelLauncher` will pass this directory as the skills
overlay path to the kernel subprocess, allowing the kernel to
discover and register these tools.

## Sample Skill Format

```yaml
name: document_structure_validator
description: Validate construction plan document structure completeness
type: tool
parameters:
  - name: document_content
    type: string
    required: true
```
