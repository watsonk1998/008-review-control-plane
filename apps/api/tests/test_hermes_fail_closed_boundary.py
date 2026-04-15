from datetime import datetime, timezone
from src.review.contracts import ReviewBrief, FactPacket, FindingItem, ReviewPacketMetrics
from src.review.hermes.assembler import HermesReviewAssembler

def test_no_formal_report_when_hermes_packets_empty():
    assembler = HermesReviewAssembler()
    
    brief = ReviewBrief(
        review_id="test_review_123",
        review_object_type="supervision_plan",
        task_parameters={},
        file_attachments=[],
        rule_pack_ids=[]
    )
    
    # Simulate a degraded support packet
    support_packet = FactPacket(
        review_id="test_review_123",
        engine="008",
        summary_metrics=ReviewPacketMetrics(total_findings=1, high_severity=1, medium_severity=0, low_severity=0, info_findings=0, grounded_findings=1, evidence_gap_findings=0, manual_review_needed=0),
        findings=[
            FindingItem(
                id="FINDING-1",
                severity="high",
                title="Support layer basic check failed",
                summary="Some problem found in pre-check",
            )
        ],
        produced_at=datetime.now(timezone.utc),
        metadata={"ownership": "support_material"}
    )
    
    # EMPTY hermes review packets -> Fail-Closed condition
    payload, packet = assembler.assemble(
        brief=brief,
        support_packet_008=support_packet,
        hermes_review_packets=[],
        support_result_008={},
        agent_results=[]
    )
    
    assert packet is None, "Formal packet MUST NOT be generated"
    assert payload["hermesController"]["finalReportReady"] is False, "Must signal not ready"
    assert payload["hermesController"]["degraded"] is True, "Must be flagged as degraded"
    assert "非正式审查报告" in payload["finalReportMarkdown"], "Fallback report must explicitly declare itself informal."
    assert "Support layer basic check failed" in payload["finalReportMarkdown"], "Should still show underlying facts for reference."

def test_no_formal_report_when_hermes_reports_degraded():
    assembler = HermesReviewAssembler()
    
    brief = ReviewBrief(
        review_id="test_review_123",
        review_object_type="supervision_plan",
        task_parameters={},
        file_attachments=[],
        rule_pack_ids=[]
    )
    
    degraded_hermes = FactPacket(
        review_id="test_review_123",
        engine="hermes",
        summary_metrics=ReviewPacketMetrics(total_findings=0, high_severity=0, medium_severity=0, low_severity=0, info_findings=0, grounded_findings=0, evidence_gap_findings=0, manual_review_needed=0),
        findings=[],
        degraded=True,
        error="LLM API Failure",
        produced_at=datetime.now(timezone.utc)
    )
    
    payload, packet = assembler.assemble(
        brief=brief,
        support_packet_008=None,
        hermes_review_packets=[degraded_hermes],
        support_result_008={},
        agent_results=[]
    )
    
    assert packet is None, "Formal packet MUST NOT be generated"
    assert payload["hermesController"]["degraded"] is True
    assert "LLM API Failure" in payload["finalReportMarkdown"]
    assert "非正式审查报告" in payload["finalReportMarkdown"]
