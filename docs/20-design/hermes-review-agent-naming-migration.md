# Hermes Review Agent Naming Migration

This document records naming changes introduced during the Hermes review-agent shrink.
PR1 records the migration map without forcing import-path churn; PR2/PR3 apply the runtime-safe renames.

## Canonical direction

- `apps/api/src/adapters/hermes_llm_adapter.py` -> `hermes_llm_fallback_engine.py`
- `apps/api/src/adapters/hermes_router_adapter.py` -> `hermes_review_engine_router.py`
- `apps/api/src/review/contracts.py` -> `review_bridge_contracts.py`
- `apps/api/src/review/report_fusion.py` -> `final_report_merger.py`
- `apps/api/src/review/hermes/templates/structure_completeness_reviewer.json` -> `structured_review_primary_worker.json`
- `apps/api/src/review/dual_review_orchestrator.py` -> `legacy_posthoc_dual_review.py`

## Notes

- `contracts.py`, `task_compiler.py`, `fact_packet_adapter.py`, `hermes_llm_adapter.py`, and the legacy serializer path are freeze-boundary files.
- Template selection now uses `structured_review_primary_worker` as the canonical primary worker ID, with one-PR internal alias support for `structure_completeness_reviewer`.
- `final_report_merger.py` is an assembler-internal helper name for packet fusion; `HermesReviewAssembler` is the only official final output entrypoint.
