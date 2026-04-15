from __future__ import annotations

from src.review.hermes.agent_runner import HermesAgentRunner
from src.review.hermes.normative_validity import NormativeValidityChecker
from src.review.hermes.template_models import AgentTemplate


class DummyModuleRegistry:
    async def run_module(self, module_id, *, workspace, context):
        workspace.setdefault('parse_result', object())
        return {'module_id': module_id}


class StubNormativeValidityChecker:
    async def verify_parse_result(self, parse_result):
        assert parse_result is not None
        return [
            {
                'title': '《中国南方电网有限责任公司电力安全工作规程》Q/CSG 510001-2015',
                'status': 'current',
                'resolvedBy': 'web',
            },
            {
                'title': '《深圳电网工程安全文明施工标准（2019年版）》',
                'status': 'unknown',
                'resolvedBy': 'web',
            },
        ]


async def test_normative_validity_reviewer_outputs_evidence_validation_findings():
    runner = HermesAgentRunner(
        hermes_engine=None,
        module_registry=DummyModuleRegistry(),
        normative_validity_checker=StubNormativeValidityChecker(),
    )
    template = AgentTemplate(
        id='normative_validity_reviewer',
        agent_name='法规现行有效性审查',
        agent_purpose='核验依据现行状态',
        agent_scope='evidence_validation',
        execution_mode='module_only',
        module_bindings=['rule_and_evidence'],
        metadata={'review_modules': ['evidence_validation']},
    )

    result = await runner.run_template(
        template,
        brief=type('Brief', (), {'query': 'test', 'metadata': {}, 'model_copy': lambda self, update: self})(),
        workspace={},
        context={},
    )

    packet = result.packet
    assert packet is not None
    findings = packet['findings']
    assert findings[0]['raw_data']['module_name'] == 'evidence_validation'
    assert findings[0]['raw_data']['normativeValidityChecks'][0]['status'] == 'current'
    assert findings[0]['title'] == '编制依据现行有效性核验'
    assert any(item['title'].startswith('编制依据现行有效性存在疑点') for item in findings[1:])


async def test_normative_validity_checker_extracts_only_preparation_basis_normative_items():
    checker = NormativeValidityChecker()
    parse_result = type(
        'ParseResult',
        (),
        {
            'sections': [
                {'id': 'section-1', 'title': '第一章 编制依据', 'parentId': None},
                {'id': 'section-2', 'title': '第二章 工程概况', 'parentId': None},
            ],
            'blocks': [
                {'type': 'heading', 'sectionId': 'section-1', 'text': '第一章 编制依据'},
                {'type': 'paragraph', 'sectionId': 'section-1', 'text': '1. 与委托方签订的项目咨询合同、委托函或中标通知书'},
                {'type': 'paragraph', 'sectionId': 'section-1', 'text': '2. 《中国南方电网有限责任公司电力安全工作规程》Q/CSG 510001-2015'},
                {'type': 'paragraph', 'sectionId': 'section-1', 'text': '3. 《深圳电网工程安全文明施工标准（2019年版）》'},
                {'type': 'paragraph', 'sectionId': 'section-2', 'text': '项目位于深圳市南山区'},
            ],
        },
    )()

    sources = checker._extract_sources_from_parse_result(parse_result)

    assert [item['title'] for item in sources] == [
        '《中国南方电网有限责任公司电力安全工作规程》Q/CSG 510001-2015',
        '《深圳电网工程安全文明施工标准（2019年版）》',
    ]


# ---------------------------------------------------------------------------
# Regression tests for tightened normative validity rules (2026-04-15)
# ---------------------------------------------------------------------------

def test_has_precise_version_anchor_with_year():
    """Standard codes WITH a year suffix should be recognized as precise."""
    checker = NormativeValidityChecker()
    assert checker._has_precise_version_anchor('《电力安全工作规程》GB 26860-2011') is True
    assert checker._has_precise_version_anchor('Q/CSG 510001-2015') is True
    assert checker._has_precise_version_anchor('GB/T 6995.1-2008') is True


def test_has_precise_version_anchor_without_year():
    """Bare standard codes WITHOUT a year suffix should NOT be precise."""
    checker = NormativeValidityChecker()
    assert checker._has_precise_version_anchor('《电线电缆识别标志方法》GB/T 6995') is False
    assert checker._has_precise_version_anchor('GB/T 2951') is False
    assert checker._has_precise_version_anchor('《深圳电网工程安全文明施工标准（2019年版）》') is False


def test_evidence_resolves_uniquely_same_base_with_year():
    """Evidence with same base + year should resolve uniquely."""
    checker = NormativeValidityChecker()
    assert checker._evidence_resolves_uniquely(
        'GB/T 50300',
        'GB/T 50300-2013 建筑工程施工质量验收统一标准',
    ) is True


def test_evidence_resolves_uniquely_family_standard_blocks():
    """Family standard (no sub-part in input) with sub-part in evidence → NOT unique."""
    checker = NormativeValidityChecker()
    assert checker._evidence_resolves_uniquely(
        '《电线电缆识别标志方法》GB/T 6995',
        'GB/T 6995.1-2008 电线电缆识别标志方法 第1部分：一般规定',
    ) is False


def test_evidence_resolves_uniquely_no_year_in_evidence():
    """Evidence without a year suffix → NOT resolved."""
    checker = NormativeValidityChecker()
    assert checker._evidence_resolves_uniquely(
        'GB/T 6995',
        'GB/T 6995 电线电缆识别标志方法',
    ) is False


async def test_bare_standard_demoted_to_unknown():
    """A bare standard number that gets 'current' from web should be demoted to 'unknown'
    when the evidence cannot uniquely resolve to a specific versioned standard."""
    checker = NormativeValidityChecker()
    # Simulate the internal flow: _verify_source gets a 'current' result from web
    # but the input title lacks a year.
    result = checker._demote_bare_to_manual_review(
        title='《电线电缆识别标志方法》GB/T 6995',
        result={
            'status': 'current',
            'resolvedBy': 'web',
            'summary': '联网结果未见废止或替代信号，当前可按现行有效处理。',
            'evidenceTitle': 'GB/T 6995.1-2008 电线电缆识别标志方法 第1部分',
            'evidenceUrl': 'https://openstd.samr.gov.cn/...',
        },
    )
    assert result['status'] == 'unknown'
    assert '缺少年份或分册版本号' in result['summary']


async def test_bare_standard_uniquely_resolved_stays_current():
    """A bare standard number that uniquely resolves to a single versioned standard
    (same base, not a family) should keep 'current' and get resolvedTitle."""
    checker = NormativeValidityChecker()
    result = checker._demote_bare_to_manual_review(
        title='GB/T 50300',
        result={
            'status': 'current',
            'resolvedBy': 'web',
            'summary': '联网结果未见废止或替代信号。',
            'evidenceTitle': 'GB/T 50300-2013 建筑工程施工质量验收统一标准',
            'evidenceUrl': 'https://openstd.samr.gov.cn/...',
        },
    )
    assert result['status'] == 'current'
    assert result['resolvedTitle'] == 'GB/T 50300-2013 建筑工程施工质量验收统一标准'


async def test_positive_keywords_without_version_anchor_demoted():
    """Even if web results contain positive keywords like '现行/有效', a bare standard
    without a precise version anchor must still be demoted to 'unknown'."""
    checker = NormativeValidityChecker()
    result = checker._demote_bare_to_manual_review(
        title='《电线电缆识别标志方法》GB/T 6995',
        result={
            'status': 'current',
            'resolvedBy': 'web',
            'summary': '现行有效',
            'evidenceTitle': '电线电缆识别标志方法 现行有效',
            'evidenceUrl': '',
        },
    )
    assert result['status'] == 'unknown'
    assert '需人工核验' in result['summary']

