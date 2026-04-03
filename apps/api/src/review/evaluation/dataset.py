from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_cases(root: str | Path, *, ci_only: bool = False) -> list[dict[str, Any]]:
    base = Path(root)
    cases: list[dict[str, Any]] = []
    for metadata_path in sorted(base.rglob('metadata.json')):
        metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
        issue_path = metadata_path.with_name('ground_truth_issues.json')
        visibility_path = metadata_path.with_name('ground_truth_visibility.json')
        metadata['groundTruthIssues'] = json.loads(issue_path.read_text(encoding='utf-8')) if issue_path.exists() else {'issues': []}
        metadata['groundTruthVisibility'] = json.loads(visibility_path.read_text(encoding='utf-8')) if visibility_path.exists() else {'attachments': {}}
        metadata['caseDir'] = str(metadata_path.parent)
        source_path = metadata.get('sourcePath')
        if source_path:
            resolved_source = Path(source_path)
            if not resolved_source.is_absolute():
                resolved_source = (metadata_path.parent / source_path).resolve()
            metadata['sourcePath'] = str(resolved_source)
        if ci_only and not metadata.get('ciEnabled', False):
            continue
        cases.append(metadata)
    return cases
