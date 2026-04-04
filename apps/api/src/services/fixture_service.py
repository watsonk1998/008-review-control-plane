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
        return [FixtureRecord(**self._normalize_record(item)) for item in payload]

    def get_fixture(self, fixture_id: str) -> FixtureRecord | None:
        for item in self.list_fixtures():
            if item.id == fixture_id:
                return item
        return None

    def _normalize_record(self, item: dict) -> dict:
        normalized = dict(item)
        normalized['sourcePath'] = self._normalize_path(item.get('sourcePath'))
        normalized['copiedPath'] = self._normalize_path(item.get('copiedPath'))
        return normalized

    def _normalize_path(self, raw_path: str | None) -> str:
        if not raw_path:
            return ''
        candidate = Path(raw_path)
        if candidate.exists():
            return str(candidate.resolve())
        if not candidate.is_absolute():
            return str((self.manifest_path.parent / candidate).resolve())
        parts = list(candidate.parts)
        if 'fixtures' in parts:
            repo_root = self.manifest_path.parent.parent
            fixtures_relative = Path(*parts[parts.index('fixtures') + 1 :])
            rewritten = repo_root / 'fixtures' / fixtures_relative
            if rewritten.exists():
                return str(rewritten.resolve())
        return str(candidate)
