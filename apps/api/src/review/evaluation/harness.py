from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys
from typing import Any

from src.services.document_loader import DocumentLoader
from src.review.evaluation.dataset import load_cases
from src.review.evaluation.metrics import compute_metrics
from src.review.evaluation.thresholds import THRESHOLDS
from src.review.pipeline import StructuredReviewExecutor

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
                    'docEvidence': [span.model_dump(mode='json') for span in candidate.docEvidence],
                    'policyEvidence': [span.model_dump(mode='json') for span in candidate.policyEvidence],
                    'recommendation': ['按证据链补齐正式审查材料。'],
                    'confidence': 'medium',
                    'whetherManualReviewNeeded': candidate.manualReviewNeeded,
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
                    'docEvidence': [span.model_dump(mode='json') for span in candidate.docEvidence],
                    'policyEvidence': [span.model_dump(mode='json') for span in candidate.policyEvidence],
                    'recommendation': ['fallback'],
                    'confidence': 'low' if candidate.manualReviewNeeded else 'medium',
                    'whetherManualReviewNeeded': candidate.manualReviewNeeded,
                }
            )
        return payloads


def _aggregate(case_summaries: list[dict[str, Any]]) -> dict[str, float]:
    metric_names = [
        'issue_recall',
        'l1_hit_rate',
        'pack_selection_accuracy',
        'policy_ref_accuracy',
        'attachment_visibility_accuracy',
        'severity_accuracy',
        'manual_review_flag_accuracy',
    ]
    return {
        name: round(statistics.mean(case['metrics'][name] for case in case_summaries), 4)
        for name in metric_names
    }


def _dataset_guard(case_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    all_cases = load_cases(case_root, ci_only=False)
    ci_cases = [case for case in all_cases if case.get('ciEnabled', False)]
    counts = {'totalCases': len(all_cases), 'ciCases': len(ci_cases)}
    return all_cases, ci_cases, counts


def _passes_thresholds(aggregate: dict[str, float]) -> bool:
    return all(aggregate.get(key, 0.0) >= threshold for key, threshold in THRESHOLDS.items())


def _run_cases(cases: list[dict[str, Any]], *, llm, execution_options: dict[str, Any] | None = None, force_policy_pack_ids: list[str] | None = None) -> list[dict[str, Any]]:
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
                'passed': True,
                'metrics': metrics,
                'resolvedProfile': result.get('resolvedProfile', {}),
                'summary': result.get('summary', {}),
            }
        )
    return summaries


def run_main(case_root: Path) -> tuple[int, dict[str, Any]]:
    all_cases, cases, counts = _dataset_guard(case_root)
    if counts['ciCases'] < MIN_CI_CASES or counts['totalCases'] < MIN_TOTAL_CASES:
        return 1, {
            'mode': 'main',
            'passed': False,
            'aggregate': {},
            'thresholds': THRESHOLDS,
            'datasetCounts': counts,
            'minimums': {'ciCases': MIN_CI_CASES, 'totalCases': MIN_TOTAL_CASES},
            'cases': [],
            'error': 'review evaluation dataset is below the required size gate',
        }
    case_summaries = _run_cases(cases, llm=DeterministicLLM())
    aggregate = _aggregate(case_summaries)
    passed = _passes_thresholds(aggregate)
    return (0 if passed else 1), {'mode': 'main', 'passed': passed, 'aggregate': aggregate, 'thresholds': THRESHOLDS, 'datasetCounts': counts, 'cases': case_summaries}


def run_ablations(case_root: Path) -> tuple[int, dict[str, Any]]:
    _, cases, counts = _dataset_guard(case_root)
    variants = {
        'baseline': {},
        'disable_normalizer': {'disable_normalizer': True},
        'disable_visibility_check': {'disable_visibility_check': True},
        'disable_rule_engine': {'disable_rule_engine': True},
        'disable_llm_explanation': {'disable_llm_explanation': True},
    }
    results = {}
    for name, options in variants.items():
        case_summaries = _run_cases(cases, llm=DeterministicLLM(), execution_options=options)
        results[name] = {
            'aggregate': _aggregate(case_summaries),
            'cases': case_summaries,
        }
    passed = bool(results)
    return 0 if passed else 1, {'mode': 'ablations', 'passed': passed, 'datasetCounts': counts, 'variants': results}


def run_cross_pack(case_root: Path) -> tuple[int, dict[str, Any]]:
    _, cases, counts = _dataset_guard(case_root)
    auto_case_summaries = _run_cases(cases, llm=DeterministicLLM())
    forced_case_summaries = []
    for case in cases:
        forced_case_summaries.extend(
            _run_cases([case], llm=DeterministicLLM(), force_policy_pack_ids=case.get('expectedPacks', []))
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
    _, cases, counts = _dataset_guard(case_root)
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
