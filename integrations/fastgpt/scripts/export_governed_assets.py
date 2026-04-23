#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
API_SRC = REPO_ROOT / 'apps' / 'api'
LEGACY_OUTPUT_DIR = (
    REPO_ROOT
    / 'integrations'
    / 'fastgpt'
    / 'toolset'
    / 'hermesStructuredReview'
    / 'assets'
    / 'generated'
)
GOVERNANCE_OUTPUT_DIR = REPO_ROOT / 'artifacts' / 'fastgpt' / 'governance'

sys.path.insert(0, str(API_SRC))

from src.review.hermes.module_bindings import REVIEW_MODULE_BINDINGS, module_titles  # type: ignore
from src.review.final_report_merger import _DOC_TYPE_LABELS  # type: ignore
from src.review.evidence.evidence_builder import EvidenceBuilder  # type: ignore

CONFIG_DIR = REPO_ROOT / 'config' / 'review_basis'
TEMPLATE_DIR = API_SRC / 'src' / 'review' / 'hermes' / 'templates'


def write_json(output_dir: Path, name: str, payload) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / name).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8'
    )


def write_both(name: str, payload) -> None:
    write_json(LEGACY_OUTPUT_DIR, name, payload)
    write_json(GOVERNANCE_OUTPUT_DIR, name, payload)


def load_yaml(name: str):
    return yaml.safe_load((CONFIG_DIR / name).read_text(encoding='utf-8'))


def build_dataset_manifest(snapshot: dict) -> dict:
    doc_type_labels = snapshot['doc_type_labels']
    profile_mapping = snapshot['profile_mapping']
    pack_registry = snapshot['pack_registry'].get('packs', {})
    basis_registry = snapshot['basis_registry']

    entries = []
    for profile_id, profile in profile_mapping.items():
        pack_ids = list(
            dict.fromkeys(
                [
                    *(profile.get('default_pack_ids') or []),
                    *(profile.get('required_pack_ids') or []),
                    *(profile.get('enterprise_pack_ids') or []),
                ]
            )
        )
        basis_ids = list(
            dict.fromkeys(
                basis_id
                for pack_id in pack_ids
                for basis_id in (pack_registry.get(pack_id, {}) or {}).get('basis_ids', [])
            )
        )
        basis_files = list(
            dict.fromkeys(
                file_ref
                for basis_id in basis_ids
                for file_ref in (basis_registry.get(basis_id, {}) or {}).get('file_refs', [])
            )
        )
        safe_key = ''.join(ch if ch.isalnum() else '_' for ch in profile_id.upper())
        entries.append(
            {
                'datasetKey': f'basis.{profile_id}',
                'datasetIdPlaceholder': f'__DATASET_{safe_key}__',
                'displayName': f"{doc_type_labels.get(profile_id, profile_id)} 依据数据集",
                'profileId': profile_id,
                'documentTypes': [doc_type for doc_type in doc_type_labels.keys() if doc_type == profile_id],
                'packIds': pack_ids,
                'basisIds': basis_ids,
                'basisFiles': basis_files,
            }
        )

    return {
        'version': 1,
        'generatedAt': datetime.now(timezone.utc).isoformat(),
        'entries': entries,
    }


def main() -> int:
    builder = EvidenceBuilder()
    templates = [json.loads(path.read_text(encoding='utf-8')) for path in sorted(TEMPLATE_DIR.glob('*.json'))]
    module_bindings = {key: binding.model_dump(mode='json') for key, binding in REVIEW_MODULE_BINDINGS.items()}

    snapshot = {
        'module_bindings': module_bindings,
        'module_titles': module_titles(),
        'doc_type_labels': _DOC_TYPE_LABELS,
        'template_manifest': templates,
        'profile_mapping': load_yaml('profile_mapping.yaml'),
        'pack_registry': load_yaml('pack_registry.yaml'),
        'rule_pack_registry': load_yaml('rule_pack_registry.yaml'),
        'basis_registry': load_yaml('basis_registry.yaml'),
        'evidence_titles': builder._titles,
        'evidence_finding_types': {k: v.value for k, v in builder._finding_types.items()},
        'evidence_manual_review_reasons': builder._manual_review_reasons,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'migration_mode': 'workflow+workflow-tools',
    }

    write_both('module_bindings.json', snapshot['module_bindings'])
    write_both('module_titles.json', snapshot['module_titles'])
    write_both('doc_type_labels.json', snapshot['doc_type_labels'])
    write_both('template_manifest.json', snapshot['template_manifest'])
    write_both('profile_mapping.json', snapshot['profile_mapping'])
    write_both('pack_registry.json', snapshot['pack_registry'])
    write_both('rule_pack_registry.json', snapshot['rule_pack_registry'])
    write_both('basis_registry.json', snapshot['basis_registry'])
    write_both('evidence_titles.json', snapshot['evidence_titles'])
    write_both('evidence_finding_types.json', snapshot['evidence_finding_types'])
    write_both('evidence_manual_review_reasons.json', snapshot['evidence_manual_review_reasons'])
    write_json(GOVERNANCE_OUTPUT_DIR, 'governance_snapshot.json', snapshot)
    write_json(GOVERNANCE_OUTPUT_DIR, 'dataset_manifest.json', build_dataset_manifest(snapshot))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
