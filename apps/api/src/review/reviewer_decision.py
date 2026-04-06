from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from src.domain.models import (
    ReviewPreparationAsset,
    ReviewPreparationAttachmentRecord,
    ReviewPreparationIssueRecord,
    ReviewPreparationProvenance,
    ReviewPreparationSummary,
    ReviewerAttachmentDecision,
    ReviewerDecision,
    ReviewerDecisionUpdateRequest,
    ReviewerIssueDecision,
    TaskRecord,
)


def build_default_reviewer_decision(task: TaskRecord) -> ReviewerDecision:
    issue_ids = _extract_issue_ids(task)
    attachment_ids = _extract_attachment_ids(task)
    return ReviewerDecision(
        taskState='pending',
        issues=[ReviewerIssueDecision(issueId=issue_id) for issue_id in issue_ids],
        attachments=[ReviewerAttachmentDecision(attachmentId=attachment_id) for attachment_id in attachment_ids],
    )


def resolve_reviewer_decision(task: TaskRecord) -> ReviewerDecision:
    decision = task.reviewerDecision or build_default_reviewer_decision(task)
    return _normalize_reviewer_decision(task, decision, touch_updated_at=False, strict=False)


def build_review_preparation_summary(task: TaskRecord) -> ReviewPreparationSummary:
    decision = resolve_reviewer_decision(task)
    preparation_state = _collect_review_preparation_state(task, decision)
    provenance = _resolve_review_preparation_provenance(task)
    return ReviewPreparationSummary(
        truthTier='internal_reviewed_preparation',
        readyForPromotion=preparation_state['readyForPromotion'],
        blockingReasons=preparation_state['blockingReasons'],
        eligibleIssueIds=preparation_state['eligibleIssueIds'],
        deferredIssueIds=preparation_state['deferredIssueIds'],
        rejectedIssueIds=preparation_state['rejectedIssueIds'],
        eligibleAttachmentIds=preparation_state['eligibleAttachmentIds'],
        deferredAttachmentIds=preparation_state['deferredAttachmentIds'],
        rejectedAttachmentIds=preparation_state['rejectedAttachmentIds'],
        issueBlockingReasons=preparation_state['issueBlockingReasons'],
        attachmentBlockingReasons=preparation_state['attachmentBlockingReasons'],
        provenance=provenance,
        disclaimer='该对象仅表示 runtime reviewer decision 对 internal-reviewed preparation 的承接状态，不构成 reviewed truth。',
    )


def build_review_preparation_asset(task: TaskRecord) -> ReviewPreparationAsset:
    decision = resolve_reviewer_decision(task)
    preparation_state = _collect_review_preparation_state(task, decision)
    summary = build_review_preparation_summary(task)
    result = task.result if isinstance(task.result, dict) else {}
    artifact_index = result.get('artifactIndex', []) if isinstance(result.get('artifactIndex'), list) else []
    artifact_names = [
        str(item.get('name'))
        for item in artifact_index
        if isinstance(item, dict) and item.get('name')
    ]
    return ReviewPreparationAsset(
        taskId=task.id,
        documentType=task.documentType,
        sourceDocumentRef=task.sourceDocumentRef,
        reviewerDecisionUpdatedAt=decision.updatedAt,
        readyForPromotion=preparation_state['readyForPromotion'],
        blockingReasons=preparation_state['blockingReasons'],
        issueDecisions=preparation_state['issueRecords'],
        attachmentDecisions=preparation_state['attachmentRecords'],
        provenance=summary.provenance.model_copy(
            update={
                'taskId': task.id,
                'taskType': task.taskType,
                'resultArtifactNames': artifact_names,
                'resultArtifactPrimary': _artifact_name_by_primary(artifact_index),
                'usesRuntimeReviewerDecision': True,
                'usesRuntimeStructuredReviewResult': True,
            }
        ),
        disclaimer='该对象用于 internal-reviewed preparation 承接；它保留 provenance，但不构成 reviewed truth。',
    )


def merge_reviewer_decision(task: TaskRecord, payload: ReviewerDecisionUpdateRequest) -> ReviewerDecision:
    return _normalize_reviewer_decision(task, payload, touch_updated_at=True, strict=True)


def _normalize_reviewer_decision(task: TaskRecord, decision_like, *, touch_updated_at: bool, strict: bool) -> ReviewerDecision:
    normalized = ReviewerDecision.model_validate(decision_like)
    issue_ids = _extract_issue_ids(task)
    attachment_ids = _extract_attachment_ids(task)

    issue_map = {item.issueId: item for item in normalized.issues}
    attachment_map = {item.attachmentId: item for item in normalized.attachments}

    unknown_issue_ids = sorted(set(issue_map) - set(issue_ids))
    unknown_attachment_ids = sorted(set(attachment_map) - set(attachment_ids))
    if strict and unknown_issue_ids:
        raise ValueError(f'Unknown reviewer decision issue ids: {", ".join(unknown_issue_ids)}')
    if strict and unknown_attachment_ids:
        raise ValueError(f'Unknown reviewer decision attachment ids: {", ".join(unknown_attachment_ids)}')

    issues = [
        issue_map.get(issue_id, ReviewerIssueDecision(issueId=issue_id))
        for issue_id in issue_ids
    ]
    attachments = [
        attachment_map.get(attachment_id, ReviewerAttachmentDecision(attachmentId=attachment_id))
        for attachment_id in attachment_ids
    ]
    task_state = _derive_task_state(issues, attachments)

    return ReviewerDecision(
        taskState=task_state,
        note=normalized.note,
        issues=issues,
        attachments=attachments,
        updatedAt=datetime.now(timezone.utc) if touch_updated_at else normalized.updatedAt,
    )


def _collect_review_preparation_state(task: TaskRecord, decision: ReviewerDecision) -> dict[str, object]:
    result = task.result if isinstance(task.result, dict) else {}
    issue_map = {
        str(item.get('id')): item
        for item in result.get('issues', [])
        if isinstance(item, dict) and item.get('id')
    }
    matrices = result.get('matrices', {}) if isinstance(result.get('matrices'), dict) else {}
    attachment_map = {
        str(item.get('id')): item
        for item in matrices.get('attachmentVisibility', [])
        if isinstance(item, dict) and item.get('id')
    }

    issue_records: list[ReviewPreparationIssueRecord] = []
    for item in decision.issues:
        issue = issue_map.get(item.issueId, {})
        disposition, promotion_blocking_reasons = _issue_review_preparation_state(item, issue)
        issue_records.append(
            ReviewPreparationIssueRecord(
                issueId=item.issueId,
                disposition=disposition,
                state=item.state,
                note=item.note,
                issueKind=issue.get('issueKind'),
                applicabilityState=issue.get('applicabilityState'),
                manualReviewNeeded=bool(issue.get('manualReviewNeeded', False)),
                manualReviewReason=issue.get('manualReviewReason'),
                evidenceMissing=bool(issue.get('evidenceMissing', False)),
                missingFactKeys=[str(value) for value in issue.get('missingFactKeys', []) if value],
                blockingReasons=[str(value) for value in issue.get('blockingReasons', []) if value],
                promotionBlockingReasons=promotion_blocking_reasons,
            )
        )

    attachment_records: list[ReviewPreparationAttachmentRecord] = []
    for item in decision.attachments:
        attachment = attachment_map.get(item.attachmentId, {})
        disposition, promotion_blocking_reasons = _attachment_review_preparation_state(item, attachment)
        attachment_records.append(
            ReviewPreparationAttachmentRecord(
                attachmentId=item.attachmentId,
                disposition=disposition,
                state=item.state,
                note=item.note,
                visibility=attachment.get('visibility'),
                parseState=attachment.get('parseState'),
                manualReviewNeeded=bool(attachment.get('manualReviewNeeded', False)),
                reason=attachment.get('reason'),
                promotionBlockingReasons=promotion_blocking_reasons,
            )
        )

    blocking_reasons: list[str] = []
    visibility = result.get('visibility', {}) if isinstance(result, dict) else {}
    if visibility.get('manualReviewNeeded'):
        blocking_reasons.append('visibility_manual_review_required')
    if not decision.note:
        blocking_reasons.append('missing_reviewer_note')
    blocking_reasons.extend(
        reason
        for record in issue_records
        for reason in record.promotionBlockingReasons
    )
    blocking_reasons.extend(
        reason
        for record in attachment_records
        for reason in record.promotionBlockingReasons
    )

    issue_blocking_reasons = {
        record.issueId: list(record.promotionBlockingReasons)
        for record in issue_records
    }
    attachment_blocking_reasons = {
        record.attachmentId: list(record.promotionBlockingReasons)
        for record in attachment_records
    }

    return {
        'readyForPromotion': bool(issue_records or attachment_records) and not blocking_reasons,
        'blockingReasons': list(dict.fromkeys(blocking_reasons)),
        'eligibleIssueIds': [record.issueId for record in issue_records if record.disposition == 'eligible'],
        'deferredIssueIds': [record.issueId for record in issue_records if record.disposition == 'deferred'],
        'rejectedIssueIds': [record.issueId for record in issue_records if record.disposition == 'rejected'],
        'eligibleAttachmentIds': [record.attachmentId for record in attachment_records if record.disposition == 'eligible'],
        'deferredAttachmentIds': [record.attachmentId for record in attachment_records if record.disposition == 'deferred'],
        'rejectedAttachmentIds': [record.attachmentId for record in attachment_records if record.disposition == 'rejected'],
        'issueBlockingReasons': issue_blocking_reasons,
        'attachmentBlockingReasons': attachment_blocking_reasons,
        'issueRecords': issue_records,
        'attachmentRecords': attachment_records,
    }


def _derive_task_state(
    issues: list[ReviewerIssueDecision],
    attachments: list[ReviewerAttachmentDecision],
) -> str:
    if any(item.state == 'confirmed' for item in issues):
        return 'rejected'
    if any(item.state == 'needs_attachment' for item in [*issues, *attachments]):
        return 'needs_attachment'
    if issues or attachments:
        if all(item.state != 'pending' for item in [*issues, *attachments]):
            return 'accepted'
    return 'pending'


def _issue_review_preparation_state(decision: ReviewerIssueDecision, issue: dict) -> tuple[str, list[str]]:
    if decision.state == 'dismissed':
        return 'rejected', []
    if decision.state == 'pending':
        return 'deferred', ['pending_issue_review']
    if decision.state == 'needs_attachment':
        return 'deferred', ['pending_issue_review', 'issue_requires_attachment_review']

    blocking_reasons: list[str] = []
    if not issue:
        blocking_reasons.append('issue_result_unavailable')
    if issue.get('issueKind') == 'visibility_gap':
        blocking_reasons.append('issue_not_promotable_visibility_gap')
    if issue.get('issueKind') == 'evidence_gap':
        blocking_reasons.append('issue_not_promotable_evidence_gap')
    if issue.get('applicabilityState') == 'blocked_by_visibility':
        blocking_reasons.append('issue_not_promotable_blocked_by_visibility')
    if issue.get('applicabilityState') == 'blocked_by_missing_fact':
        blocking_reasons.append('issue_not_promotable_blocked_by_missing_fact')
    if bool(issue.get('manualReviewNeeded', False)):
        blocking_reasons.append('issue_not_promotable_manual_review')
    if bool(issue.get('evidenceMissing', False)):
        blocking_reasons.append('issue_not_promotable_evidence_missing')
    if blocking_reasons:
        return 'deferred', list(dict.fromkeys(blocking_reasons))
    return 'eligible', []


def _attachment_review_preparation_state(decision: ReviewerAttachmentDecision, attachment: dict) -> tuple[str, list[str]]:
    if decision.state == 'dismissed':
        return 'eligible', []
    if decision.state == 'confirmed':
        return 'rejected', ['rejected_attachment_promotion']
    if decision.state == 'needs_attachment':
        return 'deferred', ['pending_attachment_review', 'attachment_requires_attachment_review']
    if not attachment:
        return 'deferred', ['pending_attachment_review', 'attachment_result_unavailable']
    return 'deferred', ['pending_attachment_review']


def _extract_issue_ids(task: TaskRecord) -> list[str]:
    result = task.result or {}
    issues = result.get('issues', []) if isinstance(result, dict) else []
    ids = [str(item.get('id')) for item in issues if isinstance(item, dict) and item.get('id')]
    return list(dict.fromkeys(ids))


def _extract_attachment_ids(task: TaskRecord) -> list[str]:
    result = task.result or {}
    matrices = result.get('matrices', {}) if isinstance(result, dict) else {}
    items = matrices.get('attachmentVisibility', []) if isinstance(matrices, dict) else []
    ids = [str(item.get('id')) for item in items if isinstance(item, dict) and item.get('id')]
    return list(dict.fromkeys(ids))


def _artifact_name_by_primary(artifact_index: list[dict]) -> str | None:
    for item in artifact_index:
        if isinstance(item, dict) and item.get('primary') and item.get('name'):
            return str(item.get('name'))
    for item in artifact_index:
        if isinstance(item, dict) and item.get('name') == 'structured-review-result':
            return str(item.get('name'))
    return None


def _resolve_review_preparation_provenance(task: TaskRecord) -> ReviewPreparationProvenance:
    metadata = _find_review_eval_case_metadata(task)
    if metadata is None:
        return ReviewPreparationProvenance()
    case_version = metadata.get('caseVersion')
    return ReviewPreparationProvenance(
        sourceTier=_source_tier_from_case_version(case_version),
        caseId=metadata.get('caseId'),
        caseVersion=case_version,
        labelStatus=metadata.get('labelStatus'),
        truthLevel=metadata.get('truthLevel'),
        reviewStatus=metadata.get('reviewStatus'),
        inferred=bool(metadata.get('inferred', False)),
    )


def _find_review_eval_case_metadata(task: TaskRecord) -> dict[str, str | bool] | None:
    candidates = []
    if task.fixtureId:
        candidates.append(('fixture_id', str(task.fixtureId), False))
    if task.sourceDocumentRef and task.sourceDocumentRef.fixtureId:
        candidates.append(('source_fixture_id', str(task.sourceDocumentRef.fixtureId), False))

    index = _review_eval_case_index()
    for lookup_type, value, inferred in candidates:
        matched = index.get((lookup_type, value))
        if matched is None:
            continue
        return {
            **matched,
            'inferred': inferred or bool(matched.get('inferred', False)),
        }
    return None


@lru_cache(maxsize=1)
def _review_eval_case_index() -> dict[tuple[str, str], dict[str, str | bool]]:
    repo_root = Path(__file__).resolve().parents[4]
    review_eval_root = repo_root / 'fixtures' / 'review_eval'
    index: dict[tuple[str, str], dict[str, str | bool]] = {}
    if not review_eval_root.exists():
        return index

    for path in review_eval_root.rglob('case_metadata.json'):
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            continue
        case_record = {
            'caseId': str(payload.get('case_id') or path.parent.parent.name),
            'caseVersion': str(payload.get('case_version') or ''),
            'labelStatus': str(payload.get('label_status') or '') or None,
            'truthLevel': str(payload.get('truth_level') or '') or None,
            'reviewStatus': str(payload.get('review_status') or '') or None,
            'inferred': False,
        }
        case_id = case_record['caseId']
        if case_id:
            index[('fixture_id', case_id)] = case_record
            index[('source_fixture_id', case_id)] = case_record
        for source_path in payload.get('source_files', []) or []:
            normalized = _normalize_case_source_path(path.parent, str(source_path))
            if normalized:
                index[('source_path', normalized)] = case_record
    return index


def _source_tier_from_case_version(case_version: str | None) -> str:
    if not case_version:
        return 'runtime_only'
    if case_version == 'v0.1.0-gemini-seed':
        return 'seed'
    if case_version == 'v0.1.0-bootstrap-seed':
        return 'bootstrap_seed'
    if case_version == 'v0.1.0-ci-stage-gate':
        return 'ci_stage_gate'
    if case_version == 'v0.2.0-internal-reviewed':
        return 'internal_reviewed'
    if case_version == 'v1.0.0-expert-golden':
        return 'expert_golden'
    return 'runtime_only'


def _normalize_case_source_path(case_dir: Path, raw_path: str) -> str | None:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return _normalize_path(candidate)
    for root in [case_dir, *case_dir.parents]:
        resolved = (root / raw_path).resolve()
        if resolved.exists():
            return _normalize_path(resolved)
    return _normalize_path(case_dir / raw_path)


def _normalize_path(path: str | Path) -> str:
    return str(Path(path).expanduser().resolve())
