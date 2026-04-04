#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


REPO_ROOT = Path(__file__).resolve().parents[1]
APPS_API_ROOT = REPO_ROOT / 'apps' / 'api'
if str(APPS_API_ROOT) not in sys.path:
    sys.path.insert(0, str(APPS_API_ROOT))

from src.adapters.llm_gateway import LLMGateway
from src.config.llm import resolve_llm_config
from src.review.pipeline import StructuredReviewExecutor
from src.services.document_loader import DocumentLoader


SHANGHAI_TZ = ZoneInfo('Asia/Shanghai')
OUTPUT_ROOT = REPO_ROOT / 'artifacts' / 'research-pack'
EVAL_DIR = OUTPUT_ROOT / 'eval'
LOG_DIR = OUTPUT_ROOT / 'logs'
SUMMARY_PATH = OUTPUT_ROOT / 'latest-eval-summary.md'
MANIFEST_PATH = OUTPUT_ROOT / 'manifest.json'
SCRIPT_PATH = Path(__file__).resolve()
GENERATOR_COMMAND = 'python scripts/build_research_pack.py'

REQUIRED_RESULT_KEYS = {
    'summary',
    'visibility',
    'resolvedProfile',
    'issues',
    'matrices',
    'artifactIndex',
    'reportMarkdown',
    'unresolvedFacts',
}

REQUIRED_SAMPLE_FILES = [
    'structured-review-result.json',
    'structured-review-report.md',
    'structured-review-parse.json',
    'structured-review-l0-visibility.json',
    'structured-review-facts.json',
    'structured-review-rule-hits.json',
    'structured-review-candidates.json',
    'structured-review-report-buckets.json',
    'hazard-identification-matrix.json',
    'rule-hit-matrix.json',
    'conflict-matrix.json',
    'attachment-visibility-matrix.json',
    'section-structure-matrix.json',
]

SAMPLES = [
    {
        'id': 'sample-a-cold-rolling',
        'slug': 'supervision-sample-a-cold-rolling',
        'name': '冷轧厂 2030 单元三台行车电气系统改造',
        'task_id': 'research-pack-sample-a-cold-rolling',
        'fixture_id': 'supervision-cold-rolling-construction-plan',
        'source_document_path': REPO_ROOT / 'fixtures' / 'supervision' / '施工组织设计-冷轧厂2030单元三台行车电气系统改造.docx',
        'document_type': 'construction_org',
        'strict_mode': True,
        'query': '对该文件执行正式结构化审查',
        'source_mode': 'fixture',
    },
    {
        'id': 'sample-b-puhua-rainwater',
        'slug': 'supervision-sample-b-puhua-rainwater',
        'name': '培花初期雨水调蓄池建设工程',
        'task_id': 'research-pack-sample-b-puhua-rainwater',
        'fixture_id': None,
        'source_document_path': REPO_ROOT / 'fixtures' / 'supervision' / '施工组织设计-培花初期雨水调蓄池建设工程.pdf',
        'document_type': 'construction_org',
        'strict_mode': True,
        'query': '对该文件执行正式结构化审查',
        'source_mode': 'direct_path',
        'pdf_boundary_note': 'PDF 样本保持 pdf_text_only + parserLimited=True；可视域受限只表示当前解析边界，不得解释为正文或附件缺失。',
    },
]

EVAL_COMMANDS = [
    {
        'name': 'eval-review',
        'make_target': 'eval-review',
        'command': ['make', 'eval-review'],
        'log_path': LOG_DIR / 'eval-review.log',
        'json_path': EVAL_DIR / 'eval-review.json',
    },
    {
        'name': 'eval-review-ablations',
        'make_target': 'eval-review-ablations',
        'command': ['make', 'eval-review-ablations'],
        'log_path': LOG_DIR / 'eval-review-ablations.log',
        'json_path': EVAL_DIR / 'eval-review-ablations.json',
    },
    {
        'name': 'eval-review-cross-pack',
        'make_target': 'eval-review-cross-pack',
        'command': ['make', 'eval-review-cross-pack'],
        'log_path': LOG_DIR / 'eval-review-cross-pack.log',
        'json_path': EVAL_DIR / 'eval-review-cross-pack.json',
    },
    {
        'name': 'eval-review-cross-model',
        'make_target': 'eval-review-cross-model',
        'command': ['make', 'eval-review-cross-model'],
        'log_path': LOG_DIR / 'eval-review-cross-model.log',
        'json_path': EVAL_DIR / 'eval-review-cross-model.json',
    },
]


def now_iso() -> str:
    return datetime.now(SHANGHAI_TZ).isoformat(timespec='seconds')


def ensure_clean_output_root() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    EVAL_DIR.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def run_git_command(args: list[str]) -> str:
    completed = subprocess.run(
        ['git', *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout.strip()


def get_git_info() -> dict[str, Any]:
    status_short = run_git_command(['status', '--short'])
    return {
        'branch': run_git_command(['branch', '--show-current']),
        'commit': run_git_command(['rev-parse', 'HEAD']),
        'dirty': bool(status_short.strip()),
        'statusShort': status_short.splitlines() if status_short.strip() else [],
    }


def resolve_llm_gateway() -> tuple[LLMGateway | None, dict[str, Any]]:
    try:
        config = resolve_llm_config()
        gateway = LLMGateway(config=config)
        return gateway, {
            'mode': 'configured',
            'config': config.sanitized(),
            'warning': 'configured 表示成功解析了 LLM 配置；若运行期请求失败，structured_review 内部仍可能自动回退为 fallback issue 文案。',
        }
    except Exception as exc:  # pragma: no cover - best-effort runtime path
        return None, {
            'mode': 'fallback',
            'errorType': type(exc).__name__,
            'error': str(exc),
            'traceback': traceback.format_exc(),
        }


def extract_json_payload(text: str) -> Any | None:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char not in '{[':
            continue
        try:
            payload, end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if text[index + end :].strip():
            continue
        return payload
    return None


def build_sample_artifact_map(sample_dir: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    artifact_map: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for file_name in REQUIRED_SAMPLE_FILES:
        path = sample_dir / file_name
        exists = path.exists()
        artifact_map[file_name] = {
            'path': str(path),
            'exists': exists,
        }
        if exists and file_name.endswith('.json'):
            try:
                json.loads(path.read_text(encoding='utf-8'))
            except json.JSONDecodeError as exc:
                artifact_map[file_name]['jsonValid'] = False
                artifact_map[file_name]['error'] = f'{type(exc).__name__}: {exc}'
            else:
                artifact_map[file_name]['jsonValid'] = True
        if not exists:
            missing.append(file_name)
    return artifact_map, missing


def export_sample(
    sample: dict[str, Any],
    *,
    executor: StructuredReviewExecutor,
    llm_info: dict[str, Any],
) -> dict[str, Any]:
    sample_dir = OUTPUT_ROOT / sample['slug']
    sample_dir.mkdir(parents=True, exist_ok=True)
    generated_at = now_iso()

    def write_json_artifact(name: str, payload: Any) -> str:
        path = sample_dir / f'{name}.json'
        write_json(path, payload)
        return str(path)

    def write_text_artifact(name: str, content: str, suffix: str) -> str:
        path = sample_dir / f'{name}{suffix}'
        write_text(path, content)
        return str(path)

    record: dict[str, Any] = {
        'id': sample['id'],
        'name': sample['name'],
        'slug': sample['slug'],
        'generatedAt': generated_at,
        'taskId': sample['task_id'],
        'fixtureId': sample.get('fixture_id'),
        'sourceMode': sample['source_mode'],
        'sourceDocumentPath': str(sample['source_document_path']),
        'documentType': sample['document_type'],
        'strictMode': sample['strict_mode'],
        'query': sample['query'],
        'outputDirectory': str(sample_dir),
        'generatorScript': str(SCRIPT_PATH),
        'generatorCommand': GENERATOR_COMMAND,
        'llmMode': llm_info.get('mode'),
    }

    try:
        result = executor.run_sync(
            task_id=sample['task_id'],
            query=sample['query'],
            source_document_path=str(sample['source_document_path']),
            fixture_id=sample.get('fixture_id'),
            document_type=sample['document_type'],
            discipline_tags=[],
            strict_mode=sample['strict_mode'],
            policy_pack_ids=[],
            write_json_artifact=write_json_artifact,
            write_text_artifact=write_text_artifact,
        )
        record['success'] = True
        record['resultContractKeysPresent'] = sorted(REQUIRED_RESULT_KEYS & set(result.keys()))
        record['resultContractKeysMissing'] = sorted(REQUIRED_RESULT_KEYS - set(result.keys()))
        record['resultSummary'] = result.get('summary')
        record['visibility'] = result.get('visibility')
        record['unresolvedFactsCount'] = len(result.get('unresolvedFacts', []))
        artifact_index = result.get('artifactIndex', [])
        local_artifact_index = []
        for item in artifact_index:
            if not isinstance(item, dict):
                continue
            file_name = item.get('fileName')
            local_path = sample_dir / str(file_name) if file_name else None
            local_artifact_index.append(
                {
                    **item,
                    'localPath': str(local_path) if local_path else None,
                    'localPathExists': bool(local_path and local_path.exists()),
                }
            )
        record['artifactIndexLocalPaths'] = local_artifact_index
    except Exception as exc:  # pragma: no cover - runtime failure path
        record['success'] = False
        record['errorType'] = type(exc).__name__
        record['error'] = str(exc)
        record['traceback'] = traceback.format_exc()
        record['artifactIndexLocalPaths'] = []
        record['resultContractKeysPresent'] = []
        record['resultContractKeysMissing'] = sorted(REQUIRED_RESULT_KEYS)

    artifact_files, missing_artifacts = build_sample_artifact_map(sample_dir)
    record['artifactFiles'] = artifact_files
    record['missingArtifacts'] = missing_artifacts
    record['successfulArtifacts'] = sorted(
        file_name for file_name, details in artifact_files.items() if details.get('exists')
    )

    parse_path = sample_dir / 'structured-review-parse.json'
    if parse_path.exists():
        parse_payload = json.loads(parse_path.read_text(encoding='utf-8'))
        record['parseSnapshot'] = {
            'parseMode': parse_payload.get('parseMode'),
            'parserLimited': parse_payload.get('parserLimited'),
            'fileType': parse_payload.get('fileType'),
            'parseWarnings': parse_payload.get('parseWarnings', []),
        }
    if sample.get('pdf_boundary_note'):
        parse_snapshot = record.get('parseSnapshot', {})
        record['pdfVisibilityBoundary'] = {
            'note': sample['pdf_boundary_note'],
            'parseMode': parse_snapshot.get('parseMode'),
            'parserLimited': parse_snapshot.get('parserLimited'),
            'parseWarnings': parse_snapshot.get('parseWarnings', []),
        }
    return record


def run_eval_command(entry: dict[str, Any]) -> dict[str, Any]:
    started_at = now_iso()
    completed = subprocess.run(
        entry['command'],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=os.environ.copy(),
    )
    finished_at = now_iso()
    combined_log = '\n'.join(
        [
            f'# command: {" ".join(entry["command"])}',
            f'# cwd: {REPO_ROOT}',
            f'# started_at: {started_at}',
            f'# finished_at: {finished_at}',
            f'# exit_code: {completed.returncode}',
            '--- STDOUT ---',
            completed.stdout,
            '--- STDERR ---',
            completed.stderr,
        ]
    )
    write_text(entry['log_path'], combined_log)

    payload = extract_json_payload(completed.stdout)
    json_path: str | None = None
    json_parse_ok = isinstance(payload, dict)
    if json_parse_ok:
        write_json(entry['json_path'], payload)
        json_path = str(entry['json_path'])

    return {
        'name': entry['name'],
        'makeTarget': entry['make_target'],
        'command': ' '.join(entry['command']),
        'startedAt': started_at,
        'finishedAt': finished_at,
        'success': completed.returncode == 0,
        'exitCode': completed.returncode,
        'logPath': str(entry['log_path']),
        'jsonPath': json_path,
        'jsonParseOk': json_parse_ok,
        'stdoutBytes': len(completed.stdout.encode('utf-8')),
        'stderrBytes': len(completed.stderr.encode('utf-8')),
        'stdoutTail': completed.stdout[-4000:],
        'stderrTail': completed.stderr[-4000:],
        'payload': payload,
    }


def threshold_failures(metrics: dict[str, Any], thresholds: dict[str, Any]) -> list[dict[str, Any]]:
    failures = []
    for metric_name, threshold in thresholds.items():
        actual = float(metrics.get(metric_name, 0.0))
        if actual < float(threshold):
            failures.append(
                {
                    'metric': metric_name,
                    'actual': round(actual, 4),
                    'threshold': threshold,
                }
            )
    return failures


def summarize_eval_result(result: dict[str, Any]) -> list[str]:
    payload = result.get('payload') or {}
    name = result['name']
    lines = [
        f'### {name}',
        f'- 状态：{"成功" if result["success"] else "失败"}（exit {result["exitCode"]}）',
        f'- 日志：`{result["logPath"]}`',
        f'- JSON：`{result["jsonPath"]}`' if result.get('jsonPath') else '- JSON：未解析成功',
    ]
    if not isinstance(payload, dict):
        lines.append('- 关键结果：stdout 未解析出结构化 JSON。')
        lines.append('')
        return lines

    if name == 'eval-review':
        aggregate = payload.get('aggregate', {})
        versioned_gate = payload.get('versionedStageGate', {})
        legacy_thresholds = payload.get('thresholds', {})
        stage_thresholds = payload.get('versionedStageThresholds', {})
        legacy_failures = threshold_failures(aggregate, legacy_thresholds)
        stage_failures = threshold_failures(versioned_gate.get('aggregate', {}), stage_thresholds)
        lines.extend(
            [
                f'- legacy baseline：{"通过" if not legacy_failures else "未通过"}',
                f'- official versioned stage gate：{"通过" if versioned_gate.get("passed") else "未通过"}',
                f'- facts_accuracy：{aggregate.get("facts_accuracy", 0.0):.4f}',
                f'- rule_hit_accuracy：{aggregate.get("rule_hit_accuracy", 0.0):.4f}',
                f'- hazard_identification_accuracy：{aggregate.get("hazard_identification_accuracy", 0.0):.4f}',
                f'- attachment_visibility_accuracy：{aggregate.get("attachment_visibility_accuracy", 0.0):.4f}',
                f'- manual_review_flag_accuracy：{aggregate.get("manual_review_flag_accuracy", 0.0):.4f}',
                f'- 主结果 passed：{payload.get("passed")}',
                f'- legacy 失败项：{json.dumps(legacy_failures, ensure_ascii=False)}' if legacy_failures else '- legacy 失败项：无',
                f'- stage gate 失败项：{json.dumps(stage_failures, ensure_ascii=False)}' if stage_failures else '- stage gate 失败项：无',
            ]
        )
    elif name == 'eval-review-ablations':
        variants = payload.get('variants', {})
        lines.append(f'- 变体：{", ".join(sorted(variants.keys())) or "无"}')
        baseline = variants.get('baseline', {}).get('aggregate', {})
        if baseline:
            lines.append(f'- baseline facts_accuracy：{baseline.get("facts_accuracy", 0.0):.4f}')
            lines.append(f'- baseline rule_hit_accuracy：{baseline.get("rule_hit_accuracy", 0.0):.4f}')
    elif name == 'eval-review-cross-pack':
        variants = payload.get('variants', {})
        auto = variants.get('auto', {}).get('aggregate', {})
        forced = variants.get('expected_packs_forced', {}).get('aggregate', {})
        lines.append(f'- auto pack_selection_accuracy：{auto.get("pack_selection_accuracy", 0.0):.4f}')
        lines.append(f'- expected_packs_forced pack_selection_accuracy：{forced.get("pack_selection_accuracy", 0.0):.4f}')
    elif name == 'eval-review-cross-model':
        models = payload.get('models', {})
        deterministic = models.get('deterministic', {}).get('aggregate', {})
        fallback = models.get('fallback', {}).get('aggregate', {})
        lines.append(f'- deterministic facts_accuracy：{deterministic.get("facts_accuracy", 0.0):.4f}')
        lines.append(f'- fallback facts_accuracy：{fallback.get("facts_accuracy", 0.0):.4f}')

    lines.append('')
    return lines


def build_layered_metrics_section(main_payload: dict[str, Any]) -> list[str]:
    layered = main_payload.get('layeredMetrics', {}) if isinstance(main_payload, dict) else {}
    lines = ['## Layered Metrics']
    for layer_name in ['L0', 'L1', 'L2', 'L3', 'CrossCutting']:
        layer_payload = layered.get(layer_name, {})
        metrics = layer_payload.get('metrics', {})
        if not metrics:
            lines.append(f'### {layer_name}')
            lines.append('- 无可用指标')
            continue
        lines.append(f'### {layer_name}')
        for metric_name, metric_value in metrics.items():
            lines.append(f'- {metric_name}: {float(metric_value):.4f}')
        if layer_payload.get('diagnosticOnly'):
            lines.append('- diagnosticOnly: true')
    lines.append('')
    return lines


def build_anomaly_section(
    eval_results: list[dict[str, Any]],
    sample_records: list[dict[str, Any]],
) -> list[str]:
    lines = ['## 异常与风险']
    failures = [item for item in eval_results if not item['success']]
    if failures:
        for failure in failures:
            lines.append(f'- 命令失败：{failure["name"]}（exit {failure["exitCode"]}），日志：`{failure["logPath"]}`')
    else:
        lines.append('- 四个 eval 命令均成功返回。')

    for sample in sample_records:
        if sample.get('missingArtifacts'):
            lines.append(
                f'- 样本 `{sample["slug"]}` 存在缺失工件：{", ".join(sample["missingArtifacts"])}'
            )
        if sample.get('pdfVisibilityBoundary'):
            boundary = sample['pdfVisibilityBoundary']
            lines.append(
                '- PDF 解释边界：'
                f' parseMode={boundary.get("parseMode")},'
                f' parserLimited={boundary.get("parserLimited")},'
                ' 仅代表可视域受限，不代表文档或附件缺失。'
            )
    lines.append('')
    return lines


def write_eval_summary(
    *,
    git_info: dict[str, Any],
    llm_info: dict[str, Any],
    sample_records: list[dict[str, Any]],
    eval_results: list[dict[str, Any]],
) -> None:
    result_map = {item['name']: item for item in eval_results}
    main_payload = (result_map.get('eval-review') or {}).get('payload') or {}
    main_aggregate = main_payload.get('aggregate', {}) if isinstance(main_payload, dict) else {}
    versioned_gate = main_payload.get('versionedStageGate', {}) if isinstance(main_payload, dict) else {}
    legacy_thresholds = main_payload.get('thresholds', {}) if isinstance(main_payload, dict) else {}
    legacy_failures = threshold_failures(main_aggregate, legacy_thresholds)
    used_local_modifications = '是' if git_info.get('dirty') else '否'

    lines = [
        '# Latest Eval Summary',
        '',
        '## 执行环境',
        f'- 生成时间：{now_iso()}',
        f'- 仓库：`{REPO_ROOT}`',
        f'- 分支：`{git_info.get("branch")}`',
        f'- commit：`{git_info.get("commit")}`',
        f'- git dirty：{"yes" if git_info.get("dirty") else "no"}',
        f'- 是否使用了本地修改：{used_local_modifications}',
        f'- 本地修改列表：{json.dumps(git_info.get("statusShort", []), ensure_ascii=False)}',
        f'- LLM 模式：`{llm_info.get("mode")}`',
        f'- 关键命令：`make eval-review` / `make eval-review-ablations` / `make eval-review-cross-pack` / `make eval-review-cross-model`',
        '',
        '## 四个命令执行结果',
        '',
    ]
    for item in eval_results:
        lines.extend(summarize_eval_result(item))

    lines.extend(
        [
            '## 主评测摘要',
            f'- legacy baseline 是否通过：{"是" if not legacy_failures else "否"}',
            f'- official versioned stage gate 是否通过：{"是" if versioned_gate.get("passed") else "否"}',
            f'- 主评测总开关 passed：{main_payload.get("passed") if isinstance(main_payload, dict) else None}',
            f'- facts_accuracy：{main_aggregate.get("facts_accuracy", 0.0):.4f}',
            f'- rule_hit_accuracy：{main_aggregate.get("rule_hit_accuracy", 0.0):.4f}',
            f'- hazard_identification_accuracy：{main_aggregate.get("hazard_identification_accuracy", 0.0):.4f}',
            f'- attachment_visibility_accuracy：{main_aggregate.get("attachment_visibility_accuracy", 0.0):.4f}',
            f'- manual_review_flag_accuracy：{main_aggregate.get("manual_review_flag_accuracy", 0.0):.4f}',
            f'- versioned stage aggregate：{json.dumps(versioned_gate.get("aggregate", {}), ensure_ascii=False)}',
            '',
        ]
    )
    lines.extend(build_layered_metrics_section(main_payload if isinstance(main_payload, dict) else {}))
    lines.extend(build_anomaly_section(eval_results, sample_records))
    write_text(SUMMARY_PATH, '\n'.join(lines).rstrip() + '\n')


def build_manifest(
    *,
    git_info: dict[str, Any],
    llm_info: dict[str, Any],
    sample_records: list[dict[str, Any]],
    eval_results: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        'generatedAt': now_iso(),
        'repoRoot': str(REPO_ROOT),
        'generatorScript': str(SCRIPT_PATH),
        'generatorCommand': GENERATOR_COMMAND,
        'outputRoot': str(OUTPUT_ROOT),
        'summaryPath': str(SUMMARY_PATH),
        'git': git_info,
        'llm': llm_info,
        'samples': sample_records,
        'eval': {
            'commands': [
                {
                    key: value
                    for key, value in result.items()
                    if key not in {'payload', 'stdoutTail', 'stderrTail'}
                }
                for result in eval_results
            ],
            'summaryPath': str(SUMMARY_PATH),
            'logDirectory': str(LOG_DIR),
            'evalDirectory': str(EVAL_DIR),
        },
    }


def main() -> int:
    print(f'[research-pack] repo root: {REPO_ROOT}')
    ensure_clean_output_root()

    git_info = get_git_info()
    llm_gateway, llm_info = resolve_llm_gateway()
    print(f'[research-pack] llm mode: {llm_info.get("mode")}')

    executor = StructuredReviewExecutor(
        document_loader=DocumentLoader(),
        llm_gateway=llm_gateway,
        fast_adapter=None,
    )

    sample_records: list[dict[str, Any]] = []
    for sample in SAMPLES:
        print(f'[research-pack] exporting sample: {sample["name"]}')
        sample_records.append(export_sample(sample, executor=executor, llm_info=llm_info))

    eval_results: list[dict[str, Any]] = []
    for entry in EVAL_COMMANDS:
        print(f'[research-pack] running: {" ".join(entry["command"])}')
        eval_results.append(run_eval_command(entry))

    git_info = get_git_info()
    write_eval_summary(
        git_info=git_info,
        llm_info=llm_info,
        sample_records=sample_records,
        eval_results=eval_results,
    )
    manifest = build_manifest(
        git_info=git_info,
        llm_info=llm_info,
        sample_records=sample_records,
        eval_results=eval_results,
    )
    write_json(MANIFEST_PATH, manifest)

    sample_failures = [sample for sample in sample_records if not sample.get('success') or sample.get('missingArtifacts')]
    eval_failures = [item for item in eval_results if not item.get('success')]
    if sample_failures or eval_failures:
        print('[research-pack] completed with failures; inspect manifest and logs.', file=sys.stderr)
        return 1
    print('[research-pack] completed successfully.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
