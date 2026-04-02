from __future__ import annotations

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


@router.get('/api/fixtures')
async def fixtures():
    return [fixture.model_dump(mode='json') for fixture in get_fixture_service().list_fixtures()]


@router.post('/api/diagnostics/check')
async def diagnostics_check():
    return await get_capability_health()
