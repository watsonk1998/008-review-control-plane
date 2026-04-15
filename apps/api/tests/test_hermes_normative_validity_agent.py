from __future__ import annotations

from src.review.hermes.agent_runner import HermesAgentRunner
from src.review.hermes.template_models import AgentTemplate


class DummyModuleRegistry:
    async def run_module(self, module_id, *, workspace, context):
        workspace.setdefault('candidates', ['demo-candidate'])
        return {'module_id': module_id}


class StubNormativeValidityChecker:
    async def verify_candidates(self, candidates):
        assert candidates == ['demo-candidate']
        return [
            {
                'title': '《建设工程安全生产管理条例》',
                'status': 'current',
                'resolvedBy': 'web',
                'summary': '联网结果未见废止信号。',
                'evidenceTitle': '国务院文件库',
                'evidenceUrl': 'https://www.gov.cn/',
            },
            {
                'title': '《电气装置安装工程低压电器施工及验收规范》GB 50254-2014',
                'status': 'unknown',
                'resolvedBy': 'web',
                'summary': '未能从公开摘要稳定判断现行状态。',
                'evidenceTitle': '国家标准全文公开系统',
                'evidenceUrl': 'https://openstd.samr.gov.cn/',
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
    assert any(item['title'].startswith('审查依据现行有效性存在疑点') for item in findings[1:])
