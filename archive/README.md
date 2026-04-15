# Archive Directory

This directory stores historical implementation code, design documents, prompts, and temporary data dumps that no longer belong in the active repository tree.

**Rule of Thumb:**
Items here are preserved strictly for historical tracing. **They must NOT be re-imported into the active codebase.** If an old capability needs to be restored, its underlying functionality should be re-implemented via the formal rule registries rather than reviving these old scripts.

---

## Controlled Archiving Manifest (Last Updated: 2026-04-13)

### 1. Old Debug Scripts
**`archive/tests/debug_presentation_agent.py`**
- **Original Path:** `apps/api/tests/debug.py`
- **Archival Reason:** Purely standalone debugging harness used during early Hermes review UI development. Does not hook into formal Pytest boundaries and possesses hardcoded mocking.
- **Substitution:** Formal evaluation is now completely covered by Pytest configurations in `test_hermes_presentation_agent.py` and structured CI stage gates.
- **Strict Constraint:** PROHIBITED from being restored to active path.

### 2. Historical Evaluation Reports
**`archive/experiments/evaluation_history/`**
- **Original Path:** `fixtures/supervision/V0.X-*`, `fixtures/supervision/gemini-deepresearch*`
- **Archival Reason:** Outdated artifacts and manual evaluation transcripts generated early in the product lifecycle (before structured evaluation pipelines existed). Obstructs readability of the `fixtures` directory.
- **Substitution:** Superceded entirely by formal structured outputs inside the versioned test beds of `fixtures/review_eval/`.
- **Strict Constraint:** PROHIBITED from being restored to active path.

### 3. Historical LLM Prompts & Instruction Drafts
**`archive/prompts/任务书/`**
- **Original Path:** `fixtures/任务书/*-prompt.md`, `*prompt.md`
- **Archival Reason:** Raw markdown prompts representing ad-hoc communications and task assignments to auxiliary GPTs during early development.
- **Substitution:** Modern review protocols are loaded from formal YAML governance files (e.g. `rule_pack_registry.yaml` and `profile_mapping.yaml`), effectively rendering offline standalone prompts obsolete.
- **Strict Constraint:** For historical reference only. PROHIBITED from being loaded onto any default review paths.

### 4. Historical Design Documents & Boundary Drafts 
**`archive/docs_history/任务书/`**
- **Original Path:** `fixtures/任务书/*.md` (excluding pure prompts) & `fixtures/任务书/archive/`
- **Archival Reason:** Historical records of product planning decisions, boundary drafts, and research conclusions generated during the `V0.1` -> `V0.3` product phase.
- **Substitution:** The definitive architectural truth rests exclusively within the `docs/20-design/` and `docs/10-governance/` architectures. These old snapshots provide historical progression insights only.
- **Strict Constraint:** Kept strictly for context. MUST NOT be cited as active architectural laws.
