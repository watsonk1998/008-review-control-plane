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
