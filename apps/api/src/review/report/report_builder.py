from __future__ import annotations

from collections import Counter
import json

from src.review.schema import StructuredReviewSummary


class StructuredReviewReportBuilder:
    def build_summary(self, *, document_type: str, selected_packs: list[str], issues, matrices, visibility_report):
        layer_counts = Counter(issue.layer.value for issue in issues)
        manual_review_needed = visibility_report.get('manualReviewNeeded', False) or any(issue.whetherManualReviewNeeded for issue in issues)
        high_risk_issue = any(issue.layer.value == 'L1' and issue.severity in {'high', 'medium'} for issue in issues)
        overall = '修改后重新报审' if high_risk_issue or manual_review_needed else '可进入人工复核'
        return StructuredReviewSummary(
            overallConclusion=overall,
            documentType=document_type,
            selectedPacks=selected_packs,
            manualReviewNeeded=manual_review_needed,
            issueCount=len(issues),
            layerCounts=dict(layer_counts),
            stats={
                'attachmentCount': len(matrices.get('attachmentVisibility', [])),
                'ruleHitCount': sum(1 for item in matrices.get('ruleHits', []) if item['status'] in {'hit', 'manual_review_needed'}),
            },
        )

    def render(self, *, summary: StructuredReviewSummary, issues, matrices, parse_result) -> str:
        lines = [
            '# Structured Review Report',
            '',
            '## 总体结论',
            f'- 结论：{summary.overallConclusion}',
            f'- 文档类型：{summary.documentType}',
            f'- 选用 packs：{", ".join(summary.selectedPacks) or "无"}',
            f'- 需人工复核：{"是" if summary.manualReviewNeeded else "否"}',
            '',
            '## 可视域与人工复核提示',
            f'- 附件数量：{summary.stats.get("attachmentCount", 0)}',
            f'- duplicate sections：{", ".join(parse_result.visibilityReport.get("duplicateSectionTitles", [])) or "无"}',
            '',
        ]
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
                        f'- manual_review_needed: {"yes" if issue.whetherManualReviewNeeded else "no"}',
                        f'- recommendations: {"；".join(issue.recommendation)}',
                        '',
                    ]
                )
        lines.extend(
            [
                '## 危大识别矩阵',
                '```json',
                json.dumps(matrices['hazardIdentification'], ensure_ascii=False, indent=2),
                '```',
                '',
                '## 规则命中矩阵',
                '```json',
                json.dumps(matrices['ruleHits'], ensure_ascii=False, indent=2),
                '```',
                '',
                '## 冲突矩阵',
                '```json',
                json.dumps(matrices['conflicts'], ensure_ascii=False, indent=2),
                '```',
                '',
                '## 附件可视域矩阵',
                '```json',
                json.dumps(matrices['attachmentVisibility'], ensure_ascii=False, indent=2),
                '```',
                '',
                '## 章节结构图',
                '```json',
                json.dumps(matrices['sectionStructure'], ensure_ascii=False, indent=2),
                '```',
                '',
                '## 证据索引与人工复核说明',
                '- 所有 issue 均保留 docEvidence / policyEvidence 索引；visibility_gap 需结合附件原件人工复核。',
            ]
        )
        return '\n'.join(lines)
