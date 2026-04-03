from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    project_root: Path
    artifacts_dir: Path
    verification_dir: Path
    tasks_dir: Path
    uploads_dir: Path
    database_path: Path
    fixture_manifest_path: Path
    api_host: str
    api_port: int
    web_origin: str
    gpt_researcher_external_path: str | None
    deeptutor_base_url: str | None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    project_root = Path(__file__).resolve().parents[4]
    artifacts_dir = project_root / 'artifacts'
    verification_dir = artifacts_dir / 'verification'
    tasks_dir = artifacts_dir / 'tasks'
    uploads_dir = artifacts_dir / 'uploads'
    verification_dir.mkdir(parents=True, exist_ok=True)
    tasks_dir.mkdir(parents=True, exist_ok=True)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    return Settings(
        project_root=project_root,
        artifacts_dir=artifacts_dir,
        verification_dir=verification_dir,
        tasks_dir=tasks_dir,
        uploads_dir=uploads_dir,
        database_path=tasks_dir / 'runtime.sqlite',
        fixture_manifest_path=project_root / 'fixtures' / 'manifest.json',
        api_host=os.getenv('REVIEW_CONTROL_API_HOST', '127.0.0.1'),
        api_port=int(os.getenv('REVIEW_CONTROL_API_PORT', '8018')),
        web_origin=os.getenv('REVIEW_CONTROL_WEB_ORIGIN', 'http://127.0.0.1:3008'),
        gpt_researcher_external_path=os.getenv('GPT_RESEARCHER_EXTERNAL_PATH'),
        deeptutor_base_url=os.getenv('DEEPTUTOR_BASE_URL'),
    )
