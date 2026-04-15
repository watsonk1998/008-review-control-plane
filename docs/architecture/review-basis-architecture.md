# Review Basis Architecture

This document dictates how external knowledge (laws, national standards, local rules, and enterprise standards) is managed, verified, and supplied to the review agents.

## 1. Physical Representation

The authoritative basis documents are stored centrally in the local workspace or a defined external block-storage target, tracked by registry files. The default path for source of truth is:

```
knowledge/review_basis/
  ├── laws/                    # 法律法规
  ├── national_standards/      # 国家标准
  ├── industry_standards/      # 行业标准
  ├── local_standards/         # 地方标准
  ├── enterprise/              # 企业规范
  └── project_overrides/       # 项目临时补充依据
```

- These are the **normative entities** (PDFs, Markdown conversions, XML structures), distinct from the code logic.
- They are NEVER to be stored within `external/hermes-agent/` or read implicitly from `fixtures/` as formal evaluation material.

## 2. Basis Registry Governance

Each basis file must be registered in the `config/review_basis/basis_registry.yaml` with explicit metadata to ensure agents are operating on a controlled reality:

- `basis_id`: The unique slug of the basis (e.g. `gb.55003.2021`)
- `title`: Human-readable title
- `source_type`: One of [law, national_standard, industry_standard, local_standard, enterprise, project_override]
- `version`: Designation or revision
- `effective_status`: One of [active, deprecated, pending]
- `jurisdiction`: Where it applies (e.g. 'National', 'Shenzhen', 'China Southern Power Grid')
- `file_refs`: Explicit pointers to the stored file paths
- `applicability_tags`: Tags for routing
- `owner`: Originator/Maintainer
- `freshness_rule`: Cadence for recertifying validity.

## 3. Metadata Degradation policy

When an agent operates on a review brief, the `BasisPackResolver` verifies the required basis IDs.
- **Fail Explicit**: If a basis document is deprecated or missing, it must explicitly signal to the execution loop and the end-user via the `degraded` metadata flag. 
- **No Silent Ignore**: Missing pages, conflicting versions, or unreadable formats must escalate as `visibility_gap`, preventing the agent from silently treating unknown material as implicitly compliant.

## 4. Promotion from Knowledge to Rule

A "Basis" (the raw document) is wrapped into a "Rule Pack" to extract actual execution constraints via `config/review_basis/rule_pack_registry.yaml`.
1. The basis document is registered.
2. Rule logic is authored down into `rule_pack_registry.yaml` mapping it to specific `basis_ids`.
3. The `rule_pack` defines `evidence_requirements` (what to look for) and maps it back to the original `basis_id` for citation generation. 

**Prohibited Methods**:
- Using LLM Adapters to read the entire corpus of laws text implicitly.
- Writing Python `if x else y` blocks inside adapters to match `documentType` directly to raw `basis` file paths.
