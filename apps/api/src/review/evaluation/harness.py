from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import statistics
import sys
import tempfile
from typing import Any

from src.review.evaluation.dataset import load_cases
from src.review.evaluation.metrics import compute_metrics
from src.review.evaluation.thresholds import THRESHOLDS, VERSIONED_STAGE_THRESHOLDS
from src.review.pipeline import StructuredReviewExecutor
from src.review.rules.packs import get_policy_pack_registry
from src.review.support_scope import get_document_type_readiness, is_official_document_type
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
    'preflight_gate_consistency',
    'evidence_traceability',
    'review_preparation_provenance_consistency',
    'suggestion_defect_separation',
    'remediation_bucket_consistency',
]


def _aggregate(case_summaries: list[dict[str, Any]]) -> dict[str, float]:
    if not case_summaries:
        return {name: 0.0 for name in _AGGREGATE_METRICS}
    return {
        name: round(statistics.mean(case['metrics'][name] for case in case_summaries), 4)
        for name in _AGGREGATE_METRICS
    }


def _build_layered_metrics(aggregate: dict[str, float]) -> dict[str, Any]:
    return {
        'L0': {
            'metrics': {
                'attachment_visibility_accuracy': aggregate.get('attachment_visibility_accuracy', 0.0),
                'manual_review_flag_accuracy': aggregate.get('manual_review_flag_accuracy', 0.0),
                'preflight_gate_consistency': aggregate.get('preflight_gate_consistency', 0.0),
            }
        },
        'L1': {
            'metrics': {
                'issue_recall': aggregate.get('issue_recall', 0.0),
                'l1_hit_rate': aggregate.get('l1_hit_rate', 0.0),
                'high_severity_issue_recall': aggregate.get('high_severity_issue_recall', 0.0),
                'hard_evidence_accuracy': aggregate.get('hard_evidence_accuracy', 0.0),
                'severity_accuracy': aggregate.get('severity_accuracy', 0.0),
            }
        },
        'L2': {
            'metrics': {
                'facts_accuracy': aggregate.get('facts_accuracy', 0.0),
                'rule_hit_accuracy': aggregate.get('rule_hit_accuracy', 0.0),
                'policy_ref_accuracy': aggregate.get('policy_ref_accuracy', 0.0),
                'hazard_identification_accuracy': aggregate.get('hazard_identification_accuracy', 0.0),
                'evidence_traceability': aggregate.get('evidence_traceability', 0.0),
            }
        },
        'L3': {
            'diagnosticOnly': True,
            'metrics': {
                'suggestion_defect_separation': aggregate.get('suggestion_defect_separation', 0.0),
                'remediation_bucket_consistency': aggregate.get('remediation_bucket_consistency', 0.0),
            },
        },
        'CrossCutting': {
            'metrics': {
                'pack_selection_accuracy': aggregate.get('pack_selection_accuracy', 0.0),
                'review_preparation_provenance_consistency': aggregate.get('review_preparation_provenance_consistency', 0.0),
            }
        },
    }


def _with_layered_metrics(payload: dict[str, Any], aggregate: dict[str, float]) -> dict[str, Any]:
    payload['layeredMetrics'] = _build_layered_metrics(aggregate)
    return payload


def _aggregate_by_doc_type_readiness(case_summaries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for summary in case_summaries:
        readiness = get_document_type_readiness(summary.get('docType'))
        grouped.setdefault(readiness, []).append(summary)
    return {
        readiness: {
            'aggregate': _aggregate(items),
            'layeredMetrics': _build_layered_metrics(_aggregate(items)),
            'caseIds': [item['caseId'] for item in items],
        }
        for readiness, items in grouped.items()
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
    artifact_capture_root: Path | None = None,
) -> list[dict[str, Any]]:
    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=llm, fast_adapter=None)
    summaries = []
    for case in cases:
        artifact_dir_path: Path
        temp_dir: tempfile.TemporaryDirectory[str] | None = None
        if artifact_capture_root is not None:
            artifact_dir_path = artifact_capture_root / str(case['caseId'])
            if artifact_dir_path.exists():
                shutil.rmtree(artifact_dir_path)
            artifact_dir_path.mkdir(parents=True, exist_ok=True)
        else:
            temp_dir = tempfile.TemporaryDirectory(prefix=f"review-eval-{case['caseId']}-")
            artifact_dir_path = Path(temp_dir.name)
        try:

            def write_json_artifact(name: str, payload: Any) -> str:
                path = artifact_dir_path / f'{name}.json'
                path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
                return str(path)

            def write_text_artifact(name: str, content: str, suffix: str) -> str:
                path = artifact_dir_path / f'{name}{suffix}'
                path.write_text(content, encoding='utf-8')
                return str(path)

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
                allow_visibility_ablation=bool((execution_options or {}).get('disable_visibility_check')),
                write_json_artifact=write_json_artifact,
                write_text_artifact=write_text_artifact,
            )
            evaluation_artifacts = _load_evaluation_artifacts(result, artifact_dir_path)
            metrics = compute_metrics(case, result, evaluation_artifacts=evaluation_artifacts)
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
                    'artifactCapture': {
                        'path': str(artifact_dir_path),
                        'artifacts': sorted(path.name for path in artifact_dir_path.iterdir() if path.is_file()),
                    }
                    if artifact_capture_root is not None
                    else None,
                    'evaluationDiagnostics': {
                        'artifactCategories': sorted((evaluation_artifacts.get('byCategory') or {}).keys()),
                        'artifactNames': sorted((evaluation_artifacts.get('byName') or {}).keys()),
                        'usedDirectFacts': bool((evaluation_artifacts.get('byCategory') or {}).get('facts')),
                        'usedDirectRuleHits': bool((evaluation_artifacts.get('byCategory') or {}).get('rule_hits')),
                        'usedDirectUnresolvedFacts': _has_direct_unresolved_facts(result, evaluation_artifacts),
                        'unresolvedFactKeys': _extract_unresolved_fact_keys(result, evaluation_artifacts),
                    },
                }
            )
        finally:
            if temp_dir is not None:
                temp_dir.cleanup()
    return summaries


def _load_evaluation_artifacts(result: dict[str, Any], artifact_dir: Path) -> dict[str, Any]:
    by_category: dict[str, Any] = {}
    by_name: dict[str, Any] = {}
    for artifact in result.get('artifactIndex', []):
        if not isinstance(artifact, dict):
            continue
        file_name = artifact.get('fileName')
        if not file_name or not str(file_name).endswith('.json'):
            continue
        path = artifact_dir / str(file_name)
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding='utf-8'))
        name = artifact.get('name')
        category = artifact.get('category')
        if name:
            by_name[str(name)] = payload
        if not category:
            continue
        existing = by_category.get(str(category))
        if existing is None:
            by_category[str(category)] = payload
        elif isinstance(existing, list):
            existing.append(payload)
        else:
            by_category[str(category)] = [existing, payload]
    return {'byCategory': by_category, 'byName': by_name}


def _extract_unresolved_fact_keys(result: dict[str, Any], evaluation_artifacts: dict[str, Any]) -> list[str]:
    by_name = evaluation_artifacts.get('byName') or {}
    result_payload = by_name.get('structured-review-result')
    unresolved_items = result_payload.get('unresolvedFacts', []) if isinstance(result_payload, dict) else result.get('unresolvedFacts', [])
    return sorted(
        {
            str(item.get('factKey'))
            for item in unresolved_items
            if isinstance(item, dict) and item.get('factKey')
        }
    )


def _has_direct_unresolved_facts(result: dict[str, Any], evaluation_artifacts: dict[str, Any]) -> bool:
    by_name = evaluation_artifacts.get('byName') or {}
    result_payload = by_name.get('structured-review-result')
    return isinstance(result_payload, dict) and 'unresolvedFacts' in result_payload


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
    main_payload = {
        'mode': 'main',
        'gateRole': 'blocking',
        'passed': passed,
        'aggregate': aggregate,
        'layeredMetrics': _build_layered_metrics(aggregate),
        'thresholds': THRESHOLDS,
        'versionedStageThresholds': VERSIONED_STAGE_THRESHOLDS,
        'datasetCounts': counts,
        'cases': stable_summaries,
        'versionedStageGate': {
            'gateRole': 'blocking',
            'aggregate': versioned_gate_aggregate,
            'layeredMetrics': _build_layered_metrics(versioned_gate_aggregate) if versioned_gate_aggregate else {},
            'caseIds': [case['caseId'] for case in versioned_gate_cases],
            'passed': (not versioned_gate_cases or _passes_versioned_stage_thresholds(versioned_gate_aggregate)),
        },
        'versionedDiagnostics': {
            'gateRole': 'diagnostic',
            'aggregate': _aggregate(versioned_summaries) if versioned_summaries else {},
            'layeredMetrics': _build_layered_metrics(_aggregate(versioned_summaries)) if versioned_summaries else {},
            'byDocumentTypeReadiness': _aggregate_by_doc_type_readiness(versioned_summaries) if versioned_summaries else {},
            'cases': versioned_summaries,
        },
    }
    return (0 if passed else 1), main_payload


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
        aggregate = _aggregate(case_summaries)
        results[name] = {
            'aggregate': aggregate,
            'layeredMetrics': _build_layered_metrics(aggregate),
            'byDocumentTypeReadiness': _aggregate_by_doc_type_readiness(case_summaries),
            'cases': case_summaries,
            'executionOptions': options,
            'ablationMode': name != 'baseline',
            'gateRole': 'diagnostic',
        }
    passed = bool(results)
    return 0 if passed else 1, {'mode': 'ablations', 'gateRole': 'diagnostic', 'passed': passed, 'datasetCounts': counts, 'variants': results}


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
        'gateRole': 'diagnostic',
        'passed': True,
        'datasetCounts': counts,
        'variants': {
            'auto': {
                'aggregate': _aggregate(auto_case_summaries),
                'layeredMetrics': _build_layered_metrics(_aggregate(auto_case_summaries)),
                'byDocumentTypeReadiness': _aggregate_by_doc_type_readiness(auto_case_summaries),
                'cases': auto_case_summaries,
                'gateRole': 'diagnostic',
            },
            'expected_packs_forced': {
                'aggregate': _aggregate(forced_case_summaries),
                'layeredMetrics': _build_layered_metrics(_aggregate(forced_case_summaries)),
                'byDocumentTypeReadiness': _aggregate_by_doc_type_readiness(forced_case_summaries),
                'cases': forced_case_summaries,
                'gateRole': 'diagnostic',
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
    payload = {'mode': 'cross-model', 'gateRole': 'diagnostic', 'passed': True, 'datasetCounts': counts, 'models': {}}
    for model_name, llm in model_runs.items():
        case_summaries = _run_cases(cases, llm=llm)
        aggregate = _aggregate(case_summaries)
        payload['models'][model_name] = {
            'aggregate': aggregate,
            'layeredMetrics': _build_layered_metrics(aggregate),
            'byDocumentTypeReadiness': _aggregate_by_doc_type_readiness(case_summaries),
            'cases': case_summaries,
            'gateRole': 'diagnostic',
        }
    return 0, payload


def run_replay(
    case_root: Path,
    *,
    case_ids: list[str] | None = None,
    case_versions: list[str] | None = None,
    doc_types: list[str] | None = None,
    output_dir: Path | None = None,
) -> tuple[int, dict[str, Any]]:
    all_cases, stable_cases, versioned_cases, counts = _dataset_guard(case_root)
    selected_case_ids = {value for value in (case_ids or []) if value}
    selected_versions = {value for value in (case_versions or []) if value}
    selected_doc_types = {value for value in (doc_types or []) if value}

    if selected_case_ids or selected_versions or selected_doc_types:
        selected_cases = [
            case
            for case in all_cases
            if (not selected_case_ids or case.get('caseId') in selected_case_ids)
            and (not selected_versions or case.get('caseVersion') in selected_versions)
            and (not selected_doc_types or case.get('docType') in selected_doc_types)
        ]
    else:
        versioned_gate_cases = [
            case
            for case in versioned_cases
            if case.get('docType') and is_official_document_type(case.get('docType')) and case.get('ciEnabled', False)
        ]
        selected_cases = [*stable_cases, *versioned_gate_cases]

    replay_output_dir = output_dir or (Path(__file__).resolve().parents[5] / 'artifacts' / 'eval-replay')
    if replay_output_dir.exists():
        shutil.rmtree(replay_output_dir)
    replay_output_dir.mkdir(parents=True, exist_ok=True)

    if not selected_cases:
        payload = {
            'mode': 'replay',
            'gateRole': 'diagnostic',
            'passed': False,
            'datasetCounts': counts,
            'selection': {
                'caseIds': sorted(selected_case_ids),
                'caseVersions': sorted(selected_versions),
                'docTypes': sorted(selected_doc_types),
                'matchedCaseCount': 0,
                'outputDirectory': str(replay_output_dir),
            },
            'error': 'no review evaluation cases matched the replay filters',
            'cases': [],
        }
        return 1, payload

    case_summaries = _run_cases(
        selected_cases,
        llm=DeterministicLLM(),
        run_label='replay',
        artifact_capture_root=replay_output_dir,
    )
    aggregate = _aggregate(case_summaries)
    payload = {
        'mode': 'replay',
        'gateRole': 'diagnostic',
        'passed': True,
        'datasetCounts': counts,
        'selection': {
            'caseIds': [case.get('caseId') for case in selected_cases],
            'caseVersions': sorted({str(case.get('caseVersion')) for case in selected_cases if case.get('caseVersion')}),
            'docTypes': sorted({str(case.get('docType')) for case in selected_cases if case.get('docType')}),
            'matchedCaseCount': len(selected_cases),
            'outputDirectory': str(replay_output_dir),
            'defaultSelection': not (selected_case_ids or selected_versions or selected_doc_types),
        },
        'aggregate': aggregate,
        'layeredMetrics': _build_layered_metrics(aggregate),
        'byDocumentTypeReadiness': _aggregate_by_doc_type_readiness(case_summaries),
        'cases': case_summaries,
    }
    return 0, payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['main', 'ablations', 'cross-pack', 'cross-model', 'replay'], default='main')
    parser.add_argument('--case-id', action='append', default=[])
    parser.add_argument('--case-version', action='append', default=[])
    parser.add_argument('--doc-type', action='append', default=[])
    parser.add_argument('--output-dir')
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[5]
    case_root = repo_root / 'fixtures' / 'review_eval'
    if args.mode == 'main':
        code, payload = run_main(case_root)
    elif args.mode == 'ablations':
        code, payload = run_ablations(case_root)
    elif args.mode == 'cross-pack':
        code, payload = run_cross_pack(case_root)
    elif args.mode == 'replay':
        code, payload = run_replay(
            case_root,
            case_ids=args.case_id,
            case_versions=args.case_version,
            doc_types=args.doc_type,
            output_dir=Path(args.output_dir).resolve() if args.output_dir else None,
        )
    else:
        code, payload = run_cross_model(case_root)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return code


if __name__ == '__main__':
    sys.exit(main())
