from __future__ import annotations

import html
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from src.review.contracts import FinalReportPacket
from src.review.evidence.packs import get_evidence_pack_registry


# ---------------------------------------------------------------------------
# Module routing configuration (loaded from config/module_routing.yaml)
# ---------------------------------------------------------------------------
_MODULE_ROUTING_CONFIG: dict[str, Any] | None = None
_CONFIG_PATH = Path(__file__).resolve().parents[5] / 'config' / 'module_routing.yaml'


def _load_module_routing_config() -> dict[str, Any]:
    """Load and cache module routing keyword configuration."""
    global _MODULE_ROUTING_CONFIG
    if _MODULE_ROUTING_CONFIG is not None:
        return _MODULE_ROUTING_CONFIG
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH, encoding='utf-8') as f:
            _MODULE_ROUTING_CONFIG = yaml.safe_load(f) or {}
    else:
        _MODULE_ROUTING_CONFIG = {}
    return _MODULE_ROUTING_CONFIG


def _get_module_keywords(document_type: str = '') -> dict[str, list[str]]:
    """Return merged keyword lists per module: generic + domain-specific."""
    cfg = _load_module_routing_config()
    generic = dict(cfg.get('generic', {}))
    domain = cfg.get('document_types', {}).get(document_type, {})
    merged: dict[str, list[str]] = {}
    for module in _MODULE_TITLES:
        base = list(generic.get(module, []))
        extra = list(domain.get(module, []))
        merged[module] = base + extra
    return merged


_MODULE_TITLES = {
    'structure_completeness': '章节完整性',
    'parameter_consistency': '参数一致性',
    'legality_compliance': '合法合规性',
    'execution_continuity': '工序连贯性',
    'evidence_validation': '证据验证',
}

_MODULE_META: dict[str, dict[str, str]] = {
    'structure_completeness': {
        'description': '检查方案是否覆盖规范要求的必备章节与大纲结构',
        'theme': 'blue',
    },
    'parameter_consistency': {
        'description': '核验方案中的数值、名称、参数在各处引用是否前后统一',
        'theme': 'purple',
    },
    'legality_compliance': {
        'description': '审查方案是否符合现行法规、强制性条文和安全规程要求',
        'theme': 'red',
    },
    'execution_continuity': {
        'description': '检查施工工序、停送电步骤、操作流程是否形成完整闭环',
        'theme': 'amber',
    },
    'evidence_validation': {
        'description': '核验编制依据的现行有效性、计算过程的正确性和证据材料的充分性',
        'theme': 'green',
    },
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

_VALIDITY_STATUS_LABELS = {
    'current': '现行有效',
    'superseded': '疑似废止/替代',
    'unknown': '待人工核验',
}

class ExecutiveSummaryMetricView(BaseModel):
    label: str
    value: str
    tone: str = 'neutral'


class ExecutiveSummaryView(BaseModel):
    verdict: str = ''
    narrative: str = ''
    metrics: list[ExecutiveSummaryMetricView] = Field(default_factory=list)


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


class ChapterCompletenessView(BaseModel):
    title: str = '章节完整性'
    tableRows: list[ChapterCompletenessRowView] = Field(default_factory=list)


class NormativeValidityCheckView(BaseModel):
    title: str
    status: str
    statusLabel: str
    resolvedTitle: str = ''
    note: str = ''


class NormativeValidityView(BaseModel):
    title: str = '编制依据现行有效性核验'
    summary: str = ''
    checks: list[NormativeValidityCheckView] = Field(default_factory=list)


class FinalReportViewModel(BaseModel):
    title: str
    documentTypeLabel: str
    executiveSummary: str
    executiveSummaryView: ExecutiveSummaryView = Field(default_factory=ExecutiveSummaryView)
    selectedModules: list[str] = Field(default_factory=list)
    basisFiles: list[str] = Field(default_factory=list)
    chapterCompleteness: ChapterCompletenessView = Field(default_factory=ChapterCompletenessView)
    normativeValidity: NormativeValidityView = Field(default_factory=NormativeValidityView)
    sections: list[FinalReportSectionView] = Field(default_factory=list)


class FinalReportRenderer:
    _document_type: str = ''
    def build_view_model(
        self,
        *,
        final_packet: FinalReportPacket | dict[str, Any],
        support_result: dict[str, Any] | None = None,
        selected_modules: list[str] | None = None,
    ) -> FinalReportViewModel:
        packet = final_packet.model_dump(mode='json') if isinstance(final_packet, FinalReportPacket) else dict(final_packet or {})
        support = dict(support_result or {})
        summary = dict(support.get('summary') or {})
        document_type = str(summary.get('documentType') or packet.get('metadata', {}).get('document_type') or '')
        self._document_type = document_type
        document_label = _DOCUMENT_TYPE_LABELS.get(document_type, document_type or '审查文档')
        effective_modules = self._resolve_selected_modules(packet, selected_modules)
        support_issues = [item for item in support.get('issues', []) if isinstance(item, dict)]
        structure_rows = [item for item in ((support.get('matrices') or {}).get('structureCompleteness') or []) if isinstance(item, dict)]
        section_structure = [item for item in ((support.get('matrices') or {}).get('sectionStructure') or []) if isinstance(item, dict)]
        basis_files = self._collect_basis_files(packet, support_issues, support)
        findings = [item for item in packet.get('all_findings', []) if isinstance(item, dict)]
        grouped = {module: [] for module in self._module_order(effective_modules)}
        deduped_findings = self._dedupe_findings(findings, effective_modules)
        # Use raw findings (pre-dedup) so normative validity table data is
        # never lost due to deduplication or module filtering.
        normative_validity = self._build_normative_validity(findings)
        for finding in deduped_findings:
            module_name = self._resolve_module(finding)
            if module_name not in grouped:
                continue
            grouped[module_name].append(finding)

        sections: list[FinalReportSectionView] = []
        for module in self._module_order(effective_modules):
            issues = [
                self._build_issue_view(finding, support_issues, structure_rows, section_structure)
                for finding in grouped[module]
                if not self._is_normative_validity_summary_finding(finding)
            ]
            issues = self._dedupe_issue_views(issues)
            sections.append(
                FinalReportSectionView(
                    key=module,
                    title=_MODULE_TITLES[module],
                    issues=issues,
                )
            )

        executive_summary = self._clean_text(packet.get('executive_summary') or support.get('finalReportMarkdown') or '')
        executive_summary_view = self._parse_executive_summary(executive_summary)
        executive_summary_view.metrics = self._build_section_metrics(sections)
        return FinalReportViewModel(
            title=f'{document_label}形式审查报告',
            documentTypeLabel=document_label,
            executiveSummary=executive_summary,
            executiveSummaryView=executive_summary_view,
            selectedModules=self._module_order(effective_modules),
            basisFiles=basis_files,
            chapterCompleteness=self._build_chapter_completeness(structure_rows) if 'structure_completeness' in self._module_order(effective_modules) else ChapterCompletenessView(),
            normativeValidity=normative_validity,
            sections=sections,
        )

    def render_html(self, view_model: FinalReportViewModel) -> str:
        parts = [
            '<article class="structured-report structured-report--final">',
            f'<h1 class="structured-report__title">{html.escape(view_model.title)}</h1>',
            '<section class="structured-report__section structured-report__section--overview">',
            '<h2 class="structured-report__section-title">第一部分：审查结论与审查依据</h2>',
            '<div class="structured-report__subsection">',
            '<h3 class="structured-report__subsection-title">1. 总体审查结论</h3>',
        ]
        parts.extend(self._render_executive_summary(view_model.executiveSummaryView, view_model.executiveSummary))
        parts.extend([
            '</div>',
            '<div class="structured-report__subsection">',
            '<h3 class="structured-report__subsection-title">2. 审查依据文件</h3>',
            '<ul class="structured-report__basis-list">',
        ])
        if view_model.basisFiles:
            parts.extend(f'<li>{html.escape(item)}</li>' for item in view_model.basisFiles)
        else:
            parts.append('<li>本次未提取到可直接展示的正式规范或法规依据。</li>')
        parts.extend(['</ul>', '</div>', '</section>'])

        section_number = 2
        for section in view_model.sections:
            if section.key == 'structure_completeness':
                parts.extend(self._render_chapter_completeness_section(section_number, section, view_model.chapterCompleteness))
            elif section.key == 'evidence_validation':
                parts.extend(self._render_evidence_validation_section(section_number, section, view_model.normativeValidity))
            else:
                parts.extend(self._render_issue_section(section_number, section))
            section_number += 1
        parts.append('</article>')
        return ''.join(parts)

    def render_print_css(self) -> str:
        return _FINAL_REPORT_CSS

    def _render_executive_summary(self, summary_view: ExecutiveSummaryView, raw_text: str) -> list[str]:
        parts: list[str] = []
        if summary_view.verdict:
            parts.extend([
                '<div class="structured-report__verdict-row">',
                '<span class="structured-report__verdict-label">总体评级结论</span>',
                f'<span class="structured-report__verdict-badge">{html.escape(summary_view.verdict)}</span>',
                '</div>',
            ])
        if summary_view.metrics:
            parts.extend(['<div class="structured-report__summary-metrics">'])
            for metric in summary_view.metrics:
                parts.extend([
                    f'<div class="structured-report__summary-metric structured-report__summary-metric--{html.escape(metric.tone)}">',
                    f'<div class="structured-report__summary-metric-label">{html.escape(metric.label)}</div>',
                    f'<div class="structured-report__summary-metric-value">{html.escape(metric.value)}</div>',
                    '</div>',
                ])
            parts.append('</div>')
        if summary_view.narrative:
            parts.append(f'<p class="structured-report__summary">{html.escape(summary_view.narrative)}</p>')
        elif not summary_view.verdict:
            # Only show fallback text when there is no verdict badge at all.
            if raw_text:
                parts.append(f'<p class="structured-report__summary">{html.escape(raw_text.replace("**", ""))}</p>')
            else:
                parts.append('<p class="structured-report__summary">本次未生成可展示的综合结论。</p>')
        return parts

    def _render_section_header(self, section_number: int, section: FinalReportSectionView) -> list[str]:
        """Render a themed section header with description and stats badge."""
        meta = _MODULE_META.get(section.key, {})
        theme = meta.get('theme', 'blue')
        desc = meta.get('description', '')
        parts = [
            f'<section class="structured-report__section structured-report__section--{theme}">',
            f'<div class="structured-report__section-header">',
            f'<h2 class="structured-report__section-title structured-report__section-title--{theme}">第{_number_to_cn(section_number)}部分：{html.escape(section.title)}</h2>',
        ]
        # Stats badges
        total = len(section.issues)
        high_count = sum(1 for i in section.issues if i.severity == 'high')
        medium_count = sum(1 for i in section.issues if i.severity == 'medium')
        if total > 0:
            badge_parts = [f'{total}项']
            if high_count:
                badge_parts.append(f'高危{high_count}')
            if medium_count:
                badge_parts.append(f'中危{medium_count}')
            parts.append(f'<span class="structured-report__section-badge structured-report__section-badge--{theme}">{" / ".join(badge_parts)}</span>')
        parts.append('</div>')  # close section-header
        if desc:
            parts.append(f'<p class="structured-report__section-desc">{html.escape(desc)}</p>')
        return parts

    def _render_chapter_completeness_section(
        self,
        section_number: int,
        section: FinalReportSectionView,
        chapter: ChapterCompletenessView,
    ) -> list[str]:
        parts = self._render_section_header(section_number, section)
        if chapter.tableRows:
            parts.extend([
                '<div class="structured-report__subsection">',
                '<div class="structured-report__table-wrap structured-report__table-wrap--landscape">',
                '<table class="structured-report__matrix-table">',
                '<thead><tr><th>序号</th><th>规范要求</th><th>规范依据</th><th>文档对应章节</th><th>结构判定</th></tr></thead>',
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
                    '</tr>'
                )
            parts.extend(['</tbody>', '</table>', '</div>', '</div>'])
        if section.issues:
            parts.extend([
                '<div class="structured-report__subsection">',
                '<h3 class="structured-report__subsection-title">相关问题</h3>',
                *self._render_issue_cards(section.issues),
                '</div>',
            ])
        elif not chapter.tableRows:
            parts.append(f'<p class="structured-report__muted">{html.escape(section.emptyText)}</p>')
        parts.append('</section>')
        return parts

    def _render_evidence_validation_section(
        self,
        section_number: int,
        section: FinalReportSectionView,
        normative_validity: NormativeValidityView,
    ) -> list[str]:
        parts = self._render_section_header(section_number, section)
        if normative_validity.checks:
            parts.extend([
                '<div class="structured-report__subsection">',
                f'<h3 class="structured-report__subsection-title">{html.escape(normative_validity.title)}</h3>',
            ])
            if normative_validity.summary:
                parts.append(f'<p class="structured-report__summary">{html.escape(normative_validity.summary)}</p>')
            parts.extend([
                '<div class="structured-report__table-wrap">',
                '<table class="structured-report__matrix-table structured-report__matrix-table--validity">',
                '<thead><tr><th>序号</th><th>规范名称</th><th>核验状态</th></tr></thead>',
                '<tbody>',
            ])
            for index, check in enumerate(normative_validity.checks, start=1):
                status_cell = html.escape(check.statusLabel)
                if check.note:
                    status_cell += f'<br><span class="structured-report__muted">{html.escape(check.note)}</span>'
                parts.append(
                    '<tr>'
                    f'<td>{index}</td>'
                    f'<td>{html.escape(check.title)}</td>'
                    f'<td>{status_cell}</td>'
                    '</tr>'
                )
            parts.extend(['</tbody>', '</table>', '</div>', '</div>'])
        if section.issues:
            if normative_validity.checks:
                parts.extend([
                    '<div class="structured-report__subsection">',
                    '<h3 class="structured-report__subsection-title">其他证据验证问题</h3>',
                    *self._render_issue_cards(section.issues),
                    '</div>',
                ])
            else:
                parts.extend(self._render_issue_cards(section.issues))
        elif not normative_validity.checks:
            parts.append(f'<p class="structured-report__muted">{html.escape(section.emptyText)}</p>')
        parts.append('</section>')
        return parts

    def _render_issue_section(self, section_number: int, section: FinalReportSectionView) -> list[str]:
        parts = self._render_section_header(section_number, section)
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
            ])
            if issue.location:
                parts.extend([
                    '<section class="structured-report__issue-card-section">',
                    '<div class="structured-report__issue-card-section-title">问题定位</div>',
                    f'<p class="structured-report__issue-card-text">{html.escape(issue.location)}</p>',
                    '</section>',
                ])
            parts.extend([
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
        for index, row in enumerate(rows, start=1):
            matched_section = self._matched_section_text(row.get('matchedSections') or [])
            status = str(row.get('status') or 'missing')
            table_rows.append(
                ChapterCompletenessRowView(
                    index=index,
                    requirement=self._clean_text(row.get('requirementLabel')) or '—',
                    basis=self._clean_text(row.get('basisClause')) or self._clean_text(row.get('basisRequirement')) or '—',
                    matchedSection=matched_section,
                    status=status,
                    statusLabel=_STATUS_LABELS.get(status, status),
                    note=self._chapter_row_note(row),
                )
            )
        return ChapterCompletenessView(tableRows=table_rows)

    def _build_normative_validity(self, findings: list[dict[str, Any]]) -> NormativeValidityView:
        checks: list[NormativeValidityCheckView] = []
        seen_keys: set[str] = set()
        for finding in findings:
            raw_data = finding.get('raw_data') if isinstance(finding.get('raw_data'), dict) else {}
            for item in raw_data.get('normativeValidityChecks') or []:
                if not isinstance(item, dict):
                    continue
                view = self._build_normative_validity_check(item)
                if not view:
                    continue
                dedupe_key = f'{view.title}|{view.status}'
                if dedupe_key in seen_keys:
                    continue
                seen_keys.add(dedupe_key)
                checks.append(view)
            single_check = raw_data.get('normativeValidityCheck')
            if isinstance(single_check, dict):
                view = self._build_normative_validity_check(single_check)
                if view:
                    dedupe_key = f'{view.title}|{view.status}'
                    if dedupe_key not in seen_keys:
                        seen_keys.add(dedupe_key)
                        checks.append(view)
        if not checks:
            return NormativeValidityView()
        current_count = sum(1 for item in checks if item.status == 'current')
        superseded_count = sum(1 for item in checks if item.status == 'superseded')
        unknown_count = sum(1 for item in checks if item.status == 'unknown')
        summary = f'共核验 {len(checks)} 项编制依据，其中现行有效 {current_count} 项，疑似废止/替代 {superseded_count} 项，待人工核验 {unknown_count} 项。'
        return NormativeValidityView(summary=summary, checks=checks)

    def _build_normative_validity_check(self, item: dict[str, Any]) -> NormativeValidityCheckView | None:
        original_title = self._clean_text(item.get('title')) or self._clean_text(item.get('sourceTitle'))
        if not original_title:
            return None
        status = self._clean_text(item.get('status')) or 'unknown'
        resolved_title = self._clean_text(item.get('resolvedTitle')) or ''
        summary = self._clean_text(item.get('summary')) or ''
        # Use resolved title as display title when available and different.
        display_title = resolved_title if resolved_title and resolved_title != original_title else original_title
        note = ''
        if status == 'unknown':
            note = summary or '需人工核验。'
        elif status == 'current' and resolved_title and resolved_title != original_title:
            note = f'已确认现行标准：{resolved_title}'
        return NormativeValidityCheckView(
            title=display_title,
            status=status,
            statusLabel=_VALIDITY_STATUS_LABELS.get(status, status),
            resolvedTitle=resolved_title,
            note=note,
        )

    def _build_issue_view(
        self,
        finding: dict[str, Any],
        support_issues: list[dict[str, Any]],
        structure_rows: list[dict[str, Any]],
        section_structure: list[dict[str, Any]],
    ) -> FinalReportIssueView:
        support_issue = self._match_support_issue(finding, support_issues)
        basis = self._collect_basis_lines(finding, support_issue)
        recommendation = self._recommendation_text(finding, support_issue)
        return FinalReportIssueView(
            id=str(finding.get('id') or ''),
            title=self._clean_text(finding.get('title')) or '未命名问题',
            severity=str(finding.get('severity') or 'info'),
            severityLabel=_SEVERITY_LABELS.get(str(finding.get('severity') or 'info'), str(finding.get('severity') or '提示')),
            location=self._resolve_location(finding, support_issue, structure_rows, section_structure),
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
        section_structure: list[dict[str, Any]],
    ) -> str:
        raw_data = finding.get('raw_data') if isinstance(finding.get('raw_data'), dict) else {}
        for matched_sections in [(support_issue or {}).get('matchedSections') or [], raw_data.get('matchedSections') or []]:
            matched_text = self._matched_section_text(matched_sections)
            if matched_text and matched_text != '未识别到稳定对应章节':
                return matched_text

        for row in self._matching_structure_rows(finding, structure_rows):
            matched_text = self._matched_section_text(row.get('matchedSections') or [])
            if matched_text and matched_text != '未识别到稳定对应章节':
                return matched_text

        section_lookup = self._build_section_lookup(section_structure)
        for source in [raw_data, support_issue or {}, finding]:
            precise = self._resolve_location_from_doc_evidence(source.get('docEvidence') or [], section_lookup)
            if precise:
                return precise

        for value in [
            finding.get('summary'),
            (support_issue or {}).get('summary'),
            finding.get('suggestion'),
            '；'.join((support_issue or {}).get('recommendation') or []) if isinstance((support_issue or {}).get('recommendation'), list) else '',
        ]:
            precise = self._format_location_candidate(self._extract_locator_phrase(self._clean_text(value)))
            if precise:
                return precise

        candidates: list[str] = []
        for source in [raw_data, support_issue or {}, finding]:
            for evidence in source.get('docEvidence') or []:
                if isinstance(evidence, dict):
                    excerpt = self._clean_text(evidence.get('excerpt'))
                    if excerpt:
                        candidates.append(excerpt)
        for candidate in candidates:
            precise = self._format_location_candidate(candidate)
            if precise:
                return precise
        return '未定位到稳定章节，请结合原文复核。'

    def _matching_structure_rows(self, finding: dict[str, Any], structure_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        raw_data = finding.get('raw_data') if isinstance(finding.get('raw_data'), dict) else {}
        title = self._clean_text(finding.get('title'))
        item_key = self._clean_text(raw_data.get('structure_item_key'))
        results: list[dict[str, Any]] = []
        for row in structure_rows:
            if item_key and item_key == self._clean_text(row.get('itemKey')):
                results.append(row)
                continue
            analysis = self._clean_text(row.get('analysis'))
            excerpt = self._clean_text(row.get('reportExcerpt'))
            requirement = self._clean_text(row.get('requirementLabel'))
            if title and any(title in value for value in [analysis, excerpt, requirement] if value):
                results.append(row)
        return results

    def _build_section_lookup(self, section_structure: list[dict[str, Any]]) -> dict[str, str]:
        by_id = {
            self._clean_text(item.get('id')): self._clean_text(item.get('title'))
            for item in section_structure
            if self._clean_text(item.get('id')) and self._clean_text(item.get('title'))
        }
        return by_id

    def _resolve_location_from_doc_evidence(self, doc_evidence: list[dict[str, Any]], section_lookup: dict[str, str]) -> str:
        for evidence in doc_evidence:
            if not isinstance(evidence, dict):
                continue
            locator = evidence.get('locator') if isinstance(evidence.get('locator'), dict) else {}
            section_id = self._clean_text(locator.get('sectionId'))
            if section_id and section_id in section_lookup:
                precise = self._format_location_candidate(section_lookup[section_id])
                if precise:
                    return precise
            excerpt = self._clean_text(evidence.get('excerpt'))
            precise = self._format_location_candidate(excerpt)
            if precise:
                return precise
        return ''

    def _format_location_candidate(self, text: str) -> str:
        value = self._clean_text(text)
        if not value:
            return ''
        locators = self._extract_section_locators(value)
        if locators:
            prefix = ' '.join(locators[:2])
            return prefix if len(prefix) <= 32 else prefix[:32].rstrip()
        if len(value) <= 60:
            return value
        return f'{value[:56].rstrip()}…'

    def _extract_locator_phrase(self, text: str) -> str:
        if not text:
            return ''
        locator_patterns = [
            r'((?:第[一二三四五六七八九十百零〇两0-9]+章)(?:[0-9A-Za-z\u4e00-\u9fa5\.\-、，,\s]{0,20})?)',
            r'((?:第[一二三四五六七八九十百零〇两0-9]+节)(?:[0-9A-Za-z\u4e00-\u9fa5\.\-、，,\s]{0,20})?)',
            r'((?:第[一二三四五六七八九十百零〇两0-9]+部分)(?:[0-9A-Za-z\u4e00-\u9fa5\.\-、，,\s]{0,20})?)',
            r'((?:第[一二三四五六七八九十百零〇两0-9]+章)?(?:\d+\.)+\d+节?)',
        ]
        for pattern in locator_patterns:
            match = re.search(pattern, text)
            if match:
                return self._clean_text(match.group(1))
        return ''

    def _collect_basis_lines(self, finding: dict[str, Any], support_issue: dict[str, Any] | None) -> list[str]:
        lines: list[str] = []
        seen: set[str] = set()
        for source in [finding.get('raw_data') if isinstance(finding.get('raw_data'), dict) else {}, support_issue or {}, finding]:
            for span in source.get('policyEvidence') or []:
                if not isinstance(span, dict):
                    continue
                source_id = self._clean_text(span.get('sourceId'))
                clause = self._clean_text(span.get('clauseTitle'))
                if not source_id or self._is_expert_review_point_source(source_id):
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

    def _collect_basis_files(self, packet: dict[str, Any], support_issues: list[dict[str, Any]], support_result: dict[str, Any]) -> list[str]:
        basis: list[str] = []
        seen: set[str] = set()
        for source in self._iter_basis_source_ids(packet, support_issues, support_result):
            if self._should_hide_basis_source(source):
                continue
            label, is_external = self._normalize_policy_source(source)
            if not is_external or label in seen:
                continue
            seen.add(label)
            basis.append(label)
        return basis[:20]

    def _iter_basis_source_ids(self, packet: dict[str, Any], support_issues: list[dict[str, Any]], support_result: dict[str, Any]) -> list[str]:
        out: list[str] = []
        for finding in packet.get('all_findings', []):
            raw_data = finding.get('raw_data') if isinstance(finding, dict) and isinstance(finding.get('raw_data'), dict) else {}
            for source in [raw_data, finding]:
                for span in source.get('policyEvidence') or []:
                    if isinstance(span, dict) and span.get('sourceId'):
                        out.append(str(span.get('sourceId')))
        for issue in support_issues:
            for span in issue.get('policyEvidence') or []:
                if isinstance(span, dict) and span.get('sourceId'):
                    out.append(str(span.get('sourceId')))
        selected_packs = list((support_result.get('summary') or {}).get('selectedPacks') or [])
        if not selected_packs:
            selected_packs = list((support_result.get('resolvedProfile') or {}).get('policyPackIds') or [])
        registry = get_evidence_pack_registry()
        for pack_id in selected_packs:
            pack = registry.get(pack_id)
            if not pack:
                continue
            for clause in pack.clauses:
                if clause.sourceId:
                    out.append(str(clause.sourceId))
        return out

    # Hard template→module rules: findings from these templates are ALWAYS
    # assigned to a fixed module, regardless of keyword/category fallback.
    _TEMPLATE_HARD_MODULE: dict[str, str] = {
        'normative_validity_reviewer': 'evidence_validation',
        'calculation_review_reviewer': 'evidence_validation',
        'visibility_gap_reviewer': 'evidence_validation',
    }

    def _resolve_module(self, finding: dict[str, Any]) -> str:
        raw_data = finding.get('raw_data') if isinstance(finding.get('raw_data'), dict) else {}
        # Hard template-based assignment takes priority (AGENTS.md HG-15)
        template_id = self._clean_text(raw_data.get('template_id'))
        if template_id in self._TEMPLATE_HARD_MODULE:
            return self._TEMPLATE_HARD_MODULE[template_id]

        # Keyword-based correction — runs BEFORE module_name because
        # Hermes templates often mis-label findings (e.g. marking
        # "现场勘察记录缺失" as execution_continuity when it's evidence).
        # Route order: structure → parameter → compliance → evidence → execution(catch-all)
        title_text = f"{self._clean_text(finding.get('title'))} {self._clean_text(finding.get('summary'))}".lower()
        kw_map = _get_module_keywords(self._document_type)

        route_order = [
            'structure_completeness',
            'parameter_consistency',
            'legality_compliance',
            'evidence_validation',
            'execution_continuity',
        ]
        for mod in route_order:
            keywords = kw_map.get(mod, [])
            if any(token in title_text for token in keywords):
                return mod

        # Hermes module_name as secondary fallback
        module_name = self._clean_text(raw_data.get('module_name'))
        if module_name in _MODULE_TITLES:
            return module_name

        # Category-based fallback
        category = self._clean_text(finding.get('category'))
        category_map = {
            'chapter_completeness': 'structure_completeness',
            'structure': 'structure_completeness',
            'visibility': 'evidence_validation',
            'parameter_consistency': 'parameter_consistency',
            'compliance': 'legality_compliance',
            'safety': 'legality_compliance',
            'rule_hits': 'legality_compliance',
            'process_coherence': 'execution_continuity',
            'evidence_verification': 'evidence_validation',
            'facts': 'evidence_validation',
        }
        return category_map.get(category, 'legality_compliance')

    def _dedupe_findings(self, findings: list[dict[str, Any]], selected_modules: list[str]) -> list[dict[str, Any]]:
        allowed = set(selected_modules or [])
        seen_keys: set[tuple[str, str]] = set()
        deduped: list[dict[str, Any]] = []
        for finding in findings:
            module_name = self._resolve_module(finding)
            if allowed and module_name not in allowed:
                continue
            item_id = self._clean_text(finding.get('id'))
            title = self._clean_text(finding.get('title')).lower()
            key = (item_id, title)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            deduped.append(finding)
        return deduped

    def _matched_section_text(self, matched_sections: list[dict[str, Any]]) -> str:
        locators: list[str] = []
        for item in matched_sections[:5]:
            if not isinstance(item, dict):
                continue
            title = self._clean_text(item.get('title'))
            locators.extend(self._extract_section_locators(title))
        locators = list(dict.fromkeys(locator for locator in locators if locator))
        if not locators:
            return '未识别到稳定对应章节'
        return '、'.join(locators[:3])

    def _chapter_row_note(self, row: dict[str, Any]) -> str:
        status = str(row.get('status') or '')
        if status == 'matched':
            return '—'
        analysis = self._clean_text(row.get('analysis'))
        recommendation = ''
        requirement = self._clean_text(row.get('requirementLabel'))
        if status == 'partial':
            recommendation = f'建议补齐或单列“{requirement}”。'
        elif status == 'missing':
            recommendation = f'建议补齐“{requirement}”专章或形成稳定章节标题。'
        elif status == 'blocked_by_visibility':
            recommendation = '当前受解析可视域限制，建议结合原件人工复核。'
        if recommendation and analysis:
            return f'{analysis} {recommendation}'[:120]
        return recommendation or analysis or '—'

    def _parse_executive_summary(self, summary: str) -> ExecutiveSummaryView:
        text = self._clean_text(summary)
        verdict = ''
        verdict_match = re.search(r'总体评级结论为：\*\*(.+?)\*\*', summary or '')
        if verdict_match:
            verdict = self._clean_text(verdict_match.group(1))
        else:
            fallback_match = re.search(r'总体评级(?:结论)?[:：]\s*([^。；]+)', text)
            if fallback_match:
                verdict = self._clean_text(fallback_match.group(1))

        narrative_parts = []
        cleaned_text = text.replace('**', '')
        for sentence in re.split(r'(?<=[。！？])\s*', cleaned_text):
            sentence = sentence.strip()
            if not sentence:
                continue
            if '总体评级结论为' in sentence or '当前命中' in sentence or '主审环节额外标注了' in sentence or '本次结果共覆盖' in sentence:
                continue
            narrative_parts.append(sentence)
        narrative = ' '.join(narrative_parts)
        return ExecutiveSummaryView(verdict=verdict, narrative=narrative, metrics=[])

    def _resolve_selected_modules(self, packet: dict[str, Any], selected_modules: list[str] | None) -> list[str]:
        if selected_modules:
            return [module for module in selected_modules if module in _MODULE_ORDER]
        metadata = dict(packet.get('metadata') or {})
        explicit = [
            module
            for module in metadata.get('selected_review_modules') or metadata.get('executed_review_modules') or []
            if isinstance(module, str) and module in _MODULE_ORDER
        ]
        return explicit or list(_MODULE_ORDER)

    def _module_order(self, selected_modules: list[str]) -> list[str]:
        requested = [module for module in selected_modules if module in _MODULE_ORDER]
        return requested or list(_MODULE_ORDER)

    def _build_section_metrics(self, sections: list[FinalReportSectionView]) -> list[ExecutiveSummaryMetricView]:
        tone_map = {
            'structure_completeness': 'medium',
            'parameter_consistency': 'medium',
            'legality_compliance': 'high',
            'execution_continuity': 'medium',
            'evidence_validation': 'low',
        }
        return [
            ExecutiveSummaryMetricView(
                label=section.title,
                value=f'{len(section.issues)} 项',
                tone=tone_map.get(section.key, 'neutral'),
            )
            for section in sections
        ]

    def _dedupe_issue_views(self, issues: list[FinalReportIssueView]) -> list[FinalReportIssueView]:
        deduped: list[FinalReportIssueView] = []
        for issue in issues:
            matched_index = next(
                (index for index, existing in enumerate(deduped) if self._issue_views_near_duplicate(existing, issue)),
                None,
            )
            if matched_index is None:
                deduped.append(issue)
                continue
            deduped[matched_index] = self._prefer_issue_view(deduped[matched_index], issue)
        return deduped

    def _issue_views_near_duplicate(self, left: FinalReportIssueView, right: FinalReportIssueView) -> bool:
        if left.severity != right.severity:
            return False
        title_similarity = self._similarity(self._normalize_compare_text(left.title), self._normalize_compare_text(right.title))
        description_similarity = self._similarity(
            self._normalize_compare_text(left.description),
            self._normalize_compare_text(right.description),
        )
        location_overlap = bool(left.location and right.location and (left.location in right.location or right.location in left.location))
        return title_similarity >= 0.72 and (description_similarity >= 0.68 or location_overlap)

    def _prefer_issue_view(self, left: FinalReportIssueView, right: FinalReportIssueView) -> FinalReportIssueView:
        def score(item: FinalReportIssueView) -> tuple[int, int, int]:
            return (
                1 if item.location and '未定位到稳定章节' not in item.location else 0,
                len(item.description),
                len(item.recommendation),
            )
        return right if score(right) > score(left) else left

    def _normalize_compare_text(self, text: str) -> str:
        return re.sub(r'[\W_]+', '', self._clean_text(text).lower())

    def _similarity(self, left: str, right: str) -> float:
        if not left or not right:
            return 0.0
        return SequenceMatcher(None, left, right).ratio()

    def _extract_section_locators(self, text: str) -> list[str]:
        value = self._clean_text(text)
        patterns = [
            r'(第[一二三四五六七八九十百零〇两0-9]+章)',
            r'(第[一二三四五六七八九十百零〇两0-9]+节)',
            r'((?:\d+\.)+\d+节?)',
        ]
        out: list[str] = []
        for pattern in patterns:
            for match in re.finditer(pattern, value):
                locator = self._clean_text(match.group(1))
                if locator and locator not in out:
                    out.append(locator)
        return out

    def _normalize_policy_source(self, source_id: str) -> tuple[str, bool]:
        if source_id in _INTERNAL_POLICY_SOURCES:
            return _INTERNAL_POLICY_SOURCES[source_id], False
        if '《' in source_id:
            return source_id[source_id.index('《'):], True
        return source_id, not source_id.startswith('review-control-plane-')

    def _is_expert_review_point_source(self, source_id: str) -> bool:
        return '监理工程师对停电施工方案的审核规则及要点' in source_id

    def _should_hide_basis_source(self, source_id: str) -> bool:
        hidden_keywords = (
            '监理工程师对停电施工方案的审核规则及要点',
            '危险性较大的分部分项工程专项施工方案编制指南',
        )
        return any(keyword in source_id for keyword in hidden_keywords)

    def _format_basis_citation(self, source_id: str, clause: str) -> str:
        source_label, _ = self._normalize_policy_source(source_id)
        clause_text = self._clean_text(clause or '').strip()
        if clause_text:
            return f'审查依据：引用自{source_label} {clause_text}'
        return f'审查依据：引用自{source_label}'

    def _is_normative_validity_summary_finding(self, finding: dict[str, Any]) -> bool:
        raw_data = finding.get('raw_data') if isinstance(finding.get('raw_data'), dict) else {}
        return bool(raw_data.get('normativeValidityChecks'))

    def _clean_text(self, value: Any) -> str:
        if value is None:
            return ''
        text = str(value).replace('\n', ' ').replace('\r', ' ')
        text = re.sub(r'\s+', ' ', text).strip()
        if text.lower() == 'demo':
            return '建议结合原文和附件补充完善后复核。'
        return text


_INTERNAL_POLICY_SOURCES = {
    'review-control-plane-support-scope-policy': '系统附件识别与复核规则',
    'review-control-plane-visibility-policy': '系统可视域处理规则',
}


def _number_to_cn(value: int) -> str:
    mapping = {1: '一', 2: '二', 3: '三', 4: '四', 5: '五', 6: '六', 7: '七', 8: '八', 9: '九', 10: '十'}
    return mapping.get(value, str(value))


_FINAL_REPORT_CSS = """
html, body {
  background: #f8f9fb !important;
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
  padding: 32px;
  background: #f8f9fb;
}

.structured-report * {
  box-sizing: border-box;
  min-width: 0;
  white-space: normal;
  word-break: break-word;
  overflow-wrap: anywhere;
}

.structured-report__title {
  margin: 0 0 28px;
  text-align: center;
  font-size: 28px;
  line-height: 1.3;
  color: #111827;
  font-weight: 700;
  letter-spacing: 0.02em;
}

/* --- Module section base --- */
.structured-report__section {
  margin-top: 28px;
  padding: 28px;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  break-inside: avoid;
}

.structured-report__section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.structured-report__section-title {
  margin: 0;
  padding: 14px 20px;
  border-radius: 10px;
  color: #ffffff;
  font-size: 20px;
  font-weight: 700;
  flex-grow: 1;
}

/* --- Per-module theme colors --- */
.structured-report__section-title--blue   { background: linear-gradient(135deg, #2563eb, #3b82f6); }
.structured-report__section-title--purple { background: linear-gradient(135deg, #7c3aed, #8b5cf6); }
.structured-report__section-title--red    { background: linear-gradient(135deg, #dc2626, #ef4444); }
.structured-report__section-title--amber  { background: linear-gradient(135deg, #d97706, #f59e0b); }
.structured-report__section-title--green  { background: linear-gradient(135deg, #059669, #10b981); }

.structured-report__section--blue   { border-left: 5px solid #2563eb; }
.structured-report__section--purple { border-left: 5px solid #7c3aed; }
.structured-report__section--red    { border-left: 5px solid #dc2626; }
.structured-report__section--amber  { border-left: 5px solid #d97706; }
.structured-report__section--green  { border-left: 5px solid #059669; }
.structured-report__section--overview { border-left: 5px solid #374151; }

/* Stats badge */
.structured-report__section-badge {
  display: inline-flex;
  align-items: center;
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  flex-shrink: 0;
}
.structured-report__section-badge--blue   { background: #dbeafe; color: #1e40af; }
.structured-report__section-badge--purple { background: #ede9fe; color: #5b21b6; }
.structured-report__section-badge--red    { background: #fee2e2; color: #991b1b; }
.structured-report__section-badge--amber  { background: #fef3c7; color: #92400e; }
.structured-report__section-badge--green  { background: #d1fae5; color: #065f46; }

/* Module description */
.structured-report__section-desc {
  margin: 12px 0 0;
  font-size: 14px;
  color: #6b7280;
  line-height: 1.6;
  padding-left: 2px;
}

.structured-report__subsection { margin-top: 20px; }
.structured-report__subsection-title {
  margin: 0 0 12px;
  font-size: 17px;
  color: #172033;
  font-weight: 600;
}

.structured-report__summary,
.structured-report__muted,
.structured-report__issue-card-text,
.structured-report__issue-card-law-item,
.structured-report__basis-list li {
  font-size: 15px;
  line-height: 1.85;
}

.structured-report__muted { color: #9ca3af; }

.structured-report__verdict-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.structured-report__verdict-label {
  color: #4b5563;
  font-weight: 600;
}

.structured-report__verdict-badge {
  display: inline-flex;
  align-items: center;
  padding: 6px 16px;
  border-radius: 999px;
  background: #fee2e2;
  color: #991b1b;
  font-weight: 700;
  font-size: 15px;
}

.structured-report__summary-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.structured-report__summary-metric {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 14px 16px;
  background: #ffffff;
}

.structured-report__summary-metric--high { background: #fef2f2; border-color: #fecaca; }
.structured-report__summary-metric--medium { background: #fff7ed; border-color: #fed7aa; }
.structured-report__summary-metric--low { background: #eff6ff; border-color: #bfdbfe; }

.structured-report__summary-metric-label {
  font-size: 13px;
  color: #6b7280;
}

.structured-report__summary-metric-value {
  margin-top: 6px;
  font-size: 22px;
  font-weight: 700;
  color: #111827;
}

.structured-report__basis-list,
.structured-report__issue-card-law-list {
  margin: 0;
  padding-left: 20px;
}

.structured-report__table-wrap {
  overflow-x: auto;
  border-radius: 12px;
  border: 1px solid #d1d5db;
  background: #ffffff;
}

.structured-report__table-wrap--landscape {
  page: wide;
  break-before: page;
  page-break-before: always;
}

.structured-report__matrix-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.structured-report__matrix-table th,
.structured-report__matrix-table td {
  padding: 14px 16px;
  border-bottom: 1px solid #e5e7eb;
  text-align: left;
  vertical-align: top;
  font-size: 14px;
  line-height: 1.7;
}

.structured-report__matrix-table th {
  background: #f3f4f6;
  color: #172033;
  font-weight: 700;
}

.structured-report__matrix-table tbody tr:last-child td { border-bottom: none; }
.structured-report__matrix-table tbody tr:nth-child(even) { background: #fafbfc; }

/* --- Issue cards --- */
.structured-report__issue-card {
  margin-top: 16px;
  padding: 22px 24px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  background: #ffffff;
  break-inside: avoid;
  page-break-inside: avoid;
  transition: box-shadow 0.15s ease;
}

.structured-report__issue-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.06); }

.structured-report__issue-card--high {
  border-left: 5px solid #dc2626;
  background: #fef8f8;
}

.structured-report__issue-card--medium {
  border-left: 5px solid #d97706;
  background: #fffcf5;
}

.structured-report__issue-card--low,
.structured-report__issue-card--info {
  border-left: 5px solid #2563eb;
  background: #f8faff;
}

.structured-report__issue-card-title {
  margin: 0 0 14px;
  font-size: 16px;
  color: #111827;
  font-weight: 600;
}

.structured-report__issue-card-section { margin-top: 12px; }
.structured-report__issue-card-section-title {
  margin-bottom: 6px;
  font-size: 14px;
  font-weight: 700;
  color: #9f1239;
}

@page {
  size: A4 portrait;
  margin: 18mm 16mm;
}

@page wide {
  size: A4 landscape;
  margin: 18mm 16mm;
}

@media print {
  html, body {
    background: #ffffff !important;
    font-size: 13px;
  }
  .structured-report {
    max-width: none;
    padding: 0;
    background: #ffffff;
  }
  .structured-report__title {
    font-size: 24px;
    margin-bottom: 20px;
  }
  .structured-report__section {
    box-shadow: none;
    border-radius: 8px;
    margin-top: 18px;
    padding: 18px 16px;
    break-inside: avoid;
    page-break-inside: avoid;
  }
  .structured-report__section-title {
    font-size: 17px;
    padding: 10px 16px;
    border-radius: 6px;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
  .structured-report__section-badge {
    font-size: 11px;
    padding: 4px 10px;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
  .structured-report__section-desc {
    font-size: 12px;
  }
  .structured-report__issue-card {
    margin-top: 12px;
    padding: 14px 16px;
    border-radius: 8px;
    break-inside: avoid;
    page-break-inside: avoid;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
  .structured-report__issue-card:hover { box-shadow: none; }
  .structured-report__issue-card-title {
    font-size: 14px;
    margin-bottom: 10px;
  }
  .structured-report__issue-card-text,
  .structured-report__issue-card-law-item,
  .structured-report__basis-list li {
    font-size: 13px;
    line-height: 1.7;
  }
  .structured-report__issue-card-section-title {
    font-size: 12px;
  }
  .structured-report__section-title,
  .structured-report__subsection-title,
  .structured-report__issue-card-title {
    break-after: avoid;
    page-break-after: avoid;
  }
  .structured-report__matrix-table thead { display: table-header-group; }
  .structured-report__matrix-table th,
  .structured-report__matrix-table td {
    padding: 10px 12px;
    font-size: 12px;
  }
  .structured-report__summary-metrics {
    gap: 8px;
  }
  .structured-report__summary-metric {
    padding: 10px 12px;
    border-radius: 8px;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
  .structured-report__summary-metric-value {
    font-size: 18px;
  }
}
"""
