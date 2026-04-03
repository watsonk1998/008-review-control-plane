from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from src.main_dependencies import get_capability_health, get_fixture_service, get_store

router = APIRouter(tags=['system'])


@router.get('/api/health')
async def health():
    return {
        'status': 'ok',
        'database': get_store().database_path,
        'capabilities': await get_capability_health(),
        'fixtureCount': len(get_fixture_service().list_fixtures()),
    }


@router.get('/api/capabilities')
async def capabilities():
    return await get_capability_health()


@router.get('/api/heartbeat')
async def heartbeat():
    store = get_store()
    latest_task_updated_at = store.latest_task_updated_at()
    return {
        'status': 'ok',
        'serverTime': datetime.now(timezone.utc).isoformat(),
        'database': store.database_path,
        'runningTaskCount': store.count_running_tasks(),
        'latestTaskUpdatedAt': latest_task_updated_at.isoformat() if latest_task_updated_at else None,
    }


@router.get('/api/fixtures')
async def fixtures():
    return [fixture.model_dump(mode='json') for fixture in get_fixture_service().list_fixtures()]


@router.post('/api/diagnostics/check')
async def diagnostics_check():
    return await get_capability_health()
