from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from src.main import app
from src.routes import system as system_route


def test_heartbeat_route_returns_lightweight_runtime_summary(monkeypatch):
    latest_updated_at = datetime(2026, 4, 3, 8, 0, tzinfo=timezone.utc)

    class FakeStore:
        database_path = '/tmp/test-runtime.sqlite'

        def count_running_tasks(self):
            return 3

        def latest_task_updated_at(self):
            return latest_updated_at

    monkeypatch.setattr(system_route, 'get_store', lambda: FakeStore())
    client = TestClient(app)

    response = client.get('/api/heartbeat')
    assert response.status_code == 200
    payload = response.json()
    assert payload['status'] == 'ok'
    assert payload['database'] == '/tmp/test-runtime.sqlite'
    assert payload['runningTaskCount'] == 3
    assert payload['latestTaskUpdatedAt'] == latest_updated_at.isoformat()
    assert payload['serverTime']
