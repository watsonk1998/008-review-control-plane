from __future__ import annotations

import json
from pathlib import Path

from src.review.evaluation.dataset import load_cases
from src.review.evaluation.harness import run_ablations, run_cross_model, run_cross_pack, run_main, run_replay
from src.review.evaluation.metrics import _evidence_traceability, _review_preparation_provenance_consistency


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def _build_legacy_case(root: Path) -> None:
    case_dir = root / 'hazardous_special_scheme' / 'case_001'
    source = case_dir / 'source.md'
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(
        '# 危大专项施工方案\n\n'
        '## 工程概况\n项目名称：Legacy 危大专项\n'
        '## 编制依据\n依据现行规范。\n'
        '起重吊装作业。\n'
        '附件1：吊装平面图\n',
        encoding='utf-8',
    )
    _write_json(
        case_dir / 'metadata.json',
        {
            'caseId': 'legacy-hz-001',
            'fixtureId': 'legacy-hz-001',
            'sourcePath': str(source),
            'query': '对该危大专项方案执行正式结构化审查',
            'docType': 'hazardous_special_scheme',
            'disciplineTags': ['lifting_operations'],
            'strictMode': True,
            'policyPackIds': [],
            'expectedPacks': ['hazardous_special_scheme.base', 'lifting_operations.base'],
            'ciEnabled': True,
        },
    )
    _write_json(
        case_dir / 'ground_truth_issues.json',
        {
            'issues': [
                {
                    'title': '危大专项方案核心章节不完整',
                    'layer': 'L1',
                    'severity': 'high',
                    'findingType': 'hard_evidence',
                    'requiredPolicyRefs': ['hazardous_scheme_structure'],
                    'manualReviewNeeded': False,
                }
            ]
        },
    )
    _write_json(case_dir / 'ground_truth_visibility.json', {'attachments': {'attachment-1': 'attachment_unparsed'}})


def _build_versioned_case(root: Path, *, ci_enabled: bool = False) -> None:
    case_dir = root / 'hazardous_special_scheme' / 'lifting' / 'cn_demo_hazardous_scheme' / 'v0.1.0-seed'
    source = root / 'hazardous_special_scheme' / 'lifting' / 'cn_demo_hazardous_scheme' / 'source.md'
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(
        '# 危大专项施工方案\n\n'
        '## 工程概况\n项目名称：Versioned 危大专项\n'
        '## 编制依据\n依据现行规范。\n'
        '起重吊装作业。\n'
        '附件1：吊装平面图\n',
        encoding='utf-8',
    )
    _write_json(
        case_dir / 'case_metadata.json',
        {
            'case_id': 'versioned-hz-001',
            'case_version': 'v0.1.0-seed',
            'doc_type': 'hazardous_special_scheme',
            'discipline_tags': ['lifting'],
            'expected_packs': ['hazardous_special_scheme.base', 'lifting_operations.base'],
            'ci_enabled': ci_enabled,
        },
    )
    _write_json(
        case_dir / 'source_ref.json',
        {
            'source_document': {
                'relative_path': 'hazardous_special_scheme/lifting/cn_demo_hazardous_scheme/source.md',
                'doc_type': 'hazardous_special_scheme',
                'file_kind': 'md',
            }
        },
    )
    _write_json(
        case_dir / 'expected_facts.json',
        {
            'facts': [
                {'key': 'lifting_operation_identified', 'value': True},
                {'key': 'has_attachment_1', 'value': True},
            ]
        },
    )
    _write_json(
        case_dir / 'expected_rule_hits.json',
        [
            {
                'rule_id': 'hazardous_special_scheme_attachment_visibility',
                'expected_status': 'manual_review_needed',
                'expected_match_type': 'visibility_gap',
            }
        ],
    )
    _write_json(
        case_dir / 'ground_truth_issues.json',
        [
            {
                'title': '专项方案附件处于可视域缺口，需人工复核原件',
                'layer': 'L1',
                'severity': 'medium',
                'finding_type': 'visibility_gap',
                'manual_review_needed': True,
            }
        ],
    )
    _write_json(
        case_dir / 'ground_truth_visibility.json',
        {
            'attachments': [
                {
                    'name': '附件1：吊装平面图',
                    'expected_visibility': 'attachment_unparsed',
                    'manual_review_needed': True,
                }
            ]
        },
    )


def test_review_eval_loader_supports_legacy_and_versioned_cases(tmp_path: Path):
    _build_legacy_case(tmp_path)
    _build_versioned_case(tmp_path)

    cases = load_cases(tmp_path)
    assert len(cases) == 2
    assert any(case.get('versioned') is False for case in cases)
    assert any(case.get('versioned') is True for case in cases)

    versioned_case = next(case for case in cases if case.get('versioned'))
    assert versioned_case['docType'] == 'hazardous_special_scheme'
    assert versioned_case['disciplineTags'] == ['lifting_operations']
    assert len(versioned_case['expectedFacts']) == 2
    assert len(versioned_case['expectedRuleHits']) == 1


def test_review_eval_harness_reports_stage_metrics_and_versioned_diagnostics(tmp_path: Path, monkeypatch):
    _build_legacy_case(tmp_path)
    _build_versioned_case(tmp_path, ci_enabled=True)

    monkeypatch.setattr('src.review.evaluation.harness.MIN_CI_CASES', 1)
    monkeypatch.setattr('src.review.evaluation.harness.MIN_TOTAL_CASES', 2)

    main_code, main_payload = run_main(tmp_path)
    assert main_code == 0
    assert 'issue_recall' in main_payload['aggregate']
    assert 'facts_accuracy' in main_payload['aggregate']
    assert 'rule_hit_accuracy' in main_payload['aggregate']
    assert 'layeredMetrics' in main_payload
    assert main_payload['layeredMetrics']['L0']['metrics']['attachment_visibility_accuracy'] >= 0
    assert main_payload['layeredMetrics']['L0']['metrics']['preflight_gate_consistency'] >= 0
    assert main_payload['layeredMetrics']['L2']['metrics']['facts_accuracy'] >= 0
    assert main_payload['layeredMetrics']['L2']['metrics']['evidence_traceability'] >= 0
    assert main_payload['layeredMetrics']['L3']['diagnosticOnly'] is True
    assert main_payload['layeredMetrics']['CrossCutting']['metrics']['review_preparation_provenance_consistency'] >= 0
    assert 'versionedDiagnostics' in main_payload
    assert len(main_payload['versionedDiagnostics']['cases']) == 1
    assert main_payload['versionedStageThresholds']['facts_accuracy'] == 0.9
    assert main_payload['versionedStageGate']['caseIds'] == ['versioned-hz-001']
    assert main_payload['versionedStageGate']['passed'] is True
    diagnostics = main_payload['versionedDiagnostics']['cases'][0]['evaluationDiagnostics']
    assert diagnostics['usedDirectFacts'] is True
    assert diagnostics['usedDirectRuleHits'] is True
    assert diagnostics['usedDirectUnresolvedFacts'] is True
    assert 'structured-review-facts' in diagnostics['artifactNames']
    assert 'structured-review-rule-hits' in diagnostics['artifactNames']

    ablation_code, ablation_payload = run_ablations(tmp_path)
    assert ablation_code == 0
    assert 'baseline' in ablation_payload['variants']
    assert 'disable_rule_engine' in ablation_payload['variants']
    assert 'facts_accuracy' in ablation_payload['variants']['baseline']['aggregate']
    assert 'layeredMetrics' in ablation_payload['variants']['baseline']

    cross_pack_code, cross_pack_payload = run_cross_pack(tmp_path)
    assert cross_pack_code == 0
    assert 'auto' in cross_pack_payload['variants']
    assert 'expected_packs_forced' in cross_pack_payload['variants']
    readiness_groups = cross_pack_payload['variants']['auto']['byDocumentTypeReadiness']
    assert 'official' in readiness_groups
    assert readiness_groups['official']['caseIds']

    cross_model_code, cross_model_payload = run_cross_model(tmp_path)
    assert cross_model_code == 0
    assert 'deterministic' in cross_model_payload['models']
    assert 'fallback' in cross_model_payload['models']
    assert 'layeredMetrics' in cross_model_payload['models']['deterministic']
    assert cross_model_payload['models']['deterministic']['gateRole'] == 'diagnostic'
    assert 'official' in cross_model_payload['models']['deterministic']['byDocumentTypeReadiness']
    assert (
        cross_model_payload['models']['deterministic']['aggregate']['facts_accuracy']
        == cross_model_payload['models']['fallback']['aggregate']['facts_accuracy']
    )

    replay_code, replay_payload = run_replay(tmp_path, case_ids=['versioned-hz-001'], output_dir=tmp_path / 'replay-output')
    assert replay_code == 0
    assert replay_payload['mode'] == 'replay'
    assert replay_payload['gateRole'] == 'diagnostic'
    assert replay_payload['selection']['matchedCaseCount'] == 1
    assert replay_payload['selection']['caseIds'] == ['versioned-hz-001']
    assert replay_payload['selection']['outputDirectory'] == str((tmp_path / 'replay-output').resolve())
    replay_case = replay_payload['cases'][0]
    assert replay_case['artifactCapture'] is not None
    assert 'structured-review-result.json' in replay_case['artifactCapture']['artifacts']
    assert Path(replay_case['artifactCapture']['path']).exists()


def test_evidence_traceability_covers_rule_hit_layer_states():
    result = {
        'matrices': {
            'ruleHits': [
                {
                    'ruleId': 'rule-visibility',
                    'status': 'manual_review_needed',
                    'applicabilityState': 'blocked_by_visibility',
                    'blockingReasons': ['visibility_gap'],
                    'missingFactKeys': [],
                },
                {
                    'ruleId': 'rule-missing-fact',
                    'status': 'hit',
                    'applicabilityState': 'blocked_by_missing_fact',
                    'blockingReasons': ['missing_fact'],
                    'missingFactKeys': ['attachments.special_scheme'],
                },
                {
                    'ruleId': 'rule-partial',
                    'status': 'manual_review_needed',
                    'applicabilityState': 'partial',
                    'blockingReasons': ['manual_confirmation_required'],
                    'missingFactKeys': [],
                },
                {
                    'ruleId': 'rule-applies',
                    'status': 'hit',
                    'applicabilityState': 'applies',
                    'blockingReasons': [],
                    'missingFactKeys': [],
                },
            ]
        },
        'issues': [
            {
                'id': 'ISSUE-001',
                'applicabilityState': 'blocked_by_missing_fact',
                'evidenceMissing': True,
                'missingFactKeys': ['attachments.special_scheme'],
                'blockingReasons': ['missing_fact'],
            }
        ],
        'unresolvedFacts': [
            {
                'factKey': 'attachments.special_scheme',
                'sourceExtractor': 'project_facts',
                'blockingRuleIds': ['rule-missing-fact'],
            }
        ],
    }

    score, checks = _evidence_traceability(result)
    assert checks >= 6
    assert score == 1.0


def test_evidence_traceability_fails_unexplained_evidence_gap_issue():
    result = {
        'matrices': {'ruleHits': []},
        'issues': [
            {
                'id': 'ISSUE-001',
                'issueKind': 'evidence_gap',
                'applicabilityState': 'applies',
                'evidenceMissing': True,
                'missingFactKeys': [],
                'blockingReasons': [],
            }
        ],
        'unresolvedFacts': [],
    }

    score, checks = _evidence_traceability(result)
    assert checks == 1
    assert score == 0.0


def test_review_preparation_provenance_consistency_distinguishes_versioned_vs_runtime():
    versioned_case = {
        'caseId': 'cn_hz_attachment_missing_ci',
        'caseVersion': 'v0.1.0-ci-stage-gate',
        'fixtureId': 'cn_hz_attachment_missing_ci',
        'sourcePath': '/tmp/source.md',
        'query': '对该危大专项方案执行正式结构化审查',
        'docType': 'hazardous_special_scheme',
        'disciplineTags': ['lifting_operations'],
    }
    runtime_case = {
        'caseId': 'runtime-only-case',
        'fixtureId': 'runtime-only-case',
        'sourcePath': '/tmp/runtime-source.md',
        'query': '对该施工组织设计执行正式结构化审查',
        'docType': 'construction_org',
        'disciplineTags': [],
    }
    result = {
        'visibility': {
            'manualReviewNeeded': False,
            'preflight': {'gateDecision': 'ready', 'blockingReasons': []},
        },
        'resolvedProfile': {'policyPackIds': ['construction_org.base']},
        'issues': [],
        'matrices': {'attachmentVisibility': []},
        'artifactIndex': [],
    }

    versioned_score, versioned_checks = _review_preparation_provenance_consistency(versioned_case, result)
    runtime_score, runtime_checks = _review_preparation_provenance_consistency(runtime_case, result)

    assert versioned_checks == runtime_checks == 4
    assert versioned_score == 1.0
    assert runtime_score == 1.0
