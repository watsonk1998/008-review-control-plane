from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys
from typing import Any

from src.review.evaluation.dataset import load_cases
from src.review.evaluation.metrics import compute_metrics
from src.review.evaluation.thresholds import THRESHOLDS, VERSIONED_STAGE_THRESHOLDS
from src.review.pipeline import StructuredReviewExecutor
from src.review.rules.packs import get_policy_pack_registry
from src.review.support_scope import is_official_document_type
from src.services.document_loader import DocumentLoader

MIN_CI_CASES = 12
MIN_TOTAL_CASES = 20


class DeterministicLLM:
    def explain_issue_candidates(self, candidates):
        payloads = []
        for index, candidate in enumerate(candidates, start=1):
            payloads.append(
                {
                    'id': f'ISSUE-{index:03d}',
                    'title': candidate.title,
                    'layer': candidate.layerHint,
                    'severity': candidate.severityHint,
                    'findingType': candidate.findingType,
                    'summary': candidate.title,
                    'manualReviewNeeded': candidate.manualReviewNeeded,
                    'evidenceMissing': candidate.evidenceMissing,
                    'manualReviewReason': candidate.manualReviewReason,
                    'docEvidence': [span.model_dump(mode='json') for span in candidate.docEvidence],
                    'policyEvidence': [span.model_dump(mode='json') for span in candidate.policyEvidence],
                    'recommendation': ['按证据链补齐正式审查材料。'],
                    'confidence': 'medium',
                }
            )
        return payloads


class FallbackLLM:
    def explain_issue_candidates(self, candidates):
        payloads = []
        for index, candidate in enumerate(candidates, start=1):
            payloads.append(
                {
                    'id': f'ISSUE-{index:03d}',
                    'title': candidate.title,
                    'layer': candidate.layerHint,
                    'severity': candidate.severityHint,
                    'findingType': candidate.findingType,
                    'summary': f'fallback::{candidate.title}',
                    'manualReviewNeeded': candidate.manualReviewNeeded,
                    'evidenceMissing': candidate.evidenceMissing,
                    'manualReviewReason': candidate.manualReviewReason,
                    'docEvidence': [span.model_dump(mode='json') for span in candidate.docEvidence],
                    'policyEvidence': [span.model_dump(mode='json') for span in candidate.policyEvidence],
                    'recommendation': ['fallback'],
                    'confidence': 'low' if candidate.manualReviewNeeded else 'medium',
                }
            )
        return payloads


_AGGREGATE_METRICS = [
    'issue_recall',
    'l1_hit_rate',
    'high_severity_issue_recall',
    'pack_selection_accuracy',
    'policy_ref_accuracy',
    'attachment_visibility_accuracy',
    'severity_accuracy',
    'manual_review_flag_accuracy',
    'hard_evidence_accuracy',
    'facts_accuracy',
    'rule_hit_accuracy',
    'hazard_identification_accuracy',
]


def _aggregate(case_summaries: list[dict[str, Any]]) -> dict[str, float]:
    if not case_summaries:
        return {name: 0.0 for name in _AGGREGATE_METRICS}
    return {
        name: round(statistics.mean(case['metrics'][name] for case in case_summaries), 4)
        for name in _AGGREGATE_METRICS
    }


def _dataset_guard(case_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    all_cases = load_cases(case_root, ci_only=False)
    stable_cases = [case for case in all_cases if case.get('ciEnabled', False) and not case.get('versioned', False)]
    versioned_cases = [case for case in all_cases if case.get('versioned', False)]
    counts = {
        'totalCases': len(all_cases),
        'ciCases': len(stable_cases),
        'versionedCases': len(versioned_cases),
    }
    return all_cases, stable_cases, versioned_cases, counts


def _passes_thresholds(aggregate: dict[str, float]) -> bool:
    return all(aggregate.get(key, 0.0) >= threshold for key, threshold in THRESHOLDS.items())


def _passes_versioned_stage_thresholds(aggregate: dict[str, float]) -> bool:
    return all(aggregate.get(key, 0.0) >= threshold for key, threshold in VERSIONED_STAGE_THRESHOLDS.items())


def _run_cases(
    cases: list[dict[str, Any]],
    *,
    llm,
    execution_options: dict[str, Any] | None = None,
    force_policy_pack_ids: list[str] | None = None,
    run_label: str | None = None,
) -> list[dict[str, Any]]:
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=llm, fast_adapter=None)
    summaries = []
    for case in cases:
        result = executor.run_sync(
            task_id=case['caseId'],
            query=case.get('query', '对该文件执行正式结构化审查'),
            source_document_path=case['sourcePath'],
            fixture_id=case.get('fixtureId'),
            document_type=case.get('docType'),
            discipline_tags=case.get('disciplineTags', []),
            strict_mode=case.get('strictMode', True),
            policy_pack_ids=force_policy_pack_ids if force_policy_pack_ids is not None else case.get('policyPackIds', []),
            execution_options=execution_options,
        )
        metrics = compute_metrics(case, result)
        summaries.append(
            {
                'caseId': case['caseId'],
                'docType': case.get('docType'),
                'versioned': case.get('versioned', False),
                'passed': True,
                'metrics': metrics,
                'resolvedProfile': result.get('resolvedProfile', {}),
                'summary': result.get('summary', {}),
                'executionOptions': execution_options or {},
                'runLabel': run_label,
            }
        )
    return summaries


def _filter_cross_pack_ids(pack_ids: list[str]) -> list[str]:
    registry = get_policy_pack_registry()
    filtered: list[str] = []
    for pack_id in pack_ids:
        pack = registry.get(pack_id)
        if pack is None or not pack.ruleIds:
            continue
        if pack.docTypes and not any(doc_type in {'construction_org', 'hazardous_special_scheme'} for doc_type in pack.docTypes):
            continue
        filtered.append(pack_id)
    return filtered


def run_main(case_root: Path) -> tuple[int, dict[str, Any]]:
    all_cases, stable_cases, versioned_cases, counts = _dataset_guard(case_root)
    if counts['ciCases'] < MIN_CI_CASES or counts['totalCases'] < MIN_TOTAL_CASES:
        return 1, {
            'mode': 'main',
            'passed': False,
            'aggregate': {},
            'thresholds': THRESHOLDS,
            'datasetCounts': counts,
            'minimums': {'ciCases': MIN_CI_CASES, 'totalCases': MIN_TOTAL_CASES},
            'cases': [],
            'versionedDiagnostics': [],
            'error': 'review evaluation dataset is below the required size gate',
        }
    stable_summaries = _run_cases(stable_cases, llm=DeterministicLLM(), run_label='main-stable')
    versioned_summaries = _run_cases(versioned_cases, llm=DeterministicLLM(), run_label='main-versioned') if versioned_cases else []
    aggregate = _aggregate(stable_summaries)
    versioned_gate_cases = [
        summary
        for summary in versioned_summaries
        if summary.get('docType') and is_official_document_type(summary.get('docType'))
        and any(case.get('caseId') == summary.get('caseId') and case.get('ciEnabled', False) for case in versioned_cases)
    ]
    versioned_gate_aggregate = _aggregate(versioned_gate_cases) if versioned_gate_cases else {}
    passed = _passes_thresholds(aggregate) and (not versioned_gate_cases or _passes_versioned_stage_thresholds(versioned_gate_aggregate))
    return (0 if passed else 1), {
        'mode': 'main',
        'passed': passed,
        'aggregate': aggregate,
        'thresholds': THRESHOLDS,
        'versionedStageThresholds': VERSIONED_STAGE_THRESHOLDS,
        'datasetCounts': counts,
        'cases': stable_summaries,
        'versionedStageGate': {
            'aggregate': versioned_gate_aggregate,
            'caseIds': [case['caseId'] for case in versioned_gate_cases],
            'passed': (not versioned_gate_cases or _passes_versioned_stage_thresholds(versioned_gate_aggregate)),
        },
        'versionedDiagnostics': {
            'aggregate': _aggregate(versioned_summaries) if versioned_summaries else {},
            'cases': versioned_summaries,
        },
    }


def run_ablations(case_root: Path) -> tuple[int, dict[str, Any]]:
    _, stable_cases, versioned_cases, counts = _dataset_guard(case_root)
    cases = [*stable_cases, *versioned_cases]
    variants = {
        'baseline': {},
        'disable_normalizer': {'disable_normalizer': True},
        'disable_visibility_check': {'disable_visibility_check': True},
        'disable_rule_engine': {'disable_rule_engine': True},
        'disable_llm_explanation': {'disable_llm_explanation': True},
    }
    results = {}
    for name, options in variants.items():
        case_summaries = _run_cases(cases, llm=DeterministicLLM(), execution_options=options, run_label=name)
        results[name] = {
            'aggregate': _aggregate(case_summaries),
            'cases': case_summaries,
            'executionOptions': options,
            'ablationMode': name != 'baseline',
        }
    passed = bool(results)
    return 0 if passed else 1, {'mode': 'ablations', 'passed': passed, 'datasetCounts': counts, 'variants': results}


def run_cross_pack(case_root: Path) -> tuple[int, dict[str, Any]]:
    _, stable_cases, versioned_cases, counts = _dataset_guard(case_root)
    cases = [*stable_cases, *versioned_cases]
    auto_case_summaries = _run_cases(cases, llm=DeterministicLLM(), run_label='cross-pack:auto')
    forced_case_summaries = []
    for case in cases:
        forced_pack_ids = _filter_cross_pack_ids(case.get('expectedPacks', []))
        if not forced_pack_ids:
            continue
        forced_case_summaries.extend(
            _run_cases([case], llm=DeterministicLLM(), force_policy_pack_ids=forced_pack_ids, run_label='cross-pack:expected_packs_forced')
        )
    payload = {
        'mode': 'cross-pack',
        'passed': True,
        'datasetCounts': counts,
        'variants': {
            'auto': {
                'aggregate': _aggregate(auto_case_summaries),
                'cases': auto_case_summaries,
            },
            'expected_packs_forced': {
                'aggregate': _aggregate(forced_case_summaries),
                'cases': forced_case_summaries,
            },
        },
    }
    return 0, payload


def run_cross_model(case_root: Path) -> tuple[int, dict[str, Any]]:
    _, stable_cases, versioned_cases, counts = _dataset_guard(case_root)
    cases = [*stable_cases, *versioned_cases]
    model_runs = {
        'deterministic': DeterministicLLM(),
        'fallback': FallbackLLM(),
    }
    payload = {'mode': 'cross-model', 'passed': True, 'datasetCounts': counts, 'models': {}}
    for model_name, llm in model_runs.items():
        case_summaries = _run_cases(cases, llm=llm)
        payload['models'][model_name] = {
            'aggregate': _aggregate(case_summaries),
            'cases': case_summaries,
        }
    return 0, payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['main', 'ablations', 'cross-pack', 'cross-model'], default='main')
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[5]
    case_root = repo_root / 'fixtures' / 'review_eval'
    if args.mode == 'main':
        code, payload = run_main(case_root)
    elif args.mode == 'ablations':
        code, payload = run_ablations(case_root)
    elif args.mode == 'cross-pack':
        code, payload = run_cross_pack(case_root)
    else:
        code, payload = run_cross_model(case_root)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return code


if __name__ == '__main__':
    sys.exit(main())
