from __future__ import annotations

from typing import Any

from src.review.rules.packs import get_policy_pack_registry


_SEVERITY_SCORE = {'info': 0, 'low': 1, 'medium': 2, 'high': 3}
_RULE_ID_ALIASES = {
    'construction_org.section_duplicate_title': 'construction_org_duplicate_sections',
    'construction_org.attachment_reference_visible': 'construction_org_attachment_visibility',
    'lifting_operations.special_plan_required': 'construction_org_special_scheme_gap',
    'gas_area_ops.risk_identification_complete': 'gas_area_ops_control_linkage',
}


def _issue_map(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {issue.get('title') or '': issue for issue in result.get('issues', [])}


def _pack_accuracy(expected: set[str], actual: set[str]) -> float:
    if not expected and not actual:
        return 1.0
    if not expected:
        return 0.0
    return len(expected & actual) / len(expected)


def _normalize_ready_pack_ids(pack_ids: set[str], *, document_type: str | None = None) -> set[str]:
    registry = get_policy_pack_registry()
    normalized: set[str] = set()
    for pack_id in pack_ids:
        pack = registry.get(pack_id)
        if pack is None:
            continue
        if pack.readiness != 'ready':
            continue
        if document_type and pack.docTypes and document_type not in pack.docTypes:
            continue
        normalized.add(pack_id)
    return normalized


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


def _artifact_payload(
    evaluation_artifacts: dict[str, Any] | None,
    *,
    category: str | None = None,
    name: str | None = None,
) -> Any:
    if not evaluation_artifacts:
        return None
    if name:
        payload = (evaluation_artifacts.get('byName') or {}).get(name)
        if payload is not None:
            return payload
    if category:
        return (evaluation_artifacts.get('byCategory') or {}).get(category)
    return None


def _manual_review_value(issue: dict[str, Any]) -> bool:
    return bool(issue.get('manualReviewNeeded', False))


def _build_actual_visibility_maps(result: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    by_id: dict[str, str] = {}
    by_title: dict[str, str] = {}
    for item in result.get('matrices', {}).get('attachmentVisibility', []):
        visibility = item.get('visibility')
        if not visibility:
            continue
        if item.get('id'):
            by_id[str(item['id'])] = visibility
        if item.get('title'):
            by_title[str(item['title'])] = visibility
    return by_id, by_title


def _build_actual_visibility_items(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in result.get('matrices', {}).get('attachmentVisibility', [])
        if isinstance(item, dict) and item.get('visibility')
    ]


def _build_actual_rule_hit_map(result: dict[str, Any], evaluation_artifacts: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    direct_rule_hits = _artifact_payload(
        evaluation_artifacts,
        category='rule_hits',
        name='structured-review-rule-hits',
    )
    rows = direct_rule_hits if isinstance(direct_rule_hits, list) else result.get('matrices', {}).get('ruleHits', [])
    return {
        row.get('ruleId') or '': row
        for row in rows
        if row.get('ruleId')
    }


def _build_fact_snapshot(result: dict[str, Any], evaluation_artifacts: dict[str, Any] | None = None) -> dict[str, Any]:
    direct_facts = _artifact_payload(
        evaluation_artifacts,
        category='facts',
        name='structured-review-facts',
    )
    if isinstance(direct_facts, dict):
        hazard_values = direct_facts.get('hazardFacts', {})
        schedule_values = direct_facts.get('scheduleFacts', {})
        attachment_facts = direct_facts.get('attachmentFacts', {})
        visibility = attachment_facts.get('visibility', {})
        attachment_titles = {
            item.get('attachmentNumber') or item.get('title')
            for item in attachment_facts.get('attachments', [])
            if isinstance(item, dict)
        }
        project_values = direct_facts.get('projectFacts', {})
    else:
        hazard_values = result.get('matrices', {}).get('hazardIdentification', {}).get('values', {})
        schedule_values = result.get('matrices', {}).get('hazardIdentification', {}).get('values', {})
        visibility = result.get('visibility', {})
        attachment_titles = {
            item.get('attachmentNumber') or item.get('title')
            for item in result.get('matrices', {}).get('attachmentVisibility', [])
            if isinstance(item, dict)
        }
        project_values = hazard_values
    duplicate_titles = set(visibility.get('duplicateSectionTitles', []))
    section_presence = project_values.get('sectionPresence', {})
    return {
        'contains_gas_area': bool(hazard_values.get('gasArea')),
        'single_crane_shutdown_days': schedule_values.get('shutdownWindowDays', hazard_values.get('shutdownWindowDays')),
        'duplicate_section_title': duplicate_titles,
        'has_attachment_1': '1' in attachment_titles,
        'has_attachment_2': '2' in attachment_titles,
        'has_attachment_3': '3' in attachment_titles,
        'lifting_operation_identified': bool(hazard_values.get('liftingOperation')),
        'temporary_power_identified': bool(hazard_values.get('temporaryPower')),
        'hot_work_identified': bool(hazard_values.get('hotWork')),
        'monitoring_plan_present': bool(section_presence.get('monitoringPlan')),
        'context_only_material': bool(project_values.get('contextOnly')),
        'document_type_hint': project_values.get('documentTypeHint'),
    }


def _fact_accuracy(
    case: dict[str, Any],
    result: dict[str, Any],
    evaluation_artifacts: dict[str, Any] | None = None,
) -> tuple[float, int]:
    snapshot = _build_fact_snapshot(result, evaluation_artifacts)
    checks = 0
    hits = 0
    for item in case.get('expectedFacts', []):
        key = item.get('key')
        checks += 1
        actual = snapshot.get(key)
        expected = item.get('value')
        if isinstance(actual, set):
            if expected in actual:
                hits += 1
        elif actual == expected:
            hits += 1
    return ((hits / checks) if checks else 1.0, checks)


def _rule_hit_accuracy(
    case: dict[str, Any],
    result: dict[str, Any],
    evaluation_artifacts: dict[str, Any] | None = None,
) -> tuple[float, int]:
    actual_rule_hits = _build_actual_rule_hit_map(result, evaluation_artifacts)
    checks = 0
    hits = 0
    for expected in case.get('expectedRuleHits', []):
        expected_rule_id = expected.get('rule_id') or expected.get('ruleId')
        if not expected_rule_id:
            continue
        mapped_rule_id = _RULE_ID_ALIASES.get(expected_rule_id, expected_rule_id)
        actual = actual_rule_hits.get(mapped_rule_id)
        checks += 1
        if actual is None:
            continue
        status_match = actual.get('status') == expected.get('expected_status', expected.get('expectedStatus'))
        match_type_match = actual.get('matchType') == expected.get('expected_match_type', expected.get('expectedMatchType'))
        if status_match and match_type_match:
            hits += 1
    return ((hits / checks) if checks else 1.0, checks)


def _suggestion_defect_separation(case: dict[str, Any], result: dict[str, Any]) -> tuple[float, int]:
    actual_issues = _issue_map(result)
    checks = 0
    hits = 0
    for expected in case.get('groundTruthIssues', {}).get('issues', []):
        actual = actual_issues.get(expected.get('title', ''))
        checks += 1
        if actual is None:
            continue
        expected_group = 'enhancement' if expected.get('findingType') == 'suggestion_enhancement' else 'defect_or_gap'
        actual_group = 'enhancement' if actual.get('issueKind') == 'enhancement' else 'defect_or_gap'
        if expected_group == actual_group:
            hits += 1
    return ((hits / checks) if checks else 1.0, checks)


def _remediation_bucket_consistency(
    result: dict[str, Any],
    evaluation_artifacts: dict[str, Any] | None = None,
) -> tuple[float, int]:
    buckets = _artifact_payload(
        evaluation_artifacts,
        category='matrices',
        name='structured-review-report-buckets',
    )
    if not isinstance(buckets, dict):
        return (0.0 if result.get('issues') else 1.0, len(result.get('issues', [])))
    issue_bucket_map: dict[str, str] = {}
    for bucket_name, items in buckets.items():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            issue_id = item.get('id')
            if issue_id:
                issue_bucket_map[str(issue_id)] = str(bucket_name)
    checks = 0
    hits = 0
    for issue in result.get('issues', []):
        if not isinstance(issue, dict):
            continue
        issue_id = issue.get('id')
        if not issue_id:
            continue
        checks += 1
        if issue_bucket_map.get(str(issue_id)) == issue.get('issueKind'):
            hits += 1
    return ((hits / checks) if checks else 1.0, checks)


def _hazard_identification_accuracy(
    case: dict[str, Any],
    result: dict[str, Any],
    evaluation_artifacts: dict[str, Any] | None = None,
) -> tuple[float, int]:
    snapshot = _build_fact_snapshot(result, evaluation_artifacts)
    checks = 0
    hits = 0
    for item in case.get('expectedFacts', []):
        key = item.get('key')
        if key not in {'contains_gas_area', 'lifting_operation_identified', 'temporary_power_identified', 'hot_work_identified'}:
            continue
        checks += 1
        if snapshot.get(key) == item.get('value'):
            hits += 1
    return ((hits / checks) if checks else 1.0, checks)


def _preflight_gate_consistency(result: dict[str, Any]) -> tuple[float, int]:
    visibility = result.get('visibility') or {}
    preflight = visibility.get('preflight') or {}
    manual_review_needed = bool(visibility.get('manualReviewNeeded', False))
    expected_gate = 'manual_review_required' if manual_review_needed else 'ready'
    actual_gate = preflight.get('gateDecision')
    blocking_reasons = preflight.get('blockingReasons') or []
    passed = actual_gate == expected_gate
    if manual_review_needed and not blocking_reasons:
        passed = False
    if not manual_review_needed and actual_gate == 'ready' and blocking_reasons:
        passed = False
    return (1.0 if passed else 0.0, 1)


def _evidence_traceability(result: dict[str, Any]) -> tuple[float, int]:
    checks = 0
    hits = 0
    for issue in result.get('issues', []):
        if not isinstance(issue, dict):
            continue
        if not issue.get('evidenceMissing') and issue.get('applicabilityState') not in {
            'blocked_by_visibility',
            'blocked_by_missing_fact',
        }:
            continue
        checks += 1
        if issue.get('applicabilityState') == 'blocked_by_missing_fact':
            if issue.get('missingFactKeys'):
                hits += 1
            continue
        if issue.get('blockingReasons'):
            hits += 1
    for fact in result.get('unresolvedFacts', []):
        if not isinstance(fact, dict):
            continue
        checks += 1
        if fact.get('sourceExtractor') and fact.get('blockingRuleIds') is not None:
            hits += 1
    return ((hits / checks) if checks else 1.0, checks)


def compute_metrics(
    case: dict[str, Any],
    result: dict[str, Any],
    *,
    evaluation_artifacts: dict[str, Any] | None = None,
) -> dict[str, float | int]:
    expected_issues = case.get('groundTruthIssues', {}).get('issues', [])
    actual_issues = _issue_map(result)
    expected_titles = {issue.get('title', '') for issue in expected_issues}
    matched_titles = {title for title in expected_titles if title in actual_issues}

    l1_expected = [issue for issue in expected_issues if issue.get('layer') == 'L1']
    l1_matched = sum(1 for issue in l1_expected if (actual := actual_issues.get(issue.get('title', ''))) and actual.get('layer') == 'L1')

    high_severity_expected = [
        issue
        for issue in expected_issues
        if issue.get('severity') == 'high' and issue.get('layer') in {'L1', 'L2'}
    ]
    high_severity_matched = sum(1 for issue in high_severity_expected if issue.get('title', '') in actual_issues)

    policy_checks = 0
    policy_hits = 0
    severity_scores: list[float] = []
    manual_checks = 0
    manual_hits = 0
    hard_evidence_scores: list[float] = []
    for issue in expected_issues:
        actual = actual_issues.get(issue.get('title', ''))
        severity_scores.append(_severity_accuracy(issue, actual))
        if actual is not None:
            manual_checks += 1
            if _manual_review_value(actual) == issue.get('manualReviewNeeded', False):
                manual_hits += 1
        if issue.get('findingType') == 'hard_evidence':
            hard_evidence_scores.append(1.0 if actual and actual.get('findingType') == 'hard_evidence' else 0.0)
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

    expected_packs = _normalize_ready_pack_ids(set(case.get('expectedPacks', [])), document_type=case.get('docType'))
    actual_packs = _normalize_ready_pack_ids(
        set((result.get('resolvedProfile') or {}).get('policyPackIds', [])),
        document_type=case.get('docType'),
    )

    expected_visibility_items = case.get('groundTruthVisibility', {}).get('attachments', [])
    actual_visibility_by_id, actual_visibility_by_title = _build_actual_visibility_maps(result)
    actual_visibility_items = _build_actual_visibility_items(result)
    used_visibility_indexes: set[int] = set()
    visibility_checks = 0
    matched_visibility = 0
    for item in expected_visibility_items:
        expected_visibility = item.get('expectedVisibility', item.get('visibility'))
        expected_id = item.get('id')
        expected_name = item.get('name') or item.get('title')
        actual_visibility = None
        matched_index: int | None = None
        if expected_id:
            actual_visibility = actual_visibility_by_id.get(str(expected_id))
        if actual_visibility is None and expected_name:
            actual_visibility = actual_visibility_by_title.get(str(expected_name))
        if actual_visibility is not None:
            for index, actual_item in enumerate(actual_visibility_items):
                if index in used_visibility_indexes:
                    continue
                if expected_id and actual_item.get('id') == str(expected_id):
                    matched_index = index
                    break
                if expected_name and actual_item.get('title') == str(expected_name):
                    matched_index = index
                    break
        if actual_visibility is None:
            for index, actual_item in enumerate(actual_visibility_items):
                if index in used_visibility_indexes:
                    continue
                if actual_item.get('visibility') == expected_visibility:
                    actual_visibility = expected_visibility
                    matched_index = index
                    break
        visibility_checks += 1
        if actual_visibility == expected_visibility:
            matched_visibility += 1
            if matched_index is not None:
                used_visibility_indexes.add(matched_index)

    facts_accuracy, facts_checks = _fact_accuracy(case, result, evaluation_artifacts)
    rule_hit_accuracy, rule_hit_checks = _rule_hit_accuracy(case, result, evaluation_artifacts)
    hazard_accuracy, hazard_checks = _hazard_identification_accuracy(case, result, evaluation_artifacts)
    suggestion_separation_accuracy, suggestion_separation_checks = _suggestion_defect_separation(case, result)
    remediation_bucket_consistency, remediation_bucket_checks = _remediation_bucket_consistency(result, evaluation_artifacts)
    preflight_gate_consistency, preflight_gate_checks = _preflight_gate_consistency(result)
    evidence_traceability, evidence_traceability_checks = _evidence_traceability(result)

    issue_recall = len(matched_titles) / len(expected_titles) if expected_titles else 1.0
    l1_hit_rate = l1_matched / len(l1_expected) if l1_expected else 1.0
    high_severity_issue_recall = high_severity_matched / len(high_severity_expected) if high_severity_expected else 1.0
    pack_selection_accuracy = _pack_accuracy(expected_packs, actual_packs)
    policy_ref_accuracy = policy_hits / policy_checks if policy_checks else 1.0
    visibility_accuracy = matched_visibility / visibility_checks if visibility_checks else 1.0
    severity_accuracy = sum(severity_scores) / len(severity_scores) if severity_scores else 1.0
    manual_accuracy = manual_hits / manual_checks if manual_checks else 1.0
    hard_evidence_accuracy = sum(hard_evidence_scores) / len(hard_evidence_scores) if hard_evidence_scores else 1.0
    return {
        'issue_recall': round(issue_recall, 4),
        'l1_hit_rate': round(l1_hit_rate, 4),
        'high_severity_issue_recall': round(high_severity_issue_recall, 4),
        'pack_selection_accuracy': round(pack_selection_accuracy, 4),
        'policy_ref_accuracy': round(policy_ref_accuracy, 4),
        'attachment_visibility_accuracy': round(visibility_accuracy, 4),
        'severity_accuracy': round(severity_accuracy, 4),
        'manual_review_flag_accuracy': round(manual_accuracy, 4),
        'hard_evidence_accuracy': round(hard_evidence_accuracy, 4),
        'facts_accuracy': round(facts_accuracy, 4),
        'rule_hit_accuracy': round(rule_hit_accuracy, 4),
        'hazard_identification_accuracy': round(hazard_accuracy, 4),
        'preflight_gate_consistency': round(preflight_gate_consistency, 4),
        'evidence_traceability': round(evidence_traceability, 4),
        'suggestion_defect_separation': round(suggestion_separation_accuracy, 4),
        'remediation_bucket_consistency': round(remediation_bucket_consistency, 4),
        'facts_checks': facts_checks,
        'rule_hit_checks': rule_hit_checks,
        'hazard_identification_checks': hazard_checks,
        'preflight_gate_checks': preflight_gate_checks,
        'evidence_traceability_checks': evidence_traceability_checks,
        'suggestion_defect_separation_checks': suggestion_separation_checks,
        'remediation_bucket_checks': remediation_bucket_checks,
        'expected_issue_count': len(expected_titles),
        'actual_issue_count': len(actual_issues),
    }
