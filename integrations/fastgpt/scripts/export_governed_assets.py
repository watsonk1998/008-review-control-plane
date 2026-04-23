#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
API_SRC = REPO_ROOT / 'apps' / 'api'
OUTPUT_DIR = REPO_ROOT / 'integrations' / 'fastgpt' / 'toolset' / 'hermesStructuredReview' / 'assets' / 'generated'

sys.path.insert(0, str(API_SRC))

from src.review.hermes.module_bindings import REVIEW_MODULE_BINDINGS, module_titles  # type: ignore
from src.review.final_report_merger import _DOC_TYPE_LABELS  # type: ignore
from src.review.evidence.evidence_builder import EvidenceBuilder  # type: ignore

CONFIG_DIR = REPO_ROOT / 'config' / 'review_basis'
TEMPLATE_DIR = API_SRC / 'src' / 'review' / 'hermes' / 'templates'

def write_json(name: str, payload):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

def load_yaml(name: str):
    return yaml.safe_load((CONFIG_DIR / name).read_text(encoding='utf-8'))

def main() -> int:
    builder = EvidenceBuilder()
    templates = [json.loads(path.read_text(encoding='utf-8')) for path in sorted(TEMPLATE_DIR.glob('*.json'))]
    module_bindings = {key: binding.model_dump(mode='json') for key, binding in REVIEW_MODULE_BINDINGS.items()}
    write_json('module_bindings.json', module_bindings)
    write_json('module_titles.json', module_titles())
    write_json('doc_type_labels.json', _DOC_TYPE_LABELS)
    write_json('template_manifest.json', templates)
    write_json('profile_mapping.json', load_yaml('profile_mapping.yaml'))
    write_json('pack_registry.json', load_yaml('pack_registry.yaml'))
    write_json('rule_pack_registry.json', load_yaml('rule_pack_registry.yaml'))
    write_json('basis_registry.json', load_yaml('basis_registry.yaml'))
    write_json('evidence_titles.json', builder._titles)
    write_json('evidence_finding_types.json', {k: v.value for k, v in builder._finding_types.items()})
    write_json('evidence_manual_review_reasons.json', builder._manual_review_reasons)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
