from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

from src.domain.models import SourceDocumentRef, TaskRecord
from src.review.contracts import FactPacket, FindingItem, ReviewPacketMetrics
from src.review.fact_packet_adapter import FactPacketAdapter
from src.review.hermes_controller import HermesController
from src.review.hermes_review_engine import HermesReviewEngine
from src.review.pipeline import StructuredReviewExecutor
from src.review.structured_review_capability_facade import StructuredReviewCapabilityFacade
from src.review.task_compiler import TaskCompiler
from src.routes.review_task_contracts import build_review_task_result
from src.services.document_loader import DocumentLoader

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_DIR = API_ROOT / 'src' / 'review' / 'hermes' / 'templates'


class DummyLLM:
    async def chat(self, messages, temperature=0.2, max_tokens=1200):
        raise RuntimeError('force deterministic candidate fallback')

    def explain_issue_candidates(self, candidates):
        return [
            {
                'id': f'ISSUE-{index + 1:03d}',
                'title': candidate.title,
                'layer': candidate.layerHint,
                'severity': candidate.severityHint,
                'findingType': candidate.findingType,
                'summary': candidate.title,
                'manualReviewNeeded': candidate.manualReviewNeeded,
                'evidenceMissing': candidate.evidenceMissing,
                'manualReviewReason': candidate.manualReviewReason,
                'docEvidence': [span.model_dump(mode='json') for span in candidate.docEvidence],
                'policyEvidence': [span.model_dump(mode='json') for span in candidate.policyEvidence],
                'recommendation': ['demo'],
                'confidence': 'medium',
                'whetherManualReviewNeeded': candidate.manualReviewNeeded,
            }
            for index, candidate in enumerate(candidates)
        ]


class FakeHermesEngine(HermesReviewEngine):
    @property
    def available(self) -> bool:
        return True

    async def health_check(self) -> dict:
        return {'available': True, 'mode': 'fake', 'detail': 'ok'}

    async def review(self, brief, fact_packet_008=None, *, document_preview='') -> FactPacket:
        return FactPacket(
            review_id=brief.review_id,
            engine='hermes',
            findings=[
                FindingItem(
                    id='H-CUSTOM-001',
                    title='停送电执行链路存在遗漏风险',
                    severity='medium',
                    category='consistency',
                    evidence_status='inferred',
                    summary='补充识别到停送电链路的执行衔接风险。',
                    suggestion='补齐停送电链路衔接措施。',
                    source_engine='hermes',
                )
            ],
            summary_metrics=ReviewPacketMetrics(total_findings=1, medium_severity=1),
            overall_assessment='fake hermes review',
        )


def _write_json_factory(base: Path):
    def _write(name: str, payload):
        path = base / f'{name}.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
        return str(path)
    return _write


def _write_text_factory(base: Path):
    def _write(name: str, content: str, suffix: str = '.md'):
        path = base / f'{name}{suffix}'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return str(path)
    return _write


def _write_binary_factory(base: Path):
    def _write(name: str, content: bytes, suffix: str = '.bin'):
        path = base / f'{name}{suffix}'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return str(path)
    return _write


def _judge(module_name: str, main_count: int, support_count: int, decision_count: int) -> str:
    if module_name == 'execution_continuity' and main_count > 0:
        return 'Hermes 主审 + 底座支撑'
    if module_name == 'structure_completeness' and support_count >= main_count:
        return '底座主导，Hermes 重表达'
    if decision_count > 0 and main_count > 0 and support_count > 0:
        return '混合过渡态'
    if main_count > support_count:
        return 'Hermes 主审 + 底座支撑'
    return '混合过渡态'


def _finding_module_name(finding: dict) -> str | None:
    raw_data = dict(finding.get('raw_data') or {})
    module_name = raw_data.get('module_name')
    if isinstance(module_name, str) and module_name:
        return module_name
    review_modules = raw_data.get('review_modules')
    if isinstance(review_modules, list) and len(review_modules) == 1 and review_modules[0]:
        return str(review_modules[0])
    return None


def _support_issue_module_name(issue: dict) -> str | None:
    support_modules = issue.get('supportModules')
    if isinstance(support_modules, list) and len(support_modules) == 1 and support_modules[0]:
        return str(support_modules[0])
    ownership = issue.get('ownership')
    if ownership == 'support_material':
        layer = issue.get('layer')
        if layer == 'L1':
            return 'structure_completeness'
        if layer == 'L2':
            return 'legality_compliance'
        title = f"{issue.get('title', '')}{issue.get('summary', '')}".lower()
        if any(token in title for token in ['停送电', '工序', '执行', '链路']):
            return 'execution_continuity'
    return None


async def main() -> None:
    tmp_dir = ROOT / 'apps' / 'api' / 'e2e_artifacts' / 'module_validation'
    tmp_dir.mkdir(parents=True, exist_ok=True)
    sample = tmp_dir / 'validation_sample.md'
    sample.write_text(
        '# 停电施工方案\n\n## 第一章 工程概况\n停电窗口7天。\n\n## 第二章 施工组织\n涉及施工用电、动火作业。\n\n## 第三章 停送电组织\n需明确执行顺序与闭环。\n\n## 第四章 规范依据\n引用配网停电施工规范。\n',
        encoding='utf-8',
    )
    llm = DummyLLM()
    controller = HermesController(
        task_compiler=TaskCompiler(),
        fact_packet_adapter=FactPacketAdapter(),
        capability_facade=StructuredReviewCapabilityFacade(
            structured_review_executor=StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=llm, fast_adapter=None),
        ),
        hermes_engine=FakeHermesEngine(),
        llm_gateway=llm,
        seed_template_dir=TEMPLATE_DIR,
        runtime_template_dir=tmp_dir / 'runtime_templates',
    )
    task = TaskRecord(
        id='task-module-validation-001',
        taskType='structured_review',
        capabilityMode='auto',
        query='重点审查章节完整性、合法合规性、停送电执行连续性',
        sourceDocumentRef=SourceDocumentRef(
            refId='upload-validation-1',
            sourceType='upload',
            fileName=sample.name,
            fileType='md',
            storagePath=str(sample),
            displayName=sample.name,
        ),
        documentType='distribution_network_special_scheme',
        disciplineTags=['temporary_power'],
        strictMode=True,
        policyPackIds=['power_outage_work.base'],
        status='created',
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
    )
    result = await controller.run(
        task=task,
        plan={
            'reviewProfile': {
                'authority': 'validation',
                'documentTypeHint': 'distribution_network_special_scheme',
                'disciplineTagHints': ['temporary_power'],
                'policyPackHints': ['power_outage_work.base'],
            },
            'hermesInput': {
                'basisFiles': [{'path': '/tmp/basis.md', 'type': 'md', 'name': 'basis.md'}],
                'contextFiles': [],
                'focusRequirements': ['章节完整性', '规范条款命中', '停送电执行闭环'],
                'enabledAgents': ['structured_review_primary_worker', 'policy_compliance_reviewer', 'execution_risk_reviewer'],
                'disabledAgents': [],
            },
        },
        source_document_ref=task.sourceDocumentRef,
        source_document_path=str(sample),
        fixture=None,
        emit=lambda *args, **kwargs: None,
        write_json_artifact=_write_json_factory(tmp_dir),
        write_text_artifact=_write_text_factory(tmp_dir),
        write_binary_artifact=_write_binary_factory(tmp_dir),
    )
    completed_task = task.model_copy(update={
        'status': 'succeeded',
        'result': result,
        'updatedAt': datetime.now(timezone.utc),
    })
    final_result = build_review_task_result(completed_task, [])

    main_outcomes = result.get('hermesController', {}).get('mainReviewOutcomes', [])
    support_result = result
    modules = ['structure_completeness', 'legality_compliance', 'execution_continuity']
    report = []
    for module_name in modules:
        main_items = []
        for outcome in main_outcomes:
            packet = outcome.get('packet') or outcome
            for finding in packet.get('findings') or []:
                if _finding_module_name(finding) == module_name:
                    main_items.append(finding)
        support_items = []
        for issue in support_result.get('support_issues') or support_result.get('issues') or []:
            if _support_issue_module_name(issue) == module_name:
                support_items.append(issue)
        decision_items = final_result.modules[module_name].findings
        report.append({
            'module': module_name,
            'main_review_contribution': {
                'count': len(main_items),
                'templates': sorted({(item.get('raw_data') or {}).get('template_id', '') for item in main_items if (item.get('raw_data') or {}).get('template_id')}),
                'titles': [item.get('title') for item in main_items[:3]],
            },
            'support_contribution': {
                'count': len(support_items),
                'titles': [item.get('title') for item in support_items[:3]],
            },
            'final_decision_contribution': {
                'count': len(decision_items),
                'titles': [item.get('title') for item in decision_items[:3]],
                'summary': final_result.summary.overall_conclusion,
            },
            'current_judgement': _judge(module_name, len(main_items), len(support_items), len(decision_items)),
        })

    output = {'task_id': completed_task.id, 'modules': report}
    (tmp_dir / 'module-contribution-summary.json').write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
