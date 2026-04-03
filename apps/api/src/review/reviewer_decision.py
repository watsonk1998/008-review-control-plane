from __future__ import annotations

from datetime import datetime, timezone

from src.domain.models import (
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

    return ReviewerDecision(
        taskState=normalized.taskState,
        note=normalized.note,
        issues=[
            issue_map.get(issue_id, ReviewerIssueDecision(issueId=issue_id))
            for issue_id in issue_ids
        ],
        attachments=[
            attachment_map.get(attachment_id, ReviewerAttachmentDecision(attachmentId=attachment_id))
            for attachment_id in attachment_ids
        ],
        updatedAt=datetime.now(timezone.utc) if touch_updated_at else normalized.updatedAt,
    )


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
