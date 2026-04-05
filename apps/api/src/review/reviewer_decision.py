from __future__ import annotations

from datetime import datetime, timezone

from src.domain.models import (
    ReviewPreparationAsset,
    ReviewPreparationAttachmentRecord,
    ReviewPreparationIssueRecord,
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
    issue_ids = _extract_issue_ids(task)
    attachment_ids = _extract_attachment_ids(task)
    eligible_issue_ids = [item.issueId for item in decision.issues if item.state == 'confirmed']
    rejected_issue_ids = [item.issueId for item in decision.issues if item.state == 'dismissed']
    deferred_issue_ids = [item.issueId for item in decision.issues if item.state in {'pending', 'needs_attachment'}]
    eligible_attachment_ids = [item.attachmentId for item in decision.attachments if item.state == 'dismissed']
    deferred_attachment_ids = [
        item.attachmentId for item in decision.attachments if item.state in {'pending', 'needs_attachment'}
    ]
    blocking_reasons: list[str] = []
    result = task.result or {}
    visibility = result.get('visibility', {}) if isinstance(result, dict) else {}
    if visibility.get('manualReviewNeeded'):
        blocking_reasons.append('visibility_manual_review_required')
    if deferred_issue_ids:
        blocking_reasons.append('pending_issue_review')
    if deferred_attachment_ids:
        blocking_reasons.append('pending_attachment_review')
    if not decision.note:
        blocking_reasons.append('missing_reviewer_note')
    ready_for_promotion = (
        bool(issue_ids or attachment_ids)
        and not deferred_issue_ids
        and not deferred_attachment_ids
        and bool(decision.note)
    )
    return ReviewPreparationSummary(
        truthTier='internal_reviewed_preparation',
        readyForPromotion=ready_for_promotion,
        blockingReasons=list(dict.fromkeys(blocking_reasons)),
        eligibleIssueIds=eligible_issue_ids,
        deferredIssueIds=deferred_issue_ids,
        rejectedIssueIds=rejected_issue_ids,
        eligibleAttachmentIds=eligible_attachment_ids,
        deferredAttachmentIds=deferred_attachment_ids,
        disclaimer='该对象仅表示 runtime reviewer decision 对 internal-reviewed preparation 的承接状态，不构成 reviewed truth。',
    )


def build_review_preparation_asset(task: TaskRecord) -> ReviewPreparationAsset:
    decision = resolve_reviewer_decision(task)
    summary = build_review_preparation_summary(task)
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
    artifact_index = result.get('artifactIndex', []) if isinstance(result.get('artifactIndex'), list) else []
    artifact_names = [
        str(item.get('name'))
        for item in artifact_index
        if isinstance(item, dict) and item.get('name')
    ]
    issue_records = []
    for item in decision.issues:
        issue = issue_map.get(item.issueId, {})
        issue_records.append(
            ReviewPreparationIssueRecord(
                issueId=item.issueId,
                state=item.state,
                note=item.note,
                issueKind=issue.get('issueKind'),
                applicabilityState=issue.get('applicabilityState'),
                manualReviewNeeded=bool(issue.get('manualReviewNeeded', False)),
                manualReviewReason=issue.get('manualReviewReason'),
                evidenceMissing=bool(issue.get('evidenceMissing', False)),
                missingFactKeys=[str(value) for value in issue.get('missingFactKeys', []) if value],
                blockingReasons=[str(value) for value in issue.get('blockingReasons', []) if value],
            )
        )
    attachment_records = []
    for item in decision.attachments:
        attachment = attachment_map.get(item.attachmentId, {})
        attachment_records.append(
            ReviewPreparationAttachmentRecord(
                attachmentId=item.attachmentId,
                state=item.state,
                note=item.note,
                visibility=attachment.get('visibility'),
                parseState=attachment.get('parseState'),
                manualReviewNeeded=bool(attachment.get('manualReviewNeeded', False)),
                reason=attachment.get('reason'),
            )
        )
    return ReviewPreparationAsset(
        taskId=task.id,
        documentType=task.documentType,
        sourceDocumentRef=task.sourceDocumentRef,
        reviewerDecisionUpdatedAt=decision.updatedAt,
        readyForPromotion=summary.readyForPromotion,
        blockingReasons=summary.blockingReasons,
        issueDecisions=issue_records,
        attachmentDecisions=attachment_records,
        provenance={
            'taskId': task.id,
            'taskType': task.taskType,
            'resultArtifactNames': artifact_names,
            'resultArtifactPrimary': _artifact_name_by_primary(artifact_index),
            'usesRuntimeReviewerDecision': True,
            'usesRuntimeStructuredReviewResult': True,
        },
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
