from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config.settings import get_settings
from src.domain.models import (
    CreateReviewTaskRequest,
    CreateTaskRequest,
    ReviewTaskDocuments,
    ReviewTaskError,
    ReviewTaskExportLinks,
    ReviewTaskModuleResult,
    ReviewTaskResultMetadata,
    ReviewTaskResultResponse,
    ReviewTaskResultSummary,
    ReviewTaskSseArtifact,
    ReviewTaskSseEvent,
    ReviewTaskStatusResponse,
    SourceDocumentRef,
    TaskArtifact,
    TaskEvent,
    TaskRecord,
)

MODULE_TEMPLATE_MAP: dict[str, list[str]] = {
    'structure_completeness': ['structured_review_primary_worker'],
    'parameter_consistency': ['execution_risk_reviewer'],
    'legality_compliance': ['policy_compliance_reviewer'],
    'execution_continuity': ['execution_risk_reviewer'],
    'evidence_validation': ['visibility_gap_reviewer'],
}

MODULE_TITLES = {
    'structure_completeness': '结构完整性',
    'parameter_consistency': '参数一致性',
    'legality_compliance': '合法合规性',
    'execution_continuity': '执行连续性',
    'evidence_validation': '证据校验',
}

RISK_ORDER = {'info': 0, 'low': 1, 'medium': 2, 'high': 3}


def resolve_uploaded_file(file_id: str) -> SourceDocumentRef:
    upload_dir = get_settings().uploads_dir / file_id
    if not upload_dir.exists() or not upload_dir.is_dir():
        raise FileNotFoundError(file_id)
    files = [path for path in upload_dir.iterdir() if path.is_file()]
    if len(files) != 1:
        raise FileNotFoundError(file_id)
    path = files[0]
    return SourceDocumentRef(
        refId=file_id,
        sourceType='upload',
        fileName=path.name,
        fileType=path.suffix.lstrip('.').lower(),
        storagePath=str(path),
        displayName=path.name,
        uploadedAt=datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc),
    )


def _ref_to_bridge_file(ref: SourceDocumentRef) -> dict[str, Any]:
    return {
        'path': ref.storagePath,
        'type': ref.fileType,
        'name': ref.fileName,
        'ref_id': ref.refId,
        'source_type': ref.sourceType,
        'display_name': ref.displayName,
    }


def _merge_unique(items: list[str]) -> list[str]:
    deduped: list[str] = []
    for item in items:
        if item and item not in deduped:
            deduped.append(item)
    return deduped


def _module_names_to_template_ids(module_names: list[str]) -> list[str]:
    template_ids: list[str] = []
    for module_name in module_names:
        template_ids.extend(MODULE_TEMPLATE_MAP.get(module_name, []))
    return _merge_unique(template_ids)


def _build_generated_query(request: CreateReviewTaskRequest) -> str:
    focus = '；'.join(request.review_intent.focus_requirements[:3])
    module_text = '、'.join(request.review_intent.enabled_modules[:3]) or '结构化正式审查'
    base = f"请对{request.classification.l2}执行正式结构化审查，重点覆盖{module_text}。"
    if focus:
        base += f" 重点要求：{focus}。"
    return base


def compile_create_task_request(request: CreateReviewTaskRequest) -> tuple[CreateTaskRequest, dict[str, Any]]:
    target_ref = resolve_uploaded_file(request.documents.target_file_ids[0])
    basis_refs = [resolve_uploaded_file(file_id) for file_id in request.documents.basis_file_ids]
    context_refs = [resolve_uploaded_file(file_id) for file_id in request.documents.project_context_file_ids]

    enabled_agents = _merge_unique(
        _module_names_to_template_ids(request.review_intent.enabled_modules)
        + list(request.builtin_asset_selections.template_ids)
    )
    disabled_agents = _merge_unique(
        _module_names_to_template_ids(request.review_intent.disabled_modules)
    )

    internal_request = CreateTaskRequest(
        taskType='structured_review',
        capabilityMode='auto',
        query=_build_generated_query(request),
        sourceDocumentRef=target_ref,
        useWeb=False,
        debug=request.metadata.debug,
        sourceUrls=[],
        documentType=request.classification.l2,
        disciplineTags=list(request.classification.l3),
        strictMode=True,
        policyPackIds=list(request.builtin_asset_selections.rule_pack_ids),
    )

    plan_seed = {
        'reviewProfile': {
            'authority': 'frontend_contract_freeze',
            'documentTypeHint': request.classification.l2,
            'disciplineTagHints': list(request.classification.l3),
            'policyPackHints': list(request.builtin_asset_selections.rule_pack_ids),
        },
        'hermesInput': {
            'basisFiles': [_ref_to_bridge_file(ref) for ref in basis_refs],
            'contextFiles': [_ref_to_bridge_file(ref) for ref in context_refs],
            'focusRequirements': list(request.review_intent.focus_requirements),
            'enabledAgents': enabled_agents,
            'disabledAgents': disabled_agents,
            'frontendSelections': {
                'classification': request.classification.model_dump(mode='json'),
                'documents': request.documents.model_dump(mode='json'),
                'builtin_asset_selections': request.builtin_asset_selections.model_dump(mode='json'),
                'review_intent': request.review_intent.model_dump(mode='json'),
                'metadata': request.metadata.model_dump(mode='json'),
            },
            'standardIds': list(request.builtin_asset_selections.standard_ids),
        },
    }
    return internal_request, plan_seed


def map_internal_status(task: TaskRecord) -> str:
    if task.status == 'created':
        return 'created'
    if task.status == 'planned':
        return 'compiling'
    if task.status == 'running':
        return 'running'
    if task.status == 'succeeded':
        return 'completed'
    if task.status == 'partial':
        return 'degraded'
    return 'failed'


def map_internal_stage(task: TaskRecord, events: list[TaskEvent]) -> str:
    if task.status == 'created':
        return 'review_brief_compiling'
    if task.status in {'succeeded', 'failed', 'partial'}:
        return 'done'
    latest = events[-1] if events else None
    stage = latest.stage if latest else ''
    if stage == 'planning':
        return 'review_brief_compiling'
    if stage == 'dispatch':
        return 'assets_loading'
    if stage in {'parse', 'extract', 'rules', 'evidence', 'explain', 'report', 'hermes_controller'}:
        return 'modules_running'
    if stage == 'finalize':
        return 'report_assembling'
    if stage in {'document', 'retrieval', 'analysis', 'research'}:
        return 'assets_loading'
    return 'modules_running' if task.status == 'running' else 'review_brief_compiling'


def build_review_task_status(task: TaskRecord, events: list[TaskEvent]) -> ReviewTaskStatusResponse:
    latest = events[-1] if events else None
    status = map_internal_status(task)
    report_id = task.id if task.status in {'succeeded', 'partial'} and isinstance(task.result, dict) else None
    error = None
    if task.error:
        error = ReviewTaskError(code='task_failed', message=str(task.error.get('message') or 'Task failed'))
    return ReviewTaskStatusResponse(
        task_id=task.id,
        status=status,
        progress_stage=map_internal_stage(task, events),
        progress_message=latest.message if latest else 'Task created',
        created_at=task.createdAt,
        updated_at=task.updatedAt,
        report_id=report_id,
        error=error,
        degraded=status == 'degraded',
    )


def _artifact_payload(artifact: TaskArtifact) -> ReviewTaskSseArtifact:
    return ReviewTaskSseArtifact(
        file_name=artifact.fileName,
        download_url=artifact.downloadUrl,
        category=artifact.category,
        stage=artifact.stage,
    )


def map_task_event_to_sse(task: TaskRecord, event: TaskEvent) -> ReviewTaskSseEvent:
    status = map_internal_status(task)
    return ReviewTaskSseEvent(
        event='progress',
        task_id=task.id,
        stage=map_internal_stage(task, [event]),
        message=event.message,
        timestamp=event.timestamp,
        status=status if status in {'created', 'compiling', 'running', 'assembling'} else 'running',
        payload={
            'capability': event.capability,
            'internal_stage': event.stage,
            'internal_status': event.status,
        },
    )


def build_task_created_event(task: TaskRecord) -> ReviewTaskSseEvent:
    return ReviewTaskSseEvent(
        event='task_created',
        task_id=task.id,
        stage='review_brief_compiling',
        message='Review task created',
        timestamp=task.createdAt,
        status='created',
        payload={'report_id': None},
    )


def build_artifact_ready_event(task: TaskRecord, artifact: TaskArtifact) -> ReviewTaskSseEvent:
    return ReviewTaskSseEvent(
        event='artifact_ready',
        task_id=task.id,
        stage=map_internal_stage(task, []),
        message=f'Artifact ready: {artifact.fileName}',
        timestamp=datetime.now(timezone.utc),
        status=map_internal_status(task),
        artifact=_artifact_payload(artifact),
    )


def build_terminal_event(task: TaskRecord) -> ReviewTaskSseEvent:
    status = map_internal_status(task)
    is_failed = status == 'failed'
    return ReviewTaskSseEvent(
        event='failed' if is_failed else 'completed',
        task_id=task.id,
        stage='done',
        message='Task failed' if is_failed else 'Task completed',
        timestamp=task.updatedAt,
        status=status,
        payload={'degraded': status == 'degraded', 'report_id': task.id if status in {'completed', 'degraded'} else None},
    )


def _build_export_links(task: TaskRecord, artifacts: list[TaskArtifact]) -> ReviewTaskExportLinks:
    links = ReviewTaskExportLinks()
    for artifact in artifacts:
        name = artifact.fileName.lower()
        if name.endswith('.md') and links.markdown is None:
            links.markdown = artifact.downloadUrl
        elif name.endswith('.pdf') and links.pdf is None:
            links.pdf = artifact.downloadUrl
        elif name.endswith('.html') and links.html is None:
            links.html = artifact.downloadUrl
    return links


def _group_issue_module(issue: dict[str, Any]) -> str:
    title = f"{issue.get('title', '')} {issue.get('summary', '')}".lower()
    if issue.get('issueKind') in {'visibility_gap', 'evidence_gap'} or issue.get('evidenceMissing') or issue.get('manualReviewNeeded'):
        return 'evidence_validation'
    if any(token in title for token in ['参数', 'capacity', '荷载', '吨', '重量', '技术参数', 'consistency']):
        return 'parameter_consistency'
    if any(token in title for token in ['停送电', '流程', '工序', '衔接', '执行', 'sequence', 'continuity']):
        return 'execution_continuity'
    if issue.get('layer') == 'L1':
        return 'structure_completeness'
    if issue.get('layer') == 'L2':
        return 'legality_compliance'
    if issue.get('layer') == 'L3':
        return 'parameter_consistency'
    return 'legality_compliance'


def _module_traceability(module_name: str, traceability: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if module_name == 'evidence_validation':
        return traceability[:5]
    return traceability[:3]


def build_review_task_result(task: TaskRecord, artifacts: list[TaskArtifact]) -> ReviewTaskResultResponse:
    if not isinstance(task.result, dict):
        raise ValueError('Task result is not available')
    result = dict(task.result)
    issues = list(result.get('issues') or [])
    summary = dict(result.get('summary') or {})
    final_packet = dict(result.get('finalReportPacket') or {})
    traceability = list(result.get('traceability') or final_packet.get('traceability') or [])
    selected = (((task.plan or {}).get('hermesInput') or {}).get('frontendSelections') or {})
    review_intent = dict(selected.get('review_intent') or {})
    disabled_modules = set(review_intent.get('disabled_modules') or [])
    enabled_modules = set(review_intent.get('enabled_modules') or [])

    modules: dict[str, ReviewTaskModuleResult] = {}
    for module_name, title in MODULE_TITLES.items():
        module_findings = [issue for issue in issues if _group_issue_module(issue) == module_name]
        severity_summary = {
            level: sum(1 for issue in module_findings if issue.get('severity') == level)
            for level in ['high', 'medium', 'low', 'info']
            if any(issue.get('severity') == level for issue in module_findings)
        }
        if module_name in disabled_modules:
            status = 'not_applicable'
        elif enabled_modules and module_name not in enabled_modules and not module_findings:
            status = 'not_applicable'
        elif module_findings:
            status = 'available'
        else:
            status = 'partial'
        modules[module_name] = ReviewTaskModuleResult(
            title=title,
            findings=module_findings,
            severity_summary=severity_summary,
            traceability_summary=_module_traceability(module_name, traceability),
            status=status,
        )

    key_findings = list(final_packet.get('key_findings') or [])
    if not key_findings:
        key_findings = sorted(issues, key=lambda item: RISK_ORDER.get(str(item.get('severity')), 0), reverse=True)[:5]

    recommendations = _merge_unique([
        recommendation
        for issue in issues
        for recommendation in issue.get('recommendation', [])
        if isinstance(recommendation, str) and recommendation.strip()
    ])

    severity_counts = {
        level: sum(1 for issue in issues if issue.get('severity') == level)
        for level in ['high', 'medium', 'low']
    }
    if severity_counts['high'] > 0:
        risk_level = 'high'
    elif severity_counts['medium'] > 0:
        risk_level = 'medium'
    elif severity_counts['low'] > 0:
        risk_level = 'low'
    else:
        risk_level = 'unknown'

    generated_at = task.updatedAt
    return ReviewTaskResultResponse(
        task_id=task.id,
        status=map_internal_status(task),
        report_id=task.id,
        summary=ReviewTaskResultSummary(
            overall_conclusion=summary.get('overallConclusion') or final_packet.get('executive_summary') or result.get('finalAnswer') or '',
            risk_level=risk_level,
            key_counts={
                'issues': len(issues),
                'manual_review_needed': sum(1 for issue in issues if issue.get('manualReviewNeeded')),
            },
            key_metrics={
                'high': severity_counts['high'],
                'medium': severity_counts['medium'],
                'low': severity_counts['low'],
            },
        ),
        modules=modules,
        key_findings=key_findings,
        recommendations=recommendations,
        export_links=_build_export_links(task, artifacts),
        metadata=ReviewTaskResultMetadata(
            report_id=task.id,
            generated_at=generated_at,
            degraded=task.status == 'partial',
            traceability_available=bool(traceability),
        ),
        raw=result,
    )
