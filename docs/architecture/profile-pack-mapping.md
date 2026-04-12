# Profile and Pack Mapping

This document details the configuration-driven translation from a user's task intent to concrete review engine instructions. 

## 1. The Resolution Chain

The mapping follows a strict resolution chain managed by the `ProfileResolver` and `BasisPackResolver`. Adapters and LLMs have no role in this resolution.

```text
Classification (Level 1 / 2 / 3 schemes) + Intent
  ↓
profile_id
  ↓
Mapped via config/review_basis/profile_mapping.yaml
  ↓
Pack Definitions (default, required, optional, enterprise overrides)
  ↓
Mapped via config/review_basis/pack_registry.yaml
  ↓
Rule Packs 
  ↓
Mapped via config/review_basis/rule_pack_registry.yaml
  ↓
Basis Documents (Laws/Standards)
```

## 2. Configuration Source of Truth

The mapping isn't handled via Python code constants or Prompt rules. It is tightly configured in the yaml registries within `config/review_basis/`. 

This guarantees:
- Any new three-level scheme instantly inherits its associated rules.
- 1st Level (General Plan), 2nd Level (Special Scheme), 3rd Level (Specific discipline, e.g., Scaffolding) automatically resolve their profiles without touching Python logic.
- Optional / localized variations (e.g., local regulations vs national regulations) can be merged dynamically before review execution.
- Enterprise-specific enhancements can be layered automatically over national defaults.

## 3. Profile Definition Structure

A mapping definition typically looks like:

```yaml
profile_id: special_scheme.dangerous.deep_excavation
classification:
  level1: "专项施工方案审查"
  level2: "危大工程专项方案"
  level3: "基坑工程"

default_pack_ids:
  - "cn.mohurd.2021.48"
  - "gb.50202.2018"

optional_pack_ids:
  - "local.deep_excavation.sz.v1"

enterprise_pack_ids:
  - "enterprise.deep_excavation.v1"
```

## 4. Strict Isolation

The resulting profile and its merged packs are provided to BOTH the `SupportPacketBuilder` (driving legacy 008 evidence extraction) and the `Hermes Controller` (directing the local kernel). 

- **No Overstepping**: Neither engine possesses hardcoded knowledge about three-level schemes. They execute strictly what the Resolver provides.
- **Fail Close Validation**: If a `documentType` dictates files that are missing or invalid in the `basis_registry`, the resolver stops the formal report generation.
