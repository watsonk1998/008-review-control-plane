from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any

from src.review.contracts import FactPacket, ReviewBrief
from src.review.hermes.agent_runner import HermesAgentRunner
from src.review.hermes.assembler import HermesReviewAssembler
from src.review.hermes.constants import is_primary_template_id
from src.review.hermes.decision_models import HermesReviewDecisionInputs
from src.review.hermes.module_registry import HermesModuleRegistry
from src.review.hermes.presentation_agent import HermesPresentationAgent
from src.review.hermes.template_models import AgentTemplate, AgentTemplateMatch
from src.review.hermes.template_registry import HermesTemplateRegistry

logger = logging.getLogger(__name__)


class HermesController:
    def __init__(
        self,
        *,
        task_compiler,
        fact_packet_adapter,
        capability_facade,
        hermes_engine,
        llm_gateway,
        basis_pack_resolver,
        support_packet_builder,
        seed_template_dir: Path,
        runtime_template_dir: Path,
        formal_mode: bool = True,
    ):
        self.task_compiler = task_compiler
        self.fact_packet_adapter = fact_packet_adapter
        self.capability_facade = capability_facade
        self.hermes_engine = hermes_engine
        self.llm_gateway = llm_gateway
        self.basis_pack_resolver = basis_pack_resolver
        self.support_packet_builder = support_packet_builder
        self.formal_mode = formal_mode
        self.template_registry = HermesTemplateRegistry(
            seed_dir=seed_template_dir,
            runtime_dir=runtime_template_dir,
            formal_mode=formal_mode,
        )
        self.module_registry = HermesModuleRegistry(capability_facade=capability_facade)
        self.agent_runner = HermesAgentRunner(
            hermes_engine=hermes_engine,
            module_registry=self.module_registry,
        )
        self.assembler = HermesReviewAssembler()
        self.presentation_agent = HermesPresentationAgent(llm_gateway=self.llm_gateway)

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

        # --- GOVERNANCE CHAIN PRE-ASSEMBLY ---
        # 1. Ensure we have early facts for resolution (SupportPacketBuilder consumes facts)
        self.capability_facade.fact_extract(workspace=workspace, context=context)
        
        # 2. Resolve Review Profile (Task Context + Facts)
        self.capability_facade.profile_and_packs(workspace=workspace, context=context)
        resolved_profile = workspace.get('resolved_profile')
        facts = workspace.get('facts')
        structured_task = workspace.get('structured_task')

        # 2.5 Ensure local rules evaluate the facts to provide compliance candidates
        self.capability_facade.rule_and_evidence(workspace=workspace, context=context)
        
        # 3. Resolve Basis Packs (Strict YAML Governance)
        resolved_basis = None
        if hasattr(self, 'basis_pack_resolver') and self.basis_pack_resolver:
            # We explicitly pass context, facts, overrides per user guidelines
            resolved_basis = self.basis_pack_resolver.resolve(
                profile=resolved_profile,
                task_context=context,
                facts=facts,
                overrides=None,
            )
            # Store it for downstream hermes main review context
            workspace['resolved_basis_profile'] = resolved_basis

        # 4. Build Governed Support Packet
        if hasattr(self, 'support_packet_builder') and self.support_packet_builder and resolved_basis:
            governed_support_packet = self.support_packet_builder.build_packet(
                review_record=structured_task,
                profile=resolved_profile,
                basis_profile=resolved_basis,
                facts=facts,
            )
            workspace['governed_support_packet'] = governed_support_packet
        # --- END GOVERNANCE CHAIN PRE-ASSEMBLY ---

        try:
            selected_templates = self.template_registry.select_templates(brief=brief, hermes_input=hermes_input)
            focus_gaps = self.template_registry.focus_gaps(selected_templates=selected_templates, brief=brief, hermes_input=hermes_input)
            is_simulation = plan.get("simulation_mode", False)
            is_learning = plan.get("learning_mode", False)

            learning_candidates = []
            candidate_template = None

            if focus_gaps and is_simulation and is_learning:
                candidate_template = await self._generate_candidate_template(
                    brief=brief,
                    hermes_input=hermes_input,
                    focus_gaps=focus_gaps,
                )
                
                learning_candidates.append({
                    "type": "template_hint",
                    "content": f"New agent needed for focus gap. Suggested Template ID: {candidate_template.id}. Prompt: {candidate_template.prompt}"
                })
                if emit:
                    emit('template', 'hermes_controller', 'info',
                         f'Candidate template generated for simulation/learning (not injected into formal run): {candidate_template.id}')

            agent_results: list[dict[str, Any]] = []
            support_packet_008: FactPacket | None = None
            support_result_008: dict[str, Any] | None = None
            hermes_review_packets: list[FactPacket] = []
            total_agents = len(selected_templates)
            completed_agents = 0

            def _emit_agent_event(stage: str, message: str, *, template_id: str | None = None, reasons: list[str] | None = None, failed: bool = False):
                if not emit:
                    return
                debug_payload = {
                    'templateId': template_id,
                    'completedAgents': completed_agents,
                    'totalAgents': total_agents,
                }
                if reasons:
                    debug_payload['reasons'] = reasons
                emit(stage, 'hermes_controller', 'failed' if failed else 'info', message, debug=debug_payload)

            sequential_matches = [match for match in selected_templates if match.template.execution_mode != 'hermes_router']
            parallel_matches = [match for match in selected_templates if match.template.execution_mode == 'hermes_router']

            for match in selected_templates:
                _emit_agent_event('agent_select', f'Selected agent: {match.template.id}', template_id=match.template.id, reasons=match.reasons)

            def _consume_run_result(template: AgentTemplate, result_payload: dict[str, Any]) -> None:
                nonlocal support_packet_008, support_result_008, completed_agents
                agent_results.append(result_payload)
                packet_payload = result_payload.get('packet')
                if packet_payload:
                    packet = FactPacket.model_validate(packet_payload)
                    if is_primary_template_id(template.id) and packet.engine == '008':
                        support_packet_008 = packet
                        support_result_008 = workspace.get('structured_support_result_008')
                    else:
                        packet.review_id = brief.review_id
                        packet.metadata = {**packet.metadata, 'template_id': template.id, 'agent_id': template.id}
                        hermes_review_packets.append(packet)
                completed_agents += 1
                _emit_agent_event('agent_done', f'专项审查器已完成：{template.id}', template_id=template.id)

            for match in sequential_matches:
                template = match.template
                _emit_agent_event('agent_running', f'主审引擎处理中：{template.id}', template_id=template.id)
                run_result = await self.agent_runner.run_template(
                    template,
                    brief=brief,
                    workspace=workspace,
                    context=context,
                )
                _consume_run_result(template, run_result.model_dump(mode='json'))

            async def _run_parallel_template(match: AgentTemplateMatch):
                template = match.template
                if emit:
                    emit(
                        'agent_running',
                        'hermes_controller',
                        'info',
                        f'专项审查器并行运行中：{template.id}',
                        debug={'templateId': template.id, 'completedAgents': completed_agents, 'totalAgents': total_agents},
                    )
                try:
                    run_result = await self.agent_runner.run_template(
                        template,
                        brief=brief,
                        workspace=workspace,
                        context=context,
                    )
                    return match, run_result.model_dump(mode='json'), None
                except Exception as exc:  # pragma: no cover - defensive runtime guard
                    return match, None, exc

            if parallel_matches:
                if emit:
                    emit(
                        'agent_running',
                        'hermes_controller',
                        'info',
                        f'专项子审查并行运行中（共 {len(parallel_matches)} 个）',
                        debug={'parallelAgents': [match.template.id for match in parallel_matches], 'totalAgents': total_agents, 'completedAgents': completed_agents},
                    )
                parallel_results = await asyncio.gather(*[_run_parallel_template(match) for match in parallel_matches], return_exceptions=False)
                for match, result_payload, exc in parallel_results:
                    template = match.template
                    if exc is not None:
                        completed_agents += 1
                        _emit_agent_event('agent_done', f'专项审查器执行失败：{template.id}（已跳过）', template_id=template.id, failed=True)
                        continue
                    if result_payload is None:
                        completed_agents += 1
                        _emit_agent_event('agent_done', f'专项审查器未产出结果：{template.id}', template_id=template.id)
                        continue
                    _consume_run_result(template, result_payload)

            decision_inputs = HermesReviewDecisionInputs(
                support_packet_008=support_packet_008.model_dump(mode='json') if support_packet_008 else None,
                support_result_008=support_result_008,
                hermes_review_packets=[packet.model_dump(mode='json') for packet in hermes_review_packets],
                agent_results=agent_results,
            )

            enriched, final_packet = self.assembler.assemble(
                brief=brief,
                support_packet_008=support_packet_008,
                hermes_review_packets=hermes_review_packets,
                support_result_008=support_result_008,
                agent_results=agent_results,
            )
            enriched.setdefault('hermesController', {})['enabled'] = True
        except Exception as exc:
            if emit:
                emit('hermes_controller', 'hermes_controller', 'failed', f'Hermes controller failed, falling back to degraded mode: {exc}')

            # Execute degraded path by running support review directly
            support_output = await self.capability_facade.primary_support_review(workspace=workspace, context=context)
            support_result_008 = support_output.get('support_result')
            support_packet_008_payload = support_output.get('support_packet')
            support_packet_008 = FactPacket.model_validate(support_packet_008_payload) if support_packet_008_payload else None

            agent_results = []
            hermes_review_packets = []
            candidate_template = None
            learning_candidates = []

            decision_inputs = HermesReviewDecisionInputs(
                support_packet_008=support_packet_008.model_dump(mode='json') if support_packet_008 else None,
                support_result_008=support_result_008,
                hermes_review_packets=[],
                agent_results=[],
            )

            enriched, final_packet = self.assembler.assemble(
                brief=brief,
                support_packet_008=support_packet_008,
                hermes_review_packets=[],
                support_result_008=support_result_008,
                agent_results=[],
            )
            enriched.setdefault('hermesController', {})['enabled'] = False
            enriched['hermesController']['error'] = str(exc)
            enriched['hermesController']['degraded'] = True

        enriched.setdefault('hermesController', {})['mainReviewOwnedBy'] = 'hermes'
        enriched['hermesController']['supportLayerOwnedBy'] = 'structured_review_capability_facade'
        enriched['hermesController']['mainReviewOutcomes'] = [packet.model_dump(mode='json') for packet in hermes_review_packets]
        enriched['hermesController']['decisionInputs'] = decision_inputs.model_dump(mode='json')

        if candidate_template is not None:
            enriched.setdefault('hermesController', {})['candidateTemplateId'] = candidate_template.id
            
        if learning_candidates:
            enriched.setdefault('hermesController', {})['learningGeneratedCandidates'] = learning_candidates

        if final_packet is not None and getattr(self, 'llm_gateway', None):
            if emit:
                emit('hermes_controller', 'hermes_controller', 'info', '派出最终审查报告表达层子agent...', debug={"status": "presentation_pass_started"})
            presentation_result = await self.presentation_agent.generate_presentation(final_packet)
            
            # HARD CONSTRAINT: Presentation output MUST NOT overwrite the assembler's
            # authoritative finalReportMarkdown / finalAnswer.  It is strictly a
            # supplementary display-layer artifact stored in separate fields.
            enriched['presentationMarkdown'] = presentation_result.presentation_markdown
            enriched['presentationSummary'] = presentation_result.presentation_markdown
            enriched.setdefault('hermesController', {})['presentationResult'] = presentation_result.model_dump(mode='json')
            
            if write_json_artifact:
                write_json_artifact('hermes-controller-presentation-result', presentation_result.model_dump(mode='json'))

        if write_json_artifact:
            write_json_artifact('hermes-controller-agent-results', agent_results)
            if final_packet is not None:
                write_json_artifact('hermes-controller-final-report-packet', final_packet.model_dump(mode='json'))
        if write_text_artifact and final_packet is not None:
            # We must ALWAYS output the authoritative formal report as a text artifact,
            # ensuring that the system of record defaults to the assembler's deterministic output.
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
            metadata={
                'generated': True,
                'experimental': True,
                'not_official': True,
                'requires_promotion_validation': True,
                'ownership': 'hermes_main_review',
            },
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
