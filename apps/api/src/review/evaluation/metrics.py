from __future__ import annotations

from typing import Any


_SEVERITY_SCORE = {'info': 0, 'low': 1, 'medium': 2, 'high': 3}


def _issue_map(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {issue.get('title') or '': issue for issue in result.get('issues', [])}


def _pack_accuracy(expected: set[str], actual: set[str]) -> float:
    if not expected and not actual:
        return 1.0
    if not expected:
        return 0.0
    union = expected | actual
    return len(expected & actual) / len(union) if union else 1.0


def _severity_accuracy(expected_issue: dict[str, Any], actual_issue: dict[str, Any] | None) -> float:
    if actual_issue is None:
        return 0.0
    expected_value = _SEVERITY_SCORE.get(expected_issue.get('severity', 'info'), 0)
    actual_value = _SEVERITY_SCORE.get(actual_issue.get('severity', 'info'), 0)
    diff = abs(expected_value - actual_value)
    if diff == 0:
        return 1.0
    if diff == 1:
        return 0.5
    return 0.0


def compute_metrics(case: dict[str, Any], result: dict[str, Any]) -> dict[str, float | int]:
    expected_issues = case.get('groundTruthIssues', {}).get('issues', [])
    actual_issues = _issue_map(result)
    expected_titles = {issue.get('title', '') for issue in expected_issues}
    matched_titles = {title for title in expected_titles if title in actual_issues}

    l1_expected = [issue for issue in expected_issues if issue.get('layer') == 'L1']
    l1_matched = sum(1 for issue in l1_expected if (actual := actual_issues.get(issue.get('title', ''))) and actual.get('layer') == 'L1')

    policy_checks = 0
    policy_hits = 0
    severity_scores: list[float] = []
    manual_scores: list[float] = []
    for issue in expected_issues:
        actual = actual_issues.get(issue.get('title', ''))
        severity_scores.append(_severity_accuracy(issue, actual))
        manual_scores.append(1.0 if actual and actual.get('whetherManualReviewNeeded') == issue.get('manualReviewNeeded', False) else 0.0)
        required_refs = issue.get('requiredPolicyRefs', [])
        if not required_refs:
            continue
        policy_checks += len(required_refs)
        actual_refs = {
            evidence.get('locator', {}).get('clauseId')
            for evidence in (actual or {}).get('policyEvidence', [])
            if isinstance(evidence, dict)
        }
        policy_hits += sum(1 for ref in required_refs if ref in actual_refs)

    expected_packs = set(case.get('expectedPacks', []))
    actual_packs = set((result.get('resolvedProfile') or {}).get('policyPackIds', []))

    expected_visibility = case.get('groundTruthVisibility', {}).get('attachments', {})
    actual_visibility = {item['id']: item['visibility'] for item in result.get('matrices', {}).get('attachmentVisibility', [])}
    matched_visibility = sum(1 for key, value in expected_visibility.items() if actual_visibility.get(key) == value)

    issue_recall = len(matched_titles) / len(expected_titles) if expected_titles else 1.0
    l1_hit_rate = l1_matched / len(l1_expected) if l1_expected else 1.0
    pack_selection_accuracy = _pack_accuracy(expected_packs, actual_packs)
    policy_ref_accuracy = policy_hits / policy_checks if policy_checks else 1.0
    visibility_accuracy = matched_visibility / len(expected_visibility) if expected_visibility else 1.0
    severity_accuracy = sum(severity_scores) / len(severity_scores) if severity_scores else 1.0
    manual_accuracy = sum(manual_scores) / len(manual_scores) if manual_scores else 1.0
    return {
        'issue_recall': round(issue_recall, 4),
        'l1_hit_rate': round(l1_hit_rate, 4),
        'pack_selection_accuracy': round(pack_selection_accuracy, 4),
        'policy_ref_accuracy': round(policy_ref_accuracy, 4),
        'attachment_visibility_accuracy': round(visibility_accuracy, 4),
        'severity_accuracy': round(severity_accuracy, 4),
        'manual_review_flag_accuracy': round(manual_accuracy, 4),
        'expected_issue_count': len(expected_titles),
        'actual_issue_count': len(actual_issues),
    }
