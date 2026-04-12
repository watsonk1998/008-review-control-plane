# Official Result Contract Governance

This document hardens the contract ownership for the `008-review-control-plane`. 

## 1. Single Path for Public Results

There is exactly one official final result schema (`FinalReportPacket`) and it is generated exclusively by the shell layer's `FinalReportAssembler`.

- Experimental features, runtime templates, or candidate rule changes cannot bypass the Assembler to mutate the public output.
- Upstream Hermes API payloads do not define the 008 API response. 

## 2. Support Material Demotion

The legacy structures originating from the 008 processing layer (`StructuredReviewCapabilityFacade`, `FactPacketAdapter`, `SupportPacketBuilder`) are formally demoted to **advisory support layers**:
- They must carry the metadata `ownership='support_material'`.
- Any legacy final conclusion fields (`verdict`, `final_grade`, `official_decision`) are aggressively stripped before reaching the Hermes Assembler.
- The `SupportPacketBuilder` extracts facts, evidence, rule hits, and visibility gaps, but never formal verdicts.

## 3. Fail-Closed Policy & Formal Degradation

If the primary Hermes judgment engine is unresponsive, fails, or produces empty results (`hermes_review_packets == 0`), the system MUST **Fail-Closed**.

- **No Masking**: The support layer `008` results MUST NOT be automatically promoted to resemble a formal `FinalReportPacket`.
- **Degraded Statuses**: The API strictly returns precheck data, supportive evidence, or an explicit "Main Review Aborted" state.

## 4. User-Visible Constraints & Phrasing (Chinese First)

The ultimate consumer of the `008-review-control-plane` expects highly accurate, Chinese-language compliance output.

**Hard Restrictions**:
1. All user-visible frontend components, textual markdown reports, degradation statuses, and notifications MUST default to natural, professional **Chinese**. No raw english API keys or JSON internal references.
2. Generated copy should be natural, restrained, and professional (avoiding robotic LLM idioms or excessive marketer tone).
3. **Immutability of Facts**: Under the pretense of "polishing", the final assembler or final report generator MUST NEVER mutate underlying factual determinations. It is forbidden to alter the number of findings, severity tier, source evidence, or article citations while rewriting tone.

## 5. Schema Freeze & Tooling Verification

Core schema invariants (e.g. `final_grade`, `executive_summary`, `top_risks`, `supplemental_findings`) require version-bumping and coordination. 

Automated pipeline checks in `verify_hermes_boundary.py` scan the Python code to ensure:
- Support layers do not assign formal verdict variables.
- Chinese UI requirements are implicitly respected in templates.
- The boundary between Hermes kernel payload and FinalReportPacket is maintained.
