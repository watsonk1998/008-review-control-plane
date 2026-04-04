from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse

from src.domain.models import CreateTaskRequest, ReviewerDecisionUpdateRequest
from src.main_dependencies import get_task_service
from src.review.reviewer_decision import resolve_reviewer_decision
from src.review.support_scope import get_support_scope_payload

router = APIRouter(prefix='/api/tasks', tags=['tasks'])
TASK_STREAM_POLL_SECONDS = 1.0
TASK_STREAM_HEARTBEAT_SECONDS = 10.0


def _serialize_structured_review_result(result):
    if not isinstance(result, dict):
        return result
    if not {'summary', 'issues', 'matrices', 'resolvedProfile'}.issubset(result.keys()):
        return result
    payload = dict(result)
    is_legacy_payload = payload.get('visibility') is None
    if is_legacy_payload:
        visibility_summary = ((payload.get('summary') or {}).get('visibilitySummary') or {})
        payload['visibility'] = {
            'parseMode': None,
            'attachmentCount': visibility_summary.get('attachmentCount', 0),
            'counts': visibility_summary.get('counts', {}),
            'reasonCounts': visibility_summary.get('reasonCounts', {}),
            'duplicateSectionTitles': visibility_summary.get('duplicateSectionTitles', []),
            'parseWarnings': visibility_summary.get('parseWarnings', []),
            'manualReviewNeeded': visibility_summary.get('manualReviewNeeded', False),
            'manualReviewReason': None,
            'parserLimited': False,
            'fileType': None,
        }
    if is_legacy_payload:
        payload['issues'] = [
            {
                **issue,
                'whetherManualReviewNeeded': issue.get('manualReviewNeeded', False),
            }
            for issue in payload.get('issues', [])
        ]
    return payload


def _serialize_task(task):
    payload = task.model_dump(mode='json')
    if task.taskType == 'structured_review':
        payload['reviewerDecision'] = resolve_reviewer_decision(task).model_dump(mode='json')
    payload['result'] = _serialize_structured_review_result(payload.get('result'))
    return payload


def _task_summary_payload(task):
    return {
        'id': task.id,
        'taskType': task.taskType,
        'capabilityMode': task.capabilityMode,
        'status': task.status,
        'query': task.query,
        'fixtureId': task.fixtureId,
        'sourceDocumentRef': task.sourceDocumentRef.model_dump(mode='json') if task.sourceDocumentRef else None,
        'documentType': task.documentType,
        'createdAt': task.createdAt.isoformat(),
        'updatedAt': task.updatedAt.isoformat(),
    }


def _sse_event(name: str, payload) -> str:
    return f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


@router.post('')
async def create_task(request: CreateTaskRequest):
    service = get_task_service()
    task = service.create_task(request)
    service.schedule_task(task.id)
    return _serialize_task(task)


@router.get('/support-scope')
async def get_support_scope():
    return get_support_scope_payload()


@router.get('')
async def list_tasks(limit: int = Query(default=8, ge=1, le=50)):
    service = get_task_service()
    tasks = service.list_tasks(limit=limit)
    return [_task_summary_payload(task) for task in tasks]


@router.get('/{task_id}')
async def get_task(task_id: str):
    service = get_task_service()
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail='Task not found')
    return _serialize_task(task)


@router.get('/{task_id}/stream')
async def stream_task(task_id: str, request: Request):
    service = get_task_service()
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail='Task not found')

    async def event_generator():
        terminal_statuses = {'succeeded', 'failed', 'partial'}
        last_heartbeat_at = 0.0
        current_task = service.get_task(task_id)
        current_events = service.get_task_events(task_id)
        current_artifacts = service.list_task_artifacts(task_id)
        last_task_updated_at = current_task.updatedAt.isoformat() if current_task else None
        last_event_count = len(current_events)
        last_artifact_payload = [artifact.model_dump(mode='json') for artifact in current_artifacts]

        yield _sse_event(
            'snapshot',
            {
                'task': _serialize_task(current_task) if current_task else None,
                'events': [event.model_dump(mode='json') for event in current_events],
                'artifacts': last_artifact_payload,
            },
        )

        while True:
            if await request.is_disconnected():
                break

            await asyncio.sleep(TASK_STREAM_POLL_SECONDS)

            current_task = service.get_task(task_id)
            if current_task is None:
                break

            task_updated_at = current_task.updatedAt.isoformat()
            if task_updated_at != last_task_updated_at:
                last_task_updated_at = task_updated_at
                yield _sse_event('task', _serialize_task(current_task))

            current_events = service.get_task_events(task_id)
            if len(current_events) > last_event_count:
                for event in current_events[last_event_count:]:
                    yield _sse_event('event', event.model_dump(mode='json'))
                last_event_count = len(current_events)

            current_artifacts = service.list_task_artifacts(task_id)
            artifact_payload = [artifact.model_dump(mode='json') for artifact in current_artifacts]
            if artifact_payload != last_artifact_payload:
                last_artifact_payload = artifact_payload
                yield _sse_event('artifacts', artifact_payload)

            now = asyncio.get_running_loop().time()
            if now - last_heartbeat_at >= TASK_STREAM_HEARTBEAT_SECONDS:
                last_heartbeat_at = now
                yield _sse_event(
                    'heartbeat',
                    {
                        'taskId': task_id,
                        'serverTime': datetime.now(timezone.utc).isoformat(),
                    },
                )

            if current_task.status in terminal_statuses:
                break

    return StreamingResponse(
        event_generator(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        },
    )


@router.get('/{task_id}/result')
async def get_task_result(task_id: str):
    service = get_task_service()
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail='Task not found')
    return {
        'taskId': task_id,
        'status': task.status,
        'result': _serialize_structured_review_result(task.result),
        'error': task.error,
    }


@router.put('/{task_id}/reviewer-decision')
async def update_reviewer_decision(task_id: str, request: ReviewerDecisionUpdateRequest):
    service = get_task_service()
    try:
        task = service.update_reviewer_decision(task_id, request)
    except KeyError:
        raise HTTPException(status_code=404, detail='Task not found') from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize_task(task)


@router.get('/{task_id}/events')
async def get_task_events(task_id: str):
    service = get_task_service()
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail='Task not found')
    return [event.model_dump(mode='json') for event in service.get_task_events(task_id)]


@router.get('/{task_id}/artifacts')
async def list_task_artifacts(task_id: str):
    service = get_task_service()
    try:
        artifacts = service.list_task_artifacts(task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail='Task not found') from None
    return [artifact.model_dump(mode='json') for artifact in artifacts]


@router.get('/{task_id}/artifacts/{artifact_name:path}')
async def download_task_artifact(task_id: str, artifact_name: str):
    service = get_task_service()
    try:
        artifact_path = service.resolve_task_artifact(task_id, artifact_name)
    except KeyError:
        raise HTTPException(status_code=404, detail='Task not found') from None
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail='Artifact not found') from None
    return FileResponse(path=artifact_path, filename=artifact_path.name)
