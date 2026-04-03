from __future__ import annotations

from typing import Any


def compute_metrics(case: dict[str, Any], result: dict[str, Any]) -> dict[str, float | int]:
    expected_titles = set(case.get('groundTruthIssues', {}).get('expectedTitles', []))
    actual_titles = {issue.get('title') or '' for issue in result.get('issues', [])}
    matched_titles = expected_titles & actual_titles

    expected_visibility = case.get('groundTruthVisibility', {}).get('attachments', {})
    actual_visibility = {item['id']: item['visibility'] for item in result.get('matrices', {}).get('attachmentVisibility', [])}
    matched_visibility = sum(1 for key, value in expected_visibility.items() if actual_visibility.get(key) == value)

    issue_recall = len(matched_titles) / len(expected_titles) if expected_titles else 1.0
    visibility_accuracy = matched_visibility / len(expected_visibility) if expected_visibility else 1.0
    return {
        'issue_recall': round(issue_recall, 4),
        'attachment_visibility_accuracy': round(visibility_accuracy, 4),
        'expected_issue_count': len(expected_titles),
        'actual_issue_count': len(actual_titles),
    }
