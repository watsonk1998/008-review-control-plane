from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_cases(root: str | Path) -> list[dict[str, Any]]:
    base = Path(root)
    cases: list[dict[str, Any]] = []
    for metadata_path in sorted(base.rglob('metadata.json')):
        metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
        issue_path = metadata_path.with_name('ground_truth_issues.json')
        visibility_path = metadata_path.with_name('ground_truth_visibility.json')
        metadata['groundTruthIssues'] = json.loads(issue_path.read_text(encoding='utf-8')) if issue_path.exists() else {}
        metadata['groundTruthVisibility'] = json.loads(visibility_path.read_text(encoding='utf-8')) if visibility_path.exists() else {}
        metadata['caseDir'] = str(metadata_path.parent)
        cases.append(metadata)
    return cases
