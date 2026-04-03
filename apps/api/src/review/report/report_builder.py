from __future__ import annotations

from collections import Counter
import json

from src.review.schema import (
    ResolvedReviewProfile,
    StructuredReviewMatrices,
    StructuredReviewSummary,
    StructuredReviewVisibilitySummary,
)


class StructuredReviewReportBuilder:
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
        overall = '修改后重新报审' if high_risk_issue or manual_review_needed else '可进入人工复核'
        visibility_summary = StructuredReviewVisibilitySummary(
            attachmentCount=visibility.attachmentCount,
            counts=visibility.counts,
            duplicateSectionTitles=visibility.duplicateSectionTitles,
            parseWarnings=parse_warnings,
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
            },
            visibilitySummary=visibility_summary,
        )

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
        lines = [
            '# Structured Review Report',
            '',
            '## 总体结论',
            f'- 结论：{summary.overallConclusion}',
            f'- 文档类型：{summary.documentType}',
            f'- 选用 packs：{", ".join(summary.selectedPacks) or "无"}',
            f'- 需人工复核：{"是" if summary.manualReviewNeeded else "否"}',
            '',
            '## 生效审查参数',
            f'- requested documentType：{resolved_profile.requestedDocumentType or "auto"}',
            f'- requested disciplineTags：{", ".join(resolved_profile.requestedDisciplineTags) or "auto"}',
            f'- requested policyPackIds：{", ".join(resolved_profile.requestedPolicyPackIds) or "auto"}',
            f'- resolved disciplineTags：{", ".join(resolved_profile.disciplineTags) or "无"}',
            f'- strictMode：{"true" if resolved_profile.strictMode else "false"}',
            '',
            '## 可视域与人工复核提示',
            f'- 附件数量：{parse_result.visibility.attachmentCount}',
            f'- parser limited：{"yes" if parse_result.visibility.parserLimited else "no"}',
            f'- file type：{parse_result.visibility.fileType or parse_result.fileType}',
            f'- 可视域计数：{json.dumps(parse_result.visibility.counts, ensure_ascii=False)}',
            f'- 可视域原因计数：{json.dumps(parse_result.visibility.reasonCounts, ensure_ascii=False)}',
            f'- duplicate sections：{", ".join(parse_result.visibility.duplicateSectionTitles) or "无"}',
            f'- parse warnings：{", ".join(parse_result.parseWarnings) or "无"}',
            '',
        ]
        if unresolved_facts:
            lines.extend(
                [
                    '## 未决 facts / 待人工确认',
                    *[f'- {item.code} · {item.summary}' for item in unresolved_facts],
                    '',
                ]
            )
        for layer in ['L1', 'L2', 'L3']:
            lines.append(f'## {layer} 问题')
            layer_issues = [issue for issue in issues if issue.layer.value == layer]
            if not layer_issues:
                lines.append('- 无')
                lines.append('')
                continue
            for issue in layer_issues:
                lines.extend(
                    [
                        f'### {issue.id} {issue.title}',
                        f'- severity: {issue.severity}',
                        f'- finding_type: {issue.findingType.value}',
                        f'- summary: {issue.summary}',
                        f'- manual_review_needed: {"yes" if issue.manualReviewNeeded else "no"}',
                        f'- manual_review_reason: {issue.manualReviewReason or "none"}',
                        f'- evidence_missing: {"yes" if issue.evidenceMissing else "no"}',
                        f'- recommendations: {"；".join(issue.recommendation)}',
                        '',
                    ]
                )
        lines.extend(
            [
                '## 危大识别矩阵',
                '```json',
                json.dumps(matrices.hazardIdentification.model_dump(mode='json'), ensure_ascii=False, indent=2),
                '```',
                '',
                '## 规则命中矩阵',
                '```json',
                json.dumps([item.model_dump(mode='json') for item in matrices.ruleHits], ensure_ascii=False, indent=2),
                '```',
                '',
                '## 冲突矩阵',
                '```json',
                json.dumps(matrices.conflicts.model_dump(mode='json'), ensure_ascii=False, indent=2),
                '```',
                '',
                '## 附件可视域矩阵',
                '```json',
                json.dumps([item.model_dump(mode='json') for item in matrices.attachmentVisibility], ensure_ascii=False, indent=2),
                '```',
                '',
                '## 章节结构图',
                '```json',
                json.dumps([item.model_dump(mode='json') for item in matrices.sectionStructure], ensure_ascii=False, indent=2),
                '```',
                '',
                '## 证据索引与人工复核说明',
                '- 所有 issue 均保留 docEvidence / policyEvidence 索引；visibility_gap 需结合附件原件人工复核。',
            ]
        )
        return '\n'.join(lines)
