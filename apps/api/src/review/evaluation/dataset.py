from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any


_TAG_ALIASES = {
    'lifting': 'lifting_operations',
    'temporary_power': 'temporary_power',
    'hot_work': 'hot_work',
    'gas_area': 'gas_area_ops',
    'gas_area_ops': 'gas_area_ops',
    'special_equipment': 'special_equipment',
    'working_at_height': 'working_at_height',
}

_NOISY_PATH_TOKENS = {'fixtures', 'copied', 'supervision', 'review', 'control', 'plane'}


def _load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding='utf-8'))


def _resolve_source_path(base_dir: Path, raw_path: str | None) -> str | None:
    if not raw_path:
        return None
    candidate = Path(raw_path)
    if candidate.is_absolute() and candidate.exists():
        return str(candidate)
    if not candidate.is_absolute():
        resolved = (base_dir / raw_path).resolve()
        if resolved.exists():
            return str(resolved)
    fallback = _fuzzy_resolve_fixture_path(base_dir, raw_path)
    if fallback:
        return fallback
    if candidate.is_absolute():
        return str(candidate)
    return str((base_dir / raw_path).resolve())


def _resolve_versioned_source_path(case_dir: Path, raw_path: str | None) -> str | None:
    if not raw_path:
        return None
    candidate = Path(raw_path)
    if candidate.is_absolute() and candidate.exists():
        return str(candidate)
    search_roots = [case_dir, *case_dir.parents]
    for root in search_roots:
        resolved = (root / raw_path).resolve()
        if resolved.exists():
            return str(resolved)
    fallback = _fuzzy_resolve_fixture_path(case_dir, raw_path)
    if fallback:
        return fallback
    return str((case_dir / raw_path).resolve())


def _find_fixture_search_root(base_dir: Path) -> Path:
    for root in [base_dir, *base_dir.parents]:
        fixtures_root = root / 'fixtures'
        if fixtures_root.exists():
            return fixtures_root
    return base_dir


def _fuzzy_resolve_fixture_path(base_dir: Path, raw_path: str) -> str | None:
    search_root = _find_fixture_search_root(base_dir)
    raw_candidate = Path(raw_path)
    suffix = raw_candidate.suffix
    stem_tokens = [
        token
        for token in re.split(r'[-_（）()\\s]+', raw_candidate.stem)
        if token and token not in _NOISY_PATH_TOKENS
    ]
    best_match: Path | None = None
    best_score = 0
    for candidate in search_root.rglob(f'*{suffix}'):
        score = sum(1 for token in stem_tokens if token in candidate.stem)
        if score > best_score:
            best_score = score
            best_match = candidate
    if best_match is None or best_score == 0:
        return None
    return str(best_match.resolve())


def _normalize_tags(values: list[str] | None) -> list[str]:
    normalized: list[str] = []
    for value in values or []:
        mapped = _TAG_ALIASES.get(value, value)
        if mapped not in normalized:
            normalized.append(mapped)
    return normalized


def _normalize_versioned_issue(issue: dict[str, Any]) -> dict[str, Any]:
    return {
        'title': issue.get('title', ''),
        'layer': issue.get('layer', 'L2'),
        'severity': issue.get('severity', 'info'),
        'findingType': issue.get('finding_type', issue.get('findingType', 'engineering_inference')),
        'requiredPolicyRefs': issue.get('requiredPolicyRefs', []),
        'manualReviewNeeded': issue.get('manual_review_needed', issue.get('manualReviewNeeded', False)),
    }


def _normalize_versioned_visibility(payload: dict[str, Any]) -> dict[str, Any]:
    attachments = payload.get('attachments', [])
    normalized_items = []
    for item in attachments:
        normalized_items.append(
            {
                'name': item.get('name') or item.get('title') or '',
                'expectedVisibility': item.get('expected_visibility', item.get('expectedVisibility', 'unknown')),
                'manualReviewNeeded': item.get('manual_review_needed', item.get('manualReviewNeeded', False)),
            }
        )
    return {'attachments': normalized_items}


def _normalize_legacy_visibility(payload: dict[str, Any]) -> dict[str, Any]:
    attachments = payload.get('attachments', {})
    if isinstance(attachments, list):
        return {'attachments': attachments}
    normalized_items = []
    for key, value in attachments.items():
        normalized_items.append({'id': key, 'expectedVisibility': value})
    return {'attachments': normalized_items}


def _default_query(doc_type: str) -> str:
    if doc_type == 'hazardous_special_scheme':
        return '对该危大专项方案执行正式结构化审查'
    return '对该文件执行正式结构化审查'


def _load_legacy_case(metadata_path: Path) -> dict[str, Any]:
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    issue_path = metadata_path.with_name('ground_truth_issues.json')
    visibility_path = metadata_path.with_name('ground_truth_visibility.json')
    expected_facts_path = metadata_path.with_name('expected_facts.json')
    expected_rule_hits_path = metadata_path.with_name('expected_rule_hits.json')
    source_path = _resolve_source_path(metadata_path.parent, metadata.get('sourcePath'))
    return {
        **metadata,
        'caseDir': str(metadata_path.parent),
        'sourcePath': source_path,
        'groundTruthIssues': _load_json(issue_path, {'issues': []}),
        'groundTruthVisibility': _normalize_legacy_visibility(_load_json(visibility_path, {'attachments': {}})),
        'expectedFacts': _load_json(expected_facts_path, {}).get('facts', []),
        'expectedRuleHits': _load_json(expected_rule_hits_path, []),
        'versioned': False,
    }


def _load_versioned_case(metadata_path: Path) -> dict[str, Any]:
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    case_dir = metadata_path.parent
    source_ref = _load_json(case_dir / 'source_ref.json', {})
    source_document = source_ref.get('source_document', {})
    source_files = metadata.get('source_files', [])
    raw_source = source_document.get('relative_path') or source_document.get('absolute_path') or (source_files[0] if source_files else None)
    source_path = _resolve_versioned_source_path(case_dir, raw_source)

    return {
        'caseId': metadata.get('case_id', case_dir.name),
        'caseVersion': metadata.get('case_version'),
        'fixtureId': metadata.get('case_id', case_dir.name),
        'sourcePath': source_path,
        'query': _default_query(metadata.get('doc_type', 'construction_org')),
        'docType': metadata.get('doc_type', 'construction_org'),
        'disciplineTags': _normalize_tags(metadata.get('discipline_tags', [])),
        'strictMode': True,
        'policyPackIds': [],
        'expectedPacks': metadata.get('expected_packs', []),
        'manualReviewCases': [],
        'ciEnabled': bool(metadata.get('ci_enabled', False)),
        'caseDir': str(case_dir),
        'groundTruthIssues': {
            'issues': [_normalize_versioned_issue(item) for item in _load_json(case_dir / 'ground_truth_issues.json', [])],
        },
        'groundTruthVisibility': _normalize_versioned_visibility(_load_json(case_dir / 'ground_truth_visibility.json', {'attachments': []})),
        'expectedFacts': _load_json(case_dir / 'expected_facts.json', {}).get('facts', []),
        'expectedRuleHits': _load_json(case_dir / 'expected_rule_hits.json', []),
        'versioned': True,
        'labelStatus': metadata.get('label_status'),
        'truthLevel': metadata.get('truth_level'),
    }


def load_cases(root: str | Path, *, ci_only: bool = False) -> list[dict[str, Any]]:
    base = Path(root)
    cases: list[dict[str, Any]] = []
    for metadata_path in sorted(base.rglob('metadata.json')):
        case = _load_legacy_case(metadata_path)
        if ci_only and not case.get('ciEnabled', False):
            continue
        cases.append(case)
    for metadata_path in sorted(base.rglob('case_metadata.json')):
        case = _load_versioned_case(metadata_path)
        if ci_only and not case.get('ciEnabled', False):
            continue
        cases.append(case)
    return cases
