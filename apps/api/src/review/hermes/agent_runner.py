from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.review.contracts import FactPacket, FindingItem, ReviewPacketMetrics
from src.review.hermes.module_bindings import template_review_modules
from src.review.hermes.constants import is_primary_template_id
from src.review.hermes.template_models import AgentRunResult, AgentTemplate


class HermesAgentRunner:
    def __init__(self, *, hermes_engine, module_registry):
        self.hermes_engine = hermes_engine
        self.module_registry = module_registry

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
            packet = await self.hermes_engine.review(
                brief=brief,
                fact_packet_008=workspace.get('support_packet_008'),
                document_preview=doc_text,
            )
            for finding in packet.findings:
                self._annotate_finding_ownership(template, finding)
            packet.metadata = {
                **packet.metadata,
                'agent_id': template.id,
                'template_id': template.id,
                'worker_id': 'hermes_router',
                'module_ids': list(template.module_bindings),
                'review_modules': template_review_modules(template.id),
                'ownership': 'hermes_main_review',
            }
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
        review_modules = template_review_modules(template.id)
        module_name = self._resolve_finding_module_name(finding, review_modules)
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
                'review_modules': template_review_modules(template.id),
                'ownership': 'support_material',
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
            if visibility.manualReviewNeeded:
                findings.append(FindingItem(
                    id='H-VIS-001',
                    title='文档存在可视域或附件复核要求',
                    severity='medium',
                    category='visibility',
                    finding_type='visibility_gap',
                    evidence_status='visibility_gap',
                    summary=visibility.manualReviewReason or '存在未解析附件、图纸或 PDF 可视域限制。',
                    suggestion='补充可解析附件原件或人工复核图纸/附件。',
                    source_engine='hermes',
                    raw_data={'attachment_count': visibility.attachmentCount},
                ))
                self._annotate_finding_ownership(template, findings[-1])
            return self._build_packet(template, findings, overall='可视域检查已完成。')
        if template.id == 'policy_compliance_reviewer':
            candidates = workspace.get('candidates') or []
            findings: list[FindingItem] = []
            for idx, candidate in enumerate(candidates[:3], start=1):
                findings.append(FindingItem(
                    id=f'H-POL-{idx:03d}',
                    title=candidate.title,
                    severity=candidate.severityHint,
                    category='compliance',
                    layer=str(candidate.layerHint),
                    evidence_status='grounded' if candidate.policyEvidence else 'evidence_gap',
                    basis_refs=[getattr(span.locator, 'clauseId', '') for span in candidate.policyEvidence if getattr(span, 'locator', None)],
                    summary='; '.join(hit.rationale for hit in candidate.ruleHits if hit.rationale)[:300],
                    suggestion='结合命中规则与规范条款进一步补齐正文。',
                    source_engine='hermes',
                    raw_data={'rule_ids': [hit.ruleId for hit in candidate.ruleHits]},
                ))
                self._annotate_finding_ownership(template, findings[-1])
            return self._build_packet(template, findings, overall='规范命中与证据线索已整理。')
        return None

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
                'review_modules': template_review_modules(template.id),
                'ownership': template.metadata.get('ownership', 'hermes_main_review' if template.execution_mode == 'hermes_router' else 'support_material'),
            },
        )
