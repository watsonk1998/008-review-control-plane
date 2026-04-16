"""
Regression tests for HermesReviewAssembler module-level gate.

Covers:
- 307075c16a7d 异常样本场景: execution_risk_reviewer degraded → 它是 parameter_consistency
  和 execution_continuity 唯一被运行的 reviewer → 两模块均被阻断 → fail-closed
- 正常样本场景: 所有 reviewer 正常运行 → 正式报告正常输出
- 部分降级但模块未被全阻断: 模块有多个 reviewer 被选中，其中一个 degraded，另一个正常 → 不阻断
- enabled_modules=None 时不触发模块级门禁
- 降级时 error_reason 不为空串
- _check_critical_module_blocks 细粒度单元测试
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from src.review.contracts import FactPacket, FindingItem, ReviewBrief, ReviewPacketMetrics
from src.review.hermes.assembler import HermesReviewAssembler


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _make_brief(review_id: str = "test-review") -> ReviewBrief:
    return ReviewBrief(
        review_id=review_id,
        query="审查",
        review_object_type="distribution_network_special_scheme",  # valid ReviewDocumentType
        metadata={},
    )


def _make_packet(
    template_id: str,
    *,
    degraded: bool = False,
    error: str = "",
    findings: list[FindingItem] | None = None,
) -> FactPacket:
    return FactPacket(
        review_id="test-review",
        engine="hermes",
        degraded=degraded,
        error=error if error else (f"{template_id} 降级" if degraded else ""),
        summary_metrics=ReviewPacketMetrics(total_findings=len(findings or [])),
        findings=findings or [],
        overall_assessment="ok",
        produced_at=datetime.now(timezone.utc),
        metadata={
            "template_id": template_id,
            "agent_id": template_id,
        },
    )


def _make_support_packet(review_id: str = "test-review") -> FactPacket:
    return FactPacket(
        review_id=review_id,
        engine="008",
        summary_metrics=ReviewPacketMetrics(total_findings=0),
        findings=[],
        overall_assessment="support done",
        produced_at=datetime.now(timezone.utc),
        metadata={"ownership": "support_material"},
    )


def _make_agent_result(
    template_id: str, *, degraded: bool = False, error: str = ""
) -> dict[str, Any]:
    packet: dict[str, Any] = {"degraded": degraded}
    if degraded:
        packet["error"] = error if error else f"{template_id} 审查组件降级，未返回有效结果"
    else:
        packet["error"] = None
    return {
        "agent_id": template_id,
        "template_id": template_id,
        "packet": packet,
    }


# ─────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────

def test_all_hermes_degraded_fails_closed():
    """全部 Hermes packet degraded → fail-closed，不输出正式报告 (全局判断路径)."""
    assembler = HermesReviewAssembler()
    brief = _make_brief()
    degraded_packet = _make_packet("execution_risk_reviewer", degraded=True, error="LLM timeout")

    payload, final_packet = assembler.assemble(
        brief=brief,
        support_packet_008=_make_support_packet(),
        hermes_review_packets=[degraded_packet, _make_packet("parameter_consistency_reviewer", degraded=True, error="LLM timeout")],
        support_result_008={},
        agent_results=[_make_agent_result("execution_risk_reviewer", degraded=True, error="LLM timeout"), _make_agent_result("parameter_consistency_reviewer", degraded=True, error="LLM timeout")],
        enabled_modules=["parameter_consistency", "execution_continuity"],
    )

    assert final_packet is None, "全部降级时不应输出正式报告"
    assert payload["hermesController"]["degraded"] is True
    assert payload["hermesController"]["finalReportReady"] is False
    assert "finalReportMarkdown" in payload
    assert payload["finalReportMarkdown"]  # 非空
    # degradedReason 非空
    assert payload["hermesController"].get("degradedReason"), "degradedReason 不得为空"


def test_module_level_gate_blocks_when_all_run_templates_degraded():
    """
    异常样本 307075c16a7d 场景:
    execution_risk_reviewer 是唯一被选中运行、且覆盖 parameter_consistency /
    execution_continuity 的 reviewer，其 degraded。
    其他 reviewer 正常。
    → 模块级门禁应阻断正式报告输出。
    """
    assembler = HermesReviewAssembler()
    brief = _make_brief()

    hermes_packets = [
        _make_packet("structured_review_primary_worker", degraded=False, findings=[
            FindingItem(id="F1", title="章节缺失", severity="high", category="chapter_completeness",
                        raw_data={"module_name": "structure_completeness"}),
        ]),
        _make_packet("policy_compliance_reviewer", degraded=False, findings=[
            FindingItem(id="F2", title="合规问题", severity="medium", category="compliance",
                        raw_data={"module_name": "legality_compliance"}),
        ]),
        # execution_risk_reviewer 和 parameter_consistency_reviewer 被隔离了
        _make_packet("execution_risk_reviewer", degraded=True, error="execution_risk_reviewer 审查组件降级"),
        _make_packet("parameter_consistency_reviewer", degraded=True, error="parameter_consistency_reviewer 审查组件降级"),
    ]

    agent_results = [
        _make_agent_result("structured_review_primary_worker", degraded=False),
        _make_agent_result("policy_compliance_reviewer", degraded=False),
        _make_agent_result("visibility_gap_reviewer", degraded=False),
        _make_agent_result("execution_risk_reviewer", degraded=True,
                           error="execution_risk_reviewer 审查组件降级"),
        _make_agent_result("parameter_consistency_reviewer", degraded=True,
                           error="parameter_consistency_reviewer 审查组件降级"),
        # power_outage_operation_chain_reviewer 未被选中运行（不在 agent_results 中）
    ]

    payload, final_packet = assembler.assemble(
        brief=brief,
        support_packet_008=_make_support_packet(),
        hermes_review_packets=hermes_packets,
        support_result_008={},
        agent_results=agent_results,
        enabled_modules=[
            "structure_completeness",
            "parameter_consistency",
            "legality_compliance",
            "execution_continuity",
        ],
    )

    # 应 fail-closed
    assert final_packet is None, (
        "执行风险和参数一致性组件 degraded，"
        "其 degraded 应触发模块级门禁，不输出正式报告"
    )
    assert payload["hermesController"]["degraded"] is True
    assert payload["hermesController"]["finalReportReady"] is False

    blocked = payload["hermesController"].get("blockedModules", [])
    assert "parameter_consistency" in blocked, f"parameter_consistency 应在 blockedModules 中，实际: {blocked}"
    assert "execution_continuity" in blocked, f"execution_continuity 应在 blockedModules 中，实际: {blocked}"

    reason = payload["hermesController"].get("degradedReason", "")
    assert reason, "degradedReason 不得为空字符串"
    assert "execution_risk_reviewer" in reason, f"degradedReason 应包含降级 reviewer 名称，实际: {reason!r}"
    assert payload.get("finalReportMarkdown"), "降级时仍应有 fallback markdown"


def test_module_gate_not_triggered_when_module_not_in_enabled_modules():
    """
    execution_risk_reviewer degraded，但 enabled_modules 只包含
    structure_completeness 和 legality_compliance（不依赖 execution_risk_reviewer）
    → 不应被模块级门禁阻断。
    """
    assembler = HermesReviewAssembler()
    brief = _make_brief()

    hermes_packets = [
        _make_packet("structured_review_primary_worker", degraded=False, findings=[
            FindingItem(id="F1", title="章节缺失", severity="high", category="chapter_completeness",
                        raw_data={"module_name": "structure_completeness"}),
        ]),
        _make_packet("policy_compliance_reviewer", degraded=False, findings=[
            FindingItem(id="F2", title="合规问题", severity="medium", category="compliance",
                        raw_data={"module_name": "legality_compliance"}),
        ]),
        _make_packet("execution_risk_reviewer", degraded=True, error="降级"),
    ]

    agent_results = [
        _make_agent_result("structured_review_primary_worker", degraded=False),
        _make_agent_result("policy_compliance_reviewer", degraded=False),
        _make_agent_result("execution_risk_reviewer", degraded=True, error="降级"),
    ]

    payload, final_packet = assembler.assemble(
        brief=brief,
        support_packet_008=_make_support_packet(),
        hermes_review_packets=hermes_packets,
        support_result_008={},
        agent_results=agent_results,
        # 只选了 structure_completeness 和 legality_compliance
        # execution_risk_reviewer 覆盖的 parameter_consistency / execution_continuity 不在合同中
        enabled_modules=["structure_completeness", "legality_compliance"],
    )

    assert final_packet is not None, (
        "enabled_modules 不包含 parameter_consistency/execution_continuity，"
        "execution_risk_reviewer degraded 不应触发门禁"
    )
    assert payload["hermesController"].get("finalReportReady") is True


def test_module_gate_not_triggered_when_only_partial_run_templates_degraded():
    """
    legality_compliance 绑定了多个 template：
    policy_compliance_reviewer 和 power_outage_normative_reviewer 等。
    两个都被选中运行，其中 policy_compliance_reviewer degraded，
    power_outage_normative_reviewer 正常。
    → 模块不被阻断，正式报告仍应输出。
    """
    assembler = HermesReviewAssembler()
    brief = _make_brief()

    hermes_packets = [
        _make_packet("policy_compliance_reviewer", degraded=True, error="降级"),
        _make_packet("power_outage_normative_reviewer", degraded=False, findings=[
            FindingItem(id="F3", title="规范问题", severity="medium", category="compliance",
                        raw_data={"module_name": "legality_compliance"}),
        ]),
    ]

    agent_results = [
        _make_agent_result("policy_compliance_reviewer", degraded=True, error="降级"),
        _make_agent_result("power_outage_normative_reviewer", degraded=False),
    ]

    payload, final_packet = assembler.assemble(
        brief=brief,
        support_packet_008=_make_support_packet(),
        hermes_review_packets=hermes_packets,
        support_result_008={},
        agent_results=agent_results,
        enabled_modules=["legality_compliance"],
    )

    assert final_packet is not None, (
        "legality_compliance 的部分 reviewer 仍正常时，整个模块不应被阻断"
    )


def test_module_gate_not_triggered_when_enabled_modules_is_none():
    """enabled_modules=None 时不触发模块级门禁（回退到全局判断）."""
    assembler = HermesReviewAssembler()
    brief = _make_brief()

    hermes_packets = [
        _make_packet("execution_risk_reviewer", degraded=True, error="降级"),
        _make_packet("policy_compliance_reviewer", degraded=False, findings=[
            FindingItem(id="F4", title="合规", severity="medium", category="compliance",
                        raw_data={"module_name": "legality_compliance"}),
        ]),
    ]

    agent_results = [
        _make_agent_result("execution_risk_reviewer", degraded=True, error="降级"),
        _make_agent_result("policy_compliance_reviewer", degraded=False),
    ]

    payload, final_packet = assembler.assemble(
        brief=brief,
        support_packet_008=_make_support_packet(),
        hermes_review_packets=hermes_packets,
        support_result_008={},
        agent_results=agent_results,
        enabled_modules=None,  # None → 不触发模块级门禁
    )

    # 全局不是全部 degraded，正式报告应该能输出
    assert final_packet is not None, "enabled_modules=None 时不触发模块级门禁"


def test_degraded_reason_never_empty_when_error_field_empty():
    """无论哪种降级路径，当 packet.error='' 时 degradedReason 也不能为空字符串."""
    assembler = HermesReviewAssembler()
    brief = _make_brief()

    # 场景：error 字段本身为空，degradedReason 应回退到有意义的描述
    hermes_packets = [
        _make_packet("execution_risk_reviewer", degraded=True, error=""),
    ]
    agent_results = [
        _make_agent_result("execution_risk_reviewer", degraded=True, error=""),
    ]

    payload, _ = assembler.assemble(
        brief=brief,
        support_packet_008=_make_support_packet(),
        hermes_review_packets=hermes_packets,
        support_result_008={},
        agent_results=agent_results,
        enabled_modules=["parameter_consistency", "execution_continuity"],
    )

    reason = payload["hermesController"].get("degradedReason", "")
    assert reason, (
        f"即使 packet.error 为空，degradedReason 也不得为空字符串，实际值: {reason!r}"
    )


def test_check_critical_module_blocks_unit():
    """直接测试 _check_critical_module_blocks 的细粒度行为."""
    assembler = HermesReviewAssembler()

    agent_results = [
        {"agent_id": "execution_risk_reviewer", "packet": {"degraded": True, "error": "timeout"}},
        {"agent_id": "parameter_consistency_reviewer", "packet": {"degraded": True, "error": "timeout"}},
        {"agent_id": "policy_compliance_reviewer", "packet": {"degraded": False, "error": None}},
    ]

    blocked, details = assembler._check_critical_module_blocks(
        enabled_modules=["parameter_consistency", "execution_continuity", "legality_compliance"],
        agent_results=agent_results,
    )

    assert "parameter_consistency" in blocked, f"parameter_consistency 应被阻断，实际 blocked={blocked}"
    assert "execution_continuity" in blocked, f"execution_continuity 应被阻断，实际 blocked={blocked}"
    assert "legality_compliance" not in blocked, f"legality_compliance 不应被阻断，实际 blocked={blocked}"

    assert details["parameter_consistency"]["title"] == "内容一致性"
    assert "parameter_consistency_reviewer" in details["parameter_consistency"]["degraded_templates"]
    err = details["parameter_consistency"]["errors"].get("parameter_consistency_reviewer", "")
    assert err, f"block detail error 应非空，实际: {err!r}"


def test_check_critical_module_blocks_not_blocked_when_second_template_succeeds():
    """模块有两个 runner 都被选中：一个降级一个正常 → 模块不被阻断."""
    assembler = HermesReviewAssembler()

    agent_results = [
        {"agent_id": "policy_compliance_reviewer", "packet": {"degraded": True, "error": "err"}},
        {"agent_id": "power_outage_normative_reviewer", "packet": {"degraded": False, "error": None}},
    ]

    blocked, _ = assembler._check_critical_module_blocks(
        enabled_modules=["legality_compliance"],
        agent_results=agent_results,
    )

    assert "legality_compliance" not in blocked, (
        "legality_compliance 有一个正常 reviewer，不应被阻断"
    )


def test_no_degradation_no_blocks():
    """所有 reviewer 正常时 _check_critical_module_blocks 返回空结果."""
    assembler = HermesReviewAssembler()

    agent_results = [
        {"agent_id": "execution_risk_reviewer", "packet": {"degraded": False, "error": None}},
        {"agent_id": "policy_compliance_reviewer", "packet": {"degraded": False, "error": None}},
    ]

    blocked, details = assembler._check_critical_module_blocks(
        enabled_modules=["parameter_consistency", "execution_continuity", "legality_compliance"],
        agent_results=agent_results,
    )

    assert blocked == []
    assert details == {}
