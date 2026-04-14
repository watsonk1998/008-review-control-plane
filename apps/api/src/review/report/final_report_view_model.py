from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.review.contracts import FinalReportPacket


_MODULE_TITLES = {
    'structure_completeness': '章节完整性',
    'parameter_consistency': '参数一致性',
    'legality_compliance': '合法合规性',
    'execution_continuity': '工序连贯性',
    'evidence_validation': '证据验证',
}

_MODULE_ORDER = [
    'structure_completeness',
    'parameter_consistency',
    'legality_compliance',
    'execution_continuity',
    'evidence_validation',
]

_STATUS_LABELS = {
    'matched': '符合',
    'partial': '部分符合',
    'missing': '缺失',
    'blocked_by_visibility': '待复核',
}

_SEVERITY_LABELS = {
    'high': '高风险',
    'medium': '中等风险',
    'low': '低风险',
    'info': '提示',
}

_DOCUMENT_TYPE_LABELS = {
    'construction_org': '施工组织设计',
    'construction_scheme': '施工方案',
    'hazardous_special_scheme': '危大专项施工方案',
    'distribution_network_special_scheme': '配网工程专项施工方案',
    'supervision_plan': '监理规划',
    'review_support_material': '审查支持材料',
}


class FinalReportIssueView(BaseModel):
    id: str
    title: str
    severity: str
    severityLabel: str
    location: str
    description: str
    recommendation: str
    basis: list[str] = Field(default_factory=list)


class FinalReportSectionView(BaseModel):
    key: str
    title: str
    issues: list[FinalReportIssueView] = Field(default_factory=list)
    emptyText: str = '本模块未发现需要单独提示的问题。'


class ChapterCompletenessRowView(BaseModel):
    index: int
    requirement: str
    basis: str
    matchedSection: str
    status: str
    statusLabel: str
    note: str


class ChapterCompletenessNoteView(BaseModel):
    title: str
    description: str


class ChapterCompletenessView(BaseModel):
    title: str = '章节完整性'
    tableRows: list[ChapterCompletenessRowView] = Field(default_factory=list)
    notes: list[ChapterCompletenessNoteView] = Field(default_factory=list)


class FinalReportViewModel(BaseModel):
    title: str
    documentTypeLabel: str
    executiveSummary: str
    basisFiles: list[str] = Field(default_factory=list)
    chapterCompleteness: ChapterCompletenessView = Field(default_factory=ChapterCompletenessView)
    sections: list[FinalReportSectionView] = Field(default_factory=list)


class FinalReportRenderer:
    def build_view_model(
        self,
        *,
        final_packet: FinalReportPacket | dict[str, Any],
        support_result: dict[str, Any] | None = None,
    ) -> FinalReportViewModel:
        packet = final_packet.model_dump(mode='json') if isinstance(final_packet, FinalReportPacket) else dict(final_packet or {})
        support = dict(support_result or {})
        summary = dict(support.get('summary') or {})
        document_type = str(summary.get('documentType') or packet.get('metadata', {}).get('document_type') or '')
        document_label = _DOCUMENT_TYPE_LABELS.get(document_type, document_type or '审查文档')
        support_issues = [item for item in support.get('issues', []) if isinstance(item, dict)]
        structure_rows = [item for item in ((support.get('matrices') or {}).get('structureCompleteness') or []) if isinstance(item, dict)]
        basis_files = self._collect_basis_files(packet, support)
        findings = [item for item in packet.get('all_findings', []) if isinstance(item, dict)]
        grouped = {module: [] for module in _MODULE_ORDER}
        for finding in self._dedupe_findings(findings):
            grouped[self._resolve_module(finding)].append(finding)

        sections: list[FinalReportSectionView] = []
        for module in _MODULE_ORDER:
            issues = [self._build_issue_view(finding, support_issues, structure_rows) for finding in grouped[module]]
            sections.append(
                FinalReportSectionView(
                    key=module,
                    title=_MODULE_TITLES[module],
                    issues=issues,
                )
            )

        return FinalReportViewModel(
            title=f'{document_label}形式审查报告',
            documentTypeLabel=document_label,
            executiveSummary=str(packet.get('executive_summary') or support.get('finalReportMarkdown') or '').strip(),
            basisFiles=basis_files,
            chapterCompleteness=self._build_chapter_completeness(structure_rows),
            sections=sections,
        )

    def render_html(self, view_model: FinalReportViewModel) -> str:
        parts = [
            '<article class="structured-report structured-report--final">',
            f'<h1 class="structured-report__title">{html.escape(view_model.title)}</h1>',
            '<section class="structured-report__section">',
            '<h2 class="structured-report__section-title">第一部分：审查结论与审查依据</h2>',
            '<div class="structured-report__subsection">',
            '<h3 class="structured-report__subsection-title">1. 总体审查结论</h3>',
            f'<p class="structured-report__summary">{html.escape(view_model.executiveSummary or "本次未生成可展示的综合结论。")}</p>',
            '</div>',
            '<div class="structured-report__subsection">',
            '<h3 class="structured-report__subsection-title">2. 审查依据文件</h3>',
            '<ul class="structured-report__basis-list">',
        ]
        if view_model.basisFiles:
            parts.extend(f'<li>{html.escape(item)}</li>' for item in view_model.basisFiles)
        else:
            parts.append('<li>本次未提取到可直接展示的正式规范或法规依据。</li>')
        parts.extend(['</ul>', '</div>', '</section>'])

        section_number = 2
        for section in view_model.sections:
            if section.key == 'structure_completeness':
                parts.extend(self._render_chapter_completeness_section(section_number, section, view_model.chapterCompleteness))
            else:
                parts.extend(self._render_issue_section(section_number, section))
            section_number += 1
        parts.append('</article>')
        return ''.join(parts)

    def render_print_css(self) -> str:
        return _FINAL_REPORT_CSS

    def _render_chapter_completeness_section(
        self,
        section_number: int,
        section: FinalReportSectionView,
        chapter: ChapterCompletenessView,
    ) -> list[str]:
        parts = [
            '<section class="structured-report__section">',
            f'<h2 class="structured-report__section-title">第{_number_to_cn(section_number)}部分：{html.escape(section.title)}</h2>',
        ]
        if chapter.tableRows:
            parts.extend([
                '<div class="structured-report__subsection">',
                '<h3 class="structured-report__subsection-title">章节完整性矩阵</h3>',
                '<div class="structured-report__table-wrap">',
                '<table class="structured-report__matrix-table">',
                '<thead><tr><th>序号</th><th>规范要求</th><th>规范依据</th><th>文档对应章节</th><th>结构判定</th><th>相关审查意见</th></tr></thead>',
                '<tbody>',
            ])
            for row in chapter.tableRows:
                parts.append(
                    '<tr>'
                    f'<td>{row.index}</td>'
                    f'<td>{html.escape(row.requirement)}</td>'
                    f'<td>{html.escape(row.basis)}</td>'
                    f'<td>{html.escape(row.matchedSection)}</td>'
                    f'<td>{html.escape(row.statusLabel)}</td>'
                    f'<td>{html.escape(row.note)}</td>'
                    '</tr>'
                )
            parts.extend(['</tbody>', '</table>', '</div>', '</div>'])
        if chapter.notes:
            parts.extend([
                '<div class="structured-report__subsection">',
                '<h3 class="structured-report__subsection-title">补充说明</h3>',
                '<div class="structured-report__note-list">',
            ])
            for note in chapter.notes:
                parts.extend([
                    '<section class="structured-report__note-card">',
                    f'<h4 class="structured-report__note-title">{html.escape(note.title)}</h4>',
                    f'<p class="structured-report__note-text">{html.escape(note.description)}</p>',
                    '</section>',
                ])
            parts.extend(['</div>', '</div>'])
        if section.issues:
            parts.extend([
                '<div class="structured-report__subsection">',
                '<h3 class="structured-report__subsection-title">相关问题</h3>',
                *self._render_issue_cards(section.issues),
                '</div>',
            ])
        elif not chapter.tableRows and not chapter.notes:
            parts.append(f'<p class="structured-report__muted">{html.escape(section.emptyText)}</p>')
        parts.append('</section>')
        return parts

    def _render_issue_section(self, section_number: int, section: FinalReportSectionView) -> list[str]:
        parts = [
            '<section class="structured-report__section">',
            f'<h2 class="structured-report__section-title">第{_number_to_cn(section_number)}部分：{html.escape(section.title)}</h2>',
        ]
        if section.issues:
            parts.extend(self._render_issue_cards(section.issues))
        else:
            parts.append(f'<p class="structured-report__muted">{html.escape(section.emptyText)}</p>')
        parts.append('</section>')
        return parts

    def _render_issue_cards(self, issues: list[FinalReportIssueView]) -> list[str]:
        parts: list[str] = []
        for index, issue in enumerate(issues, start=1):
            severity_class = f'structured-report__issue-card--{issue.severity}'
            parts.extend([
                f'<article class="structured-report__issue-card {severity_class}">',
                f'<h3 class="structured-report__issue-card-title">{index}. 【{html.escape(issue.severityLabel)}】{html.escape(issue.title)}</h3>',
                '<section class="structured-report__issue-card-section">',
                '<div class="structured-report__issue-card-section-title">问题定位</div>',
                f'<p class="structured-report__issue-card-text">{html.escape(issue.location)}</p>',
                '</section>',
                '<section class="structured-report__issue-card-section">',
                '<div class="structured-report__issue-card-section-title">问题描述</div>',
                f'<p class="structured-report__issue-card-text">{html.escape(issue.description)}</p>',
                '</section>',
            ])
            if issue.recommendation:
                parts.extend([
                    '<section class="structured-report__issue-card-section">',
                    '<div class="structured-report__issue-card-section-title">整改建议</div>',
                    f'<p class="structured-report__issue-card-text">{html.escape(issue.recommendation)}</p>',
                    '</section>',
                ])
            if issue.basis:
                parts.extend([
                    '<section class="structured-report__issue-card-section">',
                    '<div class="structured-report__issue-card-section-title">审查依据</div>',
                    '<ul class="structured-report__issue-card-law-list">',
                ])
                parts.extend(f'<li class="structured-report__issue-card-law-item">{html.escape(item)}</li>' for item in issue.basis)
                parts.extend(['</ul>', '</section>'])
            parts.append('</article>')
        return parts

    def _build_chapter_completeness(self, rows: list[dict[str, Any]]) -> ChapterCompletenessView:
        table_rows: list[ChapterCompletenessRowView] = []
        notes: list[ChapterCompletenessNoteView] = []
        for index, row in enumerate(rows, start=1):
            matched_section = self._matched_section_text(row.get('matchedSections') or [])
            status = str(row.get('status') or 'missing')
            note = self._chapter_row_note(row)
            table_rows.append(
                ChapterCompletenessRowView(
                    index=index,
                    requirement=self._clean_text(row.get('requirementLabel')) or '—',
                    basis=self._clean_text(row.get('basisClause')) or self._clean_text(row.get('basisRequirement')) or '—',
                    matchedSection=matched_section,
                    status=status,
                    statusLabel=_STATUS_LABELS.get(status, status),
                    note=note,
                )
            )
            if status in {'partial', 'missing', 'blocked_by_visibility'}:
                notes.append(
                    ChapterCompletenessNoteView(
                        title=self._clean_text(row.get('requirementLabel')) or f'结构项 {index}',
                        description=self._chapter_note_description(row),
                    )
                )
        return ChapterCompletenessView(tableRows=table_rows, notes=notes)

    def _build_issue_view(
        self,
        finding: dict[str, Any],
        support_issues: list[dict[str, Any]],
        structure_rows: list[dict[str, Any]],
    ) -> FinalReportIssueView:
        support_issue = self._match_support_issue(finding, support_issues)
        basis = self._collect_basis_lines(finding, support_issue)
        recommendation = self._recommendation_text(finding, support_issue)
        return FinalReportIssueView(
            id=str(finding.get('id') or ''),
            title=self._clean_text(finding.get('title')) or '未命名问题',
            severity=str(finding.get('severity') or 'info'),
            severityLabel=_SEVERITY_LABELS.get(str(finding.get('severity') or 'info'), str(finding.get('severity') or '提示')),
            location=self._resolve_location(finding, support_issue, structure_rows),
            description=self._description_text(finding, support_issue),
            recommendation=recommendation,
            basis=basis,
        )

    def _description_text(self, finding: dict[str, Any], support_issue: dict[str, Any] | None) -> str:
        for value in [finding.get('summary'), (support_issue or {}).get('summary')]:
            cleaned = self._clean_text(value)
            if cleaned:
                return cleaned
        return '当前未提取到更详细的问题描述，请结合原文复核。'

    def _recommendation_text(self, finding: dict[str, Any], support_issue: dict[str, Any] | None) -> str:
        suggestion = self._clean_text(finding.get('suggestion'))
        if suggestion:
            return suggestion
        recommendations = (support_issue or {}).get('recommendation') or []
        if isinstance(recommendations, list):
            joined = '；'.join(self._clean_text(item) for item in recommendations if self._clean_text(item))
            if joined:
                return joined
        return ''

    def _resolve_location(
        self,
        finding: dict[str, Any],
        support_issue: dict[str, Any] | None,
        structure_rows: list[dict[str, Any]],
    ) -> str:
        candidates: list[str] = []
        raw_data = finding.get('raw_data') if isinstance(finding.get('raw_data'), dict) else {}
        for source in [raw_data, support_issue or {}, finding]:
            for evidence in source.get('docEvidence') or []:
                if isinstance(evidence, dict):
                    excerpt = self._clean_text(evidence.get('excerpt'))
                    if excerpt:
                        candidates.append(excerpt)
        if support_issue is not None:
            matched_sections = support_issue.get('matchedSections') or []
            for item in matched_sections:
                if isinstance(item, dict):
                    title = self._clean_text(item.get('title'))
                    if title:
                        candidates.append(title)
        title = self._clean_text(finding.get('title'))
        if title:
            for row in structure_rows:
                analysis = self._clean_text(row.get('analysis'))
                excerpt = self._clean_text(row.get('reportExcerpt'))
                requirement = self._clean_text(row.get('requirementLabel'))
                if any(title in value for value in [analysis, excerpt, requirement] if value):
                    section_text = self._matched_section_text(row.get('matchedSections') or [])
                    if section_text and section_text != '未识别到稳定对应章节':
                        candidates.append(section_text)
        for candidate in candidates:
            precise = self._format_location_candidate(candidate)
            if precise:
                return precise
        return '未定位到稳定章节，请结合原文复核。'

    def _format_location_candidate(self, text: str) -> str:
        value = self._clean_text(text)
        if not value:
            return ''
        locator_match = re.search(r'(第[一二三四五六七八九十百零〇两]+章(?:第[一二三四五六七八九十百零〇两]+节)?|(?:\d+\.)+\d+节?|\d+\.\d+)', value)
        if locator_match:
            locator = locator_match.group(1)
            trimmed = value[:60].strip('；;，,。. ')
            if locator in trimmed:
                return trimmed
            return f'{locator} {trimmed}'.strip()
        if len(value) <= 60:
            return value
        return f'{value[:56].rstrip()}…'

    def _collect_basis_lines(self, finding: dict[str, Any], support_issue: dict[str, Any] | None) -> list[str]:
        lines: list[str] = []
        seen: set[str] = set()
        for source in [finding.get('raw_data') if isinstance(finding.get('raw_data'), dict) else {}, support_issue or {}, finding]:
            for span in source.get('policyEvidence') or []:
                if not isinstance(span, dict):
                    continue
                source_id = self._clean_text(span.get('sourceId'))
                clause = self._clean_text(span.get('clauseTitle'))
                if not source_id:
                    continue
                citation = self._format_basis_citation(source_id, clause)
                if citation not in seen:
                    seen.add(citation)
                    lines.append(citation)
        return lines[:6]

    def _build_support_index(self, support_issues: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
        by_id: dict[str, dict[str, Any]] = {}
        by_title: dict[str, dict[str, Any]] = {}
        for issue in support_issues:
            issue_id = self._clean_text(issue.get('id'))
            title = self._clean_text(issue.get('title')).lower()
            if issue_id and issue_id not in by_id:
                by_id[issue_id] = issue
            if title and title not in by_title:
                by_title[title] = issue
        return by_id, by_title

    def _match_support_issue(self, finding: dict[str, Any], support_issues: list[dict[str, Any]]) -> dict[str, Any] | None:
        by_id, by_title = self._build_support_index(support_issues)
        finding_id = self._clean_text(finding.get('id'))
        if finding_id and finding_id in by_id:
            return by_id[finding_id]
        title = self._clean_text(finding.get('title')).lower()
        return by_title.get(title)

    def _collect_basis_files(self, packet: dict[str, Any], support: dict[str, Any]) -> list[str]:
        basis: list[str] = []
        seen: set[str] = set()
        for finding in packet.get('all_findings', []):
            if not isinstance(finding, dict):
                continue
            for source in self._collect_basis_lines(finding, None):
                source_label = source.removeprefix('审查依据：引用自')
                if source_label not in seen:
                    seen.add(source_label)
                    basis.append(source_label)
        return basis[:8]

    def _resolve_module(self, finding: dict[str, Any]) -> str:
        raw_data = finding.get('raw_data') if isinstance(finding.get('raw_data'), dict) else {}
        module_name = self._clean_text(raw_data.get('module_name'))
        if module_name in _MODULE_TITLES:
            return module_name
        category = self._clean_text(finding.get('category'))
        category_map = {
            'chapter_completeness': 'structure_completeness',
            'structure': 'structure_completeness',
            'visibility': 'structure_completeness',
            'parameter_consistency': 'parameter_consistency',
            'compliance': 'legality_compliance',
            'safety': 'legality_compliance',
            'rule_hits': 'legality_compliance',
            'process_coherence': 'execution_continuity',
            'evidence_verification': 'evidence_validation',
            'facts': 'evidence_validation',
        }
        return category_map.get(category, 'legality_compliance')

    def _dedupe_findings(self, findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen_keys: set[tuple[str, str]] = set()
        deduped: list[dict[str, Any]] = []
        for finding in findings:
            item_id = self._clean_text(finding.get('id'))
            title = self._clean_text(finding.get('title')).lower()
            key = (item_id, title)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            deduped.append(finding)
        return deduped

    def _matched_section_text(self, matched_sections: list[dict[str, Any]]) -> str:
        titles = []
        for item in matched_sections[:3]:
            if isinstance(item, dict):
                title = self._clean_text(item.get('title'))
                if title:
                    titles.append(title)
        if not titles:
            return '未识别到稳定对应章节'
        text = '；'.join(titles)
        return text if len(text) <= 80 else f'{text[:76].rstrip()}…'

    def _chapter_row_note(self, row: dict[str, Any]) -> str:
        status = str(row.get('status') or '')
        if status == 'matched':
            return '—'
        if status == 'partial':
            return f'建议补齐“{self._clean_text(row.get("requirementLabel"))}”并形成稳定章节闭合。'
        if status == 'missing':
            return f'建议补齐“{self._clean_text(row.get("requirementLabel"))}”专章或稳定标题。'
        if status == 'blocked_by_visibility':
            return '当前受解析可视域限制，建议结合原件人工复核。'
        return self._clean_text(row.get('reportExcerpt')) or '—'

    def _chapter_note_description(self, row: dict[str, Any]) -> str:
        parts = []
        matched = self._matched_section_text(row.get('matchedSections') or [])
        if matched:
            parts.append(f'对应章节：{matched}')
        analysis = self._clean_text(row.get('analysis'))
        if analysis:
            parts.append(analysis)
        recommendation = self._chapter_row_note(row)
        if recommendation and recommendation != '—':
            parts.append(f'处理建议：{recommendation}')
        return '；'.join(parts) if parts else '请结合原文进一步核对该结构项。'

    def _format_basis_citation(self, source_id: str, clause: str) -> str:
        label = source_id
        if '《' in source_id:
            label = source_id[source_id.index('《'):]
        label = label.replace('construction-', '')
        if clause:
            return f'审查依据：引用自{label} {clause}'
        return f'审查依据：引用自{label}'

    def _clean_text(self, value: Any) -> str:
        if value is None:
            return ''
        text = str(value).replace('\n', ' ').replace('\r', ' ')
        text = re.sub(r'\s+', ' ', text).strip()
        if text.lower() == 'demo':
            return '建议结合原文和附件补充完善后复核。'
        return text


def _number_to_cn(value: int) -> str:
    mapping = {1: '一', 2: '二', 3: '三', 4: '四', 5: '五', 6: '六', 7: '七', 8: '八', 9: '九', 10: '十'}
    return mapping.get(value, str(value))


_FINAL_REPORT_CSS = """
html, body {
  background: #f8f5ef !important;
  margin: 0;
  padding: 0;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
  color: #1f2937;
  font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
}

.structured-report {
  max-width: 1200px;
  margin: 0 auto;
  padding: 28px;
  background: #f6edd7;
}

.structured-report * {
  box-sizing: border-box;
  min-width: 0;
  white-space: normal;
  word-break: break-word;
  overflow-wrap: anywhere;
}

.structured-report__title {
  margin: 0 0 24px;
  text-align: center;
  font-size: 30px;
  line-height: 1.3;
  color: #172033;
}

.structured-report__section {
  margin-top: 24px;
  padding: 24px;
  border-radius: 24px;
  background: #f3e8cc;
  border: 1px solid #eadcc0;
  break-inside: avoid;
}

.structured-report__section-title {
  margin: 0 0 16px;
  padding: 16px 20px;
  background: #d9d5c6;
  border-left: 6px solid #2563eb;
  color: #172033;
  font-size: 22px;
}

.structured-report__subsection { margin-top: 18px; }
.structured-report__subsection-title {
  margin: 0 0 12px;
  font-size: 18px;
  color: #172033;
}

.structured-report__summary,
.structured-report__muted,
.structured-report__note-text,
.structured-report__issue-card-text,
.structured-report__issue-card-law-item,
.structured-report__basis-list li {
  font-size: 15px;
  line-height: 1.9;
}

.structured-report__basis-list,
.structured-report__issue-card-law-list {
  margin: 0;
  padding-left: 20px;
}

.structured-report__table-wrap {
  overflow-x: auto;
  border-radius: 18px;
  border: 1px solid #cfc8b4;
  background: #efe6c8;
}

.structured-report__matrix-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.structured-report__matrix-table th,
.structured-report__matrix-table td {
  padding: 16px;
  border-bottom: 1px solid #cfc8b4;
  text-align: left;
  vertical-align: top;
  font-size: 15px;
  line-height: 1.7;
}

.structured-report__matrix-table th {
  background: #d9d5c6;
  color: #172033;
  font-weight: 700;
}

.structured-report__matrix-table tbody tr:last-child td { border-bottom: none; }

.structured-report__note-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.structured-report__note-card {
  padding: 18px 20px;
  border-radius: 18px;
  border: 1px solid #ebcf99;
  background: rgba(255,255,255,0.25);
}

.structured-report__note-title {
  margin: 0 0 8px;
  font-size: 16px;
  color: #172033;
}

.structured-report__issue-card {
  margin-top: 18px;
  padding: 24px 28px;
  border-radius: 18px;
  border: 1px solid #e5d8be;
  background: rgba(255,255,255,0.35);
  break-inside: avoid;
  page-break-inside: avoid;
}

.structured-report__issue-card--high {
  border-left: 6px solid #dc2626;
  background: rgba(254, 242, 242, 0.48);
}

.structured-report__issue-card--medium {
  border-left: 6px solid #d97706;
  background: rgba(255, 247, 237, 0.55);
}

.structured-report__issue-card--low,
.structured-report__issue-card--info {
  border-left: 6px solid #2563eb;
  background: rgba(239, 246, 255, 0.42);
}

.structured-report__issue-card-title {
  margin: 0 0 14px;
  font-size: 18px;
  color: #172033;
}

.structured-report__issue-card-section { margin-top: 14px; }
.structured-report__issue-card-section-title {
  margin-bottom: 8px;
  font-size: 15px;
  font-weight: 700;
  color: #9f1239;
}

@page {
  size: A4 landscape;
  margin: 14mm;
}

@media print {
  html, body { background: #f8f5ef !important; }
  .structured-report { max-width: none; padding: 0; }
  .structured-report__section-title,
  .structured-report__subsection-title,
  .structured-report__issue-card-title {
    break-after: avoid;
    page-break-after: avoid;
  }
  .structured-report__matrix-table thead { display: table-header-group; }
}
"""
