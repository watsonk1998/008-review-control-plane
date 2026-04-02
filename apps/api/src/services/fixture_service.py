from __future__ import annotations

from pathlib import Path
import json

from src.domain.models import FixtureRecord


class FixtureService:
    def __init__(self, manifest_path: Path):
        self.manifest_path = manifest_path

    def list_fixtures(self) -> list[FixtureRecord]:
        if not self.manifest_path.exists():
            return []
        payload = json.loads(self.manifest_path.read_text())
        return [FixtureRecord(**item) for item in payload]

    def get_fixture(self, fixture_id: str) -> FixtureRecord | None:
        for item in self.list_fixtures():
            if item.id == fixture_id:
                return item
        return None
