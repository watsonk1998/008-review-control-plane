from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from src.domain.models import CreateReviewTaskRequest, CreateReviewTaskResponse
from src.main_dependencies import get_task_service
from src.routes.review_task_contracts import (
    build_artifact_ready_event,
    build_review_task_result,
    build_review_task_status,
    build_task_created_event,
    build_terminal_event,
    compile_create_task_request,
    map_task_event_to_sse,
)

router = APIRouter(prefix='/api/review-tasks', tags=['review-tasks'])
REVIEW_TASK_STREAM_POLL_SECONDS = 1.0
REVIEW_TASK_STREAM_HEARTBEAT_SECONDS = 10.0


def _sse_event(payload: dict) -> str:
    return f"event: {payload['event']}\ndata: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


@router.post('')
async def create_review_task(request: CreateReviewTaskRequest):
    service = get_task_service()
    try:
        internal_request, plan_seed = compile_create_task_request(request)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail={'code': 'file_not_found', 'message': f'Unknown file_id: {exc.args[0]}'}) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={'code': 'invalid_review_task_request', 'message': str(exc)}) from None

    task = service.create_task(internal_request)
    task = service.store.update_task(task.id, plan=plan_seed)
    service.schedule_task(task.id)
    return CreateReviewTaskResponse(
        task_id=task.id,
        status='created',
        review_brief_id=task.id,
        links={
            'status': f'/api/review-tasks/{task.id}',
            'events': f'/api/review-tasks/{task.id}/events',
            'result': f'/api/review-tasks/{task.id}/result',
        },
    ).model_dump(mode='json')


@router.get('/{task_id}')
async def get_review_task(task_id: str):
    service = get_task_service()
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail={'code': 'task_not_found', 'message': 'Task not found'})
    return build_review_task_status(task, service.get_task_events(task_id)).model_dump(mode='json')


@router.get('/{task_id}/events')
async def stream_review_task_events(task_id: str, request: Request):
    service = get_task_service()
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail={'code': 'task_not_found', 'message': 'Task not found'})

    async def event_generator():
        terminal_statuses = {'succeeded', 'failed', 'partial'}
        last_heartbeat_at = 0.0
        current_task = service.get_task(task_id)
        current_events = service.get_task_events(task_id)
        current_artifacts = service.list_task_artifacts(task_id)
        last_task_updated_at = current_task.updatedAt.isoformat() if current_task else None
        last_event_count = len(current_events)
        last_artifact_names = [artifact.fileName for artifact in current_artifacts]

        if current_task is not None:
            yield _sse_event(build_task_created_event(current_task).model_dump(mode='json'))
            for event in current_events:
                yield _sse_event(map_task_event_to_sse(current_task, event).model_dump(mode='json'))
            for artifact in current_artifacts:
                yield _sse_event(build_artifact_ready_event(current_task, artifact).model_dump(mode='json'))
            if current_task.status in terminal_statuses:
                yield _sse_event(build_terminal_event(current_task).model_dump(mode='json'))
                return

        while True:
            if await request.is_disconnected():
                break
            await asyncio.sleep(REVIEW_TASK_STREAM_POLL_SECONDS)
            current_task = service.get_task(task_id)
            if current_task is None:
                break

            current_events = service.get_task_events(task_id)
            if len(current_events) > last_event_count:
                for event in current_events[last_event_count:]:
                    yield _sse_event(map_task_event_to_sse(current_task, event).model_dump(mode='json'))
                last_event_count = len(current_events)

            current_artifacts = service.list_task_artifacts(task_id)
            artifact_names = [artifact.fileName for artifact in current_artifacts]
            if artifact_names != last_artifact_names:
                known_names = set(last_artifact_names)
                for artifact in current_artifacts:
                    if artifact.fileName not in known_names:
                        yield _sse_event(build_artifact_ready_event(current_task, artifact).model_dump(mode='json'))
                last_artifact_names = artifact_names

            task_updated_at = current_task.updatedAt.isoformat()
            if task_updated_at != last_task_updated_at and current_task.status in terminal_statuses:
                last_task_updated_at = task_updated_at
                yield _sse_event(build_terminal_event(current_task).model_dump(mode='json'))
                break

            now = asyncio.get_running_loop().time()
            if now - last_heartbeat_at >= REVIEW_TASK_STREAM_HEARTBEAT_SECONDS:
                last_heartbeat_at = now
                heartbeat = {
                    'event': 'progress',
                    'task_id': task_id,
                    'stage': build_review_task_status(current_task, current_events).progress_stage,
                    'message': 'heartbeat',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'status': build_review_task_status(current_task, current_events).status,
                    'payload': {'heartbeat': True},
                }
                yield _sse_event(heartbeat)

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
async def get_review_task_result(task_id: str, debug: bool = False):
    service = get_task_service()
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail={'code': 'task_not_found', 'message': 'Task not found'})
    if task.taskType != 'structured_review':
        raise HTTPException(status_code=400, detail={'code': 'invalid_task_type', 'message': 'Review task result is only supported for structured_review'})
    if task.result is None:
        raise HTTPException(status_code=409, detail={'code': 'result_not_ready', 'message': 'Result is not ready yet'})
    artifacts = service.list_task_artifacts(task_id)
    return build_review_task_result(task, artifacts, include_raw=debug).model_dump(mode='json')
