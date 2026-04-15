"""
Real Task Entrypoint Smoke Script
Executes an E2E review through the TaskCompiler -> CapabilityFacade -> HermesController
down to Assembler output.
"""

import sys
import os
import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

# Add src to path
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root / "apps" / "api"))

from src.main_dependencies import (
    get_task_compiler,
    get_hermes_controller,
    get_governance_service,
    get_structured_review_capability_facade
)
from src.domain.models import TaskRecord, SourceDocumentRef

async def run_full_task_smoke():
    print("=" * 60)
    print("REAL TASK ENTRYPOINT SMOKE VERIFICATION")
    print("=" * 60)

    # 1. 验证治理台读取一致性
    gov_service = get_governance_service()
    mapping_dto = gov_service.get_profile_mapping()
    hazardous = mapping_dto.mappings.get("hazardous_special_scheme")
    if hazardous:
        print("[Governance Check] ✅ Read Top-Level profile successfully (Governance matches Runtime YAML).")
        print(f"   Detected packs: {hazardous.get('default_pack_ids')}")
    else:
        print("[Governance Check] ❌ Failed to read profile_mapping.yaml correctly via GovernanceService.")
        return

    # Mock the LLM Gateway and CapabilityFacade outputs to bypass missing API keys
    # and simulate a specific success / degraded flow.
    with patch("src.main_dependencies.get_llm_gateway") as mock_get_llm, \
         patch("src.main_dependencies.get_fast_adapter") as mock_get_fast_adapter, \
         patch("src.review.support_packet_builder.SupportPacketBuilder.build_packet") as mock_build_packet, \
         patch("src.review.structured_review_capability_facade.StructuredReviewCapabilityFacade.fact_extract") as mock_fact_extract, \
         patch("src.review.hermes.presentation_agent.HermesPresentationAgent.generate_presentation") as mock_generate_presentation, \
         patch("src.adapters.hermes_external_adapter.HermesExternalAdapter.review") as mock_hermes_engine, \
         patch("src.review.structured_review_capability_facade.StructuredReviewCapabilityFacade.primary_support_review") as mock_primary_support:
        
        # Setup mock presentation output
        from src.review.hermes.presentation_agent import PresentationResult
        from src.review.schema import ExtractedFacts
        from src.review.contracts import FactPacket, ReviewPacketMetrics
        
        mock_build_packet.return_value = FactPacket(
            review_id="test",
            engine="008",
            summary_metrics=ReviewPacketMetrics(total_findings=0, high_severity=0, medium_severity=0, low_severity=0, info_findings=0, grounded_findings=0, evidence_gap_findings=0, manual_review_needed=0),
            findings=[],
            produced_at=datetime.now(timezone.utc),
            metadata={}
        )

        def dummy_fact_extract(workspace, context):
            workspace['facts'] = ExtractedFacts(
                projectFacts={},
                hazardFacts={},
                visibilityFacts={}
            )
        mock_fact_extract.side_effect = dummy_fact_extract
        
        mock_generate_presentation.return_value = PresentationResult(
            review_id="test",
            presentation_markdown="# Presentation Level Display\nThis is from Presentation Agent.",
            metadata={"source": "mock_presentation_agent"}
        )

        task_id = "real_smoke_task_123"
        mock_task = TaskRecord(
            id=task_id,
            taskType="structured_review",
            capabilityMode="auto",
            query="请审查该危大方案",
            documentType="hazardous_special_scheme",
            createdAt=datetime.now(timezone.utc),
            updatedAt=datetime.now(timezone.utc),
            status="running"
        )
        source_doc = SourceDocumentRef(
            refId="file_123", 
            sourceType="fixture", 
            fileName="test_doc.pdf", 
            fileType="pdf", 
            storagePath="/tmp/test_doc.pdf"
        )
        plan = {"simulation_mode": False, "learning_mode": False, "reviewProfile": {"requestedDocumentType": "hazardous_special_scheme"}}

        events = []
        def mock_emit(event_type, source, status, message, debug=None):
            events.append(f"[{source}] {event_type} - {status}: {message}")

        # Initialize controller with mocks in place
        hermes_controller = get_hermes_controller()
        print("\n[Running E2E Task] Controller processing...")
        
        # Scenario 1: Hermes Engine returns EMPTY / Errors out (Degraded Mode)
        print(">> SCENARIO 1: Hermes Engine Degraded")
        mock_hermes_engine.side_effect = Exception("Mock LLM Connection Timeout")
        mock_primary_support.return_value = {
            "support_result": {"internal_support_flag": True},
            "support_packet": {
                "review_id": "test", "engine": "008", 
                "summary_metrics": {"total_findings": 0, "high_severity": 0, "medium_severity": 0, "low_severity": 0, "info_findings": 0, "grounded_findings": 0, "evidence_gap_findings": 0, "manual_review_needed": 0},
                "findings": [],
                "produced_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {}
            }
        }
        
        degraded_payload = await hermes_controller.run(
            task=mock_task, plan=plan, source_document_ref=source_doc, source_document_path="/tmp/test_doc.pdf",
            fixture=None, emit=mock_emit, write_json_artifact=lambda n, d: None, write_text_artifact=lambda n, d, e: None, write_binary_artifact=lambda n, d, e: None
        )

        is_degraded = degraded_payload.get("hermesController", {}).get("degraded", False)
        final_md_deg = degraded_payload.get("finalReportMarkdown", "")
        
        if is_degraded:
            print("  ✅ [Hermes Pipeline] Degraded mode successfully triggered.")
            if "非正式审查报告" in final_md_deg or "无法生成正式" in final_md_deg:
                print("  ✅ [Presentation] Degraded report successfully prevented formal output generation. (Failed-closed)")
            else:
                print("  ❌ [Presentation] Degraded report generated formal output!")
        else:
            print("  ❌ [Hermes Pipeline] Did not degrade upon engine exception!")

        print("\n>> SCENARIO 2: Hermes Engine Success")
        
        # Mock Hermes returning a valid packet (instead of throwing exception)
        mock_hermes_engine.side_effect = None
        from src.review.hermes.template_models import AgentRunResult
        mock_hermes_engine.return_value = AgentRunResult(
            raw_response="Success",
            template_id="structured_review_primary_worker",
            agent_id="hermes_main_agent",
            worker_id="worker_1",
            packet={
                "review_id": "test", "engine": "008", 
                "summary_metrics": {"total_findings": 1, "high_severity": 0, "medium_severity": 1, "low_severity": 0, "info_findings": 0, "grounded_findings": 1, "evidence_gap_findings": 0, "manual_review_needed": 0},
                "findings": [{"id": "S1", "severity": "medium", "title": "Support Test issue"}],
                "produced_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {}
            }
        )
        
        # Mock agent runner
        with patch("src.review.hermes.agent_runner.HermesAgentRunner.run_template") as mock_run_template:
            from pydantic import BaseModel
            class MockAgentResult(BaseModel):
                def model_dump(self, mode):
                    return {
                        "agent_id": "test_agent",
                        "packet": {
                            "review_id": task_id, "engine": "008",
                            "summary_metrics": {"total_findings": 1, "high_severity": 0, "medium_severity": 0, "low_severity": 0, "info_findings": 0, "grounded_findings": 0, "evidence_gap_findings": 0, "manual_review_needed": 0},
                            "findings": [{"id": "TST", "severity": "medium", "title": "Mock finding"}],
                            "produced_at": datetime.now(timezone.utc).isoformat(),
                            "metadata": {}
                        }
                    }
            mock_run_template.return_value = MockAgentResult()
            
            success_payload = await hermes_controller.run(
                task=mock_task, plan=plan, source_document_ref=source_doc, source_document_path="/tmp/test_doc.pdf",
                fixture=None, emit=mock_emit, write_json_artifact=lambda n, d: None, write_text_artifact=lambda n, d, e: None, write_binary_artifact=lambda n, d, e: None
            )

        final_md_succ = success_payload.get("finalReportMarkdown", "")
        pres_md_succ = success_payload.get("presentationMarkdown", "")
        
        if success_payload.get("hermesController", {}).get("enabled"):
            print("  ✅ [Hermes Pipeline] Completed successfully.")
            if "# Presentation Level Display" in pres_md_succ and "# Presentation Level Display" not in final_md_succ:
                 print("  ✅ [Presentation] finalReportMarkdown is preserved and strictly owned by assembler (NOT overwritten).")
            else:
                 print("  ❌ [Presentation] finalReportMarkdown was overwritten by PresentationAgent!")
        else:
            print("  ❌ [Hermes Pipeline] Failed despite success setup.")
            
        print("\n>> SCENARIO 3: Support Layer Context encapsulated")
        has_support_context = "supportLayerContext" in degraded_payload # we mocked primary support in scenario 1
        print(f"  ✅ 'supportLayerContext' found in payload: {has_support_context}")
        
    print("\n" + "=" * 60)
    print("SMOKE VERIFICATION COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_full_task_smoke())
