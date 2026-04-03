from __future__ import annotations

import json
from pathlib import Path

from src.review.evaluation.dataset import load_cases
from src.review.evaluation.harness import run_ablations, run_cross_model, run_cross_pack, run_main


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

    cross_pack_code, cross_pack_payload = run_cross_pack(tmp_path)
    assert cross_pack_code == 0
    assert 'auto' in cross_pack_payload['variants']
    assert 'expected_packs_forced' in cross_pack_payload['variants']

    cross_model_code, cross_model_payload = run_cross_model(tmp_path)
    assert cross_model_code == 0
    assert 'deterministic' in cross_model_payload['models']
    assert 'fallback' in cross_model_payload['models']
