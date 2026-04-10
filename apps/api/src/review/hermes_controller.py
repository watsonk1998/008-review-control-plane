from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from src.review.contracts import ReviewBrief, FactPacket
from src.review.hermes.agent_runner import HermesAgentRunner
from src.review.hermes.assembler import HermesReviewAssembler
from src.review.hermes.module_registry import HermesModuleRegistry
from src.review.hermes.template_models import AgentTemplate, AgentTemplateMatch
from src.review.hermes.template_registry import HermesTemplateRegistry

logger = logging.getLogger(__name__)


class HermesController:
    def __init__(
        self,
        *,
        task_compiler,
        fact_packet_adapter,
        structured_review_executor,
        hermes_engine,
        llm_gateway,
        seed_template_dir: Path,
        runtime_template_dir: Path,
    ):
        self.task_compiler = task_compiler
        self.fact_packet_adapter = fact_packet_adapter
        self.structured_review_executor = structured_review_executor
        self.hermes_engine = hermes_engine
        self.llm_gateway = llm_gateway
        self.template_registry = HermesTemplateRegistry(
            seed_dir=seed_template_dir,
            runtime_dir=runtime_template_dir,
        )
        self.module_registry = HermesModuleRegistry(structured_review_executor=structured_review_executor)
        self.agent_runner = HermesAgentRunner(
            hermes_engine=hermes_engine,
            module_registry=self.module_registry,
        )
        self.assembler = HermesReviewAssembler()

    async def run(
        self,
        *,
        task,
        plan: dict[str, Any],
        source_document_ref,
        source_document_path: str,
        fixture,
        emit,
        write_json_artifact,
        write_text_artifact,
        write_binary_artifact,
    ) -> dict[str, Any]:
        hermes_input = dict((plan or {}).get('hermesInput') or {})
        brief = self.task_compiler.compile(
            task,
            source_document_ref=source_document_ref,
            source_document_path=source_document_path,
            plan=plan,
        )
        selected_templates = self.template_registry.select_templates(brief=brief, hermes_input=hermes_input)
        focus_gaps = self.template_registry.focus_gaps(selected_templates=selected_templates, brief=brief, hermes_input=hermes_input)
        candidate_template = None
        if focus_gaps:
            candidate_template = await self._generate_candidate_template(
                brief=brief,
                hermes_input=hermes_input,
                focus_gaps=focus_gaps,
            )
            selected_templates.append(AgentTemplateMatch(template=candidate_template, score=2, reasons=['candidate_template']))
            saved_path = self.template_registry.save_runtime_template(candidate_template, task_id=task.id)
            if emit:
                emit('template', 'hermes_controller', 'completed', f'Candidate template generated: {candidate_template.id}', artifact_path=str(saved_path))

        workspace: dict[str, Any] = {}
        context = {
            'task_id': task.id,
            'query': task.query,
            'source_document_path': source_document_path,
            'source_document_ref': source_document_ref,
            'fixture_id': getattr(fixture, 'id', None) if fixture else None,
            'plan': plan,
            'document_type': task.documentType,
            'discipline_tags': task.disciplineTags,
            'strict_mode': task.strictMode,
            'policy_pack_ids': task.policyPackIds,
            'emit': emit,
            'write_json_artifact': write_json_artifact,
            'write_text_artifact': write_text_artifact,
            'write_binary_artifact': write_binary_artifact,
            'fact_packet_adapter': self.fact_packet_adapter,
        }
        agent_results: list[dict[str, Any]] = []
        primary_packet: FactPacket | None = None
        primary_result: dict[str, Any] | None = None
        supplemental_packets: list[FactPacket] = []

        for match in selected_templates:
            template = match.template
            if emit:
                emit('agent_select', 'hermes_controller', 'info', f'Selected agent: {template.id}', debug={'reasons': match.reasons})
            run_result = await self.agent_runner.run_template(
                template,
                brief=brief,
                workspace=workspace,
                context=context,
            )
            result_payload = run_result.model_dump(mode='json')
            agent_results.append(result_payload)
            packet_payload = result_payload.get('packet')
            if packet_payload:
                packet = FactPacket.model_validate(packet_payload)
                if template.id == 'structure_completeness_reviewer' and packet.engine == '008':
                    primary_packet = packet
                    primary_result = workspace.get('structured_review_result')
                else:
                    packet.review_id = brief.review_id
                    packet.metadata = {**packet.metadata, 'template_id': template.id, 'agent_id': template.id}
                    supplemental_packets.append(packet)

        enriched, final_packet = self.assembler.assemble(
            brief=brief,
            primary_packet=primary_packet,
            supplemental_packets=supplemental_packets,
            structured_result=primary_result,
            agent_results=agent_results,
        )
        if candidate_template is not None:
            enriched.setdefault('hermesController', {})['candidateTemplateId'] = candidate_template.id
        if write_json_artifact:
            write_json_artifact('hermes-controller-agent-results', agent_results)
            if final_packet is not None:
                write_json_artifact('hermes-controller-final-report-packet', final_packet.model_dump(mode='json'))
        if write_text_artifact and final_packet is not None:
            write_text_artifact('hermes-controller-final-report', final_packet.report_markdown, '.md')
        return enriched

    async def _generate_candidate_template(
        self,
        *,
        brief: ReviewBrief,
        hermes_input: dict[str, Any],
        focus_gaps: list[str],
    ) -> AgentTemplate:
        if self.llm_gateway is not None:
            try:
                content = await self.llm_gateway.chat([
                    {'role': 'system', 'content': '你是审查子 Agent 模板生成器。输出严格 JSON。'},
                    {'role': 'user', 'content': json.dumps({
                        'review_id': brief.review_id,
                        'document_type': brief.review_object_type,
                        'focus_gaps': focus_gaps,
                        'focus_pack': brief.focus_pack,
                        'query': brief.query,
                        'hermes_input': hermes_input,
                    }, ensure_ascii=False)},
                ], temperature=0.1, max_tokens=800)
                parsed = self._parse_candidate_json(content.get('content', ''))
                return AgentTemplate.model_validate(parsed)
            except Exception as exc:
                logger.warning('[hermes_controller] Candidate template generation fallback: %s', exc)
        gap = focus_gaps[0] if focus_gaps else 'custom_focus'
        template_id = self._slugify(f'candidate_{gap}')
        return AgentTemplate(
            id=template_id,
            agent_name=f'候选子Agent-{gap}',
            agent_purpose=f'补充覆盖“{gap}”相关审查重点',
            agent_scope='narrow_focus_gap',
            execution_mode='hermes_router',
            module_bindings=['fact_extract'],
            supported_document_types=[str(brief.review_object_type)],
            focus_keywords=focus_gaps,
            required_context_types=['target_document', 'focus_requirements'],
            instructions=f'重点围绕“{gap}”识别系统性风险和遗漏。',
            prompt=f'请围绕 {gap} 输出结构化审查结论。',
            save_policy={'runtime_only': True},
            compatibility={'hermes_controller_version': 'v0.1'},
            metadata={'generated': True},
        )

    def _parse_candidate_json(self, raw: str) -> dict[str, Any]:
        text = raw.strip()
        if text.startswith('```'):
            parts = text.split('```')
            if len(parts) >= 2:
                text = parts[1]
                if text.startswith('json'):
                    text = text[4:]
        parsed = json.loads(text.strip())
        if 'id' not in parsed:
            parsed['id'] = self._slugify(parsed.get('agent_name', 'candidate_agent'))
        return parsed

    def _slugify(self, value: str) -> str:
        value = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff]+', '_', value).strip('_').lower()
        return value or 'candidate_agent'
