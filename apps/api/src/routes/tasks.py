from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from src.domain.models import CreateTaskRequest
from src.main_dependencies import get_task_service

router = APIRouter(prefix='/api/tasks', tags=['tasks'])


@router.post('')
async def create_task(request: CreateTaskRequest):
    service = get_task_service()
    task = service.create_task(request)
    service.schedule_task(task.id)
    return task.model_dump(mode='json')


@router.get('/{task_id}')
async def get_task(task_id: str):
    service = get_task_service()
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail='Task not found')
    return task.model_dump(mode='json')


@router.get('/{task_id}/result')
async def get_task_result(task_id: str):
    service = get_task_service()
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail='Task not found')
    return {
        'taskId': task_id,
        'status': task.status,
        'result': task.result,
        'error': task.error,
    }


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
