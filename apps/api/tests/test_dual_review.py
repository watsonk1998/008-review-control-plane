"""Unit tests for the 008 + Hermes dual-path review integration."""

from __future__ import annotations

import asyncio
import pytest

from src.review.contracts import (
    FactPacket,
    FinalReportPacket,
    FindingItem,
    ReviewBrief,
    ReviewPacketMetrics,
)
from src.review.fact_packet_adapter import FactPacketAdapter
from src.review.report_fusion import ReportFusionService
from src.review.task_compiler import TaskCompiler
from src.adapters.hermes_adapter import HermesAdapter
from src.review.dual_review_orchestrator import DualReviewOrchestrator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _mock_008_result() -> dict:
    """Simulate a StructuredReviewResult dict from the 008 pipeline."""
    return {
        'issues': [
            {
                'id': 'ISSUE-001',
                'title': '施工组织设计缺少核心章节',
                'severity': 'high',
                'layer': 'L1',
                'findingType': 'hard_defect',
                'issueKind': 'hard_defect',
                'summary': '工程概况、部署、进度等核心章节缺失',
                'manualReviewNeeded': False,
                'evidenceMissing': False,
                'docEvidence': [],
                'policyEvidence': [],
                'recommendation': ['补齐工程概况等核心章节'],
                'confidence': 'high',
            },
            {
                'id': 'ISSUE-002',
                'title': '应急预案针对性不足',
                'severity': 'medium',
                'layer': 'L2',
                'findingType': 'engineering_inference',
                'issueKind': 'evidence_gap',
                'summary': '应急预案类型与主要危险源不完全匹配',
                'manualReviewNeeded': True,
                'evidenceMissing': False,
                'docEvidence': [],
                'policyEvidence': [],
                'recommendation': ['按主要危险源补齐对应事故类型'],
                'confidence': 'medium',
            },
        ],
        'summary': {
            'overallConclusion': '文档存在结构性缺陷，需修改后重新提交。',
        },
        'capabilitiesUsed': ['structured_review'],
    }


def _mock_review_brief() -> ReviewBrief:
    return ReviewBrief(
        review_id='test-001',
        review_object_type='construction_org',
        target_files=[{'path': '/tmp/test.docx', 'type': 'docx', 'name': 'test.docx'}],
        focus_pack={'discipline_tags': ['safety'], 'policy_pack_ids': []},
        review_policy={'strict_mode': True},
        query='审查施工组织设计',
    )


# ---------------------------------------------------------------------------
# contracts.py
# ---------------------------------------------------------------------------

class TestContracts:
    def test_review_brief_creation(self):
        brief = _mock_review_brief()
        assert brief.review_id == 'test-001'
        assert brief.review_object_type == 'construction_org'
        assert len(brief.target_files) == 1

    def test_fact_packet_degraded(self):
        packet = FactPacket(
            review_id='test-001',
            engine='hermes',
            error='timeout',
            degraded=True,
        )
        assert packet.degraded is True
        assert packet.error == 'timeout'
        assert packet.findings == []

    def test_finding_item_defaults(self):
        f = FindingItem(id='F-001', title='test', severity='high')
        assert f.source_engine == ''
        assert f.confidence == 'medium'
        assert f.evidence_status == 'grounded'


# ---------------------------------------------------------------------------
# fact_packet_adapter.py
# ---------------------------------------------------------------------------

class TestFactPacketAdapter:
    def test_adapt_basic(self):
        adapter = FactPacketAdapter()
        result = _mock_008_result()
        packet = adapter.adapt('test-001', result)

        assert packet.engine == '008'
        assert packet.review_id == 'test-001'
        assert len(packet.findings) == 2
        assert packet.summary_metrics.total_findings == 2
        assert packet.summary_metrics.high_severity == 1
        assert packet.summary_metrics.medium_severity == 1
        assert packet.findings[0].source_engine == '008'
        assert packet.findings[0].severity == 'high'
        assert packet.overall_assessment == '文档存在结构性缺陷，需修改后重新提交。'

    def test_adapt_empty(self):
        adapter = FactPacketAdapter()
        packet = adapter.adapt('empty', {'issues': [], 'summary': {}})
        assert packet.summary_metrics.total_findings == 0
        assert packet.findings == []

    def test_evidence_status_mapping(self):
        adapter = FactPacketAdapter()
        result = _mock_008_result()
        packet = adapter.adapt('test-001', result)
        assert packet.findings[0].evidence_status == 'grounded'  # hard_defect
        assert packet.findings[1].evidence_status == 'evidence_gap'  # evidence_gap kind


# ---------------------------------------------------------------------------
# hermes_adapter.py
# ---------------------------------------------------------------------------

class TestHermesAdapter:
    def test_not_available_without_gateway(self):
        adapter = HermesAdapter(llm_gateway=None)
        assert adapter.available is False

    def test_degraded_packet_on_no_gateway(self):
        adapter = HermesAdapter(llm_gateway=None)
        brief = _mock_review_brief()
        packet = asyncio.get_event_loop().run_until_complete(adapter.review(brief))
        assert packet.degraded is True
        assert packet.engine == 'hermes'
        assert 'not configured' in packet.error

    def test_json_parsing_with_code_fence(self):
        adapter = HermesAdapter(llm_gateway=None)
        raw = '```json\n{"overall_assessment": "ok", "grade": "conditional_pass", "findings": []}\n```'
        parsed = adapter._parse_json(raw)
        assert parsed['grade'] == 'conditional_pass'

    def test_json_parsing_fallback(self):
        adapter = HermesAdapter(llm_gateway=None)
        parsed = adapter._parse_json('not json at all')
        assert parsed['grade'] == 'needs_revision'
        assert parsed['findings'] == []


# ---------------------------------------------------------------------------
# report_fusion.py
# ---------------------------------------------------------------------------

class TestReportFusion:
    def test_fuse_008_only(self):
        """When Hermes is absent, all 008 findings become key findings."""
        fusion = ReportFusionService()
        brief = _mock_review_brief()
        adapter = FactPacketAdapter()
        packet_008 = adapter.adapt('test-001', _mock_008_result())

        report = fusion.fuse(brief, packet_008, packet_hermes=None)

        assert report.engines_used == ['008']
        assert len(report.key_findings) == 2
        assert len(report.supplemental_findings) == 0
        assert report.final_grade == 'needs_revision'  # 1 high
        assert '008引擎' in report.executive_summary
        assert report.report_markdown  # non-empty

    def test_fuse_with_hermes_supplemental(self):
        """Hermes-only findings go to supplemental."""
        fusion = ReportFusionService()
        brief = _mock_review_brief()
        adapter = FactPacketAdapter()
        packet_008 = adapter.adapt('test-001', _mock_008_result())

        hermes_finding = FindingItem(
            id='H-001', title='资源投入不足',
            severity='medium', source_engine='hermes',
            category='completeness', evidence_status='inferred',
        )
        packet_hermes = FactPacket(
            review_id='test-001', engine='hermes',
            findings=[hermes_finding],
            summary_metrics=ReviewPacketMetrics(total_findings=1, medium_severity=1),
        )

        report = fusion.fuse(brief, packet_008, packet_hermes)

        assert 'hermes' in report.engines_used
        assert len(report.key_findings) == 2  # 008 findings
        assert len(report.supplemental_findings) == 1  # hermes-only
        assert report.supplemental_findings[0].id == 'H-001'
        assert 'Hermes引擎补充' in report.executive_summary

    def test_fuse_with_degraded_hermes(self):
        """Degraded Hermes → report says single-path."""
        fusion = ReportFusionService()
        brief = _mock_review_brief()
        adapter = FactPacketAdapter()
        packet_008 = adapter.adapt('test-001', _mock_008_result())

        packet_hermes = FactPacket(
            review_id='test-001', engine='hermes',
            degraded=True, error='LLM timeout',
        )

        report = fusion.fuse(brief, packet_008, packet_hermes)

        assert report.engines_used == ['008']
        assert report.degradation_info['hermes']['reason'] == 'LLM timeout'
        assert '未能参与' in report.executive_summary

    def test_fuse_corroboration(self):
        """When Hermes corroborates a 008 finding, it's annotated."""
        fusion = ReportFusionService()
        brief = _mock_review_brief()
        adapter = FactPacketAdapter()
        packet_008 = adapter.adapt('test-001', _mock_008_result())

        corroborating = FindingItem(
            id='H-001', title='核心章节缺失（Hermes确认）',
            severity='high', source_engine='hermes',
            evidence_status='inferred',
            raw_data={'corroborates_008_finding': 'ISSUE-001'},
        )
        packet_hermes = FactPacket(
            review_id='test-001', engine='hermes',
            findings=[corroborating],
            summary_metrics=ReviewPacketMetrics(total_findings=1, high_severity=1),
        )

        report = fusion.fuse(brief, packet_008, packet_hermes)

        # corroborating finding should NOT appear in supplemental
        assert len(report.supplemental_findings) == 0
        # The 008 finding should be annotated
        issue_001 = next(f for f in report.key_findings if f.id == 'ISSUE-001')
        assert issue_001.raw_data.get('corroborated_by_hermes') == ['H-001']

    def test_grade_fail_on_many_high(self):
        fusion = ReportFusionService()
        findings = [
            FindingItem(id=f'F-{i}', title=f't{i}', severity='high')
            for i in range(4)
        ]
        assert fusion._grade(findings) == 'fail'


# ---------------------------------------------------------------------------
# dual_review_orchestrator.py
# ---------------------------------------------------------------------------

class TestDualReviewOrchestrator:
    def test_orchestrate_without_hermes(self):
        """Orchestrator works even when Hermes is not available."""
        orch = DualReviewOrchestrator(hermes_adapter=HermesAdapter(llm_gateway=None))
        brief = _mock_review_brief()
        result = _mock_008_result()

        artifacts = {}
        events = []

        enriched = asyncio.get_event_loop().run_until_complete(
            orch.orchestrate(
                review_brief=brief,
                result_008=result,
                document_preview='文档内容预览...',
                emit=lambda *args: events.append(args),
                write_json_artifact=lambda name, payload: artifacts.update({name: payload}),
            )
        )

        # Original result preserved
        assert enriched['issues'] == result['issues']
        assert enriched['capabilitiesUsed'] == result['capabilitiesUsed']

        # Dual review block present
        dr = enriched['dualReview']
        assert dr['enabled'] is True
        assert '008' in dr['enginesUsed']
        assert dr['hermesDegraded'] is True
        assert dr['finalGrade'] in ('conditional_pass', 'needs_revision', 'fail')
        assert dr['fusionReportMarkdown']  # non-empty

        # Artifacts written
        assert 'review-brief' in artifacts
        assert '008-fact-packet' in artifacts
        assert 'final-report-packet' in artifacts

        # Events emitted
        stages = [e[0] for e in events]
        assert 'task_compile' in stages
        assert 'fact_packet' in stages
        assert 'fusion' in stages
