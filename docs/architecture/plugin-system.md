# Plugin System Architecture

## Purpose

The plugin system exists so domain-specific review capability can evolve in the **control-plane shell** without modifying the Hermes upstream kernel.

Hermes shell responsibilities stay focused on:

- main review control
- orchestration
- assembler output shaping
- template governance
- plugin/pack governance

Laws, standards, validity checking, and citation enhancement belong to the shell-side support layer.

## Recommended Directory Structure

```text
apps/api/src/review/
  hermes/
    controller.py
    assembler.py
    module_bindings.py
    template_registry.py
    templates/

  rules/
    engine.py
    packs/
      laws/
      standards/
      scenarios/
      company_policies/

  evidence/
    source_registry.py
    citation_builder.py
    validity/
      interface.py
      local_pack_checker.py
      company_library_checker.py
      standard_library_checker.py

  plugins/
    registry.py
    interfaces.py
    law_pack_provider.py
    standard_pack_provider.py
    validity_checker_plugin.py
    citation_enricher_plugin.py
```

## Placement Rules

- reviewer templates and Hermes orchestration policy stay under `review/hermes/`
- law packs belong under `review/rules/packs/laws/`
- standard/specification packs belong under `review/rules/packs/standards/`
- company policy packs belong under `review/rules/packs/company_policies/`
- evidence source and citation logic belong under `review/evidence/`
- validity checkers belong under `review/evidence/validity/` or plugin wrappers under `review/plugins/`
- connectors to company libraries or external standards libraries belong in shell-side plugin/provider layers

None of these should be implemented by modifying the Hermes upstream kernel.

## Runtime Chain

The intended shell-side runtime chain is:

1. review profile recognition
2. applicable pack selection
3. source registry resolution
4. validity checker returns freshness / applicability metadata
5. citation builder enriches references
6. assembler emits the final report with structured citations

## Manifest / Registry Contract

Each plugin or pack should expose a manifest shape with at least:

- `plugin_id`
- `plugin_type`
- `version`
- `applicable_profiles`
- `depends_on`

Registry responsibilities:

- discover local plugins / packs
- load only compatible plugins for the active profile
- expose typed capabilities to the review pipeline
- keep plugin metadata separate from official output shaping

Plugins should be able to provide one or more of:

- rule packs
- evidence sources
- validity metadata
- citation enrichment

## Governance Principle

New domain capability should be added as:

1. a rule pack
2. an evidence source
3. a validity checker
4. a citation enricher
5. a registry-managed plugin

Case-specific kernel patching is the last resort, not the default.
