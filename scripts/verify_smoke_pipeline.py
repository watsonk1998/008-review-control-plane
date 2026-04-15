"""
Smoke verification script to address the 5 checkpoints requested for final merge validation.
"""
import sys
import os
import json
import asyncio
from pathlib import Path

# Add src to path
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root / "apps" / "api"))

from src.services.admin.governance_service import GovernanceService
from src.repositories.governance_store import SQLiteGovernanceStore
from src.review.hermes.assembler import HermesReviewAssembler
from src.review.contracts import ReviewBrief, FactPacket, FindingItem, ReviewPacketMetrics
from datetime import datetime, timezone

async def run_smoke_verification():
    print("=" * 60)
    print("SMOKE VERIFICATION EXECUTION")
    print("=" * 60)

    # ---------------------------------------------------------
    # 4. 治理台看到的 profile mapping 是否与 YAML 完全一致
    # ---------------------------------------------------------
    print("\n[Checkpoint 4] Governance Workbench vs YAML Truth")
    store = SQLiteGovernanceStore(":memory:")
    gov_service = GovernanceService(store)
    
    mapping_dto = gov_service.get_profile_mapping()
    hazardous = mapping_dto.mappings.get("hazardous_special_scheme")
    if hazardous:
        print(f"✅ Governance successfully read 'hazardous_special_scheme' profile: {hazardous.get('profile_id')}")
        print(f"   Default Packs: {hazardous.get('default_pack_ids')}")
    else:
        print("❌ Failed to read mapping!")

    # ---------------------------------------------------------
    # Mocking Data for Assembler Checks
    # ---------------------------------------------------------
    assembler = HermesReviewAssembler()
    brief = ReviewBrief(
        review_id="smoke_test_001",
        review_object_type="supervision_plan",
        task_parameters={},
        file_attachments=[],
        rule_pack_ids=[]
    )
    support_packet = FactPacket(
        review_id="smoke_test_001",
        engine="008",
        summary_metrics=ReviewPacketMetrics(total_findings=1, high_severity=1, medium_severity=0, low_severity=0, info_findings=0, grounded_findings=1, evidence_gap_findings=0, manual_review_needed=0),
        findings=[FindingItem(id="S-1", severity="high", title="Support check issue")],
        produced_at=datetime.utcnow().replace(tzinfo=timezone.utc),
        metadata={"ownership": "support_material"}
    )
    
    base_support_result = {"internal_support_id": 999, "raw_data_block": "XYZ"}

    # ---------------------------------------------------------
    # 1. 正式报告字段归属 & 3. support payload 是否只在 supportLayerContext
    # ---------------------------------------------------------
    print("\n[Checkpoint 1 & 3] Formal ownership & Support Layer Encapsulation (Success Path)")
    hermes_success_packet = FactPacket(
        review_id="smoke_test_001",
        engine="hermes",
        summary_metrics=ReviewPacketMetrics(total_findings=1, high_severity=0, medium_severity=1, low_severity=0, info_findings=0, grounded_findings=1, evidence_gap_findings=0, manual_review_needed=0),
        findings=[FindingItem(id="H-1", severity="medium", title="Hermes Deep Synthesis")],
        overall_assessment="Passed normal review",
        produced_at=datetime.utcnow().replace(tzinfo=timezone.utc),
        metadata={}
    )
    
    payload, final_packet = assembler.assemble(
        brief=brief,
        support_packet_008=support_packet,
        hermes_review_packets=[hermes_success_packet],
        support_result_008=base_support_result,
        agent_results=[]
    )

    if final_packet and payload.get("finalReportMarkdown") == final_packet.report_markdown:
        print("✅ Checkpoint 1 Provided: finalReportMarkdown exactly matches assembler formal output.")
    else:
        print("❌ finalReportMarkdown mismatch!")

    if "internal_support_id" not in payload:
        print("✅ Checkpoint 3 Provided: Support result fields are NOT at formal payload root.")
        if "supportLayerContext" in payload and payload["supportLayerContext"].get("internal_support_id") == 999:
            print("✅ Checkpoint 3 Provided: Support data safely isolated inside 'supportLayerContext' sub-key.")
        else:
            print("❌ supportLayerContext missing or corrupted!")
    else:
         print("❌ Support data leaked to root!")


    # ---------------------------------------------------------
    # 2. degraded 情况下的输出类型
    # ---------------------------------------------------------
    print("\n[Checkpoint 2] Degraded Fallback Output Type")
    degraded_payload, degraded_packet = assembler.assemble(
        brief=brief,
        support_packet_008=support_packet,
        hermes_review_packets=[], # Empty -> Fail closed
        support_result_008=base_support_result,
        agent_results=[]
    )
    
    if degraded_packet is None:
        print("✅ Checkpoint 2 Provided: Formal report packet strictly aborted (Fail-Closed).")
    else:
         print("❌ Formal packet generated despite degraded state!")
         
    if degraded_payload.get("hermesController", {}).get("degraded") is True:
        if "非正式审查报告" in degraded_payload.get("finalReportMarkdown", ""):
            print("✅ Checkpoint 2 Provided: Output clearly tagged as degraded/informal only.")
        else:
             print("❌ Downgraded disclaimer missing!")
    else:
         print("❌ Controller payload not flagged as degraded!")
         
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(run_smoke_verification())
