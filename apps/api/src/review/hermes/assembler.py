from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.review.contracts import FactPacket, FinalReportPacket, FindingItem, ReviewBrief
from src.review.final_report_merger import FinalReportMerger

_GRADE_LABELS = {
    'conditional_pass': '有条件通过',
    'needs_revision': '需要修改',
    'fail': '不通过',
}


class HermesReviewAssembler:
    """Official final output entrypoint for HermesController-first structured review.

    The assembler owns the external final result protocol exposed by controller/runtime.
    FinalReportMerger is only an internal helper used here for packet fusion.
    
    HARD CONSTRAINT: If Hermes main review fails or degrades, this assembler MUST NOT 
    output a formal FinalReportPacket. It must fail-closed and return degraded/support facts.
    """

    def __init__(self):
        self.merger = FinalReportMerger()

    def assemble(
        self,
        *,
        brief: ReviewBrief,
        support_packet_008: FactPacket | None,
        hermes_review_packets: list[FactPacket],
        support_result_008: dict[str, Any] | None,
        agent_results: list[dict[str, Any]],
        enabled_modules: list[str] | None = None,
    ) -> tuple[dict[str, Any], FinalReportPacket | None]:
        
        hermes_ok = bool(hermes_review_packets and not all(p.degraded for p in hermes_review_packets))

        if not hermes_ok:
            # FAIL-CLOSED: Do not emit a formal formal review report if Hermes is unavailable.
            payload = dict(support_result_008 or (support_packet_008.raw_result if support_packet_008 else {}) or {})
            payload['hermesController'] = {
                'enabled': True,
                'selectedAgents': [result.get('agent_id') for result in agent_results],
                'agentResults': agent_results,
                'finalReportReady': False,
                'supplementalPacketCount': 0,
                'mainReviewOwnedBy': 'hermes',
                'decisionOwner': 'hermes',
                'supportOwner': 'structured_review_capability_facade',
                'degraded': True,
            }
            
            error_reason = hermes_review_packets[0].error if hermes_review_packets and hermes_review_packets[0].error else "主审引擎未返回有效裁决"
            fallback_markdown = self._render_degraded_markdown(
                doc_label=_GRADE_LABELS.get(str(brief.review_object_type), str(brief.review_object_type)),
                support_packet=support_packet_008,
                error_reason=error_reason
            )
            payload['finalReportMarkdown'] = fallback_markdown
            payload['finalAnswer'] = fallback_markdown
            payload['traceability'] = []
            return payload, None

        merged_hermes_main_review = self._merge_hermes_review_outcomes(support_packet_008.review_id if support_packet_008 else brief.review_id, hermes_review_packets)
        support_packet_008, merged_hermes_main_review = self._apply_support_confidence_adjustments(
            support_packet_008=support_packet_008,
            hermes_review_packet=merged_hermes_main_review,
        )
        support_packet_008, merged_hermes_main_review = self._resolve_conflicts_and_gaps(
            support_packet_008=support_packet_008,
            hermes_review_packet=merged_hermes_main_review,
        )
        support_packet_008 = self._filter_packet_by_enabled_modules(support_packet_008, enabled_modules)
        merged_hermes_main_review = self._filter_packet_by_enabled_modules(merged_hermes_main_review, enabled_modules)
        final_packet = self._build_final_decision_packet(
            brief=brief,
            support_packet_008=support_packet_008,  # type: ignore
            hermes_review_packet=merged_hermes_main_review,
        )
        final_packet.metadata = {
            **final_packet.metadata,
            'assembler': 'hermes_review_assembler',
            'supplemental_packet_count': len(hermes_review_packets),
            'decision_owner': 'hermes',
            'support_owner': 'structured_review_capability_facade',
            'final_output_entrypoint': 'hermes_review_assembler',
            'selected_review_modules': list(enabled_modules or []),
            'executed_review_modules': self._executed_modules(
                support_packet_008=support_packet_008,
                hermes_review_packet=merged_hermes_main_review,
                enabled_modules=enabled_modules,
            ),
        }
        
        # SUCCESS PATH: Build payload from assembler contract — NOT from support_result_008.
        # Support layer data is placed into an explicit sub-key, preventing it from
        # becoming the implicit root of the formal payload.
        payload: dict[str, Any] = {}
        payload['hermesController'] = {
            'enabled': True,
            'selectedAgents': [result.get('agent_id') for result in agent_results],
            'agentResults': agent_results,
            'finalReportReady': True,
            'supplementalPacketCount': len(hermes_review_packets),
            'mainReviewOwnedBy': 'hermes',
            'decisionOwner': 'hermes',
            'supportOwner': 'structured_review_capability_facade',
        }
        # Authoritative formal report fields — assembler owns these exclusively.
        payload['traceability'] = final_packet.traceability
        payload['finalReportMarkdown'] = final_packet.report_markdown
        payload['finalReportPacket'] = final_packet.model_dump(mode='json')
        payload['finalAnswer'] = final_packet.report_markdown
        # Support layer context placed in a dedicated sub-key (not at root level).
        if support_result_008:
            payload['supportLayerContext'] = support_result_008
        
        return payload, final_packet

    def _render_degraded_markdown(self, doc_label: str, support_packet: FactPacket | None, error_reason: str) -> str:
        lines: list[str] = []
        lines.append(f'# {doc_label} — 预检结果与支撑层数据（非正式审查报告）\n')
        lines.append(f'> **【系统状态提示】**\n> 审查主控引擎（Hermes）未能完整执行或当前处于不可用状态（原因：{error_reason}）。由于系统启用严格的安全边界限制（Fail-Closed 原则），**本次任务无法生成正式审查裁决报告**。下面列出的内容仅为结构化引擎初步提取的原始支撑证据，不代表最终通过或拒绝的审查结论，请安排人工专项复核。\n')
        
        if not support_packet or not support_packet.findings:
            lines.append('未提取到明确的预检支撑事实或结构化内容丢失。')
            return '\n'.join(lines)
            
        lines.append('## 底层提取异常或风险预警（仅供参考）\n')
        for finding in support_packet.findings:
            lines.append(f'- **[{finding.severity.upper()}]** {finding.title}')
            if finding.summary:
                lines.append(f'  {finding.summary[:200]}')
        lines.append('')
        return '\n'.join(lines)


    def _merge_hermes_review_outcomes(self, review_id: str, packets: list[FactPacket]) -> FactPacket | None:
        if not packets:
            return None
        findings = []
        metadata_packets = []
        for packet in packets:
            findings.extend(packet.findings)
            metadata_packets.append({
                'metadata': packet.metadata,
                'overall_assessment': packet.overall_assessment,
            })
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
            review_id=review_id,
            engine='hermes',
            summary_metrics=metrics,
            findings=findings,
            overall_assessment='；'.join(packet.overall_assessment for packet in packets if packet.overall_assessment),
            produced_at=datetime.now(timezone.utc),
            metadata={
                'worker_id': 'supplemental_packet_merge',
                'source_packets': metadata_packets,
                'ownership': 'hermes_main_review',
            },
        )

    def _apply_support_confidence_adjustments(
        self,
        *,
        support_packet_008: FactPacket | None,
        hermes_review_packet: FactPacket | None,
    ) -> tuple[FactPacket | None, FactPacket | None]:
        if hermes_review_packet is None or support_packet_008 is None:
            return support_packet_008, hermes_review_packet
        adjusted_support = support_packet_008.model_copy(deep=True)
        hermes_titles = {finding.title for finding in hermes_review_packet.findings}
        for finding in adjusted_support.findings:
            if finding.title in hermes_titles:
                finding.raw_data = {**finding.raw_data, 'hermes_decision_signal': 'corroborated'}
        return adjusted_support, hermes_review_packet

    def _resolve_conflicts_and_gaps(
        self,
        *,
        support_packet_008: FactPacket | None,
        hermes_review_packet: FactPacket | None,
    ) -> tuple[FactPacket | None, FactPacket | None]:
        if hermes_review_packet is None or support_packet_008 is None:
            return support_packet_008, hermes_review_packet
        adjusted_hermes = hermes_review_packet.model_copy(deep=True)
        support_titles = {finding.title for finding in support_packet_008.findings}
        for finding in adjusted_hermes.findings:
            if finding.evidence_status in {'evidence_gap', 'visibility_gap'}:
                finding.raw_data = {**finding.raw_data, 'decision_action': 'degraded_by_support_evidence_gap'}
            elif finding.title not in support_titles:
                finding.raw_data = {**finding.raw_data, 'decision_action': 'supplement_from_support_gap_scan'}
        return support_packet_008, adjusted_hermes

    def _build_final_decision_packet(
        self,
        *,
        brief: ReviewBrief,
        support_packet_008: FactPacket,
        hermes_review_packet: FactPacket | None,
    ) -> FinalReportPacket:
        material = self.merger.prepare_decision_material(
            brief=brief,
            packet_008=support_packet_008,
            packet_hermes=hermes_review_packet,
        )

        all_findings = material['all_findings']
        key_findings = material['key_findings']
        supplemental_findings = material['supplemental_findings']

        # Hermes Assembler decides the final grade and risks
        top_risks = [item for item in all_findings if item.severity == 'high']
        final_grade = self._decide_grade(all_findings)
        executive_summary = self._decide_executive_summary(
            all_findings=all_findings,
            executed_modules=self._executed_modules(
                support_packet_008=support_packet_008,
                hermes_review_packet=hermes_review_packet,
                enabled_modules=None,
            ),
            grade=final_grade
        )

        report_markdown = self._render_markdown(
            doc_label=material['doc_label'],
            summary=executive_summary,
            all_findings=all_findings,
            engines=material['engines_used'],
            degradation=material['degradation_info'],
        )

        packet = FinalReportPacket(
            review_id=brief.review_id,
            final_grade=final_grade,
            executive_summary=executive_summary,
            top_risks=top_risks,
            key_findings=key_findings,
            supplemental_findings=supplemental_findings,
            all_findings=all_findings,
            traceability=material['traceability'],
            report_markdown=report_markdown,
            engines_used=material['engines_used'],
            degradation_info=material['degradation_info'],
            produced_at=datetime.now(timezone.utc),
            source_packets=material['source_packets'],
        )

        self._annotate_final_decision_findings(
            packet,
            support_packet_008=support_packet_008,
            hermes_review_packet=hermes_review_packet,
        )
        return packet

    def _filter_packet_by_enabled_modules(
        self,
        packet: FactPacket | None,
        enabled_modules: list[str] | None,
    ) -> FactPacket | None:
        if packet is None or not enabled_modules:
            return packet
        allowed = {module for module in enabled_modules if module}
        filtered = packet.model_copy(deep=True)
        filtered.findings = [
            finding
            for finding in filtered.findings
            if self._finding_in_enabled_modules(finding, allowed)
        ]
        filtered.summary_metrics = ReviewPacketMetrics(
            total_findings=len(filtered.findings),
            high_severity=sum(1 for finding in filtered.findings if finding.severity == 'high'),
            medium_severity=sum(1 for finding in filtered.findings if finding.severity == 'medium'),
            low_severity=sum(1 for finding in filtered.findings if finding.severity == 'low'),
        )
        filtered.metadata = {
            **filtered.metadata,
            'selected_review_modules': list(enabled_modules),
            'executed_review_modules': self._packet_review_modules(filtered, allowed),
        }
        return filtered

    def _finding_in_enabled_modules(self, finding: FindingItem, allowed: set[str]) -> bool:
        raw_data = dict(finding.raw_data or {})
        module_name = raw_data.get('module_name')
        if isinstance(module_name, str) and module_name in allowed:
            return True
        review_modules = raw_data.get('review_modules') or []
        return any(isinstance(module, str) and module in allowed for module in review_modules)

    def _packet_review_modules(self, packet: FactPacket, allowed: set[str] | None = None) -> list[str]:
        modules: list[str] = []
        for finding in packet.findings:
            raw_data = dict(finding.raw_data or {})
            candidates = []
            if isinstance(raw_data.get('module_name'), str):
                candidates.append(raw_data['module_name'])
            for module in raw_data.get('review_modules') or []:
                if isinstance(module, str):
                    candidates.append(module)
            for module in candidates:
                if allowed and module not in allowed:
                    continue
                if module not in modules:
                    modules.append(module)
        return modules

    def _executed_modules(
        self,
        *,
        support_packet_008: FactPacket | None,
        hermes_review_packet: FactPacket | None,
        enabled_modules: list[str] | None,
    ) -> list[str]:
        allowed = {module for module in enabled_modules or [] if module} or None
        modules: list[str] = []
        for packet in [support_packet_008, hermes_review_packet]:
            if packet is None:
                continue
            for module in self._packet_review_modules(packet, allowed):
                if module not in modules:
                    modules.append(module)
        return modules

    def _decide_grade(self, all_findings: list[FindingItem]) -> str:
        high = sum(1 for finding in all_findings if finding.severity == 'high')
        medium = sum(1 for finding in all_findings if finding.severity == 'medium')
        if high >= 3:
            return 'fail'
        if high >= 1 or medium >= 5:
            return 'needs_revision'
        return 'conditional_pass'

    def _decide_executive_summary(
        self,
        all_findings: list[FindingItem],
        executed_modules: list[str],
        grade: str,
    ) -> str:
        high_count = sum(1 for finding in all_findings if finding.severity == 'high')
        medium_count = sum(1 for finding in all_findings if finding.severity == 'medium')
        low_count = sum(1 for finding in all_findings if finding.severity == 'low')
        module_labels = {
            'structure_completeness': '章节完整性',
            'parameter_consistency': '参数一致性',
            'legality_compliance': '合法合规性',
            'execution_continuity': '工序连贯性',
            'evidence_validation': '证据验证',
        }
        covered_modules = '、'.join(module_labels.get(module, module) for module in executed_modules[:5])
        lines = [
            f"本次审查已由专业主审组件裁决完成，总体评级结论为：**{_GRADE_LABELS.get(grade, grade)}**。",
            f"本次结果共覆盖 {len(executed_modules)} 个审查模块{f'（{covered_modules}）' if covered_modules else ''}，形成 {len(all_findings)} 项审查问题（高风险 {high_count} 项，中等风险 {medium_count} 项，低风险 {low_count} 项）。",
        ]
        return ' '.join(lines)

    def _render_markdown(
        self,
        doc_label: str,
        summary: str,
        all_findings: list[FindingItem],
        engines: list[str],
        degradation: dict[str, Any],
    ) -> str:
        lines: list[str] = []
        lines.append(f'# {doc_label} — 综合审查报告\n')
        lines.append(f'## 最终合成裁决\n\n{summary}\n')

        dimension_map = {
            'chapter_completeness': '一、 章节完整性',
            'structure': '一、 章节完整性',
            'visibility': '一、 章节完整性',
            'parameter_consistency': '二、 参数一致性',
            'compliance': '三、 合法合规性',
            'safety': '三、 合法合规性',
            'rule_hits': '三、 合法合规性',
            'process_coherence': '四、 工序连贯性',
            'evidence_verification': '五、 证据验证',
            'facts': '五、 证据验证',
        }

        grouped_findings: dict[str, list[FindingItem]] = {
            '一、 章节完整性': [],
            '二、 参数一致性': [],
            '三、 合法合规性': [],
            '四、 工序连贯性': [],
            '五、 证据验证': [],
            '六、 其他审查发现': [],
        }

        # Deduplicate to prevent overlapping items
        seen_ids = set()
        seen_titles = set()
        deduped_findings = []
        for finding in all_findings:
            title_key = finding.title.lower().strip()
            if finding.id not in seen_ids and title_key not in seen_titles:
                seen_ids.add(finding.id)
                seen_titles.add(title_key)
                deduped_findings.append(finding)

        for finding in deduped_findings:
            dim = dimension_map.get(finding.category, '六、 其他审查发现')
            grouped_findings[dim].append(finding)

        severity_order = {'high': 0, 'medium': 1, 'low': 2, 'info': 3}
        severity_zh_map = {'high': '高风险', 'medium': '中等风险', 'low': '低风险', 'info': '提示'}
        for dim_title, items in grouped_findings.items():
            if not items:
                continue
            lines.append(f'## {dim_title}\n')
            items.sort(key=lambda x: severity_order.get(x.severity, 99))
            
            for finding in items:
                severity_zh = severity_zh_map.get(finding.severity.lower(), finding.severity.upper())
                lines.append(f'- **[{severity_zh}]** {finding.title}')
                if finding.summary:
                    lines.append(f'  > {finding.summary.strip()}')
                if finding.suggestion:
                    lines.append(f'  **整改建议**: {finding.suggestion.strip()}')
            lines.append('')
        for engine, info in degradation.items():
            lines.append(f"- 组件降级通报: {engine} 模块异常 ({info.get('reason', '未知')})")
        lines.append('')
        return '\n'.join(lines)

    def _annotate_final_decision_findings(
        self,
        packet: FinalReportPacket,
        *,
        support_packet_008: FactPacket,
        hermes_review_packet: FactPacket | None,
    ) -> None:
        support_modules = list(support_packet_008.metadata.get('review_modules') or [])
        hermes_modules = list((hermes_review_packet.metadata if hermes_review_packet else {}).get('review_modules') or [])

        for finding in packet.key_findings:
            module_name = self._prefer_single_module(
                finding.raw_data.get('review_modules'),
                support_modules,
            )
            finding.raw_data = {
                **finding.raw_data,
                'decision_role': 'key_finding',
                'decision_owner': 'hermes',
                'ownership': finding.raw_data.get('ownership', support_packet_008.metadata.get('ownership', 'support_material')),
                'source_template_id': finding.raw_data.get('template_id') or support_packet_008.metadata.get('template_id'),
                'review_modules': finding.raw_data.get('review_modules') or support_modules,
                **({'module_name': module_name} if module_name else {}),
            }

        for finding in packet.supplemental_findings:
            module_name = self._prefer_single_module(
                finding.raw_data.get('review_modules'),
                hermes_modules,
            )
            finding.raw_data = {
                **finding.raw_data,
                'decision_role': 'supplemental_finding',
                'decision_owner': 'hermes',
                'ownership': finding.raw_data.get('ownership', 'hermes_main_review'),
                'source_template_id': finding.raw_data.get('template_id') or (hermes_review_packet.metadata.get('template_id') if hermes_review_packet else None),
                'review_modules': finding.raw_data.get('review_modules') or hermes_modules,
                **({'module_name': module_name} if module_name else {}),
            }

        final_index = {finding.id: finding for finding in packet.key_findings + packet.supplemental_findings}
        for finding in packet.all_findings:
            source = final_index.get(finding.id)
            if source is not None:
                finding.raw_data = {**source.raw_data}
            else:
                finding.raw_data = {
                    **finding.raw_data,
                    'decision_role': 'all_finding',
                    'decision_owner': 'hermes',
                }

    def _prefer_single_module(self, *module_lists: Any) -> str | None:
        for modules in module_lists:
            if isinstance(modules, list) and len(modules) == 1 and modules[0]:
                return str(modules[0])
        return None
