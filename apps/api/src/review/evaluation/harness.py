from __future__ import annotations

import json
from pathlib import Path
import sys

from src.services.document_loader import DocumentLoader
from src.review.evaluation.dataset import load_cases
from src.review.evaluation.metrics import compute_metrics
from src.review.pipeline import StructuredReviewExecutor


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


def main() -> int:
    repo_root = Path(__file__).resolve().parents[5]
    case_root = repo_root / 'fixtures' / 'review_eval'
    cases = load_cases(case_root)
    if not cases:
        print(json.dumps({'error': 'no_cases_found', 'caseRoot': str(case_root)}, ensure_ascii=False))
        return 1

    executor = StructuredReviewExecutor(document_loader=DocumentLoader(), llm_gateway=DeterministicLLM(), fast_adapter=None)
    summaries = []
    all_ok = True
    for case in cases:
        result = executor.run_sync(
            task_id=case['caseId'],
            query=case.get('query', '对该施工组织设计执行正式结构化审查'),
            source_document_path=case['sourcePath'],
            fixture_id=case.get('fixtureId'),
        )
        metrics = compute_metrics(case, result)
        passed = metrics['issue_recall'] >= 0.75 and metrics['attachment_visibility_accuracy'] >= 1.0
        all_ok = all_ok and passed
        summaries.append(
            {
                'caseId': case['caseId'],
                'passed': passed,
                'metrics': metrics,
                'summary': result.get('summary', {}),
            }
        )
    print(json.dumps({'passed': all_ok, 'cases': summaries}, ensure_ascii=False, indent=2))
    return 0 if all_ok else 1


if __name__ == '__main__':
    sys.exit(main())
