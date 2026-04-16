from __future__ import annotations

from pathlib import Path

from src.review.contracts import (
    FactPacket,
    FindingItem,
    ReviewBrief,
    ReviewPacketMetrics,
)
from src.review.fact_packet_adapter import FactPacketAdapter
from src.review.final_report_merger import FinalReportMerger

"""Tests for the assembler-internal final report merger helper.

These tests protect packet-fusion behavior only. They do not elevate FinalReportMerger
to an independent runtime entrypoint.
"""


def _mock_008_result() -> dict:
    return {
        "issues": [
            {
                "id": "ISSUE-001",
                "title": "施工组织设计缺少核心章节",
                "severity": "high",
                "layer": "L1",
                "findingType": "hard_defect",
                "issueKind": "hard_defect",
                "summary": "工程概况、部署、进度等核心章节缺失",
                "manualReviewNeeded": False,
                "evidenceMissing": False,
                "docEvidence": [],
                "policyEvidence": [],
                "recommendation": ["补齐工程概况等核心章节"],
                "confidence": "high",
            },
            {
                "id": "ISSUE-002",
                "title": "应急预案针对性不足",
                "severity": "medium",
                "layer": "L2",
                "findingType": "engineering_inference",
                "issueKind": "evidence_gap",
                "summary": "应急预案类型与主要危险源不完全匹配",
                "manualReviewNeeded": True,
                "evidenceMissing": False,
                "docEvidence": [],
                "policyEvidence": [],
                "recommendation": ["按主要危险源补齐对应事故类型"],
                "confidence": "medium",
            },
        ],
        "summary": {
            "overallConclusion": "文档存在结构性缺陷，需修改后重新提交。",
        },
        "capabilitiesUsed": ["structured_review"],
    }


def _mock_review_brief() -> ReviewBrief:
    return ReviewBrief(
        review_id="test-001",
        review_object_type="construction_org",
        target_files=[{"path": "/tmp/test.docx", "type": "docx", "name": "test.docx"}],
        focus_pack={"discipline_tags": ["safety"], "policy_pack_ids": []},
        review_policy={"strict_mode": True},
        query="审查施工组织设计",
    )


def test_fact_packet_adapter_still_bridges_008_result():
    packet = FactPacketAdapter().adapt("test-001", _mock_008_result())
    assert packet.engine == "008"
    assert packet.summary_metrics.total_findings == 2
    assert packet.findings[0].source_engine == "008"
    assert packet.overall_assessment == "文档存在结构性缺陷，需修改后重新提交。"


def test_final_report_merger_fuses_008_only_result():
    merger = FinalReportMerger()
    brief = _mock_review_brief()
    packet_008 = FactPacketAdapter().adapt("test-001", _mock_008_result())

    report = merger.prepare_decision_material(brief, packet_008, packet_hermes=None)

    assert report["engines_used"] == ["008"]
    assert len(report["key_findings"]) == 2
    assert len(report["supplemental_findings"]) == 0
    assert report["final_grade"] == "needs_revision"
    assert report["traceability"]
    assert report["report_markdown"]


def test_final_report_merger_keeps_hermes_only_findings_as_supplemental():
    merger = FinalReportMerger()
    brief = _mock_review_brief()
    packet_008 = FactPacketAdapter().adapt("test-001", _mock_008_result())

    hermes_packet = FactPacket(
        review_id="test-001",
        engine="hermes",
        findings=[
            FindingItem(
                id="H-001",
                title="资源投入不足",
                severity="medium",
                source_engine="hermes",
                category="completeness",
                evidence_status="inferred",
            )
        ],
        summary_metrics=ReviewPacketMetrics(total_findings=1, medium_severity=1),
    )

    report = merger.fuse(brief, packet_008, hermes_packet)

    assert "hermes" in report.engines_used
    assert len(report.key_findings) == 2
    assert len(report.supplemental_findings) == 1
    assert report.supplemental_findings[0].id == "H-001"


def test_runtime_live_path_does_not_directly_depend_on_final_report_merger():
    root = Path(__file__).resolve().parents[1] / "src"
    for relpath in [
        "orchestrator/deepresearch_runtime.py",
        "review/hermes_controller.py",
        "routes/tasks.py",
    ]:
        source = (root / relpath).read_text(encoding="utf-8")
        assert "FinalReportMerger" not in source
        assert "final_report_merger" not in source
