from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.review.contracts import FactPacket, FindingItem, ReviewPacketMetrics
from src.review.hermes.constants import is_primary_template_id
from src.review.hermes.module_bindings import template_review_modules
from src.review.hermes.normative_validity import NormativeValidityChecker
from src.review.hermes.template_models import AgentRunResult, AgentTemplate

# Hard template→module mapping: these templates ALWAYS produce findings
# for a specific module. Keyword-based guessing is ONLY a fallback for
# templates not listed here. See AGENTS.md HG-15 / HG-17.
_TEMPLATE_HARD_MODULE: dict[str, str] = {
    'normative_validity_reviewer': 'evidence_validation',
    'calculation_review_reviewer': 'evidence_validation',
    'visibility_gap_reviewer': 'evidence_validation',
}


class HermesAgentRunner:
    def __init__(self, *, hermes_engine, module_registry, llm_gateway=None, normative_validity_checker=None):
        self.hermes_engine = hermes_engine
        self.module_registry = module_registry
        self.llm_gateway = llm_gateway
        self.normative_validity_checker = normative_validity_checker or NormativeValidityChecker(llm_gateway=llm_gateway)

    async def run_template(
        self,
        template: AgentTemplate,
        *,
        brief,
        workspace: dict[str, Any],
        context: dict[str, Any],
    ) -> AgentRunResult:
        module_outputs: dict[str, Any] = {}
        packet: FactPacket | None = None
        for module_id in template.module_bindings:
            module_outputs[module_id] = await self.module_registry.run_module(
                module_id,
                workspace=workspace,
                context=context,
            )

        if template.execution_mode == 'hermes_router':
            parse_result = workspace.get('parse_result')
            doc_text = parse_result.normalizedText if parse_result else ''
            effective_brief = self._brief_for_template(brief, template, workspace.get('governed_support_packet'))
            packet = await self.hermes_engine.review(
                brief=effective_brief,
                fact_packet_008=workspace.get('support_packet_008'),
                document_preview=doc_text,
                governed_support_packet=workspace.get('governed_support_packet'),
            )
            for finding in packet.findings:
                self._annotate_finding_ownership(template, finding)
            packet.metadata = {
                **packet.metadata,
                'agent_id': template.id,
                'template_id': template.id,
                'worker_id': 'hermes_router',
                'module_ids': list(template.module_bindings),
                'review_modules': self._template_review_modules(template),
                'ownership': 'hermes_main_review',
                'input_token_limit': template.input_token_limit,
                'output_token_limit': template.output_token_limit,
            }
            # Calculation reviewer deterministic fallback: if the LLM router
            # produced zero findings, inject a conservative "evidence insufficient"
            # finding so the module is always visible in the report (AGENTS.md HG-17).
            if template.id == 'calculation_review_reviewer' and not packet.findings:
                packet.findings.append(
                    FindingItem(
                        id='H-CALC-FALLBACK-001',
                        title='计算核验：未见计算书或验算过程',
                        severity='info',
                        category='evidence_verification',
                        finding_type='calculation_review_insufficient_evidence',
                        evidence_status='evidence_gap',
                        summary='被审方案中未识别到计算式、验算过程或参数取值依据，无法完成计算核验。',
                        suggestion='如方案涉及荷载、安全系数、电气参数等验算需求，请补充计算书或验算过程后重新审查。',
                        source_engine='hermes',
                        raw_data={'module_name': 'evidence_validation'},
                    )
                )
                self._annotate_finding_ownership(template, packet.findings[-1])
                packet.overall_assessment = '未见计算书或验算过程，计算核验功能已就绪但证据不足。'
        else:
            if template.id == 'normative_validity_reviewer':
                packet = await self._build_normative_validity_packet(template=template, workspace=workspace)
            else:
                packet = self._module_output_to_packet(template=template, workspace=workspace)

        return AgentRunResult(
            agent_id=template.id,
            template_id=template.id,
            worker_id=packet.metadata.get('worker_id', template.execution_mode) if packet else template.execution_mode,
            packet=packet.model_dump(mode='json') if packet else None,
            module_outputs=module_outputs,
            metadata={'execution_mode': template.execution_mode},
        )

    def _annotate_finding_ownership(self, template: AgentTemplate, finding: FindingItem) -> FindingItem:
        review_modules = self._template_review_modules(template)
        # Hard mapping takes priority over keyword guessing (AGENTS.md HG-15)
        module_name = _TEMPLATE_HARD_MODULE.get(template.id) or self._resolve_finding_module_name(finding, review_modules)
        finding.raw_data = {
            **finding.raw_data,
            'template_id': template.id,
            'agent_id': template.id,
            'review_modules': review_modules,
            **({'module_name': module_name} if module_name else {}),
            'ownership': template.metadata.get(
                'ownership',
                'hermes_main_review' if template.execution_mode == 'hermes_router' else 'support_material',
            ),
        }
        return finding

    def _resolve_finding_module_name(self, finding: FindingItem, review_modules: list[str]) -> str:
        if len(review_modules) == 1:
            return review_modules[0]
        title = f'{finding.title} {finding.summary}'.lower()
        if any(token in title for token in ['停送电', '执行链路', '流程', '工序', '连续']):
            return 'execution_continuity'
        if any(token in title for token in ['参数', 'capacity', '荷载', '吨', '重量', '一致']):
            return 'parameter_consistency'
        if any(token in title for token in ['依据', '证据', '现行有效', '废止', '替代']):
            return 'evidence_validation'
        return ''

    def _module_output_to_packet(self, *, template: AgentTemplate, workspace: dict[str, Any]) -> FactPacket | None:
        if is_primary_template_id(template.id) and workspace.get('support_packet_008') is not None:
            packet = workspace['support_packet_008'].model_copy(deep=True)
            packet.engine = '008'
            packet.metadata = {
                **packet.metadata,
                'agent_id': template.id,
                'template_id': template.id,
                'worker_id': 'structured_review_primary_worker',
                'module_ids': list(template.module_bindings),
                'review_modules': self._template_review_modules(template),
                'ownership': 'support_material',
                'input_token_limit': template.input_token_limit,
                'output_token_limit': template.output_token_limit,
            }
            for finding in packet.findings:
                self._annotate_finding_ownership(template, finding)
            return packet

        if template.id == 'visibility_gap_reviewer':
            parse_result = workspace.get('parse_result')
            if parse_result is None:
                return None
            visibility = parse_result.visibility
            findings: list[FindingItem] = []
            reason_zh_map = {
                'reference_detected_without_attachment_body': '正文引用了附件或图纸，但系统未能扫描到其实质内容。',
                'pdf_contains_images': '文档由于包含纯图片或未识别节点，部分内页可能未能完全提取。',
                'attachment_file_too_large': '部分附件或图纸超出了自动挂载体积限制。',
                'unsupported_attachment_format': '部分图纸格式暂不支持完全结构化阅读。',
            }
            if visibility.manualReviewNeeded:
                raw_reason = visibility.manualReviewReason or ''
                mapped_reason = reason_zh_map.get(raw_reason, raw_reason) if raw_reason else '存在未解析的附件、图纸或系统提取限制。'
                findings.append(
                    FindingItem(
                        id='H-VIS-001',
                        title='附件及图纸解析受限，请结合原件复核',
                        severity='medium',
                        category='visibility',
                        finding_type='visibility_gap',
                        evidence_status='visibility_gap',
                        summary=mapped_reason,
                        suggestion='提取盲区不影响核心指标评级。请根据提示，自行确认图纸或附件内容是否无误。',
                        source_engine='hermes',
                        raw_data={'attachment_count': visibility.attachmentCount},
                    )
                )
                self._annotate_finding_ownership(template, findings[-1])
            return self._build_packet(template, findings, overall='可视域检查已完成。')

        if template.id == 'policy_compliance_reviewer':
            candidates = workspace.get('candidates') or []
            findings: list[FindingItem] = []
            for idx, candidate in enumerate(candidates, start=1):
                rule_ids = [hit.ruleId for hit in candidate.ruleHits]
                rule_str = ' '.join(rule_ids)
                if 'structure_completeness' in rule_str:
                    category = 'chapter_completeness'
                elif 'parameter' in rule_str or 'calculation' in rule_str or 'drawing' in rule_str:
                    category = 'parameter_consistency'
                elif 'sequence' in rule_str or 'process' in rule_str or 'control' in rule_str:
                    category = 'process_coherence'
                elif 'traceability' in rule_str or 'evidence' in rule_str:
                    category = 'evidence_verification'
                else:
                    category = 'compliance'

                findings.append(
                    FindingItem(
                        id=f'H-POL-{idx:03d}',
                        title=candidate.title,
                        severity=candidate.severityHint,
                        category=category,
                        layer=str(candidate.layerHint),
                        evidence_status='grounded' if candidate.policyEvidence else 'evidence_gap',
                        basis_refs=[getattr(span.locator, 'clauseId', '') for span in candidate.policyEvidence if getattr(span, 'locator', None)],
                        summary='; '.join(hit.rationale for hit in candidate.ruleHits if hit.rationale)[:300],
                        suggestion='结合命中规则与规范条款进一步补齐正文。',
                        source_engine='hermes',
                        finding_type=candidate.findingType.value,
                        raw_data={
                            'rule_ids': rule_ids,
                            'corroborates_008_finding': candidate.candidateId,
                        },
                    )
                )
                self._annotate_finding_ownership(template, findings[-1])
            return self._build_packet(template, findings, overall='规范命中与证据线索已整理。')
        return None

    async def _build_normative_validity_packet(self, *, template: AgentTemplate, workspace: dict[str, Any]) -> FactPacket:
        checks = await self.normative_validity_checker.verify_parse_result(workspace.get('parse_result'))
        if not checks:
            return self._build_packet(template, [], overall='未识别到被审方案“编制依据”章节中可执行现行有效性核验的规范。')

        findings: list[FindingItem] = [
            FindingItem(
                id='H-NORM-SUM-001',
                title='编制依据现行有效性核验',
                severity='info',
                category='evidence_verification',
                layer='L2',
                evidence_status='grounded' if any(item.get('resolvedBy') == 'web' for item in checks) else 'inferred',
                summary=(
                    f"共核验 {len(checks)} 项编制依据，其中现行有效 {sum(1 for item in checks if item.get('status') == 'current')} 项，"
                    f"疑似废止/替代 {sum(1 for item in checks if item.get('status') == 'superseded')} 项，"
                    f"待人工核验 {sum(1 for item in checks if item.get('status') == 'unknown')} 项。"
                ),
                suggestion='被审方案编制依据中现行状态异常或未核实的规范，应在正式引用前补做联网或人工复核。',
                source_engine='hermes',
                finding_type='normative_validity_summary',
                raw_data={
                    'module_name': 'evidence_validation',
                    'normativeValidityChecks': checks,
                },
            )
        ]
        self._annotate_finding_ownership(template, findings[0])
        for idx, check in enumerate(checks, start=1):
            if check.get('status') == 'current':
                continue
            findings.append(
                FindingItem(
                    id=f'H-NORM-{idx:03d}',
                    title=f"编制依据现行有效性存在疑点：{check.get('title', '')}",
                    severity='medium' if check.get('status') == 'superseded' else 'info',
                    category='evidence_verification',
                    layer='L2',
                    evidence_status='grounded' if check.get('resolvedBy') == 'web' else 'inferred',
                    summary=str(check.get('summary') or '当前编制依据的现行状态仍需进一步复核。'),
                    suggestion='如该编制依据已废止、被替代或状态不明，请改用现行版本并同步修正文内引用。',
                    source_engine='hermes',
                    finding_type='normative_validity_issue',
                    raw_data={
                        'module_name': 'evidence_validation',
                        'normativeValidityCheck': check,
                    },
                )
            )
            self._annotate_finding_ownership(template, findings[-1])
        return self._build_packet(template, findings, overall='被审方案“编制依据”现行有效性核验已完成。')

    def _template_review_modules(self, template: AgentTemplate) -> list[str]:
        configured = list(template.metadata.get('review_modules') or [])
        return configured or template_review_modules(template.id)

    def _brief_for_template(self, brief, template: AgentTemplate, governed_support_packet) -> Any:
        focus_lines = []
        if template.instructions:
            focus_lines.append(f'专项职责：{template.instructions}')
        if template.prompt:
            focus_lines.append(f'专项任务：{template.prompt}')
        priority_focus_axes = list(getattr(governed_support_packet, 'priority_focus_axes', []) or [])
        if priority_focus_axes and template.id.startswith('power_outage_'):
            focus_lines.append('优先深挖轴：' + '；'.join(priority_focus_axes))
        if not focus_lines:
            return brief
        merged_query = '\n'.join([brief.query.strip(), *focus_lines]).strip()
        return brief.model_copy(update={'query': merged_query, 'metadata': {**brief.metadata, 'template_id': template.id, 'input_token_limit': template.input_token_limit, 'output_token_limit': template.output_token_limit}})

    def _build_packet(self, template: AgentTemplate, findings: list[FindingItem], *, overall: str) -> FactPacket:
        findings = [self._annotate_finding_ownership(template, finding) for finding in findings]
        metrics = ReviewPacketMetrics(
            total_findings=len(findings),
            high_severity=sum(1 for item in findings if item.severity == 'high'),
            medium_severity=sum(1 for item in findings if item.severity == 'medium'),
            low_severity=sum(1 for item in findings if item.severity == 'low'),
            info_findings=sum(1 for item in findings if item.severity == 'info'),
            grounded_findings=sum(1 for item in findings if item.evidence_status == 'grounded'),
            evidence_gap_findings=sum(1 for item in findings if item.evidence_status == 'evidence_gap'),
            manual_review_needed=sum(1 for item in findings if item.manual_review_needed),
        )
        return FactPacket(
            review_id='agent-runtime',
            engine='hermes',
            summary_metrics=metrics,
            findings=findings,
            overall_assessment=overall,
            produced_at=datetime.now(timezone.utc),
            metadata={
                'agent_id': template.id,
                'template_id': template.id,
                'worker_id': template.execution_mode,
                'module_ids': list(template.module_bindings),
                'review_modules': self._template_review_modules(template),
                'ownership': template.metadata.get('ownership', 'hermes_main_review' if template.execution_mode == 'hermes_router' else 'support_material'),
                'input_token_limit': template.input_token_limit,
                'output_token_limit': template.output_token_limit,
            },
        )
