from __future__ import annotations

from datetime import datetime, timezone
import logging
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
from src.review.hermes.module_bindings import module_template_ids, module_titles, template_review_modules

MODULE_TITLES = module_titles()
logger = logging.getLogger(__name__)

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
    return _merge_unique(module_template_ids(module_names))


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

    requested_policy_pack_ids = list(request.builtin_asset_selections.policy_pack_ids)
    requested_rule_pack_ids = list(request.builtin_asset_selections.rule_pack_ids)
    if requested_rule_pack_ids and not requested_policy_pack_ids:
        logger.warning(
            "[review_task_contracts] Legacy frontend contract detected: rule_pack_ids provided without policy_pack_ids; "
            "keeping policyPackIds empty and passing rulePackIds separately."
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
        policyPackIds=requested_policy_pack_ids,
        rulePackIds=requested_rule_pack_ids,
    )

    plan_seed = {
        'reviewProfile': {
            'authority': 'frontend_contract_freeze',
            'documentTypeHint': request.classification.l2,
            'disciplineTagHints': list(request.classification.l3),
            'policyPackHints': requested_policy_pack_ids,
            'rulePackHints': requested_rule_pack_ids,
            'requestedRulePackIds': requested_rule_pack_ids,
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
    if stage in {'parse', 'extract', 'rules', 'evidence', 'explain'}:
        return 'modules_running'
    if stage in {'agent_select', 'agent_running', 'agent_done', 'hermes_controller'}:
        return 'agents_running'
    if stage == 'report':
        return 'report_assembling'
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
        error = ReviewTaskError(code='task_failed', message=str(task.error.get('message') or '任务执行失败'))
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
            'debug': event.debug or {},
            'artifact_path': event.artifactPath,
        },
    )


def build_task_created_event(task: TaskRecord) -> ReviewTaskSseEvent:
    return ReviewTaskSseEvent(
        event='task_created',
        task_id=task.id,
        stage='review_brief_compiling',
        message='审查任务已创建',
        timestamp=task.createdAt,
        status='created',
        payload={'report_id': None},
    )


def build_artifact_ready_event(task: TaskRecord, artifact: TaskArtifact) -> ReviewTaskSseEvent:
    return ReviewTaskSseEvent(
        event='artifact_ready',
        task_id=task.id,
        stage=map_internal_stage(task, []),
        message=f'报告文件已生成：{artifact.fileName}',
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
        message='任务执行失败' if is_failed else '任务已完成',
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
        if name.endswith('.pdf') and links.pdf is None:
            links.pdf = artifact.downloadUrl
        if name.endswith('.html') and links.html is None:
            links.html = artifact.downloadUrl
    return links


def _group_issue_module_fallback(issue: dict[str, Any]) -> str:
    """Legacy heuristic fallback only.

    The canonical path prefers explicit module metadata emitted by Hermes review packets,
    decision packets, and support-material annotations. This function exists only for
    orphan support issues that still lack execution metadata.
    """

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


def _first_module_name(payload: dict[str, Any] | None) -> str | None:
    if not isinstance(payload, dict):
        return None
    module_name = payload.get('module_name')
    if isinstance(module_name, str) and module_name in MODULE_TITLES:
        return module_name
    review_modules = payload.get('review_modules')
    if isinstance(review_modules, list):
        for candidate in review_modules:
            if isinstance(candidate, str) and candidate in MODULE_TITLES:
                return candidate
    template_id = payload.get('template_id') or payload.get('source_template_id') or payload.get('agent_id')
    if isinstance(template_id, str):
        for candidate in template_review_modules(template_id):
            if candidate in MODULE_TITLES:
                return candidate
    return None


def _normalize_decision_finding(finding: dict[str, Any], *, role: str) -> dict[str, Any]:
    raw_data = dict(finding.get('raw_data') or {})
    module_name = _first_module_name(raw_data)
    suggestion = finding.get('suggestion')
    return {
        'id': finding.get('id'),
        'title': finding.get('title') or '',
        'summary': finding.get('summary') or '',
        'severity': finding.get('severity') or 'info',
        'issueKind': finding.get('finding_type') or raw_data.get('decision_role') or role,
        'layer': finding.get('layer') or '',
        'manualReviewNeeded': bool(finding.get('manual_review_needed')),
        'evidenceMissing': finding.get('evidence_status') in {'evidence_gap', 'visibility_gap'},
        'findingType': finding.get('finding_type') or '',
        'recommendation': [suggestion] if isinstance(suggestion, str) and suggestion.strip() else [],
        'sourceEngine': finding.get('source_engine') or 'hermes',
        'ownership': raw_data.get('ownership') or 'hermes_decision_layer',
        'module_name': module_name,
        'review_modules': raw_data.get('review_modules') or ([module_name] if module_name else []),
        'decision_role': raw_data.get('decision_role') or role,
        'supportDerived': raw_data.get('ownership') == 'support_material',
        'traceabilityHint': raw_data.get('traceability_hint'),
    }


def _annotate_support_issue_source(issue: dict[str, Any]) -> dict[str, Any]:
    annotated = dict(issue)
    annotated.setdefault('ownership', 'support_material')
    annotated.setdefault('supportDerived', True)
    annotated.setdefault('sourceEngine', '008')
    # Force removal of any nested unstructured data to prevent protocol bleed
    annotated.pop('raw_data', None)
    annotated.pop('source_packets', None)
    return annotated


def _support_traceability_source(traceability: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{**item, 'source': item.get('source', 'support-derived')} for item in traceability]


def _decision_finding_lists(final_packet: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    key_findings = [_normalize_decision_finding(item, role='key_finding') for item in list(final_packet.get('key_findings') or [])]
    supplemental_findings = [_normalize_decision_finding(item, role='supplemental_finding') for item in list(final_packet.get('supplemental_findings') or [])]
    all_findings = [_normalize_decision_finding(item, role='all_finding') for item in list(final_packet.get('all_findings') or [])]
    return key_findings, supplemental_findings, all_findings


def _build_module_indices(
    *,
    decision_findings: list[dict[str, Any]],
    main_review_outcomes: list[dict[str, Any]],
) -> tuple[dict[str, str], dict[str, str]]:
    by_id: dict[str, str] = {}
    by_title: dict[str, str] = {}

    for finding in decision_findings:
        module_name = finding.get('module_name') or _first_module_name(finding)
        if not module_name:
            continue
        if finding.get('id'):
            by_id[str(finding['id'])] = module_name
        title = str(finding.get('title') or '').strip().lower()
        if title:
            by_title[title] = module_name

    for outcome in main_review_outcomes:
        packet = dict(outcome.get('packet') or {})
        packet_metadata = dict(packet.get('metadata') or {})
        packet_module = _first_module_name(packet_metadata)
        for finding in list(packet.get('findings') or []):
            module_name = _first_module_name(dict(finding.get('raw_data') or {})) or packet_module
            if not module_name:
                continue
            if finding.get('id'):
                by_id[str(finding['id'])] = module_name
            title = str(finding.get('title') or '').strip().lower()
            if title:
                by_title[title] = module_name

    return by_id, by_title


def _resolve_issue_module(
    issue: dict[str, Any],
    *,
    module_by_id: dict[str, str],
    module_by_title: dict[str, str],
) -> str:
    explicit = _first_module_name(issue)
    if explicit:
        return explicit
    issue_id = issue.get('id')
    if isinstance(issue_id, str) and issue_id in module_by_id:
        return module_by_id[issue_id]
    title = str(issue.get('title') or '').strip().lower()
    if title and title in module_by_title:
        return module_by_title[title]
    return _group_issue_module_fallback(issue)


def _decision_module_findings(final_packet: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    _, _, all_findings = _decision_finding_lists(final_packet)
    grouped: dict[str, list[dict[str, Any]]] = {name: [] for name in MODULE_TITLES}
    for finding in all_findings:
        module_name = finding.get('module_name')
        if not module_name or module_name not in grouped:
            continue
        grouped[module_name].append(finding)
    return grouped


def _module_order(enabled_modules: set[str], disabled_modules: set[str]) -> list[str]:
    if enabled_modules:
        return [module for module in MODULE_TITLES if module in enabled_modules and module not in disabled_modules]
    return [module for module in MODULE_TITLES if module not in disabled_modules]


def _severity_counts(findings: list[dict[str, Any]]) -> dict[str, int]:
    return {
        level: sum(1 for item in findings if item.get('severity') == level)
        for level in ['high', 'medium', 'low', 'info']
        if any(item.get('severity') == level for item in findings)
    }


def build_review_task_result(task: TaskRecord, artifacts: list[TaskArtifact], include_raw: bool = False) -> ReviewTaskResultResponse:
    if not isinstance(task.result, dict):
        raise ValueError('Task result is not available')
    result = dict(task.result)
    final_packet = dict(result.get('finalReportPacket') or {})
    hermes_controller = dict(result.get('hermesController') or {})
    main_review_outcomes = list(hermes_controller.get('mainReviewOutcomes') or [])
    support_material = {
        'structured_support_result_008': result.get('structured_support_result_008'),
        'support_summary': result.get('support_summary') or result.get('summary') or {},
        'support_issues': list(result.get('support_issues') or result.get('issues') or []),
        'support_traceability': _support_traceability_source(list(result.get('traceability') or final_packet.get('traceability') or [])),
    }
    summary = dict(support_material['support_summary'] or {})
    issues = [_annotate_support_issue_source(issue) for issue in support_material['support_issues']]
    traceability = support_material['support_traceability']
    selected = (((task.plan or {}).get('hermesInput') or {}).get('frontendSelections') or {})
    review_intent = dict(selected.get('review_intent') or {})
    disabled_modules = set(review_intent.get('disabled_modules') or [])
    enabled_modules = set(review_intent.get('enabled_modules') or [])
    key_findings, _, all_decision_findings = _decision_finding_lists(final_packet)
    visible_modules = _module_order(enabled_modules, disabled_modules)
    module_by_id, module_by_title = _build_module_indices(
        decision_findings=all_decision_findings,
        main_review_outcomes=main_review_outcomes,
    )
    grouped_decision_findings = _decision_module_findings(final_packet)

    modules: dict[str, ReviewTaskModuleResult] = {}
    covered_issue_ids = {str(item.get('id')) for item in all_decision_findings if item.get('id')}
    filtered_decision_findings = [
        finding for finding in all_decision_findings if finding.get('module_name') in visible_modules
    ]
    filtered_issues = []
    for issue in issues:
        issue_module = _resolve_issue_module(issue, module_by_id=module_by_id, module_by_title=module_by_title)
        if issue_module in visible_modules:
            filtered_issues.append({**issue, 'module_name': issue_module})

    for module_name in visible_modules:
        title = MODULE_TITLES[module_name]
        module_findings = list(grouped_decision_findings.get(module_name) or [])
        for issue in filtered_issues:
            issue_module = issue.get('module_name')
            if issue_module != module_name:
                continue
            if issue.get('id') and str(issue.get('id')) in covered_issue_ids:
                continue
            module_findings.append(issue)
        severity_summary = _severity_counts(module_findings)
        status = 'available' if module_findings else 'partial'
        modules[module_name] = ReviewTaskModuleResult(
            title=title,
            findings=module_findings,
            severity_summary=severity_summary,
            traceability_summary=_module_traceability(module_name, traceability),
            status=status,
        )

    key_findings = [finding for finding in key_findings if finding.get('module_name') in visible_modules]
    if not key_findings:
        key_findings = sorted(filtered_issues, key=lambda item: RISK_ORDER.get(str(item.get('severity')), 0), reverse=True)[:5]

    recommendations = _merge_unique([
        recommendation
        for issue in (filtered_decision_findings or filtered_issues)
        for recommendation in (
            issue.get('recommendation', [])
            if isinstance(issue.get('recommendation'), list)
            else ([issue.get('suggestion')] if isinstance(issue.get('suggestion'), str) and issue.get('suggestion') else [])
        )
        if isinstance(recommendation, str) and recommendation.strip()
    ])

    risk_source = filtered_decision_findings or filtered_issues
    severity_counts = {
        level: sum(1 for issue in risk_source if issue.get('severity') == level)
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
    final_metadata = dict(final_packet.get('metadata') or {})
    return ReviewTaskResultResponse(
        task_id=task.id,
        status=map_internal_status(task),
        report_id=task.id,
        summary=ReviewTaskResultSummary(
            overall_conclusion=final_packet.get('executive_summary') or summary.get('overallConclusion') or result.get('finalAnswer') or '',
            risk_level=risk_level,
            key_counts={
                'issues': len(risk_source),
                'manual_review_needed': sum(1 for issue in risk_source if issue.get('manualReviewNeeded') or issue.get('manual_review_needed')),
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
            assembler='HermesReviewAssembler',
            decision_owner=str(final_metadata.get('decision_owner') or 'hermes'),
            support_owner=str(final_metadata.get('support_owner') or 'structured_review_capability_facade'),
            final_output_entrypoint=str(final_metadata.get('final_output_entrypoint') or 'hermes_review_assembler'),
            result_ownership='hermes_decision_layer',
            module_bucketing='execution_metadata_first',
            support_material_present=bool(issues),
        ),
        raw=result if include_raw else {},
    )
