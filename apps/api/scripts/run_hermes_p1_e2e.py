"""
Minimal E2E Runner for Hermes External Review.
Tests the P1 Goal:
1. Real Hermes Server connection
2. Dual Review orchestrator correctly triggers it
3. Generates the 4 required artifacts
4. Verify fallback logic on connection failure
"""
import sys
import os

# Ensure src can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import json
from src.review.contracts import ReviewBrief
from src.adapters.hermes_external_adapter import HermesExternalAdapter
from src.review.dual_review_orchestrator import DualReviewOrchestrator

def minimal_008_result():
    return {
        'issues': [
            {
                'id': 'ISSUE-001',
                'title': 'The main structure is missing critical details',
                'severity': 'high',
                'layer': 'L1',
                'findingType': 'hard_defect',
                'issueKind': 'hard_defect',
                'summary': 'A key section is entirely missing.',
                'manualReviewNeeded': False,
                'evidenceMissing': False,
                'docEvidence': [],
                'policyEvidence': [],
                'recommendation': ['Add the missing details.'],
                'confidence': 'high',
            }
        ],
        'summary': {
            'overallConclusion': 'Needs revision.',
        },
        'capabilitiesUsed': ['structured_review'],
    }

async def run_e2e():
    print("=== [Phase 1: Real External Hermes] ===")
    
    brief = ReviewBrief(
        review_id='hermes-e2e-real',
        review_object_type='construction_org',
        target_files=[{'path': 'dummy.pdf', 'type': 'pdf', 'name': 'dummy.pdf'}],
        focus_pack={'discipline_tags': ['safety']},
        review_policy={'strict_mode': True},
        query='Please review this document for structural and safety issues.',
    )
    
    adapter_real = HermesExternalAdapter(endpoint="http://127.0.0.1:8088")
    health = await adapter_real.health_check()
    print(f"Health check for real endpoint (8088): {health}")
    
    orch = DualReviewOrchestrator(hermes_engine=adapter_real)
    
    artifacts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "e2e_artifacts"))
    os.makedirs(artifacts_dir, exist_ok=True)
    
    def write_artifact(name, payload):
        path = os.path.join(artifacts_dir, f"{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            if isinstance(payload, str):
                f.write(payload)
            else:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f" -> Artifact written: {name}.json")
        
    def _emit(stage, cap, status, msg):
        print(f"[{stage}] {cap} - {status}: {msg}")

    print("Orchestrating Real Request...")
    result_real = await orch.orchestrate(
        review_brief=brief,
        result_008=minimal_008_result(),
        document_preview="This is the mock text for the construction doc. Contains building plans.",
        emit=_emit,
        write_json_artifact=write_artifact
    )
    
    dr = result_real.get("dualReview", {})
    print(f"\nReal Dual Review Result:")
    print(f" Engines Used: {dr.get('enginesUsed')}")
    print(f" Final Grade: {dr.get('finalGrade')}")
    print(f" Hermes Degraded: {dr.get('hermesDegraded')}")
    print(f" Fusion Report Markdown Length: {len(dr.get('fusionReportMarkdown', ''))} chars")

    print("\n=== [Phase 2: Fallback Logic] ===")
    
    brief_fail = ReviewBrief(
        review_id='hermes-e2e-fail',
        review_object_type='construction_org',
        target_files=[{'path': 'dummy.pdf', 'type': 'pdf', 'name': 'dummy.pdf'}],
        focus_pack={'discipline_tags': ['safety']},
        review_policy={'strict_mode': True},
        query='Review for issues.',
    )
    
    adapter_fail = HermesExternalAdapter(endpoint="http://127.0.0.1:9999")
    health_fail = await adapter_fail.health_check()
    print(f"Health check for unreachable endpoint (9999): {health_fail}")
    
    orch_fail = DualReviewOrchestrator(hermes_engine=adapter_fail)
    
    def write_artifact_fail(name, payload):
        path = os.path.join(artifacts_dir, f"fail_{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            if isinstance(payload, str):
                f.write(payload)
            else:
                json.dump(payload, f, ensure_ascii=False, indent=2)

    print("Orchestrating Fallback Request...")
    result_fail = await orch_fail.orchestrate(
        review_brief=brief_fail,
        result_008=minimal_008_result(),
        document_preview="Blah",
        emit=_emit,
        write_json_artifact=write_artifact_fail
    )
    
    dr_fail = result_fail.get("dualReview", {})
    print(f"\nFallback Dual Review Result:")
    print(f" Engines Used: {dr_fail.get('enginesUsed')}")
    print(f" Final Grade: {dr_fail.get('finalGrade')}")
    print(f" Hermes Degraded: {dr_fail.get('hermesDegraded')}")
    print(f" Degradation Info: {dr_fail.get('degradationInfo')}")

if __name__ == "__main__":
    asyncio.run(run_e2e())
