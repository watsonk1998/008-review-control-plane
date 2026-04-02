from __future__ import annotations

from fastapi import APIRouter, HTTPException

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
