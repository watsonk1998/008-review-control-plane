from __future__ import annotations

from collections import Counter

from src.review.evidence.packs import get_evidence_pack_registry
from src.review.schema import (
    ResolvedReviewProfile,
    StructuredReviewMatrices,
    StructuredReviewSummary,
    StructuredReviewVisibilitySummary,
)


class StructuredReviewReportBuilder:
    _SEVERITY_ORDER = {'high': 0, 'medium': 1, 'low': 2, 'info': 3}
    _DOCUMENT_TYPE_LABELS = {
        'construction_org': '施工组织设计',
        'construction_scheme': '施工方案',
        'hazardous_special_scheme': '危大专项施工方案',
        'supervision_plan': '监理规划',
        'review_support_material': '审查支持材料',
    }
    _ISSUE_KIND_LABELS = {
        'hard_defect': '硬缺陷',
        'visibility_gap': '可视域缺口',
        'evidence_gap': '证据缺口',
        'enhancement': '优化建议',
    }
    _SEVERITY_LABELS = {'high': '高', 'medium': '中', 'low': '低', 'info': '提示'}
    _APPLICABILITY_LABELS = {
        'applies': '已满足当前判定条件',
        'partial': '仅形成部分判定',
        'blocked_by_visibility': '受可视域限制，需人工结合原件复核',
        'blocked_by_missing_fact': '关键事实不足，暂不能形成闭合判定',
    }
    _PARSE_MODE_LABELS = {
        'docx_structured': '结构化文档解析',
        'pdf_text_only': 'PDF 文本受限解析',
        'markdown_text': 'Markdown 文本解析',
        'plain_text': '纯文本解析',
    }
    _FILE_TYPE_LABELS = {'docx': 'Word 文档', 'pdf': 'PDF 文档', 'md': 'Markdown 文档', 'txt': '文本文件'}
    _STRUCTURE_STATUS_LABELS = {
        'matched': '符合',
        'partial': '部分符合',
        'missing': '缺失',
        'blocked_by_visibility': '受可视域限制',
    }
    _MANUAL_REVIEW_REASON_LABELS = {
        'title_detected_without_attachment_body': '已识别到附件标题，但附件正文未进入当前可视域。',
        'title_detected_but_body_not_reliably_parsed': '已识别到附件标题，但正文解析可靠性不足。',
        'reference_detected_in_limited_parser': '正文存在附件引用，但当前受限解析路径无法可靠定位附件内容。',
        'reference_detected_without_attachment_body': '正文提及附件，但附件正文未进入当前可视域。',
        'attachment_unparsed': '存在未完成解析的附件或附图。',
        'referenced_only': '正文仅提及附件，未取得附件正文。',
        'visibility_unknown': '当前无法确认附件或附图的可视状态。',
        'parser_limited_pdf_requires_manual_review': '当前 PDF 仅按文本路径解析，需结合原件人工复核。',
        'weak_section_structure_signal': '关键章节或附件边界重复，正式定位结果不稳定。',
        'visibility_gap': '当前问题受附件可视域限制，需人工核验原件。',
        'manual_confirmation_required': '当前问题仍需人工确认。',
    }
    _BLOCKING_REASON_LABELS = {
        'visibility_gap': '当前问题受附件或图纸可视域限制。',
        'attachment_unparsed': '附件标题已识别，但正文未完成可靠解析。',
        'referenced_only': '正文已引用附件，但附件正文未进入当前可视域。',
        'visibility_unknown': '当前无法确认附件或图纸状态。',
        'parser_limited_pdf_requires_manual_review': 'PDF 受限解析路径不足以支撑直接下结论。',
        'weak_section_structure_signal': '章节结构存在重复或边界不稳，定位需谨慎。',
        'missing_fact': '完成判定所需关键事实尚未提取完整。',
        'parser_limited_source': '受限解析路径导致证据链未闭合。',
        'document_evidence_unavailable': '文档侧证据不足以支撑硬性结论。',
        'policy_evidence_unavailable': '条文依据链未完全闭合。',
        'manual_confirmation_required': '仍需人工确认现场条件或附件内容。',
    }
    _INTERNAL_POLICY_SOURCES = {
        'review-control-plane-support-scope-policy': '系统审查支持材料边界规则',
        'review-control-plane-visibility-policy': '系统附件可视域处理规则',
    }
    _HAZARD_VALUE_LABELS = {
        'liftingOperation': '涉及起重吊装作业',
        'gasArea': '涉及煤气区域作业',
        'hotWork': '涉及动火作业',
        'temporaryPower': '涉及临时用电',
        'specialEquipmentMentioned': '提及特种设备',
        'craneCapacityTon': '起重设备额定吨位',
        'calculatedLiftWeightTon': '计算吊重',
        'shutdownWindowDays': '停机窗口天数',
        'laborTotal': '劳动力总量',
        'calculationEvidencePresent': '已提取验算依据',
        'measureSectionPresent': '已识别风险控制措施章节',
        'monitoringSectionPresent': '已识别监测监控章节',
    }
    _L1_STRUCTURE_TITLES = {
        '施工组织设计核心章节不完整',
        '章节结构存在重复标题，正式审查定位不稳定',
    }
    _L1_PREFLIGHT_TITLES = {
        '附件处于可视域缺口，需人工复核原件',
    }

    def build_summary(
        self,
        *,
        document_type: str,
        selected_packs: list[str],
        issues,
        matrices: StructuredReviewMatrices,
        visibility,
        parse_warnings: list[str],
        unresolved_facts,
    ):
        layer_counts = Counter(issue.layer.value for issue in issues)
        manual_review_needed = visibility.manualReviewNeeded or any(issue.manualReviewNeeded for issue in issues)
        high_risk_issue = any(issue.layer.value == 'L1' and issue.severity in {'high', 'medium'} for issue in issues)
        if high_risk_issue:
            overall = '修改后重新报审'
        elif manual_review_needed:
            overall = '需人工复核'
        else:
            overall = '合格通过'
        visibility_summary = StructuredReviewVisibilitySummary(
            attachmentCount=visibility.attachmentCount,
            counts=visibility.counts,
            duplicateSectionTitles=visibility.duplicateSectionTitles,
            parseWarnings=visibility.parseWarnings or parse_warnings,
            reasonCounts=visibility.reasonCounts,
            manualReviewNeeded=visibility.manualReviewNeeded,
        )
        return StructuredReviewSummary(
            overallConclusion=overall,
            documentType=document_type,
            selectedPacks=selected_packs,
            manualReviewNeeded=manual_review_needed,
            issueCount=len(issues),
            layerCounts=dict(layer_counts),
            stats={
                'attachmentCount': len(matrices.attachmentVisibility),
                'ruleHitCount': sum(1 for item in matrices.ruleHits if item.status in {'hit', 'manual_review_needed'}),
                'unresolvedFactCount': len(unresolved_facts),
                'issueKindCounts': dict(Counter(issue.issueKind for issue in issues)),
                'preflightGateDecision': visibility.preflight.gateDecision,
                'blockedIssueCount': sum(
                    1 for issue in issues if issue.applicabilityState in {'blocked_by_visibility', 'blocked_by_missing_fact'}
                ),
            },
            visibilitySummary=visibility_summary,
        )

    def build_issue_buckets(self, issues) -> dict[str, list[dict[str, str]]]:
        bucket_order = ['hard_defect', 'visibility_gap', 'evidence_gap', 'enhancement']
        buckets = {bucket: [] for bucket in bucket_order}
        for issue in issues:
            buckets.setdefault(issue.issueKind, []).append(
                {
                    'id': issue.id,
                    'title': issue.title,
                    'layer': issue.layer.value,
                    'severity': issue.severity,
                }
            )
        return buckets

    def render(
        self,
        *,
        summary: StructuredReviewSummary,
        resolved_profile: ResolvedReviewProfile,
        issues,
        matrices: StructuredReviewMatrices,
        parse_result,
        unresolved_facts,
    ) -> str:
        document_label = self._document_type_label(summary.documentType)
        basis_files = self._collect_basis_files(summary.selectedPacks or resolved_profile.policyPackIds, issues)
        layer_sections = {
            'L1': '第二部分：L1 审查发现——合法合规与结构完整性',
            'L2': '第三部分：L2 审查发现——核心参数与规则实质性验证',
            'L3': '第四部分：L3 审查发现——工程逻辑与实施风险预判',
        }
        lines = [
            f'# {document_label}形式审查报告',
            '',
            '## 第一部分：审查结论与可视域门禁',
            '',
            '### 1. 总体审查结论',
            f'- 审查结论：{summary.overallConclusion}',
            f'- 文档类型：{document_label}',
            f'- 是否需人工复核：{"是" if summary.manualReviewNeeded else "否"}',
            f'- 当前识别问题总数：{summary.issueCount} 项',
            '',
            '### 2. 审查依据文件',
        ]
        if basis_files['primary']:
            lines.extend(['- 主要审查依据文件：', *[f'  - {item}' for item in basis_files['primary']]])
        else:
            lines.append('- 主要审查依据文件：本次未提取到可直接展示的外部规范或法规条文来源。')
        if basis_files['supplemental']:
            lines.extend(['- 补充依据：', *[f'  - {item}' for item in basis_files['supplemental']]])
        lines.append('')
        lines.extend(
            [
                '### 3. 可视域与预检状态',
                f'- 预检状态：{self._preflight_gate_label(parse_result.visibility.preflight.gateDecision)}',
                f'- 当前解析方式：{self._parse_mode_label(parse_result.visibility.parseMode or parse_result.parseMode)}',
                f'- 文件类型：{self._file_type_label(parse_result.visibility.fileType or parse_result.fileType)}',
                f'- 已识别附件数量：{parse_result.visibility.attachmentCount}',
                f'- 人工复核说明：{self._manual_review_reason_text(parse_result.visibility.manualReviewReason)}',
                *self._render_preflight_blocking_lines(parse_result.visibility.preflight.blockingReasons),
                *self._render_visibility_observation_lines(parse_result.visibility),
                '',
                '### 4. 附件可视域断链',
                *self._render_attachment_gaps(matrices.attachmentVisibility),
                '',
                '### 5. 待人工确认事项',
                *self._render_unresolved_facts(unresolved_facts),
                '',
            ]
        )

        lines.extend(['## ' + layer_sections['L1'], ''])
        if summary.documentType == 'construction_org' and matrices.structureCompleteness:
            l1_structure_issues = [
                issue
                for issue in issues
                if issue.layer.value == 'L1' and issue.title in self._L1_STRUCTURE_TITLES
            ]
            l1_compliance_issues = [
                issue
                for issue in issues
                if issue.layer.value == 'L1' and issue.title not in self._L1_STRUCTURE_TITLES | self._L1_PREFLIGHT_TITLES
            ]
            lines.extend(self._render_construction_org_l1_section(matrices, l1_structure_issues, l1_compliance_issues))
        else:
            l1_issues = sorted(
                [issue for issue in issues if issue.layer.value == 'L1'],
                key=lambda issue: (self._SEVERITY_ORDER.get(issue.severity, 99), issue.title),
            )
            if l1_issues:
                basis_lines = self._render_layer_basis(l1_issues)
                if basis_lines:
                    lines.extend(['### 主要审查依据', *basis_lines, ''])
            if not l1_issues:
                lines.extend(['- 本层未发现需要单独提示的问题。', ''])
            else:
                for index, issue in enumerate(l1_issues, start=1):
                    lines.extend(self._render_issue(index, issue))

        for layer in ['L2', 'L3']:
            lines.extend(['## ' + layer_sections[layer], ''])
            layer_issues = sorted(
                [issue for issue in issues if issue.layer.value == layer],
                key=lambda issue: (self._SEVERITY_ORDER.get(issue.severity, 99), issue.title),
            )
            if layer_issues:
                basis_lines = self._render_layer_basis(layer_issues)
                if basis_lines:
                    lines.extend(['### 主要审查依据', *basis_lines, ''])
            if not layer_issues:
                lines.extend(['- 本层未发现需要单独提示的问题。', ''])
                continue
            for index, issue in enumerate(layer_issues, start=1):
                lines.extend(self._render_issue(index, issue))

        lines.extend(
            [
                '## 第五部分：核心数据提取矩阵',
                '',
                '### 1. 危大工程识别情况',
                *self._render_hazard_summary(matrices.hazardIdentification.values),
                '',
                '### 2. 附件可视域情况',
                *self._render_attachment_matrix_summary(matrices.attachmentVisibility, parse_result.visibility),
                '',
                '### 3. 施组结构完整性情况',
                *self._render_structure_completeness_summary(matrices.structureCompleteness),
                '',
                '### 4. 章节结构情况',
                *self._render_section_structure_summary(matrices.sectionStructure, parse_result.visibility),
                '',
                '### 5. 规则命中总体情况',
                *self._render_rule_hit_summary(matrices.ruleHits),
                '',
                '### 6. 主要冲突与联动提示',
                *self._render_conflict_summary(matrices.conflicts.values),
                '',
                '说明：完整结构化结果、矩阵明细及可追溯工件已保留在系统结果与附件中，供复核和留档使用。',
            ]
        )
        return '\n'.join(lines)

    def _document_type_label(self, document_type: str) -> str:
        return self._DOCUMENT_TYPE_LABELS.get(document_type, document_type)

    def _parse_mode_label(self, parse_mode: str | None) -> str:
        return self._PARSE_MODE_LABELS.get(parse_mode or '', '未识别解析方式')

    def _file_type_label(self, file_type: str | None) -> str:
        return self._FILE_TYPE_LABELS.get((file_type or '').lower(), file_type or '未识别文件类型')

    def _preflight_gate_label(self, gate: str | None) -> str:
        return '需先进入人工复核' if gate == 'manual_review_required' else '可进入正式审查'

    def _manual_review_reason_text(self, reason: str | None) -> str:
        if not reason:
            return '当前未触发额外人工复核说明。'
        return self._MANUAL_REVIEW_REASON_LABELS.get(reason, f'需人工复核，原因：{reason}')

    def _blocking_reason_text(self, reason: str) -> str:
        return self._BLOCKING_REASON_LABELS.get(reason, reason)

    def _issue_kind_label(self, issue_kind: str) -> str:
        return self._ISSUE_KIND_LABELS.get(issue_kind, issue_kind)

    def _severity_label(self, severity: str) -> str:
        return self._SEVERITY_LABELS.get(severity, severity)

    def _applicability_label(self, applicability_state: str) -> str:
        return self._APPLICABILITY_LABELS.get(applicability_state, applicability_state)

    def _normalize_policy_source(self, source_id: str) -> tuple[str, bool]:
        if source_id in self._INTERNAL_POLICY_SOURCES:
            return self._INTERNAL_POLICY_SOURCES[source_id], False
        if '《' in source_id:
            return source_id[source_id.index('《'):], True
        return source_id, not source_id.startswith('review-control-plane-')

    def _collect_basis_files(self, selected_packs: list[str], issues) -> dict[str, list[str]]:
        primary: list[str] = []
        supplemental: list[str] = []
        seen: set[str] = set()
        for source_id in self._iter_policy_source_ids(selected_packs, issues):
            label, is_external = self._normalize_policy_source(source_id)
            if label in seen:
                continue
            seen.add(label)
            if is_external:
                primary.append(label)
            else:
                supplemental.append(label)
        return {'primary': primary, 'supplemental': supplemental}

    def _iter_policy_source_ids(self, selected_packs: list[str], issues):
        for issue in issues:
            for span in issue.policyEvidence:
                if span.sourceId:
                    yield span.sourceId
        registry = get_evidence_pack_registry()
        for pack_id in selected_packs:
            pack = registry.get(pack_id)
            if not pack:
                continue
            for clause in pack.clauses:
                if clause.sourceId:
                    yield clause.sourceId

    def _render_preflight_blocking_lines(self, blocking_reasons: list[str]) -> list[str]:
        if not blocking_reasons:
            return ['- 预检阻断说明：当前未识别额外阻断项。']
        details = '；'.join(self._blocking_reason_text(reason) for reason in blocking_reasons)
        return [f'- 预检阻断说明：{details}']

    def _render_visibility_observation_lines(self, visibility) -> list[str]:
        lines: list[str] = []
        counts = visibility.counts or {}
        if counts:
            observations = []
            if counts.get('parsed', 0):
                observations.append(f'已完整进入可视域的附件 {counts["parsed"]} 项')
            if counts.get('attachment_unparsed', 0):
                observations.append(f'标题已识别但正文未解析的附件 {counts["attachment_unparsed"]} 项')
            if counts.get('referenced_only', 0):
                observations.append(f'仅在正文中被提及的附件 {counts["referenced_only"]} 项')
            if counts.get('unknown', 0):
                observations.append(f'状态暂不能确认的附件 {counts["unknown"]} 项')
            if counts.get('missing', 0):
                observations.append(f'存在明确缺失证据的附件 {counts["missing"]} 项')
            if observations:
                lines.append(f'- 可视域概况：{"；".join(observations)}。')
        duplicates = visibility.duplicateSectionTitles or []
        if duplicates:
            lines.append(f'- 章节结构提示：存在重复标题，重点包括：{"、".join(duplicates[:5])}。')
        elif not lines:
            lines.append('- 可视域概况：当前未检测到额外的结构提示。')
        return lines

    def _render_attachment_gaps(self, attachment_items) -> list[str]:
        gap_items = [item for item in attachment_items if item.visibility.value != 'parsed' or item.manualReviewNeeded]
        if not gap_items:
            return ['- 当前未发现需要单独提示的附件可视域断链。']
        lines = []
        for item in gap_items:
            reason = self._manual_review_reason_text(item.reason) if item.reason else '当前附件未完全进入可视域。'
            lines.append(f'- {item.attachmentNumber}《{item.title}》：{reason}')
        return lines

    def _render_unresolved_facts(self, unresolved_facts) -> list[str]:
        if not unresolved_facts:
            return ['- 当前未形成单独列示的待人工确认事实。']
        return [f'- {item.summary}' for item in unresolved_facts]

    def _render_construction_org_l1_section(self, matrices: StructuredReviewMatrices, structure_issues, compliance_issues) -> list[str]:
        lines = [
            '### 2.1 结构完整性与形式合规性',
            '- 审查依据：本节仅依据《建筑施工组织设计规范》GB/T 50502-2009 进行结构完整性与形式合规性审查。',
            f'- 总体结论：{self._structure_completeness_conclusion(matrices.structureCompleteness)}',
            '',
            '| 序号 | 规范要求 | 规范依据 | 文档对应章节 | 结构判定 | 定位说明 |',
            '| --- | --- | --- | --- | --- | --- |',
        ]
        for index, row in enumerate(matrices.structureCompleteness, start=1):
            lines.append(
                '| {index} | {label} | {basis} | {sections} | {status} | {excerpt} |'.format(
                    index=index,
                    label=row.requirementLabel,
                    basis=row.basisClause,
                    sections=self._matched_sections_text(row.matchedSections),
                    status=self._STRUCTURE_STATUS_LABELS.get(row.status, row.status),
                    excerpt=row.reportExcerpt,
                )
            )
        lines.extend(['', '#### 缺项分析与补齐意见'])
        lines.extend(self._render_structure_followups(matrices.structureCompleteness))
        duplicate_issue = next((issue for issue in structure_issues if issue.title == '章节结构存在重复标题，正式审查定位不稳定'), None)
        if duplicate_issue is not None:
            lines.extend(
                [
                    '',
                    '#### 结构稳定性提示',
                    f'- {duplicate_issue.summary}',
                    f'- 当前风险/限制：{self._duplicate_issue_detail(duplicate_issue)}',
                    '- 审查建议：',
                    *[f'  - {item}' for item in (duplicate_issue.recommendation or ['统一重复标题和章节编号，避免正式审查定位混乱。'])],
                ]
            )
        lines.append('')
        lines.extend(['### 2.2 合法合规与法定挂接问题'])
        if compliance_issues:
            basis_lines = self._render_layer_basis(compliance_issues)
            if basis_lines:
                lines.extend(['- 主要审查依据：', *[f'  - {item[2:]}' if item.startswith('- ') else f'  - {item}' for item in basis_lines], ''])
            for index, issue in enumerate(
                sorted(compliance_issues, key=lambda issue: (self._SEVERITY_ORDER.get(issue.severity, 99), issue.title)),
                start=1,
            ):
                lines.extend(self._render_issue(index, issue))
        else:
            lines.extend(['- 当前未发现需要单列提示的法定挂接问题。', ''])
        return lines

    def _structure_completeness_conclusion(self, rows) -> str:
        if not rows:
            return '当前未生成结构完整性矩阵。'
        missing_count = sum(1 for row in rows if row.status == 'missing')
        partial_count = sum(1 for row in rows if row.status == 'partial')
        blocked_count = sum(1 for row in rows if row.status == 'blocked_by_visibility')
        if missing_count == partial_count == blocked_count == 0:
            return '对照 GB/T 50502-2009，本文件结构主干已形成闭合。'
        parts: list[str] = []
        if missing_count:
            parts.append(f'存在 {missing_count} 项明确缺项')
        if partial_count:
            parts.append(f'存在 {partial_count} 项仅部分识别')
        if blocked_count:
            parts.append(f'存在 {blocked_count} 项受可视域限制')
        return f'对照 GB/T 50502-2009，本文件结构主干未完全闭合，{"，".join(parts)}。'

    def _matched_sections_text(self, matched_sections) -> str:
        if not matched_sections:
            return '未识别到稳定对应章节'
        return '；'.join(
            f'{item.title}{f"（位置 {item.position}）" if item.position is not None else ""}'
            for item in matched_sections[:3]
        )

    def _render_structure_followups(self, rows) -> list[str]:
        focus_rows = [row for row in rows if row.status in {'missing', 'partial', 'blocked_by_visibility'}]
        if not focus_rows:
            return ['- 结构完整性矩阵各项均已闭合，当前未形成额外补齐意见。']
        lines: list[str] = []
        for row in focus_rows:
            prefix = self._STRUCTURE_STATUS_LABELS.get(row.status, row.status)
            lines.append(f'- {row.requirementLabel}：{prefix}。{row.analysis}')
        if any(row.status == 'blocked_by_visibility' for row in focus_rows):
            lines.append('- 对受可视域限制的项目，应结合原件目录、附图附表和正式报审文本进行人工复核，不直接按缺失处理。')
        return lines

    def _duplicate_issue_detail(self, issue) -> str:
        details = []
        if issue.manualReviewNeeded and issue.manualReviewReason:
            details.append(self._manual_review_reason_text(issue.manualReviewReason))
        details.extend(self._blocking_reason_text(reason) for reason in issue.blockingReasons or [])
        return '；'.join(details) if details else '重复标题会降低章节映射与复核稳定性。'

    def _render_layer_basis(self, issues) -> list[str]:
        seen: set[str] = set()
        lines: list[str] = []
        for issue in issues:
            for source in self._issue_policy_source_lines(issue):
                if source in seen:
                    continue
                seen.add(source)
                lines.append(f'- {source}')
        return lines[:6]

    def _issue_policy_source_lines(self, issue) -> list[str]:
        sources: list[str] = []
        seen: set[str] = set()
        for span in issue.policyEvidence:
            source_label, _ = self._normalize_policy_source(span.sourceId)
            clause_title = span.clauseTitle or '相关条文要求'
            text = f'{source_label}：{clause_title}'
            if text in seen:
                continue
            seen.add(text)
            sources.append(text)
        return sources

    def _render_issue(self, index: int, issue) -> list[str]:
        policy_lines = self._render_policy_requirements(issue)
        risk_lines = self._render_issue_risk_lines(issue)
        recommendation_lines = issue.recommendation or ['建议结合原文及附件补充完善后再次提交审查。']
        lines = [
            f'### {index}. {issue.title}',
            f'- 问题描述：{issue.summary}',
            *policy_lines,
            *risk_lines,
            '- 审查建议：',
            *[f'  - {item}' for item in recommendation_lines],
            '',
        ]
        return lines

    def _render_policy_requirements(self, issue) -> list[str]:
        lines = ['- 条文规定：']
        seen: set[str] = set()
        items: list[str] = []
        for span in issue.policyEvidence:
            source_label, _ = self._normalize_policy_source(span.sourceId)
            excerpt = span.excerpt.strip().replace('\n', ' ')
            clause_title = span.clauseTitle or '相关条文要求'
            content = f'{source_label}中“{clause_title}”要求：{excerpt}' if excerpt else f'{source_label}中“{clause_title}”提出相关要求。'
            if content in seen:
                continue
            seen.add(content)
            items.append(content)
        if not items:
            items.append('当前结果未单独提取到明确条文摘录，建议结合本次命中的规范、法规和原文附件继续复核。')
        lines.extend(f'  - {item}' for item in items)
        return lines

    def _render_issue_risk_lines(self, issue) -> list[str]:
        details = [
            f'问题性质为“{self._issue_kind_label(issue.issueKind)}”，严重程度为“{self._severity_label(issue.severity)}”，当前状态为“{self._applicability_label(issue.applicabilityState)}”。'
        ]
        if issue.manualReviewNeeded:
            details.append(self._manual_review_reason_text(issue.manualReviewReason))
        if issue.missingFactKeys:
            details.append(f'仍缺少以下关键事实：{"、".join(issue.missingFactKeys)}。')
        if issue.blockingReasons:
            details.extend(self._blocking_reason_text(reason) for reason in issue.blockingReasons)
        if issue.evidenceMissing and not issue.missingFactKeys and not issue.blockingReasons:
            details.append('当前证据链尚未完全闭合，建议结合原始资料继续核实。')
        return ['- 当前风险/限制：', *[f'  - {item}' for item in details]]

    def _render_hazard_summary(self, hazard_values: dict) -> list[str]:
        lines: list[str] = []
        active_categories = hazard_values.get('highRiskCategories') or []
        if active_categories:
            lines.append(f'- 已识别的高风险作业类型：{"、".join(str(item) for item in active_categories)}。')
        for key, label in self._HAZARD_VALUE_LABELS.items():
            value = hazard_values.get(key)
            if value in (None, '', [], {}):
                continue
            if isinstance(value, bool):
                lines.append(f'- {label}：{"是" if value else "否"}。')
            else:
                lines.append(f'- {label}：{value}。')
        section_presence = hazard_values.get('sectionPresence') or {}
        if isinstance(section_presence, dict):
            missing_sections = [name for name, present in section_presence.items() if present is False]
            if missing_sections:
                lines.append(f'- 结构提示：以下关键章节未明确识别到：{"、".join(missing_sections[:8])}。')
        if not lines:
            return ['- 当前未提取到明确的危大工程识别参数。']
        return lines

    def _render_attachment_matrix_summary(self, attachment_items, visibility) -> list[str]:
        counts = visibility.counts or {}
        lines = [
            f'- 已识别附件共 {visibility.attachmentCount} 项，其中完整进入可视域 {counts.get("parsed", 0)} 项。'
        ]
        if counts.get('attachment_unparsed', 0):
            lines.append(f'- 存在 {counts["attachment_unparsed"]} 项附件仅识别到标题，尚需补核正文或原件。')
        if counts.get('referenced_only', 0):
            lines.append(f'- 存在 {counts["referenced_only"]} 项附件仅在正文中被提及。')
        if counts.get('unknown', 0):
            lines.append(f'- 存在 {counts["unknown"]} 项附件状态暂不能确认。')
        if counts.get('missing', 0):
            lines.append(f'- 存在 {counts["missing"]} 项附件具有明确缺失证据。')
        example_items = [item for item in attachment_items if item.visibility.value != 'parsed'][:3]
        for item in example_items:
            lines.append(f'- 重点提示：{item.attachmentNumber}《{item.title}》当前状态为“{item.visibility.value}”。')
        return lines

    def _render_section_structure_summary(self, section_items, visibility) -> list[str]:
        duplicate_count = sum(1 for item in section_items if item.duplicate)
        lines = [f'- 已识别章节 {len(section_items)} 个。']
        if duplicate_count:
            lines.append(f'- 其中存在重复标题章节 {duplicate_count} 个，可能影响正文与附件的精确定位。')
        if visibility.duplicateSectionTitles:
            lines.append(f'- 重点重复标题包括：{"、".join(visibility.duplicateSectionTitles[:5])}。')
        if duplicate_count == 0:
            lines.append('- 当前未检测到明显的重复章节结构问题。')
        return lines

    def _render_structure_completeness_summary(self, rows) -> list[str]:
        if not rows:
            return ['- 当前未生成施组结构完整性矩阵。']
        counts = Counter(row.status for row in rows)
        lines = [f'- 共核对 {len(rows)} 项结构要求，其中符合 {counts.get("matched", 0)} 项。']
        if counts.get('partial', 0):
            lines.append(f'- 仅部分符合 {counts["partial"]} 项。')
        if counts.get('missing', 0):
            lines.append(f'- 明确缺失 {counts["missing"]} 项。')
        if counts.get('blocked_by_visibility', 0):
            lines.append(f'- 受可视域限制 {counts["blocked_by_visibility"]} 项。')
        focus_rows = [row.requirementLabel for row in rows if row.status in {'partial', 'missing', 'blocked_by_visibility'}]
        if focus_rows:
            lines.append(f'- 重点关注项：{"、".join(focus_rows[:6])}。')
        return lines

    def _render_rule_hit_summary(self, rule_hits) -> list[str]:
        if not rule_hits:
            return ['- 本次未形成可单列展示的规则命中结果。']
        status_counts = Counter(item.status for item in rule_hits)
        layer_counts = Counter(item.layerHint for item in rule_hits)
        lines = [
            f'- 规则命中统计：命中 {status_counts.get("hit", 0)} 项，需人工复核 {status_counts.get("manual_review_needed", 0)} 项，不适用 {status_counts.get("not_applicable", 0)} 项，通过 {status_counts.get("pass", 0)} 项。',
            f'- 分层分布：L1 {layer_counts.get("L1", 0)} 项，L2 {layer_counts.get("L2", 0)} 项，L3 {layer_counts.get("L3", 0)} 项。',
        ]
        blocked = sum(1 for item in rule_hits if item.applicabilityState in {'blocked_by_visibility', 'blocked_by_missing_fact'})
        if blocked:
            lines.append(f'- 其中有 {blocked} 项规则受可视域或关键事实不足影响，需结合原文和附件进一步复核。')
        return lines

    def _render_conflict_summary(self, conflict_values: dict) -> list[str]:
        lines: list[str] = []
        schedule_vs_resources = conflict_values.get('scheduleVsResources') or {}
        if schedule_vs_resources:
            if schedule_vs_resources.get('issueTriggered'):
                lines.append('- 工期窗口与资源配置之间已触发组织压力提示，需重点核查停机窗口、劳动力投入和高风险工序是否匹配。')
            else:
                lines.append('- 当前未触发明显的工期与资源组织压力提示。')
        hazard_vs_measures = conflict_values.get('hazardVsMeasures') or {}
        if hazard_vs_measures:
            if hazard_vs_measures.get('issueTriggered'):
                lines.append('- 危险源识别与控制措施之间已出现闭环不足提示，需重点补核监测监控和风险控制衔接。')
            else:
                lines.append('- 当前未触发明显的危险源与控制措施闭环冲突提示。')
        if not lines:
            lines.append('- 当前未形成可单列展示的冲突联动提示。')
        return lines
