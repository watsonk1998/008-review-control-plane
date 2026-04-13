"""
测试类 2：正式结果所有权测试

验证:
- assembler 是唯一正式结果出口
- presentation 不再覆盖正式输出
- support payload 不再默默主导成功结果
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

from src.review.contracts import (
    FactPacket,
    FinalReportPacket,
    FindingItem,
    ReviewBrief,
    ReviewPacketMetrics,
)
from src.review.hermes.assembler import HermesReviewAssembler


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _make_brief(**overrides) -> ReviewBrief:
    defaults = dict(
        review_id="test_ownership_123",
        review_object_type="construction_org",
        task_parameters={},
        file_attachments=[],
        rule_pack_ids=[],
    )
    defaults.update(overrides)
    return ReviewBrief(**defaults)


def _make_support_packet(review_id: str = "test_ownership_123") -> FactPacket:
    return FactPacket(
        review_id=review_id,
        engine="008",
        summary_metrics=ReviewPacketMetrics(
            total_findings=2,
            high_severity=1,
            medium_severity=1,
            low_severity=0,
            info_findings=0,
            grounded_findings=2,
            evidence_gap_findings=0,
            manual_review_needed=0,
        ),
        findings=[
            FindingItem(id="S-1", severity="high", title="Support finding HIGH"),
            FindingItem(id="S-2", severity="medium", title="Support finding MEDIUM"),
        ],
        produced_at=datetime.now(timezone.utc),
        metadata={"ownership": "support_material"},
    )


def _make_hermes_packet(review_id: str = "test_ownership_123") -> FactPacket:
    return FactPacket(
        review_id=review_id,
        engine="hermes",
        summary_metrics=ReviewPacketMetrics(
            total_findings=1,
            high_severity=0,
            medium_severity=1,
            low_severity=0,
            info_findings=0,
            grounded_findings=1,
            evidence_gap_findings=0,
            manual_review_needed=0,
        ),
        findings=[
            FindingItem(id="H-1", severity="medium", title="Hermes deep finding"),
        ],
        overall_assessment="Hermes completed main review.",
        produced_at=datetime.now(timezone.utc),
        metadata={"ownership": "hermes_main_review", "template_id": "hermes_main"},
    )


# ---------------------------------------------------------------------------
# Test 1: Authoritative final report is from assembler only
# ---------------------------------------------------------------------------

def test_authoritative_final_report_is_from_assembler_only():
    """成功路径中 finalReportMarkdown 和 finalAnswer 必须来自 assembler。

    assembler.assemble() 返回的 payload 中的 finalReportMarkdown / finalAnswer
    必须等于 FinalReportPacket.report_markdown。
    """
    assembler = HermesReviewAssembler()
    brief = _make_brief()
    support_packet = _make_support_packet()
    hermes_packet = _make_hermes_packet()

    payload, final_packet = assembler.assemble(
        brief=brief,
        support_packet_008=support_packet,
        hermes_review_packets=[hermes_packet],
        support_result_008={"some_support_field": "should_not_leak_to_root"},
        agent_results=[],
    )

    assert final_packet is not None, "assembler must produce a FinalReportPacket on success"
    assert payload["finalReportMarkdown"] == final_packet.report_markdown, (
        "finalReportMarkdown does not match assembler's report_markdown"
    )
    assert payload["finalAnswer"] == final_packet.report_markdown, (
        "finalAnswer does not match assembler's report_markdown"
    )

    # Verify assembler metadata stamp
    assert final_packet.metadata.get("final_output_entrypoint") == "hermes_review_assembler"
    assert final_packet.metadata.get("decision_owner") == "hermes"


# ---------------------------------------------------------------------------
# Test 2: Presentation output does not override final report
# ---------------------------------------------------------------------------

def test_presentation_output_does_not_override_final_report():
    """hermes_controller.py 中的 presentation 结果必须仅存入附加字段，
    不能覆盖 finalReportMarkdown / finalAnswer。

    我们通过检查 controller 源代码中的赋值逻辑来验证。
    """
    import ast
    from pathlib import Path

    controller_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "review"
        / "hermes_controller.py"
    )
    source = controller_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    # Find all assignments to enriched['finalReportMarkdown'] and enriched['finalAnswer']
    presentation_overwrites_final = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Subscript)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "enriched"
                    and isinstance(target.slice, ast.Constant)
                    and target.slice.value in ("finalReportMarkdown", "finalAnswer")
                ):
                    # Check if the value references presentation_result
                    source_segment = ast.get_source_segment(source, node.value)
                    if source_segment and "presentation_result" in source_segment:
                        presentation_overwrites_final.append(
                            f"Line {node.lineno}: enriched['{target.slice.value}'] = {source_segment}"
                        )

    assert not presentation_overwrites_final, (
        "Presentation output still overwrites authoritative final report fields:\n"
        + "\n".join(presentation_overwrites_final)
    )


# ---------------------------------------------------------------------------
# Test 3: Success payload not rooted in support_result by default
# ---------------------------------------------------------------------------

def test_success_payload_not_rooted_in_support_result_by_default():
    """成功路径中的 formal payload 不应以 support_result_008 为根 dict。

    support_result_008 的字段不应出现在 payload 顶层，
    应放入明确的子字段（如 supportLayerContext）。
    """
    assembler = HermesReviewAssembler()
    brief = _make_brief()
    support_packet = _make_support_packet()
    hermes_packet = _make_hermes_packet()

    # Inject distinctive support_result keys to detect root leakage
    support_result = {
        "__support_sentinel_key__": True,
        "supportSpecificData": {"detail": "value"},
        "legacy_field_should_not_be_root": 42,
    }

    payload, final_packet = assembler.assemble(
        brief=brief,
        support_packet_008=support_packet,
        hermes_review_packets=[hermes_packet],
        support_result_008=support_result,
        agent_results=[],
    )

    assert final_packet is not None

    # These support-specific keys must NOT be at payload root
    assert "__support_sentinel_key__" not in payload, (
        "support_result_008 sentinel key leaked to payload root"
    )
    assert "supportSpecificData" not in payload, (
        "support_result_008 field leaked to payload root"
    )
    assert "legacy_field_should_not_be_root" not in payload, (
        "support_result_008 field leaked to payload root"
    )

    # Support data should be in a dedicated sub-key if present
    if "supportLayerContext" in payload:
        assert payload["supportLayerContext"] == support_result

    # Formal keys must be present at root
    assert "finalReportMarkdown" in payload
    assert "finalAnswer" in payload
    assert "hermesController" in payload
    assert "traceability" in payload
